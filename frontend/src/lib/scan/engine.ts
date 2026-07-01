// Blueprint builder — wraps the shared scoring engine (IMPORT ONLY, never reimplement).
// Uses the LEVELS engine. The numeric SCORE is NOT computed (scoreDirection throws,
// pass 2). Score is surfaced as pending; the real 85/82 gate sits behind a flag.

import {
  calcADX,
  calcATR,
  calcEMA,
  calcRSI,
  closedCandles,
  computeReversalAnchor,
  computeSlTp,
  ema7Slope,
  type SlTpOpt,
} from "@finaroda/scoring-engine";

import type { Blueprint, Direction, MarketData, RiskStyle } from "./types";

// Real PASS/WATCH thresholds — wired but GATED OFF until the score exists (pass 2).
export const SCORE_GATE_ENABLED = false;
export const PASS_THRESHOLD = 85;
export const WATCH_THRESHOLD = 82;

// Risk Style → computeSlTp opt (PRD §3.5.4). Balanced === engine defaults.
// Client choice affects OUTPUT geometry only — NEVER the score (RED LINE §3.5.5).
export const RISK_STYLE_OPT: Record<RiskStyle, SlTpOpt> = {
  Conservative: { slAtrMult: 1.0, tp1Mult: 1.0, tp2Mult: 2.0 },
  Balanced: { slAtrMult: 1.5, tp1Mult: 1.5, tp2Mult: 3.0 },
  Aggressive: { slAtrMult: 2.0, tp1Mult: 2.0, tp2Mult: 4.0 },
};

// Interim direction rule (documented): until the scorer exists, derive a provisional
// direction from the VERIFIED signed EMA7 slope. Positive → long, negative → short.
// This is NOT a score and NOT a recommendation — it only orients the level geometry.
function interimDirection(slope: number): Direction | null {
  if (slope > 0) return "long";
  if (slope < 0) return "short";
  return null;
}

function volumeRatio(v: number[]): number {
  const closed = closedCandles(v);
  if (closed.length < 20) return 1;
  const last = closed[closed.length - 1];
  const avg = closed.slice(-20).reduce((a, b) => a + b, 0) / 20;
  return avg > 0 ? last / avg : 1;
}

export function buildBlueprint(
  coin: string,
  md: MarketData,
  riskStyle: RiskStyle,
): Blueprint | null {
  const closes = closedCandles(md.daily.c);
  const highs = closedCandles(md.daily.h);
  const lows = closedCandles(md.daily.l);

  const slope = ema7Slope(closes); // verified edge; null if < 12 candles
  const atr = calcATR(highs, lows, closes, 14);
  if (slope === null || atr <= 0 || closes.length < 30) return null; // levels invalid → skip

  const direction = interimDirection(slope);
  if (!direction) return null;

  const ema7 = calcEMA(closes, 7);
  const ema14 = calcEMA(closes, 14);
  const ema28 = calcEMA(closes, 28);
  const ema200 = calcEMA(closes, 200);
  const rsi = calcRSI(closes, 14);
  const adx = calcADX(highs, lows, closes, 14);
  const price = md.price;

  const opt = RISK_STYLE_OPT[riskStyle];
  const levels = computeSlTp(direction, price, ema14, ema28, atr, opt);

  // Dynamic Risk Level (trailing) — ATR-based trailing geometry (same buffer as SL side).
  const trailMult = opt.slAtrMult ?? 1.5;
  const dynamic = direction === "long" ? price - atr * trailMult : price + atr * trailMult;
  const dynamicPct = (Math.abs(price - dynamic) / price) * 100;

  // Reversal anchor context (display/research only) — verified structural basis.
  const swingHigh = Math.max(...highs.slice(-20));
  const swingLow = Math.min(...lows.slice(-20));
  computeReversalAnchor({ price, ema7, ema14, ema200, swingHigh, swingLow, atr });

  const riskReward = levels.slPct > 0 ? Math.round((levels.tp1Pct / levels.slPct) * 10) / 10 : null;

  return {
    coin,
    direction,
    score: null,
    scorePending: true,
    mathematicalTriggerPoint: {
      value: price,
      note: "Calculated from live price relative to EMA structure.",
    },
    calculatedRiskLevel: {
      value: levels.sl,
      pct: levels.slPct,
      note: "Calculated via ATR14 on your selected chart.",
    },
    calculatedTargetLevel: {
      value: levels.tp1,
      pct: levels.tp1Pct,
      note: "Calculated as an R-multiple of the risk distance.",
    },
    dynamicRiskLevel: {
      value: dynamic,
      pct: dynamicPct,
      note: "Calculated from ATR-based trailing geometry.",
    },
    riskReward,
    ema7SlopePct: slope,
    volumeRatio: volumeRatio(md.daily.v),
    rsi,
    adx,
    price,
    riskStyle,
    interimPassed: false, // set by the lens gate
  };
}
