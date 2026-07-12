// ============================================================================
// scoring-engine.js — FINARODA shared calculation engine (pure math, zero UI)
// ============================================================================
// Extracted faithfully from the personal tool (finaroda-offline.html v25.80).
// Imported by BOTH the personal tool (browser) and the SaaS scan core (Next.js
// client-side). A fix here propagates to both. SPEC §6.1, §12 decision 7.
//
// INVARIANTS (must always hold):
//   1. Deterministic — pure functions of inputs. No LLM, no randomness, no I/O,
//      no Date/time. Same input → same output, always.
//   2. Verified indicators only are exposed to clients: signed EMA7 slope +
//      volume ratio. No funding/OI in client-facing scoring (SPEC §1.4).
//   3. Shared single source — never fork the math.
//   4. Analysis, not advice — outputs a score + levels; does not decide entry.
//
// STATUS OF THIS FILE:
//   ✅ LEVELS ENGINE — fully extracted & verified (byte-faithful to v25.80):
//        calcEMA, calcRSI, calcATR, calcADX, ema7Slope, closedCandles,
//        computeSlTp, computeReversalAnchor.
//   🟡 SCORER (scoreDirection) — NOT ported here. It is ~500 lines coupled to a
//        calibration object (`cal`, ~25 params), cross-coin marketContext, and
//        riskParams. Porting it without golden-reference vectors risks silent
//        numeric drift. It is deliberately left as a throwing stub until Nadav
//        supplies golden vectors from the personal tool (extraction pass 2).
//        Everything the decision card needs for LEVELS (Entry basis / SL / TP /
//        Trailing / R:R / EMA7 slope / reversal anchor) is available now.
// ============================================================================

/** Frozen sentinel returned by not-yet-extracted stubs. */
const TODO = Object.freeze({ __todo: true, message: 'awaiting golden-vector extraction (pass 2)' });

// ---------------------------------------------------------------------------
// Pure indicator helpers (verified — byte-faithful to v25.80)
// ---------------------------------------------------------------------------

/**
 * Exponential moving average.
 * @param {number[]} data  ordered closes (oldest → newest)
 * @param {number}   period
 * @returns {number} EMA over the full series (seeded on data[0])
 */
export function calcEMA(data, period) {
  if (!data || data.length === 0) return 0;
  const mult = 2 / (period + 1);
  let ema = data[0];
  for (let i = 1; i < data.length; i++) ema = (data[i] - ema) * mult + ema;
  return ema;
}

/**
 * Wilder-lite RSI over the last `period` diffs.
 * @param {number[]} data ordered closes
 * @param {number}   period default 6
 * @returns {number} 0–100 (50 if insufficient data, 100 if no losses)
 */
export function calcRSI(data, period = 6) {
  if (!data || data.length < period + 1) return 50;
  let g = 0, l = 0;
  for (let i = data.length - period; i < data.length; i++) {
    const d = data[i] - data[i - 1];
    if (d > 0) g += d; else l -= d;
  }
  const avgLoss = l / period;
  if (avgLoss === 0) return 100;
  return 100 - 100 / (1 + g / period / avgLoss);
}

/**
 * Average True Range over the last `period` bars.
 * @returns {number} ATR (0 if insufficient data)
 */
export function calcATR(highs, lows, closes, period = 14) {
  if (!highs || highs.length < period + 1) return 0;
  const trs = [];
  for (let i = 1; i < highs.length; i++) {
    trs.push(Math.max(
      highs[i] - lows[i],
      Math.abs(highs[i] - closes[i - 1]),
      Math.abs(lows[i] - closes[i - 1])
    ));
  }
  return trs.slice(-period).reduce((a, b) => a + b, 0) / period;
}

/**
 * ADX (Wilder) — trend-strength (not direction). Intel only; never enters the
 * score, never blocks. Returns null if insufficient data.
 * @returns {{adx:number, plusDI:number, minusDI:number}|null}
 */
