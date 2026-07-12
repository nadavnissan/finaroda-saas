"use client";

import { ConceptTooltip } from "@/components/onboarding/ConceptTooltip";
import { C } from "@/lib/onboarding/types";
import { toChartCandles } from "@/lib/scan/chart";
import type { ChartLayers } from "@/lib/scan/entitlements";
import type { Blueprint, MarketData } from "@/lib/scan/types";

import { AppHeader, Disclaimer } from "./AppHeader";
import { BlueprintChart } from "./BlueprintChart";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

// E7b - tapping a non-passing coin opens the SAME chart (layers per plan) plus a
// "why not" card naming ONLY the blocking check in plain language, with its Concept
// Tooltip. No score, weight or formula is shown. Snapshot (timestamped), not live.
export function NonPasser({
  bp,
  md,
  layers,
  xp,
  timestamp,
  onSeePlans,
  onClose,
}: {
  bp: Blueprint;
  md: MarketData;
  layers: ChartLayers;
  xp: number;
  timestamp: string;
  onSeePlans: () => void;
  onClose: () => void;
}) {
  const candles = toChartCandles(md);
  const why = bp.whyNot;
  const parts = why ? why.text.split(why.term) : [""];

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 40, background: C.bg, overflowY: "auto", display: "flex", flexDirection: "column" }}>
      <div style={{ maxWidth: 480, margin: "0 auto", width: "100%", display: "flex", flexDirection: "column", flex: 1 }}>
        <AppHeader xp={xp} left="close" onLeft={onClose} freeBadge={layers === "ema200_only"} />

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 20px 0" }}>
          <div style={{ font: `600 15px ${MONO}`, color: C.fg }}>
            {bp.coin} <span style={{ color: C.muted, fontWeight: 400 }}>- NO PASS</span>
          </div>
          <div style={{ font: `400 9px ${MONO}`, color: C.muted }}>SNAPSHOT · {timestamp}</div>
        </div>

        <BlueprintChart candles={candles} symbol={bp.coin} layers={layers} onSeePlans={onSeePlans} />

        {why && (
          <div style={{ margin: "12px 16px 0", background: C.panel, border: `1px solid rgba(224,145,63,.35)`, borderRadius: 12, padding: "13px 15px", display: "flex", flexDirection: "column", gap: 7 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ font: `600 8.5px ${MONO}`, letterSpacing: 2, color: C.amber }}>WHY NOT</span>
              <span style={{ font: `400 8.5px ${MONO}`, color: C.muted }}>blocking check: {why.checkLabel}</span>
            </div>
            <div style={{ font: `400 13px ${SANS}`, color: C.fg, lineHeight: 1.6 }}>
              {parts[0]}
              <ConceptTooltip id={why.tooltipId} label={why.term} />
              {parts[1] ?? ""}
            </div>
            <div style={{ font: `400 9.5px ${MONO}`, color: C.muted }}>Every skip is a lesson - tap the term to learn the check.</div>
          </div>
        )}

        <div style={{ marginTop: "auto" }}>
          <Disclaimer />
        </div>
      </div>
    </div>
  );
}
