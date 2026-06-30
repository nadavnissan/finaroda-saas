"""Migration 008 — system_settings (key-value, audit 017).

Admin-controlled runtime settings without code (SPEC §6: coins-per-scan by plan,
global scan threshold, etc. are stored here). Schema + a few FINARODA defaults.
"""
import aiosqlite

MIGRATION_ID = "008_system_settings"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS system_settings (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL,
            value_type  TEXT NOT NULL DEFAULT 'string'
                        CHECK (value_type IN ('string','int','float','bool','json')),
            description TEXT,
            updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # FINARODA defaults — coins per scan by plan + global threshold (admin-editable; SPEC §9).
    seeds = [
        ("scan_coins_basic", "2", "int", "Coins returned per scan — basic plan"),
        ("scan_coins_advanced", "5", "int", "Coins returned per scan — advanced plan"),
        ("scan_coins_pro", "10", "int", "Coins returned per scan — pro plan"),
        ("scan_threshold_global", "70", "float", "Global score threshold for a coin to pass"),
    ]
    for key, value, vtype, desc in seeds:
        await db.execute(
            """INSERT OR IGNORE INTO system_settings (key, value, value_type, description)
               VALUES (?, ?, ?, ?)""",
            (key, value, vtype, desc),
        )
    await db.commit()
