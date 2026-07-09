"""Migration 022 — add 'trial_ended_to_free' to subscription_events.event_type.

D1 change order (2026-07-09): a no-card trial that lapses is moved to **Free**
(never expired/blocked, never charged). expire_trials logs this transition, which
needs a dedicated event type. SQLite can't ALTER a CHECK constraint, so the table is
rebuilt with the extended allowed set; all rows/columns/indexes are preserved.
"""
import aiosqlite

MIGRATION_ID = "022_subscription_events_trial_to_free"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS subscription_events_new (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL REFERENCES users(internal_id),
            event_type     VARCHAR(40) NOT NULL CHECK (event_type IN (
                               'trial_started','trial_ended_converted','trial_ended_expired',
                               'trial_ended_to_free',
                               'subscription_started','subscription_renewed',
                               'subscription_cancelled_user',
                               'subscription_cancelled_failed_payment',
                               'subscription_reactivated',
                               'plan_upgraded','plan_downgraded','refund_issued')),
            tier_before    TEXT,
            tier_after     TEXT,
            transaction_id INTEGER REFERENCES payment_transactions(id),
            metadata_json  TEXT,
            created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        """INSERT INTO subscription_events_new
           SELECT id, user_id, event_type, tier_before, tier_after,
                  transaction_id, metadata_json, created_at
           FROM subscription_events"""
    )
    await db.execute("DROP TABLE subscription_events")
    await db.execute("ALTER TABLE subscription_events_new RENAME TO subscription_events")
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_sub_events_user ON subscription_events(user_id, created_at DESC)"
    )
    await db.commit()
