"""Academy 2.0 shared logic: dual gating (plan + rank), lock reasons, video URL validation.

Gating is STATUS-based (D-AC1): a lesson passes when the user's plan >= min_plan AND
xp_total >= min_rank. This is never "spend XP to unlock" (XP_ECONOMY: no XP-as-currency);
holding the rank is a status, not a purchase. Server-authoritative (D-AC7): the caller
decides visibility here, the client never gates itself.
"""
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

from backend.core.ranks import RANKS
from backend.models.auth import CurrentUser

VALID_PLANS = ("free", "basic", "pro")
VALID_MIN_RANKS = (0, 1000, 3000, 8000)

# free < basic < pro. Legacy 'advanced' == basic (Decision A, mig 029). Trial = Pro access.
_PLAN_LEVEL = {"free": 0, "basic": 1, "advanced": 1, "pro": 2}
_MIN_PLAN_LEVEL = {"free": 0, "basic": 1, "pro": 2}


def user_plan_level(user: CurrentUser) -> int:
    if user.subscription_status == "trial":
        return _PLAN_LEVEL["pro"]          # a trial is full Pro access (B6b)
    return _PLAN_LEVEL.get(user.tier, 0)


def plan_ok(user: CurrentUser, min_plan: str) -> bool:
    return user_plan_level(user) >= _MIN_PLAN_LEVEL.get(min_plan, 0)


def rank_ok(xp_total: int, min_rank: int) -> bool:
    return xp_total >= min_rank


def is_unlocked(user: CurrentUser, xp_total: int, min_plan: str, min_rank: int) -> bool:
    """Both gates must pass (D-AC1)."""
    return plan_ok(user, min_plan) and rank_ok(xp_total, min_rank)


def _rank_name(min_rank: int) -> str:
    for _lvl, name, floor in RANKS:
        if floor == min_rank:
            return name
    return f"{min_rank:,} XP"


def _plan_name(min_plan: str) -> str:
    return {"free": "Free", "basic": "Basic", "pro": "Pro"}.get(min_plan, min_plan.title())


def lock_reason(user: CurrentUser, xp_total: int, min_plan: str, min_rank: int) -> Optional[str]:
    """Plain-language reason a lesson is locked, or None when unlocked. The rank gate is
    named first (bonus content), else the plan gate. 'Show the door, name the key.'"""
    if is_unlocked(user, xp_total, min_plan, min_rank):
        return None
    if min_rank > 0 and not rank_ok(xp_total, min_rank):
        return f"Unlocks at {_rank_name(min_rank)}"
    return f"Available on {_plan_name(min_plan)} plan"


# ── Video URL validation (D-AC2: YouTube / Vimeo only, no uploads) ──
_YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}
_VIMEO_HOSTS = {"vimeo.com", "www.vimeo.com", "player.vimeo.com"}


def validate_video_url(url: str) -> Optional[str]:
    """Return a normalized embeddable URL, or None if it is not a valid YouTube/Vimeo link.
    We normalize at write time so the client can iframe the stored value directly."""
    if not url:
        return None
    try:
        p = urlparse(url.strip())
    except Exception:
        return None
    if p.scheme not in ("http", "https"):
        return None
    host = (p.hostname or "").lower()
    if host in _YT_HOSTS:
        vid = None
        if host in ("youtu.be", "www.youtu.be"):
            vid = p.path.lstrip("/").split("/")[0]
        elif p.path == "/watch":
            vid = (parse_qs(p.query).get("v") or [None])[0]
        elif p.path.startswith(("/embed/", "/v/", "/shorts/")):
            parts = [seg for seg in p.path.split("/") if seg]
            vid = parts[1] if len(parts) > 1 else None
        if vid and re.fullmatch(r"[A-Za-z0-9_-]{6,20}", vid):
            return f"https://www.youtube.com/embed/{vid}"
        return None
    if host in _VIMEO_HOSTS:
        m = re.search(r"/(\d{5,})", p.path)
        if m:
            return f"https://player.vimeo.com/video/{m.group(1)}"
        return None
    return None
