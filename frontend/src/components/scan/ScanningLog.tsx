"use client";

// Streaming terminal log during scanning (UX.md §3): 4 steps reveal in sequence.
export const SCAN_STEPS = [
  "Downloading tickers",
  "Analyzing candles",
  "Computing volume",
  "Scoring setups",
];

export function ScanningLog({ step }: { step: number }) {
  return (
    <div style={{ fontFamily: "monospace", textAlign: "left", minWidth: 240 }}>
      {SCAN_STEPS.map((label, i) => (
        <div key={label} style={{ color: i <= step ? "#1FB286" : "#3a3f47", padding: "2px 0" }}>
          {i < step ? "✓" : i === step ? "▸" : "·"} {label}
          {i === step ? "…" : ""}
        </div>
      ))}
    </div>
  );
}
