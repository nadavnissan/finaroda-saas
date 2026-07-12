"use client";

import { C } from "@/lib/onboarding/types";

// "Analysis, not financial advice." — mandatory on EVERY onboarding screen (AC / PRD §8.1).
export function Disclaimer() {
  return (
    <small style={{ display: "block", marginTop: 10, color: C.subtle, fontFamily: "monospace", fontSize: 11 }}>
      Analysis, not financial advice. Hypothetical, educational simulation. You decide.
    </small>
  );
}
