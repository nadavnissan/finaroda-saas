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


# ── XP: server-authoritative + idempotent ─────────────────────────────────────


def test_xp_award_idempotent_and_server_priced():
    """Awarding the same ref twice never doubles; amount comes from the server."""
    with TestClient(app) as client:
        _login(client, "xp1@example.com")
        r1 = client.post("/api/onboarding/xp", json={"ref": "s2_scan"})
        assert r1.status_code == 200
        assert r1.json()["total"] == 50
        # replay the same ref → no double award
        r2 = client.post("/api/onboarding/xp", json={"ref": "s2_scan"})
        assert r2.json()["total"] == 50
        assert len(r2.json()["events"]) == 1


def test_full_onboarding_xp_totals_300():
    """The four onboarding awards sum to the locked 300 (50+100+50+100)."""
    with TestClient(app) as client:
        _login(client, "xp2@example.com")
        for ref in ("s2_scan", "s4_first_decision", "s8_scan", "s8_lesson"):
            client.post("/api/onboarding/xp", json={"ref": ref})
        state = client.get("/api/onboarding/xp").json()
    assert state["total"] == 300


def test_xp_rejects_unknown_ref():
    """A client cannot invent a ref (and cannot inject an amount)."""
    with TestClient(app) as client:
        _login(client, "xp3@example.com")
        r = client.post("/api/onboarding/xp", json={"ref": "hack_1000000"})
    assert r.status_code == 400


def test_xp_requires_auth():
    with TestClient(app) as client:
        r = client.post("/api/onboarding/xp", json={"ref": "s2_scan"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_xp_events_unique_constraint():
    """The farming guard is enforced at the schema level."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        idx = await db.execute_fetchall("PRAGMA index_list(xp_events)")
    assert any("unique" in str(row).lower() or row[2] == 1 for row in idx)


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
