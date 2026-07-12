// Copy helpers. Product copy rule (Nadav, 12/07): no em dashes anywhere.

const NBSP = String.fromCharCode(0xa0); // non-breaking space

// Prevent single-word orphans on the last line: bind the last two words with a
// non-breaking space so a heading/paragraph never breaks one word onto its own line.
export function noOrphan(s: string): string {
  const idx = s.lastIndexOf(" ");
  if (idx <= 0) return s;
  return s.slice(0, idx) + NBSP + s.slice(idx + 1);
}
