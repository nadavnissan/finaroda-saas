"""Migration 010 — oauth_states (CSRF state store for OAuth; audit 005).

Used by Google (and future Apple) OAuth login flows. internal_id-keyed.
"""
import aiosqlite

MIGRATION_ID = "010_oauth_states"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_states (
            state      TEXT PRIMARY KEY,
            user_id    INTEGER REFERENCES users(internal_id),
            provider   TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL,
            used_at    DATETIME
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_oauth_states_expiry ON oauth_states(expires_at)"
    )
    await db.commit()
