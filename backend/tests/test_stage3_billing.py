"""Stage 3 — live billing (Cardcom). State machine, webhook, cron/dunning, cancel,
documents, agorot, forward-compat columns. All Cardcom calls mocked; zero network (AC8).

TC-B3-xx acceptance cases (ATP)."""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite
import pytest
from fastapi.testclient import TestClient

import backend.config as cfg
from backend.core import billing_state, cardcom_invoice, cardcom_service
from backend.core.email import format_agorot_ils
from backend.main import app


@pytest.fixture(scope="module", autouse=True)
def _ensure_migrations():
    """Apply migrations before the async DB tests (which may run before any TestClient
    triggers app startup). Mirrors the schema the app builds on boot."""
    import asyncio

    from backend.migrations.run_migrations import apply_migrations

    asyncio.run(apply_migrations(cfg.DATABASE_URL))
    yield


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


async def _mk_user(db, email, **cols):
    """Insert a user with sensible defaults; return internal_id."""
    base = {
        "auth_provider": "email",
        "subscription_status": "none",
        "tier": "free",
        "created_at": _iso(_now()),
    }
    base.update(cols)
    keys = ["email"] + list(base.keys())
    vals = [email] + list(base.values())
    placeholders = ", ".join("?" for _ in keys)
    cur = await db.execute(
        f"INSERT INTO users ({', '.join(keys)}) VALUES ({placeholders})", tuple(vals)
    )
    await db.commit()
    return cur.lastrowid


# ── TC-B3-01 — state machine matrix (legal + illegal) ────────────────────────

def test_state_machine_legal_transitions():
    S = billing_state
    legal = [
        (S.NONE, S.TRIAL), (S.NONE, S.ACTIVE),
        (S.TRIAL, S.ACTIVE), (S.TRIAL, S.CANCELLED), (S.TRIAL, S.NONE),
        (S.ACTIVE, S.ACTIVE), (S.ACTIVE, S.PAST_DUE), (S.ACTIVE, S.CANCELLED),
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
        (S.ACTIVE, S.TRIAL), (S.ACTIVE, S.EXPIRED), (S.ACTIVE, S.NONE),
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
    # Entitled states keep the paid tier.
    assert billing_state.effective_tier(S.ACTIVE, "pro") == "pro"
    assert billing_state.effective_tier(S.TRIAL, "pro") == "pro"
    assert billing_state.effective_tier(S.PAST_DUE, "basic") == "basic"   # grace during dunning
    assert billing_state.effective_tier(S.CANCELLED, "pro") == "pro"       # until period end
    # Non-entitled states collapse to Free regardless of the stored plan.
    assert billing_state.effective_tier(S.EXPIRED, "pro") == "free"
    assert billing_state.effective_tier(S.NONE, "pro") == "free"


@pytest.mark.asyncio
async def test_apply_transition_rejects_illegal_in_db():
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "sm_illegal@example.com", subscription_status="none", tier="free")
        # none -> past_due is illegal and must not mutate the row.
        with pytest.raises(billing_state.IllegalTransition):
            await cardcom_service_apply(db, uid, billing_state.PAST_DUE, "subscription_past_due")
        rows = await db.execute_fetchall(
            "SELECT subscription_status FROM users WHERE internal_id=?", (uid,)
        )
    assert rows[0]["subscription_status"] == "none"


async def cardcom_service_apply(db, uid, to, ev):
    """Thin wrapper so the illegal-transition test reads clearly."""
    return await billing_state.apply_transition(db, uid, to, ev)


# ── TC-B3-02 — agorot arithmetic (money integrity, D-B10/AC7) ────────────────

def test_agorot_formatting_is_exact():
    assert format_agorot_ils(5900) == "59.00 ILS"
    assert format_agorot_ils(14900) == "149.00 ILS"
    assert format_agorot_ils(99) == "0.99 ILS"
    assert format_agorot_ils(100) == "1.00 ILS"
    assert format_agorot_ils(0) == "0.00 ILS"


@pytest.mark.asyncio
async def test_plan_prices_are_agorot_ints():
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        basic = await cardcom_service.get_plan_price_agorot(db, "basic")
        pro = await cardcom_service.get_plan_price_agorot(db, "pro")
    assert isinstance(basic, int) and isinstance(pro, int)
    assert basic == 5900 and pro == 14900


# ── TC-B3-03 — billing documents (D-B3) + forward-compat columns (D-B7) ──────

