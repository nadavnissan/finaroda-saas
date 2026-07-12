"use client";

import { ConceptTooltip } from "@/components/onboarding/ConceptTooltip";
import { C } from "@/lib/onboarding/types";
import type { Lens, RiskStyle } from "@/lib/scan/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";

const LENSES: Lens[] = ["EMA200", "RSI", "Volume", "Full"];
const RISK_STYLES: RiskStyle[] = ["Conservative", "Balanced", "Aggressive"];

function seg<T extends string>(value: T, opt: T, onChange: (v: T) => void, key: string) {
  const active = value === opt;
  return (
    <button
      key={key}
      type="button"
      onClick={() => onChange(opt)}
      style={{
        flex: 1,
        padding: "7px 4px",
        font: `600 9.5px ${MONO}`,
        letterSpacing: 0.3,
        color: active ? C.bg : C.fg,
        background: active ? C.green : C.panel,
        border: `1px solid ${active ? C.green : C.border}`,
        borderRadius: 7,
        cursor: "pointer",
        whiteSpace: "nowrap",
      }}
    >
      {opt.toUpperCase()}
    </button>
  );
}

// E9 Horizon selector - SWING active from v1; POSITION locked with the approved
// copy + its Concept Tooltip (the full validation sentence).
export function HorizonSelector() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <span style={{ font: `600 8.5px ${MONO}`, letterSpacing: 2, color: C.muted }}>HORIZON</span>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <div
          style={{
            height: 46,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 1,
            background: "rgba(31,178,134,.1)",
            border: `1px solid ${C.green}`,
            borderRadius: 9,
          }}
        >
          <span style={{ font: `600 11px ${MONO}`, letterSpacing: 1, color: C.green }}>SWING</span>
          <span style={{ font: `400 8.5px ${MONO}`, color: C.muted }}>1–7 DAYS</span>
        </div>
        <div
          style={{
            height: 46,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 1,
            background: C.panel,
            border: `1px solid ${C.border}`,
            borderRadius: 9,
            opacity: 0.75,
          }}
        >
          <span style={{ font: `600 11px ${MONO}`, letterSpacing: 1, color: C.muted }}>
            🔒 <ConceptTooltip id="horizon" label="POSITION" />
          </span>
          <span style={{ font: `400 8.5px ${MONO}`, color: C.muted }}>WEEKS+</span>
        </div>
      </div>
      <span style={{ font: `400 10px ${MONO}`, color: C.muted, textAlign: "right" }}>
        In validation. Unlocks when it earns it.
      </span>
    </div>
  );
}

export function LensSelect({ value, onChange }: { value: Lens; onChange: (l: Lens) => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <span style={{ font: `600 7.5px ${MONO}`, letterSpacing: 1.5, color: C.muted }}>
        <ConceptTooltip id="analysis_lens" label="ANALYSIS LENS" />
      </span>
      <div style={{ display: "flex", gap: 5 }}>{LENSES.map((l) => seg(value, l, onChange, l))}</div>
    </div>
  );
}

export function RiskStyleSelect({ value, onChange }: { value: RiskStyle; onChange: (s: RiskStyle) => void }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <span style={{ font: `600 7.5px ${MONO}`, letterSpacing: 1.5, color: C.muted }}>
        <ConceptTooltip id="risk_style" label="RISK STYLE" />
      </span>
      <div style={{ display: "flex", gap: 5 }}>{RISK_STYLES.map((s) => seg(value, s, onChange, s))}</div>
    </div>
  );
}

export function RedLineCaption() {
  return (
    <span style={{ font: `400 9.5px ${MONO}`, color: C.muted, textAlign: "center", lineHeight: 1.5 }}>
      Display &amp; geometry only - never what counts as an opportunity.
    </span>
  );
}
