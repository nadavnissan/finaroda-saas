"""Stage 3R — PSP migration Cardcom -> Stripe. State machine, Stripe webhook (signature +
event-id idempotency + status mapping), checkout, invoice.paid/failed/recovery,
subscription.deleted -> expired, cancel-at-period-end, MOCK invoice provider, DEV
zero-network, seed idempotency, and the no-Cardcom / no-sk_live grep guard.

TC-R3-xx acceptance cases (ATP). All Stripe calls mocked; zero network (AC8)."""
import hashlib
import hmac
import json
import time
from pathlib import Path
from types import SimpleNamespace

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.core import billing_state, invoice_provider, stripe_service
from backend.core.email import format_agorot_ils
from backend.main import app
from backend.scripts.seed_stripe_prices import seed_prices

from datetime import datetime, timedelta, timezone

_WHSEC = "whsec_test_3r"


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


async def _mk_user(db, email, **cols):
    base = {"auth_provider": "email", "subscription_status": "none", "tier": "free",
            "created_at": _iso(_now())}
    base.update(cols)
    keys = ["email"] + list(base.keys())
    vals = [email] + list(base.values())
    placeholders = ", ".join("?" for _ in keys)
    cur = await db.execute(
        f"INSERT INTO users ({', '.join(keys)}) VALUES ({placeholders})", tuple(vals)
    )
    await db.commit()
    return cur.lastrowid


async def _mk_pending_tx(db, user_id, amount=14900):
    cur = await db.execute(
        """INSERT INTO payment_transactions (user_id, amount_ils, currency, status, kind, created_at)
           VALUES (?, ?, 'ILS', 'pending', 'first', ?)""",
        (user_id, amount, _iso(_now())),
    )
    await db.commit()
    return cur.lastrowid


def _sign(secret: str, body: bytes, ts: int | None = None) -> str:
    ts = ts or int(time.time())
    signed = f"{ts}".encode() + b"." + body
    v1 = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={v1}"


def _post_event(client: TestClient, event: dict, secret: str = _WHSEC):
    body = json.dumps(event).encode()
    sig = _sign(secret, body)
    return client.post("/api/billing/webhook", headers={"Stripe-Signature": sig}, content=body)


# ── TC-R3-01 — state machine matrix (with the Stage-3R active->expired edge) ──

def test_state_machine_legal_transitions():
    S = billing_state
    legal = [
        (S.NONE, S.TRIAL), (S.NONE, S.ACTIVE),
        (S.TRIAL, S.ACTIVE), (S.TRIAL, S.CANCELLED), (S.TRIAL, S.NONE),
        (S.ACTIVE, S.ACTIVE), (S.ACTIVE, S.PAST_DUE), (S.ACTIVE, S.CANCELLED),
        (S.ACTIVE, S.EXPIRED),                                    # NEW in Stage 3R
        (S.PAST_DUE, S.ACTIVE), (S.PAST_DUE, S.EXPIRED), (S.PAST_DUE, S.CANCELLED),
        (S.CANCELLED, S.NONE), (S.CANCELLED, S.ACTIVE),
        (S.EXPIRED, S.ACTIVE), (S.EXPIRED, S.TRIAL), (S.EXPIRED, S.NONE),
    ]
    for frm, to in legal:
        assert billing_state.can_transition(frm, to), f"{frm}->{to} should be legal"


def test_state_machine_illegal_transitions_raise():
    S = billing_state
    illegal = [
        (S.NONE, S.PAST_DUE), (S.NONE, S.EXPIRED), (S.NONE, S.CANCELLED),
        (S.TRIAL, S.PAST_DUE), (S.TRIAL, S.EXPIRED),
        (S.ACTIVE, S.TRIAL), (S.ACTIVE, S.NONE),
        (S.PAST_DUE, S.TRIAL), (S.PAST_DUE, S.NONE),
        (S.EXPIRED, S.PAST_DUE), (S.EXPIRED, S.CANCELLED),
        (S.CANCELLED, S.PAST_DUE), (S.CANCELLED, S.EXPIRED), (S.CANCELLED, S.TRIAL),
    ]
    for frm, to in illegal:
        assert not billing_state.can_transition(frm, to), f"{frm}->{to} should be illegal"
        with pytest.raises(billing_state.IllegalTransition):
            billing_state.assert_transition(frm, to)


def test_effective_tier_derives_from_state():
    S = billing_state
    assert billing_state.effective_tier(S.ACTIVE, "pro") == "pro"
    assert billing_state.effective_tier(S.TRIAL, "pro") == "pro"
    assert billing_state.effective_tier(S.PAST_DUE, "basic") == "basic"
    assert billing_state.effective_tier(S.CANCELLED, "pro") == "pro"
    assert billing_state.effective_tier(S.EXPIRED, "pro") == "free"
    assert billing_state.effective_tier(S.NONE, "pro") == "free"


