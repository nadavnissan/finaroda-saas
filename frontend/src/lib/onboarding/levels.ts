// Swing support/resistance from pivots (mirrors the scorer's swingHigh/swingLow
// idea: a pivot high/low is a candle that turns the local trend). Used by the
// chart to draw S/R. Pure, client-safe.
import type { Candle } from "./types";

export interface RangeLevels {
  support: number | null;
  resistance: number | null;
}

export function computeRangeLevels(candles: Candle[], lookback = candles.length): RangeLevels {
  const c = candles.slice(-lookback);
  if (c.length < 3) return { support: null, resistance: null };
  const pivotHighs: number[] = [];
  const pivotLows: number[] = [];
  for (let i = 1; i < c.length - 1; i++) {
    if (c[i].h >= c[i - 1].h && c[i].h >= c[i + 1].h) pivotHighs.push(c[i].h);
    if (c[i].l <= c[i - 1].l && c[i].l <= c[i + 1].l) pivotLows.push(c[i].l);
  }
  const resistance = pivotHighs.length ? Math.max(...pivotHighs) : Math.max(...c.map((x) => x.h));
  const support = pivotLows.length ? Math.min(...pivotLows) : Math.min(...c.map((x) => x.l));
  return { support, resistance };
}
