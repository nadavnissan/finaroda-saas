"""Content + copy-rule guards (Nadav, 12/07).

- The concept-tooltip content loads all 46 terms with the required shape.
- The frontend bundled copy is byte-identical to the locked root file (drift guard).
- No em dashes in product copy: greps frontend/src for U+2014 inside strings/JSX
  (comments excluded, since only rendered copy is "product copy").
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROOT_JSON = ROOT / "concept_tooltips_content.json"
FRONTEND_JSON = ROOT / "frontend" / "src" / "lib" / "onboarding" / "concept_tooltips_content.json"
FRONTEND_SRC = ROOT / "frontend" / "src"

# F16 market narratives (locked-file flow, same governance as the tooltips).
NARR_ROOT_JSON = ROOT / "market_narratives.json"
NARR_FRONTEND_JSON = ROOT / "frontend" / "src" / "lib" / "scan" / "market_narratives.json"

# Block comments /* ... */ (covers JSX {/* ... */}) and // line comments. Removing these
# BEFORE scanning is what makes the em-dash guard trustworthy: a dash inside a comment is
# not product copy, and must not be flagged (the pre-2026-07-14 line-prefix heuristic
# missed JSX block comments — fixed here).
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")


def _strip_comments(src: str) -> str:
    """Remove /* */ (and JSX {/* */}) block comments and // line comments from TS/TSX."""
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", src))


def em_dash_violations(src_dir: Path) -> list[str]:
    """Files:line of an em dash (U+2014) in rendered TS/TSX copy, comments excluded."""
    violations: list[str] = []
    for f in src_dir.rglob("*"):
        if f.suffix not in (".ts", ".tsx"):
            continue
        cleaned = _strip_comments(f.read_text(encoding="utf-8"))
        for i, line in enumerate(cleaned.splitlines(), 1):
            if "—" in line:
                violations.append(f"{f.relative_to(ROOT)}:{i}")
    return violations


def test_tooltip_content_loads_46_terms():
    data = json.loads(ROOT_JSON.read_text(encoding="utf-8"))
    terms = data["terms"]
    assert len(terms) == 46, f"expected 46 terms, got {len(terms)}"
    for tid, t in terms.items():
        for field in ("term", "what", "now", "academy"):
            assert t.get(field), f"term {tid} missing {field}"


def test_frontend_tooltip_copy_matches_root():
    """The bundled frontend copy must match the locked root file exactly."""
    root = json.loads(ROOT_JSON.read_text(encoding="utf-8"))
    fe = json.loads(FRONTEND_JSON.read_text(encoding="utf-8"))
    assert fe == root, "frontend tooltip copy drifted from the locked root file"


def test_no_em_dash_in_product_copy():
    """No em dash (U+2014) in strings/JSX across frontend/src (comments excluded)."""
    violations = em_dash_violations(FRONTEND_SRC)
    assert not violations, "em dashes in product copy: " + ", ".join(violations)


# FX3 red line: the raw trade words SL / TP / ENTRY are forbidden in user-facing copy.
# The canonical calculator terminology replaces them (Mathematical Trigger Point /
# Calculated Risk Level / Dynamic Risk Level / Calculated Target Level, PRD §3.5.1).
# Uppercase whole-word match over comment-stripped source keeps false positives out
# (lowercase code identifiers like `sl`/`tp`/`entry` and words like SLOPE/HTTP are safe).
_FORBIDDEN_TRADE_TERMS = re.compile(r"\b(ENTRY|SL|TP)\b")


def forbidden_trade_term_violations(src_dir: Path) -> list[str]:
    """Files:line where a forbidden trade word appears in rendered TS/TSX (comments out)."""
    violations: list[str] = []
    for f in src_dir.rglob("*"):
        if f.suffix not in (".ts", ".tsx"):
            continue
        cleaned = _strip_comments(f.read_text(encoding="utf-8"))
        for i, line in enumerate(cleaned.splitlines(), 1):
            if _FORBIDDEN_TRADE_TERMS.search(line):
                violations.append(f"{f.relative_to(ROOT)}:{i}")
    return violations


def test_no_forbidden_trade_terms_in_ui():
    """FX3: SL / TP / ENTRY must not appear in user-facing frontend copy (comments out)."""
    violations = forbidden_trade_term_violations(FRONTEND_SRC)
    assert not violations, "forbidden trade terms (SL/TP/ENTRY) in UI copy: " + ", ".join(violations)


def test_forbidden_trade_term_guard_ignores_comments_and_code():
    """Meta-test: the guard flags rendered SL/TP/ENTRY but not comments or lowercase ids."""
    assert forbidden_trade_term_violations  # symbol exists
    assert _FORBIDDEN_TRADE_TERMS.search("<Level label=\"ENTRY\" />")   # rendered label caught
    assert not _FORBIDDEN_TRADE_TERMS.search(_strip_comments("// note about SL / TP"))  # comment out
    assert not _FORBIDDEN_TRADE_TERMS.search("const sl = r.sl; // slope")  # lowercase id safe
    assert not _FORBIDDEN_TRADE_TERMS.search("EMA7 SLOPE verified")        # SLOPE not SL


