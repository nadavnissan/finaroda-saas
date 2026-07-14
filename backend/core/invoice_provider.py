"""
Israeli tax-invoice layer (Stage 3R) — provider-agnostic document issuance.

Every successful charge (first + recurring, driven by Stripe webhooks) gets ONE legal
Israeli tax document. The document TYPE is config, not code (`system_settings.
billing_document_type`, accountant-driven; default `tax_invoice_receipt` for the
VAT-registered LTD). The PROVIDER that mints it is config too (`INVOICE_PROVIDER`).

⚠️ Stripe's own invoices are NOT Israeli tax documents and are never presented as such.
The tax document is issued here, by the configured provider, and its URL is what we email
and store.

Providers:
  * mock (default)      — offline, deterministic, zero network. Clearly marked so it is
                          never mistaken for a real fiscal document. Used in DEV/test and
                          whenever FEATURE_STRIPE_LIVE is false.
  * green_invoice /     — documented interface, NOT chosen yet. Each is a stub that raises
    icount / ezcount      NotImplementedError with the exact fields it will need, so the
                          seam is obvious when Nadav picks one. Only reached when
                          FEATURE_STRIPE_LIVE is true AND INVOICE_PROVIDER names it.

Amounts are agorot ints end-to-end (D-B10). Idempotent per transaction (one document per
charge, enforced by the UNIQUE index on billing_documents.transaction_id).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from backend import config

logger = logging.getLogger(__name__)

_DEFAULT_DOCUMENT_TYPE = "tax_invoice_receipt"
VALID_DOCUMENT_TYPES = ("tax_invoice_receipt", "invoice_receipt", "receipt")


# ── Provider interface ─────────────────────────────────────────────────────────
class InvoiceProvider:
    """Interface every tax-invoice provider implements.

    A provider turns a successful charge into a legal Israeli tax document and returns the
    stable identifiers we persist + email: (provider_document_id, document_number,
    document_url). Implementations must be idempotent-friendly (the caller already dedupes
    per transaction, so a provider only needs to create one document per call)."""

    name = "base"

    async def create_document(
        self, *, user_email: str, user_name: Optional[str], amount_agorot: int,
        document_type: str, transaction_id: int,
    ) -> dict:
        raise NotImplementedError


class MockInvoiceProvider(InvoiceProvider):
    """Offline provider — zero network. Deterministic id/number derived from the charge."""

    name = "mock"

    async def create_document(
        self, *, user_email: str, user_name: Optional[str], amount_agorot: int,
        document_type: str, transaction_id: int,
    ) -> dict:
        return {
            "provider_document_id": f"MOCK-DOC-{transaction_id}",
            "document_number": f"MOCK-{transaction_id:06d}",
            "document_url": f"{config.get_frontend_url()}/billing/documents/{transaction_id}?mock=1",
        }


class _UnconfiguredProvider(InvoiceProvider):
    """A real provider that has been named but not implemented/credentialed yet.

    Raising here (never in DEV/test — only when FEATURE_STRIPE_LIVE and this provider is
    selected) makes the missing integration loud instead of silently dropping documents.
    The caller catches it so the payment itself is never lost (doc stays pending)."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def create_document(self, **_) -> dict:
        raise NotImplementedError(
            f"Invoice provider '{self.name}' is not implemented. Choose one and wire it in "
            f"core/invoice_provider.py: it needs create_document(user_email, user_name, "
            f"amount_agorot, document_type, transaction_id) -> "
            f"{{provider_document_id, document_number, document_url}} and API credentials "
            f"(config + Railway). Candidates: Green Invoice, iCount, EZcount."
        )


_MOCK = MockInvoiceProvider()


def get_provider() -> InvoiceProvider:
    """Resolve the active provider. Offline (not live) ALWAYS uses the mock — zero network,
    tests stay green. Live uses the INVOICE_PROVIDER selection."""
    if not config.FEATURE_STRIPE_LIVE:
        return _MOCK
    name = config.INVOICE_PROVIDER
    if name == "mock":
        return _MOCK
    return _UnconfiguredProvider(name)


