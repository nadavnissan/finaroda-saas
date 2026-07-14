"""Migration 035 — PSP switch Cardcom -> Stripe (Stage 3R). Non-destructive.

Repurposes the Cardcom-named columns to their Stripe equivalents (no data can exist —
Cardcom was never live, S1/AC8) and adds the pieces the webhook loop needs:

1. users            — cardcom_token RENAMEd to stripe_customer_id (the PSP's handle for
                      this user); + stripe_subscription_id, card_last4, card_expiry.
2. payment_transactions — cardcom_tx_id RENAMEd to stripe_reference (session / invoice /
                      payment-intent id, still UNIQUE); cardcom_response_json RENAMEd to
                      provider_response_json.
3. billing_documents — cardcom_document_id RENAMEd to provider_document_id (the invoice
                      provider's id, or a MOCK id offline).
4. processed_webhook_events — NEW. Stripe event-id idempotency ledger (AC3): a duplicate
                      event id is a no-op.
5. system_settings  — billing_document_type default moves receipt -> tax_invoice_receipt
                      (the operating entity is now a VAT-registered Israeli LTD; the
                      Israeli tax document is a tax-invoice-receipt). Only updated if the
                      value is still the mig-034 default (an admin's explicit choice wins).

SQLite >= 3.25 (RENAME COLUMN) — the runtime bundles 3.49. Each step is guarded so a
re-apply on a partially-migrated schema is safe. Money stays agorot ints (D-B10).
"""
import aiosqlite

MIGRATION_ID = "035_stripe_migration"


async def _cols(db: aiosqlite.Connection, table: str) -> list[str]:
    return [r[1] for r in await db.execute_fetchall(f"PRAGMA table_info({table})")]


async def _rename(db: aiosqlite.Connection, table: str, old: str, new: str) -> None:
    """Rename old->new only when old exists and new does not (idempotent)."""
    cols = await _cols(db, table)
    if old in cols and new not in cols:
        await db.execute(f"ALTER TABLE {table} RENAME COLUMN {old} TO {new}")


async def _add(db: aiosqlite.Connection, table: str, col: str, decl: str) -> None:
    if col not in await _cols(db, table):
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


async def up(db: aiosqlite.Connection) -> None:
    # ── 1. users: Cardcom -> Stripe handles ───────────────────────────────────
    await _rename(db, "users", "cardcom_token", "stripe_customer_id")
    await _add(db, "users", "stripe_subscription_id", "TEXT")
    await _add(db, "users", "card_last4", "TEXT")
    await _add(db, "users", "card_expiry", "TEXT")

    # ── 2. payment_transactions: Cardcom -> Stripe references ──────────────────
    # cardcom_tx_id carried a UNIQUE constraint; RENAME COLUMN preserves it.
    await _rename(db, "payment_transactions", "cardcom_tx_id", "stripe_reference")
    await _rename(db, "payment_transactions", "cardcom_response_json", "provider_response_json")

    # ── 3. billing_documents: provider-agnostic document id ────────────────────
    await _rename(db, "billing_documents", "cardcom_document_id", "provider_document_id")

    # ── 4. processed_webhook_events: Stripe event-id idempotency (AC3) ─────────
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_webhook_events (
            event_id     TEXT PRIMARY KEY,      -- Stripe event id (evt_...)
            event_type   TEXT,
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # ── 5. Israeli tax document type (VAT-registered LTD) ─────────────────────
    # Only flip the mig-034 default; never override an admin's explicit selection.
    await db.execute(
        """UPDATE system_settings SET value = 'tax_invoice_receipt'
           WHERE key = 'billing_document_type' AND value = 'receipt'"""
    )
    # Refresh the description to reflect the Stripe/LTD reality.
    await db.execute(
        "UPDATE system_settings SET description = "
        "'Israeli tax document per charge: tax_invoice_receipt | invoice_receipt | receipt "
        "(accountant-driven; issued by INVOICE_PROVIDER)' "
        "WHERE key = 'billing_document_type'"
    )
    await db.commit()
