// Tooltip `now`-template renderer. Pure, dependency-free (unit-tested).
//
//   {key}                    -> ctx[key]
//   {a: 'text' | b: 'text2'} -> the branch whose label is TRUTHY in ctx
//
// CONTEXT SUPPRESSION (Nadav 12/07): if ANY simple {key} placeholder is missing
// from ctx, the whole "now" line is suppressed (returns ""), so a half-filled or
// context-free line never renders (e.g. long_short on S1 before a choice is made).
// Static templates (no placeholders) always render.

export function renderNow(template: string, ctx: Record<string, unknown> = {}): string {
  const { text, ok } = render(template, ctx);
  return ok ? text.replace(/\s{2,}/g, " ").trim() : "";
}

function render(template: string, ctx: Record<string, unknown>): { text: string; ok: boolean } {
  let text = "";
  let ok = true;
  let i = 0;
  while (i < template.length) {
    if (template[i] === "{") {
      const { inner, end } = readBraced(template, i);
      const r = resolveToken(inner, ctx);
      text += r.text;
      ok = ok && r.ok;
      i = end + 1;
    } else {
      text += template[i];
      i += 1;
    }
  }
  return { text, ok };
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

function resolveToken(inner: string, ctx: Record<string, unknown>): { text: string; ok: boolean } {
  // conditional group: `label: 'text' | label2: 'text2'`
  if (/^\s*[a-zA-Z_]+\s*:/.test(inner) && inner.includes("'")) {
    for (const branch of splitTopLevel(inner, "|")) {
      const m = branch.match(/^\s*([a-zA-Z_]+)\s*:\s*'([\s\S]*)'\s*$/);
      if (!m) continue;
      const [, label, text] = m;
      if (ctx[label]) return render(text, ctx); // first truthy branch wins
    }
    return { text: "", ok: true }; // no branch selected is fine (optional colour)
  }
  // simple {key}: missing value suppresses the whole line
  const v = ctx[inner.trim()];
  if (v == null || v === "") return { text: "", ok: false };
  return { text: String(v), ok: true };
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
