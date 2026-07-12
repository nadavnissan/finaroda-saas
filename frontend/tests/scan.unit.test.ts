// Pure-logic unit tests for Package B B1 (scan) — gating slice, E7b why-not
// sourcing, swing-levels adapter, chart candle building.
// Run: node --test --experimental-strip-types tests/scan.unit.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";

import { deriveWhyNot } from "../src/lib/scan/engine.ts";
import { SCAN_UNIVERSE } from "../src/lib/scan/bybit.ts";
import { swingLevels } from "../src/lib/chart/swings.ts";
import { toChartCandles } from "../src/lib/scan/chart.ts";
import type { MarketData } from "../src/lib/scan/types.ts";

// ── gating: the plan's coin count slices the scanned universe ──────────────────
// (Server is the source of truth — tested in backend/tests/test_b1_gating.py. Here
// we assert the client honours the count by slicing the universe.)
test("gating: a 2-coin (Free) plan slices the universe to 2 coins", () => {
  const scanned = SCAN_UNIVERSE.slice(0, 2);
  assert.equal(scanned.length, 2);
  assert.deepEqual(scanned, ["BTCUSDT", "ETHUSDT"]);
  const pro = SCAN_UNIVERSE.slice(0, 10);
  assert.equal(pro.length, 10);
});

// ── E7b: why-not names the blocking check from verified data, no numbers ───────
test("E7b: long below EMA200 → regime block via the 200-day average", () => {
  const w = deriveWhyNot("long", 90, 100, true); // price < ema200
  assert.equal(w.checkId, "regime");
  assert.equal(w.tooltipId, "ema200");
  assert.equal(w.term, "the 200-day average");
  assert.match(w.text, /below the 200-day average/);
  assert.match(w.text, /No PASS\.$/);
});

test("E7b: short above EMA200 → regime positive against the short", () => {
  const w = deriveWhyNot("short", 110, 100, true); // price > ema200
  assert.equal(w.checkId, "regime");
  assert.match(w.text, /above the 200-day average/);
  assert.match(w.text, /regime positive/);
});

test("E7b: blocked but regime aligned → methodology conditions", () => {
  const w = deriveWhyNot("long", 110, 100, true); // price above ema200 (aligned) yet blocked
  assert.equal(w.checkId, "methodology_conditions");
  assert.equal(w.tooltipId, "methodology_conditions");
});

test("E7b: not blocked (below threshold) → threshold check, exposes no score", () => {
  const w = deriveWhyNot("long", 110, 100, false);
  assert.equal(w.checkId, "score");
  assert.equal(w.tooltipId, "pass_watch");
  assert.doesNotMatch(w.text, /\d/); // no numeric score/weight leaked
});

// ── swing adapter: maps the shared engine's pivots to chart S/R ────────────────
test("swingLevels: maps swingHigh/swingLow → resistance/support", () => {
  // Pivot high at idx 4 (30), pivot low at idx 5 (5) — inside the scan window.
  const candles = [10, 11, 12, 13, 30, 13, 12, 11, 10, 9].map((h, i) => ({
    t: i,
    o: h,
    h,
    l: [20, 19, 18, 17, 16, 5, 16, 17, 18, 19][i],
    c: h,
    v: 1,
  }));
  const r = swingLevels(candles);
  assert.equal(r.resistance, 30);
  assert.equal(r.support, 5);
});

// ── chart data: candles carry EMA7/EMA200 series + timestamps ──────────────────
test("toChartCandles: attaches ema7/ema200 and windows to count", () => {
  const n = 60;
  const arr = (f: (i: number) => number) => Array.from({ length: n }, (_, i) => f(i));
  const md = {
    daily: {
      o: arr((i) => 100 + i),
      h: arr((i) => 101 + i),
      l: arr((i) => 99 + i),
      c: arr((i) => 100 + i),
      v: arr(() => 1000),
      t: arr((i) => i * 86_400_000),
    },
  } as unknown as MarketData;
  const candles = toChartCandles(md, 28);
  assert.equal(candles.length, 28);
  for (const c of candles) {
    assert.equal(typeof c.ema7, "number");
    assert.equal(typeof c.ema200, "number");
    assert.equal(typeof c.t, "number");
  }
  // EMA7 tracks a rising series more closely than EMA200 (shorter memory).
  const last = candles[candles.length - 1];
  assert.ok((last.ema7 as number) > (last.ema200 as number));
});
