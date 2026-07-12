"use client";

import { lensPanel } from "@/lib/scan/lens";
import type { Blueprint, Lens, Level, RiskStyle } from "@/lib/scan/types";

import { RiskStyleToggle } from "./Controls";

function fmt(n: number): string {
  if (!isFinite(n)) return "-";
  const abs = Math.abs(n);
  const digits = abs >= 100 ? 2 : abs >= 1 ? 3 : 6;
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function LevelRow({ label, level }: { label: string; level: Level }) {
  return (
    <div style={{ padding: "8px 0", borderBottom: "1px solid #1b2028" }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "monospace" }}>
        <span style={{ color: "#8593A2" }}>{label}</span>
        <span>
          {fmt(level.value)}
          {level.pct != null ? `  (${level.pct >= 0 ? "+" : ""}${level.pct.toFixed(2)}%)` : ""}
        </span>
      </div>
      <small style={{ color: "#5c6672" }}>{level.note}</small>
    </div>
  );
}

// The Trading Blueprint (PRD §3.5.1 terminology — MANDATORY). Score is pending pass 2.
export function TradingBlueprint({
  bp,
  lens,
  onRiskStyle,
  onClose,
}: {
  bp: Blueprint;
  lens: Lens;
  onRiskStyle: (s: RiskStyle) => void;
  onClose: () => void;
}) {
  const panel = lensPanel(lens, bp);
  const dirColor = bp.direction === "long" ? "#1FB286" : "#E0913F";

  return (
    <div
      style={{
        position: "fixed",
        left: 0,
        right: 0,
        bottom: 0,
        maxWidth: 480,
        margin: "0 auto",
        background: "#161B22",
        border: "1px solid #2a2f37",
        borderRadius: "16px 16px 0 0",
        padding: 20,
        textAlign: "left",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>
          {bp.coin} <span style={{ color: dirColor }}>{bp.direction.toUpperCase()}</span>
        </h2>
        <button type="button" onClick={onClose} style={{ background: "none", color: "#8593A2", border: "none", cursor: "pointer" }}>
          ✕
        </button>
      </div>
      <div style={{ color: "#8593A2", fontFamily: "monospace", fontSize: 13 }}>Trading Blueprint</div>

      {/* Real momentum-profile score + SaaS 85/82 gate. */}
      <div
        style={{
          margin: "10px 0",
          padding: "8px 10px",
          background: "#0b0d12",
          borderRadius: 8,
          display: "flex",
          justifyContent: "space-between",
          fontFamily: "monospace",
        }}
      >
        <span>Score {bp.score}/100</span>
        <span style={{ color: bp.passLabel === "PASS" ? "#1FB286" : "#E0913F" }}>
          {bp.passLabel === "PASS" ? "PASS ≥85" : "WATCH 82–84"}
        </span>
      </div>

      {/* Verified / collected indicators */}
      <div style={{ fontFamily: "monospace", fontSize: 13, color: "#8593A2" }}>
        EMA7 slope (verified): {bp.ema7SlopePct >= 0 ? "+" : ""}
        {bp.ema7SlopePct.toFixed(2)}% · Volume (collected): {bp.volumeRatio.toFixed(2)}×
        {bp.riskReward != null ? ` · R:R 1:${bp.riskReward}` : ""}
      </div>
      {panel && (
        <div style={{ fontFamily: "monospace", fontSize: 13, color: "#8593A2" }}>
          {panel.label}: {panel.value}
        </div>
      )}

      {/* Calculated levels (PRD §3.5.1 + §3.5.2 transparency notes) */}
      <div style={{ marginTop: 10 }}>
        <LevelRow label="Mathematical Trigger Point" level={bp.mathematicalTriggerPoint} />
        <LevelRow label="Calculated Risk Level" level={bp.calculatedRiskLevel} />
        <LevelRow label="Dynamic Risk Level" level={bp.dynamicRiskLevel} />
        <LevelRow label="Calculated Target Level" level={bp.calculatedTargetLevel} />
      </div>

      <div style={{ marginTop: 12 }}>
        <RiskStyleToggle value={bp.riskStyle} onChange={onRiskStyle} />
      </div>

      <small style={{ display: "block", marginTop: 12, color: "#5c6672" }}>
        Analysis, not financial advice. Hypothetical. You decide.
      </small>
    </div>
  );
}
