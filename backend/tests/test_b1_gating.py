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


def test_first_scan_of_day_awards_xp_once():
    """+50 on the first scan of the day; 0 on later scans the same day (D3)."""
    with TestClient(app) as client:
        _login(client, "xp_scan@example.com")
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
    """B2 — /api/plans returns all four tiers with prices/coins from system_settings."""
    with TestClient(app) as client:
        r = client.get("/api/plans")
        assert r.status_code == 200
        body = r.json()
        assert body["currency"] == "₪"
        by = {p["tier"]: p for p in body["plans"]}
        assert set(by) == {"free", "basic", "advanced", "pro"}
        assert by["free"]["price_ils"] == 0
        assert by["basic"]["price_ils"] == 50
        assert by["advanced"]["price_ils"] == 100
        assert by["pro"]["price_ils"] == 150
        assert by["free"]["coins_per_scan"] == 2
        assert by["pro"]["coins_per_scan"] == 10
        assert by["free"]["chart_layers"] == "ema200_only"
        assert by["pro"]["chart_layers"] == "full"


def test_trial_start_no_card():
    """B2 — start the no-card Pro trial; a second attempt is rejected (409)."""
    with TestClient(app) as client:
        _login(client, "trial_b2@example.com")
        r = client.post("/api/cardcom/trial")
        assert r.status_code == 200
        assert r.json()["subscription_status"] == "trial"
        assert r.json()["tier"] == "pro"
        again = client.post("/api/cardcom/trial")
        assert again.status_code == 409
