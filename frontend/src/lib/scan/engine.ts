// Blueprint builder - wraps the shared engine (IMPORT ONLY, never reimplement).
// The REAL scorer is now wired (scorer.js, verbatim v25.80). The momentum profile is
// displayed; pullback/continuation are computed and logged (measure-first), not shown.
//
// RED LINE (PRD §3.5.5): the score comes from scoreDirection with FIXED inputs
// (DEFAULT_RISK + MOMENTUM_CAL). The client's Risk Style feeds ONLY computeSlTp's opt
// (the displayed levels) - it never touches the score, weights, edge, or threshold.

import {
  calcADX,
  calcATR,
  calcEMA,
  calcRSI,
  closedCandles,
  computeSlTp,
  ema7Slope,
  type SlTpOpt,
} from "@finaroda/scoring-engine";
import {
  DEFAULT_CALIBRATION,
  DEFAULT_RISK,
  MOMENTUM_CAL,
  scoreDirection,
  type Calibration,
  type MarketContext,
  type ScoreResult,
} from "@finaroda/scoring-engine/scorer.js";

import type { Blueprint, Direction, MarketData, PassLabel, Profile, RiskStyle, WhyNot } from "./types";

// Real SaaS gate is now ON (score exists). PASS/WATCH per PRD/UX §3.
export const SCORE_GATE_ENABLED = true;
export const PASS_THRESHOLD = 85;
export const WATCH_THRESHOLD = 82;

// Calibration profiles via the tool's own entryMode switch (no invented numbers):
// momentum (displayed) = MOMENTUM_CAL; pullback = DEFAULT_CALIBRATION (entryMode
// 'pullback'); continuation = same base with entryMode flipped.
const CONTINUATION_CAL: Calibration = { ...DEFAULT_CALIBRATION, entryMode: "continuation" };
const PROFILE_CAL: Record<Profile, Calibration> = {
  momentum: MOMENTUM_CAL,
  pullback: DEFAULT_CALIBRATION,
  continuation: CONTINUATION_CAL,
};

// Risk Style → computeSlTp opt (PRD §3.5.4). Balanced === engine defaults.
// OUTPUT geometry only - NEVER the score (RED LINE §3.5.5).
export const RISK_STYLE_OPT: Record<RiskStyle, SlTpOpt> = {
  Conservative: { slAtrMult: 1.0, tp1Mult: 1.0, tp2Mult: 2.0 },
  Balanced: { slAtrMult: 1.5, tp1Mult: 1.5, tp2Mult: 3.0 },
  Aggressive: { slAtrMult: 2.0, tp1Mult: 2.0, tp2Mult: 4.0 },
};

function scoreSafe(
  md: MarketData,
  dir: Direction,
  cal: Calibration,
  ctx: MarketContext,
  coin: string,
): ScoreResult | null {
  try {
    return scoreDirection(md, dir, DEFAULT_RISK, cal, ctx, coin);
  } catch {
    return null; // bad/insufficient data → skip rather than surface a bogus score
  }
}

function passLabelFor(score: number, blocked: boolean): PassLabel {
  if (blocked) return "HIDE";
  if (score >= PASS_THRESHOLD) return "PASS";
  if (score >= WATCH_THRESHOLD) return "WATCH";
  return "HIDE";
}

// E7b - name the blocking check for a non-passing coin in plain language, sourced
// from verified data only (regime = price vs EMA200; else the threshold). No score,
// weight or formula is exposed. Deterministic; each names a locked Concept Tooltip.
export function deriveWhyNot(
  direction: Direction,
  price: number,
  ema200: number,
  blocked: boolean,
): WhyNot {
  const regimeAgainst = direction === "long" ? price < ema200 : price > ema200;
  if (blocked && regimeAgainst) {
    const side = direction === "long" ? "below" : "above";
    const sign = direction === "long" ? "negative" : "positive";
    return {
      checkId: "regime",
      checkLabel: "regime",
      tooltipId: "ema200",
      term: "the 200-day average",
      text: `Price is ${side} the 200-day average - regime ${sign}. Setups against the regime usually fade. No PASS.`,
    };
  }
  if (blocked) {
    return {
      checkId: "methodology_conditions",
      checkLabel: "methodology conditions",
      tooltipId: "methodology_conditions",
      term: "methodology conditions",
      text: "A mandatory methodology condition did not hold on this coin, so it is not a valid setup right now. No PASS.",
    };
  }
  return {
    checkId: "score",
    checkLabel: "threshold",
    tooltipId: "pass_watch",
    term: "verified threshold",
    text: "This coin cleared the methodology but did not reach the verified threshold. No PASS.",
  };
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
  ctx: MarketContext,
): Blueprint | null {
  const closes = closedCandles(md.daily.c);
  const highs = closedCandles(md.daily.h);
  const lows = closedCandles(md.daily.l);
  const slope = ema7Slope(closes);
  const atr = calcATR(highs, lows, closes, 14);
  if (slope === null || atr <= 0 || closes.length < 30) return null;

  // Momentum profile decides the direction: score both, prefer non-blocked, then higher.
  const results = (["long", "short"] as Direction[])
    .map((dir) => ({ dir, r: scoreSafe(md, dir, MOMENTUM_CAL, ctx, coin) }))
    .filter((x): x is { dir: Direction; r: ScoreResult } => x.r !== null);
  if (results.length === 0) return null;
  results.sort((a, b) => {
    if (a.r.blocked !== b.r.blocked) return a.r.blocked ? 1 : -1; // non-blocked first
    return b.r.score - a.r.score; // then higher score
  });
  const { dir: direction, r: momentum } = results[0];

  // Other-profile scores for the SAME direction - logged for measure-first, not shown.
  const profileScores: Record<Profile, number | null> = {
    momentum: momentum.score,
    pullback: scoreSafe(md, direction, PROFILE_CAL.pullback, ctx, coin)?.score ?? null,
    continuation: scoreSafe(md, direction, PROFILE_CAL.continuation, ctx, coin)?.score ?? null,
  };

  const ema14 = calcEMA(closes, 14);
  const ema28 = calcEMA(closes, 28);
  const ema200 = calcEMA(closes, 200);
  const rsi = calcRSI(closes, 14);
  const adx = calcADX(highs, lows, closes, 14);
  const price = md.price;
  const passLabel = passLabelFor(momentum.score, momentum.blocked);

  // Displayed levels - Risk Style adjustable (NEVER affects the score).
  const opt = RISK_STYLE_OPT[riskStyle];
  const levels = computeSlTp(direction, price, ema14, ema28, atr, opt);
  const trailMult = opt.slAtrMult ?? 1.5;
  const dynamic = direction === "long" ? price - atr * trailMult : price + atr * trailMult;
  const dynamicPct = (Math.abs(price - dynamic) / price) * 100;
  const riskReward = levels.slPct > 0 ? Math.round((levels.tp1Pct / levels.slPct) * 10) / 10 : null;

  return {
    coin,
    direction,
    score: Math.round(momentum.score * 10) / 10,
    signal: momentum.signal,
    passLabel,
    profileScores,
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
    ema200,
    price,
    riskStyle,
    whyNot: passLabel === "HIDE" ? deriveWhyNot(direction, price, ema200, momentum.blocked) : null,
  };
}
