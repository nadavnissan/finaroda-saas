"""Migration 003 — coupons + coupon_applications (modern admin variant, audit 020).

Resolves the legacy db.py vs migration-020 `coupons` collision in favour of the
admin-panel variant (discount_pct, created_by, applications join table).
"""
import aiosqlite

MIGRATION_ID = "003_coupons"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS coupons (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            code         TEXT UNIQUE NOT NULL,
            discount_pct INTEGER NOT NULL CHECK (discount_pct > 0 AND discount_pct <= 100),
            description  TEXT,
            expires_at   DATETIME,
            max_uses     INTEGER,
            uses_count   INTEGER DEFAULT 0,
            is_active    INTEGER DEFAULT 1,
            created_by   INTEGER NOT NULL REFERENCES users(internal_id),
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS coupon_applications (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            coupon_id        INTEGER NOT NULL REFERENCES coupons(id),
            user_id          INTEGER NOT NULL REFERENCES users(internal_id),
            applied_by_admin INTEGER NOT NULL REFERENCES users(internal_id),
            applied_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (coupon_id, user_id)
        )
        """
    )
    await db.commit()
