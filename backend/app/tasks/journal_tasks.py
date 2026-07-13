"""B4 journal cron tasks — server-side scenario resolution + notification logging.

resolve_scenarios_task  evaluates open PASS scenarios against real Bybit daily klines
                        (target / risk / 7-day expiry) and writes the honest outcome.
                        Outcomes stay withheld from clients until the reveal (a scan).

journal_reveal_teasers_task  logs a 'journal_reveal_teaser' notification (in-app) for
                             users who have resolved-but-unrevealed outcomes. This is a
                             PULL teaser record only — never a push that reveals content
                             (the reveal still requires the user's own next scan).

log_trial_reminders_task  mirrors the day-11 trial reminders into notifications_log so
                          the B7f admin log shows the two decided system sends.
"""
import logging
from datetime import date, datetime, timezone

import aiosqlite
import httpx

from backend.config import BYBIT_PUBLIC_BASE_URL, DATABASE_URL
from backend.core.journal import RESOLUTION_WINDOW_DAYS, evaluate_outcome

log = logging.getLogger(__name__)
_TIMEOUT = 15.0


def _db_path() -> str:
    return DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")


async def _fetch_daily_candles(coin: str, start_ms: int) -> list[dict]:
    """Fetch Bybit daily klines for `coin` from start_ms forward (chronological)."""
    url = f"{BYBIT_PUBLIC_BASE_URL}/kline"
    params = {"category": "linear", "symbol": coin, "interval": "D", "start": start_ms, "limit": 60}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, params=params)
    resp.raise_for_status()
    rows = resp.json().get("result", {}).get("list", []) or []
    candles = [
        {"t": int(r[0]), "high": float(r[2]), "low": float(r[3]), "close": float(r[4])}
        for r in rows
    ]
    candles.sort(key=lambda c: c["t"])  # Bybit returns newest-first
    return candles


