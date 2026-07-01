"""P1 tests — auth (TC-A) + billing/Cardcom test-mode (TC-F)."""
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.core import cardcom_service
from backend.core.auth import hash_token, is_email_allowed
from backend.main import app


def _token_from_dev_link(link: str) -> str:
    return parse_qs(urlparse(link).query)["token"][0]


# ── TC-A — Auth ───────────────────────────────────────────────────────────────

def test_magic_link_signup_login_and_me():
    """magic-link creates a user, verify sets the cookie, /me returns the user."""
    with TestClient(app) as client:
        r = client.post("/api/auth/magic-link", json={"email": "trader@example.com"})
        assert r.status_code == 200
        link = r.json()["dev_magic_link"]

        token = _token_from_dev_link(link)
        v = client.get("/api/auth/verify", params={"token": token})
        assert v.status_code == 200

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["data"]["email"] == "trader@example.com"
        assert me.json()["data"]["is_admin"] is False


def test_me_requires_auth():
    """/me without a cookie → 401."""
    with TestClient(app) as client:
        assert client.get("/api/auth/me").status_code == 401


@pytest.mark.asyncio
async def test_magic_link_token_is_hashed_not_plaintext():
    """The stored magic_link_token is a SHA-256 hash, never the raw token (SPEC §4)."""
    with TestClient(app) as client:
        r = client.post("/api/auth/magic-link", json={"email": "hashcheck@example.com"})
        raw = _token_from_dev_link(r.json()["dev_magic_link"])

    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall(
            "SELECT magic_link_token FROM users WHERE email = ?", ("hashcheck@example.com",)
        )
    stored = rows[0][0]
    assert stored != raw
    assert stored == hash_token(raw)


def test_bootstrap_admin_gets_is_admin():
    """The founder email is auto-granted is_admin on signup (DB role, not env)."""
    with TestClient(app) as client:
        r = client.post("/api/auth/magic-link", json={"email": "rodanis@gmail.com"})
        token = _token_from_dev_link(r.json()["dev_magic_link"])
        client.get("/api/auth/verify", params={"token": token})
        me = client.get("/api/auth/me")
    assert me.json()["data"]["is_admin"] is True


def test_apple_is_stub_501():
    with TestClient(app) as client:
        assert client.post("/api/auth/apple").status_code == 501


@pytest.mark.asyncio
async def test_beta_gate_blocks_when_closed(monkeypatch):
    """With signups closed, only allowlisted emails pass the beta gate."""
    monkeypatch.setattr(cfg, "FEATURE_PUBLIC_SIGNUPS_OPEN", False)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        assert await is_email_allowed("rodanis@gmail.com", db) is True   # seeded allowlist
        assert await is_email_allowed("random@nobody.com", db) is False


def test_waitlist_join():
    with TestClient(app) as client:
        r = client.post("/api/waitlist", json={"email": "wait@example.com", "source": "test"})
    assert r.status_code == 200
    assert r.json()["email"] == "wait@example.com"


# ── TC-F — Billing / Cardcom (TEST mode) ─────────────────────────────────────

def _login(client: TestClient, email: str) -> None:
    r = client.post("/api/auth/magic-link", json={"email": email})
    token = _token_from_dev_link(r.json()["dev_magic_link"])
    client.get("/api/auth/verify", params={"token": token})


def test_cardcom_initiate_test_mode_returns_503():
    """FEATURE_CARDCOM_LIVE=false → initiate is 503 (no real terminal). No live charge."""
    with TestClient(app) as client:
        _login(client, "buyer@example.com")
        r = client.post("/api/cardcom/initiate", json={"plan": "basic"})
    assert r.status_code == 503


def test_cardcom_status_after_login():
    with TestClient(app) as client:
        _login(client, "statuscheck@example.com")
        r = client.get("/api/cardcom/status")
    assert r.status_code == 200
    body = r.json()
    assert body["subscription_status"] == "none"
    assert body["tier"] == "free"


def test_cardcom_webhook_bad_signature_is_ignored():
    """A webhook with a bad HMAC signature is ignored but still returns 200."""
    with TestClient(app) as client:
        r = client.post(
            "/api/cardcom/webhook",
            headers={"X-Cardcom-Signature": "deadbeef"},
            content=b'{"LowProfileId":"x","ResponseCode":0}',
        )
    assert r.status_code == 200
    assert r.json()["received"] is True


@pytest.mark.asyncio
async def test_start_trial_sets_trial_state():
    """start_trial puts the user on a 14-day trial with a billing date."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "INSERT INTO users (email, auth_provider, created_at) VALUES (?, 'email', ?)",
            ("trialuser@example.com", datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()
        user_id = cur.lastrowid

        result = await cardcom_service.start_trial(db, user_id, plan="advanced")
        assert result["subscription_status"] == "trial"
        assert result["tier"] == "advanced"

        rows = await db.execute_fetchall(
            "SELECT subscription_status, tier, trial_ends_at FROM users WHERE internal_id=?", (user_id,)
        )
    assert rows[0]["subscription_status"] == "trial"
    assert rows[0]["trial_ends_at"] is not None


@pytest.mark.asyncio
async def test_expire_trials_marks_expired():
    """expire_trials flips a past-due trial to expired/free."""
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """INSERT INTO users (email, auth_provider, subscription_status, tier,
                                  trial_started_at, trial_ends_at, created_at)
               VALUES (?, 'email', 'trial', 'basic', ?, ?, ?)""",
            ("expired@example.com", past, past, past),
        )
        await db.commit()
        user_id = cur.lastrowid

        result = await cardcom_service.expire_trials(db)
        assert result["expired"] >= 1

        rows = await db.execute_fetchall(
            "SELECT subscription_status, tier FROM users WHERE internal_id=?", (user_id,)
        )
    assert rows[0]["subscription_status"] == "expired"
    assert rows[0]["tier"] == "free"


@pytest.mark.asyncio
async def test_plan_prices_seeded():
    """Migration 019 seeded the 3 FINARODA plan prices (agorot)."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        assert await cardcom_service.get_plan_price_agorot(db, "basic") == 5000
        assert await cardcom_service.get_plan_price_agorot(db, "advanced") == 10000
        assert await cardcom_service.get_plan_price_agorot(db, "pro") == 15000
