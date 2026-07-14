"""Stage 4 — Coupons + Referral (Stripe-native). TC-S4-xx acceptance cases (ATP).

All Stripe calls mocked; zero network (AC8). No XP is written by any new path (AC8, asserted
in TC-S4-15). Webhook events are signed with the same t=,v1= scheme the SDK verifies (C2)."""
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import aiosqlite
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.core import coupon_service, referral_service, stripe_service
from backend.main import app

_WHSEC = "whsec_test_s4"
_ADMIN = "rodanis@gmail.com"  # ADMIN_BOOTSTRAP_EMAILS default → is_admin=1


@pytest.fixture(scope="module", autouse=True)
def _ensure_migrations():
    import asyncio

    from backend.migrations.run_migrations import apply_migrations

    asyncio.run(apply_migrations(cfg.DATABASE_URL))
    yield


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


async def _mk_user(email, **cols):
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        base = {"auth_provider": "email", "subscription_status": "none", "tier": "free",
                "created_at": _iso(_now())}
        base.update(cols)
        keys = ["email"] + list(base.keys())
        vals = [email] + list(base.values())
        cur = await db.execute(
            f"INSERT INTO users ({', '.join(keys)}) VALUES ({', '.join('?' for _ in keys)})",
            tuple(vals),
        )
        await db.commit()
        return cur.lastrowid


async def _conn():
    db = await aiosqlite.connect(cfg.DATABASE_URL)
    db.row_factory = aiosqlite.Row
    return db


def _sign(secret: str, body: bytes, ts: int | None = None) -> str:
    ts = ts or int(time.time())
    signed = f"{ts}".encode() + b"." + body
    v1 = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={v1}"


def _post_event(client: TestClient, event: dict, secret: str = _WHSEC):
    body = json.dumps(event).encode()
    return client.post("/api/billing/webhook",
                       headers={"Stripe-Signature": _sign(secret, body)}, content=body)


def _login(client: TestClient, email: str) -> None:
    r = client.post("/api/auth/magic-link", json={"email": email})
    token = parse_qs(urlparse(r.json()["dev_magic_link"]).query)["token"][0]
    client.get("/api/auth/verify", params={"token": token})


# ── TC-S4-01 — migration reshape: new schema present, legacy names gone ────────

