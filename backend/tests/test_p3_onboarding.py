"""P3 tests — onboarding F13: episode withholding, XP idempotency, funnel, complete.

Covers the RED-LINE ACs:
- outcome value NOT present in the setup (pre-reveal) response — server withholds.
- onboarding XP is server-authoritative + idempotent (UNIQUE user+source+ref).
"""
import json
from urllib.parse import urlparse, parse_qs

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.main import app


def _login(client: TestClient, email: str) -> None:
    r = client.post("/api/auth/magic-link", json={"email": email})
    token = parse_qs(urlparse(r.json()["dev_magic_link"]).query)["token"][0]
    client.get("/api/auth/verify", params={"token": token})


# ── Seed / withholding ────────────────────────────────────────────────────────


def test_episodes_seeded():
    """The 3 curated episodes seed (E1 trap, E3 valid_setup, E4 patience)."""
    with TestClient(app) as client:
        r = client.get("/api/onboarding/episodes")
    assert r.status_code == 200
    eps = {e["ext_id"]: e for e in r.json()}
    assert set(eps) == {"E1", "E3", "E4"}
    assert eps["E1"]["scenario_type"] == "trap"
    assert eps["E3"]["scenario_type"] == "valid_setup"
    assert eps["E4"]["scenario_type"] == "patience"
    assert eps["E3"]["score"] == 86  # PASS demo quality signal


def test_setup_withholds_outcome_pre_reveal():
    """AC: the outcome value is NOT in the DOM (setup response) before reveal (S10)."""
    with TestClient(app) as client:
        r = client.get("/api/onboarding/episodes/E4")  # S10 time-machine, reveal-gated
    assert r.status_code == 200
    body = r.json()
    # structurally withheld: no outcome object, and withheld candles remain server-side
    assert "outcome" not in body
    assert body["reveal_count"] > 0
    assert len(body["setup_klines"]) == body["entry_index"] + 1
    # the withheld numbers (+3.33R, target 1770.6, +10%) must not leak into the payload
    raw = r.text
    assert "3.33" not in raw
    assert "1770" not in raw
    assert "r_multiple" not in raw


def test_reveal_returns_withheld_outcome():
    """The explicit reveal call returns the outcome + playback candles."""
    with TestClient(app) as client:
        setup = client.get("/api/onboarding/episodes/E4").json()
        r = client.post("/api/onboarding/episodes/E4/reveal")
    assert r.status_code == 200
    body = r.json()
    assert len(body["reveal_klines"]) == setup["reveal_count"]
    oc = body["outcome"]
    assert oc["resolved"] == "win"
    assert oc["r_multiple"] == 3.33
    assert oc["pct"] == 10.0  # empirically derived from the real klines


def test_valid_setup_reveal_has_risk_and_checks():
    """S8 PASS demo: E3 reveal carries the Calculated Risk Level + top passed checks."""
    with TestClient(app) as client:
        r = client.post("/api/onboarding/episodes/E3/reveal")
    oc = r.json()["outcome"]
    assert oc["risk_price"] == 0.1511  # verified ADA Calculated Risk Level (drawn on S8)
    assert oc["exit_price"] == 0.1391  # Calculated Target Level
    checks = oc["checks"]
    ids = {c["id"] for c in checks}
    assert {"regime", "weekly_bias", "ema7_slope", "volume"} <= ids
    assert all(c["pass"] for c in checks)


def test_trap_outcome_is_a_real_loss():
    """E1 trap resolves to a real (kline-derived) loss — no fabricated drop."""
    with TestClient(app) as client:
        r = client.post("/api/onboarding/episodes/E1/reveal")
    oc = r.json()["outcome"]
    assert oc["resolved"] == "loss"
    assert oc["pct"] < -5  # >=5% fade, asserted at build time


def test_unknown_episode_404():
    with TestClient(app) as client:
        assert client.get("/api/onboarding/episodes/E9").status_code == 404


# ── XP: single lifetime grant + anti-farming (once per user ever) ─────────────


def test_onboarding_xp_granted_once_at_completion():
    """Completion credits the one-time onboarding grant of 300 (server-priced)."""
    with TestClient(app) as client:
        _login(client, "xp1@example.com")
        assert client.get("/api/onboarding/xp").json()["total"] == 0  # nothing before completion
        client.post("/api/onboarding/complete")
        state = client.get("/api/onboarding/xp").json()
    assert state["total"] == 300
    assert len(state["events"]) == 1


def test_onboarding_xp_replay_grants_zero():
    """REGRESSION: replaying onboarding (completing again) grants 0 more XP."""
    with TestClient(app) as client:
        _login(client, "xp2@example.com")
        client.post("/api/onboarding/complete")
        client.post("/api/onboarding/complete")  # replay
        client.post("/api/onboarding/complete")  # replay
        state = client.get("/api/onboarding/xp").json()
    assert state["total"] == 300  # still exactly one grant
    assert len(state["events"]) == 1


def test_xp_requires_auth():
    with TestClient(app) as client:
        r = client.get("/api/onboarding/xp")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_xp_onboarding_once_per_user_index():
    """The anti-farming guard is a partial unique index (once per user+source)."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        idx = await db.execute_fetchall("PRAGMA index_list(xp_events)")
    names = {row[1] for row in idx}
    assert "ux_xp_onboarding_once" in names


@pytest.mark.asyncio
async def test_xp_partial_unique_blocks_second_onboarding_row():
    """A direct second onboarding row for the same user is rejected by the index."""
    import aiosqlite as _sq

    async with _sq.connect(cfg.DATABASE_URL) as db:
        await db.execute("PRAGMA foreign_keys=OFF")
        await db.execute(
            "INSERT INTO xp_events (user_id, source, ref, amount) VALUES (999001, 'onboarding', 'a', 300)"
        )
        await db.commit()
        raised = False
        try:
            await db.execute(
                "INSERT INTO xp_events (user_id, source, ref, amount) VALUES (999001, 'onboarding', 'b', 300)"
            )
            await db.commit()
        except _sq.IntegrityError:
            raised = True
    assert raised, "partial unique index must block a second onboarding row per user"


# ── Funnel ────────────────────────────────────────────────────────────────────


def test_funnel_accepts_anon_and_user():
    """Pre-signup events carry anon_id (no auth); post-signup carry user_id."""
    with TestClient(app) as client:
        # pre-signup, anonymous
        a = client.post(
            "/api/onboarding/funnel",
            json={"stage": "branch_1a_to_s2", "anon_id": "anon-abc", "detail": {"screen": "S1a"}},
        )
        assert a.status_code == 200
        # post-signup, authenticated
        _login(client, "funnel@example.com")
        b = client.post("/api/onboarding/funnel", json={"stage": "fork_choice", "detail": {"choice": "trial"}})
        assert b.status_code == 200


def test_complete_marks_user_and_logs_completion():
    with TestClient(app) as client:
        _login(client, "done@example.com")
        r = client.post("/api/onboarding/complete")
        assert r.status_code == 200
        me = client.get("/api/auth/me").json()
    assert me["data"]["onboarding_completed"] is True
