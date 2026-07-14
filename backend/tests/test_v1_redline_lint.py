"""RED-LINE SUITE — repo hygiene lint (ATP V1, TC-V1-LINT-xx).

Three constitution lints as laws over LIVE code (never touching tests, which legitimately
carry fixtures):
  - no real secret-key material committed (sk_live/sk_test/whsec/rk_live/pk_live + value),
  - zero Cardcom references (the PSP was fully migrated to Stripe in Stage 3R),
  - the em-dash product-copy guard lives in test_content_copy.py (frontend rendered copy,
    now JSX-comment-trustworthy) — this suite complements it on the secret/PSP side.

test_stage3r_stripe.py::TC-R3-12 asserts a narrower (sk_live + cardcom) form; this suite
widens the key patterns and stands as the dedicated, named red-line law.
"""
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND.parent / "frontend" / "src"

_EXTS = {".py", ".ts", ".tsx", ".js"}
# Live (non-test) code locations.
_LIVE_TARGETS = [BACKEND / d for d in ("core", "api", "models", "app", "scripts")]
_LIVE_TARGETS += [BACKEND / "config.py", BACKEND / "main.py", FRONTEND_SRC]

# A key PREFIX followed by real key characters — matches committed key material, not the
# env-var NAMES (STRIPE_SECRET_KEY) that legitimately appear in config.
_KEY_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9]"),
    re.compile(r"sk_test_[A-Za-z0-9]"),
    re.compile(r"rk_live_[A-Za-z0-9]"),
    re.compile(r"pk_live_[A-Za-z0-9]"),
    re.compile(r"whsec_[A-Za-z0-9]{6,}"),
]


def _live_files():
    for target in _LIVE_TARGETS:
        if target.is_file():
            yield target
        elif target.exists():
            for p in target.rglob("*"):
                if p.suffix.lower() in _EXTS:
                    yield p


# ── TC-V1-LINT-01 — no committed secret-key material in live code ──────────────
def test_no_committed_key_material():
    hits = []
    for p in _live_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        for pat in _KEY_PATTERNS:
            if pat.search(text):
                hits.append(f"{p.name}: {pat.pattern}")
    assert not hits, f"secret-key material committed to live code: {hits}"


# ── TC-V1-LINT-02 — zero Cardcom references in live code (Stripe migration) ────
def test_no_cardcom_in_live_code():
    hits = [str(p) for p in _live_files() if "cardcom" in
            p.read_text(encoding="utf-8", errors="ignore").lower()]
    assert not hits, f"Cardcom references remain in live code (migrated to Stripe): {hits}"
