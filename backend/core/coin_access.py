"""Per-plan coin allowlist (FX4) — server-authoritative coin-identity gating.

DB-backed (`coin_access`, mig 037), admin-editable, read per-request (no cache) — same
shape as entitlements (mig 027). /api/scan/coin-access exposes the current user's access
for the UI; /api/scan/events rejects a scan of a managed-universe coin outside the plan's
allowlist with 403 COIN_GATED.

RED LINE unchanged: coin access is BREADTH (which of our coins a plan may scan), never a
different verdict/score/threshold. Trial = Pro access (mirrors academy_gate.user_plan_level).

Universe-only rule: identity gating applies ONLY to coins in SCAN_UNIVERSE_BASE (the
managed universe, mirrored from frontend/src/lib/scan/bybit.ts SCAN_UNIVERSE). A symbol
outside the universe is out of scope for identity gating (it is never offered in the UI);
the coin COUNT and daily gates still apply to it. This keeps the count-gate law (proven on
synthetic C{i}USDT symbols in the red-line suite) orthogonal to coin-identity gating.
"""
import json

import aiosqlite

from backend.models.auth import CurrentUser

# Mirror of SCAN_UNIVERSE (frontend/src/lib/scan/bybit.ts), base symbols only. Adding a
# coin there means adding it here; it then auto-includes for Pro via the wildcard.
SCAN_UNIVERSE_BASE = ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "LINK", "DOGE", "DOT")

_PLANS = ("free", "basic", "pro")

# Fallback (used only if a coin_access row is missing). Mirrors the mig 037 seed.
_DEFAULT_ACCESS = {
    "free": (["LINK", "AVAX"], False),
    "basic": (["LINK", "AVAX", "SOL", "ADA", "DOGE"], False),
    "pro": ([], True),
}

_PLAN_NAMES = {"free": "Free", "basic": "Basic", "pro": "Pro"}


def base_symbol(coin: str) -> str:
    """Canonical coin identity: the base symbol, e.g. 'BTCUSDT' -> 'BTC'."""
    c = (coin or "").upper()
    return c[:-4] if c.endswith("USDT") else c


def effective_plan(user: CurrentUser) -> str:
    """The plan whose coin access applies. Trial = full Pro access (B6b); legacy
    'advanced' resolves to Basic (Decision A, mig 029)."""
    if getattr(user, "subscription_status", None) == "trial":
        return "pro"
    t = getattr(user, "tier", None)
    if t == "advanced":
        return "basic"
    return t if t in _PLANS else "free"


async def resolve_coin_access(db: aiosqlite.Connection, plan: str) -> dict:
    """Return {plan, coins:[base...], wildcard:bool} for a plan (DB-first, safe fallback).
    Coins are normalized to base symbols and restricted to the known universe."""
    p = plan if plan in _PLANS else "free"
    rows = await db.execute_fetchall(
        "SELECT coins, wildcard FROM coin_access WHERE plan = ?", (p,)
    )
    if rows:
        try:
            raw = json.loads(rows[0][0]) or []
        except (TypeError, json.JSONDecodeError):
            raw = list(_DEFAULT_ACCESS[p][0])
        wildcard = bool(rows[0][1])
    else:
        raw, wildcard = list(_DEFAULT_ACCESS[p][0]), _DEFAULT_ACCESS[p][1]
    coins = [b for b in (base_symbol(c) for c in raw) if b in SCAN_UNIVERSE_BASE]
    return {"plan": p, "coins": coins, "wildcard": wildcard}


async def resolve_all_access(db: aiosqlite.Connection) -> dict:
    """All three plans' access — used to compute the minimal unlocking plan for a coin."""
    out = {}
    for p in _PLANS:
        out[p] = await resolve_coin_access(db, p)
    return out


def coin_allowed(coin: str, access: dict) -> bool:
    """Universe-only identity gate. Unknown symbols and wildcard plans pass through."""
    b = base_symbol(coin)
    if b not in SCAN_UNIVERSE_BASE:
        return True
    if access.get("wildcard"):
        return True
    return b in access.get("coins", [])


def gated_coins(coins, access: dict) -> list:
    """Sorted, de-duplicated base symbols in `coins` that are blocked for this access."""
    return sorted({base_symbol(c) for c in coins if not coin_allowed(c, access)})


def unlock_plan(base: str, all_access: dict) -> str:
    """The lowest plan whose allowlist (or wildcard) includes this base symbol."""
    for p in _PLANS:
        a = all_access[p]
        if a["wildcard"] or base in a["coins"]:
            return p
    return "pro"


def plan_name(plan: str) -> str:
    return _PLAN_NAMES.get(plan, plan.title())
