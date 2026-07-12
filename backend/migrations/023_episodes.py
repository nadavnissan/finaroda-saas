"""Migration 023 — episodes (Episode Library; SPEC §5.5 + onboarding F13).

Real, dated daily klines rendered in-app (recharts) — never external captures.
Seeded from backend/data/onboarding_episodes.json, which is built from Bybit's
public API with empirical-truth assertions (the builder throws if the real klines
do not support the documented entry/outcome). Seed is idempotent on ext_id.

Withholding: `entry_index` splits the stored klines into a pre-decision "setup"
slice (candles 0..entry_index) and a withheld "reveal" slice (entry_index+1..).
The API never returns the reveal slice or `outcome` until an explicit reveal call
(S1 trap, S10 time-machine — AC: outcome not present in the DOM pre-reveal).
"""
import json
from pathlib import Path

import aiosqlite

MIGRATION_ID = "023_episodes"

_SEED = Path(__file__).parent / "seed_data" / "onboarding_episodes.json"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS episodes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            ext_id         TEXT UNIQUE NOT NULL,   -- E1/E3/E4 (natural seed key)
            coin           TEXT NOT NULL,
            date_range     TEXT NOT NULL,          -- dated range (source of truth: real klines)
            kline_data     TEXT NOT NULL,          -- JSON: full real daily candles [{t,o,h,l,c,v}]
            scenario_type  TEXT NOT NULL,          -- trap|valid_setup|discipline_save|patience
            lesson_flag    TEXT,
            direction      TEXT,                   -- long|short (the simulated position)
            entry_index    INTEGER NOT NULL,       -- split point for server-side withholding
            entry_price    REAL,
            outcome        TEXT NOT NULL,          -- JSON, WITHHELD until reveal
            real_stats_ref TEXT,
            created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute("CREATE INDEX IF NOT EXISTS idx_episodes_scenario ON episodes(scenario_type)")

    if _SEED.exists():
        items = json.loads(_SEED.read_text(encoding="utf-8"))
        for it in items:
            derived = it.get("derived", {})
            resolved = it["resolved"]
            outcome = {
                "resolved": resolved,
                "direction": it["direction"],
                "entry_price": it["entry_price"],
                "exit_price": it.get("target_price")
                or derived.get("adverse_low")
                or derived.get("favorable_low")
                or derived.get("favorable_high"),
                "r_multiple": it["r_multiple"],
                # pct = the excursion that makes the lesson: adverse for a trap, favorable for a win
                "pct": derived.get("adverse_pct")
                if resolved == "loss"
                else derived.get("favorable_pct"),
                "score": it.get("score"),
                "real_stats_ref": it["real_stats_ref"],
            }
            await db.execute(
                """INSERT OR IGNORE INTO episodes
                   (ext_id, coin, date_range, kline_data, scenario_type, lesson_flag,
                    direction, entry_index, entry_price, outcome, real_stats_ref)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    it["ext_id"],
                    it["coin"],
                    it["date_range"],
                    json.dumps(it["kline_data"], separators=(",", ":")),
                    it["scenario_type"],
                    it["lesson_flag"],
                    it["direction"],
                    it["entry_index"],
                    it["entry_price"],
                    json.dumps(outcome, separators=(",", ":")),
                    it["real_stats_ref"],
                ),
            )
    await db.commit()
