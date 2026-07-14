"""Package B B1 — server-authoritative scan gating, first-scan XP, support tickets."""
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


async def _set_tier(email: str, tier: str) -> None:
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        await db.execute("UPDATE users SET tier = ? WHERE email = ?", (tier, email))
        await db.commit()


def _scan_payload(n: int) -> dict:
    coins = [
        {"coin": f"C{i}USDT", "direction": "long", "score": None, "passed_threshold": 0}
        for i in range(n)
    ]
    return {"coins_scanned": n, "coins_passed": 0, "threshold": 85, "coins": coins}


def test_entitlements_free_defaults():
    with TestClient(app) as client:
        _login(client, "free_ent@example.com")
        r = client.get("/api/scan/entitlements")
        assert r.status_code == 200
        body = r.json()
        assert body["tier"] == "free"
        assert body["coins_per_scan"] == 2
        assert body["chart_layers"] == "ema200_only"
        assert body["scans_per_day"] == 1


@pytest.mark.asyncio
async def test_entitlements_pro_full_layers():
    with TestClient(app) as client:
        _login(client, "pro_ent@example.com")
        await _set_tier("pro_ent@example.com", "pro")
        r = client.get("/api/scan/entitlements")
        body = r.json()
        assert body["tier"] == "pro"
        assert body["coins_per_scan"] == 10
        assert body["chart_layers"] == "full"
        assert body["scans_per_day"] == 0  # unlimited


def test_gating_rejects_over_limit_for_free():
    """Free plan = 2 coins; a 3-coin scan is rejected server-side (403)."""
    with TestClient(app) as client:
        _login(client, "over@example.com")
        r = client.post("/api/scan/events", json=_scan_payload(3))
        assert r.status_code == 403
        detail = r.json()["detail"]
        assert detail["code"] == "PLAN_COIN_LIMIT"
        assert detail["coins_per_scan"] == 2


def test_gating_allows_at_limit():
    with TestClient(app) as client:
        _login(client, "atlimit@example.com")
        r = client.post("/api/scan/events", json=_scan_payload(2))
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_gating_allows_more_coins_for_pro():
    with TestClient(app) as client:
        _login(client, "pro_scan@example.com")
        await _set_tier("pro_scan@example.com", "pro")
        r = client.post("/api/scan/events", json=_scan_payload(10))
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_first_scan_of_day_awards_xp_once():
    """+50 on the first scan of the day; 0 on later scans the same day (D3).
    Pro tier so the daily-scan cap (Bug 3) does not block the second same-day scan."""
    with TestClient(app) as client:
        _login(client, "xp_scan@example.com")
        await _set_tier("xp_scan@example.com", "pro")
        first = client.post("/api/scan/events", json=_scan_payload(1)).json()
        assert first["first_scan_of_day"] is True
        assert first["xp_awarded"] == 50

        second = client.post("/api/scan/events", json=_scan_payload(1)).json()
        assert second["first_scan_of_day"] is False
        assert second["xp_awarded"] == 0

        xp = client.get("/api/onboarding/xp").json()
        daily = [e for e in xp["events"] if e["source"] == "daily_first_scan"]
        assert len(daily) == 1 and daily[0]["amount"] == 50


def test_support_ticket_filed():
    with TestClient(app) as client:
        _login(client, "ticket@example.com")
        r = client.post(
            "/api/support/tickets",
            json={"subject": "Scan stuck", "body": "It hangs on Computing volume", "category": "bug"},
        )
        assert r.status_code == 200
        assert r.json()["id"] > 0
        assert r.json()["status"] == "open"


def test_support_ticket_requires_auth():
    with TestClient(app) as client:
        r = client.post("/api/support/tickets", json={"subject": "x", "body": "y"})
    assert r.status_code == 401