def test_em_dash_guard_ignores_comments_but_catches_copy():
    """Meta-test: the guard must NOT flag an em dash inside a JSX/block/line comment, but
    MUST flag one in rendered copy. Proves the lint is trustworthy (fixes the JSX gap)."""
    assert _strip_comments("{/* a — b */}") .strip() == "{}"        # JSX block comment stripped
    assert "—" not in _strip_comments("const x = 1; // note — here")  # line comment stripped
    assert "—" not in _strip_comments("/* multi\n line — c */")       # multi-line block stripped
    assert "—" in _strip_comments('const s = "price — value";')      # real copy survives


# ── F16 market narratives: locked-file governance (drift + copy rules) ─────────
_NARR_STATE_IDS = {"S1", "S2", "S3", "S4", "S5", "S6"}

# Imperative verbs that must never open a narrative sentence (descriptive language only,
# B4 / PRD §8.1 "analysis not advice"). Sentence-initial only, so nouns like "watch band"
# and past-tense verbs mid-sentence stay safe.
_IMPERATIVE_VERBS = {
    "buy", "sell", "enter", "exit", "hold", "wait", "consider", "add", "trade", "take",
    "avoid", "look", "try", "use", "set", "place", "close", "open", "keep", "stay",
    "click", "tap", "scan", "watch", "check", "get", "go", "book", "cut", "chase",
    "grab", "ride", "catch", "lock", "do", "don't", "buy/sell",
}


def _narr_variants(data: dict) -> list:
    """All (state_id, variant_text) pairs across the narratives file."""
    out = []
    for sid, state in data["states"].items():
        for v in state["variants"]:
            out.append((sid, v))
    return out


def _narr_sentences(variant: str) -> list:
    """Split a variant into sentences after stripping concept markers and placeholders."""
    text = re.sub(r"\[\[[a-z0-9_]+\|([^\]]+)\]\]", r"\1", variant)  # [[id|display]] -> display
    text = re.sub(r"\{[a-z0-9_]+\}", "", text)                       # drop {placeholders}
    return [s.strip() for s in re.split(r"[.:]\s+", text) if s.strip()]


def test_market_narratives_loads_six_states():
    """All 6 F16 states load with 2-3 DRAFT variants and a source ref (governance)."""
    data = json.loads(NARR_ROOT_JSON.read_text(encoding="utf-8"))
    states = data["states"]
    assert len(states) == 6, f"expected 6 states, got {len(states)}"
    assert {s["id"] for s in states.values()} == _NARR_STATE_IDS
    assert data.get("disclaimer"), "missing top-level disclaimer"
    for sid, state in states.items():
        assert state.get("_source_ref"), f"{sid} missing _source_ref (verified-numbers rule)"
        variants = state["variants"]
        assert 2 <= len(variants) <= 3, f"{sid} must have 2-3 variants, got {len(variants)}"
        for v in variants:
            assert v.startswith("DRAFT"), f"{sid} variant missing DRAFT marker"


def test_frontend_narratives_match_root():
    """The bundled frontend narratives must match the locked root file exactly."""
    root = json.loads(NARR_ROOT_JSON.read_text(encoding="utf-8"))
    fe = json.loads(NARR_FRONTEND_JSON.read_text(encoding="utf-8"))
    assert fe == root, "frontend market narratives drifted from the locked root file"


def test_narratives_no_em_dash():
    """No em dash (U+2014) anywhere in the narratives copy (all strings)."""
    blob = NARR_ROOT_JSON.read_text(encoding="utf-8")
    assert "—" not in blob, "em dash in market narratives copy"


def test_narratives_no_imperative_verbs():
    """No narrative sentence opens with an imperative verb (descriptive language only)."""
    data = json.loads(NARR_ROOT_JSON.read_text(encoding="utf-8"))
    offenders = []
    for sid, variant in _narr_variants(data):
        for sent in _narr_sentences(variant):
            first = re.sub(r"^[^A-Za-z']+", "", sent).split(" ")[0].lower().strip(".,")
            if first in _IMPERATIVE_VERBS:
                offenders.append(f"{sid}: '{sent[:40]}'")
    assert not offenders, "imperative-opening narrative sentences: " + "; ".join(offenders)


def test_narratives_no_forbidden_trade_terms():
    """SL / TP / ENTRY must not appear in narrative copy (FX3 red line)."""
    blob = NARR_ROOT_JSON.read_text(encoding="utf-8")
    assert not _FORBIDDEN_TRADE_TERMS.search(blob), "forbidden trade term in market narratives"


def test_narratives_imperative_guard_meta():
    """Meta-test: the imperative guard catches an opener and ignores descriptive verbs."""
    bad = {"states": {"X": {"variants": ["DRAFT. Buy the dip now."]}}}
    assert any(
        re.sub(r"^[^A-Za-z']+", "", s).split(" ")[0].lower().strip(".,") in _IMPERATIVE_VERBS
        for _, v in _narr_variants(bad) for s in _narr_sentences(v)
    )
    good = {"states": {"X": {"variants": ["DRAFT. {coin} cleared the checks this scan."]}}}
    assert not any(
        re.sub(r"^[^A-Za-z']+", "", s).split(" ")[0].lower().strip(".,") in _IMPERATIVE_VERBS
        for _, v in _narr_variants(good) for s in _narr_sentences(v)
    )
