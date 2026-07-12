// Concept Tooltip content — loaded from the LOCKED root file concept_tooltips_content.json
// (this is a verbatim bundled copy; a pytest drift-guard asserts it matches root).
//
// Each term: { term, what, now (template), academy }. The `now` template uses:
//   {key}                         -> ctx[key] (empty string if missing, gracefully)
//   {a: 'text' | b: 'text2'}      -> the branch whose label is TRUTHY in ctx
// Placeholders inside a chosen branch are resolved recursively.
import content from "./concept_tooltips_content.json";

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

// ── template renderer ─────────────────────────────────────────────────────────

export function renderNow(template: string, ctx: Record<string, unknown> = {}): string {
  let out = "";
  let i = 0;
  while (i < template.length) {
    if (template[i] === "{") {
      const { inner, end } = readBraced(template, i);
      out += resolveToken(inner, ctx);
      i = end + 1;
    } else {
      out += template[i];
      i += 1;
    }
  }
  // collapse any double spaces left by empty placeholders
  return out.replace(/\s{2,}/g, " ").trim();
}

function readBraced(s: string, start: number): { inner: string; end: number } {
  let depth = 0;
  for (let j = start; j < s.length; j++) {
    if (s[j] === "{") depth += 1;
    else if (s[j] === "}") {
      depth -= 1;
      if (depth === 0) return { inner: s.slice(start + 1, j), end: j };
    }
  }
  return { inner: s.slice(start + 1), end: s.length - 1 };
}

function resolveToken(inner: string, ctx: Record<string, unknown>): string {
  // conditional group: starts with `label:` and contains a quoted branch
  if (/^\s*[a-zA-Z_]+\s*:/.test(inner) && inner.includes("'")) {
    for (const branch of splitTopLevel(inner, "|")) {
      const m = branch.match(/^\s*([a-zA-Z_]+)\s*:\s*'([\s\S]*)'\s*$/);
      if (!m) continue;
      const [, label, text] = m;
      if (ctx[label]) return renderNow(text, ctx); // first truthy branch wins
    }
    return ""; // no branch selected -> empty, gracefully
  }
  const v = ctx[inner.trim()];
  return v == null ? "" : String(v);
}

function splitTopLevel(s: string, sep: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let inQuote = false;
  let cur = "";
  for (const c of s) {
    if (c === "'") inQuote = !inQuote;
    else if (!inQuote && c === "{") depth += 1;
    else if (!inQuote && c === "}") depth -= 1;
    if (!inQuote && depth === 0 && c === sep) {
      parts.push(cur);
      cur = "";
    } else {
      cur += c;
    }
  }
  parts.push(cur);
  return parts;
}
