"""Migration 025 — onboarding_funnel_events (Onboarding Spec §5).

Funnel metrics measured from day 1: 60-second completion, failure-branch
completion (1a→S2), signup after S4, trial-vs-Free fork at S11, D1 return.
Events before signup (S0–S4) carry an anon_id only; events after signup carry
user_id. Append-only analytics — NOT gamification (no streaks, no frequency
rewards; trust-not-engagement, CLAUDE.md §8.3).
"""
import aiosqlite

MIGRATION_ID = "025_onboarding_funnel_events"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS onboarding_funnel_events (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER REFERENCES users(internal_id),  -- NULL before signup
            anon_id  TEXT,                                    -- pre-signup session id
            stage    TEXT NOT NULL,   -- screen_view|branch_1a_to_s2|signup|completion|fork_choice|d1_return
            detail   TEXT,            -- JSON (e.g. {"choice":"trial"} | {"screen":"S3"})
            ts       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_funnel_stage ON onboarding_funnel_events(stage, ts DESC)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_funnel_user ON onboarding_funnel_events(user_id, ts DESC)"
    )
    await db.commit()
