// Analysis Lens (PRD §3.5.3) — DISPLAY ONLY. The engine and (future) score are
// identical across lenses. The lens changes (a) which extra panel is shown, and
// (b) the INTERIM visibility condition used only while the score is pending.
//
// RED LINE (§3.5.5): the lens NEVER changes the score, weights, edge, or threshold.

import type { Blueprint, Lens } from "./types";

export const LENSES: Lens[] = ["EMA200", "RSI", "Volume", "Full"];

// Interim visibility rule (documented). While the numeric score is pending (pass 2),
// a coin is shown if its levels are valid AND the lens condition holds. When the real
// score arrives, SCORE_GATE_ENABLED flips and 85/82 replaces this rule entirely.
export function lensCondition(lens: Lens, bp: Blueprint): boolean {
  switch (lens) {
    case "EMA200":
      // Trend alignment with the macro EMA (via the verified slope direction).
      return bp.direction === "long" ? bp.ema7SlopePct > 0 : bp.ema7SlopePct < 0;
    case "RSI":
      // Room to move in the trade direction (not already exhausted).
      return bp.direction === "long" ? bp.rsi < 70 : bp.rsi > 30;
    case "Volume":
      // Above-average participation.
      return bp.volumeRatio >= 1;
    case "Full":
    default:
      return true;
  }
}

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
