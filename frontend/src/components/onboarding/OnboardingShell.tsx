"use client";

import type { ReactNode } from "react";

import { C } from "@/lib/onboarding/types";

import { Disclaimer } from "./Disclaimer";
import { LevelMeter } from "./LevelMeter";

// Consistent onboarding frame: a compact terminal LEVEL header, the card body, and
// the mandatory "Analysis, not financial advice." footer on EVERY screen. Episode
// context now lives on the chart header (not a low-contrast gray caption row).
export function OnboardingShell({ xp, children }: { xp: number; children: ReactNode }) {
  return (
    <div style={{ width: "100%", maxWidth: 480, margin: "0 auto", display: "flex", flexDirection: "column", gap: 12 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          background: C.panel,
          border: `1px solid ${C.border}`,
          borderRadius: 12,
          padding: "8px 12px",
        }}
      >
        <LevelMeter xp={xp} />
      </div>
      <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 12, padding: 20, textAlign: "center" }}>
        {children}
        <Disclaimer />
      </div>
    </div>
  );
}
