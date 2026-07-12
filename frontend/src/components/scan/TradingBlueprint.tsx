"use client";

import { ConceptTooltip } from "@/components/onboarding/ConceptTooltip";
import { C } from "@/lib/onboarding/types";
import { blueprintLevels, toChartCandles } from "@/lib/scan/chart";
import type { ChartLayers } from "@/lib/scan/entitlements";
import type { Blueprint, Level, Lens, MarketData, RiskStyle } from "@/lib/scan/types";

import { AppHeader, Disclaimer } from "./AppHeader";
import { BlueprintChart } from "./BlueprintChart";
import { RiskStyleSelect } from "./Controls";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

function fmt(n: number): string {
  if (!isFinite(n)) return "-";
  const abs = Math.abs(n);
  const digits = abs >= 100 ? 2 : abs >= 1 ? 3 : 6;
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function LevelCard({ label, level, accent, tooltip, noteTerm }: { label: string; level: Level; accent: string; tooltip: string; noteTerm?: { id: string; label: string } }) {
  return (
    <div style={{ background: C.bg, border: `1px solid ${accent}`, borderRadius: 8, padding: "9px 11px", display: "flex", flexDirection: "column", gap: 2 }}>
      <div style={{ font: `600 7.5px ${MONO}`, letterSpacing: 0.8, color: C.muted }}>
        <ConceptTooltip id={tooltip} label={label} />
      </div>
      <div style={{ font: `600 15px ${MONO}`, color: accent === C.border ? C.fg : accent }}>{fmt(level.value)}</div>
      <div style={{ font: `400 8.5px ${SANS}`, color: C.muted, lineHeight: 1.4 }}>
        {noteTerm ? (
          <>
            {level.note.split(noteTerm.label)[0]}
            <ConceptTooltip id={noteTerm.id} label={noteTerm.label} />
            {level.note.split(noteTerm.label)[1]}
          </>
        ) : (
          level.note
        )}
      </div>
    </div>
  );
}

// Trading Blueprint + Chart Standard (B1d paid / B1e free). Full-screen modal.
export function TradingBlueprint({
  bp,
  md,
  lens,
  layers,
  xp,
  onRiskStyle,
  onSeePlans,
  onClose,
}: {
  bp: Blueprint;
  md: MarketData;
  lens: Lens;
  layers: ChartLayers;
  xp: number;
  onRiskStyle: (s: RiskStyle) => void;
  onSeePlans: () => void;
  onClose: () => void;
}) {
  const dirColor = bp.direction === "long" ? C.green : C.red;
  const gate = bp.passLabel === "PASS" ? C.green : C.amber;
  const candles = toChartCandles(md);
  const lensStyle = `LENS: ${lens.toUpperCase()} · ${bp.riskStyle.toUpperCase()}`;

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 40, background: C.bg, overflowY: "auto", display: "flex", flexDirection: "column" }}>
      <div style={{ maxWidth: 480, margin: "0 auto", width: "100%", display: "flex", flexDirection: "column", flex: 1 }}>
        <AppHeader xp={xp} left="close" onLeft={onClose} freeBadge={layers === "ema200_only"} />

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 20px 0" }}>
          <div style={{ font: `600 15px ${MONO}`, color: C.fg }}>
            {bp.coin} <span style={{ color: dirColor }}>{bp.direction === "long" ? "↑ LONG" : "↓ SHORT"}</span>
          </div>
          <div style={{ font: `600 10px ${MONO}`, color: gate }}>
            {bp.passLabel === "PASS" ? "TIMING VERIFIED · " : "WATCH · "}
            {bp.score}/100
          </div>
        </div>

        <BlueprintChart
          candles={candles}
          symbol={bp.coin}
          layers={layers}
          blueprint={blueprintLevels(bp)}
          lensStyle={lensStyle}
          onSeePlans={onSeePlans}
        />

        {/* Trading Blueprint card (full on every plan - only chart layers are gated). */}
        <div style={{ margin: "12px 16px 0", background: C.panel, border: `1px solid rgba(31,178,134,.3)`, borderRadius: 14, overflow: "hidden" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "11px 16px", borderBottom: `1px solid rgba(233,238,243,.07)` }}>
            <div style={{ font: `700 12.5px ${SANS}`, color: C.fg }}>TRADING BLUEPRINT</div>
            <div style={{ font: `500 9px ${MONO}`, color: C.muted }}>
              <ConceptTooltip id="ema7_slope" label="EMA7 SLOPE" /> <span style={{ color: bp.ema7SlopePct >= 0 ? C.green : C.red }}>{bp.ema7SlopePct >= 0 ? "▲" : "▼"} verified</span>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, padding: "11px 14px" }}>
            <LevelCard label="MATHEMATICAL TRIGGER POINT" level={bp.mathematicalTriggerPoint} accent={C.border} tooltip="trigger_point" />
            <LevelCard label="CALCULATED RISK LEVEL" level={bp.calculatedRiskLevel} accent={C.red} tooltip="risk_level" noteTerm={{ id: "atr", label: "ATR14" }} />
            <LevelCard label="DYNAMIC RISK LEVEL" level={bp.dynamicRiskLevel} accent={C.border} tooltip="dynamic_risk" noteTerm={{ id: "dynamic_risk", label: "trailing" }} />
            <LevelCard label="CALCULATED TARGET LEVEL" level={bp.calculatedTargetLevel} accent={C.green} tooltip="target_level" noteTerm={{ id: "r_multiple", label: "R-multiple" }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "2px 16px 11px", font: `500 10px ${MONO}` }}>
            <span style={{ color: C.muted }}>
              <ConceptTooltip id="risk_reward" label="RISK:REWARD" />{" "}
              <span style={{ color: C.fg, fontWeight: 600 }}>{bp.riskReward != null ? `1:${bp.riskReward}` : "-"}</span>
            </span>
            <span style={{ color: C.muted }}>
              VOLUME <ConceptTooltip id="volume" label="collected" />
            </span>
          </div>
        </div>

        {/* Risk Style on the card → rebuild LEVELS only (score unchanged, RED LINE). */}
        <div style={{ padding: "12px 16px 0" }}>
          <RiskStyleSelect value={bp.riskStyle} onChange={onRiskStyle} />
        </div>

        <div style={{ marginTop: "auto" }}>
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}