export function calcADX(highs, lows, closes, period = 14) {
  const n = highs ? highs.length : 0;
  if (!highs || n < period * 2 + 1) return null;
  const trArr = [], plusDM = [], minusDM = [];
  for (let i = 1; i < n; i++) {
    const up = highs[i] - highs[i - 1];
    const down = lows[i - 1] - lows[i];
    plusDM.push(up > down && up > 0 ? up : 0);
    minusDM.push(down > up && down > 0 ? down : 0);
    trArr.push(Math.max(
      highs[i] - lows[i],
      Math.abs(highs[i] - closes[i - 1]),
      Math.abs(lows[i] - closes[i - 1])
    ));
  }
  let tr = trArr.slice(0, period).reduce((a, b) => a + b, 0);
  let pdm = plusDM.slice(0, period).reduce((a, b) => a + b, 0);
  let mdm = minusDM.slice(0, period).reduce((a, b) => a + b, 0);
  const dxArr = [];
  for (let i = period; i < trArr.length; i++) {
    tr = tr - tr / period + trArr[i];
    pdm = pdm - pdm / period + plusDM[i];
    mdm = mdm - mdm / period + minusDM[i];
    if (tr === 0) continue;
    const pDI = 100 * pdm / tr, mDI = 100 * mdm / tr;
    const denom = pDI + mDI;
    dxArr.push(denom === 0 ? 0 : 100 * Math.abs(pDI - mDI) / denom);
  }
  if (dxArr.length < period) return null;
  let adx = dxArr.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (let i = period; i < dxArr.length; i++) adx = (adx * (period - 1) + dxArr[i]) / period;
  const lastPDI = tr === 0 ? 0 : 100 * pdm / tr;
  const lastMDI = tr === 0 ? 0 : 100 * mdm / tr;
  return {
    adx: Math.round(adx * 10) / 10,
    plusDI: Math.round(lastPDI),
    minusDI: Math.round(lastMDI),
  };
}

/**
 * CLOSED-CANDLE guard (personal tool v25.38). The last daily candle from Bybit
 * is the LIVE candle (not closed until 00:00 UTC). Scoring on it makes the score
 * flicker scan-to-scan — the anti-thesis of swing. All checks run on closed
 * candles only; the live price is used solely for Entry/SL/TP sizing.
 * @param {number[]} series any OHLCV array (oldest → newest)
 * @returns {number[]} series without the live (last) candle, unless data is thin
 */
export function closedCandles(series) {
  if (!series) return series;
  const trim = series.length > 30 ? 1 : 0; // don't trim when data is scarce
  return series.slice(0, series.length - trim);
}

/**
 * Signed EMA7 slope in percent (personal tool v25.77). The single verified
 * timing edge (78.7% beat random, monotonic, 10/10 coins). Positive = rising,
 * negative = falling. Magnitude consumers apply Math.abs() themselves.
 * Uses a 5-candle lookback on CLOSED candles.
 * @param {number[]} closes ordered closes (oldest → newest)
 * @returns {number|null} signed slope % (null if < 12 candles)
 */
export function ema7Slope(closes) {
  if (!closes || closes.length < 12) return null;
  const e7now = calcEMA(closes, 7);
  const e7prev = calcEMA(closes.slice(0, closes.length - 5), 7);
  if (!e7prev) return null;
  return (e7now - e7prev) / e7prev * 100;
}

// ---------------------------------------------------------------------------
// LEVELS geometry (verified — byte-faithful to v25.80)
// ---------------------------------------------------------------------------

/**
 * Stop-loss / take-profit geometry from EMA structure + ATR (v25.80 clamped).
 * SL is always on the correct side of price. TP1/TP2 are R-multiples of risk.
 * @param {"long"|"short"} dir
 * @param {number} price   live price (entry reference)
 * @param {number} ema14
 * @param {number} ema28
 * @param {number} atr
 * @param {object} [opt] { slAtrMult=1.5, tp1Mult=1.5, tp2Mult=3.0, slMaxPct=2.0, slMinPct=0.5 }
 * @returns {{sl:number,tp1:number,tp2:number,slPct:number,tp1Pct:number,tp2Pct:number}}
 */
