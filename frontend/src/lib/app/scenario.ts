// Pure reveal-gating display logic for a journal scenario (B4). Extracted so the
// "unrevealed rows carry no outcome data" contract is unit-testable: for an unrevealed
// scenario this returns null, so the row has nothing to render but a blurred placeholder.

import type { ScenarioView } from "./types";

export interface Outcome {
  top: string;      // e.g. "+2.60R" | "SAVE"
  bottom: string;   // e.g. "WIN · REVEALED"
  tone: "green" | "red" | "muted";
}

// Returns the displayable outcome ONLY for a revealed scenario, else null.
export function scenarioOutcome(s: ScenarioView): Outcome | null {
  if (!s.revealed) return null;              // withheld: nothing to show
  if (s.status === "save") return { top: "SAVE", bottom: "LOSS AVOIDED", tone: "green" };
  if (s.status === "win") return { top: `+${(s.r_result ?? 0).toFixed(2)}R`, bottom: "WIN · REVEALED", tone: "green" };
  if (s.status === "loss") return { top: `${(s.r_result ?? -1).toFixed(2)}R`, bottom: "STOPPED", tone: "red" };
  const r = s.r_result ?? 0;
  return { top: `${r >= 0 ? "+" : ""}${r.toFixed(2)}R`, bottom: "CLOSED", tone: r >= 0 ? "green" : "red" };
}
