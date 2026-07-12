// Haptic feedback on SCAN with a SILENT fallback where unsupported
// (iOS Safari does not implement the Vibration API — no buzz, no error, no block).
export function vibrateScan(): void {
  if (typeof navigator === "undefined") return;
  const nav = navigator as Navigator & { vibrate?: (pattern: number | number[]) => boolean };
  if (typeof nav.vibrate !== "function") return; // silent fallback
  try {
    nav.vibrate(12); // gentle; never blocks or alters the scan
  } catch {
    // ignore — feedback is purely cosmetic
  }
}
