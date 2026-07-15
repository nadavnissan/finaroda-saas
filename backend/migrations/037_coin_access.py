"""Migration 037 — FX4: per-plan coin allowlist (coin-identity gating).

Adds `coin_access`: one row per live plan (free/basic/pro) holding the plan's coin
allowlist (JSON array of BASE symbols, e.g. "LINK") plus a `wildcard` flag. Wildcard = 1
means "all coins in the managed universe" and auto-includes any coin added later (Pro).
DB-backed and admin-editable (mig 008/027 pattern) so the business can retune coin access
without a deploy; read per-request by resolve_coin_access() (no cache).

Founder-approved seed (2026-07-15):
  free  = [LINK, AVAX]
  basic = [LINK, AVAX, SOL, ADA, DOGE]
  pro   = wildcard (all universe coins)

RED LINE unchanged: coin access is BREADTH (which of our coins a plan may scan), never a
different verdict/score/threshold. The per-plan COUNT limits (2/5/10, mig 027) and the
daily cap are enforced independently. Trial = Pro access is applied at resolve time.
"""
import aiosqlite

MIGRATION_ID = "037_coin_access"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS coin_access (
            plan       TEXT PRIMARY KEY CHECK (plan IN ('free','basic','pro')),
            coins      TEXT NOT NULL DEFAULT '[]',  -- JSON array of base symbols
            wildcard   INTEGER NOT NULL DEFAULT 0   -- 1 = all universe coins (Pro)
                       CHECK (wildcard IN (0, 1)),
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    seeds = [
        ("free", '["LINK", "AVAX"]', 0),
        ("basic", '["LINK", "AVAX", "SOL", "ADA", "DOGE"]', 0),
        ("pro", "[]", 1),
    ]
    for plan, coins, wildcard in seeds:
        await db.execute(
            "INSERT OR IGNORE INTO coin_access (plan, coins, wildcard) VALUES (?, ?, ?)",
            (plan, coins, wildcard),
        )
    await db.commit()
