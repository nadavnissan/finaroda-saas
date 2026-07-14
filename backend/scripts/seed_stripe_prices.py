"""
Idempotent Stripe Product + Price seeder (Stage 3R, D-R3).

Creates one Stripe Product per paid plan and a monthly ILS recurring Price, then stores the
Price id in system_settings (`stripe_price_<plan>`). Idempotent: a plan that already has a
stored price id is skipped, so re-running never creates duplicates. A price CHANGE is a NEW
Stripe Price via this script (old subscriptions keep their old price — Stripe default).

Run in Stripe TEST mode first:
    python -m backend.scripts.seed_stripe_prices

DEV/no-key: a no-op that reports what it WOULD create (zero network). Amounts are agorot
ints from system_settings (plan_price_<plan>), currency ILS.
"""
import asyncio
import logging

import aiosqlite

from backend import config
from backend.core import stripe_service

log = logging.getLogger(__name__)

PAID_PLANS = ("basic", "pro")


async def _set_setting(db: aiosqlite.Connection, key: str, value: str) -> None:
    cur = await db.execute(
        "UPDATE system_settings SET value = ? WHERE key = ?", (value, key)
    )
    if cur.rowcount == 0:
        await db.execute(
            """INSERT INTO system_settings (key, value, value_type, description)
               VALUES (?, ?, 'string', 'Stripe Price id (seeded by seed_stripe_prices)')""",
            (key, value),
        )
    await db.commit()


async def seed_prices(db: aiosqlite.Connection) -> dict:
    """Ensure each paid plan has a Stripe Price. Returns {plan: {price_id, created, note}}."""
    live = bool(config.FEATURE_STRIPE_LIVE and config.STRIPE_SECRET_KEY)
    result: dict = {}
    for plan in PAID_PLANS:
        existing = await stripe_service.get_stripe_price_id(db, plan)
        if existing:
            result[plan] = {"price_id": existing, "created": False, "note": "exists"}
            continue
        amount = await stripe_service.get_plan_price_agorot(db, plan)
        if amount <= 0:
            result[plan] = {"price_id": None, "created": False, "note": "no plan price"}
            continue
        if not live:
            result[plan] = {"price_id": None, "created": False,
                            "note": f"dev_mode (would create {amount} agorot ILS/month)"}
            continue
        stripe = stripe_service._stripe()
        product = stripe.Product.create(
            name=f"FINARODA {plan.upper()}", metadata={"plan": plan}
        )
        price = stripe.Price.create(
            unit_amount=amount, currency="ils", recurring={"interval": "month"},
            product=product["id"], metadata={"plan": plan},
        )
        price_id = price["id"]
        await _set_setting(db, f"stripe_price_{plan}", price_id)
        result[plan] = {"price_id": price_id, "created": True, "note": "created"}
    log.info("seed_stripe_prices: %s", result)
    return result


async def _main() -> None:
    db_path = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        result = await seed_prices(db)
    print(result)


if __name__ == "__main__":
    asyncio.run(_main())
