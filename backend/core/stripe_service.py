"""
Stripe Checkout + Billing — sole PSP (Stage 3R, 2026-07-14; replaces the prior provider).

Design (PSP-agnostic core survives):
  * Checkout is a hosted Stripe Checkout Session (the card never touches our servers).
    Activation happens ONLY via the verified webhook, never the browser redirect (AC2).
  * Recurring + retries are Stripe Billing / Smart Retries — the homegrown recurring-charge
    and +24h/+72h dunning scheduler were DELETED. Our failure/recovery/cancel emails still
    fire from the webhook so the copy stays ours (D-R4).
  * `billing_state` remains the single source of truth for entitlements, now fed only by
    webhooks. Our 14-day trial stays OURS (card-free, D-R2) — Stripe knows nothing about
    trialing users; the trial is expired by the cron, not Stripe.
  * Every successful charge issues an Israeli tax document via `invoice_provider` (MOCK by
    default). Stripe's own invoices are NOT Israeli tax documents.

DEV fallback (D-R1): FEATURE_STRIPE_LIVE false OR an empty STRIPE_SECRET_KEY puts checkout
into a zero-network dev path (a fake session id, redirect to the success page). Webhook
processing itself is provider-logic and runs identically offline — tests POST synthetic
Stripe events with a valid signature. All amounts are agorot ints (D-B10).
"""
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite
from fastapi import HTTPException

from backend import config
from backend.core import billing_state, invoice_provider
from backend.core import notifications as notif
from backend.core.email import (
    send_payment_failed_email,
    send_payment_receipt_email,
    send_subscription_canceled_email,
)
from backend.models.billing import CheckoutInitiateResponse, SubscriptionCancelResponse

logger = logging.getLogger(__name__)

VALID_PLANS = ("basic", "pro")  # Advanced retired (mig 029)
_SIG_TOLERANCE_SECONDS = 300


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dev_mode() -> bool:
    """True when we must NOT call Stripe (test mode or no secret key) — zero network."""
    return (not config.FEATURE_STRIPE_LIVE) or (not config.STRIPE_SECRET_KEY)


def _stripe():
    """Lazily import + configure the official SDK (only on the live path)."""
    import stripe

    stripe.api_key = config.STRIPE_SECRET_KEY
    return stripe


def _iso_from_unix(ts) -> Optional[str]:
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


# ── Settings ───────────────────────────────────────────────────────────────────
async def _get_setting_int(db: aiosqlite.Connection, key: str, default: int) -> int:
    rows = await db.execute_fetchall("SELECT value FROM system_settings WHERE key = ?", (key,))
    if rows and rows[0][0] is not None:
        try:
            return int(rows[0][0])
        except (TypeError, ValueError):
            return default
    return default


async def _get_setting_str(db: aiosqlite.Connection, key: str) -> Optional[str]:
    rows = await db.execute_fetchall("SELECT value FROM system_settings WHERE key = ?", (key,))
    if rows and rows[0][0]:
        return str(rows[0][0])
    return None


async def get_plan_price_agorot(db: aiosqlite.Connection, plan: str) -> int:
    """Plan price in agorot, from system_settings (admin-editable)."""
    return await _get_setting_int(db, f"plan_price_{plan}", 0)


async def get_stripe_price_id(db: aiosqlite.Connection, plan: str) -> Optional[str]:
    """The Stripe Price id for a plan (seeded by scripts/seed_stripe_prices.py)."""
    return await _get_setting_str(db, f"stripe_price_{plan}")


