"""
Referral — permanent code + one-free-month reward, Stripe-native (Stage 4, part B).

Founder's ruling (fixed): a referred friend's FIRST paid charge earns the referrer ONE
FREE MONTH. XP is involved in NO direction (D / AC8 — this module never touches xp_events).

Mechanics:
  * Every user has a permanent referral code (generated lazily). /r/<code> stores the code
    client-side; signup binds `referred_by_user_id` + a `referrals` row ONCE, immutable
    (D-S6). Self-referral is blocked by both user id and email.
  * Reward trigger (D-S7): the referred user's first `invoice.paid` with amount>0. A
    100%-coupon first month (amount 0) does NOT trigger — the reward fires on their first
    genuinely PAID invoice, which may be month 2. Exactly one reward per referred user,
    idempotent under duplicate/out-of-order webhooks (a single bound->rewarded transition
    gates it).
  * Reward form (D-S5): if the referrer is on a paid Stripe subscription, a customer
    balance credit equal to one month of THEIR current plan (Customer.create_balance_
    transaction, negative agorot ILS) that Stripe auto-consumes on upcoming invoices. If
    the referrer is trial/free (no Stripe customer / no paid sub), the credit is BANKED in
    referral_credits and resolved to one month of whatever plan they later buy, applied on
    their first paid checkout. Credits stack and Stripe consumes them across invoices.

DEV mode (no live Stripe): the balance-transaction call is skipped and a deterministic fake
id is recorded — zero network, same pattern as checkout. Amounts are agorot ints (D-B10).
"""
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from backend import config
from backend.core import notifications as notif
from backend.core import stripe_service
from backend.core.email import (
    send_referral_credit_applied_email,
    send_referral_reward_email,
)

logger = logging.getLogger(__name__)

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous 0/O/1/I
_CODE_LEN = 8
# A referrer holding a real paid Stripe subscription gets the credit immediately; any other
# state (trial/free/none/expired) banks it until they convert.
_PAYING_STATES = ("active", "past_due", "cancelled")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cbt_dev_id(kind: str, ref: int) -> str:
    return f"cbt_dev_{kind}_{ref}"


# ── Permanent code ─────────────────────────────────────────────────────────────
async def get_or_create_code(db: aiosqlite.Connection, user_id: int) -> str:
    """Return the user's permanent referral code, generating a unique one on first need."""
    rows = await db.execute_fetchall(
        "SELECT referral_code FROM users WHERE internal_id = ?", (user_id,)
    )
    if rows and rows[0][0]:
        return rows[0][0]
    for _ in range(12):
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LEN))
        exists = await db.execute_fetchall(
            "SELECT 1 FROM users WHERE referral_code = ?", (code,)
        )
        if exists:
            continue
        try:
            await db.execute(
                "UPDATE users SET referral_code = ? WHERE internal_id = ?", (code, user_id)
            )
            await db.commit()
            return code
        except aiosqlite.IntegrityError:
            continue  # race on UNIQUE(referral_code); retry
    raise RuntimeError("could not allocate a unique referral code")


def share_link(code: str) -> str:
    return f"{config.get_frontend_url()}/r/{code}"


