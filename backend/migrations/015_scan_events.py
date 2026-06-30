"""Migration 015 — scan_events (every scan, not just passers; SPEC §5.1).

One row per client scan press. Stores privacy-safe region, not full IP.
"""
import aiosqlite

MIGRATION_ID = "015_scan_events"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS scan_events (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL REFERENCES users(internal_id),
            scanned_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            coins_scanned    INTEGER,       -- how many coins were scanned
            coins_passed     INTEGER,       -- how many passed the threshold
            threshold        REAL,          -- the active threshold at scan time
            client_ip_region TEXT           -- region only (privacy), not full IP
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_scan_user ON scan_events(user_id, scanned_at DESC)"
    )
    await db.commit()
