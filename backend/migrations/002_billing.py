"""Migration 002 — billing: payment_transactions + subscription_events.

Modern Cardcom payment ledger (consolidates legacy db.py `payments`/`subscriptions`
into the single internal_id-keyed model from audit migrations 024/025).
"""
import aiosqlite

MIGRATION_ID = "002_billing"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id               INTEGER NOT NULL REFERENCES users(internal_id),
            cardcom_tx_id         TEXT UNIQUE,
            amount_ils            INTEGER NOT NULL,          -- agorot (avoids float)
            currency              VARCHAR(3) NOT NULL DEFAULT 'ILS',
            status                VARCHAR(20) NOT NULL CHECK (status IN
                                  ('pending','success','failed','refunded','disputed')),
            cardcom_response_json TEXT,
            failure_reason        TEXT,
            created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at          DATETIME
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_payment_tx_user ON payment_transactions(user_id, created_at DESC)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_payment_tx_status ON payment_transactions(status, created_at DESC)"
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS subscription_events (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL REFERENCES users(internal_id),
            event_type     VARCHAR(40) NOT NULL CHECK (event_type IN (
                               'trial_started','trial_ended_converted','trial_ended_expired',
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
        "CREATE INDEX IF NOT EXISTS idx_sub_events_user ON subscription_events(user_id, created_at DESC)"
    )
    await db.commit()