# ── Document type (config, accountant-driven) ──────────────────────────────────
async def get_document_type(db: aiosqlite.Connection) -> str:
    rows = await db.execute_fetchall(
        "SELECT value FROM system_settings WHERE key = 'billing_document_type'"
    )
    if rows and rows[0][0] in VALID_DOCUMENT_TYPES:
        return rows[0][0]
    return _DEFAULT_DOCUMENT_TYPE


async def get_document_for_transaction(
    db: aiosqlite.Connection, transaction_id: int
) -> Optional[dict]:
    """Return the existing billing document for a charge, or None."""
    rows = await db.execute_fetchall(
        """SELECT id, document_type, provider_document_id, document_number, document_url,
                  amount_agorot, currency, emailed_at
           FROM billing_documents WHERE transaction_id = ?""",
        (transaction_id,),
    )
    if not rows:
        return None
    r = rows[0]
    return {
        "id": r[0],
        "document_type": r[1],
        "provider_document_id": r[2],
        "document_number": r[3],
        "document_url": r[4],
        "amount_agorot": r[5],
        "currency": r[6],
        "emailed_at": r[7],
    }


async def issue_document(
    db: aiosqlite.Connection,
    user_id: int,
    transaction_id: int,
    amount_agorot: int,
    *,
    coupon_code: Optional[str] = None,
    referral_source: Optional[str] = None,
    commit: bool = True,
) -> dict:
    """
    Issue (or return the existing) tax document for a successful charge.

    Idempotent per transaction: a second call returns the document already recorded, so a
    duplicate webhook never issues two documents. Offline (not live) writes a deterministic
    MOCK record — zero network. On a live-provider failure the payment is never lost: the
    document row is written with empty provider ids (doc pending) and the error is logged.
    """
    existing = await get_document_for_transaction(db, transaction_id)
    if existing:
        return existing

    document_type = await get_document_type(db)
    urows = await db.execute_fetchall(
        "SELECT email, first_name FROM users WHERE internal_id = ?", (user_id,)
    )
    email = urows[0][0] if urows else ""
    first_name = urows[0][1] if urows else None

    # Forward-compat (D-B7): carry any coupon/referral recorded on the charge onto the
    # document row. Inert until Stage 4 (redesigned Stripe-native).
    tx_rows = await db.execute_fetchall(
        "SELECT coupon_code, referral_source FROM payment_transactions WHERE id = ?",
        (transaction_id,),
    )
    if tx_rows:
        coupon_code = coupon_code or tx_rows[0][0]
        referral_source = referral_source or tx_rows[0][1]

    provider = get_provider()
    try:
        created = await provider.create_document(
            user_email=email, user_name=first_name, amount_agorot=amount_agorot,
            document_type=document_type, transaction_id=transaction_id,
        )
        provider_document_id = created["provider_document_id"]
        document_number = created["document_number"]
        document_url = created["document_url"]
    except Exception as e:  # noqa: BLE001 — payment already succeeded; never lose it
        logger.error(
            "Invoice provider '%s' failed for tx=%s: %s", provider.name, transaction_id, e
        )
        provider_document_id = ""
        document_number = ""
        document_url = ""

    now = datetime.now(timezone.utc).isoformat()
    cur = await db.execute(
        """INSERT INTO billing_documents
           (user_id, transaction_id, document_type, provider_document_id, document_number,
            document_url, amount_agorot, currency, coupon_code, referral_source, issued_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'ILS', ?, ?, ?)""",
        (user_id, transaction_id, document_type, provider_document_id, document_number,
         document_url, amount_agorot, coupon_code, referral_source, now),
    )
    if commit:
        await db.commit()
    return {
        "id": cur.lastrowid,
        "document_type": document_type,
        "provider_document_id": provider_document_id,
        "document_number": document_number,
        "document_url": document_url,
        "amount_agorot": amount_agorot,
        "currency": "ILS",
        "emailed_at": None,
    }


async def mark_emailed(db: aiosqlite.Connection, document_id: int, commit: bool = True) -> None:
    """Stamp the document as emailed (so a re-run does not re-send the receipt)."""
    await db.execute(
        "UPDATE billing_documents SET emailed_at = ? WHERE id = ? AND emailed_at IS NULL",
        (datetime.now(timezone.utc).isoformat(), document_id),
    )
    if commit:
        await db.commit()
