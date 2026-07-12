// Ambient types for the linked shared engine (@finaroda/scoring-engine).
// The engine is plain JS; these signatures mirror shared/scoring-engine.js (v25.80).
// Types only — no logic. The engine is the single source of truth for the math.

declare module "@finaroda/scoring-engine" {
  export function calcEMA(data: number[], period: number): number;
  export function calcRSI(data: number[], period?: number): number;
  export function calcATR(highs: number[], lows: number[], closes: number[], period?: number): number;
  export function calcADX(
    highs: number[],
    lows: number[],
    closes: number[],
    period?: number,
  ): { adx: number; plusDI: number; minusDI: number } | null;
  export function closedCandles(series: number[]): number[];
  export function ema7Slope(closes: number[]): number | null;

  export interface SwingPivot {
    idx: number;
    value: number;
  }
  export function findRecentSwingLevels(
    highs: number[],
    lows: number[],
    lookback?: number,
    scanRange?: number,
  ): { swingHigh: SwingPivot | null; swingLow: SwingPivot | null };

  export interface SlTpOpt {
    slAtrMult?: number;
    tp1Mult?: number;
    tp2Mult?: number;
    slMaxPct?: number;
    slMinPct?: number;
  }
  export function computeSlTp(
    dir: "long" | "short",
    price: number,
    ema14: number,
    ema28: number,
    atr: number,
    opt?: SlTpOpt,
  ): { sl: number; tp1: number; tp2: number; slPct: number; tp1Pct: number; tp2Pct: number };

  export interface ReversalAnchorInput {
    price: number;
    ema7: number;
    ema14: number;
    ema200: number;
    swingHigh: number;
    swingLow: number;
    atr: number;
    oiChangePct?: number;
    weeklyBias?: string | null;
  }
  export interface ReversalAnchor {
    flipDir: "long" | "short";
    earlyTrigger: number;
    bosLevel: number;
    floor: number;
    macroTarget: number;
    gapToMacroPct: number;
    gapToEarlyPct: number | null;
    rr: number | null;
    slPct: number | null;
    background: { oiFalling: boolean; oiChangePct: number | null };
    core: {
      reclaimedEarly: boolean;
      slopeFlipped: boolean;
      confirmed: number;
      confirmMax: number;
      fired: boolean;
    };
    weeklyBias: string | null;
  }
  export function computeReversalAnchor(b: ReversalAnchorInput): ReversalAnchor | null;

  export const TODO: { __todo: true; message: string };
  export function scoreDirection(...args: unknown[]): never;
}

// The real scorer (verbatim v25.80). Subpath import — types only, no logic.
declare module "@finaroda/scoring-engine/scorer.js" {
  interface OHLCVLike {
    o: number[];
    h: number[];
    l: number[];
    c: number[];
    v: number[];
  }
  export interface ScorerMarketData {
    daily: OHLCVLike;
    hourly: OHLCVLike;
    weekly: OHLCVLike;
    price: number;
    funding: number;
    oi?: number | null;
    oiChangePct?: number | null;
  }
  export interface MarketContext {
    coinChanges: Record<string, number>;
    meanChange: number;
    stdChange: number;
  }
  export type Calibration = { entryMode: string; [k: string]: unknown };
  export interface ScoreResult {
    score: number;
    signal: "EXECUTE" | "WAIT" | "NO TRADE";
    blocked: boolean;
    price: number;
    sl: number;
    tp1: number;
    tp2: number;
    scoreComponents: unknown[];
    [k: string]: unknown;
  }
  export function scoreDirection(
    raw: ScorerMarketData,
    dir: "long" | "short",
    riskParams: unknown,
    cal: Calibration,
    marketContext: MarketContext,
    coin: string,
  ): ScoreResult;
  export const MOMENTUM_CAL: Calibration;
  export const DEFAULT_CALIBRATION: Calibration;
  export const DEFAULT_RISK: Record<string, unknown>;
  export const TREND_MGMT_RISK: Record<string, unknown>;
}
