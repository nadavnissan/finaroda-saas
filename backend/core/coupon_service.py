"""
Coupons — Stripe-native (Stage 4, part A).

A coupon is a Stripe **Coupon** (percent OR fixed-amount ILS, duration 'once' = first
charge only, D-S1) with an attached Stripe **Promotion Code** (the user-facing code
string). Admin creates/deactivates them from OUR admin, which drives the Stripe API; we
keep a mirror row per coupon (code, params, stripe ids, active, redeemed_count) so listing
and audit never need a Stripe round-trip (D-S2). Redemptions are synced from webhooks.

Plan restriction mechanism (D-S1, reported): enforced OUR-SIDE via
`validate_coupon_for_plan`, called before the Checkout Session is created when a promotion
code is supplied to our checkout endpoint (AC2). We build a per-plan session anyway, so
this fully covers plan-restricted codes. We do NOT use Stripe Coupon `applies_to` because
that is product-scoped and we track only per-plan Price ids, not Product ids — our-side
validation is the single, testable enforcement point. Unrestricted codes ride Stripe's
hosted promotion-code field (allow_promotion_codes=true, D-S3); Stripe itself enforces
max_redemptions + expiry natively, and we keep our mirror count in sync from the webhook.

DEV mode (FEATURE_STRIPE_LIVE false or no key): deterministic fake Stripe ids, zero
network — the same pattern as checkout. Amounts are agorot ints (D-B10). No XP anywhere.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import aiosqlite
from fastapi import HTTPException

from backend import config
from backend.core import stripe_service
from backend.core.stripe_service import VALID_PLANS

logger = logging.getLogger(__name__)

VALID_DISCOUNT_TYPES = ("percent", "fixed")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_unix(expires_at: Optional[str]) -> Optional[int]:
    if not expires_at:
        return None
    try:
        dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None


def _row_to_dict(r) -> dict:
    return {
        "id": r[0], "code": r[1], "stripe_coupon_id": r[2],
        "stripe_promotion_code_id": r[3], "discount_type": r[4],
        "percent_off": r[5], "amount_off_agorot": r[6], "duration": r[7],
        "plan_restriction": r[8], "max_redemptions": r[9], "redeemed_count": r[10],
        "expires_at": r[11], "active": bool(r[12]), "description": r[13],
        "created_by": r[14], "created_at": r[15],
    }


_SELECT = (
    "SELECT id, code, stripe_coupon_id, stripe_promotion_code_id, discount_type, "
    "percent_off, amount_off_agorot, duration, plan_restriction, max_redemptions, "
    "redeemed_count, expires_at, active, description, created_by, created_at FROM coupons"
)


async def get_coupon_by_code(db: aiosqlite.Connection, code: str) -> Optional[dict]:
    rows = await db.execute_fetchall(f"{_SELECT} WHERE code = ?", (code,))
    return _row_to_dict(rows[0]) if rows else None


async def get_coupon_by_promotion_code_id(
    db: aiosqlite.Connection, promo_code_id: str
) -> Optional[dict]:
    rows = await db.execute_fetchall(
        f"{_SELECT} WHERE stripe_promotion_code_id = ?", (promo_code_id,)
    )
    return _row_to_dict(rows[0]) if rows else None


async def list_coupons(db: aiosqlite.Connection) -> list[dict]:
    rows = await db.execute_fetchall(f"{_SELECT} ORDER BY created_at DESC, id DESC")
    return [_row_to_dict(r) for r in rows]


# ── Create (drives Stripe, then mirrors) ───────────────────────────────────────
async def create_coupon(
    db: aiosqlite.Connection,
    *,
    admin_id: int,
    code: str,
    discount_type: str,
    percent_off: Optional[int] = None,
    amount_off_agorot: Optional[int] = None,
    max_redemptions: Optional[int] = None,
    expires_at: Optional[str] = None,
    plan_restriction: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Create a Stripe Coupon + Promotion Code (or DEV fakes) and mirror the row.

    Validates params, refuses a duplicate code (409). Percent coupons need 1..100;
    fixed coupons need a positive agorot amount. duration is always 'once' (first charge
    only, D-S1). Never raises past a Stripe error without persisting nothing."""
    code = (code or "").strip().upper()
    if not code:
        raise HTTPException(400, "Coupon code is required")
    if discount_type not in VALID_DISCOUNT_TYPES:
        raise HTTPException(400, f"Invalid discount_type: {discount_type}")
    if discount_type == "percent":
        if not percent_off or not (1 <= int(percent_off) <= 100):
            raise HTTPException(400, "percent_off must be 1..100")
        percent_off = int(percent_off)
        amount_off_agorot = None
    else:
        if not amount_off_agorot or int(amount_off_agorot) <= 0:
            raise HTTPException(400, "amount_off_agorot must be a positive integer (agorot)")
        amount_off_agorot = int(amount_off_agorot)
        percent_off = None
    if plan_restriction is not None and plan_restriction not in VALID_PLANS:
        raise HTTPException(400, f"Invalid plan_restriction: {plan_restriction}")
    if max_redemptions is not None and int(max_redemptions) <= 0:
        raise HTTPException(400, "max_redemptions must be a positive integer or omitted")

    if await get_coupon_by_code(db, code):
        raise HTTPException(409, f"Coupon code already exists: {code}")

    # ── Drive Stripe (or fake in DEV) ──────────────────────────────────────────
    if stripe_service._dev_mode():
        stripe_coupon_id = f"coupon_dev_{code}"
        stripe_promo_id = f"promo_dev_{code}"
    else:
        stripe = stripe_service._stripe()
        coupon_kwargs: dict = {"duration": "once", "name": description or code}
        if discount_type == "percent":
            coupon_kwargs["percent_off"] = percent_off
        else:
            coupon_kwargs["amount_off"] = amount_off_agorot  # agorot = ILS minor unit
            coupon_kwargs["currency"] = "ils"
        try:
            scoupon = stripe.Coupon.create(**coupon_kwargs)
            promo_kwargs: dict = {
                "coupon": scoupon["id"] if isinstance(scoupon, dict) else scoupon.id,
                "code": code,
                "active": True,
            }
            if max_redemptions is not None:
                promo_kwargs["max_redemptions"] = int(max_redemptions)
            exp_unix = _to_unix(expires_at)
            if exp_unix is not None:
                promo_kwargs["expires_at"] = exp_unix
            spromo = stripe.PromotionCode.create(**promo_kwargs)
        except Exception as e:  # noqa: BLE001 — surface, persist nothing
            logger.error("Stripe coupon create failed code=%s: %s", code, e)
            raise HTTPException(503, "Payment gateway error creating coupon")
        stripe_coupon_id = scoupon["id"] if isinstance(scoupon, dict) else scoupon.id
        stripe_promo_id = spromo["id"] if isinstance(spromo, dict) else spromo.id

    cur = await db.execute(
        """INSERT INTO coupons
           (code, stripe_coupon_id, stripe_promotion_code_id, discount_type, percent_off,
            amount_off_agorot, duration, plan_restriction, max_redemptions, redeemed_count,
            active, description, created_by, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'once', ?, ?, 0, 1, ?, ?, ?)""",
        (code, stripe_coupon_id, stripe_promo_id, discount_type, percent_off,
         amount_off_agorot, plan_restriction, max_redemptions, description, admin_id, _now_iso()),
    )
    if expires_at:
        await db.execute("UPDATE coupons SET expires_at = ? WHERE id = ?", (expires_at, cur.lastrowid))
    await db.commit()
    return (await get_coupon_by_code(db, code)) or {}


