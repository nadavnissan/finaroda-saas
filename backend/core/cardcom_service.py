"""
Cardcom v11 service layer — checkout / recurring charge / webhook handling.

P0 scope: PLACEHOLDER. Function signatures are declared to fix the P1 contract;
bodies raise NotImplementedError. No Morning / Stripe / legacy code (SPEC §3.3).
"""
from __future__ import annotations

import aiosqlite


async def initiate_checkout(db: aiosqlite.Connection, user_id: int, plan: str) -> dict:
    """Build a Cardcom LowProfile/Create checkout and return redirect URL. (P1)"""
    raise NotImplementedError("Cardcom checkout is implemented in P1 (SPEC §9).")


async def charge_recurring(db: aiosqlite.Connection, user_id: int) -> dict:
    """Charge a stored Cardcom token (Token/ChargeToken) for renewal. (P1)"""
    raise NotImplementedError("Cardcom recurring charge is implemented in P1 (SPEC §9).")


async def handle_webhook(raw_body: bytes, signature_header: str, db: aiosqlite.Connection) -> None:
    """Verify HMAC, update payment_transactions + users, log subscription_events. (P1)"""
    raise NotImplementedError("Cardcom webhook handling is implemented in P1 (SPEC §9).")
