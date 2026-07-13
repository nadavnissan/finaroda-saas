"use client";

import { C } from "@/lib/onboarding/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";

// Streaming terminal log during scanning (UX.md §3 / B1b): the SAME locked 4-step
// animation the user met in onboarding S2. Three states: done ✓ / running ▸ / queued ·
export const SCAN_STEPS = [
  "Downloading tickers",
  "Analyzing candles",
  "Computing volume",
  "Scoring setups",
];

export function ScanningLog({ step, markets = 10 }: { step: number; markets?: number }) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 30, padding: "0 28px" }}>
      <div
        style={{
          width: 158,
          height: 158,
          borderRadius: "50%",
          background: "radial-gradient(circle at 38% 32%,#1c2530,#10151c 70%)",
          border: "1px solid rgba(31,178,134,.45)",
          boxShadow: "0 0 42px rgba(31,178,134,.18), inset 0 0 30px rgba(31,178,134,.07)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 6,
        }}
      >
        <div style={{ font: `600 12px ${MONO}`, letterSpacing: 3, color: C.green }}>SCANNING</div>
        <div style={{ font: `400 8.5px ${MONO}`, color: C.muted }}>{markets} COINS · BYBIT LIVE</div>
      </div>
      <div
        style={{
          width: "100%",
          background: C.panel,
          border: `1px solid rgba(233,238,243,.08)`,
          borderRadius: 12,
          padding: "16px 18px",
          display: "flex",
          flexDirection: "column",
          gap: 11,
          font: `400 12px ${MONO}`,
        }}
      >
        {SCAN_STEPS.map((label, i) => {
          const done = i < step;
          const running = i === step;
          return (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 10, color: running ? C.green : done ? C.fg : C.muted }}>
              <span style={{ color: done ? C.green : running ? C.green : C.muted, fontWeight: 600 }}>
                {done ? "✓" : running ? "▸" : "·"}
              </span>
              {label}
              {running && <span style={{ display: "inline-block", width: 7, height: 13, background: C.green }} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
