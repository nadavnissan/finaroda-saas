"""Billing cron tasks — open a DB connection and delegate to cardcom_service."""
import logging

import aiosqlite

from backend.config import DATABASE_URL
from backend.core import cardcom_service

log = logging.getLogger(__name__)


def _db_path() -> str:
    return DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")


async def expire_trials_task() -> dict:
    """Mark trials whose end date has passed as expired."""
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        result = await cardcom_service.expire_trials(db)
    log.info("expire_trials_task: %s", result)
    return result


async def subscription_renewal_task() -> dict:
    """Charge subscriptions due for billing (dry-run unless FEATURE_CARDCOM_LIVE)."""
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        result = await cardcom_service.run_renewal_batch(db)
    log.info("subscription_renewal_task: %s", result)
    return result


async def trial_ending_soon_task() -> dict:
    """Day-13 reminder: find trials ending within ~1 day. Emails are best-effort."""
    from datetime import datetime, timedelta, timezone

    from backend.core.email import send_welcome_email  # placeholder reminder sender

    window_start = datetime.now(timezone.utc).isoformat()
    window_end = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            """SELECT email, first_name FROM users
               WHERE subscription_status='trial'
                 AND trial_ends_at BETWEEN ? AND ?""",
            (window_start, window_end),
        )
    for row in rows:
        # Reminder email is a no-op without RESEND_API_KEY (dev). Kept best-effort.
        await send_welcome_email(row["email"], row["first_name"])
    log.info("trial_ending_soon_task: notified=%d", len(rows))
    return {"notified": len(rows)}
