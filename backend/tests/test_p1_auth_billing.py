"""P1 tests — auth (TC-A) + billing/Stripe DEV-mode (TC-F)."""
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.core import stripe_service
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


# ── TC-F — Billing / Stripe (DEV mode) ───────────────────────────────────────

def _login(client: TestClient, email: str) -> None:
    r = client.post("/api/auth/magic-link", json={"email": email})
    token = _token_from_dev_link(r.json()["dev_magic_link"])
    client.get("/api/auth/verify", params={"token": token})


def test_checkout_dev_mode_returns_fake_session():
    """FEATURE_STRIPE_LIVE=false + no key → checkout returns a zero-network DEV session
    (lands on the success page). No live charge, and activation still needs the webhook."""
    with TestClient(app) as client:
        _login(client, "buyer@example.com")
        r = client.post("/api/billing/checkout", json={"plan": "basic"})
    assert r.status_code == 200
    body = r.json()
    assert body["dev_mode"] is True
    assert "/checkout/success" in body["redirect_url"]
    assert "session_id=cs_dev_" in body["redirect_url"]


def test_billing_status_after_login():
    with TestClient(app) as client:
        _login(client, "statuscheck@example.com")
        r = client.get("/api/billing/status")
    assert r.status_code == 200
    body = r.json()
    assert body["subscription_status"] == "none"
    assert body["tier"] == "free"


def test_stripe_webhook_bad_signature_is_ignored():
    """A webhook with a bad Stripe signature is ignored but still returns 200 (AC2)."""
    with TestClient(app) as client:
        r = client.post(
            "/api/billing/webhook",
            headers={"Stripe-Signature": "t=1,v1=deadbeef"},
            content=b'{"id":"evt_x","type":"checkout.session.completed"}',
        )
    assert r.status_code == 200
    assert r.json()["received"] is True


@pytest.mark.asyncio
async def test_start_trial_no_card_no_autocharge():
    """TC-F-005 (D1, no-card trial): start_trial puts the user on a 14-day trial with
    NO card and NO auto-charge — next_billing_at stays NULL, no Stripe customer."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "INSERT INTO users (email, auth_provider, created_at) VALUES (?, 'email', ?)",
            ("trialuser@example.com", datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()
        user_id = cur.lastrowid

        result = await stripe_service.start_trial(db, user_id, plan="pro")
        assert result["subscription_status"] == "trial"
        assert result["tier"] == "pro"

        rows = await db.execute_fetchall(
            """SELECT subscription_status, tier, trial_ends_at, next_billing_at, stripe_customer_id
               FROM users WHERE internal_id=?""",
            (user_id,),
        )
    assert rows[0]["subscription_status"] == "trial"
    assert rows[0]["trial_ends_at"] is not None
    # No auto-charge, no Stripe customer created for a card-free trial (D-R2).
    assert rows[0]["next_billing_at"] is None
    assert rows[0]["stripe_customer_id"] is None


@pytest.mark.asyncio
async def test_start_trial_rejects_second_trial():
    """A second start_trial on the same account → 409 (trial already used)."""
    from fastapi import HTTPException

    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "INSERT INTO users (email, auth_provider, created_at) VALUES (?, 'email', ?)",
            ("retrial@example.com", datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()
        user_id = cur.lastrowid
        await stripe_service.start_trial(db, user_id, plan="pro")
        with pytest.raises(HTTPException) as exc:
            await stripe_service.start_trial(db, user_id, plan="pro")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_expire_trials_moves_to_free_never_charges():
    """TC-F-006 (D1/D2): a past-due trial is moved to Free (tier='free',
    subscription_status='none') — not expired/blocked — and is never charged."""
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """INSERT INTO users (email, auth_provider, subscription_status, tier,
                                  trial_started_at, trial_ends_at, created_at)
               VALUES (?, 'email', 'trial', 'pro', ?, ?, ?)""",
            ("lapsed@example.com", past, past, past),
        )
        await db.commit()
        user_id = cur.lastrowid

        result = await stripe_service.expire_trials(db)
        assert result["moved_to_free"] >= 1

        rows = await db.execute_fetchall(
            "SELECT subscription_status, tier, next_billing_at FROM users WHERE internal_id=?", (user_id,)
        )
        evt = await db.execute_fetchall(
            "SELECT event_type FROM subscription_events WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)
        )
    assert rows[0]["subscription_status"] == "none"
    assert rows[0]["tier"] == "free"
    assert rows[0]["next_billing_at"] is None
    assert evt[0]["event_type"] == "trial_ended_to_free"


@pytest.mark.asyncio
async def test_plan_prices_seeded():
    """The two paid plan prices after the three-plan retune (mig 029, agorot)."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        assert await stripe_service.get_plan_price_agorot(db, "basic") == 5900
        assert await stripe_service.get_plan_price_agorot(db, "pro") == 14900