# ── TC-R3-02 — agorot arithmetic (money integrity, D-B10) ────────────────────

def test_agorot_formatting_is_exact():
    assert format_agorot_ils(5900) == "59.00 ILS"
    assert format_agorot_ils(14900) == "149.00 ILS"
    assert format_agorot_ils(99) == "0.99 ILS"
    assert format_agorot_ils(0) == "0.00 ILS"


@pytest.mark.asyncio
async def test_plan_prices_are_agorot_ints():
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        basic = await stripe_service.get_plan_price_agorot(db, "basic")
        pro = await stripe_service.get_plan_price_agorot(db, "pro")
    assert isinstance(basic, int) and isinstance(pro, int)
    assert basic == 5900 and pro == 14900


# ── TC-R3-03 — invoice provider MOCK: offline, idempotent, tax doc type ──────

@pytest.mark.asyncio
async def test_mock_invoice_provider_offline_and_idempotent():
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "doc1@example.com")
        tx = await _mk_pending_tx(db, uid)
        doc1 = await invoice_provider.issue_document(db, uid, tx, 14900)
        doc2 = await invoice_provider.issue_document(db, uid, tx, 14900)  # idempotent
    assert doc1["id"] == doc2["id"]
    assert doc1["document_type"] == "tax_invoice_receipt"          # LTD / VAT registered
    assert doc1["provider_document_id"].startswith("MOCK-")        # offline, zero network
    assert doc1["amount_agorot"] == 14900


# ── TC-R3-04 — webhook signature: valid activates, tampered is ignored ───────

@pytest.mark.asyncio
async def test_webhook_valid_signature_activates_and_idempotent(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "wh_ok@example.com")
        tx = await _mk_pending_tx(db, uid)

    event = {
        "id": "evt_checkout_ok",
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_ok", "client_reference_id": str(uid),
            "customer": "cus_ok", "subscription": "sub_ok", "amount_total": 14900,
            "metadata": {"user_id": str(uid), "plan": "pro", "transaction_id": str(tx)},
        }},
    }
    with TestClient(app) as client:
        r1 = _post_event(client, event)
        r2 = _post_event(client, event)  # duplicate event id
    assert r1.status_code == 200 and r2.status_code == 200

    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        u = (await db.execute_fetchall(
            """SELECT subscription_status, tier, stripe_customer_id, stripe_subscription_id,
                      next_billing_at FROM users WHERE internal_id=?""", (uid,)))[0]
        docs = await db.execute_fetchall("SELECT id FROM billing_documents WHERE user_id=?", (uid,))
        txs = await db.execute_fetchall(
            "SELECT status FROM payment_transactions WHERE id=?", (tx,))
    assert u["subscription_status"] == "active"
    assert u["tier"] == "pro"
    assert u["stripe_customer_id"] == "cus_ok"
    assert u["stripe_subscription_id"] == "sub_ok"
    assert u["next_billing_at"] is not None
    assert len(docs) == 1                       # duplicate event issues no second doc
    assert txs[0]["status"] == "success"


@pytest.mark.asyncio
async def test_webhook_tampered_signature_never_activates(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "wh_bad@example.com")
        tx = await _mk_pending_tx(db, uid)
    event = {
        "id": "evt_bad", "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_bad", "client_reference_id": str(uid),
                            "metadata": {"user_id": str(uid), "plan": "pro",
                                         "transaction_id": str(tx)}}},
    }
    body = json.dumps(event).encode()
    with TestClient(app) as client:
        # Tampered signature (redirect alone / forged callback): must NOT activate (AC2).
        r = client.post("/api/billing/webhook",
                        headers={"Stripe-Signature": "t=1,v1=deadbeef"}, content=body)
    assert r.status_code == 200
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        u = (await db.execute_fetchall(
            "SELECT subscription_status, tier FROM users WHERE internal_id=?", (uid,)))[0]
    assert u["subscription_status"] == "none"
    assert u["tier"] == "free"


# ── TC-R3-05 — invoice.paid recurring: doc + idempotent by event AND invoice ─