def test_plans_public_comparison_table():
    """B2 — /api/plans returns the three live tiers (Decision A) with prices/coins."""
    with TestClient(app) as client:
        r = client.get("/api/plans")
        assert r.status_code == 200
        body = r.json()
        assert body["currency"] == "₪"
        by = {p["tier"]: p for p in body["plans"]}
        assert set(by) == {"free", "basic", "pro"}    # Advanced retired (mig 029)
        assert by["free"]["price_ils"] == 0
        assert by["basic"]["price_ils"] == 59          # PENDING-ACCOUNTANT
        assert by["pro"]["price_ils"] == 149           # PENDING-ACCOUNTANT
        assert by["free"]["coins_per_scan"] == 2
        assert by["basic"]["coins_per_scan"] == 5      # Basic inherits old Advanced breadth
        assert by["pro"]["coins_per_scan"] == 10
        assert by["free"]["chart_layers"] == "ema200_only"
        assert by["basic"]["chart_layers"] == "full"
        assert by["pro"]["chart_layers"] == "full"


def test_trial_start_no_card():
    """B2 — start the no-card Pro trial; a second attempt is rejected (409)."""
    with TestClient(app) as client:
        _login(client, "trial_b2@example.com")
        r = client.post("/api/billing/trial")
        assert r.status_code == 200
        assert r.json()["subscription_status"] == "trial"
        assert r.json()["tier"] == "pro"
        again = client.post("/api/billing/trial")
        assert again.status_code == 409


# ── Bug 3: daily scan cap enforcement ────────────────────────────────────────
def test_daily_scan_cap_free_blocks_second(monkeypatch):
    """Free = 1 scan/day: the second same-day scan is rejected (429, DAILY_SCAN_LIMIT)."""
    with TestClient(app) as client:
        _login(client, "daily_free@example.com")
        first = client.post("/api/scan/events", json=_scan_payload(1))
        assert first.status_code == 200
        second = client.post("/api/scan/events", json=_scan_payload(1))
        assert second.status_code == 429
        detail = second.json()["detail"]
        assert detail["code"] == "DAILY_SCAN_LIMIT"
        assert detail["scans_per_day"] == 1


@pytest.mark.asyncio
async def test_daily_scan_cap_unlimited_for_paid():
    """Paid (pro) = unlimited (scans_per_day=0): repeated same-day scans all pass."""
    with TestClient(app) as client:
        _login(client, "daily_pro@example.com")
        await _set_tier("daily_pro@example.com", "pro")
        for _ in range(3):
            assert client.post("/api/scan/events", json=_scan_payload(1)).status_code == 200


# ── Bug 4: trial activation → Free on expiry ─────────────────────────────────
@pytest.mark.asyncio
async def test_trial_expires_to_free():
    """An elapsed trial is moved to Free (never charged, never blocked)."""
    from datetime import datetime, timedelta, timezone

    from backend.core import stripe_service

    with TestClient(app) as client:
        _login(client, "trial_expire@example.com")
        assert client.post("/api/billing/trial").status_code == 200
        # Force the trial end into the past, then run the expiry job.
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                "UPDATE users SET trial_ends_at=? WHERE email=?", (past, "trial_expire@example.com")
            )
            await db.commit()
            result = await stripe_service.expire_trials(db)
        assert result["moved_to_free"] >= 1
        status = client.get("/api/billing/status").json()
        assert status["tier"] == "free"
        assert status["subscription_status"] == "none"


# ── Decision B: recent scans history (read-only) ─────────────────────────────
def test_scan_history_lists_and_stores():
    with TestClient(app) as client:
        _login(client, "history@example.com")
        client.post("/api/scan/events", json=_scan_payload(2))
        hist = client.get("/api/scan/history").json()
        assert len(hist["scans"]) == 1
        sid = hist["scans"][0]["scan_event_id"]
        assert hist["scans"][0]["coins_scanned"] == 2
        stored = client.get(f"/api/scan/history/{sid}").json()
        assert stored["scan_event_id"] == sid
        assert len(stored["rows"]) == 2


def test_scan_history_owner_scoped():
    with TestClient(app) as client:
        _login(client, "history_a@example.com")
        client.post("/api/scan/events", json=_scan_payload(1))
        sid = client.get("/api/scan/history").json()["scans"][0]["scan_event_id"]
        _login(client, "history_b@example.com")
        assert client.get(f"/api/scan/history/{sid}").status_code == 404
