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


def test_em_dash_guard_ignores_comments_but_catches_copy():
    """Meta-test: the guard must NOT flag an em dash inside a JSX/block/line comment, but
    MUST flag one in rendered copy. Proves the lint is trustworthy (fixes the JSX gap)."""
    assert _strip_comments("{/* a — b */}") .strip() == "{}"        # JSX block comment stripped
    assert "—" not in _strip_comments("const x = 1; // note — here")  # line comment stripped
    assert "—" not in _strip_comments("/* multi\n line — c */")       # multi-line block stripped
    assert "—" in _strip_comments('const s = "price — value";')      # real copy survives