# ── Binding (immutable, self-referral blocked, D-S6) ───────────────────────────
async def bind_referral(
    db: aiosqlite.Connection, referred_user_id: int, code: Optional[str]
) -> bool:
    """Bind a newly-created user to a referrer by code. Returns True when a NEW binding is
    written. Silent no-op (returns False) on anything invalid so signup never breaks:
    missing/unknown code, already-bound user, or self-referral (same id OR same email)."""
    if not code:
        return False
    code = code.strip().upper()

    urows = await db.execute_fetchall(
        "SELECT email, referred_by_user_id FROM users WHERE internal_id = ?", (referred_user_id,)
    )
    if not urows:
        return False
    referred_email = (urows[0][0] or "").lower()
    if urows[0][1] is not None:
        return False  # already bound — immutable
    already = await db.execute_fetchall(
        "SELECT 1 FROM referrals WHERE referred_id = ?", (referred_user_id,)
    )
    if already:
        return False

    rrows = await db.execute_fetchall(
        "SELECT internal_id, email FROM users WHERE referral_code = ?", (code,)
    )
    if not rrows:
        return False
    referrer_id, referrer_email = rrows[0][0], (rrows[0][1] or "").lower()
    if referrer_id == referred_user_id or (referrer_email and referrer_email == referred_email):
        return False  # self-referral blocked (id + email)

    await db.execute(
        """INSERT INTO referrals (referrer_id, referred_id, referral_code, status, created_at)
           VALUES (?, ?, ?, 'bound', ?)""",
        (referrer_id, referred_user_id, code, _now_iso()),
    )
    await db.execute(
        "UPDATE users SET referred_by_user_id = ? WHERE internal_id = ?",
        (referrer_id, referred_user_id),
    )
    await db.commit()
    logger.info("referral bound: referrer=%s referred=%s", referrer_id, referred_user_id)
    return True


