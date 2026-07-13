"""Migration 029 — three-plan model: Free / Basic / Pro (Decision A, Nadav 2026-07-13).

The Advanced tier is retired. The catalogue becomes:

    plan    ₪/month   coins/scan   chart layers   scans/day
    free       0           2        ema200_only       1
    basic      59          5           full        0 (unlimited)
    pro       149         10           full        0 (unlimited)

Basic inherits the old Advanced breadth (5 coins, full layers) at the new price, so
any existing `advanced` user is migrated to `basic` (identical entitlement, cheaper).
Prices are PENDING-ACCOUNTANT (marked in PRD/SPEC); admin can retune them from
`system_settings` without a deploy.

The `tier` CHECK constraints (users, broadcasts, academy, feature_flags) still tolerate
the legacy 'advanced' literal — we do NOT rebuild those tables (destructive, needless):
'advanced' simply stops being offered or assigned. The advanced-specific settings rows
are removed so `GET /api/plans` and the admin editor surface only the three live plans.
"""
import aiosqlite

MIGRATION_ID = "029_three_plan_model"


async def up(db: aiosqlite.Connection) -> None:
    # 1. Migrate any existing Advanced users to Basic (same 5-coin / full-layer breadth).
    await db.execute("UPDATE users SET tier = 'basic' WHERE tier = 'advanced'")

    # 2. Retune the live plan settings. Basic takes the old Advanced breadth (5 coins);
    #    prices move to the new (PENDING-ACCOUNTANT) numbers, stored in agorot.
    updates = [
        ("scan_coins_basic", "5"),        # was 2 → Basic now = old Advanced breadth
        ("plan_price_basic", "5900"),     # ₪59  (PENDING-ACCOUNTANT)
        ("plan_price_pro", "14900"),      # ₪149 (PENDING-ACCOUNTANT)
    ]
    for key, value in updates:
        await db.execute(
            "UPDATE system_settings SET value = ? WHERE key = ?", (value, key)
        )

    # 3. Drop the Advanced-specific settings rows (retired tier).
    for key in (
        "scan_coins_advanced",
        "plan_price_advanced",
        "chart_layers_advanced",
        "scans_per_day_advanced",
    ):
        await db.execute("DELETE FROM system_settings WHERE key = ?", (key,))

    await db.commit()
