"""
Cardcom v11 REST payment service — FINARODA (SPEC §9).

Sole payment provider. All amounts in agorot (integer, 1/100 ILS). HMAC-SHA256
webhook verification with constant-time compare. Credentials only from config. Every
subscription-status change routes through `billing_state` (the one state machine,
D-B4); every successful charge issues a billing document (`cardcom_invoice`, D-B3) and
emails a receipt (Stage-5 email, product-email pref respected).

⚠️ TEST/SANDBOX by default: every network call is gated by FEATURE_CARDCOM_LIVE
(default False → dry-run, no real charge). Real credentials stay as placeholders in
.env.example. No live terminal is wired (S1/AC8). Going live is a manual step by Nadav.

v11 endpoints: LowProfile/Create, LowProfile/GetLpResult, Token/ChargeToken.
Plans (tier == plan name): basic / pro (Advanced retired, mig 029). Prices from
system_settings. Dunning cadence from config (D-B5).
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite
import httpx
from fastapi import HTTPException

from backend import config
from backend.core import billing_state, cardcom_invoice
from backend.core import notifications as notif
from backend.core.email import (
    send_payment_failed_email,
    send_payment_receipt_email,
    send_subscription_canceled_email,
)
from backend.models.cardcom import CardcomCancelResponse, CardcomInitiateResponse

logger = logging.getLogger(__name__)

VALID_PLANS = ("basic", "pro")  # Advanced retired (Decision A, mig 029)
_TIMEOUT = 30.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _v11_auth() -> dict:
    """The 3 auth fields required by every v11 endpoint (from config; never hardcoded)."""
    return {
        "TerminalNumber": config.CARDCOM_TERMINAL_ID,
        "ApiName": config.CARDCOM_API_NAME,
        "ApiPassword": config.CARDCOM_API_PASSWORD,
    }


async def _get_setting_int(db: aiosqlite.Connection, key: str, default: int) -> int:
    rows = await db.execute_fetchall("SELECT value FROM system_settings WHERE key = ?", (key,))
    if rows and rows[0][0] is not None:
        try:
            return int(rows[0][0])
        except (TypeError, ValueError):
            return default
    return default


async def get_plan_price_agorot(db: aiosqlite.Connection, plan: str) -> int:
    """Plan price in agorot, from system_settings (admin-editable)."""
    return await _get_setting_int(db, f"plan_price_{plan}", 0)


async def _issue_document_and_receipt(
    db: aiosqlite.Connection,
    user_id: int,
    transaction_id: int,
    amount_agorot: int,
    plan: Optional[str],
    *,
    commit: bool = False,
) -> dict:
    """
    Issue the billing document for a successful charge and email the receipt (D-B3).

    Idempotent: the document is unique per transaction, and the receipt is only sent
    once (emailed_at guard). The receipt is a product email (email_product pref honored,
    Stage 5). Never raises — a payment must never be lost to a doc/email hiccup.
    """
    doc = await cardcom_invoice.issue_document(db, user_id, transaction_id, amount_agorot, commit=False)
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
                    await cardcom_invoice.mark_emailed(db, doc["id"], commit=False)
    if commit:
        await db.commit()
    return doc


async def initiate_checkout(
    user_id: int,
    plan: str,
    db: aiosqlite.Connection,
    is_upgrade: bool = False,
) -> CardcomInitiateResponse:
    """
    Initiate a Cardcom v11 LowProfile checkout (tokenizes the card).
    503 when FEATURE_CARDCOM_LIVE is False (sandbox not wired to a terminal).
    409 when the user already has an active subscription for this plan.
    """
    if plan not in VALID_PLANS:
        raise HTTPException(400, f"Invalid plan: {plan}")
    if not config.FEATURE_CARDCOM_LIVE:
        raise HTTPException(503, "Payment processing is in test mode (FEATURE_CARDCOM_LIVE=false)")

    cursor = await db.execute(
        "SELECT tier, subscription_status FROM users WHERE internal_id = ?", (user_id,)
    )
    user_row = await cursor.fetchone()
    if not user_row:
        raise HTTPException(404, "User not found")
    current_tier, sub_status = user_row[0], user_row[1]
    if current_tier == plan and sub_status == "active" and not is_upgrade:
        raise HTTPException(409, f"Already subscribed to plan: {plan}")

    amount_agorot = await get_plan_price_agorot(db, plan)
    if amount_agorot <= 0:
        raise HTTPException(400, f"No price configured for plan: {plan}")

    cursor = await db.execute(
        """INSERT INTO payment_transactions
           (user_id, amount_ils, currency, status, kind, cardcom_response_json, created_at)
           VALUES (?, ?, 'ILS', 'pending', 'first', ?, ?)""",
        (user_id, amount_agorot, json.dumps({"tier_target": plan}), _now().isoformat()),
    )
    await db.commit()
    transaction_id = cursor.lastrowid

    payload = {
        **_v11_auth(),
        "ReturnValue": str(transaction_id),
        "Amount": amount_agorot,  # v11: integer agorot
        "SuccessRedirectUrl": f"{config.CARDCOM_REDIRECT_RETURN_URL}/checkout/success",
        "FailedRedirectUrl": f"{config.CARDCOM_REDIRECT_RETURN_URL}/checkout/cancelled",
        "WebHookUrl": f"{config.CARDCOM_REDIRECT_RETURN_URL}/api/cardcom/webhook",
    }
    url = f"{config.CARDCOM_BASE_URL}/LowProfile/Create"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            cardcom_data = response.json()
    except Exception as e:  # noqa: BLE001 — persist failure then surface 503
        logger.error("Cardcom LowProfile/Create failure tx=%s: %s", transaction_id, e)
        await db.execute(
            "UPDATE payment_transactions SET status='failed', failure_reason=? WHERE id=?",
            (str(e), transaction_id),
        )
        await db.commit()
        raise HTTPException(503, "Payment gateway error")

    cardcom_tx_id = cardcom_data.get("LowProfileId", "")
    redirect_url = cardcom_data.get("Url", "")
    if not cardcom_tx_id or not redirect_url:
        await db.execute(
            "UPDATE payment_transactions SET status='failed', failure_reason=? WHERE id=?",
            ("Missing LowProfileId or Url", transaction_id),
        )
        await db.commit()
        raise HTTPException(503, "Payment gateway error")

    await db.execute(
        "UPDATE payment_transactions SET cardcom_tx_id=? WHERE id=?",
        (cardcom_tx_id, transaction_id),
    )
    await db.commit()
    return CardcomInitiateResponse(
        redirect_url=redirect_url,
        transaction_id=transaction_id,
        expires_at=_now() + timedelta(minutes=15),
    )


async def get_lp_result(low_profile_id: str) -> dict:
    """Fallback poll of LowProfile/GetLpResult when the webhook hasn't arrived."""
    url = f"{config.CARDCOM_BASE_URL}/LowProfile/GetLpResult"
    payload = {**_v11_auth(), "LowProfileId": low_profile_id}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except Exception as e:  # noqa: BLE001
        logger.error("Cardcom GetLpResult failure lp=%s: %s", low_profile_id, e)
        raise HTTPException(503, "Payment gateway error")


