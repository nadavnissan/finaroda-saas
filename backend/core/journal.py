"""B4 "What Would Have Happened" — journal scenario logic (F3, the retention core).

Three responsibilities, deliberately server-side and reveal-gated:

  1. CREATION (on scan): each PASS setup (a momentum score_log row with
     passed_threshold=1) becomes one `pass` scenario. WATCH is NEVER a scenario
     (PRD F3 AC2). A scan day with no PASS records one `no_setups_day` discipline
     row (the skip is the edge). Backfillable from historical score_log.

  2. RESOLUTION (cron, server-side): open `pass` scenarios are evaluated against the
     coin's subsequent daily candles — trigger fill, then target / risk / 7-day
     expiry — producing an honest hypothetical R (never money, F3 AC4). Outcomes are
     written to journal_scenarios but stay WITHHELD from every client payload.

  3. REVEAL-GATING (on scan): the reveal event IS the user's next scan (ALIGNMENT B3
     / F3 AC5). resolved-but-unrevealed scenarios get `revealed_at` stamped on the
     next scan; only then does the dashboard serialize their outcome. Unrevealed rows
     carry NO outcome data to the client (regression-tested, same pattern as S10).

`evaluate_outcome` is a pure function so the resolution logic is unit-testable with
synthetic candles (no network). The cron wrapper (app/tasks/journal_tasks.py) fetches
the real Bybit klines and feeds them here.
"""
from __future__ import annotations

import aiosqlite

# +25 XP for viewing a revealed outcome (XP_ECONOMY.md §1). Once per scenario.
JOURNAL_VIEW_SOURCE = "journal_reveal_viewed"
JOURNAL_VIEW_XP = 25

# Resolution window: a setup resolves against candles for up to N days after scan.
RESOLUTION_WINDOW_DAYS = 7


def evaluate_outcome(
    direction: str,
    entry: float | None,
    sl: float | None,
    tp: float | None,
    candles: list[dict],
    window_complete: bool,
) -> tuple[str, float | None]:
    """Resolve one setup against subsequent daily candles. Pure, no I/O.

    candles: chronological days AFTER the scan day, each {'high','low','close'}.
    window_complete: True once RESOLUTION_WINDOW_DAYS have fully elapsed.

    Returns (status, r_result):
      win     target hit first        r_result = +reward/risk (R)
      loss    risk level hit first    r_result = -1.0
      save    trigger never filled    r_result =  0.0  (capital preserved, no entry)
      expired triggered, no target/risk in window   r_result = signed R at last close
      open    not yet resolvable (keep waiting)      r_result = None
    """
    if entry is None or sl is None or tp is None or not candles:
        return ("open", None)
    risk = abs(entry - sl)
    if risk <= 0:
        # Degenerate geometry — nothing honest to compute.
        return ("expired", 0.0) if window_complete else ("open", None)
    r_target = round(abs(tp - entry) / risk, 4)

    triggered = False
    for c in candles:
        hi, lo, cl = c["high"], c["low"], c["close"]
        if not triggered:
            if direction == "long" and hi >= entry:
                triggered = True
            elif direction == "short" and lo <= entry:
                triggered = True
            if not triggered:
                continue
        # Once triggered, check risk before target within a candle (conservative).
        if direction == "long":
            if lo <= sl:
                return ("loss", -1.0)
            if hi >= tp:
                return ("win", r_target)
        else:
            if hi >= sl:
                return ("loss", -1.0)
            if lo <= tp:
                return ("win", r_target)

    if not triggered:
        # The entry never filled: the user was never in the trade. Capital preserved.
        return ("save", 0.0) if window_complete else ("open", None)
    if not window_complete:
        return ("open", None)
    last = candles[-1]["close"]
    r = (last - entry) / risk if direction == "long" else (entry - last) / risk
    return ("expired", round(r, 4))


async def create_scenarios_for_scan(
    db: aiosqlite.Connection,
    user_id: int,
    scan_event_id: int,
    scan_date: str,
    coins: list[dict],
) -> None:
    """Create `pass` scenarios for this scan's PASS setups; else a no_setups_day row.

    `coins` are the persisted score_log items; we key PASS scenarios on the displayed
    momentum row (which carries the geometry). Idempotent via the mig-028 partial
    unique indexes, so a backfill of the same scan is a no-op.
    """
    passes = [
        c for c in coins
        if c.get("profile") == "momentum" and c.get("passed_threshold") == 1
    ]
    if passes:
        for c in passes:
            await db.execute(
                """INSERT OR IGNORE INTO journal_scenarios
                   (user_id, scan_event_id, score_log_id, scenario_type, scan_date,
                    coin, direction, score, entry, sl, tp, trailing_pct)
                   VALUES (?, ?, ?, 'pass', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, scan_event_id, c.get("score_log_id"), scan_date,
                 c.get("coin"), c.get("direction"), c.get("score"),
                 c.get("entry"), c.get("sl"), c.get("tp"), c.get("trailing_pct")),
            )
    else:
        # A disciplined skip day. Revealed immediately (it is not an outcome to gate),
        # status 'skip' so it never inflates the reveal badge.
        await db.execute(
            """INSERT OR IGNORE INTO journal_scenarios
               (user_id, scan_event_id, scenario_type, scan_date, status,
                r_result, resolved_at, revealed_at)
               VALUES (?, ?, 'no_setups_day', ?, 'skip', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            (user_id, scan_event_id, scan_date),
        )


async def reveal_resolved_scenarios(db: aiosqlite.Connection, user_id: int) -> int:
    """Stamp revealed_at on this user's resolved-but-unrevealed PASS scenarios.

    Called when the user performs a NEW scan (the reveal event). Returns how many
    were revealed (drives the "journal has an update" teaser — pull, never push).
    """
    cur = await db.execute(
        """UPDATE journal_scenarios
              SET revealed_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
              AND scenario_type = 'pass'
              AND status != 'open'
              AND resolved_at IS NOT NULL
              AND revealed_at IS NULL""",
        (user_id,),
    )
    return cur.rowcount


async def unrevealed_count(db: aiosqlite.Connection, user_id: int) -> int:
    """Nav badge = count of resolved-but-unrevealed outcomes. Never content, never push."""
    rows = await db.execute_fetchall(
        """SELECT COUNT(*) FROM journal_scenarios
            WHERE user_id = ? AND scenario_type = 'pass'
              AND status != 'open' AND resolved_at IS NOT NULL AND revealed_at IS NULL""",
        (user_id,),
    )
    return rows[0][0] if rows else 0


async def on_scan(
    db: aiosqlite.Connection,
    user_id: int,
    scan_event_id: int,
    scan_date: str,
    coins: list[dict],
) -> int:
    """Full scan-time journal hook: reveal prior resolutions, then record this scan.

    Order matters: reveal FIRST (only scenarios resolved before this scan), then
    create this scan's scenarios (which start 'open' and are not revealed). Returns
    the number newly revealed (for the teaser).
    """
    revealed = await reveal_resolved_scenarios(db, user_id)
    await create_scenarios_for_scan(db, user_id, scan_event_id, scan_date, coins)
    return revealed
