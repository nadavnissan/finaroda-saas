"""Migration 020 — make score_log.score NULLABLE (P2).

The numeric SCORE is not available until scoreDirection extraction pass 2. P2 records
every scanned coin with score=NULL (levels are real; score is pending). Rebuilds
score_log with a nullable `score` column; all other columns/semantics unchanged.
Safe: runs on a fresh schema (no production data yet).
"""
import aiosqlite

MIGRATION_ID = "020_score_log_nullable"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS score_log_new (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_event_id    INTEGER NOT NULL REFERENCES scan_events(id),
            user_id          INTEGER NOT NULL REFERENCES users(internal_id),
            logged_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            coin             TEXT NOT NULL,
            direction        TEXT NOT NULL CHECK (direction IN ('long','short')),
            score            REAL,               -- NULLABLE until engine pass 2
            passed_threshold INTEGER NOT NULL,   -- 0/1 (interim rule until score exists)
            ema7_slope_pct   REAL,
            volume_ratio     REAL,
            price            REAL,
            entry            REAL,
            sl               REAL,
            tp               REAL,
            trailing_pct     REAL,
            outcome          TEXT,
            r_multiple       REAL,
            resolved_at      DATETIME
        )
        """
    )
    await db.execute(
        """INSERT INTO score_log_new
           SELECT id, scan_event_id, user_id, logged_at, coin, direction, score,
                  passed_threshold, ema7_slope_pct, volume_ratio, price, entry, sl, tp,
                  trailing_pct, outcome, r_multiple, resolved_at
           FROM score_log"""
    )
    await db.execute("DROP TABLE score_log")
    await db.execute("ALTER TABLE score_log_new RENAME TO score_log")
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_scorelog_coin ON score_log(coin, logged_at DESC)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_scorelog_unresolved ON score_log(outcome) WHERE outcome IS NULL"
    )
    await db.commit()
