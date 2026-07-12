import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  calcEMA, calcRSI, calcATR, calcADX, closedCandles,
  ema7Slope, computeSlTp, computeReversalAnchor, findRecentSwingLevels,
  scoreDirection, TODO,
} from './scoring-engine.js';

// Reference implementation — copied VERBATIM from the personal tool
// (C:\Users\rodan\FINARODA\engine.mjs, `findRecentSwingLevels`). The equivalence
// test below asserts the ported shared-engine version produces byte-identical
// swings for identical klines, so the SaaS chart draws exactly the S/R the
// personal-tool scorer measured all 680 logged trades against.
const referenceFindRecentSwingLevels = (highs, lows, lookback = 3, scanRange = 30) => {
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
};

// Deterministic PRNG (mulberry32) — no Math.random, so the vectors are fixed
// across runs and CI. Generates coherent-ish OHLC-style highs/lows.
function makeSeries(seed, len) {
  let s = seed >>> 0;
  const rnd = () => {
    s |= 0; s = (s + 0x6D2B79F5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const highs = [], lows = [];
  let base = 100;
  for (let i = 0; i < len; i++) {
    base += (rnd() - 0.5) * 6;
    const spread = rnd() * 2 + 0.5;
    highs.push(base + spread);
    lows.push(base - spread);
  }
  return { highs, lows };
}

test('calcEMA golden vectors', () => {
  assert.equal(calcEMA([1,2,3,4,5], 3), 4.0625);
  assert.equal(calcEMA([5,5,5,5,5,5,5,5,5,5], 5), 5);
  assert.equal(calcEMA([], 5), 0);
});

test('calcRSI bounds', () => {
  assert.equal(calcRSI([1,2,3,4,5,6,7], 6), 100);          // all up
  assert.equal(calcRSI([1,2], 6), 50);                     // insufficient
});

test('calcATR', () => {
  const H=[10,11,12,11,12,13,12], L=[9,10,10,10,11,11,11], C=[9.5,10.5,11,10.5,11.5,12,11.5];
  assert.equal(calcATR(H,L,C,3), 1.5);
});

test('closedCandles trims live candle when >30', () => {
  const big = Array.from({length: 40}, (_,i)=>i);
  assert.equal(closedCandles(big).length, 39);
  assert.equal(closedCandles([1,2,3]).length, 3);          // scarce → no trim
});

test('ema7Slope is signed', () => {
  const rising  = Array.from({length: 20}, (_,i)=>100+i);
  const falling = Array.from({length: 20}, (_,i)=>100-i);
  assert.ok(ema7Slope(rising)  > 0, 'rising → positive');
  assert.ok(ema7Slope(falling) < 0, 'falling → negative');
  assert.equal(ema7Slope([1,2,3]), null);                  // insufficient
});

test('computeSlTp: SL always on correct side', () => {
  const L = computeSlTp('long', 100, 99, 98, 2);
  assert.ok(L.sl < 100, 'long SL below price');
  assert.ok(L.tp1 > 100 && L.tp2 > L.tp1, 'long TPs above, ordered');
  const S = computeSlTp('short', 100, 101, 102, 2);
  assert.ok(S.sl > 100, 'short SL above price');
  assert.ok(S.tp1 < 100 && S.tp2 < S.tp1, 'short TPs below, ordered');
});

test('computeReversalAnchor: floor on correct side + fires on 2/2', () => {
  // bear macro (price < ema200) → long reversal; broken swing above price
  const a = computeReversalAnchor({ price:100, ema7:102, ema14:101, ema200:130, swingHigh:120, swingLow:118, atr:3 });
  assert.equal(a.flipDir, 'long');
  assert.ok(a.floor < 100, 'floor clamped below price for long');
  assert.equal(a.core.reclaimedEarly, false);              // price 100 < ema7 102
  assert.ok(typeof a.rr === 'number');
  // fired case: price reclaimed EMA7 and EMA7>EMA14
  const f = computeReversalAnchor({ price:103, ema7:102, ema14:101, ema200:130, swingHigh:120, swingLow:95, atr:3 });
  assert.equal(f.core.reclaimedEarly, true);
  assert.equal(f.core.slopeFlipped, true);
  assert.equal(f.core.fired, true);
});

test('findRecentSwingLevels: equivalent to personal-tool engine.mjs', () => {
  // Byte-identical swings for identical klines across many deterministic series,
  // varying lengths and the lookback/scanRange params.
  for (let seed = 1; seed <= 25; seed++) {
    for (const len of [8, 15, 30, 45, 60, 120]) {
      const { highs, lows } = makeSeries(seed * 97, len);
      for (const [lb, sr] of [[3, 30], [2, 20], [5, 50], [1, 10]]) {
        const got = findRecentSwingLevels(highs, lows, lb, sr);
        const ref = referenceFindRecentSwingLevels(highs, lows, lb, sr);
        assert.deepEqual(got, ref, `mismatch seed=${seed} len=${len} lb=${lb} sr=${sr}`);
      }
    }
  }
});

test('findRecentSwingLevels: pivot semantics + defaults', () => {
  // Clear pivot high at idx 4 (peak) and pivot low at idx 5 (valley), both inside
  // the [lookback, len-lookback) scan window so they survive the margins.
  const highs = [10, 11, 12, 13, 30, 13, 12, 11, 10, 9];
  const lows  = [20, 19, 18, 17, 16,  5, 16, 17, 18, 19];
  const r = findRecentSwingLevels(highs, lows); // lookback 3, scanRange 30
  assert.equal(r.swingHigh.idx, 4);
  assert.equal(r.swingHigh.value, 30);
  assert.equal(r.swingLow.idx, 5);
  assert.equal(r.swingLow.value, 5);
  // Too-short series → no pivot survives the lookback margins.
  const flat = findRecentSwingLevels([1, 2, 3], [1, 2, 3]);
  assert.deepEqual(flat, { swingHigh: null, swingLow: null });
});

test('scoreDirection is a guarded stub (pass 2)', () => {
  assert.throws(() => scoreDirection(), /not extracted yet/);
  assert.equal(TODO.__todo, true);
});
