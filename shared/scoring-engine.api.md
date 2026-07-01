# `scoring-engine.js` — API contract (v0.2 — LEVELS EXTRACTED)

> Shared, pure calculation brain. Imported by BOTH the personal tool (browser)
> and the SaaS scan core (Next.js client-side). SPEC §6.1, §12 decision 7.
> Source of truth for extraction: personal tool `finaroda-offline.html` **v25.80**.

## Status

| Group | State |
|---|---|
| **Levels engine** — calcEMA, calcRSI, calcATR, calcADX, closedCandles, ema7Slope, computeSlTp, computeReversalAnchor | ✅ **Extracted, byte-faithful, unit-tested (8/8)** |
| **Scorer** — scoreDirection | 🟡 **Stub (throws).** Pass-2 extraction — needs golden vectors + `cal` defaults from the personal tool. |

## Invariants (enforced)
1. Deterministic — pure, no LLM/randomness/I·O/Date.
2. Verified indicators only to clients: signed EMA7 slope + volume ratio. No funding/OI.
3. Shared single source — never fork the math.
4. Analysis, not advice — score + levels; does not decide entry.

## Functions (extracted)

### `calcEMA(data: number[], period: number): number`
EMA seeded on `data[0]`. Golden: `calcEMA([1,2,3,4,5],3) === 4.0625`.

### `calcRSI(data: number[], period = 6): number`
0–100; 50 if insufficient, 100 if no losses.

### `calcATR(highs, lows, closes, period = 14): number`
Average true range over last `period` bars.

### `calcADX(highs, lows, closes, period = 14): {adx,plusDI,minusDI}|null`
Wilder ADX — intel only, never scores/blocks.

### `closedCandles(series: number[]): number[]`
Drops the live (last) candle when length > 30 (v25.38 closed-candle rule).

### `ema7Slope(closes: number[]): number|null`
**Signed** EMA7 slope %, 5-candle lookback (v25.77). +rising / −falling. The one
verified timing edge. null if < 12 candles.

### `computeSlTp(dir, price, ema14, ema28, atr, opt?): {sl,tp1,tp2,slPct,tp1Pct,tp2Pct}`
SL/TP geometry, ATR-based, clamped (slMinPct 0.5 … slMaxPct 2.0). SL always on the
correct side. `opt`: slAtrMult 1.5, tp1Mult 1.5, tp2Mult 3.0.

### `computeReversalAnchor(b): object|null`
Macro-reversal SPOT anchor (v25.80). Returns **structured flags + levels, no UI
strings** — each UI localizes. `b` = { price, ema7, ema14, ema200, swingHigh,
swingLow, atr, oiChangePct?, weeklyBias? }. Returns { flipDir, earlyTrigger,
bosLevel, floor, macroTarget, gapToMacroPct, gapToEarlyPct, rr, slPct,
background:{oiFalling,oiChangePct}, core:{reclaimedEarly,slopeFlipped,confirmed,
confirmMax,fired}, weeklyBias }. Display/research only until 30+ reversals × 2 regimes.

## Functions (pending — pass 2)

### `scoreDirection(marketData, direction, cal, marketContext, riskParams): number`
🟡 Throws until extracted. The verified 30+ filter scorer is ~500 lines coupled to
a calibration object (`cal`, ~25 params), cross-coin `marketContext`, and
`riskParams`. **Pass-2 requirements:** (1) Nadav exports golden input→score vectors
from the personal tool; (2) the `cal` defaults object is bundled; (3) port + verify
against vectors; (4) lock shapes here.

## marketData shape (from the personal tool `raw`)
```
{
  daily:  { o:[], h:[], l:[], c:[], v:[] },   // oldest → newest
  hourly: { o:[], h:[], l:[], c:[], v:[] },
  price:  number,                              // live price (Entry/SL/TP only)
  funding: number
}
```
The SaaS pulls this fresh from Bybit per scan (client-side, IP of the user) and
passes it into these pure functions.

## Notes for consumers
- Levels engine is safe to wire into the SaaS decision card NOW (Entry basis / SL /
  TP / Trailing / R:R / EMA7 slope / reversal anchor).
- The SCORE (gate for PASS ≥85 / WATCH 82–84) requires `scoreDirection` → blocked on
  pass 2. Until then the card can show levels but not a real score.
