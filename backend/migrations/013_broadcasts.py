"""Migration 013 — admin_broadcasts + broadcast_reads (in-app + email; audit 020).

Admin announcements: in-app feed (by tier) and email fan-out (via Resend).
target_tier vocabulary aligned to FINARODA plans.
"""
import aiosqlite

MIGRATION_ID = "013_broadcasts"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_broadcasts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            body        TEXT NOT NULL,
            target_tier TEXT
                        CHECK (target_tier IS NULL OR
                               target_tier IN ('free','basic','advanced','pro')),
            created_by  INTEGER NOT NULL REFERENCES users(internal_id),
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS broadcast_reads (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            broadcast_id INTEGER NOT NULL REFERENCES admin_broadcasts(id) ON DELETE CASCADE,
            user_id      INTEGER NOT NULL REFERENCES users(internal_id),
            read_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (broadcast_id, user_id)
        )
        """
    )
    await db.commit()