@pytest.mark.asyncio
async def test_migration_reshape_schema():
    db = await _conn()
    try:
        async def cols(t):
            return {r[1] for r in await db.execute_fetchall(f"PRAGMA table_info({t})")}

        assert {"stripe_coupon_id", "stripe_promotion_code_id", "discount_type",
                "percent_off", "amount_off_agorot", "plan_restriction", "redeemed_count"} \
            <= await cols("coupons")
        assert {"coupon_id", "user_id", "promotion_code", "transaction_id"} <= await cols("coupon_redemptions")
        assert {"referrer_id", "referred_id", "status", "reward_type",
                "reward_amount_agorot"} <= await cols("referrals")
        assert {"referrer_id", "referral_id", "status", "applied_amount_agorot"} <= await cols("referral_credits")
        gone = await db.execute_fetchall(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='coupon_applications'")
        assert not gone
    finally:
        await db.close()


# ── TC-S4-02 — coupon param mapping: DEV fake ids + mirror row (percent+fixed) ─

@pytest.mark.asyncio
async def test_coupon_create_dev_percent_and_fixed():
    db = await _conn()
    try:
        admin_id = await _mk_user("cpn_dev_admin@example.com")
        pct = await coupon_service.create_coupon(
            db, admin_id=admin_id, code="save20", discount_type="percent", percent_off=20,
            max_redemptions=100, plan_restriction="pro", description="20 pct off pro")
        assert pct["percent_off"] == 20 and pct["amount_off_agorot"] is None
        assert pct["discount_type"] == "percent" and pct["duration"] == "once"
        assert pct["stripe_coupon_id"] == "coupon_dev_SAVE20"      # DEV fake, zero network
        assert pct["stripe_promotion_code_id"] == "promo_dev_SAVE20"
        assert pct["plan_restriction"] == "pro" and pct["active"] is True

        fixed = await coupon_service.create_coupon(
            db, admin_id=admin_id, code="ten-off", discount_type="fixed", amount_off_agorot=1000)
        assert fixed["amount_off_agorot"] == 1000 and fixed["percent_off"] is None
        assert fixed["discount_type"] == "fixed"

        with pytest.raises(HTTPException):   # duplicate code → 409
            await coupon_service.create_coupon(
                db, admin_id=admin_id, code="save20", discount_type="percent", percent_off=5)
        with pytest.raises(HTTPException):   # percent out of range
            await coupon_service.create_coupon(
                db, admin_id=admin_id, code="bad1", discount_type="percent", percent_off=200)
    finally:
        await db.close()


# ── TC-S4-03 — coupon create drives Stripe with the right params (mocked live) ─

@pytest.mark.asyncio
async def test_coupon_create_live_stripe_params(monkeypatch):
    captured = {}

    def _coupon_create(**kw):
        captured["coupon"] = kw
        return {"id": "co_live_1"}

    def _promo_create(**kw):
        captured["promo"] = kw
        return {"id": "promo_live_1"}

    fake = SimpleNamespace(
        Coupon=SimpleNamespace(create=_coupon_create),
        PromotionCode=SimpleNamespace(create=_promo_create),
    )
    monkeypatch.setattr(cfg, "FEATURE_STRIPE_LIVE", True)
    monkeypatch.setattr(cfg, "STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setattr(stripe_service, "_stripe", lambda: fake)

    db = await _conn()
    try:
        admin_id = await _mk_user("cpn_live_admin@example.com")
        exp = _iso(_now() + timedelta(days=30))
        await coupon_service.create_coupon(
            db, admin_id=admin_id, code="live-pct", discount_type="percent", percent_off=25,
            max_redemptions=5, expires_at=exp)
        assert captured["coupon"]["percent_off"] == 25
        assert captured["coupon"]["duration"] == "once"
        assert "currency" not in captured["coupon"]
        assert captured["promo"]["code"] == "LIVE-PCT"
        assert captured["promo"]["max_redemptions"] == 5
        assert isinstance(captured["promo"]["expires_at"], int)

        await coupon_service.create_coupon(
            db, admin_id=admin_id, code="live-fix", discount_type="fixed", amount_off_agorot=2500)
        assert captured["coupon"]["amount_off"] == 2500
        assert captured["coupon"]["currency"] == "ils"
    finally:
        await db.close()


# ── TC-S4-04 — plan restriction rejected our-side before session creation ──────

@pytest.mark.asyncio
async def test_plan_restriction_validation_and_checkout_reject():
    db = await _conn()
    try:
        admin_id = await _mk_user("cpn_restrict_admin@example.com")
        await coupon_service.create_coupon(
            db, admin_id=admin_id, code="proonly", discount_type="percent", percent_off=50,
            plan_restriction="pro")
        good = await coupon_service.validate_coupon_for_plan(db, "proonly", "pro")
        bad = await coupon_service.validate_coupon_for_plan(db, "proonly", "basic")
        assert good["valid"] is True
        assert bad["valid"] is False and bad["reason"] == "WRONG_PLAN"

        uid = await _mk_user("cpn_restrict_user@example.com")
        # Our-side rejection BEFORE the Checkout Session is created (AC2).
        with pytest.raises(HTTPException) as ei:
            await stripe_service.initiate_checkout(uid, "basic", db, promotion_code="proonly")
        assert ei.value.status_code == 400
        # No pending transaction was created for the rejected attempt.
        txs = await db.execute_fetchall(
            "SELECT COUNT(*) FROM payment_transactions WHERE user_id=?", (uid,))
        assert txs[0][0] == 0
    finally:
        await db.close()


# ── TC-S4-05 — admin coupon endpoints: create/list/deactivate + 403 non-admin ─

def test_admin_coupon_endpoints_and_403():
    with TestClient(app) as client:
        # Non-admin is forbidden.
        _login(client, "cpn_notadmin@example.com")
        r = client.post("/api/admin/coupons",
                        json={"code": "nope", "discount_type": "percent", "percent_off": 10})
        assert r.status_code == 403

        _login(client, _ADMIN)
        c = client.post("/api/admin/coupons",
                        json={"code": "adm10", "discount_type": "percent", "percent_off": 10,
                              "max_redemptions": 3})
        assert c.status_code == 200
        cid = c.json()["coupon"]["id"]
        lst = client.get("/api/admin/coupons").json()["coupons"]
        assert any(x["code"] == "ADM10" for x in lst)
        d = client.post(f"/api/admin/coupons/{cid}/deactivate")
        assert d.status_code == 200 and d.json()["coupon"]["active"] is False


# ── TC-S4-06 — redemption sync from checkout webhook: count + idempotent ───────

@pytest.mark.asyncio
async def test_redemption_sync_and_idempotent(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    db = await _conn()
    try:
        admin_id = await _mk_user("redeem_admin@example.com")
        await coupon_service.create_coupon(
            db, admin_id=admin_id, code="red15", discount_type="percent", percent_off=15)
        uid = await _mk_user("redeem_user@example.com")
        cur = await db.execute(
            "INSERT INTO payment_transactions (user_id, amount_ils, currency, status, kind, coupon_code, created_at) "
            "VALUES (?, 12665, 'ILS', 'pending', 'first', 'RED15', ?)", (uid, _iso(_now())))
        await db.commit()
        tx = cur.lastrowid
    finally:
        await db.close()

    def _evt(eid):
        return {"id": eid, "type": "checkout.session.completed",
                "data": {"object": {
                    "id": "cs_red", "client_reference_id": str(uid),
                    "customer": "cus_red", "subscription": "sub_red", "amount_total": 12665,
                    "total_details": {"amount_discount": 2235},
                    "metadata": {"user_id": str(uid), "plan": "pro", "transaction_id": str(tx)}}}}
    with TestClient(app) as client:
        _post_event(client, _evt("evt_red_1"))
        _post_event(client, _evt("evt_red_2"))  # different event id, same user/coupon

    db = await _conn()
    try:
        coupon = await coupon_service.get_coupon_by_code(db, "RED15")
        reds = await db.execute_fetchall(
            "SELECT COUNT(*) FROM coupon_redemptions WHERE coupon_id=?", (coupon["id"],))
        assert coupon["redeemed_count"] == 1     # counted once (idempotent per coupon,user)
        assert reds[0][0] == 1
    finally:
        await db.close()


# ── TC-S4-07 — max_redemptions + expiry enforced our-side ─────────────────────

@pytest.mark.asyncio
async def test_coupon_expiry_and_max_redemptions():
    db = await _conn()
    try:
        admin_id = await _mk_user("cpn_limits_admin@example.com")
        past = _iso(_now() - timedelta(days=1))
        await coupon_service.create_coupon(
            db, admin_id=admin_id, code="expired1", discount_type="percent", percent_off=10,
            expires_at=past)
        assert (await coupon_service.validate_coupon_for_plan(db, "expired1", "pro"))["reason"] == "EXPIRED"

        await coupon_service.create_coupon(
            db, admin_id=admin_id, code="maxed1", discount_type="percent", percent_off=10,
            max_redemptions=1)
        await db.execute("UPDATE coupons SET redeemed_count=1 WHERE code='MAXED1'")
        await db.commit()
        assert (await coupon_service.validate_coupon_for_plan(db, "maxed1", "pro"))["reason"] == "MAX_REDEEMED"

        await coupon_service.create_coupon(
            db, admin_id=admin_id, code="inactive1", discount_type="percent", percent_off=10)
        await db.execute("UPDATE coupons SET active=0 WHERE code='INACTIVE1'")
        await db.commit()
        assert (await coupon_service.validate_coupon_for_plan(db, "inactive1", "pro"))["reason"] == "INACTIVE"
        assert (await coupon_service.validate_coupon_for_plan(db, "ghost", "pro"))["reason"] == "NOT_FOUND"
    finally:
        await db.close()


# ── TC-S4-08 — referral bind: once, immutable, self-referral blocked ──────────

@pytest.mark.asyncio
async def test_referral_bind_immutable_and_self_block():
    db = await _conn()
    try:
        ref_id = await _mk_user("ref_binder@example.com")
        code = await referral_service.get_or_create_code(db, ref_id)
        assert code and len(code) == 8

        # Self-referral by id → blocked.
        assert await referral_service.bind_referral(db, ref_id, code) is False

        friend = await _mk_user("ref_friend@example.com")
        assert await referral_service.bind_referral(db, friend, code) is True
        # Immutable: a second bind is a no-op.
        other = await _mk_user("ref_other@example.com")
        other_code = await referral_service.get_or_create_code(db, other)
        assert await referral_service.bind_referral(db, friend, other_code) is False
        rows = await db.execute_fetchall(
            "SELECT referrer_id FROM referrals WHERE referred_id=?", (friend,))
        assert len(rows) == 1 and rows[0][0] == ref_id

        # Unknown code → no-op (does not break signup).
        assert await referral_service.bind_referral(db, other, "ZZZZZZZZ") is False
        # Empty / missing code → no-op.
        assert await referral_service.bind_referral(db, other, None) is False
    finally:
        await db.close()


# ── TC-S4-09 — referral binding via signup (/r/<code>) ────────────────────────

def test_referral_bind_at_signup():
    import asyncio
    with TestClient(app) as client:
        _login(client, "ref_referrer_signup@example.com")
    referrer_id = asyncio.run(_get_uid("ref_referrer_signup@example.com"))
    code = asyncio.run(_get_or_make_code(referrer_id))
    with TestClient(app) as client:
        r = client.post("/api/auth/magic-link",
                        json={"email": "ref_signup_friend@example.com", "referral_code": code})
        assert r.status_code == 200
    bound = asyncio.run(_referrer_of("ref_signup_friend@example.com"))
    assert bound == referrer_id


async def _get_uid(email):
    db = await _conn()
    try:
        return (await db.execute_fetchall(
            "SELECT internal_id FROM users WHERE email=?", (email,)))[0][0]
    finally:
        await db.close()


async def _get_or_make_code(uid):
    db = await _conn()
    try:
        return await referral_service.get_or_create_code(db, uid)
    finally:
        await db.close()


async def _referrer_of(email):
    db = await _conn()
    try:
        return (await db.execute_fetchall(
            "SELECT referred_by_user_id FROM users WHERE email=?", (email,)))[0][0]
    finally:
        await db.close()


# ── TC-S4-10 — reward: first amount>0 invoice → balance credit (referrer plan) ─

@pytest.mark.asyncio
async def test_reward_balance_credit_on_first_paid(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    db = await _conn()
    try:
        referrer = await _mk_user("rw_ref@example.com", subscription_status="active", tier="pro",
                                  stripe_customer_id="cus_rw", stripe_subscription_id="sub_rw_ref")
        code = await referral_service.get_or_create_code(db, referrer)
        friend = await _mk_user("rw_friend@example.com", subscription_status="active", tier="pro",
                                stripe_subscription_id="sub_rw_friend")
        await referral_service.bind_referral(db, friend, code)
    finally:
        await db.close()

    def _inv(eid, iid):
        return {"id": eid, "type": "invoice.paid",
                "data": {"object": {"id": iid, "subscription": "sub_rw_friend",
                                    "customer": "cus_friend", "amount_paid": 14900,
                                    "billing_reason": "subscription_cycle",
                                    "lines": {"data": [{"period": {"end": int((_now()+timedelta(days=30)).timestamp())}}]}}}}
    with TestClient(app) as client:
        _post_event(client, _inv("evt_rw_1", "in_rw_1"))
        _post_event(client, _inv("evt_rw_2", "in_rw_2"))  # out-of-order/dup cycle → still one reward

    db = await _conn()
    try:
        r = (await db.execute_fetchall(
            "SELECT status, reward_type, reward_amount_agorot, stripe_balance_transaction_id "
            "FROM referrals WHERE referred_id=?", (friend,)))[0]
        assert r[0] == "rewarded" and r[1] == "balance_credit"
        assert r[2] == 14900                            # one month of referrer's pro plan
        assert r[3].startswith("cbt_dev_")              # DEV balance credit, zero network
        events = await db.execute_fetchall(
            "SELECT COUNT(*) FROM subscription_events WHERE user_id=? AND event_type='referral_reward_earned'",
            (referrer,))
        assert events[0][0] == 1                        # exactly one reward (idempotent)
        bell = await db.execute_fetchall(
            "SELECT COUNT(*) FROM notifications WHERE user_id=? AND type='referral_reward'", (referrer,))
        assert bell[0][0] == 1
    finally:
        await db.close()


# ── TC-S4-11 — reward banked when referrer is trial/free ──────────────────────

@pytest.mark.asyncio
async def test_reward_banked_for_trial_referrer(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    db = await _conn()
    try:
        referrer = await _mk_user("bk_ref@example.com", subscription_status="trial", tier="pro")
        code = await referral_service.get_or_create_code(db, referrer)
        friend = await _mk_user("bk_friend@example.com", subscription_status="active", tier="basic",
                                stripe_subscription_id="sub_bk_friend")
        await referral_service.bind_referral(db, friend, code)
    finally:
        await db.close()

    inv = {"id": "evt_bk_1", "type": "invoice.paid",
           "data": {"object": {"id": "in_bk_1", "subscription": "sub_bk_friend",
                               "customer": "cus_bk", "amount_paid": 5900,
                               "billing_reason": "subscription_cycle"}}}
    with TestClient(app) as client:
        _post_event(client, inv)

    db = await _conn()
    try:
        r = (await db.execute_fetchall(
            "SELECT status, reward_type, reward_amount_agorot FROM referrals WHERE referred_id=?",
            (friend,)))[0]
        assert r[0] == "rewarded" and r[1] == "banked" and r[2] is None
        credits = await db.execute_fetchall(
            "SELECT status, applied_amount_agorot FROM referral_credits WHERE referrer_id=?", (referrer,))
        assert len(credits) == 1 and credits[0][0] == "banked"
    finally:
        await db.close()


# ── TC-S4-12 — 100%-coupon first month (amount 0) does NOT trigger the reward ──

@pytest.mark.asyncio
async def test_hundred_percent_first_month_no_reward_then_month2(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    db = await _conn()
    try:
        referrer = await _mk_user("hp_ref@example.com", subscription_status="active", tier="pro",
                                  stripe_customer_id="cus_hp", stripe_subscription_id="sub_hp_ref")
        code = await referral_service.get_or_create_code(db, referrer)
        friend = await _mk_user("hp_friend@example.com", subscription_status="active", tier="pro",
                                stripe_subscription_id="sub_hp_friend")
        await referral_service.bind_referral(db, friend, code)
    finally:
        await db.close()

    zero_inv = {"id": "evt_hp_0", "type": "invoice.paid",
                "data": {"object": {"id": "in_hp_0", "subscription": "sub_hp_friend",
                                    "customer": "cus_hpf", "amount_paid": 0,
                                    "billing_reason": "subscription_create"}}}
    paid_inv = {"id": "evt_hp_1", "type": "invoice.paid",
                "data": {"object": {"id": "in_hp_1", "subscription": "sub_hp_friend",
                                    "customer": "cus_hpf", "amount_paid": 14900,
                                    "billing_reason": "subscription_cycle"}}}
    with TestClient(app) as client:
        _post_event(client, zero_inv)
        db = await _conn()
        try:
            s = (await db.execute_fetchall(
                "SELECT status FROM referrals WHERE referred_id=?", (friend,)))[0][0]
            assert s == "bound"     # amount 0 → no reward yet
        finally:
            await db.close()
        _post_event(client, paid_inv)

    db = await _conn()
    try:
        s = (await db.execute_fetchall(
            "SELECT status, reward_type FROM referrals WHERE referred_id=?", (friend,)))[0]
        assert s[0] == "rewarded" and s[1] == "balance_credit"
    finally:
        await db.close()


# ── TC-S4-13 — banked credit auto-applies on referrer's first paid checkout ────

@pytest.mark.asyncio
async def test_banked_credit_applies_on_checkout_and_stacks(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    db = await _conn()
    try:
        referrer = await _mk_user("ap_ref@example.com", subscription_status="none", tier="free")
        # Two banked credits stack.
        for _ in range(2):
            await db.execute(
                "INSERT INTO referral_credits (referrer_id, status, created_at) VALUES (?, 'banked', ?)",
                (referrer, _iso(_now())))
        await db.commit()
        cur = await db.execute(
            "INSERT INTO payment_transactions (user_id, amount_ils, currency, status, kind, created_at) "
            "VALUES (?, 5900, 'ILS', 'pending', 'first', ?)", (referrer, _iso(_now())))
        await db.commit()
        tx = cur.lastrowid
    finally:
        await db.close()

    evt = {"id": "evt_ap_1", "type": "checkout.session.completed",
           "data": {"object": {"id": "cs_ap", "client_reference_id": str(referrer),
                               "customer": "cus_ap", "subscription": "sub_ap", "amount_total": 5900,
                               "metadata": {"user_id": str(referrer), "plan": "basic",
                                            "transaction_id": str(tx)}}}}
    with TestClient(app) as client:
        _post_event(client, evt)

    db = await _conn()
    try:
        credits = await db.execute_fetchall(
            "SELECT status, applied_amount_agorot FROM referral_credits WHERE referrer_id=?", (referrer,))
        assert len(credits) == 2
        assert all(c[0] == "applied" and c[1] == 5900 for c in credits)   # resolved to basic price
    finally:
        await db.close()


# ── TC-S4-14 — void: compensating tx for applied, plain void for banked ───────

@pytest.mark.asyncio
async def test_void_referral_compensating_and_banked():
    db = await _conn()
    try:
        # Applied balance credit → compensating tx reverses the amount.
        ref1 = await _mk_user("void_ref1@example.com", stripe_customer_id="cus_v1")
        friend1 = await _mk_user("void_friend1@example.com")
        await db.execute(
            "INSERT INTO referrals (referrer_id, referred_id, referral_code, status, reward_type, "
            "reward_amount_agorot, stripe_balance_transaction_id, created_at) "
            "VALUES (?, ?, 'CODE1', 'rewarded', 'balance_credit', 14900, 'cbt_dev_x', ?)",
            (ref1, friend1, _iso(_now())))
        await db.commit()
        rid1 = (await db.execute_fetchall(
            "SELECT id FROM referrals WHERE referred_id=?", (friend1,)))[0][0]
        res1 = await referral_service.void_referral(db, rid1, admin_id=1)
        assert res1["reversed_agorot"] == 14900
        assert (await db.execute_fetchall(
            "SELECT status FROM referrals WHERE id=?", (rid1,)))[0][0] == "void"

        # Banked (not applied) → plain void, nothing reversed.
        ref2 = await _mk_user("void_ref2@example.com")
        friend2 = await _mk_user("void_friend2@example.com")
        await db.execute(
            "INSERT INTO referrals (referrer_id, referred_id, referral_code, status, reward_type, created_at) "
            "VALUES (?, ?, 'CODE2', 'rewarded', 'banked', ?)", (ref2, friend2, _iso(_now())))
        await db.commit()
        rid2 = (await db.execute_fetchall(
            "SELECT id FROM referrals WHERE referred_id=?", (friend2,)))[0][0]
        await db.execute(
            "INSERT INTO referral_credits (referrer_id, referral_id, status, created_at) "
            "VALUES (?, ?, 'banked', ?)", (ref2, rid2, _iso(_now())))
        await db.commit()
        res2 = await referral_service.void_referral(db, rid2, admin_id=1)
        assert res2["reversed_agorot"] == 0
        assert (await db.execute_fetchall(
            "SELECT status FROM referral_credits WHERE referral_id=?", (rid2,)))[0][0] == "void"
        # Idempotent second void.
        assert (await referral_service.void_referral(db, rid2, admin_id=1)).get("already_void")
    finally:
        await db.close()


# ── TC-S4-15 — zero-amount invoice issues NO tax document (checkout + recurring) ─

@pytest.mark.asyncio
async def test_zero_amount_no_document(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    db = await _conn()
    try:
        uid = await _mk_user("zero_user@example.com")
        cur = await db.execute(
            "INSERT INTO payment_transactions (user_id, amount_ils, currency, status, kind, created_at) "
            "VALUES (?, 0, 'ILS', 'pending', 'first', ?)", (uid, _iso(_now())))
        await db.commit()
        tx = cur.lastrowid
    finally:
        await db.close()

    evt = {"id": "evt_zero_1", "type": "checkout.session.completed",
           "data": {"object": {"id": "cs_zero", "client_reference_id": str(uid),
                               "customer": "cus_zero", "subscription": "sub_zero", "amount_total": 0,
                               "metadata": {"user_id": str(uid), "plan": "pro", "transaction_id": str(tx)}}}}
    with TestClient(app) as client:
        _post_event(client, evt)

    db = await _conn()
    try:
        u = (await db.execute_fetchall(
            "SELECT subscription_status, tier FROM users WHERE internal_id=?", (uid,)))[0]
        assert u[0] == "active" and u[1] == "pro"        # activated despite 0 total
        docs = await db.execute_fetchall(
            "SELECT COUNT(*) FROM billing_documents WHERE user_id=?", (uid,))
        assert docs[0][0] == 0                            # NO tax document (D-S8)
        audit = await db.execute_fetchall(
            "SELECT COUNT(*) FROM subscription_events WHERE user_id=? "
            "AND event_type='zero_amount_invoice_no_document'", (uid,))
        assert audit[0][0] == 1                           # internal audit row instead
    finally:
        await db.close()


# ── TC-S4-16 — XP is never written by any Stage-4 path (AC8) ──────────────────

@pytest.mark.asyncio
async def test_zero_xp_writes_in_referral_flow(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    db = await _conn()
    try:
        before = (await db.execute_fetchall("SELECT COUNT(*) FROM xp_events"))[0][0]
        referrer = await _mk_user("xp_ref@example.com", subscription_status="active", tier="pro",
                                  stripe_customer_id="cus_xp", stripe_subscription_id="sub_xp_ref")
        code = await referral_service.get_or_create_code(db, referrer)
        friend = await _mk_user("xp_friend@example.com", subscription_status="active", tier="pro",
                                stripe_subscription_id="sub_xp_friend")
        await referral_service.bind_referral(db, friend, code)
    finally:
        await db.close()

    inv = {"id": "evt_xp_1", "type": "invoice.paid",
           "data": {"object": {"id": "in_xp_1", "subscription": "sub_xp_friend",
                               "customer": "cus_xpf", "amount_paid": 14900,
                               "billing_reason": "subscription_cycle"}}}
    with TestClient(app) as client:
        _post_event(client, inv)

    db = await _conn()
    try:
        after = (await db.execute_fetchall("SELECT COUNT(*) FROM xp_events"))[0][0]
        assert after == before                            # AC8: zero XP writes
    finally:
        await db.close()


# ── TC-S4-17 — /api/referral summary + /api/billing/coupon/validate ───────────

def test_referral_summary_and_coupon_validate_endpoints():
    with TestClient(app) as client:
        _login(client, "sum_user@example.com")
        s = client.get("/api/referral")
        assert s.status_code == 200
        body = s.json()
        assert len(body["code"]) == 8 and body["code"] in body["share_link"]
        assert body["referred_count"] == 0

        _login(client, _ADMIN)
        client.post("/api/admin/coupons",
                    json={"code": "val50", "discount_type": "percent", "percent_off": 50,
                          "plan_restriction": "pro"})
        _login(client, "val_user@example.com")
        ok = client.post("/api/billing/coupon/validate", json={"code": "val50", "plan": "pro"})
        assert ok.json()["valid"] is True and ok.json()["percent_off"] == 50
        wrong = client.post("/api/billing/coupon/validate", json={"code": "val50", "plan": "basic"})
        assert wrong.json()["valid"] is False and wrong.json()["reason"] == "WRONG_PLAN"


# ── TC-S4-18 — C2: webhook verify uses the SDK; bad signature is rejected ──────

@pytest.mark.asyncio
async def test_webhook_verify_sdk_parity(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    body = json.dumps({"id": "evt_x", "type": "ping"}).encode()
    good = stripe_service.verify_and_parse(body, _sign(_WHSEC, body), _WHSEC)
    assert good and good["id"] == "evt_x"
    assert stripe_service.verify_and_parse(body, "t=1,v1=deadbeef", _WHSEC) is None
    assert stripe_service.verify_and_parse(body, "", _WHSEC) is None