# ── Invite summary (for the profile invite card) ───────────────────────────────
async def get_summary(db: aiosqlite.Connection, user_id: int) -> dict:
    code = await get_or_create_code(db, user_id)
    referred = (await db.execute_fetchall(
        "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,)))[0][0]
    rewarded = (await db.execute_fetchall(
        "SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND status = 'rewarded'",
        (user_id,)))[0][0]
    banked = (await db.execute_fetchall(
        "SELECT COUNT(*) FROM referral_credits WHERE referrer_id = ? AND status = 'banked'",
        (user_id,)))[0][0]
    return {
        "code": code,
        "share_link": share_link(code),
        "referred_count": referred,
        "rewarded_count": rewarded,
        "credits_banked": banked,
    }


# ── Audit helper ───────────────────────────────────────────────────────────────
async def _audit(db, user_id, event_type, metadata: dict) -> None:
    import json
    await db.execute(
        """INSERT INTO subscription_events (user_id, event_type, metadata_json, created_at)
           VALUES (?, ?, ?, ?)""",
        (user_id, event_type, json.dumps(metadata), _now_iso()),
    )


async def _create_balance_credit(customer_id: str, amount_agorot: int, description: str) -> Optional[str]:
    """Post a negative customer balance transaction (a credit). Returns the tx id, or None
    on failure. Never raises."""
    try:
        stripe = stripe_service._stripe()
        bt = stripe.Customer.create_balance_transaction(
            customer_id, amount=-int(amount_agorot), currency="ils", description=description
        )
        return bt["id"] if isinstance(bt, dict) else getattr(bt, "id", None)
    except Exception as e:  # noqa: BLE001
        logger.error("Stripe balance credit failed cust=%s: %s", customer_id, e)
        return None


async def _email_reward(db, referrer_id: int, amount_agorot: int, banked: bool) -> None:
    urows = await db.execute_fetchall(
        "SELECT email, first_name FROM users WHERE internal_id = ?", (referrer_id,)
    )
    if not urows:
        return
    prefs = await notif.get_prefs(db, referrer_id)
    await notif.create_notification(
        db, referrer_id, "referral_reward", "You earned a free month",
        "A friend you invited started a paid plan, so you earned a free month.",
        "/profile", commit=False,
    )
    if prefs.get("email_product", True):
        await send_referral_reward_email(urows[0][0], urows[0][1], amount_agorot, banked)


# ── Reward trigger (referred user's first paid invoice, D-S7) ──────────────────
async def grant_reward_for_referred(
    db: aiosqlite.Connection, referred_user_id: int, *, commit: bool = True
) -> Optional[dict]:
    """Grant the referrer their free month for this referred user's first paid charge.

    Idempotent: the bound->rewarded transition is the single gate, so duplicate or
    out-of-order webhooks grant exactly one reward. Returns the reward dict, or None when
    there is nothing to do (no binding, or already rewarded/void)."""
    # Atomically claim the reward: only a 'bound' referral for this referred user flips.
    cur = await db.execute(
        "UPDATE referrals SET status = 'rewarded' WHERE referred_id = ? AND status = 'bound'",
        (referred_user_id,),
    )
    if cur.rowcount != 1:
        if commit:
            await db.commit()
        return None

    rrows = await db.execute_fetchall(
        "SELECT id, referrer_id FROM referrals WHERE referred_id = ?", (referred_user_id,)
    )
    referral_id, referrer_id = rrows[0][0], rrows[0][1]

    urows = await db.execute_fetchall(
        "SELECT tier, subscription_status, stripe_customer_id FROM users WHERE internal_id = ?",
        (referrer_id,),
    )
    tier, sub_status, customer_id = urows[0][0], urows[0][1], urows[0][2]
    plan_price = await stripe_service.get_plan_price_agorot(db, tier) if tier in ("basic", "pro") else 0

    immediate = bool(customer_id) and sub_status in _PAYING_STATES and plan_price > 0
    reward_type, reward_amount, cbt_id = "banked", None, None

    if immediate:
        if stripe_service._dev_mode():
            cbt_id = _cbt_dev_id("reward", referral_id)
        else:
            cbt_id = await _create_balance_credit(
                customer_id, plan_price, f"FINARODA referral reward (referral {referral_id})"
            )
        if cbt_id:
            reward_type, reward_amount = "balance_credit", plan_price

    if reward_type == "banked":
        await db.execute(
            """INSERT INTO referral_credits (referrer_id, referral_id, status, created_at)
               VALUES (?, ?, 'banked', ?)""",
            (referrer_id, referral_id, _now_iso()),
        )
        await _audit(db, referrer_id, "referral_credit_banked",
                     {"referral_id": referral_id, "referred_id": referred_user_id})

    await db.execute(
        """UPDATE referrals SET reward_type = ?, reward_amount_agorot = ?,
           reward_granted_at = ?, stripe_balance_transaction_id = ? WHERE id = ?""",
        (reward_type, reward_amount, _now_iso(), cbt_id, referral_id),
    )
    await _audit(db, referrer_id, "referral_reward_earned",
                 {"referral_id": referral_id, "referred_id": referred_user_id,
                  "reward_type": reward_type, "amount_agorot": reward_amount})
    await _email_reward(db, referrer_id, reward_amount or 0, banked=(reward_type == "banked"))

    if commit:
        await db.commit()
    logger.info("referral reward: referrer=%s type=%s amount=%s", referrer_id, reward_type, reward_amount)
    return {"referral_id": referral_id, "referrer_id": referrer_id,
            "reward_type": reward_type, "amount_agorot": reward_amount}


# ── Banked-credit application (referrer's first paid checkout, D-S5/AC6) ────────
async def apply_banked_credits(
    db: aiosqlite.Connection, referrer_user_id: int, plan: str, *, commit: bool = True
) -> int:
    """Apply all banked referral credits for a referrer who just went paid. Each is resolved
    to one month of the plan they bought (agorot), posted as a customer balance credit;
    credits stack and Stripe consumes them across invoices. Returns the number applied."""
    banked = await db.execute_fetchall(
        "SELECT id FROM referral_credits WHERE referrer_id = ? AND status = 'banked' ORDER BY id",
        (referrer_user_id,),
    )
    if not banked:
        return 0
    price = await stripe_service.get_plan_price_agorot(db, plan) if plan in ("basic", "pro") else 0
    if price <= 0:
        return 0
    urows = await db.execute_fetchall(
        "SELECT email, first_name, stripe_customer_id FROM users WHERE internal_id = ?",
        (referrer_user_id,),
    )
    email, first_name, customer_id = urows[0][0], urows[0][1], urows[0][2]

    applied = 0
    for (credit_id,) in banked:
        if stripe_service._dev_mode() or not customer_id:
            cbt_id = _cbt_dev_id("banked", credit_id)
        else:
            cbt_id = await _create_balance_credit(
                customer_id, price, f"FINARODA banked referral credit ({credit_id})"
            )
            if not cbt_id:
                continue  # leave banked; retried on a later webhook
        await db.execute(
            """UPDATE referral_credits SET status = 'applied', applied_amount_agorot = ?,
               applied_at = ?, stripe_balance_transaction_id = ? WHERE id = ?""",
            (price, _now_iso(), cbt_id, credit_id),
        )
        await _audit(db, referrer_user_id, "referral_credit_applied",
                     {"credit_id": credit_id, "amount_agorot": price, "plan": plan})
        applied += 1

    if applied:
        prefs = await notif.get_prefs(db, referrer_user_id)
        await notif.create_notification(
            db, referrer_user_id, "referral_credit", "Your referral credit is active",
            "Your banked referral credit is now applied to your account.", "/profile", commit=False,
        )
        if prefs.get("email_product", True):
            await send_referral_credit_applied_email(email, first_name, price * applied)
    if commit:
        await db.commit()
    logger.info("banked credits applied: referrer=%s count=%s", referrer_user_id, applied)
    return applied


# ── Void (admin, D-S10) ────────────────────────────────────────────────────────
async def void_referral(db: aiosqlite.Connection, referral_id: int, admin_id: int) -> dict:
    """Void a referral: remove a not-yet-applied banked credit, or post a compensating
    (positive) balance transaction that reverses an applied credit. Audited. Idempotent —
    an already-void referral is a no-op success."""
    from fastapi import HTTPException

    rows = await db.execute_fetchall(
        """SELECT id, referrer_id, referred_id, status, reward_type, reward_amount_agorot,
                  stripe_balance_transaction_id FROM referrals WHERE id = ?""",
        (referral_id,),
    )
    if not rows:
        raise HTTPException(404, "Referral not found")
    r = rows[0]
    referrer_id, status, reward_type, reward_amount = r[1], r[3], r[4], r[5]
    if status == "void":
        return {"ok": True, "already_void": True}

    cust_rows = await db.execute_fetchall(
        "SELECT stripe_customer_id FROM users WHERE internal_id = ?", (referrer_id,)
    )
    customer_id = cust_rows[0][0] if cust_rows else None
    reversed_agorot = 0

    async def _compensate(amount: int, ref: str) -> None:
        nonlocal reversed_agorot
        if not amount or amount <= 0:
            return
        if not stripe_service._dev_mode() and customer_id:
            try:
                stripe = stripe_service._stripe()
                stripe.Customer.create_balance_transaction(
                    customer_id, amount=int(amount), currency="ils",
                    description=f"FINARODA referral void ({ref})",
                )
            except Exception as e:  # noqa: BLE001 — reconcile locally regardless
                logger.error("Stripe compensating tx failed cust=%s: %s", customer_id, e)
        reversed_agorot += amount

    # Reverse any linked banked credits (applied -> compensate; banked -> just void).
    credits = await db.execute_fetchall(
        "SELECT id, status, applied_amount_agorot FROM referral_credits WHERE referral_id = ?",
        (referral_id,),
    )
    for cid, cstatus, capplied in credits:
        if cstatus == "applied" and capplied:
            await _compensate(capplied, f"credit {cid}")
        await db.execute(
            "UPDATE referral_credits SET status = 'void' WHERE id = ? AND status != 'void'", (cid,)
        )

    # An immediate balance credit (no referral_credits row) is reversed here.
    if reward_type == "balance_credit" and reward_amount:
        await _compensate(reward_amount, f"referral {referral_id}")

    await db.execute("UPDATE referrals SET status = 'void' WHERE id = ?", (referral_id,))
    await _audit(db, referrer_id, "referral_reward_voided",
                 {"referral_id": referral_id, "reversed_agorot": reversed_agorot, "admin_id": admin_id})
    await db.commit()
    logger.info("referral voided: id=%s reversed_agorot=%s", referral_id, reversed_agorot)
    return {"ok": True, "reversed_agorot": reversed_agorot}
