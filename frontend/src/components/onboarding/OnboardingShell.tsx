"use client";

import type { ReactNode } from "react";

import { C } from "@/lib/onboarding/types";

import { Disclaimer } from "./Disclaimer";
import { XPMeter } from "./XPMeter";

// Consistent onboarding frame: context strip + XP header, card body, and the
// mandatory "Analysis, not financial advice." footer on EVERY screen.
export function OnboardingShell({
  xp,
  contextLine,
  children,
}: {
  xp: number;
  contextLine?: string;
  children: ReactNode;
}) {
  return (
    <div style={{ width: "100%", maxWidth: 480, margin: "0 auto", display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <small style={{ color: C.subtle, fontFamily: "monospace", fontSize: 11, textAlign: "left", flex: 1 }}>
          {contextLine ?? "Educational simulation · real dated market data"}
        </small>
        <XPMeter total={xp} />
      </div>
      <div
        style={{
          background: C.panel,
          border: `1px solid ${C.border}`,
          borderRadius: 12,
          padding: 20,
          textAlign: "center",
        }}
      >
        {children}
        <Disclaimer />
      </div>
    </div>
  );
}
