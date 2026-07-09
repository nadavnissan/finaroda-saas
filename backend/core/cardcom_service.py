"""
Cardcom v11 REST payment service — FINARODA (SPEC §9).

Sole payment provider. All amounts in agorot (integer, 1/100 ILS). HMAC-SHA256
webhook verification with constant-time compare. Credentials only from config.

⚠️ TEST/SANDBOX by default: every network call is gated by FEATURE_CARDCOM_LIVE
(default False → dry-run, no real charge). Real credentials stay as placeholders in
.env.example. Going live is a manual step by Nadav.

v11 endpoints: LowProfile/Create, LowProfile/GetLpResult, Token/ChargeToken.
Plans (tier == plan name): basic / advanced / pro. Prices from system_settings.
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
from backend.models.cardcom import CardcomCancelResponse, CardcomInitiateResponse

logger = logging.getLogger(__name__)

VALID_PLANS = ("basic", "advanced", "pro")
_TIMEOUT = 30.0


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
           (user_id, amount_ils, currency, status, cardcom_response_json, created_at)
           VALUES (?, ?, 'ILS', 'pending', ?, ?)""",
        (user_id, amount_agorot, json.dumps({"tier_target": plan}),
         datetime.now(timezone.utc).isoformat()),
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
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
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
    """Verify HMAC (constant-time), then update payment + subscription state. Idempotent."""
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
        "SELECT id, user_id, status, cardcom_response_json FROM payment_transactions WHERE cardcom_tx_id=?",
        (cardcom_tx_id,),
    )
    tx_row = await cursor.fetchone()
    if not tx_row:
        logger.warning("Cardcom webhook: tx not found cardcom_tx=%s", cardcom_tx_id)
        return
    tx_id, user_id, tx_status, response_json_str = tx_row
    if tx_status != "pending":
        logger.info("Cardcom webhook: duplicate tx=%s (status=%s), skipping", tx_id, tx_status)
        return

    try:
        tier_target = json.loads(response_json_str or "{}").get("tier_target", "")
    except Exception:  # noqa: BLE001
        tier_target = ""

    now = datetime.now(timezone.utc)
    if str(data.get("ResponseCode", "")) == "0":
        cursor = await db.execute("SELECT tier FROM users WHERE internal_id=?", (user_id,))
        old = await cursor.fetchone()
        old_tier = old[0] if old else "free"
        await db.execute(
            "UPDATE payment_transactions SET status='success', completed_at=? WHERE id=?",
            (now.isoformat(), tx_id),
        )
        await db.execute(
            """UPDATE users
               SET tier=?, subscription_status='active', last_payment_at=?,
                   next_billing_at=?, cardcom_token=?, billing_failure_count=0
               WHERE internal_id=?""",
            (tier_target, now.isoformat(), (now + timedelta(days=30)).isoformat(),
             data.get("Token", ""), user_id),
        )
        await db.execute(
            """INSERT INTO subscription_events
               (user_id, event_type, tier_before, tier_after, transaction_id, created_at)
               VALUES (?, 'subscription_started', ?, ?, ?, ?)""",
            (user_id, old_tier, tier_target, tx_id, now.isoformat()),
        )
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
    """Cancel at period end. User keeps access until next_billing_at."""
    cursor = await db.execute(
        "SELECT subscription_status, next_billing_at FROM users WHERE internal_id=?", (user_id,)
    )
    user_row = await cursor.fetchone()
    if not user_row:
        raise HTTPException(404, "User not found")
    sub_status, next_billing_str = user_row
    if sub_status not in ("active", "trial"):
        raise HTTPException(400, "No active subscription")

    next_billing_at: Optional[datetime] = None
    if next_billing_str:
        try:
            next_billing_at = datetime.fromisoformat(str(next_billing_str))
        except ValueError:
            next_billing_at = None

    now = datetime.now(timezone.utc)
    await db.execute(
        "UPDATE users SET subscription_cancelled_pending_at=? WHERE internal_id=?",
        ((next_billing_at or now).isoformat(), user_id),
    )
    await db.execute(
        "INSERT INTO subscription_events (user_id, event_type, created_at) VALUES (?, 'subscription_cancelled_user', ?)",
        (user_id, now.isoformat()),
    )
    await db.commit()

    if next_billing_at:
        msg = f"Subscription cancelled. Access retained until {next_billing_at.strftime('%d/%m/%Y')}."
    else:
        msg = "Subscription cancelled."
    return CardcomCancelResponse(cancelled_at=now, access_until=next_billing_at, message=msg)


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

    now = datetime.now(timezone.utc)
    trial_days = await _get_setting_int(db, "trial_days", config.TRIAL_DAYS)
    trial_ends = now + timedelta(days=trial_days)
    # next_billing_at is explicitly NULL — no card on file, no day-15 auto-charge.
    await db.execute(
        """UPDATE users SET tier=?, subscription_status='trial',
           trial_started_at=?, trial_ends_at=?, next_billing_at=NULL WHERE internal_id=?""",
        (plan, now.isoformat(), trial_ends.isoformat(), user_id),
    )
    await db.execute(
        "INSERT INTO subscription_events (user_id, event_type, tier_after, created_at) VALUES (?, 'trial_started', ?, ?)",
        (user_id, plan, now.isoformat()),
    )
    await db.commit()
    return {"subscription_status": "trial", "tier": plan, "trial_ends_at": trial_ends.isoformat()}


