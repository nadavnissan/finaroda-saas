"""Migration 018 — support_tickets (modern; SPEC §5.4).

Replaces the legacy Telegram-bot `support_tickets` (Claude-answer columns) with a
clean customer↔admin ticket model, internal_id-keyed.
"""
import aiosqlite

MIGRATION_ID = "018_support_tickets"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS support_tickets (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(internal_id),
            subject    TEXT NOT NULL,
            body       TEXT NOT NULL,
            category   TEXT CHECK (category IS NULL OR
                                  category IN ('bug','question','billing','other')),
            status     TEXT NOT NULL DEFAULT 'open'
                       CHECK (status IN ('open','in_progress','resolved','closed')),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_ticket_status ON support_tickets(status, created_at DESC)"
    )
    await db.commit()
