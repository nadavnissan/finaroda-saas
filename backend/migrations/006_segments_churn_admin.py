"""Migration 006 — customer_segments + churn_reasons + admin_events (audit 001/020).

CRM/analytics infra: segment tagging, exit-survey churn capture, and the admin
audit trail (every admin mutation logged here).
"""
import aiosqlite

MIGRATION_ID = "006_segments_churn_admin"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS customer_segments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(internal_id),
            segment     TEXT NOT NULL,
            assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            assigned_by TEXT,
            UNIQUE (user_id, segment)
        )
        """
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS churn_reasons (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id            INTEGER NOT NULL REFERENCES users(internal_id),
            reason_category    TEXT NOT NULL,
            reason_subcategory TEXT,
            reason_free_text   TEXT,
            improvement_text   TEXT,
            days_as_customer   INTEGER,
            subscription_plan  TEXT,
            total_spent_ils    REAL,
            would_return       INTEGER,
            created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id    INTEGER NOT NULL REFERENCES users(internal_id),
            event_type  TEXT NOT NULL,
            target_user_id INTEGER REFERENCES users(internal_id),
            details_json TEXT,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_admin_events ON admin_events(event_type, created_at DESC)"
    )
    await db.commit()
