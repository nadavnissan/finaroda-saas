"""Migration 017 — decision_snapshots (what the client actually saw; SPEC §5.3).

Evidentiary record of the decision card as displayed, tagged "analysis not advice".
Feeds the "what would have happened" client dashboard.
"""
import aiosqlite

MIGRATION_ID = "017_decision_snapshots"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_snapshots (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            score_log_id INTEGER NOT NULL REFERENCES score_log(id),
            user_id      INTEGER NOT NULL REFERENCES users(internal_id),
            shown_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            card_json    TEXT NOT NULL    -- the full card as shown (levels + 3-tier + breakdown)
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_decision_user ON decision_snapshots(user_id, shown_at DESC)"
    )
    await db.commit()
