"use client";

import { LENSES } from "@/lib/scan/lens";
import type { Lens, RiskStyle } from "@/lib/scan/types";

const RISK_STYLES: RiskStyle[] = ["Conservative", "Balanced", "Aggressive"];

const segStyle: React.CSSProperties = {
  display: "flex",
  gap: 4,
  flexWrap: "wrap",
  justifyContent: "center",
};

function seg(active: boolean): React.CSSProperties {
  return {
    padding: "4px 10px",
    fontFamily: "monospace",
    fontSize: 12,
    borderRadius: 6,
    border: "1px solid #2a2f37",
    background: active ? "#1FB286" : "transparent",
    color: active ? "#0b0d12" : "#8593A2",
    cursor: "pointer",
  };
}

// Analysis Lens — DISPLAY ONLY (PRD §3.5.3). Never changes the score.
export function LensToggle({ value, onChange }: { value: Lens; onChange: (l: Lens) => void }) {
  return (
    <div>
      <small style={{ color: "#8593A2" }}>Analysis Lens (display only)</small>
      <div style={segStyle}>
        {LENSES.map((l) => (
          <button key={l} style={seg(l === value)} onClick={() => onChange(l)} type="button">
            {l}
          </button>
        ))}
      </div>
    </div>
  );
}

// Risk Style — affects OUTPUT geometry only, never the score (PRD §3.5.4).
export function RiskStyleToggle({
  value,
  onChange,
}: {
  value: RiskStyle;
  onChange: (s: RiskStyle) => void;
}) {
  return (
    <div>
      <small style={{ color: "#8593A2" }}>Risk Style (levels only, not score)</small>
      <div style={segStyle}>
        {RISK_STYLES.map((s) => (
          <button key={s} style={seg(s === value)} onClick={() => onChange(s)} type="button">
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
