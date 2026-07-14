"""Billing cron tasks (Stage 3R). Open a DB connection and delegate to stripe_service.

Stripe Billing owns recurring charges + retries now, so the homegrown renewal/dunning
batch is gone. Only the non-Stripe sweeps remain here: expire our card-free trials, and a
safety-net drop of cancelled subscriptions whose period has ended (covers cancelled trials
and any missed webhook). The day-11 trial reminder also lives here."""
import logging

import aiosqlite

from backend.config import DATABASE_URL
from backend.core import stripe_service

log = logging.getLogger(__name__)


def _db_path() -> str:
    return DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")


async def expire_trials_task() -> dict:
    """Mark trials whose end date has passed as Free (D1/D2). No charge, no Stripe."""
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        result = await stripe_service.expire_trials(db)
    log.info("expire_trials_task: %s", result)
    return result


async def billing_batch_task() -> dict:
    """Stage-3R billing cron: the non-Stripe lifecycle sweeps in one pass.

    Order: expire lapsed trials, then drop cancelled subs whose period ended. Both are
    idempotent and safe to run twice. Recurring charges + dunning are Stripe's job now, so
    there is no charge step here — the webhook drives active/past_due/expired transitions."""
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        expired = await stripe_service.expire_trials(db)
        dropped = await stripe_service.drop_cancelled_to_free(db)
    result = {"expire_trials": expired, "cancel_drop": dropped}
    log.info("billing_batch_task: %s", result)
    return result


async def trial_ending_soon_task() -> dict:
    """Day-11 reminder (no-card trial, D1): find trials ending TRIAL_REMINDER_LEAD_DAYS
    out (default 3 → day 11 of a 14-day trial). Idempotent via notifications_log
    UNIQUE(notif_type, ref); a re-run inside the daily window sends zero. Each first send
    creates a bell row (respecting inapp_enabled) and a reminder email (respecting
    email_product). No charge — the reminder only prompts an active choice."""
    from datetime import datetime, timezone  # noqa: F401 (kept for parity with callers)

    from backend.config import TRIAL_REMINDER_LEAD_DAYS
    from backend.core import notifications as notif
    from backend.core.email import send_trial_reminder_email

    lead = TRIAL_REMINDER_LEAD_DAYS
    notified = 0
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        # Half-open window [now+lead, now+lead+1). datetime() normalizes stored ISO
        # timestamps (with or without tz/'T') so the day-10/11/12 boundary is exact.
        rows = await db.execute_fetchall(
            """SELECT internal_id, email, first_name, trial_ends_at FROM users
               WHERE subscription_status='trial'
                 AND datetime(trial_ends_at) >= datetime('now', ? )
                 AND datetime(trial_ends_at) <  datetime('now', ? )""",
            (f"+{lead} days", f"+{lead + 1} days"),
        )
        for row in rows:
            # One day-11 reminder per user per trial-end date. UNIQUE(notif_type, ref)
            # makes the daily-window overlap a no-op. This is the durable audit record.
            ref = f"trial:{row['internal_id']}:{(row['trial_ends_at'] or '')[:10]}"
            cur = await db.execute(
                """INSERT OR IGNORE INTO notifications_log
                   (user_id, notif_type, channel, ref, status, detail)
                   VALUES (?, 'trial_reminder_day11', 'email_in_app', ?, 'sent', ?)""",
                (row["internal_id"], ref, f"Trial ends in ~{lead} days — choose a plan or continue on Free."),
            )
            if cur.rowcount != 1:
                continue  # already sent for this trial-end date
            notified += 1
            # Bell row (D-N11), gated by inapp_enabled. Batched — committed below.
            await notif.create_notification(
                db, row["internal_id"], "trial_reminder",
                "Your trial is ending soon",
                f"Your trial ends in {lead} days. Choose a paid plan or continue on Free — no auto-charge.",
                "/subscribe", commit=False,
            )
            # Product email, gated by email_product.
            prefs = await notif.get_prefs(db, row["internal_id"])
            if prefs["email_product"]:
                await send_trial_reminder_email(row["email"], row["first_name"], lead)
        await db.commit()
    log.info("trial_ending_soon_task: notified=%d", notified)
    return {"notified": notified}
