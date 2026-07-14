"""Stage 4 admin console API — coupons + referrals. Admin-role gated (403 for non-admins);
every mutation is audited to admin_events with the admin id. No em dashes in copy."""
import json

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException

from backend.core import coupon_service, referral_service
from backend.core.auth import require_admin
from backend.core.database import get_db_connection
from backend.models.admin import CouponCreate, ReferralVoid
from backend.models.auth import CurrentUser

router = APIRouter(prefix="/api/admin", tags=["admin-promotions"])
log = structlog.get_logger(__name__)


async def _audit(db, admin_id: int, event_type: str, target_user_id, details: dict) -> None:
    await db.execute(
        """INSERT INTO admin_events (admin_id, event_type, target_user_id, details_json)
           VALUES (?, ?, ?, ?)""",
        (admin_id, event_type, target_user_id, json.dumps(details)),
    )


# ── Coupons ───────────────────────────────────────────────────────────────────
@router.get("/coupons")
async def list_coupons(
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    return {"coupons": await coupon_service.list_coupons(db)}


@router.post("/coupons")
async def create_coupon(
    body: CouponCreate,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    coupon = await coupon_service.create_coupon(
        db,
        admin_id=admin.internal_id,
        code=body.code,
        discount_type=body.discount_type,
        percent_off=body.percent_off,
        amount_off_agorot=body.amount_off_agorot,
        max_redemptions=body.max_redemptions,
        expires_at=body.expires_at,
        plan_restriction=body.plan_restriction,
        description=body.description,
    )
    await _audit(db, admin.internal_id, "coupon_create", None,
                 {"coupon_id": coupon.get("id"), "code": coupon.get("code")})
    await db.commit()
    return {"ok": True, "coupon": coupon}


@router.post("/coupons/{coupon_id}/deactivate")
async def deactivate_coupon(
    coupon_id: int,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    coupon = await coupon_service.deactivate_coupon(db, coupon_id)
    await _audit(db, admin.internal_id, "coupon_deactivate", None,
                 {"coupon_id": coupon_id, "code": coupon.get("code")})
    await db.commit()
    return {"ok": True, "coupon": coupon}


# ── Referrals ─────────────────────────────────────────────────────────────────
@router.get("/referrals")
async def list_referrals(
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Referrals list (D-S10): referrer, referred, status, reward state."""
    rows = await db.execute_fetchall(
        """SELECT r.id, r.status, r.reward_type, r.reward_amount_agorot, r.reward_granted_at,
                  r.created_at, ur.internal_id AS referrer_id, ur.email AS referrer_email,
                  ud.internal_id AS referred_id, ud.email AS referred_email
             FROM referrals r
             JOIN users ur ON ur.internal_id = r.referrer_id
             JOIN users ud ON ud.internal_id = r.referred_id
            ORDER BY r.created_at DESC, r.id DESC LIMIT 500"""
    )
    counts_rows = await db.execute_fetchall(
        "SELECT status, COUNT(*) FROM referrals GROUP BY status"
    )
    counts = {r[0]: r[1] for r in counts_rows}
    banked = (await db.execute_fetchall(
        "SELECT COUNT(*) FROM referral_credits WHERE status = 'banked'"))[0][0]
    return {"referrals": [dict(r) for r in rows], "counts": counts, "credits_banked": banked}


@router.post("/referrals/{referral_id}/void")
async def void_referral(
    referral_id: int,
    body: ReferralVoid,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    result = await referral_service.void_referral(db, referral_id, admin.internal_id)
    await _audit(db, admin.internal_id, "referral_void", None,
                 {"referral_id": referral_id, "note": body.note, **result})
    await db.commit()
    return {"ok": True, **result}