@pytest.mark.asyncio
async def test_issue_document_is_mock_offline_and_idempotent():
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "doc1@example.com")
        cur = await db.execute(
            """INSERT INTO payment_transactions (user_id, amount_ils, currency, status, kind, created_at)
               VALUES (?, 14900, 'ILS', 'success', 'first', ?)""",
            (uid, _iso(_now())),
        )
        await db.commit()
        tx_id = cur.lastrowid

        doc1 = await cardcom_invoice.issue_document(db, uid, tx_id, 14900)
        doc2 = await cardcom_invoice.issue_document(db, uid, tx_id, 14900)  # idempotent
    assert doc1["id"] == doc2["id"]                      # one document per charge
    assert doc1["document_type"] == "receipt"            # config default
    assert doc1["cardcom_document_id"].startswith("MOCK-")   # offline mock, zero network
    assert doc1["amount_agorot"] == 14900


@pytest.mark.asyncio
async def test_charges_and_documents_carry_inert_coupon_referral_columns():
    """D-B7: coupon_code + referral_source exist on charges and documents but are inert
    (no discount math in Stage 3). A charge with them still records the full price."""
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        tx_cols = [r["name"] for r in await db.execute_fetchall("PRAGMA table_info(payment_transactions)")]
        doc_cols = [r["name"] for r in await db.execute_fetchall("PRAGMA table_info(billing_documents)")]
        assert "coupon_code" in tx_cols and "referral_source" in tx_cols
        assert "coupon_code" in doc_cols and "referral_source" in doc_cols

        uid = await _mk_user(db, "coupon@example.com")
        cur = await db.execute(
            """INSERT INTO payment_transactions
               (user_id, amount_ils, currency, status, kind, coupon_code, referral_source, created_at)
               VALUES (?, 14900, 'ILS', 'success', 'first', 'WELCOME10', 'friend', ?)""",
            (uid, _iso(_now())),
        )
        await db.commit()
        tx_id = cur.lastrowid
        doc = await cardcom_invoice.issue_document(db, uid, tx_id, 14900)
        drow = await db.execute_fetchall(
            "SELECT coupon_code, referral_source, amount_agorot FROM billing_documents WHERE id=?",
            (doc["id"],),
        )
    # Carried onto the document, but the amount is untouched (inert).
    assert drow[0]["coupon_code"] == "WELCOME10"
    assert drow[0]["referral_source"] == "friend"
    assert drow[0]["amount_agorot"] == 14900


# ── TC-B3-04 — webhook: signature + idempotency (D-B8/AC6) ───────────────────

def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_webhook_activates_issues_doc_and_is_idempotent(monkeypatch):
    monkeypatch.setattr(cfg, "CARDCOM_WEBHOOK_SECRET", "whsec_test")
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "wh@example.com", subscription_status="none", tier="free")
        cur = await db.execute(
            """INSERT INTO payment_transactions
               (user_id, cardcom_tx_id, amount_ils, currency, status, kind, cardcom_response_json, created_at)
               VALUES (?, 'deal_wh_1', 14900, 'ILS', 'pending', 'first', ?, ?)""",
            (uid, json.dumps({"tier_target": "pro"}), _iso(_now())),
        )
        await db.commit()

    body = json.dumps({"LowProfileId": "deal_wh_1", "ResponseCode": 0, "Token": "tok_wh"}).encode()
    sig = _sign("whsec_test", body)
    with TestClient(app) as client:
        r1 = client.post("/api/cardcom/webhook", headers={"X-Cardcom-Signature": sig}, content=body)
        r2 = client.post("/api/cardcom/webhook", headers={"X-Cardcom-Signature": sig}, content=body)  # dup
    assert r1.status_code == 200 and r2.status_code == 200

    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        urow = (await db.execute_fetchall(
            "SELECT subscription_status, tier, cardcom_token, next_billing_at FROM users WHERE internal_id=?",
            (uid,),
        ))[0]
        docs = await db.execute_fetchall(
            "SELECT id FROM billing_documents WHERE user_id=?", (uid,)
        )
        txs = await db.execute_fetchall(
            "SELECT status FROM payment_transactions WHERE user_id=? AND cardcom_tx_id='deal_wh_1'", (uid,)
        )
    assert urow["subscription_status"] == "active"       # AC1: activated server-side
    assert urow["tier"] == "pro"
    assert urow["cardcom_token"] == "tok_wh"
    assert urow["next_billing_at"] is not None
    assert len(docs) == 1                                 # AC6: duplicate processed once
    assert txs[0]["status"] == "success"


