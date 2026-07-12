"""Migration 026 — onboarding XP is once-per-user-ever (anti-farming).

A partial UNIQUE index guarantees at most ONE xp_events row per user for the
onboarding source, regardless of ref. Replaying onboarding (even after clearing
client state) therefore grants 0. Product decision (Nadav, 12/07): onboarding XP
is a single lifetime grant, credited once at completion.
"""
import aiosqlite

MIGRATION_ID = "026_xp_onboarding_once"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_xp_onboarding_once "
        "ON xp_events(user_id) WHERE source = 'onboarding'"
    )
    await db.commit()
