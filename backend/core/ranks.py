"""XP rank ladder (XP_ECONOMY.md v1.0) — server-side mirror of frontend lib/onboarding/xp.ts.

Display only: ranks unlock knowledge, never signals, and this module NEVER grants XP or
gates anything (RED LINE). Used by the admin console to label a user's rank.
"""

# (level, name, floor) — floor = XP at which the rank begins. Keep in lockstep with
# frontend RANKS.
RANKS: list[tuple[int, str, int]] = [
    (1, "Strategy Apprentice", 0),
    (2, "Risk Manager", 1000),
    (3, "Regime Reader", 3000),
    (4, "Master Strategist", 8000),
]


def rank_for(xp: int) -> dict:
    """Return {'level', 'name'} for an XP total (highest floor not exceeding xp)."""
    level, name, _ = RANKS[0]
    for lvl, nm, floor in RANKS:
        if xp >= floor:
            level, name = lvl, nm
    return {"level": level, "name": name}