async def handle_webhook(raw_body: bytes, signature_header: str, db: aiosqlite.Connection) -> None:
    """
    Verify HMAC (constant-time), then confirm the payment server-side (D-B8): activate
    via the state machine, issue the document, email the receipt. Idempotent — deduped
    by deal id (cardcom_tx_id) and the pending->success guard, so a duplicate callback
    is processed once. A tampered/unsigned callback is ignored. The client redirect
    alone never activates a plan (only this server-verified path does).
    """
    expected = hmac.new(
        config.CARDCOM_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature_header or ""):
        logger.warning("Cardcom webhook: invalid signature")
        return

    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.error("Cardcom webhook: bad JSON: %s", e)
        return

    cardcom_tx_id = data.get("LowProfileId", "")
    if not cardcom_tx_id:
        logger.warning("Cardcom webhook: missing LowProfileId")
        return

    cursor = await db.execute(
        "SELECT id, user_id, status, amount_ils, cardcom_response_json FROM payment_transactions WHERE cardcom_tx_id=?",
        (cardcom_tx_id,),
    )
    tx_row = await cursor.fetchone()
    if not tx_row:
        logger.warning("Cardcom webhook: tx not found cardcom_tx=%s", cardcom_tx_id)
        return
    tx_id, user_id, tx_status, amount_agorot, response_json_str = tx_row
    if tx_status != "pending":
        logger.info("Cardcom webhook: duplicate tx=%s (status=%s), skipping", tx_id, tx_status)
        return

    try:
        tier_target = json.loads(response_json_str or "{}").get("tier_target", "")
    except Exception:  # noqa: BLE001
        tier_target = ""

    now = _now()
    if str(data.get("ResponseCode", "")) == "0":
        cursor = await db.execute("SELECT tier FROM users WHERE internal_id=?", (user_id,))
        old = await cursor.fetchone()
        old_tier = old[0] if old else "free"
        await db.execute(
            "UPDATE payment_transactions SET status='success', completed_at=? WHERE id=?",
            (now.isoformat(), tx_id),
        )
        # Activate via the state machine (any prior state -> active is legal).
        await billing_state.apply_transition(
            db, user_id, billing_state.ACTIVE, "subscription_started",
            new_tier=tier_target, tier_before=old_tier, tier_after=tier_target,
            transaction_id=tx_id, commit=False,
        )
        # Billing bookkeeping: clear any dunning / cancel state, set the next charge date.
        await db.execute(
            """UPDATE users
               SET last_payment_at=?, next_billing_at=?, cardcom_token=?,
                   billing_failure_count=0, dunning_next_retry_at=NULL,
                   subscription_cancelled_pending_at=NULL, suspended_at=NULL,
                   subscription_started_at=COALESCE(subscription_started_at, ?)
               WHERE internal_id=?""",
            (now.isoformat(), (now + timedelta(days=config.BILLING_PERIOD_DAYS)).isoformat(),
             data.get("Token", ""), now.isoformat(), user_id),
        )
        await _issue_document_and_receipt(db, user_id, tx_id, amount_agorot, tier_target, commit=False)
        await db.commit()
        logger.info("Cardcom webhook: success tx=%s user=%s tier=%s", tx_id, user_id, tier_target)
    else:
        await db.execute(
            "UPDATE payment_transactions SET status='failed', failure_reason=? WHERE id=?",
            (data.get("Description", "unknown"), tx_id),
        )
        await db.commit()
        logger.warning("Cardcom webhook: payment failed tx=%s", tx_id)