@pytest.mark.asyncio
async def test_webhook_bad_signature_never_activates(monkeypatch):
    monkeypatch.setattr(cfg, "CARDCOM_WEBHOOK_SECRET", "whsec_test")
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(db, "wh_bad@example.com", subscription_status="none", tier="free")
        await db.execute(
            """INSERT INTO payment_transactions
               (user_id, cardcom_tx_id, amount_ils, currency, status, kind, cardcom_response_json, created_at)
               VALUES (?, 'deal_wh_bad', 14900, 'ILS', 'pending', 'first', ?, ?)""",
            (uid, json.dumps({"tier_target": "pro"}), _iso(_now())),
        )
        await db.commit()

    body = json.dumps({"LowProfileId": "deal_wh_bad", "ResponseCode": 0, "Token": "x"}).encode()
    with TestClient(app) as client:
        # Tampered signature + client redirect alone: must NOT activate (D-B8/AC6).
        r = client.post("/api/cardcom/webhook", headers={"X-Cardcom-Signature": "deadbeef"}, content=body)
    assert r.status_code == 200
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        urow = (await db.execute_fetchall(
            "SELECT subscription_status, tier FROM users WHERE internal_id=?", (uid,)))[0]
    assert urow["subscription_status"] == "none"        # AC2/AC6: no partial activation
    assert urow["tier"] == "free"


# ── TC-B3-05 — recurring cron: success + idempotent double-run (AC3) ─────────

def _fake_charge_ok():
    async def _charge(db, user_id, token, tier, amount):
        cur = await db.execute(
            """INSERT INTO payment_transactions (user_id, amount_ils, currency, status, kind, created_at)
               VALUES (?, ?, 'ILS', 'success', 'recurring', ?)""",
            (user_id, amount, _iso(_now())),
        )
        await db.commit()
        return {"success": True, "transaction_id": cur.lastrowid}
    return _charge


def _fake_charge_fail():
    async def _charge(db, user_id, token, tier, amount):
        return {"success": False, "error": "declined"}
    return _charge


@pytest.mark.asyncio
async def test_recurring_charges_once_then_zero_on_double_run(monkeypatch):
    monkeypatch.setattr(cfg, "FEATURE_CARDCOM_LIVE", True)
    monkeypatch.setattr(cardcom_service, "charge_recurring", _fake_charge_ok())
    past = _iso(_now() - timedelta(minutes=1))
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(
            db, "recur@example.com", subscription_status="active", tier="pro",
            next_billing_at=past, cardcom_token="tok_r", billing_failure_count=0,
        )
        r1 = await cardcom_service.run_renewal_batch(db)
        r2 = await cardcom_service.run_renewal_batch(db)  # idempotent
        docs = await db.execute_fetchall("SELECT id FROM billing_documents WHERE user_id=?", (uid,))
        urow = (await db.execute_fetchall(
            "SELECT subscription_status, next_billing_at FROM users WHERE internal_id=?", (uid,)))[0]
    assert r1["charged_ok"] == 1
    assert r2["charged_ok"] == 0                          # AC3: second run charges zero
    assert len(docs) == 1                                 # one document per successful charge
    assert urow["subscription_status"] == "active"


# ── TC-B3-06 — dunning ladder: past_due -> retry -> expired -> Free (AC4) ─────

@pytest.mark.asyncio
async def test_dunning_ladder_expires_after_two_retries(monkeypatch):
    monkeypatch.setattr(cfg, "FEATURE_CARDCOM_LIVE", True)
    monkeypatch.setattr(cardcom_service, "charge_recurring", _fake_charge_fail())
    past = _iso(_now() - timedelta(minutes=1))
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(
            db, "dun@example.com", subscription_status="active", tier="pro",
            next_billing_at=past, cardcom_token="tok_d", billing_failure_count=0,
        )
        # Failure 1: active -> past_due, retry scheduled ~ +24h.
        await cardcom_service.run_renewal_batch(db)
        u = (await db.execute_fetchall(
            "SELECT subscription_status, tier, billing_failure_count, dunning_next_retry_at FROM users WHERE internal_id=?",
            (uid,)))[0]
        assert u["subscription_status"] == "past_due"
        assert u["tier"] == "pro"                         # grace: access retained
        assert u["billing_failure_count"] == 1
        assert u["dunning_next_retry_at"] is not None

        # Force retry due -> failure 2 (still past_due, count 2).
        await db.execute("UPDATE users SET dunning_next_retry_at=? WHERE internal_id=?", (past, uid))
        await db.commit()
        await cardcom_service.run_renewal_batch(db)
        u = (await db.execute_fetchall(
            "SELECT subscription_status, billing_failure_count FROM users WHERE internal_id=?", (uid,)))[0]
        assert u["subscription_status"] == "past_due"
        assert u["billing_failure_count"] == 2

        # Force retry due -> failure 3 -> expired -> Free (AC4).
        await db.execute("UPDATE users SET dunning_next_retry_at=? WHERE internal_id=?", (past, uid))
        await db.commit()
        res = await cardcom_service.run_renewal_batch(db)
        u = (await db.execute_fetchall(
            "SELECT subscription_status, tier, next_billing_at FROM users WHERE internal_id=?", (uid,)))[0]
    assert u["subscription_status"] == "expired"
    assert u["tier"] == "free"                            # entitlements drop to Free
    assert u["next_billing_at"] is None
    assert res["newly_expired"] == 1


