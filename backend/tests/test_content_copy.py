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


# ── F16b Outcome Narratives: resolved-scenario states (same governance) ─────────
# R1/R2/R3 ship LIVE; R4/R5 are BUILT but gated behind FEATURE_ARENA (default OFF) for
# F17. All five share the F16 locked-file governance. The whole-blob em-dash and
# forbidden-trade-term guards above already cover resolved_states (they read the file
# text); these add the structural + imperative + foreseeability + no-XP guards.
_RESOLVED_STATE_IDS = {"R1", "R2", "R3", "R4", "R5"}
_GATED_STATE_IDS = {"R4", "R5"}


def _narr_resolved_variants(data: dict) -> list:
    """All (state_id, variant_text) pairs across resolved_states (skips the _note key)."""
    out = []
    for sid, state in data["resolved_states"].items():
        if sid.startswith("_"):
            continue
        for v in state["variants"]:
            out.append((sid, v))
    return out


def test_resolved_states_load_five_states():
    """R1..R5 load with 2-3 DRAFT variants, a source ref, and the correct live/gated flag."""
    data = json.loads(NARR_ROOT_JSON.read_text(encoding="utf-8"))
    resolved = {k: v for k, v in data["resolved_states"].items() if not k.startswith("_")}
    assert len(resolved) == 5, f"expected 5 resolved states, got {len(resolved)}"
    assert {s["id"] for s in resolved.values()} == _RESOLVED_STATE_IDS
    for sid, state in resolved.items():
        assert state.get("_source_ref"), f"{sid} missing _source_ref (verified-numbers rule)"
        assert isinstance(state.get("live"), bool), f"{sid} missing live flag"
        # R4/R5 must be gated behind FEATURE_ARENA; R1/R2/R3 must be live.
        gated = state["id"] in _GATED_STATE_IDS
        assert state["live"] is (not gated), f"{state['id']} live flag wrong (gated={gated})"
        if gated:
            assert state.get("flag") == "FEATURE_ARENA", f"{state['id']} must name FEATURE_ARENA"
        variants = state["variants"]
        assert 2 <= len(variants) <= 3, f"{sid} must have 2-3 variants, got {len(variants)}"
        for v in variants:
            assert v.startswith("DRAFT"), f"{sid} variant missing DRAFT marker"


def test_resolved_narratives_no_imperative_verbs():
    """No resolved-narrative sentence opens with an imperative verb (descriptive only)."""
    data = json.loads(NARR_ROOT_JSON.read_text(encoding="utf-8"))
    offenders = []
    for sid, variant in _narr_resolved_variants(data):
        for sent in _narr_sentences(variant):
            first = re.sub(r"^[^A-Za-z']+", "", sent).split(" ")[0].lower().strip(".,")
            if first in _IMPERATIVE_VERBS:
                offenders.append(f"{sid}: '{sent[:40]}'")
    assert not offenders, "imperative-opening resolved sentences: " + "; ".join(offenders)


def test_resolved_narratives_no_regret_framing():
    """R5 (and all resolved copy) must never frame a missed winner as regret / 'you should'."""
    data = json.loads(NARR_ROOT_JSON.read_text(encoding="utf-8"))
    banned = re.compile(r"should have|you should|regret|missed out|if only", re.IGNORECASE)
    offenders = [f"{sid}: '{v[:40]}'" for sid, v in _narr_resolved_variants(data) if banned.search(v)]
    assert not offenders, "regret framing in resolved narratives: " + "; ".join(offenders)


def test_foreseeability_affirmative_needs_a_flag():
    """The affirmative foreseeability line must carry a {placeholder} so it cannot render
    without a logged flag; the honest 'not_marked' line is a plain sentence. No such flag
    exists in journal_scenarios today, so only 'not_marked' ever renders (no manufactured
    hindsight)."""
    data = json.loads(NARR_ROOT_JSON.read_text(encoding="utf-8"))
    f = data["foreseeability"]
    assert f.get("not_marked") and f.get("marked")
    assert re.search(r"\{[a-z0-9_]+\}", f["marked"]), "affirmative line must require a flag placeholder"
    assert not re.search(r"\{[a-z0-9_]+\}", f["not_marked"]), "the honest default must be flag-free"


def test_resolved_narratives_no_new_xp_source():
    """F16b is pure display: its copy must not reference XP (zero new XP sources)."""
    data = json.loads(NARR_ROOT_JSON.read_text(encoding="utf-8"))
    blob = json.dumps(data["resolved_states"]) + json.dumps(data["foreseeability"])
    assert not re.search(r"\bxp\b", blob, re.IGNORECASE), "F16b copy must not reference XP"
