"""Migration 004 — referrals (modern REST, monetary discount reward; SPEC §3.2/§9).

Rebuilt from the legacy token-based, Telegram-coupled engine into a clean REST model:
reward = 50% discount for one month to the referrer, granted ONLY after the referred
user completes 3 consecutive paid months, AND an admin approves (anti-"tourist" gate).
No tokens. No Telegram.
"""
import aiosqlite

MIGRATION_ID = "004_referral"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS referrals (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id            INTEGER NOT NULL REFERENCES users(internal_id),
            referred_id            INTEGER NOT NULL REFERENCES users(internal_id),
            referral_code          TEXT NOT NULL,
            -- lifecycle of the referral toward the reward:
            status                 TEXT NOT NULL DEFAULT 'registered'
                                   CHECK (status IN
                                          ('registered','qualifying','eligible',
                                           'approved','rewarded','rejected')),
            referred_paid_months   INTEGER NOT NULL DEFAULT 0,  -- consecutive paid months
            eligible_at            DATETIME,    -- when 3-month threshold was reached
            -- admin control gate (SPEC §9 — required before granting the discount):
            approved_by_admin      INTEGER REFERENCES users(internal_id),
            approved_at            DATETIME,
            reward_discount_pct    INTEGER DEFAULT 50,
            reward_granted_at      DATETIME,
            created_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (referred_id)   -- a user can be referred only once
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id, status)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_referrals_status ON referrals(status, created_at DESC)"
    )
    await db.commit()
