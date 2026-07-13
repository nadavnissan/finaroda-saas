// Concept Tooltip content — loaded from the LOCKED root file concept_tooltips_content.json
// (this is a verbatim bundled copy; a pytest drift-guard asserts it matches root).
//
// Each term: { term, what, now (template), academy }. The `now` template uses:
//   {key}                         -> ctx[key] (empty string if missing, gracefully)
//   {a: 'text' | b: 'text2'}      -> the branch whose label is TRUTHY in ctx
// Placeholders inside a chosen branch are resolved recursively.
import content from "./concept_tooltips_content.json";

export { renderNow } from "./tooltipTemplate";

export interface TermContent {
  term: string;
  what: string;
  now: string;
  academy: string;
}

const TERMS = (content as { terms: Record<string, TermContent> }).terms;

export function getTerm(id: string): TermContent | null {
  return TERMS[id] ?? null;
}

export function termCount(): number {
  return Object.keys(TERMS).length;
}

// B6 Academy: the seed material for a module is its related terms' plain-language
// `what` content (no invented lessons this phase). Grouped by the `academy` id.
export interface AcademyTerm {
  id: string;
  term: string;
  what: string;
}

export function termsByAcademy(academyId: string): AcademyTerm[] {
  return Object.entries(TERMS)
    .filter(([, t]) => t.academy === academyId)
    .map(([id, t]) => ({ id, term: t.term, what: t.what }));
}
