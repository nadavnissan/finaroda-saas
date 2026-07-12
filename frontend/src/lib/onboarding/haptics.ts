function vibrate(pattern: number | number[]): void {
  if (typeof navigator === "undefined") return;
  const nav = navigator as Navigator & { vibrate?: (p: number | number[]) => boolean };
  if (typeof nav.vibrate !== "function") return; // silent fallback (iOS Safari)
  try {
    nav.vibrate(pattern);
  } catch {
    // ignore — feedback is purely cosmetic
  }
}

// Subtle buzz on SCAN and XP-gain moments (E6). Silent where unsupported.
export function vibrateScan(): void {
  vibrate(12);
}

// Distinct celebratory pattern, ONLY on rank threshold crossings (never on XP gain).
export function vibrateLevelUp(): void {
  vibrate([18, 45, 30]);
}
