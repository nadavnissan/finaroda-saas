"""Package B phase 2 — B4 journal/reveal-gating, B5 profile, B6 academy, B7 admin.

The headline regression is reveal-withholding: an outcome computed server-side must not
appear in ANY client payload until the user's next scan reveals it (same contract as the
S10 onboarding time-machine).
"""
from urllib.parse import parse_qs, urlparse

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.core.journal import evaluate_outcome
from backend.main import app


def _login(client: TestClient, email: str) -> None:
    r = client.post("/api/auth/magic-link", json={"email": email})
    token = parse_qs(urlparse(r.json()["dev_magic_link"]).query)["token"][0]
    client.get("/api/auth/verify", params={"token": token})


async def _set_user(email: str, **fields) -> None:
    sets = ", ".join(f"{k} = ?" for k in fields)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        await db.execute(f"UPDATE users SET {sets} WHERE email = ?", (*fields.values(), email))
        await db.commit()


async def _user_id(email: str) -> int:
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall("SELECT internal_id FROM users WHERE email = ?", (email,))
        return rows[0][0]


async def _resolve_latest_pass(email: str, status: str, r: float) -> int:
    """Simulate the resolution cron on the user's latest open PASS scenario."""
    uid = await _user_id(email)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall(
            "SELECT id FROM journal_scenarios WHERE user_id=? AND scenario_type='pass' AND status='open' "
            "ORDER BY id DESC LIMIT 1", (uid,))
        sid = rows[0][0]
        await db.execute(
            "UPDATE journal_scenarios SET status=?, r_result=?, resolved_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, r, sid))
        await db.commit()
    return sid


def _pass_scan(coin: str = "LINKUSDT") -> dict:
    return {"coins_scanned": 1, "coins_passed": 1, "threshold": 85, "coins": [
        {"coin": coin, "direction": "short", "profile": "momentum", "score": 86,
         "passed_threshold": 1, "entry": 100.0, "sl": 110.0, "tp": 74.0},
    ]}


def _nopass_scan(coin: str = "LINKUSDT") -> dict:
    return {"coins_scanned": 1, "coins_passed": 0, "threshold": 85, "coins": [
        {"coin": coin, "direction": "long", "profile": "momentum", "score": 60, "passed_threshold": 0},
    ]}


# ── B4: reveal-gating (the headline regression) ──────────────────────────────
@pytest.mark.asyncio
async def test_journal_withholds_outcome_until_reveal():
    email = "reveal_hold@example.com"
    with TestClient(app) as client:
        _login(client, email)
        client.post("/api/scan/events", json=_pass_scan("LINKUSDT"))
        await _resolve_latest_pass(email, "win", 2.60)  # resolved server-side, NOT revealed

        r = client.get("/api/journal")
        assert r.status_code == 200
        body = r.json()
        # The withheld VALUE must not leak anywhere in the payload.
        assert "2.6" not in r.text
        assert "win" not in r.text
        pass_rows = [s for s in body["scenarios"] if s["type"] == "pass"]
        assert len(pass_rows) == 1
        s = pass_rows[0]
        assert s["revealed"] is False
        # No outcome fields disclosed.
        assert s.get("status") in (None,)
        assert s.get("r_result") in (None,)
        assert s.get("resolved_at") in (None,)
        # It counts as awaiting, but contributes 0 revealed R.
        assert body["stats"]["awaiting_reveal"] == 1
        assert body["stats"]["cumulative_r_revealed"] == 0.0

        # Badge is a bare count, never content.
        b = client.get("/api/journal/badge").json()
        assert b == {"unrevealed": 1}


@pytest.mark.asyncio
async def test_next_scan_reveals_outcome():
    email = "reveal_next@example.com"
    with TestClient(app) as client:
        _login(client, email)
        await _set_user(email, tier="pro")  # unlimited scans/day so the reveal 2nd scan lands same day
        client.post("/api/scan/events", json=_pass_scan("LINKUSDT"))
        sid = await _resolve_latest_pass(email, "win", 2.60)

        # The reveal event IS the next scan.
        client.post("/api/scan/events", json=_pass_scan("ETHUSDT"))
        body = client.get("/api/journal").json()
        revealed = next(s for s in body["scenarios"] if s.get("id") == sid)
        assert revealed["revealed"] is True
        assert revealed["status"] == "win"
        assert revealed["r_result"] == 2.60
        assert body["stats"]["cumulative_r_revealed"] == 2.60
        assert client.get("/api/journal/badge").json()["unrevealed"] == 0


@pytest.mark.asyncio
async def test_journal_view_awards_25_xp_once():
    email = "reveal_xp@example.com"
    with TestClient(app) as client:
        _login(client, email)
        await _set_user(email, tier="pro")  # unlimited scans/day so the reveal 2nd scan lands same day
        client.post("/api/scan/events", json=_pass_scan("LINKUSDT"))
        sid = await _resolve_latest_pass(email, "win", 3.0)
        client.post("/api/scan/events", json=_pass_scan("ETHUSDT"))  # reveal

        first = client.post(f"/api/journal/scenarios/{sid}/view").json()
        assert first["xp_awarded"] == 25
        second = client.post(f"/api/journal/scenarios/{sid}/view").json()
        assert second["xp_awarded"] == 0  # idempotent per scenario


def test_watch_is_never_a_scenario_and_skip_is_recorded():
    with TestClient(app) as client:
        _login(client, "noset@example.com")
        client.post("/api/scan/events", json=_nopass_scan("LINKUSDT"))
        body = client.get("/api/journal").json()
        assert all(s["type"] != "pass" for s in body["scenarios"])
        assert any(s["type"] == "no_setups_day" for s in body["scenarios"])


def test_cannot_view_unrevealed_scenario():
    with TestClient(app) as client:
        _login(client, "view_guard@example.com")
        client.post("/api/scan/events", json=_pass_scan("LINKUSDT"))
        body = client.get("/api/journal").json()
        sid = next(s["id"] for s in body["scenarios"] if s["type"] == "pass")
        # Not resolved / not revealed → no outcome to view.
        r = client.post(f"/api/journal/scenarios/{sid}/view")
        assert r.status_code == 409


# ── B4: resolution evaluator (pure, synthetic candles) ───────────────────────
def test_evaluate_outcome_win_loss_save_expired():
    # SHORT: entry 100, sl 110, tp 80 (risk 10, reward 20 → R 2.0).
    win = [{"high": 101, "low": 79, "close": 80}]          # trigger (low<=100) + target (low<=80)
    assert evaluate_outcome("short", 100, 110, 80, win, True) == ("win", 2.0)

    loss = [{"high": 112, "low": 99, "close": 111}]        # trigger + stop (high>=110)
    assert evaluate_outcome("short", 100, 110, 80, loss, True) == ("loss", -1.0)

    # Never triggered (price never fell to entry) within a complete window → capital save.
    save = [{"high": 130, "low": 120, "close": 125}]
    assert evaluate_outcome("short", 100, 110, 80, save, True) == ("save", 0.0)

    # Not yet complete and no hit → stay open.
    assert evaluate_outcome("short", 100, 110, 80, save, False) == ("open", None)

    # Triggered, no target/stop, window complete → expire at last close (signed R).
    exp = [{"high": 101, "low": 95, "close": 96}]          # trigger, closes at 96 → (100-96)/10 = 0.4
    assert evaluate_outcome("short", 100, 110, 80, exp, True) == ("expired", 0.4)


# ── B5: profile ──────────────────────────────────────────────────────────────
def test_profile_call_sign_fallback_and_settings_persist():
    with TestClient(app) as client:
        _login(client, "nighthawk@example.com")
        p = client.get("/api/profile").json()
        assert p["call_sign"] == "NIGHTHAWK"
        assert p["settings"]["risk_style"] == "balanced"

        upd = client.put("/api/profile/settings", json={"risk_style": "aggressive", "call_sign": "OWL"}).json()
        assert upd["settings"]["risk_style"] == "aggressive"
        assert upd["call_sign"] == "OWL"


# ── B6: academy ──────────────────────────────────────────────────────────────
def test_academy_twelve_modules_and_lesson_xp():
    with TestClient(app) as client:
        _login(client, "academy1@example.com")
        data = client.get("/api/academy").json()
        assert len(data["modules"]) == 12

        # A real basic lesson awards +100 once; replay awards 0.
        first = client.post("/api/academy/regime_ema200/complete").json()
        assert first == {"xp_awarded": 100, "completed": True}
        again = client.post("/api/academy/regime_ema200/complete").json()
        assert again["xp_awarded"] == 0

        # A stub module (single term) awards nothing.
        stub = client.post("/api/academy/volume_basics/complete").json()
        assert stub["xp_awarded"] == 0
        assert stub["completed"] is False


@pytest.mark.asyncio
async def test_academy_full_module_locked_for_free():
    email = "academy_free@example.com"
    with TestClient(app) as client:
        _login(client, email)
        await _set_user(email, tier="free", subscription_status="none")
        r = client.post("/api/academy/smart_skip/complete")  # 'full' tier module
        assert r.status_code == 403


# ── B7: admin gating + console ───────────────────────────────────────────────
def test_admin_routes_403_for_non_admin():
    with TestClient(app) as client:
        _login(client, "plainuser@example.com")
        for path in ("/api/admin/overview", "/api/admin/users", "/api/admin/tickets",
                     "/api/admin/settings", "/api/admin/broadcasts", "/api/admin/notifications"):
            assert client.get(path).status_code == 403


@pytest.mark.asyncio
async def test_admin_overview_and_override():
    admin_email = "boss@example.com"
    target_email = "target@example.com"
    with TestClient(app) as client:
        _login(client, target_email)          # create the target user
        _login(client, admin_email)
        await _set_user(admin_email, is_admin=1)

        ov = client.get("/api/admin/overview")
        assert ov.status_code == 200
        assert ov.json()["sample"] is False
        assert "mrr_ils" in ov.json()

        tid = await _user_id(target_email)
        r = client.post(f"/api/admin/users/{tid}/override",
                        json={"action": "plan_override", "value": "pro", "note": "comp"})
        assert r.status_code == 200
        # Applied + audited.
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            u = await db.execute_fetchall("SELECT tier FROM users WHERE internal_id=?", (tid,))
            assert u[0][0] == "pro"
            ev = await db.execute_fetchall(
                "SELECT COUNT(*) FROM admin_events WHERE event_type='override_plan_override' AND target_user_id=?",
                (tid,))
            assert ev[0][0] == 1


@pytest.mark.asyncio
async def test_admin_settings_edit_rejects_non_editable():
    email = "settings_admin@example.com"
    with TestClient(app) as client:
        _login(client, email)
        await _set_user(email, is_admin=1)
        ok = client.put("/api/admin/settings",
                        json={"updates": [{"key": "trial_reminder_day", "value": "12"}], "note": "tune"})
        assert ok.status_code == 200
        bad = client.put("/api/admin/settings",
                         json={"updates": [{"key": "score_gate", "value": "70"}], "note": "nope"})
        assert bad.status_code == 400


@pytest.mark.asyncio
async def test_broadcast_create_and_active_banner():
    admin_email = "caster@example.com"
    with TestClient(app) as client:
        _login(client, admin_email)
        await _set_user(admin_email, is_admin=1)
        r = client.post("/api/admin/broadcasts", json={
            "title": "Heads up", "body": "Your Pro trial ends in 3 days, no card was taken.",
            "audience": "all", "channel_in_app": True, "channel_email": False})
        assert r.status_code == 200
        banner = client.get("/api/broadcasts/active").json()["banner"]
        assert banner is not None
        assert banner["title"] == "Heads up"
