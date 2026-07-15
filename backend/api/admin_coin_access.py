"""Coin access admin API (FX4) — per-plan coin allowlist editor. Admin-only
(require_admin -> 403 for everyone else). Every mutation is audited to admin_events
(same pattern as api/admin.py / api/admin_academy.py). Changes are read per-request by
core.coin_access.resolve_coin_access (no cache) so they take effect without a deploy.

No em dashes in copy; the coin allowlist is BREADTH only (which of our coins a plan may
scan), never a score/threshold/verdict knob (RED LINE unchanged).
"""
import json

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core.auth import require_admin
from backend.core.coin_access import (
    SCAN_UNIVERSE_BASE,
    base_symbol,
    resolve_all_access,
)
from backend.core.database import get_db_connection
from backend.models.auth import CurrentUser

router = APIRouter(prefix="/api/admin/coin-access", tags=["admin-coin-access"])


class CoinAccessUpdate(BaseModel):
    coins: list[str] = []
    wildcard: bool = False
    note: str | None = None


async def _audit(db: aiosqlite.Connection, admin_id: int, event_type: str, details: dict) -> None:
    await db.execute(
        """INSERT INTO admin_events (admin_id, event_type, target_user_id, details_json)
           VALUES (?, ?, NULL, ?)""",
        (admin_id, event_type, json.dumps(details)),
    )


@router.get("")
async def get_coin_access(
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """All three plans' allowlists plus the managed universe (for the checklist UI)."""
    all_access = await resolve_all_access(db)
    return {
        "universe": list(SCAN_UNIVERSE_BASE),
        "plans": [all_access[p] for p in ("free", "basic", "pro")],
    }


@router.put("/{plan}")
async def update_coin_access(
    plan: str,
    body: CoinAccessUpdate,
    admin: CurrentUser = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> dict:
    """Set a plan's allowlist (base symbols) or its wildcard flag. Coins must be within the
    managed universe; unknown symbols are rejected so the checklist cannot drift."""
    if plan not in ("free", "basic", "pro"):
        raise HTTPException(400, f"invalid plan: {plan}")
    coins = []
    for c in body.coins:
        b = base_symbol(c)
        if b not in SCAN_UNIVERSE_BASE:
            raise HTTPException(400, f"coin not in universe: {c}")
        if b not in coins:
            coins.append(b)
    wildcard = 1 if body.wildcard else 0
    stored_coins = "[]" if wildcard else json.dumps(coins)
    await db.execute(
        "UPDATE coin_access SET coins=?, wildcard=?, updated_at=CURRENT_TIMESTAMP WHERE plan=?",
        (stored_coins, wildcard, plan),
    )
    await _audit(
        db, admin.internal_id, "coin_access_update",
        {"plan": plan, "coins": coins, "wildcard": bool(wildcard), "note": body.note},
    )
    await db.commit()
    return {"ok": True, "plan": plan, "coins": coins, "wildcard": bool(wildcard)}