# ── Document + receipt (shared by first + recurring charges) ───────────────────
async def _issue_document_and_receipt(
    db: aiosqlite.Connection,
    user_id: int,
    transaction_id: int,
    amount_agorot: int,
    plan: Optional[str],
    *,
    commit: bool = False,
) -> dict:
    """Issue the tax document for a successful charge and email the receipt.

    Idempotent: one document per transaction, receipt sent once (emailed_at guard). Never
    raises — a payment must never be lost to a doc/email hiccup. The receipt is a product
    email (email_product pref honored, Stage 5)."""
    doc = await invoice_provider.issue_document(db, user_id, transaction_id, amount_agorot, commit=False)
    await db.execute(
        """INSERT INTO subscription_events (user_id, event_type, transaction_id, metadata_json, created_at)
           VALUES (?, 'payment_document_issued', ?, ?, ?)""",
        (user_id, transaction_id,
         json.dumps({"document_id": doc["id"], "document_type": doc["document_type"]}),
         _now().isoformat()),
    )
    if doc.get("emailed_at") is None:
        urows = await db.execute_fetchall(
            "SELECT email, first_name FROM users WHERE internal_id = ?", (user_id,)
        )
        if urows:
            email, first_name = urows[0][0], urows[0][1]
            prefs = await notif.get_prefs(db, user_id)
            if prefs.get("email_product", True):
                sent = await send_payment_receipt_email(
                    email, first_name, amount_agorot,
                    doc["document_url"], doc["document_number"], plan,
                )
                if sent:
                    await invoice_provider.mark_emailed(db, doc["id"], commit=False)
    if commit:
        await db.commit()
    return doc


# ── Checkout ───────────────────────────────────────────────────────────────────
async def initiate_checkout(
    user_id: int,
    plan: str,
    db: aiosqlite.Connection,
    is_upgrade: bool = False,
) -> CheckoutInitiateResponse:
    """
    Create a Stripe Checkout Session (mode=subscription) and return its hosted URL.

    409 when already actively subscribed to this plan. In DEV mode (no live key) returns a
    zero-network fake session that lands on the success page — activation still only ever
    happens via the webhook.
    """
    if plan not in VALID_PLANS:
        raise HTTPException(400, f"Invalid plan: {plan}")

    cursor = await db.execute(
        "SELECT tier, subscription_status, stripe_customer_id, email FROM users WHERE internal_id = ?",
        (user_id,),
    )
    user_row = await cursor.fetchone()
    if not user_row:
        raise HTTPException(404, "User not found")
    current_tier, sub_status, stripe_customer_id, email = (
        user_row[0], user_row[1], user_row[2], user_row[3]
    )
    if current_tier == plan and sub_status == "active" and not is_upgrade:
        raise HTTPException(409, f"Already subscribed to plan: {plan}")

    amount_agorot = await get_plan_price_agorot(db, plan)
    if amount_agorot <= 0:
        raise HTTPException(400, f"No price configured for plan: {plan}")

    cursor = await db.execute(
        """INSERT INTO payment_transactions
           (user_id, amount_ils, currency, status, kind, provider_response_json, created_at)
           VALUES (?, ?, 'ILS', 'pending', 'first', ?, ?)""",
        (user_id, amount_agorot, json.dumps({"tier_target": plan}), _now().isoformat()),
    )
    await db.commit()
    transaction_id = cursor.lastrowid

    frontend = config.get_frontend_url()
    success_url = f"{frontend}{config.STRIPE_SUCCESS_PATH}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{frontend}{config.STRIPE_CANCEL_PATH}"

    if _dev_mode():
        # DEV fallback: no network, deterministic fake session id.
        fake_session = f"cs_dev_{transaction_id}"
        await db.execute(
            "UPDATE payment_transactions SET stripe_reference=? WHERE id=?",
            (fake_session, transaction_id),
        )
        await db.commit()
        return CheckoutInitiateResponse(
            redirect_url=f"{frontend}{config.STRIPE_SUCCESS_PATH}?session_id={fake_session}&dev=1",
            transaction_id=transaction_id,
            expires_at=_now() + timedelta(minutes=30),
            dev_mode=True,
        )

    price_id = await get_stripe_price_id(db, plan)
    if not price_id:
        await db.execute(
            "UPDATE payment_transactions SET status='failed', failure_reason=? WHERE id=?",
            ("No Stripe price configured (run scripts/seed_stripe_prices.py)", transaction_id),
        )
        await db.commit()
        raise HTTPException(400, f"No Stripe price configured for plan: {plan}")

    stripe = _stripe()
    session_kwargs = dict(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(user_id),
        metadata={"user_id": str(user_id), "plan": plan, "transaction_id": str(transaction_id)},
        subscription_data={"metadata": {"user_id": str(user_id), "plan": plan}},
    )
    # `customer` and `customer_email` are mutually exclusive in Stripe.
    if stripe_customer_id:
        session_kwargs["customer"] = stripe_customer_id
    elif email:
        session_kwargs["customer_email"] = email

    try:
        session = stripe.checkout.Session.create(**session_kwargs)
    except Exception as e:  # noqa: BLE001 — persist failure then surface 503
        logger.error("Stripe Checkout create failure tx=%s: %s", transaction_id, e)
        await db.execute(
            "UPDATE payment_transactions SET status='failed', failure_reason=? WHERE id=?",
            (str(e), transaction_id),
        )
        await db.commit()
        raise HTTPException(503, "Payment gateway error")

    session_id = session.get("id") if isinstance(session, dict) else getattr(session, "id", "")
    session_url = session.get("url") if isinstance(session, dict) else getattr(session, "url", "")
    if not session_id or not session_url:
        await db.execute(
            "UPDATE payment_transactions SET status='failed', failure_reason=? WHERE id=?",
            ("Missing session id or url", transaction_id),
        )
        await db.commit()
        raise HTTPException(503, "Payment gateway error")

    await db.execute(
        "UPDATE payment_transactions SET stripe_reference=? WHERE id=?",
        (session_id, transaction_id),
    )
    await db.commit()
    return CheckoutInitiateResponse(
        redirect_url=session_url,
        transaction_id=transaction_id,
        expires_at=_now() + timedelta(minutes=30),
        dev_mode=False,
    )


