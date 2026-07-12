// Concept Tooltip content (F14 / E1) — SINGLE source file, keyed by term id.
//
// IMPORTANT: `whatItMeasures` is intentionally left EMPTY. Per the internal guide,
// Nadav supplies the plain-language definitions (35+ terms) — they are NOT written
// here (empirical-truth / no invented copy). Until a definition is supplied the
// bubble shows a neutral "pending" line, never a fabricated explanation.
//
// The contextual "what it means here, right now" line is passed by the caller at
// each usage site (it is per-screen context, not static content).

export interface ConceptContent {
  id: string;
  term: string; // display label (not a definition)
  whatItMeasures: string; // PLACEHOLDER — filled by Nadav from the internal guide
  academyHref: string; // deep-link to the full Academy lesson (F6)
}

function pending(id: string, term: string): ConceptContent {
  return { id, term, whatItMeasures: "", academyHref: `/academy#${id}` };
}

// Onboarding surface terms (extend to the full 35+ as the guide is supplied).
export const CONCEPTS: Record<string, ConceptContent> = {
  ema200: pending("ema200", "200-day average"),
  "ema7-slope": pending("ema7-slope", "EMA7 slope"),
  "pass-watch": pending("pass-watch", "PASS / WATCH"),
  threshold: pending("threshold", "threshold"),
  "mathematical-trigger-point": pending("mathematical-trigger-point", "Mathematical Trigger Point"),
  "calculated-risk-level": pending("calculated-risk-level", "Calculated Risk Level"),
  "calculated-target-level": pending("calculated-target-level", "Calculated Target Level"),
  "dynamic-risk-level": pending("dynamic-risk-level", "Dynamic Risk Level"),
  "r-multiple": pending("r-multiple", "R multiple"),
  "volume-ratio": pending("volume-ratio", "volume ratio"),
  "weekly-structure": pending("weekly-structure", "weekly structure"),
  regime: pending("regime", "market regime"),
};

export function getConcept(id: string): ConceptContent {
  return CONCEPTS[id] ?? pending(id, id);
}