async def cancel_subscription(user_id: int, db: aiosqlite.Connection) -> CardcomCancelResponse:
    """
    Cancel at period end (D-B6). Status -> `cancelled`; the user keeps paid access until
    the paid-through date (next_billing_at, or trial_ends_at for a trial), then a cron
    drops them to Free. Idempotent: cancelling an already-cancelled / non-paid account
    returns gracefully without a second transition. The churn survey is a separate,
    skippable client call (POST /api/churn/survey).
    """
    cursor = await db.execute(
        """SELECT subscription_status, next_billing_at, trial_ends_at, email, first_name
           FROM users WHERE internal_id=?""",
        (user_id,),
    )
    user_row = await cursor.fetchone()
    if not user_row:
        raise HTTPException(404, "User not found")
    sub_status, next_billing_str, trial_ends_str, email, first_name = user_row

    now = _now()
    # Already cancelled (idempotent) — return the existing access-until, no re-transition.
    if sub_status == billing_state.CANCELLED:
        cur = await db.execute(
            "SELECT subscription_cancelled_pending_at FROM users WHERE internal_id=?", (user_id,)
        )
        pend = (await cur.fetchone())[0]
        access_until = _parse_dt(pend)
        return CardcomCancelResponse(
            cancelled_at=now, access_until=access_until,
            message="Subscription already cancelled.",
        )
    if sub_status not in (billing_state.ACTIVE, billing_state.TRIAL, billing_state.PAST_DUE):
        raise HTTPException(400, "No active subscription")

    # Access-until: paid subs keep to next_billing_at; a trial keeps to trial_ends_at.
    access_until = _parse_dt(next_billing_str) or _parse_dt(trial_ends_str)

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
    return CardcomCancelResponse(cancelled_at=now, access_until=access_until, message=msg)


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


