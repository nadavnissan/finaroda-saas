"""
Billing state machine — the single source of truth for subscription status (D-B4).

Server-authoritative. Every subscription-status change funnels through
`apply_transition`, which (1) reads the current status, (2) refuses an illegal
transition, (3) writes the new status (and optional plan tier) and logs a
`subscription_events` row in one step. Entitlements derive ONLY from this state via
`effective_tier` — reveal-gating and scan limits keep their existing plan semantics
(the plan value buys breadth; the STATE decides whether the user holds a paid tier
at all).

State vocabulary is the existing `users.subscription_status` CHECK (mig 001), which
already covers D-B4 one-to-one (only spelling differs: D-B4 "trialing"->`trial`,
"canceled"->`cancelled`). No schema rename — the mapping is documented, not migrated.

    none      no subscription (Free)
    trial     14-day trial (D-B4 "trialing"), card-free (D1)
    active    paid, current
    past_due  a recurring charge failed; in the dunning grace window (D-B5)
    cancelled user cancelled; keeps access until period end (D-B6)
    expired   dunning exhausted; entitlements dropped to Free (D-B5)

Money is never touched here (that is cardcom_service); this module only moves state.
"""
import json
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

# ── States ────────────────────────────────────────────────────────────────────
NONE = "none"
TRIAL = "trial"
ACTIVE = "active"
PAST_DUE = "past_due"
CANCELLED = "cancelled"
EXPIRED = "expired"

ALL_STATES = frozenset({NONE, TRIAL, ACTIVE, PAST_DUE, CANCELLED, EXPIRED})

# States in which the user still holds their paid plan tier. `cancelled` retains
# access until the period-end drop (D-B6); `past_due` retains access during the
# dunning grace window until it is exhausted -> `expired` (D-B5).
ENTITLED_STATES = frozenset({TRIAL, ACTIVE, PAST_DUE, CANCELLED})

# Legal transitions (D-B4). A self-loop on ACTIVE models an idempotent renewal.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    NONE: frozenset({TRIAL, ACTIVE}),                 # start trial | direct paid checkout
    TRIAL: frozenset({ACTIVE, CANCELLED, NONE}),      # convert | cancel | trial_ended_to_free
    ACTIVE: frozenset({ACTIVE, PAST_DUE, CANCELLED}), # renew (self) | charge fail | user cancel
    PAST_DUE: frozenset({ACTIVE, EXPIRED, CANCELLED}),# retry ok | dunning exhausted | cancel
    CANCELLED: frozenset({NONE, ACTIVE}),             # period-end drop | reactivate
    EXPIRED: frozenset({ACTIVE, TRIAL, NONE}),        # resubscribe | (fresh) | idle
}


class IllegalTransition(ValueError):
    """Raised when a subscription state change is not permitted by the matrix."""


def can_transition(from_state: str, to_state: str) -> bool:
    """True if from_state -> to_state is a legal subscription transition."""
    return to_state in ALLOWED_TRANSITIONS.get(from_state, frozenset())


def assert_transition(from_state: str, to_state: str) -> None:
    """Raise IllegalTransition if the move is not permitted (used by every writer)."""
    if to_state not in ALL_STATES:
        raise IllegalTransition(f"Unknown target state: {to_state!r}")
    if not can_transition(from_state, to_state):
        raise IllegalTransition(f"Illegal subscription transition: {from_state!r} -> {to_state!r}")


def effective_tier(status: str, tier: Optional[str]) -> str:
    """
    The tier entitlements must honour, given the subscription state (D-B4).

    Paid breadth applies only in ENTITLED_STATES; `none`/`expired` (and any unknown
    status) collapse to Free regardless of the stored plan value. This is the one
    function gating code should call to decide "does this user get paid breadth?".
    """
    if status in ENTITLED_STATES and tier in ("basic", "advanced", "pro"):
        return tier
    return "free"


def is_entitled(status: str) -> bool:
    """True when the state grants the paid plan tier (access retained)."""
    return status in ENTITLED_STATES


async def get_status(db: aiosqlite.Connection, user_id: int) -> str:
    """Current subscription_status for a user ('none' if the row is missing)."""
    cur = await db.execute(
        "SELECT subscription_status FROM users WHERE internal_id = ?", (user_id,)
    )
    row = await cur.fetchone()
    if not row:
        return NONE
    return row[0] or NONE


async def apply_transition(
    db: aiosqlite.Connection,
    user_id: int,
    to_state: str,
    event_type: str,
    *,
    new_tier: Optional[str] = None,
    tier_before: Optional[str] = None,
    tier_after: Optional[str] = None,
    transaction_id: Optional[int] = None,
    metadata: Optional[dict] = None,
    commit: bool = True,
) -> str:
    """
    Guarded state change + audit log, in one place (server-authoritative).

    Reads the current status, refuses an illegal move (IllegalTransition), writes the
    new status (and `new_tier` when the plan value itself changes), and records a
    `subscription_events` row. Returns the previous status.

    `commit=False` lets a caller batch several writes (charge + doc + state) into one
    transaction and commit once. `tier_before`/`tier_after` populate the audit columns
    (plan-tier semantics, matching existing rows); when omitted they are left NULL.
    """
    current = await get_status(db, user_id)
    assert_transition(current, to_state)

    if new_tier is not None:
        await db.execute(
            "UPDATE users SET subscription_status = ?, tier = ? WHERE internal_id = ?",
            (to_state, new_tier, user_id),
        )
    else:
        await db.execute(
            "UPDATE users SET subscription_status = ? WHERE internal_id = ?",
            (to_state, user_id),
        )

    await db.execute(
        """INSERT INTO subscription_events
           (user_id, event_type, tier_before, tier_after, transaction_id, metadata_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            event_type,
            tier_before,
            tier_after,
            transaction_id,
            json.dumps(metadata) if metadata else None,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    if commit:
        await db.commit()
    return current
