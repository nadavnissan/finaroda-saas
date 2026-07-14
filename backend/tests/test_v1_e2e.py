"""E2E JOURNEYS (ATP V1, TC-V1-E2E-xx).

Full user journeys chained through the public API (not unit slices): the value here is
that the STAGES compose correctly end to end.

  E2E-01  new user: onboarding -> first scan -> journal reveal -> academy lesson, XP adds up
  E2E-02  subscribe (DEV fake session) -> webhook activate -> cancel -> churn survey -> admin sees it
  E2E-03  referral: bind -> friend's first paid invoice -> referrer rewarded -> bell -> mark read
  E2E-04  coupon: admin creates a plan-restricted coupon -> user validates + wrong-plan checkout rejected

All Stripe/email is DEV/mocked (zero network). Webhooks are signed with the SDK scheme.
"""
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.core import referral_service
from backend.main import app

_WHSEC = "whsec_test_e2e"
_ADMIN = "rodanis@gmail.com"


@pytest.fixture(scope="module", autouse=True)
def _migrate():
    import asyncio
    from backend.migrations.run_migrations import apply_migrations
    asyncio.run(apply_migrations(cfg.DATABASE_URL))


def _login(client: TestClient, email: str) -> None:
    r = client.post("/api/auth/magic-link", json={"email": email})
    token = parse_qs(urlparse(r.json()["dev_magic_link"]).query)["token"][0]
    client.get("/api/auth/verify", params={"token": token})


async def _uid(email: str) -> int:
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall("SELECT internal_id FROM users WHERE email=?", (email,))
        return rows[0][0]


async def _set_user(email: str, **fields) -> None:
    sets = ", ".join(f"{k}=?" for k in fields)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        await db.execute(f"UPDATE users SET {sets} WHERE email=?", (*fields.values(), email))
        await db.commit()


async def _resolve_latest_pass(uid: int, status: str, r: float) -> None:
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        rows = await db.execute_fetchall(
            "SELECT id FROM journal_scenarios WHERE user_id=? AND scenario_type='pass' "
            "AND status='open' ORDER BY id DESC LIMIT 1", (uid,))
        await db.execute(
            "UPDATE journal_scenarios SET status=?, r_result=?, resolved_at=CURRENT_TIMESTAMP "
            "WHERE id=?", (status, r, rows[0][0]))
        await db.commit()


def _pass_scan(coin: str) -> dict:
    return {"coins_scanned": 1, "coins_passed": 1, "threshold": 85, "coins": [
        {"coin": coin, "direction": "short", "profile": "momentum", "score": 86,
         "passed_threshold": 1, "entry": 100.0, "sl": 110.0, "tp": 74.0}]}


def _sign(body: bytes) -> str:
    ts = int(time.time())
    v1 = hmac.new(_WHSEC.encode(), f"{ts}".encode() + b"." + body, hashlib.sha256).hexdigest()
    return f"t={ts},v1={v1}"


def _post_event(client: TestClient, event: dict):
    body = json.dumps(event).encode()
    return client.post("/api/billing/webhook",
                       headers={"Stripe-Signature": _sign(body)}, content=body)


# ── TC-V1-E2E-01 — onboarding -> scan -> reveal -> academy: XP composes to 475 ─
@pytest.mark.asyncio
async def test_e2e_new_user_xp_journey():
    email = "e2e_journey@example.com"
    with TestClient(app) as client:
        _login(client, email)
        await _set_user(email, tier="pro")  # unlimited scans so reveal lands same day
        uid = await _uid(email)

        assert client.post("/api/onboarding/complete").status_code == 200          # +300
        assert client.post("/api/scan/events", json=_pass_scan("BTCUSDT")
                           ).json()["xp_awarded"] == 50                            # +50
        await _resolve_latest_pass(uid, "win", 2.60)
        client.post("/api/scan/events", json=_pass_scan("ETHUSDT"))                # reveals
        journal = client.get("/api/journal").json()
        sid = next(s["id"] for s in journal["scenarios"]
                   if s["type"] == "pass" and s.get("revealed"))
        assert client.post(f"/api/journal/scenarios/{sid}/view").json()["xp_awarded"] == 25
        assert client.post("/api/academy/regime_ema200/complete").json()["xp_awarded"] == 100

        xp = client.get("/api/onboarding/xp").json()
        total = sum(e["amount"] for e in xp["events"])
        assert total == 475, f"onboarding+scan+reveal+lesson should be 475, got {total}"


