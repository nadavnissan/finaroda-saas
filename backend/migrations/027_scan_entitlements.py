"""Migration 027 — per-plan scan entitlements in system_settings (E3 table, B2).

Package B B1 gating is server-authoritative (Nadav 2026-07-13): the scan
entitlements — coins per scan, chart layers, scans per day — live in
system_settings so they are admin-editable (B7) without a deploy, exactly like the
plan prices (mig 019). The B2/E3 comparison table is the product copy for these
same values:

    plan      coins/scan   chart layers   scans/day
    free          2         ema200_only       1
    basic         2            full        0 (unlimited)
    advanced      5            full        0 (unlimited)
    pro          10            full        0 (unlimited)

`chart_layers`:   'ema200_only' = Free (chart + EMA200 only, E7) ·
                  'full' = paid (EMA7 + drawn Blueprint levels).
`scans_per_day`:  0 means unlimited. Only coins/scan + chart_layers are HARD-gated
                  server-side this phase; scans/day is exposed for the UI.

Note: basic/advanced/pro coins were already seeded in mig 008 as scan_coins_basic
/_advanced/_pro. Here we add the missing scan_coins_free plus the two new
dimensions for all four tiers. INSERT OR IGNORE keeps mig 008 values authoritative.
"""
import aiosqlite

MIGRATION_ID = "027_scan_entitlements"


async def up(db: aiosqlite.Connection) -> None:
    seeds = [
        # Free coin count (basic/advanced/pro already seeded in mig 008).
        ("scan_coins_free", "2", "int", "Coins returned per scan — free plan"),
        # Chart layers entitlement (E7): free = EMA200 only, paid = all layers.
        ("chart_layers_free", "ema200_only", "string", "Chart layers — free (chart + EMA200 only)"),
        ("chart_layers_basic", "full", "string", "Chart layers — basic (all layers)"),
        ("chart_layers_advanced", "full", "string", "Chart layers — advanced (all layers)"),
        ("chart_layers_pro", "full", "string", "Chart layers — pro (all layers)"),
        # Scans per day (0 = unlimited). Free = 1/day (F7); paid = unlimited (S11).
        ("scans_per_day_free", "1", "int", "Scans per day — free (0 = unlimited)"),
        ("scans_per_day_basic", "0", "int", "Scans per day — basic (0 = unlimited)"),
        ("scans_per_day_advanced", "0", "int", "Scans per day — advanced (0 = unlimited)"),
        ("scans_per_day_pro", "0", "int", "Scans per day — pro (0 = unlimited)"),
    ]
    for key, value, vtype, desc in seeds:
        await db.execute(
            """INSERT OR IGNORE INTO system_settings (key, value, value_type, description)
               VALUES (?, ?, ?, ?)""",
            (key, value, vtype, desc),
        )
    await db.commit()
