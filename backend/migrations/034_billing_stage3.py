"""Migration 034 — Stage 3 live-billing spine (additive, non-destructive).

Adds the pieces the full billing loop needs without touching any existing row:

1. billing_documents        — one receipt/invoice-receipt record per successful
                              charge (D-B3). Amounts in agorot. Document type is
                              config-driven (system_settings billing_document_type).
2. payment_transactions +=  — coupon_code, referral_source (D-B7 forward-compat for
                              Stage 4; nullable + inert, no logic reads them yet) and
                              kind ('first' | 'recurring') to label a charge.
3. users +=                 — dunning_next_retry_at, the +24h/+72h retry clock (D-B5).
                              billing_failure_count (mig 019) stays the attempt counter.
4. subscription_events      — CHECK rebuilt (SQLite can't ALTER a CHECK) to allow the
                              Stage-3 event types. All rows/columns/indexes preserved.
5. system_settings          — billing_document_type seed (admin-editable, default
                              'receipt'; the accountant picks receipt vs invoice_receipt).

Money stays agorot ints end-to-end (D-B10). No live terminal is wired (S1/AC8).
"""
import aiosqlite

MIGRATION_ID = "034_billing_stage3"


async def up(db: aiosqlite.Connection) -> None:
    # ── 1. billing_documents ──────────────────────────────────────────────────
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS billing_documents (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             INTEGER NOT NULL REFERENCES users(internal_id),
            transaction_id      INTEGER REFERENCES payment_transactions(id),
            document_type       TEXT NOT NULL,          -- receipt | invoice_receipt (config)
            cardcom_document_id TEXT,                   -- Cardcom's doc id (or mock id offline)
            document_number     TEXT,                   -- human-facing running number
            document_url        TEXT,                   -- link / PDF url emailed to the user
            amount_agorot       INTEGER NOT NULL,       -- agorot, never a float (D-B10)
            currency            TEXT NOT NULL DEFAULT 'ILS',
            coupon_code         TEXT,                   -- D-B7 forward-compat (inert)
            referral_source     TEXT,                   -- D-B7 forward-compat (inert)
            issued_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
            emailed_at          DATETIME
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_billing_docs_user ON billing_documents(user_id, issued_at DESC)"
    )
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_docs_tx ON billing_documents(transaction_id)"
    )

    # ── 2. payment_transactions: coupon/referral (inert) + kind ───────────────
    tx_cols = [r[1] for r in await db.execute_fetchall("PRAGMA table_info(payment_transactions)")]
    if "coupon_code" not in tx_cols:
        await db.execute("ALTER TABLE payment_transactions ADD COLUMN coupon_code TEXT")
    if "referral_source" not in tx_cols:
        await db.execute("ALTER TABLE payment_transactions ADD COLUMN referral_source TEXT")
    if "kind" not in tx_cols:
        await db.execute(
            "ALTER TABLE payment_transactions ADD COLUMN kind TEXT NOT NULL DEFAULT 'first'"
        )

    # ── 3. users: dunning retry clock ─────────────────────────────────────────
    user_cols = [r[1] for r in await db.execute_fetchall("PRAGMA table_info(users)")]
    if "dunning_next_retry_at" not in user_cols:
        await db.execute("ALTER TABLE users ADD COLUMN dunning_next_retry_at DATETIME")

    # ── 4. subscription_events: extend the event_type CHECK ───────────────────
    # SQLite cannot ALTER a CHECK, so rebuild the table with the extended allowed
    # set (same non-destructive copy pattern as mig 022). All columns preserved.
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS subscription_events_new (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL REFERENCES users(internal_id),
            event_type     VARCHAR(48) NOT NULL CHECK (event_type IN (
                               'trial_started','trial_ended_converted','trial_ended_expired',
                               'trial_ended_to_free',
                               'subscription_started','subscription_renewed',
                               'subscription_cancelled_user',
                               'subscription_cancelled_failed_payment',
                               'subscription_reactivated',
                               'plan_upgraded','plan_downgraded','refund_issued',
                               -- Stage 3 (live billing) additions:
                               'payment_document_issued',
                               'subscription_past_due',
                               'dunning_retry_scheduled',
                               'subscription_expired_dunning',
                               'subscription_dropped_to_free')),
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

    # ── 5. billing_document_type setting (accountant-driven; default receipt) ──
    await db.execute(
        """INSERT OR IGNORE INTO system_settings (key, value, value_type, description)
           VALUES ('billing_document_type', 'receipt', 'string',
                   'Cardcom billing document per charge: receipt | invoice_receipt (accountant-driven)')""",
    )
    await db.commit()
