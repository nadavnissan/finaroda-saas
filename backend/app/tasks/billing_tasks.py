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
    """Day-11 reminder (no-card trial, D1): find trials ending ~TRIAL_REMINDER_LEAD_DAYS
    out (default 3 → day 11 of a 14-day trial). Daily cron + a 1-day window fires once
    per trial. Emails are best-effort. No charge — the reminder just prompts an active
    choice (paid plan or Free) before the trial ends."""
    from datetime import datetime, timedelta, timezone

    from backend.config import TRIAL_REMINDER_LEAD_DAYS
    from backend.core.email import send_welcome_email  # placeholder reminder sender

    lead = TRIAL_REMINDER_LEAD_DAYS
    now = datetime.now(timezone.utc)
    window_start = (now + timedelta(days=lead)).isoformat()
    window_end = (now + timedelta(days=lead + 1)).isoformat()
    notified = 0
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            """SELECT internal_id, email, first_name, trial_ends_at FROM users
               WHERE subscription_status='trial'
                 AND trial_ends_at BETWEEN ? AND ?""",
            (window_start, window_end),
        )
        for row in rows:
            # Idempotent notification record (B7f notifications_log): one day-11 reminder
            # per user per trial-end date. UNIQUE(notif_type, ref) makes a re-run a no-op,
            # so the day+1 window overlap never double-notifies. This is the durable record
            # (in-app + email); the email itself is a best-effort stub in dev.
            ref = f"trial:{row['internal_id']}:{(row['trial_ends_at'] or '')[:10]}"
            cur = await db.execute(
                """INSERT OR IGNORE INTO notifications_log
                   (user_id, notif_type, channel, ref, status, detail)
                   VALUES (?, 'trial_reminder_day11', 'email_in_app', ?, 'sent', ?)""",
                (row["internal_id"], ref, f"Trial ends in ~{lead} days — choose a plan or continue on Free."),
            )
            if cur.rowcount == 1:
                notified += 1
                # Reminder email is a no-op without RESEND_API_KEY (dev). Best-effort.
                await send_welcome_email(row["email"], row["first_name"])
        await db.commit()
    log.info("trial_ending_soon_task: notified=%d", notified)
    return {"notified": notified}
