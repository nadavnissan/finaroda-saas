"""Server-side breadcrumb sanitizer (Stage 7, D-A7 / red line).

Breadcrumbs are the reporter's last client-side events (route changes, scan submits, API
errors, notification-panel opens) attached to a support ticket. They are ALLOWLISTED
metadata only: this sanitizer drops every field not on the allowlist, so a journal
outcome value (status / r_result / win-loss) can never ride into a ticket payload — the
reveal-gating red line applies here too. The client never holds unrevealed values, and
this is the belt-and-suspenders server guard.
"""
from typing import Any

# Only these keys survive per crumb. Deliberately excludes anything outcome-shaped
# (status, r_result, outcome, pnl, direction, entry, sl, tp, score, ...).
_ALLOWED_KEYS = {
    "type", "event_type", "path", "route", "label", "ts", "timestamp", "code",
    "status_code", "method",
}
_MAX_ITEMS = 20
_MAX_STR = 200


def sanitize_breadcrumbs(raw: Any, max_items: int = _MAX_ITEMS) -> list[dict]:
    """Return an allowlisted, length-capped copy. Non-list / malformed input → []."""
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw[:max_items]:
        if not isinstance(item, dict):
            continue
        clean: dict = {}
        for key, val in item.items():
            if key not in _ALLOWED_KEYS:
                continue
            if isinstance(val, bool):
                clean[key] = val
            elif isinstance(val, (int, float)):
                clean[key] = val
            elif isinstance(val, str):
                clean[key] = val[:_MAX_STR]
            # anything else (dict/list/None) is dropped
        if clean:
            out.append(clean)
    return out
