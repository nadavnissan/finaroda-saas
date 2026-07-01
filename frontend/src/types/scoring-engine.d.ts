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
