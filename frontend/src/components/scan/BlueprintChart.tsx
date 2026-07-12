"use client";

import { EpisodeChart, type BlueprintLevels, type ChartAnnotation } from "@/components/onboarding/EpisodeChart";
import { C, type Candle } from "@/lib/onboarding/types";
import type { ChartLayers } from "@/lib/scan/entitlements";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";

function Chip({ text, color, filled, locked }: { text: string; color: string; filled?: boolean; locked?: boolean }) {
  return (
    <span
      style={{
        font: `600 8px ${MONO}`,
        color: filled ? C.bg : locked ? C.muted : C.fg,
        background: filled ? color : "transparent",
        border: filled ? "none" : locked ? `1px dashed rgba(133,147,162,.4)` : `1px solid rgba(233,238,243,.3)`,
        borderRadius: 3,
        padding: "2px 7px",
      }}
    >
      {locked ? "🔒 " : ""}
      {text}
    </span>
  );
}

// Chart Standard v1 with E7 layer gating. Free = chart + EMA200 only (EMA7 &
// Blueprint levels locked → SEE PLANS). Paid = all layers (EMA7 + drawn levels +
// swing S/R). Same underlying EpisodeChart component either way.
export function BlueprintChart({
  candles,
  symbol,
  dateRange,
  layers,
  blueprint,
  annotations = [],
  lensStyle,
  onSeePlans,
}: {
  candles: Candle[];
  symbol: string;
  dateRange?: string;
  layers: ChartLayers;
  blueprint?: BlueprintLevels;
  annotations?: ChartAnnotation[];
  lensStyle?: string; // e.g. "LENS: FULL · BALANCED"
  onSeePlans?: () => void;
}) {
  const full = layers === "full";
  return (
    <div style={{ margin: "10px 16px 0", background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 12, padding: "10px 8px 6px" }}>
      <div style={{ display: "flex", gap: 6, padding: "0 4px 8px", alignItems: "center", flexWrap: "wrap" }}>
        <Chip text="EMA200" color={C.green} filled />
        <Chip text="EMA7" color={C.amber} filled={full} locked={!full} />
        <Chip text="LEVELS" color={C.fg} locked={!full} />
        <span style={{ font: `400 8px ${MONO}`, color: C.muted, marginLeft: "auto" }}>
          {full ? lensStyle ?? "ALL LAYERS" : "FREE · EMA200 ONLY"}
        </span>
      </div>

      <EpisodeChart
        data={candles}
        entryIndex={-1}
        emaMode={full ? "both" : "ema200"}
        symbol={symbol}
        dateRange={dateRange}
        annotations={full ? annotations : []}
        blueprint={full ? blueprint : undefined}
        showSwingLevels={full}
      />

      {!full && (
        <div
          style={{
            margin: "12px 0 2px",
            background: "rgba(31,178,134,.06)",
            border: `1px solid rgba(31,178,134,.3)`,
            borderRadius: 10,
            padding: "12px 14px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 10,
          }}
        >
          <span style={{ font: `400 11px 'Space Grotesk', system-ui, sans-serif`, color: C.muted, lineHeight: 1.5 }}>
            EMA7 timing and the Blueprint levels drawn on the chart are paid layers.
          </span>
          <button
            type="button"
            onClick={onSeePlans}
            style={{ flex: "none", font: `600 10px ${MONO}`, color: C.bg, background: C.green, border: "none", borderRadius: 7, padding: "8px 12px", cursor: "pointer" }}
          >
            SEE PLANS
          </button>
        </div>
      )}
    </div>
  );
}