@pytest.mark.asyncio
async def test_invoice_paid_recurring_issues_doc_idempotent(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    period_end = int((_now() + timedelta(days=30)).timestamp())
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "recur@example.com", subscription_status="active", tier="pro",
                             stripe_subscription_id="sub_recur")

    def _inv(event_id):
        return {
            "id": event_id, "type": "invoice.paid",
            "data": {"object": {
                "id": "in_recur_1", "subscription": "sub_recur", "customer": "cus_recur",
                "amount_paid": 14900, "billing_reason": "subscription_cycle",
                "lines": {"data": [{"period": {"end": period_end}}]},
            }},
        }
    with TestClient(app) as client:
        _post_event(client, _inv("evt_inv_1"))
        _post_event(client, _inv("evt_inv_2"))  # new event id, SAME invoice id -> no dup

    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        docs = await db.execute_fetchall("SELECT id FROM billing_documents WHERE user_id=?", (uid,))
        txs = await db.execute_fetchall(
            "SELECT id FROM payment_transactions WHERE user_id=? AND kind='recurring'", (uid,))
        u = (await db.execute_fetchall(
            "SELECT subscription_status, next_billing_at FROM users WHERE internal_id=?", (uid,)))[0]
    assert len(txs) == 1            # one recurring charge (idempotent by invoice id)
    assert len(docs) == 1           # one tax document
    assert u["subscription_status"] == "active"
    assert u["next_billing_at"] is not None


# ── TC-R3-06 — payment_failed -> past_due -> recovery -> active (AC4) ─────────

@pytest.mark.asyncio
async def test_payment_failed_then_recovery(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "fail@example.com", subscription_status="active", tier="pro",
                             stripe_subscription_id="sub_fail")

    failed = {
        "id": "evt_fail_1", "type": "invoice.payment_failed",
        "data": {"object": {"id": "in_fail", "subscription": "sub_fail", "customer": "cus_fail",
                            "attempt_count": 1,
                            "next_payment_attempt": int((_now() + timedelta(days=3)).timestamp())}},
    }
    recover = {
        "id": "evt_recover_1", "type": "invoice.paid",
        "data": {"object": {"id": "in_recover", "subscription": "sub_fail", "customer": "cus_fail",
                            "amount_paid": 14900, "billing_reason": "subscription_cycle",
                            "lines": {"data": [{"period": {"end": int((_now()+timedelta(days=30)).timestamp())}}]}}},
    }
    with TestClient(app) as client:
        _post_event(client, failed)
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            db.row_factory = aiosqlite.Row
            u = (await db.execute_fetchall(
                "SELECT subscription_status, tier FROM users WHERE internal_id=?", (uid,)))[0]
        assert u["subscription_status"] == "past_due"     # dunning grace (access kept)
        assert u["tier"] == "pro"

        _post_event(client, recover)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        u = (await db.execute_fetchall(
            "SELECT subscription_status, billing_failure_count FROM users WHERE internal_id=?", (uid,)))[0]
        bell = await db.execute_fetchall(
            "SELECT type FROM notifications WHERE user_id=? AND type='billing_past_due'", (uid,))
    assert u["subscription_status"] == "active"           # recovered
    assert len(bell) >= 1                                 # past-due banner/bell fired


# ── TC-R3-07 — subscription.deleted: involuntary -> expired -> Free (AC4) ─────

@pytest.mark.asyncio
async def test_subscription_deleted_involuntary_expires_from_active(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "del_active@example.com", subscription_status="active", tier="pro",
                             stripe_subscription_id="sub_del_a")
    event = {
        "id": "evt_del_a", "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_del_a", "customer": "cus_del_a"}},
    }
    with TestClient(app) as client:
        _post_event(client, event)  # exercises the NEW active->expired edge
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        u = (await db.execute_fetchall(
            "SELECT subscription_status, tier, stripe_subscription_id FROM users WHERE internal_id=?", (uid,)))[0]
    assert u["subscription_status"] == "expired"
    assert u["tier"] == "free"
    assert u["stripe_subscription_id"] is None


# ── TC-R3-08 — cancel at period end + deleted-while-cancelled -> Free (AC5) ───

@pytest.mark.asyncio
async def test_cancel_at_period_end_then_dropped(monkeypatch):
    monkeypatch.setattr(cfg, "STRIPE_WEBHOOK_SECRET", _WHSEC)
    future = int((_now() + timedelta(days=12)).timestamp())
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "cancel@example.com", subscription_status="active", tier="pro",
                             stripe_subscription_id="sub_cancel",
                             next_billing_at=_iso(_now() + timedelta(days=12)))
    updated = {
        "id": "evt_cancel_upd", "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_cancel", "customer": "cus_cancel", "status": "active",
                            "cancel_at_period_end": True, "current_period_end": future}},
    }
    deleted = {
        "id": "evt_cancel_del", "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_cancel", "customer": "cus_cancel"}},
    }
    with TestClient(app) as client:
        _post_event(client, updated)
        async with aiosqlite.connect(cfg.DATABASE_URL) as db:
            db.row_factory = aiosqlite.Row
            u = (await db.execute_fetchall(
                """SELECT subscription_status, tier, subscription_cancelled_pending_at
                   FROM users WHERE internal_id=?""", (uid,)))[0]
        assert u["subscription_status"] == "cancelled"   # access retained
        assert u["tier"] == "pro"
        assert u["subscription_cancelled_pending_at"] is not None

        _post_event(client, deleted)  # period end reached -> voluntary drop to Free
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        u = (await db.execute_fetchall(
            "SELECT subscription_status, tier FROM users WHERE internal_id=?", (uid,)))[0]
    assert u["subscription_status"] == "none"
    assert u["tier"] == "free"