@pytest.mark.asyncio
async def test_dunning_recovery_past_due_to_active(monkeypatch):
    monkeypatch.setattr(cfg, "FEATURE_CARDCOM_LIVE", True)
    monkeypatch.setattr(cardcom_service, "charge_recurring", _fake_charge_ok())
    past = _iso(_now() - timedelta(minutes=1))
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(
            db, "recover@example.com", subscription_status="past_due", tier="pro",
            dunning_next_retry_at=past, cardcom_token="tok_rec", billing_failure_count=1,
        )
        await cardcom_service.run_renewal_batch(db)
        u = (await db.execute_fetchall(
            "SELECT subscription_status, tier, billing_failure_count, dunning_next_retry_at FROM users WHERE internal_id=?",
            (uid,)))[0]
    assert u["subscription_status"] == "active"           # recovery
    assert u["tier"] == "pro"
    assert u["billing_failure_count"] == 0
    assert u["dunning_next_retry_at"] is None


# ── TC-B3-07 — cancel end-of-period + churn + safe double cancel (AC5) ───────

@pytest.mark.asyncio
async def test_cancel_end_of_period_then_drop_to_free():
    future = _iso(_now() + timedelta(days=10))
    past = _iso(_now() - timedelta(minutes=1))
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(
            db, "cancel@example.com", subscription_status="active", tier="pro",
            next_billing_at=future, cardcom_token="tok_c",
        )
        resp = await cardcom_service.cancel_subscription(uid, db)
        assert resp.access_until is not None

        u = (await db.execute_fetchall(
            "SELECT subscription_status, tier, subscription_cancelled_pending_at FROM users WHERE internal_id=?",
            (uid,)))[0]
        assert u["subscription_status"] == "cancelled"
        assert u["tier"] == "pro"                          # access retained until period end
        assert u["subscription_cancelled_pending_at"] is not None

        # Cancelling again is safe (idempotent).
        resp2 = await cardcom_service.cancel_subscription(uid, db)
        assert "already" in resp2.message.lower()

        # Period ends -> drop to Free.
        await db.execute(
            "UPDATE users SET subscription_cancelled_pending_at=? WHERE internal_id=?", (past, uid))
        await db.commit()
        dropped = await cardcom_service.drop_cancelled_to_free(db)
        assert dropped["dropped_to_free"] >= 1
        u = (await db.execute_fetchall(
            "SELECT subscription_status, tier FROM users WHERE internal_id=?", (uid,)))[0]
    assert u["subscription_status"] == "none"
    assert u["tier"] == "free"


@pytest.mark.asyncio
async def test_cancel_trial_keeps_access_until_trial_end():
    trial_end = _iso(_now() + timedelta(days=5))
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        uid = await _mk_user(
            db, "canceltrial@example.com", subscription_status="trial", tier="pro",
            trial_started_at=_iso(_now()), trial_ends_at=trial_end,
        )
        resp = await cardcom_service.cancel_subscription(uid, db)
        u = (await db.execute_fetchall(
            "SELECT subscription_status FROM users WHERE internal_id=?", (uid,)))[0]
    assert u["subscription_status"] == "cancelled"
    assert resp.access_until is not None


# ── TC-B3-08 — billing cron endpoint auth + shape (D-B9) ─────────────────────

def test_billing_cron_requires_secret():
    with TestClient(app) as client:
        assert client.post("/api/cron/billing").status_code in (403, 422)
        bad = client.post("/api/cron/billing", headers={"X-Cron-Secret": "wrong"})
        assert bad.status_code == 403
        ok = client.post("/api/cron/billing", headers={"X-Cron-Secret": cfg.CRON_SECRET})
    assert ok.status_code == 200
    body = ok.json()
    assert "expire_trials" in body and "cancel_drop" in body and "renewal" in body


# ── TC-B3-09 — no live terminal wired (AC8) ──────────────────────────────────

def test_no_live_terminal_configured():
    assert cfg.FEATURE_CARDCOM_LIVE is False
    assert cfg.CARDCOM_TERMINAL_ID == ""                 # no real terminal in env
    env_example = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")
    assert "FEATURE_CARDCOM_LIVE=false" in env_example
    assert "CARDCOM_TERMINAL_ID=\n" in env_example or "CARDCOM_TERMINAL_ID=" in env_example