export function computeSlTp(dir, price, ema14, ema28, atr, opt) {
  opt = opt || {};
  const slAtrMult = opt.slAtrMult ?? 1.5;
  const tp1Mult = opt.tp1Mult ?? 1.5;
  const tp2Mult = opt.tp2Mult ?? 3.0;
  const slMaxPct = opt.slMaxPct ?? 2.0;
  const slMinPct = opt.slMinPct ?? 0.5;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  let sl, slPct;
  if (dir === 'long') {
    const slRaw = Math.min(ema14, ema28) - atr * slAtrMult; // structural, below price
    slPct = clamp((price - slRaw) / price * 100, slMinPct, slMaxPct);
    sl = price * (1 - slPct / 100);                         // always below price
  } else {
    const slRaw = Math.max(ema14, ema28) + atr * slAtrMult; // structural, above price
    slPct = clamp((slRaw - price) / price * 100, slMinPct, slMaxPct);
    sl = price * (1 + slPct / 100);                         // always above price
  }
  const risk = Math.abs(price - sl);
  const tp1 = dir === 'long' ? price + risk * tp1Mult : price - risk * tp1Mult;
  const tp2 = dir === 'long' ? price + risk * tp2Mult : price - risk * tp2Mult;
  return {
    sl, tp1, tp2, slPct,
    tp1Pct: Math.abs(tp1 - price) / price * 100,
    tp2Pct: Math.abs(tp2 - price) / price * 100,
  };
}

/**
 * Reversal anchor — the geometric basis for macro-reversal SPOT entries
 * (personal tool v25.78→v25.80). Distilled to the verified core: the anchor
 * "fires" on EMA7-slope reversal (reclaim EMA7 + EMA7×EMA14 cross). Ripeness
 * components (moveDone/RSI/proximity/ADL) were 0/30 in backtest and dropped;
 * OI-falling stays as weak background only. Floor (SL) is clamped to the correct
 * side with an ATR×1.5 buffer (v25.80 fix).
 *
 * Returns STRUCTURED FLAGS + LEVELS only — no UI strings. Each UI (Hebrew tool /
 * English SaaS) localizes the labels itself. Display/research only, never a
 * trigger, until 30+ real reversals across 2+ regimes.
 *
 * @param {object} b { price, ema7, ema14, ema200, swingHigh, swingLow, atr, oiChangePct?, weeklyBias? }
 * @returns {object|null}
 */
export function computeReversalAnchor(b) {
  if (!b || b.ema7 == null || b.ema200 == null || b.price == null) return null;
  const price = b.price;
  const belowMacro = price < b.ema200;
  const flipDir = belowMacro ? 'long' : 'short';
  const macroTarget = b.ema200;
  const earlyTrigger = b.ema7;
  const bosLevel = belowMacro ? b.swingHigh : b.swingLow;
  // v25.80: floor (SL / invalidation) must be on the correct side. A broken swing
  // can land above entry for a long (inverted SL) — clamp with an ATR×1.5 buffer.
  const atrBuf = (b.atr != null && b.atr > 0 ? b.atr : price * 0.02) * 1.5;
  const rawFloor = belowMacro ? b.swingLow : b.swingHigh;
  const floor = belowMacro
    ? Math.min(rawFloor != null ? rawFloor : Infinity, price - atrBuf)
    : Math.max(rawFloor != null ? rawFloor : -Infinity, price + atrBuf);
  const gapToMacroPct = Math.abs(price - b.ema200) / b.ema200 * 100;
  const gapToEarlyPct = b.ema7 ? Math.abs(price - b.ema7) / b.ema7 * 100 : null;
  // R:R (reward:risk) + SL% — EMA7 as the entry reference.
  const rewardDist = Math.abs(macroTarget - earlyTrigger);
  const riskDist = Math.abs(earlyTrigger - floor);
  const rr = riskDist > 0 ? Math.round(rewardDist / riskDist * 10) / 10 : null;
  const slPct = earlyTrigger ? Math.round(riskDist / earlyTrigger * 1000) / 10 : null;
  // Background (OI falling) — collected, weak, not decisive.
  const oiFalling = b.oiChangePct != null && b.oiChangePct < 0;
  // Verified core (EMA7 slope reversal). Anchor "fires" on 2/2.
  const reclaimedEarly = flipDir === 'long' ? price > b.ema7 : price < b.ema7;
  const slopeFlipped = flipDir === 'long'
    ? (b.ema14 != null && b.ema7 > b.ema14)
    : (b.ema14 != null && b.ema7 < b.ema14);
  const confirmed = (reclaimedEarly ? 1 : 0) + (slopeFlipped ? 1 : 0);
  const fired = confirmed === 2; // display only, not a trade signal
  return {
    flipDir, earlyTrigger, bosLevel, floor, macroTarget,
    gapToMacroPct, gapToEarlyPct, rr, slPct,
    background: { oiFalling, oiChangePct: b.oiChangePct ?? null },
    core: { reclaimedEarly, slopeFlipped, confirmed, confirmMax: 2, fired },
    weeklyBias: b.weeklyBias ?? null,
  };
}