async def start_trial(db: aiosqlite.Connection, user_id: int, plan: str = "pro") -> dict:
    """
    Start the 14-day trial WITHOUT a card (SPEC §9/§12.3, D1 change order 2026-07-09).
    No card, no tokenization, no auto-charge: next_billing_at stays NULL. A day-11
    reminder is sent by the trial-ending cron; at expiry the user is moved to Free
    (expire_trials), never charged. Card capture happens only at explicit paid
    conversion via initiate_checkout. Only from a fresh account.
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
    # State: none -> trial via the machine. next_billing_at is explicitly NULL (no card).
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


async def charge_recurring(
    db: aiosqlite.Connection, user_id: int, cardcom_token: str, tier: str, amount_agorot: int
) -> dict:
    """Charge a stored token via Token/ChargeToken. Never raises. Dry-run when not live."""
    if not config.FEATURE_CARDCOM_LIVE:
        return {"success": False, "dry_run": True}

    now = _now()
    cursor = await db.execute(
        """INSERT INTO payment_transactions
           (user_id, amount_ils, currency, status, kind, cardcom_response_json, created_at)
           VALUES (?, ?, 'ILS', 'pending', 'recurring', ?, ?)""",
        (user_id, amount_agorot, json.dumps({"tier_target": tier, "recurring": True}), now.isoformat()),
    )
    await db.commit()
    transaction_id = cursor.lastrowid

    url = f"{config.CARDCOM_BASE_URL}/Token/ChargeToken"
    payload = {**_v11_auth(), "Token": cardcom_token, "Amount": amount_agorot, "ReturnValue": str(transaction_id)}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            cardcom_data = response.json()
    except Exception as e:  # noqa: BLE001
        await db.execute(
            "UPDATE payment_transactions SET status='failed', failure_reason=? WHERE id=?",
            (str(e), transaction_id),
        )
        await db.commit()
        return {"success": False, "error": str(e), "transaction_id": transaction_id}

    if str(cardcom_data.get("ResponseCode", "")) == "0":
        await db.execute(
            "UPDATE payment_transactions SET status='success', completed_at=? WHERE id=?",
            (now.isoformat(), transaction_id),
        )
        await db.commit()
        return {"success": True, "transaction_id": transaction_id}
    await db.execute(
        "UPDATE payment_transactions SET status='failed', failure_reason=? WHERE id=?",
        (cardcom_data.get("Description", "unknown"), transaction_id),
    )
    await db.commit()
    return {"success": False, "error": cardcom_data.get("Description", "unknown"),
            "transaction_id": transaction_id}


async def _charge_succeeded(db: aiosqlite.Connection, user_id: int, was_past_due: bool) -> None:
    """Post-success bookkeeping for a recurring charge: reset dunning, advance the period,
    and (if recovering from past_due) move back to active."""
    now = _now()
    next_at = (now + timedelta(days=config.BILLING_PERIOD_DAYS)).isoformat()
    if was_past_due:
        await billing_state.apply_transition(
            db, user_id, billing_state.ACTIVE, "subscription_reactivated", commit=False
        )
    else:
        await billing_state.apply_transition(
            db, user_id, billing_state.ACTIVE, "subscription_renewed", commit=False
        )
    await db.execute(
        """UPDATE users SET last_payment_at=?, next_billing_at=?, billing_failure_count=0,
           dunning_next_retry_at=NULL, suspended_at=NULL WHERE internal_id=?""",
        (now.isoformat(), next_at, user_id),
    )


async def _charge_failed(db: aiosqlite.Connection, user_id: int, failure_count: int,
                         email: str, first_name: Optional[str]) -> str:
    """
    Dunning ladder (D-B5) for a failed recurring charge. Returns the outcome:
    'past_due' (scheduled a retry) or 'expired' (dunning exhausted -> Free).
    Idempotent per run: state + schedule are derived from the failure count only.
    """
    now = _now()
    new_count = failure_count + 1
    offsets = config.DUNNING_RETRY_OFFSETS_HOURS
    prefs = await notif.get_prefs(db, user_id)

    if new_count <= len(offsets):
        # Schedule the next retry. First failure moves active -> past_due; subsequent
        # failures stay past_due and only reschedule (past_due self-loop is not a
        # transition, so it is a plain reschedule + audit row).
        retry_at = now + timedelta(hours=offsets[new_count - 1])
        if failure_count == 0:
            await billing_state.apply_transition(
                db, user_id, billing_state.PAST_DUE, "subscription_past_due", commit=False
            )
        else:
            await db.execute(
                """INSERT INTO subscription_events (user_id, event_type, metadata_json, created_at)
                   VALUES (?, 'dunning_retry_scheduled', ?, ?)""",
                (user_id, json.dumps({"attempt": new_count, "retry_at": retry_at.isoformat()}),
                 now.isoformat()),
            )
        await db.execute(
            """UPDATE users SET billing_failure_count=?, dunning_next_retry_at=?,
               suspended_at=? WHERE internal_id=?""",
            (new_count, retry_at.isoformat(),
             now.isoformat() if failure_count == 0 else None, user_id),
        )
        if prefs.get("email_product", True):
            await send_payment_failed_email(email, first_name, new_count, retry_at.strftime("%d/%m/%Y"))
        # Past-due bell notification (in-app banner reads subscription_status).
        await notif.create_notification(
            db, user_id, "billing_past_due", "Payment issue",
            "We could not process your subscription payment. We will retry automatically.",
            "/subscribe", commit=False,
        )
        return "past_due"

    # Dunning exhausted: expire and drop entitlements to Free.
    await billing_state.apply_transition(
        db, user_id, billing_state.EXPIRED, "subscription_expired_dunning",
        new_tier="free", tier_before=None, tier_after="free", commit=False,
    )
    await db.execute(
        """UPDATE users SET billing_failure_count=?, dunning_next_retry_at=NULL,
           next_billing_at=NULL, suspended_at=? WHERE internal_id=?""",
        (new_count, now.isoformat(), user_id),
    )
    if prefs.get("email_product", True):
        await send_payment_failed_email(email, first_name, new_count, None)
    return "expired"


async def run_renewal_batch(db: aiosqlite.Connection) -> dict:
    """
    Cron: charge subscriptions due for billing + process dunning retries (D-B5/D-B9).

    Charges (a) active subscriptions whose next_billing_at has passed and (b) past_due
    subscriptions whose dunning_next_retry_at has passed. On success: issue document,
    email receipt, advance the period (past_due recovers to active). On failure: walk
    the dunning ladder (past_due -> retry -> expired -> Free). Idempotent and safe to
    run twice: a charge flips the row's status/schedule so a second pass finds nothing
    due. Trials (card-free, no next_billing_at) and cancelled subs are never charged.
    """
    if not config.FEATURE_CARDCOM_LIVE:
        logger.warning("Renewal cron dry-run (FEATURE_CARDCOM_LIVE=false)")
        return {"total_due": 0, "charged_ok": 0, "charged_failed": 0,
                "newly_past_due": 0, "newly_expired": 0, "dry_run": True}

    now_iso = _now().isoformat()
    cursor = await db.execute(
        """SELECT internal_id, tier, cardcom_token, billing_failure_count,
                  subscription_status, email, first_name
           FROM users
           WHERE (
                   (subscription_status = 'active'   AND next_billing_at <= ?)
                OR (subscription_status = 'past_due' AND dunning_next_retry_at <= ?)
                 )""",
        (now_iso, now_iso),
    )
    users_due = await cursor.fetchall()
    total_due = len(users_due)
    charged_ok = charged_failed = newly_past_due = newly_expired = 0

    for row in users_due:
        user_id = row[0]
        tier = row[1]
        cardcom_token = row[2]
        failure_count = row[3] or 0
        status = row[4]
        email = row[5]
        first_name = row[6]
        was_past_due = status == billing_state.PAST_DUE

        amount = await get_plan_price_agorot(db, tier)
        if not cardcom_token or amount <= 0:
            # Cannot charge (no token / no price) — treat as a failed attempt.
            outcome = await _charge_failed(db, user_id, failure_count, email, first_name)
            charged_failed += 1
            newly_expired += outcome == "expired"
            newly_past_due += outcome == "past_due"
            await db.commit()
            continue

        result = await charge_recurring(db, user_id, cardcom_token, tier, amount)
        if result.get("success"):
            charged_ok += 1
            await _charge_succeeded(db, user_id, was_past_due)
            tx_id = result.get("transaction_id")
            if tx_id:
                await _issue_document_and_receipt(db, user_id, tx_id, amount, tier, commit=False)
            await db.commit()
        else:
            charged_failed += 1
            outcome = await _charge_failed(db, user_id, failure_count, email, first_name)
            newly_expired += outcome == "expired"
            newly_past_due += outcome == "past_due"
            await db.commit()

    return {"total_due": total_due, "charged_ok": charged_ok,
            "charged_failed": charged_failed, "newly_past_due": newly_past_due,
            "newly_expired": newly_expired}


async def drop_cancelled_to_free(db: aiosqlite.Connection) -> dict:
    """
    Cron (D-B6): a cancelled subscription whose access period has ended drops to Free.
    status cancelled -> none, tier -> free. Idempotent (only rows past their
    subscription_cancelled_pending_at are moved; a second run finds none).
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
    Cron: end trials whose date has passed. Trial → **Free** (D1/D2, 2026-07-09):
    tier='free', subscription_status='none' (the standard free state), never charged
    and never blocked. A no-card trial has no next_billing_at, so nothing is billed.
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
