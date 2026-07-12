// Swing support/resistance for charts — thin adapter over the shared engine's
// canonical pivot detection (findRecentSwingLevels, ported byte-faithfully from
// the personal tool). These are the exact S/R levels the scorer measures against
// (liquidity-proximity check + all logged trades), so the chart draws what the
// engine scores, never a separate drawing approximation. Replaces the old
// lib/onboarding/levels.ts pivot fn (deleted 2026-07-13).
import { findRecentSwingLevels } from "@finaroda/scoring-engine";

import type { Candle } from "@/lib/onboarding/types";

export interface RangeLevels {
  support: number | null;
  resistance: number | null;
}

export function swingLevels(candles: Candle[], lookback = 3, scanRange = 30): RangeLevels {
  const highs = candles.map((c) => c.h);
  const lows = candles.map((c) => c.l);
  const { swingHigh, swingLow } = findRecentSwingLevels(highs, lows, lookback, scanRange);
  return {
    resistance: swingHigh ? swingHigh.value : null,
    support: swingLow ? swingLow.value : null,
  };
}
