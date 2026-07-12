"""Content + copy-rule guards (Nadav, 12/07).

- The concept-tooltip content loads all 46 terms with the required shape.
- The frontend bundled copy is byte-identical to the locked root file (drift guard).
- No em dashes in product copy: greps frontend/src for U+2014 inside strings/JSX
  (comments excluded, since only rendered copy is "product copy").
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROOT_JSON = ROOT / "concept_tooltips_content.json"
FRONTEND_JSON = ROOT / "frontend" / "src" / "lib" / "onboarding" / "concept_tooltips_content.json"
FRONTEND_SRC = ROOT / "frontend" / "src"


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
    violations = []
    for f in FRONTEND_SRC.rglob("*"):
        if f.suffix not in (".ts", ".tsx"):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith(("*", "//", "/*")):
                continue  # comment line
            code = line.split("//")[0]  # drop trailing line comment
            if "—" in code:
                violations.append(f"{f.relative_to(ROOT)}:{i}")
    assert not violations, "em dashes in product copy: " + ", ".join(violations)
