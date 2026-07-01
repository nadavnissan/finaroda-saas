"""Migration 019 — P1 billing: users.billing_failure_count + plan-price settings.

Adds the renewal failure counter used by the recurring-charge cron, and seeds the
3 FINARODA plan prices into system_settings (admin-editable, SPEC §9): Basic 50 /
Advanced 100 / Pro 150 ₪, stored in agorot.
"""
import aiosqlite

MIGRATION_ID = "019_billing_plan_settings"


async def up(db: aiosqlite.Connection) -> None:
    # billing_failure_count — consecutive failed recurring charges (suspend at 3).
    cols = [r[1] for r in await db.execute_fetchall("PRAGMA table_info(users)")]
    if "billing_failure_count" not in cols:
        await db.execute(
            "ALTER TABLE users ADD COLUMN billing_failure_count INTEGER NOT NULL DEFAULT 0"
        )

    # Plan prices in agorot (admin-editable via system_settings; SPEC §9).
    seeds = [
        ("plan_price_basic", "5000", "int", "Basic plan price in agorot (₪50)"),
        ("plan_price_advanced", "10000", "int", "Advanced plan price in agorot (₪100)"),
        ("plan_price_pro", "15000", "int", "Pro plan price in agorot (₪150)"),
        ("trial_days", "14", "int", "Trial length in days (card on file, charge on day 15)"),
    ]
    for key, value, vtype, desc in seeds:
        await db.execute(
            """INSERT OR IGNORE INTO system_settings (key, value, value_type, description)
               VALUES (?, ?, ?, ?)""",
            (key, value, vtype, desc),
        )
    await db.commit()
