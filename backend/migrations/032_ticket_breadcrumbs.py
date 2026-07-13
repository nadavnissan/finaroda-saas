"""Migration 032 — Stage 7: ticket breadcrumbs + churn-survey index.

Adds `support_tickets.breadcrumbs` (JSON array of the reporter's last client-side
events — route changes, scan submits, API errors, notification-panel opens) so admin
can debug blind alongside the existing server-side event union. Breadcrumbs are
whitelisted client metadata only — NEVER journal outcome values (reveal-gating red
line; enforced by the server-side sanitizer in api/support.py).

`churn_reasons` (mig 006) already holds the exit-survey schema; here we only add an
index on user_id so the admin user-table churn-flag lookup and the churn list stay
cheap.
"""
import aiosqlite

MIGRATION_ID = "032_ticket_breadcrumbs"


async def up(db: aiosqlite.Connection) -> None:
    cols = {
        r[1]
        for r in await db.execute_fetchall("PRAGMA table_info(support_tickets)")
    }
    if "breadcrumbs" not in cols:
        # JSON array text; NULL for tickets filed before this migration / without a buffer.
        await db.execute("ALTER TABLE support_tickets ADD COLUMN breadcrumbs TEXT")

    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_churn_user ON churn_reasons(user_id, created_at DESC)"
    )
    await db.commit()
