"use client";

import { C } from "@/lib/onboarding/types";
import { levelFor, two } from "@/lib/onboarding/xp";

const HEX = "polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)";
const MONO = "'IBM Plex Mono', ui-monospace, monospace";

// Compact terminal header: hexagon rank badge + rank name + XP + progress toward
// the next rank (XP_ECONOMY ladder). Mono numerals, high-contrast (no gray-on-black
// caption). Replaces the old XP bar + gray caption row.
export function LevelMeter({ xp }: { xp: number }) {
  const s = levelFor(xp);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, fontFamily: MONO }}>
      <div
        style={{
          width: 30,
          height: 34,
          flex: "none",
          background: "rgba(31,178,134,0.08)",
          border: `1.5px solid ${C.green}`,
          clipPath: HEX,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: C.green,
          fontWeight: 700,
          fontSize: 13,
        }}
      >
        {two(s.level)}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 168 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
          <span style={{ color: C.green, fontSize: 10, fontWeight: 600, letterSpacing: 1 }}>
            LVL {two(s.level)} · {s.name.toUpperCase()}
          </span>
          <span style={{ color: C.fg, fontSize: 11, fontWeight: 600 }}>{xp.toLocaleString()} XP</span>
        </div>
        <div style={{ width: "100%", height: 5, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 3, overflow: "hidden" }}>
          <div style={{ width: `${s.progressPct}%`, height: "100%", background: C.green, transition: "width 0.5s ease" }} />
        </div>
        <span style={{ color: C.muted, fontSize: 9 }}>
          {s.next
            ? `${xp.toLocaleString()} / ${s.next.floor.toLocaleString()} → LVL ${two(s.next.level)} ${s.next.name}`
            : "Top rank reached"}
        </span>
      </div>
    </div>
  );
}
