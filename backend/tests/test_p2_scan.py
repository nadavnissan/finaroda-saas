"""P2 tests — scan persistence (TC-B) + score_log nullable + CORS proxy guard."""
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


def test_scan_events_persists_with_null_score():
    """A scan records scan_events + one score_log per coin, score NULL (pending pass 2)."""
    with TestClient(app) as client:
        _login(client, "scanner@example.com")
        payload = {
            "coins_scanned": 2,
            "coins_passed": 1,
            "threshold": 85,
            "client_ip_region": "IL",
            "coins": [
                {"coin": "LINKUSDT", "direction": "long", "score": None, "passed_threshold": 1,
                 "ema7_slope_pct": 1.2, "volume_ratio": 1.4, "price": 60000,
                 "entry": 60000, "sl": 58800, "tp": 61800, "trailing_pct": 1.5},
                {"coin": "AVAXUSDT", "direction": "short", "score": None, "passed_threshold": 0,
                 "ema7_slope_pct": -0.5, "volume_ratio": 0.9, "price": 3000,
                 "entry": 3000, "sl": 3060, "tp": 2940, "trailing_pct": 1.5},
            ],
        }
        r = client.post("/api/scan/events", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["scan_event_id"] > 0
        assert len(body["score_logs"]) == 2


def test_scan_events_requires_auth():
    with TestClient(app) as client:
        r = client.post("/api/scan/events", json={"coins_scanned": 0, "coins_passed": 0, "coins": []})
    assert r.status_code == 401


def test_snapshot_persists_blueprint():
    """Showing a Trading Blueprint records a decision_snapshot for the owning user."""
    with TestClient(app) as client:
        _login(client, "snap@example.com")
        r = client.post("/api/scan/events", json={
            "coins_scanned": 1, "coins_passed": 1, "threshold": 85,
            "coins": [{"coin": "LINKUSDT", "direction": "long", "score": None,
                       "passed_threshold": 1, "price": 150, "entry": 150, "sl": 147, "tp": 153}],
        })
        score_log_id = r.json()["score_logs"][0]["id"]
        s = client.post("/api/scan/snapshot", json={
            "score_log_id": score_log_id,
            "card_json": '{"blueprint":"BTC","score":"pending"}',
        })
    assert s.status_code == 200
    assert s.json()["id"] > 0


def test_snapshot_rejects_foreign_score_log():
    """A user cannot snapshot another user's score_log row."""
    with TestClient(app) as client:
        _login(client, "owner@example.com")
        r = client.post("/api/scan/events", json={
            "coins_scanned": 1, "coins_passed": 1, "coins": [
                {"coin": "LINKUSDT", "direction": "long", "score": None, "passed_threshold": 1}]})
        foreign_id = r.json()["score_logs"][0]["id"]
        # second user
        _login(client, "attacker@example.com")
        s = client.post("/api/scan/snapshot", json={"score_log_id": foreign_id, "card_json": "{}"})
    assert s.status_code == 404


def test_market_proxy_whitelist():
    """The CORS-fallback proxy only forwards whitelisted endpoints."""
    with TestClient(app) as client:
        assert client.get("/api/market/proxy/evil").status_code == 400


@pytest.mark.asyncio
async def test_score_log_score_is_nullable():
    """Migration 020 made score_log.score nullable."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        cols = {r[1]: r for r in await db.execute_fetchall("PRAGMA table_info(score_log)")}
    # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
    assert cols["score"][3] == 0, "score_log.score must be NULLABLE"
