"""RED-LINE SUITE — money is integer agorot only (ATP V1, TC-V1-MON-xx).

D-B10: every money amount is stored and handled as INTEGER agorot (ILS minor units).
NO floats in any money path — float drift on money is a correctness red line. This suite
guards it two ways: a STATIC lint over the money-handling files (no float() cast, no
Decimal/Fraction, no bare float literal), and RUNTIME checks that the agorot formatter,
plan prices, and money DB columns are all integer-exact.
"""
import re
from pathlib import Path

import aiosqlite
import pytest

import backend.config as cfg
from backend.core import stripe_service
from backend.core.email import format_agorot_ils

BACKEND = Path(__file__).resolve().parents[1]

# Files that touch money amounts.
_MONEY_FILES = [
    "core/stripe_service.py", "core/coupon_service.py", "core/referral_service.py",
    "core/invoice_provider.py", "api/billing.py", "api/plans.py",
]
# INTEGER agorot columns (table, column).
_MONEY_COLUMNS = [
    ("payment_transactions", "amount_ils"),
    ("billing_documents", "amount_agorot"),
    ("coupons", "amount_off_agorot"),
    ("coupon_redemptions", "amount_discounted_agorot"),
    ("referrals", "reward_amount_agorot"),
    ("referral_credits", "applied_amount_agorot"),
]

_FLOAT_LITERAL = re.compile(r"\b\d+\.\d+\b")


def _code_lines(rel: str):
    """Yield (lineno, code) for non-comment, non-docstring-ish lines."""
    text = (BACKEND / rel).read_text(encoding="utf-8")
    in_doc = False
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.count('"""') == 1:
            in_doc = not in_doc
            continue
        if in_doc or stripped.startswith("#") or stripped.startswith('"""'):
            continue
        yield i, line.split("#", 1)[0]  # drop trailing comment


# ── TC-V1-MON-01 — no float() cast in any money file ──────────────────────────
def test_no_float_cast_in_money_files():
    offenders = [f"{rel}:{i}" for rel in _MONEY_FILES for i, code in _code_lines(rel)
                 if "float(" in code]
    assert not offenders, f"float() cast in a money path: {offenders}"


# ── TC-V1-MON-02 — no Decimal / Fraction import (money is plain ints) ─────────
def test_no_decimal_or_fraction_import():
    for rel in _MONEY_FILES:
        text = (BACKEND / rel).read_text(encoding="utf-8")
        assert "import decimal" not in text and "from decimal" not in text
        assert "import fractions" not in text and "from fractions" not in text


# ── TC-V1-MON-03 — no bare float literal in money-handling code lines ──────────
def test_no_float_literal_in_money_files():
    offenders = []
    for rel in _MONEY_FILES:
        for i, code in _code_lines(rel):
            if _FLOAT_LITERAL.search(code):
                offenders.append(f"{rel}:{i}: {code.strip()}")
    assert not offenders, "float literal in a money path (agorot are ints):\n" + "\n".join(offenders)


# ── TC-V1-MON-04 — agorot formatter is integer-exact (divmod, no float math) ───
def test_format_agorot_ils_integer_exact():
    cases = {0: "0.00 ILS", 99: "0.99 ILS", 100: "1.00 ILS",
             5900: "59.00 ILS", 14900: "149.00 ILS", 100000: "1000.00 ILS"}
    for agorot, expected in cases.items():
        assert format_agorot_ils(agorot) == expected


# ── TC-V1-MON-05 — plan prices are integer agorot ──────────────────────────────
@pytest.mark.asyncio
async def test_plan_prices_are_int_agorot():
    from backend.migrations.run_migrations import apply_migrations
    await apply_migrations(cfg.DATABASE_URL)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        basic = await stripe_service.get_plan_price_agorot(db, "basic")
        pro = await stripe_service.get_plan_price_agorot(db, "pro")
    assert isinstance(basic, int) and isinstance(pro, int)
    assert basic == 5900 and pro == 14900  # PENDING-ACCOUNTANT values, agorot


# ── TC-V1-MON-06 — every money DB column is declared INTEGER ───────────────────
@pytest.mark.asyncio
async def test_money_columns_are_integer():
    from backend.migrations.run_migrations import apply_migrations
    await apply_migrations(cfg.DATABASE_URL)
    async with aiosqlite.connect(cfg.DATABASE_URL) as db:
        for table, col in _MONEY_COLUMNS:
            info = await db.execute_fetchall(f"PRAGMA table_info({table})")
            types = {r[1]: (r[2] or "").upper() for r in info}
            assert col in types, f"{table}.{col} missing"
            assert "INT" in types[col], f"{table}.{col} is {types[col]}, expected INTEGER agorot"
