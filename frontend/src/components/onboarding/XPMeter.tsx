"use client";

import { C, XP_TARGET } from "@/lib/onboarding/types";

// XP meter shown in the onboarding header. XP measures discipline & learning only
// (XP_ECONOMY.md) — never profit, frequency, or streaks.
export function XPMeter({ total, target = XP_TARGET }: { total: number; target?: number }) {
  const pct = Math.min(100, Math.round((total / target) * 100));
  return (
    <div style={{ width: 220, fontFamily: "monospace" }}>
      <div style={{ display: "flex", justifyContent: "space-between", color: C.green, fontSize: 13 }}>
        <span>XP</span>
        <span>
          {total} / {target}
        </span>
      </div>
      <div
        style={{
          width: "100%",
          height: 6,
          background: C.bg,
          border: `1px solid ${C.border}`,
          borderRadius: 4,
          overflow: "hidden",
          marginTop: 4,
        }}
      >
        <div style={{ width: `${pct}%`, height: "100%", background: C.green, transition: "width 0.5s ease" }} />
      </div>
    </div>
  );
}
