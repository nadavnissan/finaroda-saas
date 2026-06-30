"""Migration 011 — beta_allowlist (closed-beta gate; audit 035).

Seeds the founder's email so it can never be locked out.
"""
import aiosqlite

MIGRATION_ID = "011_beta_allowlist"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS beta_allowlist (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT UNIQUE NOT NULL,
            added_by   TEXT,
            note       TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        """INSERT OR IGNORE INTO beta_allowlist (email, added_by, note)
           VALUES ('rodanis@gmail.com', 'system', 'founder — never lock out')"""
    )
    await db.commit()
