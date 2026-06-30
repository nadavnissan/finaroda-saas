"""Migration 012 — waitlist (public signup capture + approval; audit 036)."""
import aiosqlite

MIGRATION_ID = "012_waitlist"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS waitlist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT UNIQUE NOT NULL,
            name        TEXT,
            source      TEXT,
            utm_source  TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            approved_at DATETIME,
            approved_by TEXT
        )
        """
    )
    await db.commit()
