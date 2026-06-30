"""Migration 007 — feature_flags + user_feature_overrides (audit 011/012).

Admin-toggleable feature gates by tier, plus per-user allow/deny overrides.
Schema only — no seed flags in P0 (features land in later phases).
"""
import aiosqlite

MIGRATION_ID = "007_feature_flags"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS feature_flags (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            key           TEXT UNIQUE NOT NULL,
            description   TEXT,
            enabled       INTEGER NOT NULL DEFAULT 0,
            min_tier      TEXT NOT NULL DEFAULT 'free'
                          CHECK (min_tier IN ('free','basic','advanced','pro')),
            updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS user_feature_overrides (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(internal_id),
            feature_key TEXT NOT NULL,
            allowed     INTEGER NOT NULL,   -- 1 = force allow, 0 = force deny
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, feature_key)
        )
        """
    )
    await db.commit()
