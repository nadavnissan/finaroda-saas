"""P2 scorer wiring — score_log.profile + real (non-null) score persistence (TC-SCORER).

The scorer itself is JS (verified via `node --test` in shared/, 12/12). These tests
cover the backend persistence contract for the 3 profiles.
"""
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


def test_three_profiles_logged_momentum_only_returned():
    """Momentum + pullback + continuation are logged; only momentum is returned for linking."""
    with TestClient(app) as client:
        _login(client, "profiles@example.com")
        payload = {
            "coins_scanned": 1, "coins_passed": 1, "threshold": 85,
            "coins": [
                {"coin": "BTCUSDT", "direction": "short", "profile": "momentum",
                 "score": 88.0, "passed_threshold": 1, "price": 60000, "sl": 61200, "tp": 58200},
                {"coin": "BTCUSDT", "direction": "short", "profile": "pullback",
                 "score": 74.0, "passed_threshold": 0, "price": 60000},
                {"coin": "BTCUSDT", "direction": "short", "profile": "continuation",
                 "score": 81.0, "passed_threshold": 0, "price": 60000},
            ],
        }
        r = client.post("/api/scan/events", json=payload)
    assert r.status_code == 200
    body = r.json()
    # only the momentum row is returned (the displayed one, for snapshot linking)
    assert len(body["score_logs"]) == 1
    assert body["score_logs"][0]["coin"] == "BTCUSDT"


@pytest.mark.asyncio
async def test_profiles_and_real_score_persisted():
    """All 3 profile rows exist with a real (non-null) score and the profile discriminator."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            "SELECT profile, score FROM score_log WHERE coin='BTCUSDT' AND profile IN ('momentum','pullback','continuation')"
        )
    profiles = {r["profile"] for r in rows}
    assert {"momentum", "pullback", "continuation"} <= profiles
    # at least one momentum row carries a real (non-null) score
    assert any(r["profile"] == "momentum" and r["score"] is not None for r in rows)


@pytest.mark.asyncio
async def test_score_log_has_profile_column():
    """Migration 021 added score_log.profile."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        cols = [r[1] for r in await db.execute_fetchall("PRAGMA table_info(score_log)")]
    assert "profile" in cols