# ── TC-V1-E2E-02 — subscribe (DEV) -> activate -> cancel -> churn survey ───────
@pytest.mark.asyncio
async def test_e2e_subscribe_cancel_churn(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    email = "e2e_sub@example.com"
    with TestClient(app) as client:
        _login(client, email)
        uid = await _uid(email)
        # DEV fake Checkout Session (zero network) — a redirect URL + pending tx come back.
        co = client.post("/api/billing/checkout", json={"plan": "pro"}).json()
        assert co.get("dev_mode") is True and co.get("redirect_url") and co.get("transaction_id")
        tx = co["transaction_id"]
        assert client.get("/api/billing/status").json()["subscription_status"] != "active"

        # Activation happens ONLY via the signed webhook, never the redirect.
        _post_event(client, {"id": "evt_e2e_sub", "type": "checkout.session.completed",
                             "data": {"object": {"id": "cs_e2e", "client_reference_id": str(uid),
                                                 "customer": "cus_e2e", "subscription": "sub_e2e",
                                                 "amount_total": 14900,
                                                 "metadata": {"user_id": str(uid), "plan": "pro",
                                                              "transaction_id": str(tx)}}}})
        status = client.get("/api/billing/status").json()
        assert status["subscription_status"] == "active" and status["tier"] == "pro"

        # Cancel at period end -> cancelled (access retained until paid-through).
        assert client.post("/api/billing/cancel").status_code == 200
        assert client.get("/api/billing/status").json()["subscription_status"] == "cancelled"

        # Exit survey (separate, skippable client call).
        assert client.post("/api/churn/survey",
                           json={"reason_category": "too_expensive", "would_return": True}
                           ).status_code == 200

    # Admin sees the churn row.
    with TestClient(app) as client:
        _login(client, _ADMIN)
        churn = client.get("/api/admin/churn").json()
        blob = json.dumps(churn)
        assert "too_expensive" in blob


# ── TC-V1-E2E-03 — referral reward -> bell notification -> mark read ──────────
@pytest.mark.asyncio
async def test_e2e_referral_reward_to_bell(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    ref_email, friend_email = "e2e_referrer@example.com", "e2e_friend@example.com"
    with TestClient(app) as client:
        _login(client, ref_email)
        _login(client, friend_email)
    ref_id, friend_id = await _uid(ref_email), await _uid(friend_email)
    await _set_user(ref_email, subscription_status="active", tier="pro",
                    stripe_customer_id="cus_e2e_ref", stripe_subscription_id="sub_e2e_ref")
    await _set_user(friend_email, subscription_status="active", tier="pro",
                    stripe_subscription_id="sub_e2e_friend")
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        code = await referral_service.get_or_create_code(db, ref_id)
        await referral_service.bind_referral(db, friend_id, code)

    # Friend's first paid invoice earns the referrer a free month + a bell notification.
    with TestClient(app) as client:
        _post_event(client, {"id": "evt_e2e_inv", "type": "invoice.paid",
                             "data": {"object": {"id": "in_e2e", "subscription": "sub_e2e_friend",
                                                 "customer": "cus_e2e_friend", "amount_paid": 14900,
                                                 "billing_reason": "subscription_cycle"}}})
        # Referrer opens the bell, sees the reward, marks it read.
        _login(client, ref_email)
        feed = client.get("/api/notifications").json()
        rewards = [n for n in feed["notifications"] if n["type"] == "referral_reward"]
        assert len(rewards) == 1
        # Reveal-gating still holds — a reward notification carries no journal outcome.
        assert "r_result" not in json.dumps(feed) and "\"status\": \"win\"" not in json.dumps(feed)
        client.post("/api/notifications/read", json={})  # ids omitted -> mark all read
        after = client.get("/api/notifications").json()
        assert after["unread_count"] == 0
        assert all(n.get("read_at") for n in after["notifications"])


# ── TC-V1-E2E-04 — coupon: admin create -> user validate + wrong-plan reject ───
def test_e2e_coupon_validate_and_reject():
    with TestClient(app) as client:
        _login(client, _ADMIN)
        client.post("/api/admin/coupons",
                    json={"code": "e2e50", "discount_type": "percent", "percent_off": 50,
                          "plan_restriction": "pro"})
        _login(client, "e2e_coupon_user@example.com")
        ok = client.post("/api/billing/coupon/validate", json={"code": "e2e50", "plan": "pro"})
        assert ok.json()["valid"] is True and ok.json()["percent_off"] == 50
        wrong = client.post("/api/billing/coupon/validate", json={"code": "e2e50", "plan": "basic"})
        assert wrong.json()["valid"] is False and wrong.json()["reason"] == "WRONG_PLAN"
        # A wrong-plan coupon is rejected at checkout, our-side, before any Stripe session.
        rej = client.post("/api/billing/checkout",
                          json={"plan": "basic", "promotion_code": "e2e50"})
        assert rej.status_code == 400