# ── Webhook: verify + dispatch ─────────────────────────────────────────────────
def verify_and_parse(raw_body: bytes, sig_header: str, secret: str) -> Optional[dict]:
    """Verify a Stripe webhook signature (the documented t=,v1= HMAC-SHA256 scheme) and
    return the parsed event, or None if verification fails. Hand-rolled (no SDK dependency
    at the verification boundary) so the webhook path is fully testable offline; the SDK is
    still used for the outbound Checkout/Subscription API calls (D-R1)."""
    if not secret or not sig_header:
        return None
    timestamp: Optional[str] = None
    sigs: list[str] = []
    for part in sig_header.split(","):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        if k == "t":
            timestamp = v
        elif k == "v1":
            sigs.append(v)
    if not timestamp or not sigs:
        return None
    signed_payload = timestamp.encode() + b"." + raw_body
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, s) for s in sigs):
        return None
    try:
        if abs(time.time() - int(timestamp)) > _SIG_TOLERANCE_SECONDS:
            return None
    except ValueError:
        return None
    try:
        return json.loads(raw_body.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


async def handle_webhook(raw_body: bytes, sig_header: str, db: aiosqlite.Connection) -> None:
    """Verify, dedupe by event id (AC3), then dispatch. A tampered/unsigned event is
    ignored (no state change); a duplicate event id is a no-op."""
    event = verify_and_parse(raw_body, sig_header, config.STRIPE_WEBHOOK_SECRET)
    if event is None:
        logger.warning("Stripe webhook: invalid signature or body")
        return

    event_id = event.get("id")
    event_type = event.get("type")
    if not event_id or not event_type:
        return

    seen = await db.execute_fetchall(
        "SELECT 1 FROM processed_webhook_events WHERE event_id = ?", (event_id,)
    )
    if seen:
        logger.info("Stripe webhook: duplicate event %s (%s), skipping", event_id, event_type)
        return

    obj = (event.get("data") or {}).get("object") or {}
    try:
        if event_type == "checkout.session.completed":
            await _on_checkout_completed(db, obj)
        elif event_type == "invoice.paid":
            await _on_invoice_paid(db, obj)
        elif event_type == "invoice.payment_failed":
            await _on_invoice_payment_failed(db, obj)
        elif event_type == "customer.subscription.updated":
            await _on_subscription_updated(db, obj)
        elif event_type == "customer.subscription.deleted":
            await _on_subscription_deleted(db, obj)
        else:
            logger.info("Stripe webhook: unhandled event type %s", event_type)
    finally:
        # Mark processed after handling so a failed handler can be retried by Stripe.
        await db.execute(
            "INSERT OR IGNORE INTO processed_webhook_events (event_id, event_type, processed_at) VALUES (?, ?, ?)",
            (event_id, event_type, _now().isoformat()),
        )
        await db.commit()


async def _resolve_user(
    db: aiosqlite.Connection, subscription_id: Optional[str],
    customer_id: Optional[str], obj: dict,
) -> Optional[int]:
    """Map a Stripe object back to our user by subscription id, metadata, then customer id."""
    if subscription_id:
        rows = await db.execute_fetchall(
            "SELECT internal_id FROM users WHERE stripe_subscription_id = ?", (subscription_id,)
        )
        if rows:
            return rows[0][0]
    md = obj.get("metadata") or {}
    if md.get("user_id"):
        try:
            uid = int(md["user_id"])
        except (TypeError, ValueError):
            uid = None
        if uid is not None:
            rows = await db.execute_fetchall(
                "SELECT internal_id FROM users WHERE internal_id = ?", (uid,)
            )
            if rows:
                return uid
    if customer_id:
        rows = await db.execute_fetchall(
            "SELECT internal_id FROM users WHERE stripe_customer_id = ?", (customer_id,)
        )
        if rows:
            return rows[0][0]
    return None


async def _on_checkout_completed(db: aiosqlite.Connection, obj: dict) -> None:
    """checkout.session.completed → activate, store Stripe ids, issue the first document."""
    md = obj.get("metadata") or {}
    user_id = None
    if obj.get("client_reference_id"):
        try:
            user_id = int(obj["client_reference_id"])
        except (TypeError, ValueError):
            user_id = None
    if user_id is None and md.get("user_id"):
        try:
            user_id = int(md["user_id"])
        except (TypeError, ValueError):
            user_id = None
    if user_id is None:
        logger.warning("checkout.session.completed: no user id")
        return

    plan = md.get("plan") or ""
    customer_id = obj.get("customer")
    subscription_id = obj.get("subscription")
    session_id = obj.get("id")

    # Resolve the pending 'first' transaction (by metadata id, else by session id).
    tx_id = None
    if md.get("transaction_id"):
        try:
            tx_id = int(md["transaction_id"])
        except (TypeError, ValueError):
            tx_id = None
    if tx_id is None and session_id:
        rows = await db.execute_fetchall(
            "SELECT id FROM payment_transactions WHERE stripe_reference = ?", (session_id,)
        )
        if rows:
            tx_id = rows[0][0]

    trows = await db.execute_fetchall(
        "SELECT status, amount_ils FROM payment_transactions WHERE id = ?", (tx_id,)
    ) if tx_id else []
    if not trows:
        logger.warning("checkout.session.completed: tx not found user=%s", user_id)
        return
    tx_status, tx_amount = trows[0][0], trows[0][1]
    if tx_status == "success":
        return  # already activated (idempotent)

    amount_agorot = obj.get("amount_total") or tx_amount

    cur = await db.execute_fetchall("SELECT tier FROM users WHERE internal_id = ?", (user_id,))
    old_tier = cur[0][0] if cur else "free"

    now = _now()
    await db.execute(
        "UPDATE payment_transactions SET status='success', completed_at=? WHERE id=?",
        (now.isoformat(), tx_id),
    )
    await billing_state.apply_transition(
        db, user_id, billing_state.ACTIVE, "subscription_started",
        new_tier=plan, tier_before=old_tier, tier_after=plan,
        transaction_id=tx_id, commit=False,
    )
    next_at = (now + timedelta(days=config.BILLING_PERIOD_DAYS)).isoformat()
    await db.execute(
        """UPDATE users
           SET last_payment_at=?, next_billing_at=?, stripe_customer_id=COALESCE(?, stripe_customer_id),
               stripe_subscription_id=COALESCE(?, stripe_subscription_id),
               billing_failure_count=0, dunning_next_retry_at=NULL,
               subscription_cancelled_pending_at=NULL, suspended_at=NULL,
               subscription_started_at=COALESCE(subscription_started_at, ?)
           WHERE internal_id=?""",
        (now.isoformat(), next_at, customer_id, subscription_id, now.isoformat(), user_id),
    )
    await _issue_document_and_receipt(db, user_id, tx_id, amount_agorot, plan or old_tier, commit=False)
    await db.commit()
    logger.info("checkout.session.completed: active user=%s plan=%s", user_id, plan)


async def _on_invoice_paid(db: aiosqlite.Connection, obj: dict) -> None:
    """invoice.paid → recurring document + receipt (subscription_create is handled by the
    checkout event, so its invoice only refines the period date)."""
    subscription_id = obj.get("subscription")
    customer_id = obj.get("customer")
    user_id = await _resolve_user(db, subscription_id, customer_id, obj)
    if user_id is None:
        logger.warning("invoice.paid: no user (sub=%s cust=%s)", subscription_id, customer_id)
        return

    period_end = _period_end_from_invoice(obj)
    if period_end:
        await db.execute(
            "UPDATE users SET next_billing_at=? WHERE internal_id=?", (period_end, user_id)
        )

    billing_reason = obj.get("billing_reason")
    if billing_reason == "subscription_create":
        await db.commit()  # first charge already documented at checkout
        return

    invoice_id = obj.get("id")
    amount_agorot = obj.get("amount_paid") or 0
    # Idempotent per invoice id (UNIQUE stripe_reference): a duplicate paid event is a no-op.
    existing = await db.execute_fetchall(
        "SELECT id FROM payment_transactions WHERE stripe_reference = ?", (invoice_id,)
    ) if invoice_id else []
    if existing:
        await db.commit()
        return

    trow = await db.execute_fetchall(
        "SELECT subscription_status, tier FROM users WHERE internal_id = ?", (user_id,)
    )
    status = trow[0][0] if trow else "active"
    tier = trow[0][1] if trow else None
    was_past_due = status == billing_state.PAST_DUE

    cur = await db.execute(
        """INSERT INTO payment_transactions
           (user_id, amount_ils, currency, status, kind, stripe_reference, provider_response_json, created_at)
           VALUES (?, ?, 'ILS', 'success', 'recurring', ?, ?, ?)""",
        (user_id, amount_agorot, invoice_id, json.dumps({"billing_reason": billing_reason}),
         _now().isoformat()),
    )
    tx_id = cur.lastrowid

    if was_past_due:
        await billing_state.apply_transition(
            db, user_id, billing_state.ACTIVE, "subscription_reactivated", commit=False
        )
    else:
        await billing_state.apply_transition(
            db, user_id, billing_state.ACTIVE, "subscription_renewed", commit=False
        )
    now = _now()
    next_at = period_end or (now + timedelta(days=config.BILLING_PERIOD_DAYS)).isoformat()
    await db.execute(
        """UPDATE users SET last_payment_at=?, next_billing_at=?, billing_failure_count=0,
           dunning_next_retry_at=NULL, suspended_at=NULL WHERE internal_id=?""",
        (now.isoformat(), next_at, user_id),
    )
    await _issue_document_and_receipt(db, user_id, tx_id, amount_agorot, tier, commit=False)
    await db.commit()
    logger.info("invoice.paid: recurring charge user=%s amount=%s", user_id, amount_agorot)


async def _on_invoice_payment_failed(db: aiosqlite.Connection, obj: dict) -> None:
    """invoice.payment_failed → past_due + our dunning email (Stripe owns the retries)."""
    subscription_id = obj.get("subscription")
    customer_id = obj.get("customer")
    user_id = await _resolve_user(db, subscription_id, customer_id, obj)
    if user_id is None:
        return

    urow = await db.execute_fetchall(
        "SELECT subscription_status, email, first_name FROM users WHERE internal_id = ?", (user_id,)
    )
    if not urow:
        return
    status, email, first_name = urow[0][0], urow[0][1], urow[0][2]

    now = _now()
    if status == billing_state.ACTIVE:
        await billing_state.apply_transition(
            db, user_id, billing_state.PAST_DUE, "subscription_past_due", commit=False
        )
        await db.execute("UPDATE users SET suspended_at=? WHERE internal_id=?", (now.isoformat(), user_id))
    elif status == billing_state.PAST_DUE:
        # Subsequent Smart-Retry failure — no state transition (self-loop), just an audit row.
        await db.execute(
            """INSERT INTO subscription_events (user_id, event_type, metadata_json, created_at)
               VALUES (?, 'dunning_retry_scheduled', ?, ?)""",
            (user_id, json.dumps({"attempt": obj.get("attempt_count")}), now.isoformat()),
        )
    else:
        await db.commit()
        return

    attempt = obj.get("attempt_count") or 1
    retry_at = _iso_from_unix(obj.get("next_payment_attempt"))
    retry_date = None
    if retry_at:
        dt = _parse_dt(retry_at)
        retry_date = dt.strftime("%d/%m/%Y") if dt else None

    prefs = await notif.get_prefs(db, user_id)
    if prefs.get("email_product", True):
        await send_payment_failed_email(email, first_name, attempt, retry_date)
    await notif.create_notification(
        db, user_id, "billing_past_due", "Payment issue",
        "We could not process your subscription payment. We will retry automatically.",
        "/subscribe", commit=False,
    )
    await db.commit()


async def _on_subscription_updated(db: aiosqlite.Connection, obj: dict) -> None:
    """customer.subscription.updated → sync cancel-at-period-end / past_due / recovery."""
    subscription_id = obj.get("id")
    customer_id = obj.get("customer")
    user_id = await _resolve_user(db, subscription_id, customer_id, obj)
    if user_id is None:
        return

    stripe_status = obj.get("status")
    cancel_at_period_end = bool(obj.get("cancel_at_period_end"))
    period_end = _iso_from_unix(obj.get("current_period_end"))
    current = await billing_state.get_status(db, user_id)

    # Keep our Stripe ids + display period in sync.
    await db.execute(
        """UPDATE users SET stripe_subscription_id=COALESCE(stripe_subscription_id, ?),
           next_billing_at=COALESCE(?, next_billing_at) WHERE internal_id=?""",
        (subscription_id, period_end, user_id),
    )

    if cancel_at_period_end and current == billing_state.ACTIVE:
        await billing_state.apply_transition(
            db, user_id, billing_state.CANCELLED, "subscription_cancelled_user", commit=False
        )
        await db.execute(
            "UPDATE users SET subscription_cancelled_pending_at=? WHERE internal_id=?",
            (period_end or _now().isoformat(), user_id),
        )
    elif (not cancel_at_period_end and current == billing_state.CANCELLED
          and stripe_status in ("active", "trialing")):
        await billing_state.apply_transition(
            db, user_id, billing_state.ACTIVE, "subscription_reactivated", commit=False
        )
        await db.execute(
            "UPDATE users SET subscription_cancelled_pending_at=NULL WHERE internal_id=?", (user_id,)
        )
    elif stripe_status == "past_due" and current == billing_state.ACTIVE:
        await billing_state.apply_transition(
            db, user_id, billing_state.PAST_DUE, "subscription_past_due", commit=False
        )
    elif stripe_status == "active" and current == billing_state.PAST_DUE:
        await billing_state.apply_transition(
            db, user_id, billing_state.ACTIVE, "subscription_reactivated", commit=False
        )
        await db.execute(
            "UPDATE users SET billing_failure_count=0, dunning_next_retry_at=NULL WHERE internal_id=?",
            (user_id,),
        )
    await db.commit()


async def _on_subscription_deleted(db: aiosqlite.Connection, obj: dict) -> None:
    """customer.subscription.deleted → terminal. Voluntary (local cancelled) → Free/none;
    involuntary (active/past_due) → expired. Both drop entitlements to Free."""
    subscription_id = obj.get("id")
    customer_id = obj.get("customer")
    user_id = await _resolve_user(db, subscription_id, customer_id, obj)
    if user_id is None:
        return

    current = await billing_state.get_status(db, user_id)
    now = _now()
    if current == billing_state.CANCELLED:
        await billing_state.apply_transition(
            db, user_id, billing_state.NONE, "subscription_dropped_to_free",
            new_tier="free", tier_before=None, tier_after="free", commit=False,
        )
    elif current in (billing_state.ACTIVE, billing_state.PAST_DUE):
        await billing_state.apply_transition(
            db, user_id, billing_state.EXPIRED, "subscription_expired_dunning",
            new_tier="free", tier_before=None, tier_after="free", commit=False,
        )
    else:
        return  # already terminal (none/expired)

    await db.execute(
        """UPDATE users SET stripe_subscription_id=NULL, next_billing_at=NULL,
           dunning_next_retry_at=NULL, subscription_cancelled_pending_at=NULL,
           suspended_at=? WHERE internal_id=?""",
        (now.isoformat(), user_id),
    )
    await db.commit()
    logger.info("customer.subscription.deleted: user=%s from=%s", user_id, current)


def _period_end_from_invoice(obj: dict) -> Optional[str]:
    """Best-effort current-period-end from an invoice's line items (or None)."""
    lines = (obj.get("lines") or {}).get("data") or []
    for line in lines:
        period = line.get("period") or {}
        if period.get("end"):
            return _iso_from_unix(period["end"])
    return _iso_from_unix(obj.get("period_end"))


# ── Cancel (our end-of-period semantics + churn hook) ──────────────────────────
async def cancel_subscription(user_id: int, db: aiosqlite.Connection) -> SubscriptionCancelResponse:
    """
    Cancel at period end (D-B6): status → cancelled, access kept until the paid-through date.
    Tells Stripe cancel_at_period_end=true (live + has a subscription); the webhook later
    reconciles the terminal drop. Idempotent: cancelling an already-cancelled account is a
    no-op. The churn survey is a separate, skippable client call.
    """
    cursor = await db.execute(
        """SELECT subscription_status, next_billing_at, trial_ends_at, email, first_name,
                  stripe_subscription_id
           FROM users WHERE internal_id=?""",
        (user_id,),
    )
    user_row = await cursor.fetchone()
    if not user_row:
        raise HTTPException(404, "User not found")
    sub_status, next_billing_str, trial_ends_str, email, first_name, stripe_sub_id = user_row

    now = _now()
    if sub_status == billing_state.CANCELLED:
        cur = await db.execute(
            "SELECT subscription_cancelled_pending_at FROM users WHERE internal_id=?", (user_id,)
        )
        pend = (await cur.fetchone())[0]
        return SubscriptionCancelResponse(
            cancelled_at=now, access_until=_parse_dt(pend),
            message="Subscription already cancelled.",
        )
    if sub_status not in (billing_state.ACTIVE, billing_state.TRIAL, billing_state.PAST_DUE):
        raise HTTPException(400, "No active subscription")

    access_until = _parse_dt(next_billing_str) or _parse_dt(trial_ends_str)

    if not _dev_mode() and stripe_sub_id:
        try:
            _stripe().Subscription.modify(stripe_sub_id, cancel_at_period_end=True)
        except Exception as e:  # noqa: BLE001 — reconcile locally; webhook will confirm
            logger.error("Stripe cancel_at_period_end failed sub=%s: %s", stripe_sub_id, e)

    await billing_state.apply_transition(
        db, user_id, billing_state.CANCELLED, "subscription_cancelled_user",
        transaction_id=None, commit=False,
    )
    await db.execute(
        "UPDATE users SET subscription_cancelled_pending_at=? WHERE internal_id=?",
        ((access_until or now).isoformat(), user_id),
    )
    await db.commit()

    await send_subscription_canceled_email(
        email, first_name, access_until.strftime("%d/%m/%Y") if access_until else None
    )
    if access_until:
        msg = f"Subscription cancelled. Access retained until {access_until.strftime('%d/%m/%Y')}."
    else:
        msg = "Subscription cancelled."
    return SubscriptionCancelResponse(cancelled_at=now, access_until=access_until, message=msg)


# ── Trial (OURS — card-free, no Stripe; D-R2) ──────────────────────────────────
async def start_trial(db: aiosqlite.Connection, user_id: int, plan: str = "pro") -> dict:
    """
    Start the 14-day trial WITHOUT a card (SPEC §9/§12.3, D1). No Stripe involvement: Stripe
    knows nothing about trialing users. A day-11 reminder is sent by the trial-ending cron;
    at expiry the user is moved to Free (expire_trials), never charged. Card capture happens
    only at explicit paid conversion via initiate_checkout. Only from a fresh account.
    """
    if plan not in VALID_PLANS:
        raise HTTPException(400, f"Invalid plan: {plan}")
    cursor = await db.execute(
        "SELECT subscription_status, trial_started_at FROM users WHERE internal_id=?", (user_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    if row[1]:
        raise HTTPException(409, "Trial already used")

    now = _now()
    trial_days = await _get_setting_int(db, "trial_days", config.TRIAL_DAYS)
    trial_ends = now + timedelta(days=trial_days)
    await billing_state.apply_transition(
        db, user_id, billing_state.TRIAL, "trial_started",
        new_tier=plan, tier_after=plan, commit=False,
    )
    await db.execute(
        """UPDATE users SET trial_started_at=?, trial_ends_at=?, next_billing_at=NULL
           WHERE internal_id=?""",
        (now.isoformat(), trial_ends.isoformat(), user_id),
    )
    await db.commit()
    return {"subscription_status": "trial", "tier": plan, "trial_ends_at": trial_ends.isoformat()}


# ── Cron sweeps that remain (non-Stripe states) ────────────────────────────────
async def drop_cancelled_to_free(db: aiosqlite.Connection) -> dict:
    """
    Cron safety net (D-B6): a cancelled subscription whose access period has ended drops to
    Free. For paid subs Stripe's customer.subscription.deleted normally does this; this
    sweep covers cancelled TRIALS (no Stripe subscription) and any missed webhook. Idempotent.
    """
    now_iso = _now().isoformat()
    cursor = await db.execute(
        """SELECT internal_id FROM users
           WHERE subscription_status='cancelled'
             AND subscription_cancelled_pending_at IS NOT NULL
             AND subscription_cancelled_pending_at <= ?""",
        (now_iso,),
    )
    ids = [r[0] for r in await cursor.fetchall()]
    for user_id in ids:
        await billing_state.apply_transition(
            db, user_id, billing_state.NONE, "subscription_dropped_to_free",
            new_tier="free", tier_before=None, tier_after="free", commit=False,
        )
        await db.execute(
            """UPDATE users SET next_billing_at=NULL, dunning_next_retry_at=NULL,
               subscription_cancelled_pending_at=NULL WHERE internal_id=?""",
            (user_id,),
        )
    await db.commit()
    return {"dropped_to_free": len(ids)}


async def expire_trials(db: aiosqlite.Connection) -> dict:
    """
    Cron: end trials whose date has passed. Trial → Free (D1/D2): tier='free',
    subscription_status='none', never charged (no card, no Stripe). Idempotent.
    """
    now = _now().isoformat()
    cursor = await db.execute(
        "SELECT internal_id FROM users WHERE subscription_status='trial' AND trial_ends_at < ?",
        (now,),
    )
    moved = [r[0] for r in await cursor.fetchall()]
    for user_id in moved:
        await billing_state.apply_transition(
            db, user_id, billing_state.NONE, "trial_ended_to_free",
            new_tier="free", tier_before="trial", tier_after="free", commit=False,
        )
        await db.execute(
            "UPDATE users SET next_billing_at=NULL WHERE internal_id=?", (user_id,)
        )
    await db.commit()
    return {"moved_to_free": len(moved)}