async def deactivate_coupon(db: aiosqlite.Connection, coupon_id: int) -> dict:
    """Deactivate a coupon: flip the Stripe Promotion Code inactive (no new redemptions)
    and our mirror active=0. Idempotent; an already-inactive coupon is a no-op success."""
    rows = await db.execute_fetchall(f"{_SELECT} WHERE id = ?", (coupon_id,))
    if not rows:
        raise HTTPException(404, "Coupon not found")
    coupon = _row_to_dict(rows[0])

    if not stripe_service._dev_mode() and coupon["stripe_promotion_code_id"]:
        try:
            stripe_service._stripe().PromotionCode.modify(coupon["stripe_promotion_code_id"], active=False)
        except Exception as e:  # noqa: BLE001 — reconcile locally regardless
            logger.error("Stripe promo deactivate failed id=%s: %s", coupon_id, e)

    await db.execute("UPDATE coupons SET active = 0 WHERE id = ?", (coupon_id,))
    await db.commit()
    return (await get_coupon_by_code(db, coupon["code"])) or {}


# ── Validation (our-side plan restriction + status, D-S1/AC2) ──────────────────
async def validate_coupon_for_plan(db: aiosqlite.Connection, code: str, plan: str) -> dict:
    """Validate a coupon code for a specific plan BEFORE creating a Checkout Session.

    Returns {"valid": bool, "reason": str|None, "coupon": dict|None}. Reasons:
    NOT_FOUND | INACTIVE | EXPIRED | MAX_REDEEMED | WRONG_PLAN. Enforces the plan
    restriction our-side (the single enforcement point, D-S1)."""
    coupon = await get_coupon_by_code(db, (code or "").strip().upper())
    if not coupon:
        return {"valid": False, "reason": "NOT_FOUND", "coupon": None}
    if not coupon["active"]:
        return {"valid": False, "reason": "INACTIVE", "coupon": coupon}
    if coupon["expires_at"]:
        exp = _to_unix(coupon["expires_at"])
        if exp is not None and exp < int(datetime.now(timezone.utc).timestamp()):
            return {"valid": False, "reason": "EXPIRED", "coupon": coupon}
    if (coupon["max_redemptions"] is not None
            and coupon["redeemed_count"] >= coupon["max_redemptions"]):
        return {"valid": False, "reason": "MAX_REDEEMED", "coupon": coupon}
    if coupon["plan_restriction"] and coupon["plan_restriction"] != plan:
        return {"valid": False, "reason": "WRONG_PLAN", "coupon": coupon}
    return {"valid": True, "reason": None, "coupon": coupon}


# ── Redemption sync (from checkout webhook, AC3) ───────────────────────────────
async def record_redemption(
    db: aiosqlite.Connection,
    *,
    coupon: dict,
    user_id: int,
    transaction_id: Optional[int],
    amount_discounted_agorot: Optional[int],
    promotion_code: Optional[str],
    commit: bool = True,
) -> bool:
    """Record one redemption and keep the mirror count in sync (AC3). Idempotent per
    (coupon, user): a duplicate webhook does not double-count. Returns True when a NEW
    redemption row was written (count incremented), False when it was already recorded."""
    cur = await db.execute(
        """INSERT OR IGNORE INTO coupon_redemptions
           (coupon_id, user_id, promotion_code, transaction_id, amount_discounted_agorot, redeemed_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (coupon["id"], user_id, promotion_code, transaction_id,
         amount_discounted_agorot, _now_iso()),
    )
    new_redemption = cur.rowcount == 1
    if new_redemption:
        await db.execute(
            "UPDATE coupons SET redeemed_count = redeemed_count + 1 WHERE id = ?",
            (coupon["id"],),
        )
    if commit:
        await db.commit()
    return new_redemption
