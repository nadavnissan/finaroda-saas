"""Migration 024 — xp_events (SPEC §5.6; XP_ECONOMY.md v1.0).

Every XP gain is a discrete event from a CLOSED list of sources. Server-side only.
The UNIQUE (user_id, source, ref) constraint is the idempotency / farming guard:
a duplicate (source, ref) never awards XP twice. Ranks are derived from SUM(amount)
— no stored rank column. Forbidden forever: XP on profit/what-if outcome, scan
count, streaks, referrals (RED LINE — XP measures discipline & learning only).
"""
import aiosqlite

MIGRATION_ID = "024_xp_events"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS xp_events (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER NOT NULL REFERENCES users(internal_id),
            source   TEXT NOT NULL,   -- onboarding | daily_first_scan | academy_lesson | journal_reveal_viewed
            ref      TEXT NOT NULL,   -- idempotency key: screen/action | YYYY-MM-DD | lesson_id | scenario_id
            amount   INTEGER NOT NULL,
            ts       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, source, ref)
        )
        """
    )
    await db.execute("CREATE INDEX IF NOT EXISTS idx_xp_user ON xp_events(user_id, ts DESC)")
    await db.commit()