async def charge_recurring(
    db: aiosqlite.Connection, user_id: int, cardcom_token: str, tier: str, amount_agorot: int
) -> dict:
    """Charge a stored token via Token/ChargeToken. Never raises. Dry-run when not live."""
    if not config.FEATURE_CARDCOM_LIVE:
        return {"success": False, "dry_run": True}

    now = datetime.now(timezone.utc)
    cursor = await db.execute(
        """INSERT INTO payment_transactions
           (user_id, amount_ils, currency, status, cardcom_response_json, created_at)
           VALUES (?, ?, 'ILS', 'pending', ?, ?)""",
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
        return {"success": False, "error": str(e)}

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
    return {"success": False, "error": cardcom_data.get("Description", "unknown")}


async def run_renewal_batch(db: aiosqlite.Connection) -> dict:
    """Cron: charge subscriptions due for billing. Suspend (past_due) after 3 failures."""
    if not config.FEATURE_CARDCOM_LIVE:
        logger.warning("Renewal cron dry-run (FEATURE_CARDCOM_LIVE=false)")
        return {"total_due": 0, "charged_ok": 0, "charged_failed": 0, "newly_suspended": 0, "dry_run": True}

    now = datetime.now(timezone.utc).isoformat()
    # Only 'active' paid subscriptions are billed. Trials are card-free (no
    # next_billing_at) and must NEVER be charged (D1, 2026-07-09).
    cursor = await db.execute(
        """SELECT internal_id, tier, cardcom_token, billing_failure_count
           FROM users
           WHERE subscription_status = 'active'
             AND next_billing_at <= ?
             AND (subscription_cancelled_pending_at IS NULL OR subscription_cancelled_pending_at > ?)""",
        (now, now),
    )
    users_due = await cursor.fetchall()
    total_due = len(users_due)
    charged_ok = charged_failed = newly_suspended = 0

    for row in users_due:
        user_id, tier, cardcom_token, failure_count = row[0], row[1], row[2], row[3] or 0
        amount = await get_plan_price_agorot(db, tier)
        if not cardcom_token or amount <= 0:
            charged_failed += 1
            continue
        result = await charge_recurring(db, user_id, cardcom_token, tier, amount)
        if result.get("success"):
            charged_ok += 1
            await db.execute(
                """UPDATE users SET subscription_status='active', last_payment_at=?,
                   next_billing_at=?, billing_failure_count=0 WHERE internal_id=?""",
                (datetime.now(timezone.utc).isoformat(),
                 (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(), user_id),
            )
            await db.execute(
                "INSERT INTO subscription_events (user_id, event_type, created_at) VALUES (?, 'subscription_renewed', ?)",
                (user_id, datetime.now(timezone.utc).isoformat()),
            )
            await db.commit()
        else:
            charged_failed += 1
            new_count = failure_count + 1
            if new_count >= 3:
                newly_suspended += 1
                await db.execute(
                    """UPDATE users SET subscription_status='past_due', suspended_at=?,
                       billing_failure_count=? WHERE internal_id=?""",
                    (datetime.now(timezone.utc).isoformat(), new_count, user_id),
                )
                await db.execute(
                    "INSERT INTO subscription_events (user_id, event_type, created_at) VALUES (?, 'subscription_cancelled_failed_payment', ?)",
                    (user_id, datetime.now(timezone.utc).isoformat()),
                )
            else:
                await db.execute(
                    "UPDATE users SET billing_failure_count=? WHERE internal_id=?", (new_count, user_id)
                )
            await db.commit()

    return {"total_due": total_due, "charged_ok": charged_ok,
            "charged_failed": charged_failed, "newly_suspended": newly_suspended}


async def expire_trials(db: aiosqlite.Connection) -> dict:
    """
    Cron: end trials whose date has passed. Trial → **Free** (D1/D2, 2026-07-09):
    tier='free', subscription_status='none' (the standard free state), never charged
    and never blocked. A no-card trial has no next_billing_at, so nothing is billed.
    """
    now = datetime.now(timezone.utc).isoformat()
    cursor = await db.execute(
        "SELECT internal_id FROM users WHERE subscription_status='trial' AND trial_ends_at < ?",
        (now,),
    )
    moved = [r[0] for r in await cursor.fetchall()]
    for user_id in moved:
        await db.execute(
            "UPDATE users SET subscription_status='none', tier='free', next_billing_at=NULL WHERE internal_id=?",
            (user_id,),
        )
        await db.execute(
            "INSERT INTO subscription_events (user_id, event_type, tier_before, tier_after, created_at) "
            "VALUES (?, 'trial_ended_to_free', 'trial', 'free', ?)",
            (user_id, now),
        )
    await db.commit()
    return {"moved_to_free": len(moved)}
