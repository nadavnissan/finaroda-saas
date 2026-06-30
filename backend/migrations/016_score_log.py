"""Migration 016 — score_log (timeline log for learning; SPEC §5.2).

The heart of the research loop: logs EVERY coin scanned (passed or not) so a true
base-rate can be computed. Levels are recorded at scan time; a backtest cron runs
price forward and fills outcome/r_multiple. Only verified indicators (EMA7 slope +
volume) are stored. No client Bybit account is recorded.
"""
import aiosqlite

MIGRATION_ID = "016_score_log"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS score_log (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_event_id    INTEGER NOT NULL REFERENCES scan_events(id),
            user_id          INTEGER NOT NULL REFERENCES users(internal_id),
            logged_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            coin             TEXT NOT NULL,
            direction        TEXT NOT NULL CHECK (direction IN ('long','short')),
            score            REAL NOT NULL,
            passed_threshold INTEGER NOT NULL,   -- 0/1

            -- verified indicators only (timeline):
            ema7_slope_pct   REAL,               -- signed
            volume_ratio     REAL,
            price            REAL,

            -- levels at scan time (for backtest):
            entry            REAL,
            sl               REAL,
            tp               REAL,
            trailing_pct     REAL,

            -- filled retroactively by the backtest cron:
            outcome          TEXT,               -- NULL | win | loss | open
            r_multiple       REAL,
            resolved_at      DATETIME
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_scorelog_coin ON score_log(coin, logged_at DESC)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_scorelog_unresolved ON score_log(outcome) WHERE outcome IS NULL"
    )
    await db.commit()
