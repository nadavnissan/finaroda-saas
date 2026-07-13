"""Migration 030 — support ticket diagnostic context (Nadav 2026-07-13).

A ticket must carry enough context to debug blind: who, on what plan, on what app
version, and what they just did. user_id / plan are already joinable; here we add the
app_version captured at filing time. The "last 20 logged events" are assembled at read
time in the admin ticket view from the existing xp / scan / funnel logs (no new store).
"""
import aiosqlite

MIGRATION_ID = "030_ticket_app_version"


async def up(db: aiosqlite.Connection) -> None:
    cols = {r[1] for r in await db.execute_fetchall("PRAGMA table_info(support_tickets)")}
    if "app_version" not in cols:
        await db.execute("ALTER TABLE support_tickets ADD COLUMN app_version TEXT")
    await db.commit()