async def resolve_scenarios_task() -> dict:
    """Resolve every open PASS scenario whose candles are available. Returns counts."""
    resolved = 0
    skipped = 0
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            """SELECT id, coin, direction, entry, sl, tp, scan_date
                 FROM journal_scenarios
                WHERE scenario_type='pass' AND status='open'"""
        )
        for r in rows:
            try:
                scan_day = datetime.strptime(r["scan_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                # Candles strictly after the scan day.
                start_ms = int(scan_day.timestamp() * 1000) + 86_400_000
                candles = await _fetch_daily_candles(r["coin"], start_ms)
            except Exception as e:  # noqa: BLE001
                log.warning("resolve fetch failed coin=%s err=%s", r["coin"], e)
                skipped += 1
                continue
            days_elapsed = (date.today() - scan_day.date()).days
            window_complete = days_elapsed >= RESOLUTION_WINDOW_DAYS
            window = candles[:RESOLUTION_WINDOW_DAYS]
            status, r_result = evaluate_outcome(
                r["direction"], r["entry"], r["sl"], r["tp"], window, window_complete
            )
            if status == "open":
                skipped += 1
                continue
            await db.execute(
                """UPDATE journal_scenarios
                      SET status=?, r_result=?, resolved_at=CURRENT_TIMESTAMP
                    WHERE id=? AND status='open'""",
                (status, r_result, r["id"]),
            )
            resolved += 1
        await db.commit()
    log.info("resolve_scenarios_task: resolved=%d skipped=%d", resolved, skipped)
    return {"resolved": resolved, "skipped": skipped}


async def journal_reveal_teasers_task() -> dict:
    """Teaser sweep for users with resolved-but-unrevealed outcomes (D-N5).

    PULL-ONLY red line: the teaser NEVER carries an outcome value — the reveal still
    requires the user's own next scan. Deduped per reveal via journal_scenarios.
    teaser_sent_at, so a second run sends zero (idempotent). Multiple pending reveals
    for one user collapse into a single teaser (one bell row + one email) per sweep."""
    from backend.core import notifications as notif
    from backend.core.email import send_reveal_teaser_email

    teased_users = 0
    teased_scenarios = 0
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            """SELECT js.id, js.user_id, u.email, u.first_name
                 FROM journal_scenarios js
                 JOIN users u ON u.internal_id = js.user_id
                WHERE js.scenario_type='pass' AND js.status!='open'
                  AND js.resolved_at IS NOT NULL AND js.revealed_at IS NULL
                  AND js.teaser_sent_at IS NULL"""
        )
        by_user: dict[int, dict] = {}
        for r in rows:
            u = by_user.setdefault(
                r["user_id"],
                {"email": r["email"], "first_name": r["first_name"], "ids": []},
            )
            u["ids"].append(r["id"])

        today = date.today().isoformat()
        for user_id, info in by_user.items():
            # Admin audit record (idempotent per user per day; teaser_sent_at is the
            # authoritative per-reveal dedup below).
            await db.execute(
                """INSERT OR IGNORE INTO notifications_log
                   (user_id, notif_type, channel, ref, status, detail)
                   VALUES (?, 'journal_reveal_teaser', 'email_in_app', ?, 'sent',
                           'A journal reveal is waiting (unlocked on your next scan)')""",
                (user_id, f"teaser:{user_id}:{today}"),
            )
            # Bell row (D-N11), content-free, gated by inapp_enabled.
            await notif.create_notification(
                db, user_id, "reveal_teaser",
                "A journal reveal is waiting",
                "Run your next scan to unlock it.",
                "/dashboard", commit=False,
            )
            prefs = await notif.get_prefs(db, user_id)
            if prefs["email_product"]:
                await send_reveal_teaser_email(info["email"], info["first_name"])
            # Per-reveal sent-flag — makes the sweep idempotent.
            placeholders = ",".join("?" for _ in info["ids"])
            await db.execute(
                f"UPDATE journal_scenarios SET teaser_sent_at = CURRENT_TIMESTAMP "
                f"WHERE id IN ({placeholders})",
                tuple(info["ids"]),
            )
            teased_users += 1
            teased_scenarios += len(info["ids"])
        await db.commit()
    log.info("journal_reveal_teasers_task: users=%d scenarios=%d", teased_users, teased_scenarios)
    return {"teased_users": teased_users, "teased_scenarios": teased_scenarios}


async def log_trial_reminders_task() -> dict:
    """DEPRECATED (Stage 5): superseded by billing_tasks.trial_ending_soon_task, which the
    POST /api/cron/notifications endpoint runs. That task is now the single authoritative
    day-11 path (bell row + email + audit log). Kept for backward compatibility; no longer
    wired into any cron. Do not call alongside trial_ending_soon_task — divergent refs."""
    from datetime import timedelta

    from backend.config import TRIAL_REMINDER_LEAD_DAYS

    lead = TRIAL_REMINDER_LEAD_DAYS
    now = datetime.now(timezone.utc)
    window_start = (now + timedelta(days=lead)).isoformat()
    window_end = (now + timedelta(days=lead + 1)).isoformat()
    logged = 0
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            """SELECT internal_id FROM users
                WHERE subscription_status='trial' AND trial_ends_at BETWEEN ? AND ?""",
            (window_start, window_end),
        )
        today = now.date().isoformat()
        for r in rows:
            cur = await db.execute(
                """INSERT OR IGNORE INTO notifications_log
                   (user_id, notif_type, channel, ref, status, detail)
                   VALUES (?, 'trial_reminder_day11', 'email_in_app', ?, 'sent',
                           'Trial ends soon: active choice required (paid or Free), no auto-charge')""",
                (r["internal_id"], f"trial:{r['internal_id']}:{today}"),
            )
            logged += cur.rowcount
        await db.commit()
    log.info("log_trial_reminders_task: logged=%d", logged)
    return {"logged": logged}