/**
 * Recent swing high / low — the verified support/resistance the personal-tool
 * scorer measures against (liquidity-proximity check + all 680 logged trades).
 * Ported byte-faithfully from the personal tool (engine.mjs `findRecentSwingLevels`).
 * A pivot is a candle whose high (low) strictly exceeds (undercuts) the `lookback`
 * candles on both sides; the scan walks newest→oldest inside the last `scanRange`
 * closed candles and returns the first pivot of each kind found.
 *
 * This is the ONE canonical S/R source — the SaaS chart draws exactly the levels
 * the engine scores against. Do not fork with a different pivot definition.
 *
 * @param {number[]} highs     ordered highs (oldest → newest)
 * @param {number[]} lows      ordered lows (oldest → newest)
 * @param {number}   lookback  bars on each side that a pivot must beat (default 3)
 * @param {number}   scanRange how many recent bars to search (default 30)
 * @returns {{ swingHigh: {idx:number,value:number}|null, swingLow: {idx:number,value:number}|null }}
 */
export function findRecentSwingLevels(highs, lows, lookback = 3, scanRange = 30) {
  let swingHigh = null, swingLow = null;
  const start = Math.max(lookback, highs.length - scanRange);
  const end = highs.length - lookback;
  for (let i = end - 1; i >= start; i--) {
    let isHigh = true, isLow = true;
    for (let j = 1; j <= lookback && (isHigh || isLow); j++) {
      if (highs[i] <= highs[i - j] || highs[i] <= highs[i + j]) isHigh = false;
      if (lows[i]  >= lows[i  - j] || lows[i]  >= lows[i  + j]) isLow  = false;
    }
    if (isHigh && swingHigh === null) swingHigh = { idx: i, value: highs[i] };
    if (isLow  && swingLow  === null) swingLow  = { idx: i, value: lows[i] };
    if (swingHigh && swingLow) break;
  }
  return { swingHigh, swingLow };
}

// ---------------------------------------------------------------------------
// SCORER — NOT YET EXTRACTED (pass 2). See file header.
// ---------------------------------------------------------------------------

/**
 * Deterministic 0–100 score for one direction of one coin (30+ filters).
 * 🟡 STUB — the real scorer (~500 lines) is coupled to a calibration object,
 * cross-coin market context, and risk params. It will be ported in extraction
 * pass 2 with golden-reference vectors from the personal tool. Do NOT invent it.
 * @throws until extracted
 */
export function scoreDirection(/* marketData, direction, cal, marketContext, riskParams */) {
  throw new Error(
    'scoreDirection: not extracted yet (pass 2). The verified scorer lives in the ' +
    'personal tool and must be ported with golden vectors before use. ' +
    'Levels (computeSlTp / computeReversalAnchor / ema7Slope) are available now.'
  );
}

export { TODO };
