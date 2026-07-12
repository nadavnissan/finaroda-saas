"""Onboarding F13 API — episodes (server-side outcome withholding), XP, funnel.

Pre-signup screens (S0–S4, the trap) call the episode + funnel endpoints with no
cookie, so those are optional-auth. XP and completion are post-signup (required).

RED-LINE guarantees enforced here:
- The episode SETUP response never contains the reveal candles or the outcome
  (win/loss, R, %). They are returned ONLY by the explicit /reveal call. This is
  the "outcome not present in the DOM pre-reveal" AC for S1 (trap) and S10.
- XP amounts are server-authoritative (a closed map); the client sends only a ref.
  UNIQUE (user_id, source, ref) makes every award idempotent (farming guard).
"""
import json
from typing import Optional

import aiosqlite
import structlog
from fastapi import APIRouter, Cookie, Depends, HTTPException
from jose import JWTError, jwt

from backend.config import JWT_ALGORITHM, JWT_SECRET
from backend.core.auth import get_current_user
from backend.core.database import get_db_connection
from backend.models.auth import CurrentUser
from backend.models.onboarding import (
    EpisodeOutcome,
    EpisodeReveal,
    EpisodeSetup,
    FunnelEventCreate,
    OkResponse,
    XPState,
)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])
log = structlog.get_logger(__name__)

# Onboarding XP is a single lifetime grant (XP_ECONOMY.md §1: 50+100+50+100=300),
# credited ONCE at completion. The per-screen 50/100/50/100 progression is a
# client-side meter only. Server-authoritative amount; idempotent (mig 026 partial
# unique index → once per user+source). The client never sends an amount.
ONBOARDING_SOURCE = "onboarding"
ONBOARDING_TOTAL = 300


async def get_optional_user_id(
    access_token: Optional[str] = Cookie(None),
) -> Optional[int]:
    """Return the user id from the JWT cookie, or None (pre-signup screens)."""
    if not access_token:
        return None
    try:
        payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        return None


def _candles(kline_json: str) -> list[dict]:
    return json.loads(kline_json)


# ── Episodes ──────────────────────────────────────────────────────────────────


async def _load_episode(db: aiosqlite.Connection, ext_id: str) -> dict:
    rows = await db.execute_fetchall(
        """SELECT ext_id, coin, date_range, kline_data, scenario_type, lesson_flag,
                  direction, entry_index, entry_price, outcome
           FROM episodes WHERE ext_id = ?""",
        (ext_id,),
    )
    if not rows:
        raise HTTPException(404, {"code": "EPISODE_NOT_FOUND", "message": ext_id})
    return dict(rows[0])


def _to_setup(ep: dict) -> EpisodeSetup:
    candles = _candles(ep["kline_data"])
    entry_index = ep["entry_index"]
    setup = candles[: entry_index + 1]
    reveal_count = max(0, len(candles) - len(setup))
    # "Spike day" annotation = the candle with the biggest high across the full
    # series (a structural index hint, not the withheld outcome value).
    spike_index = max(range(len(candles)), key=lambda i: candles[i]["h"]) if candles else None
    # score is a setup-time quality signal for the PASS demo (valid_setup only);
    # it is NOT the withheld outcome.
    score = None
    if ep["scenario_type"] == "valid_setup":
        score = json.loads(ep["outcome"]).get("score")
    return EpisodeSetup(
        ext_id=ep["ext_id"],
        coin=ep["coin"],
        date_range=ep["date_range"],
        scenario_type=ep["scenario_type"],
        lesson_flag=ep["lesson_flag"],
        direction=ep["direction"],
        entry_index=entry_index,
        entry_price=ep["entry_price"],
        spike_index=spike_index,
        setup_klines=setup,
        reveal_count=reveal_count,
        score=score,
    )


@router.get("/episodes", response_model=list[EpisodeSetup])
async def list_episodes(
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> list[EpisodeSetup]:
    """List episode SETUPS (outcome + reveal candles withheld)."""
    rows = await db.execute_fetchall("SELECT ext_id FROM episodes ORDER BY ext_id")
    return [_to_setup(await _load_episode(db, r[0])) for r in rows]


@router.get("/episodes/{ext_id}", response_model=EpisodeSetup)
async def get_episode(
    ext_id: str,
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> EpisodeSetup:
    """Episode SETUP only — the pre-decision candles. Outcome is withheld (AC)."""
    return _to_setup(await _load_episode(db, ext_id))


@router.post("/episodes/{ext_id}/reveal", response_model=EpisodeReveal)
async def reveal_episode(
    ext_id: str,
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> EpisodeReveal:
    """Reveal the withheld outcome + playback candles (post-decision / post-scan)."""
    ep = await _load_episode(db, ext_id)
    candles = _candles(ep["kline_data"])
    reveal = candles[ep["entry_index"] + 1 :]
    outcome = json.loads(ep["outcome"])
    return EpisodeReveal(
        ext_id=ep["ext_id"],
        reveal_klines=reveal,
        outcome=EpisodeOutcome(**outcome),
    )


# ── XP (post-signup; server-authoritative, idempotent) ────────────────────────


async def _xp_state(db: aiosqlite.Connection, user_id: int) -> XPState:
    rows = await db.execute_fetchall(
        "SELECT source, ref, amount FROM xp_events WHERE user_id = ? ORDER BY ts",
        (user_id,),
    )
    events = [dict(r) for r in rows]
    total = sum(e["amount"] for e in events)
    return XPState(total=total, events=events)


async def _grant_onboarding_xp(db: aiosqlite.Connection, user_id: int) -> None:
    """Credit the single lifetime onboarding grant. Idempotent (mig 026)."""
    await db.execute(
        "INSERT OR IGNORE INTO xp_events (user_id, source, ref, amount) VALUES (?, ?, 'onboarding', ?)",
        (user_id, ONBOARDING_SOURCE, ONBOARDING_TOTAL),
    )


@router.get("/xp", response_model=XPState)
async def get_xp(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> XPState:
    """Current user's persisted XP (for the meter after signup)."""
    return await _xp_state(db, user.internal_id)


# ── Funnel (optional-auth: anon before signup, user after) ────────────────────


@router.post("/funnel", response_model=OkResponse)
async def log_funnel(
    body: FunnelEventCreate,
    user_id: Optional[int] = Depends(get_optional_user_id),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> OkResponse:
    """Append a funnel event (Onboarding Spec §5). Analytics only — never gamified."""
    await db.execute(
        "INSERT INTO onboarding_funnel_events (user_id, anon_id, stage, detail) VALUES (?, ?, ?, ?)",
        (
            user_id,
            body.anon_id,
            body.stage,
            json.dumps(body.detail, separators=(",", ":")) if body.detail else None,
        ),
    )
    await db.commit()
    return OkResponse()


# ── Completion ────────────────────────────────────────────────────────────────


@router.post("/complete", response_model=OkResponse)
async def complete_onboarding(
    user: CurrentUser = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db_connection),
) -> OkResponse:
    """Mark onboarding complete (idempotent), grant the one-time XP, log completion."""
    await db.execute(
        """UPDATE users SET onboarding_completed_at = CURRENT_TIMESTAMP
           WHERE internal_id = ? AND onboarding_completed_at IS NULL""",
        (user.internal_id,),
    )
    await _grant_onboarding_xp(db, user.internal_id)
    await db.execute(
        "INSERT INTO onboarding_funnel_events (user_id, stage) VALUES (?, 'completion')",
        (user.internal_id,),
    )
    await db.commit()
    return OkResponse()