@pytest.mark.asyncio
async def test_cancel_subscription_dev_mode_and_double_cancel_safe():
    """Our cancel endpoint (DEV mode: no Stripe call) sets cancelled + access-until; a
    second cancel is idempotent."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "cancel_dev@example.com", subscription_status="active", tier="pro",
                             next_billing_at=_iso(_now() + timedelta(days=8)),
                             stripe_subscription_id="sub_cd")
        resp = await stripe_service.cancel_subscription(uid, db)
        assert resp.access_until is not None
        u = (await db.execute_fetchall(
            "SELECT subscription_status FROM users WHERE internal_id=?", (uid,)))[0]
        assert u["subscription_status"] == "cancelled"
        resp2 = await stripe_service.cancel_subscription(uid, db)
    assert "already" in resp2.message.lower()


# ── TC-R3-09 — DEV fallback checkout is zero-network ─────────────────────────

@pytest.mark.asyncio
async def test_checkout_dev_fallback_zero_network():
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "devco@example.com")
        resp = await stripe_service.initiate_checkout(uid, "pro", db)
    assert resp.dev_mode is True
    assert "session_id=cs_dev_" in resp.redirect_url
    assert resp.transaction_id > 0


# ── TC-R3-10 — seed script is idempotent (mocked Stripe, zero network) ───────

@pytest.mark.asyncio
async def test_seed_stripe_prices_idempotent(monkeypatch):
    monkeypatch.setattr(cfg, "FEATURE_STRIPE_LIVE", True)
    monkeypatch.setattr(cfg, "STRIPE_SECRET_KEY", "sk_test_dummy")
    created = {"products": 0, "prices": 0}

    def _prod_create(**kw):
        created["products"] += 1
        return {"id": f"prod_{created['products']}"}

    def _price_create(**kw):
        created["prices"] += 1
        return {"id": f"price_{kw['metadata']['plan']}"}

    fake = SimpleNamespace(
        Product=SimpleNamespace(create=_prod_create),
        Price=SimpleNamespace(create=_price_create),
    )
    monkeypatch.setattr(stripe_service, "_stripe", lambda: fake)

    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        r1 = await seed_prices(db)
        r2 = await seed_prices(db)  # idempotent: nothing new created
    assert r1["basic"]["created"] is True and r1["pro"]["created"] is True
    assert r2["basic"]["created"] is False and r2["pro"]["created"] is False
    assert created["prices"] == 2       # exactly one Price per plan, ever


# ── TC-R3-11 — billing cron endpoint: auth + shape (no charge step) ──────────

def test_billing_cron_requires_secret_and_has_no_charge_step():
    with TestClient(app) as client:
        assert client.post("/api/cron/billing").status_code in (403, 422)
        assert client.post("/api/cron/billing", headers={"X-Cron-Secret": "wrong"}).status_code == 403
        ok = client.post("/api/cron/billing", headers={"X-Cron-Secret": cfg.CRON_SECRET})
    assert ok.status_code == 200
    body = ok.json()
    assert "expire_trials" in body and "cancel_drop" in body
    assert "renewal" not in body      # homegrown recurring/dunning deleted (Stripe owns it)


# ── TC-R3-12 — no Cardcom in live code; no sk_live anywhere (AC7) ────────────

def test_no_cardcom_in_live_code_and_no_live_key_pattern():
    backend_dir = Path(__file__).resolve().parents[1]
    frontend_src = backend_dir.parent / "frontend" / "src"
    live_dirs = [backend_dir / d for d in ("core", "api", "models", "app", "scripts")]
    live_dirs.append(frontend_src)
    live_dirs.append(backend_dir / "config.py")

    exts = {".py", ".ts", ".tsx", ".js"}
    live_key = "sk_" + "live"   # split so this guard file never matches itself
    cardcom_hits: list[str] = []
    key_hits: list[str] = []
    for target in live_dirs:
        files = [target] if target.is_file() else [
            p for p in target.rglob("*") if p.suffix.lower() in exts
        ]
        for p in files:
            text = p.read_text(encoding="utf-8", errors="ignore")
            if "cardcom" in text.lower():
                cardcom_hits.append(str(p))
            if live_key in text:
                key_hits.append(str(p))
    assert not cardcom_hits, f"Cardcom references remain in live code: {cardcom_hits}"
    assert not key_hits, f"Live secret-key pattern found in code: {key_hits}"
