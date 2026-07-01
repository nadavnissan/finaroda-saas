"""Migration 021 — score_log.profile (P2 scorer wiring).

The real scorer runs three calibration profiles per coin (momentum / pullback /
continuation). Only momentum is DISPLAYED; all three are LOGGED for measure-first
research (base-rate per profile). Adds a `profile` discriminator to score_log.
"""
import aiosqlite

MIGRATION_ID = "021_score_log_profile"


async def up(db: aiosqlite.Connection) -> None:
    cols = [r[1] for r in await db.execute_fetchall("PRAGMA table_info(score_log)")]
    if "profile" not in cols:
        await db.execute(
            "ALTER TABLE score_log ADD COLUMN profile TEXT NOT NULL DEFAULT 'momentum'"
        )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_scorelog_profile ON score_log(profile, logged_at DESC)"
    )
    await db.commit()
