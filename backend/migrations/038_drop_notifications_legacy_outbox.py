"""Migration 038 — drop the dead notifications_legacy_outbox table (Stage 8 housekeeping).

Background: mig 005 created a `notifications` scheduled-outbox table that NO application
code ever read or wrote. When the Stage-5 bell feed (D-N1) needed the `notifications`
name, mig 031 renamed the outbox aside to `notifications_legacy_outbox` (non-destructive)
and flagged it for a later drop once confirmed truly dead.

Confirmed dead at Stage 8 (2026-07-20):
  - Zero application reads/writes — the only code reference is the mig-031 rename itself.
  - Zero rows on dev (verified before writing this migration).
  - Not in test_smoke.EXPECTED_TABLES (never part of the live schema contract).

Straight, idempotent drop. No data loss (the table was empty and unreferenced).
"""
import aiosqlite

MIGRATION_ID = "038_drop_notifications_legacy_outbox"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute("DROP TABLE IF EXISTS notifications_legacy_outbox")
    await db.commit()
