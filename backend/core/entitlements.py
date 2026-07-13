"""Plan entitlements — the server-authoritative source for scan gating (B1).

Resolved from system_settings (admin-editable, mig 027) by the user's tier. The
scan is computed client-side (locked principle), but the *entitlements are binding*:
/api/scan/entitlements is what the client must honour, and /api/scan/events rejects
an over-limit scan. Only coins-per-scan and chart-layers are hard-gated this phase;
scans_per_day is exposed for the UI. RED LINE unchanged: the score / threshold are
identical on every plan — plans buy breadth (coins) and depth (chart layers), never
a different verdict.
"""
import aiosqlite

VALID_TIERS = ("free", "basic", "advanced", "pro")

# Fallback defaults (used only if a setting row is missing). Mirror the E3 table.
_DEFAULT_COINS = {"free": 2, "basic": 2, "advanced": 5, "pro": 10}
_DEFAULT_LAYERS = {"free": "ema200_only", "basic": "full", "advanced": "full", "pro": "full"}
_DEFAULT_SCANS = {"free": 1, "basic": 0, "advanced": 0, "pro": 0}


async def _setting(db: aiosqlite.Connection, key: str) -> str | None:
    rows = await db.execute_fetchall("SELECT value FROM system_settings WHERE key = ?", (key,))
    return rows[0][0] if rows and rows[0][0] is not None else None


async def get_setting_int(db: aiosqlite.Connection, key: str, default: int) -> int:
    """Read an int system_setting with a safe fallback (shared by journal / admin)."""
    raw = await _setting(db, key)
    try:
        return int(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default


def _norm_tier(tier: str | None) -> str:
    return tier if tier in VALID_TIERS else "free"


async def resolve_entitlements(db: aiosqlite.Connection, tier: str | None) -> dict:
    """Return {tier, coins_per_scan, chart_layers, scans_per_day} for a tier."""
    t = _norm_tier(tier)

    coins_raw = await _setting(db, f"scan_coins_{t}")
    try:
        coins = int(coins_raw) if coins_raw is not None else _DEFAULT_COINS[t]
    except (TypeError, ValueError):
        coins = _DEFAULT_COINS[t]

    layers = await _setting(db, f"chart_layers_{t}") or _DEFAULT_LAYERS[t]
    if layers not in ("ema200_only", "full"):
        layers = _DEFAULT_LAYERS[t]

    scans_raw = await _setting(db, f"scans_per_day_{t}")
    try:
        scans = int(scans_raw) if scans_raw is not None else _DEFAULT_SCANS[t]
    except (TypeError, ValueError):
        scans = _DEFAULT_SCANS[t]

    return {
        "tier": t,
        "coins_per_scan": coins,
        "chart_layers": layers,
        "scans_per_day": scans,
    }
