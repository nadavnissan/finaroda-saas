// Analysis Lens (PRD §3.5.3) — DISPLAY ONLY. Now that the real score gates visibility
// (85/82, SCORE_GATE_ENABLED), the lens changes ONLY which extra panel is shown. It
// never changes which coins pass, the score, weights, edge, or threshold (RED LINE §3.5.5).

import type { Blueprint, Lens } from "./types";

export const LENSES: Lens[] = ["EMA200", "RSI", "Volume", "Full"];

// Which extra panel the lens surfaces on the Blueprint (display only).
export function lensPanel(lens: Lens, bp: Blueprint): { label: string; value: string } | null {
  switch (lens) {
    case "RSI":
      return { label: "RSI(14)", value: bp.rsi.toFixed(1) };
    case "Volume":
      return { label: "Volume ratio", value: `${bp.volumeRatio.toFixed(2)}×` };
    case "EMA200":
      return { label: "EMA7 slope", value: `${bp.ema7SlopePct >= 0 ? "+" : ""}${bp.ema7SlopePct.toFixed(2)}%` };
    case "Full":
    default:
      return null;
  }
}
