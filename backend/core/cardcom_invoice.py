"""
Billing documents — receipt / invoice-receipt per successful charge (D-B3).

Every successful charge (first + recurring) gets a document. The type is CONFIG, not
code (`system_settings.billing_document_type`, accountant-driven: `receipt` vs
`invoice_receipt`), so the accountant's choice never needs a code change.

S3 outcome: no Cardcom account/invoice-module settings exist offline, so the live path
(Cardcom's Documents API) is scaffolded but gated behind FEATURE_CARDCOM_LIVE. Until a
terminal + invoice module are provisioned, `issue_document` writes a MOCK document
record with zero network — the whole flow (issue -> persist -> email) stays testable and
green. Real document type / osek settings are listed for Nadav in SESSION_HANDOFF.

Amounts are agorot ints end-to-end (D-B10). Idempotent per transaction (one document
per charge, enforced by the UNIQUE index on billing_documents.transaction_id).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import aiosqlite
import httpx

from backend import config

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0
_DEFAULT_DOCUMENT_TYPE = "receipt"
VALID_DOCUMENT_TYPES = ("receipt", "invoice_receipt")


async def get_document_type(db: aiosqlite.Connection) -> str:
    """Configured billing document type (admin-editable). Falls back to 'receipt'."""
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
        """SELECT id, document_type, cardcom_document_id, document_number, document_url,
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
        "cardcom_document_id": r[2],
        "document_number": r[3],
        "document_url": r[4],
        "amount_agorot": r[5],
        "currency": r[6],
        "emailed_at": r[7],
    }


async def _create_cardcom_document(
    user_email: str, user_name: Optional[str], amount_agorot: int, document_type: str
) -> dict:
    """
    LIVE path: create a document via Cardcom's Documents API. Only reached when
    FEATURE_CARDCOM_LIVE is True (never in tests). Returns {cardcom_document_id,
    document_number, document_url}. On any failure raises — the caller degrades to a
    charge-succeeded-doc-pending state rather than losing the payment.
    """
    payload = {
        "TerminalNumber": config.CARDCOM_TERMINAL_ID,
        "ApiName": config.CARDCOM_API_NAME,
        "ApiPassword": config.CARDCOM_API_PASSWORD,
        "DocumentTypeToCreate": document_type,
        "Customer": {"Name": user_name or user_email, "Email": user_email},
        "TotalAmount": amount_agorot,
    }
    url = f"{config.CARDCOM_BASE_URL}/Documents/Create"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    return {
        "cardcom_document_id": str(data.get("DocumentId", "")),
        "document_number": str(data.get("DocumentNumber", "")),
        "document_url": data.get("DocumentUrl", ""),
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
    Issue (or return the existing) billing document for a successful charge.

    Idempotent per transaction: a second call returns the document already recorded,
    so a cron double-run or a webhook retry never issues two documents. Offline (not
    live) it writes a deterministic MOCK record — zero network — so tests stay green.
    Returns the document dict (see get_document_for_transaction).
    """
    existing = await get_document_for_transaction(db, transaction_id)
    if existing:
        return existing

    document_type = await get_document_type(db)
    urows = await db.execute_fetchall(
        "SELECT email, first_name, coupon_code, referral_source FROM users u "
        "LEFT JOIN payment_transactions pt ON pt.id = ? WHERE u.internal_id = ?",
        (transaction_id, user_id),
    )
    email = urows[0][0] if urows else ""
    first_name = urows[0][1] if urows else None
    # Forward-compat (D-B7): carry any coupon/referral recorded on the charge onto the
    # document row. Inert in Stage 3 (no discount math), wired in Stage 4.
    tx_rows = await db.execute_fetchall(
        "SELECT coupon_code, referral_source FROM payment_transactions WHERE id = ?",
        (transaction_id,),
    )
    if tx_rows:
        coupon_code = coupon_code or tx_rows[0][0]
        referral_source = referral_source or tx_rows[0][1]

    if config.FEATURE_CARDCOM_LIVE:
        try:
            created = await _create_cardcom_document(email, first_name, amount_agorot, document_type)
            cardcom_document_id = created["cardcom_document_id"]
            document_number = created["document_number"]
            document_url = created["document_url"]
        except Exception as e:  # noqa: BLE001 — payment already succeeded; do not lose it
            logger.error("Cardcom document creation failed tx=%s: %s", transaction_id, e)
            cardcom_document_id = ""
            document_number = ""
            document_url = ""
    else:
        # MOCK: deterministic, offline. Clearly marked so it is never mistaken for a
        # real fiscal document. Number derives from the transaction id (stable, unique).
        cardcom_document_id = f"MOCK-DOC-{transaction_id}"
        document_number = f"MOCK-{transaction_id:06d}"
        document_url = f"{config.get_frontend_url()}/billing/documents/{transaction_id}?mock=1"

    now = datetime.now(timezone.utc).isoformat()
    cur = await db.execute(
        """INSERT INTO billing_documents
           (user_id, transaction_id, document_type, cardcom_document_id, document_number,
            document_url, amount_agorot, currency, coupon_code, referral_source, issued_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'ILS', ?, ?, ?)""",
        (user_id, transaction_id, document_type, cardcom_document_id, document_number,
         document_url, amount_agorot, coupon_code, referral_source, now),
    )
    if commit:
        await db.commit()
    return {
        "id": cur.lastrowid,
        "document_type": document_type,
        "cardcom_document_id": cardcom_document_id,
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
