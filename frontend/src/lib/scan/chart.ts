// Chart data for the Trading Blueprint's Chart Standard v1 (B1d/B1e/B1g).
// Turns the scan's MarketData (raw daily OHLCV) into the Candle[] the shared
// EpisodeChart component draws - attaching per-candle EMA7/EMA200 series computed
// over the FULL history, then windowed to the last `count` candles. Display
// geometry only; the score/levels come from the engine, never from here.

import type { BlueprintLevels } from "@/components/onboarding/EpisodeChart";
import type { Candle } from "@/lib/onboarding/types";

import type { Blueprint, MarketData } from "./types";

// Rolling EMA (value at each index), seeded on the first close - same recurrence
// as the engine's calcEMA, kept per-step so the chart can draw the line.
function emaSeries(closes: number[], period: number): number[] {
  const mult = 2 / (period + 1);
  const out: number[] = [];
  let ema = closes.length ? closes[0] : 0;
  for (let i = 0; i < closes.length; i++) {
    ema = i === 0 ? closes[0] : (closes[i] - ema) * mult + ema;
    out.push(ema);
  }
  return out;
}

const DAY_MS = 86_400_000;

export function toChartCandles(md: MarketData, count = 28): Candle[] {
  const { o, h, l, c, v, t } = md.daily;
  const n = c.length;
  if (n === 0) return [];
  const ema7 = emaSeries(c, 7);
  const ema200 = emaSeries(c, 200);
  const start = Math.max(0, n - count);
  const candles: Candle[] = [];
  for (let i = start; i < n; i++) {
    // Real candle timestamps when Bybit provided them; else synthesize daily steps
    // backward from the newest candle (display axis only).
    const ts = t && t[i] != null ? t[i] : Date.now() - (n - 1 - i) * DAY_MS;
    candles.push({
      t: ts,
      o: o[i],
      h: h[i],
      l: l[i],
      c: c[i],
      v: v[i],
      ema7: ema7[i],
      ema200: ema200[i],
    });
  }
  return candles;
}

export function blueprintLevels(bp: Blueprint): BlueprintLevels {
  return {
    trigger: bp.mathematicalTriggerPoint.value,
    risk: bp.calculatedRiskLevel.value,
    target: bp.calculatedTargetLevel.value,
  };
}
