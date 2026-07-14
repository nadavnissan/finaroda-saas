"""Migration 033 — Academy 2.0 lessons (flat card grid, dual gating, video, admin CRUD).

Supersedes the B6 hardcoded _MODULES list with a DB-backed academy_lessons table.
Completion/XP stays in xp_events (source='academy_lesson', ref=slug) UNCHANGED — this
migration is purely additive (no xp_events row is touched), so every existing completion
and its +100 XP survives, keyed by the same slug that used to be the module id (S3 safe).

Seeds the 12 existing B6 modules with slug == old module id, preserving:
  - title, duration (minutes), plan/rank gating mapped to (min_plan, min_rank),
  - awards_xp = 0 for the 3 legacy stubs (<3 terms) so their +0 / completed=False
    behavior is byte-identical to B6 (existing tests stay green).
Text bodies are seeded from concept_tooltips_content.json (the same source B6 rendered
client-side) so migrated lessons keep their content, now served server-authoritatively
and gated (403 on a locked lesson's content fetch, D-AC7).

The dormant mig-009 academy_bundles/episodes VOD tables are left untouched (unused legacy).
"""
import json
from pathlib import Path

import aiosqlite

MIGRATION_ID = "033_academy_lessons"

# (slug, title[no em dash], minutes, min_plan, min_rank, awards_xp) — mirrors B6 _MODULES.
# B6 tier 'basic' -> min_plan 'free' (open to all); tier 'full' -> 'basic' (paid).
# B6 rank_unlock None -> 0, 1000, 3000.  awards_xp 0 for the 3 stubs (<3 terms in B6).
_SEED = [
    ("regime_ema200",         "The 200-day average: reading regime",              10, "free",  0,    1),
    ("ema7_timing",           "EMA7 timing: the verified slope",                  12, "free",  0,    1),
    ("closed_candle_scoring", "Closed-candle scoring: why we wait for the close",  8, "free",  0,    1),
    ("methodology_overview",  "The Trading Blueprint: PASS, WATCH, and the score",14, "free",  0,    1),
    ("smart_skip",            "Smart-skip: the discipline curriculum",            18, "basic", 0,    1),
    ("momentum_basics",       "Momentum basics: RSI and exhaustion",              11, "basic", 0,    1),
    ("risk_geometry",         "R and risk geometry: one number to rule sizing",   15, "basic", 0,    1),
    ("structure_levels",      "Structure and levels: support, resistance, gaps",  13, "basic", 0,    1),
    ("volume_basics",         "Volume: confirmation, not prediction",              6, "free",  0,    0),
    ("positioning_basics",    "Positioning: funding and isolation",                7, "basic", 0,    0),
    ("spike_anatomy",         "Anatomy of a spike: why most fade",                12, "basic", 1000, 1),
    ("regime_transitions",    "Regime transitions: reading the turn",              9, "basic", 3000, 0),
]

# Short card descriptions (metadata for the card grid, not lesson content). No em dashes.
_DESC = {
    "regime_ema200": "How the 200-day line separates uptrend from downtrend, and why it is the first gate.",
    "ema7_timing": "The one verified edge: the slope of the 7-day average, measured on closed candles.",
    "closed_candle_scoring": "Why the score only counts a candle once it has closed, and what that protects you from.",
    "methodology_overview": "PASS, WATCH, and the 85/82 score line: the whole blueprint in one lesson.",
    "smart_skip": "The discipline curriculum: most days the right move is to skip, and why that is a skill.",
    "momentum_basics": "RSI, exhaustion, and reading momentum without turning it into a prediction.",
    "risk_geometry": "R as one number that governs sizing, stops, and targets with the same geometry.",
    "structure_levels": "Support, resistance, and gaps: how structure frames a setup.",
    "volume_basics": "Volume confirms, it does not predict. A short reference lesson.",
    "positioning_basics": "Funding and isolation: how positioning shows crowd pressure. A short reference lesson.",
    "spike_anatomy": "Bonus: the anatomy of a spike and why most of them fade.",
    "regime_transitions": "Bonus: reading the turn when one regime hands off to the next.",
}

_TAGS = {
    "regime_ema200": ["regime", "ema200", "trend"],
    "ema7_timing": ["ema7", "timing", "edge"],
    "closed_candle_scoring": ["scoring", "candles", "discipline"],
    "methodology_overview": ["blueprint", "pass", "watch", "score"],
    "smart_skip": ["discipline", "skip", "patience"],
    "momentum_basics": ["momentum", "rsi", "exhaustion"],
    "risk_geometry": ["risk", "r-multiple", "sizing"],
    "structure_levels": ["structure", "support", "resistance"],
    "volume_basics": ["volume", "confirmation"],
    "positioning_basics": ["positioning", "funding"],
    "spike_anatomy": ["spike", "reversal", "bonus"],
    "regime_transitions": ["regime", "transition", "bonus"],
}


def _bodies_from_concept_json() -> dict:
    """Group each academy id's terms into a text body. Falls back to {} if unavailable
    (a migration must never crash startup on a missing optional seed source)."""
    try:
        root = Path(__file__).resolve().parents[2] / "concept_tooltips_content.json"
        data = json.loads(root.read_text(encoding="utf-8"))
    except Exception:
        return {}
    bodies: dict = {}
    for t in data.get("terms", {}).values():
        aid = t.get("academy")
        if not aid:
            continue
        section = f"## {(t.get('term') or '').strip()}\n\n{(t.get('what') or '').strip()}"
        bodies.setdefault(aid, []).append(section)
    return {aid: "\n\n".join(secs) for aid, secs in bodies.items()}


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS academy_lessons (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            slug             TEXT NOT NULL UNIQUE,
            title            TEXT NOT NULL,
            description      TEXT NOT NULL DEFAULT '',
            content_type     TEXT NOT NULL DEFAULT 'text'
                             CHECK (content_type IN ('text','video')),
            body             TEXT NOT NULL DEFAULT '',
            video_url        TEXT,
            duration_minutes INTEGER NOT NULL DEFAULT 0,
            tags             TEXT NOT NULL DEFAULT '[]',
            min_plan         TEXT NOT NULL DEFAULT 'free'
                             CHECK (min_plan IN ('free','basic','pro')),
            min_rank         INTEGER NOT NULL DEFAULT 0,
            sort_index       INTEGER NOT NULL DEFAULT 0,
            awards_xp        INTEGER NOT NULL DEFAULT 1,
            archived_at      DATETIME,
            created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_academy_lessons_sort ON academy_lessons(sort_index, id)"
    )

    bodies = _bodies_from_concept_json()
    for i, (slug, title, minutes, min_plan, min_rank, awards_xp) in enumerate(_SEED):
        await db.execute(
            """
            INSERT OR IGNORE INTO academy_lessons
                (slug, title, description, content_type, body, video_url,
                 duration_minutes, tags, min_plan, min_rank, sort_index, awards_xp)
            VALUES (?, ?, ?, 'text', ?, NULL, ?, ?, ?, ?, ?, ?)
            """,
            (slug, title, _DESC.get(slug, ""), bodies.get(slug, ""), minutes,
             json.dumps(_TAGS.get(slug, [])), min_plan, min_rank, i, awards_xp),
        )
    await db.commit()
