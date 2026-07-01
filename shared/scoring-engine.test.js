import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  calcEMA, calcRSI, calcATR, calcADX, closedCandles,
  ema7Slope, computeSlTp, computeReversalAnchor, scoreDirection, TODO,
} from './scoring-engine.js';

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

test('scoreDirection is a guarded stub (pass 2)', () => {
  assert.throws(() => scoreDirection(), /not extracted yet/);
  assert.equal(TODO.__todo, true);
});
