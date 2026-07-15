// F16 Market Narrative resolver — deterministic state mapping + variant rotation.
// Run: node --test --experimental-strip-types tests/narrative.unit.test.ts
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  dayOfYear,
  resolveDailyLimit,
  resolveNarrative,
  type NarrativeCoin,
  type NarrativesFile,
} from "../src/lib/scan/narrative.ts";

const data = JSON.parse(
  readFileSync(new URL("../src/lib/scan/market_narratives.json", import.meta.url), "utf-8"),
) as NarrativesFile;

function coin(p: Partial<NarrativeCoin>): NarrativeCoin {
  return {
    coin: p.coin ?? "LINKUSDT",
    passLabel: p.passLabel ?? "HIDE",
    score: p.score ?? 50,
    ema7SlopePct: p.ema7SlopePct ?? -0.2,
    riskReward: p.riskReward ?? null,
    change24h: p.change24h ?? 0,
    whyNotCheckId: p.whyNotCheckId ?? null,
  };
}

const D = (dayNum: number) => new Date(Date.UTC(2026, 0, dayNum)); // day-of-year == dayNum
const NO_UNFILLED = /\{[a-z0-9_]+\}/;

// ── S4 pass_with_context: a PASS is the headline, and wins over any 0-PASS state ──
test("S4 fires when a coin passes, names coin + score + risk:reward", () => {
  const input = {
    coins: [
      coin({ coin: "AVAXUSDT", passLabel: "PASS", score: 88, riskReward: 2.1 }),
      coin({ coin: "LINKUSDT", passLabel: "HIDE", whyNotCheckId: "regime", change24h: 9 }),
    ],
    date: D(10),
  };
  const r = resolveNarrative(input, data);
  assert.equal(r.stateId, "pass_with_context");
  assert.equal(r.code, "S4");
  assert.match(r.text, /AVAX/);
  assert.match(r.text, /88/);
  assert.doesNotMatch(r.text, NO_UNFILLED);
});

// ── S1 regime_blocked_spike: 0 PASS, all regime-failed, a coin up > +3% ──────────
test("S1 fires on a spike inside a fully failed regime", () => {
  const input = {
    coins: [
      coin({ coin: "LINKUSDT", passLabel: "HIDE", whyNotCheckId: "regime", change24h: 4.2 }),
      coin({ coin: "AVAXUSDT", passLabel: "HIDE", whyNotCheckId: "regime", change24h: 1.0 }),
      coin({ coin: "SOLUSDT", passLabel: "HIDE", whyNotCheckId: "regime", change24h: -2.0 }),
    ],
    date: D(10),
  };
  const r = resolveNarrative(input, data);
  assert.equal(r.stateId, "regime_blocked_spike");
  assert.equal(r.code, "S1");
  assert.match(r.text, /LINK/); // the spike coin (max change24h)
  assert.match(r.text, /\+4\.2%/);
  assert.doesNotMatch(r.text, NO_UNFILLED);
});

// ── S3 transition_flicker (DEGRADED): 0 PASS, >=3 short-average up, regime fails ──
test("S3 fires on >=3 flickering coins with no spike", () => {
  const input = {
    coins: [
      coin({ coin: "LINKUSDT", passLabel: "HIDE", whyNotCheckId: "regime", ema7SlopePct: 0.4, change24h: 1 }),
      coin({ coin: "AVAXUSDT", passLabel: "HIDE", whyNotCheckId: "regime", ema7SlopePct: 0.6, change24h: 1 }),
      coin({ coin: "SOLUSDT", passLabel: "HIDE", whyNotCheckId: "regime", ema7SlopePct: 0.2, change24h: 1 }),
    ],
    date: D(10),
  };
  const r = resolveNarrative(input, data);
  assert.equal(r.stateId, "transition_flicker");
  assert.equal(r.code, "S3");
  assert.match(r.text, /3 of 3/);
  assert.doesNotMatch(r.text, NO_UNFILLED);
});

// ── S5 watch_only: 0 PASS, a coin in the 82 to 84 band, no spike, < 3 flicker ────
test("S5 fires when a coin is in the watch band", () => {
  const input = {
    coins: [
      coin({ coin: "AVAXUSDT", passLabel: "WATCH", score: 83, ema7SlopePct: -0.1 }),
      coin({ coin: "LINKUSDT", passLabel: "HIDE", whyNotCheckId: "score", ema7SlopePct: -0.5 }),
    ],
    date: D(10),
  };
  const r = resolveNarrative(input, data);
  assert.equal(r.stateId, "watch_only");
  assert.equal(r.code, "S5");
  assert.match(r.text, /AVAX/);
  assert.match(r.text, /83/);
  assert.doesNotMatch(r.text, NO_UNFILLED);
});

// ── S2 no_setups_quiet: the fallback when nothing else matches ────────────────────
test("S2 is the fallback for a quiet, blank scan", () => {
  const input = {
    coins: [
      coin({ coin: "LINKUSDT", passLabel: "HIDE", whyNotCheckId: "score", ema7SlopePct: -0.4 }),
      coin({ coin: "AVAXUSDT", passLabel: "HIDE", whyNotCheckId: "score", ema7SlopePct: -0.3 }),
    ],
    date: D(10),
  };
  const r = resolveNarrative(input, data);
  assert.equal(r.stateId, "no_setups_quiet");
  assert.equal(r.code, "S2");
  assert.doesNotMatch(r.text, NO_UNFILLED);
});

// ── S2 optional {unrevealed}: the variant using it is eligible only when provided ──
test("S2 can use the unrevealed-journal count when provided, and never leaves it unfilled", () => {
  for (let d = 1; d <= 3; d++) {
    const r = resolveNarrative(
      { coins: [coin({ passLabel: "HIDE", whyNotCheckId: "score" })], unrevealed: 2, date: D(d) },
      data,
    );
    assert.equal(r.code, "S2");
    assert.doesNotMatch(r.text, NO_UNFILLED);
  }
});

// ── S6 daily_limit_reached: resolved separately (rendered in the 429 screen) ──────
test("S6 resolves the daily-limit narrative", () => {
  const r = resolveDailyLimit(1, data, D(10));
  assert.equal(r.stateId, "daily_limit_reached");
  assert.equal(r.code, "S6");
  assert.match(r.text, /1/);
  assert.doesNotMatch(r.text, NO_UNFILLED);
});

// ── Determinism + date rotation ───────────────────────────────────────────────
test("resolution is deterministic for a given payload and date", () => {
  const input = () => ({
    coins: [coin({ coin: "LINKUSDT", passLabel: "HIDE", whyNotCheckId: "regime", change24h: 4.2 })],
    date: D(7),
  });
  assert.deepEqual(resolveNarrative(input(), data), resolveNarrative(input(), data));
});

test("variants rotate by date across a 3-variant state", () => {
  const mk = (d: number) =>
    resolveNarrative(
      { coins: [coin({ coin: "LINKUSDT", passLabel: "HIDE", whyNotCheckId: "regime", change24h: 4.2 })], date: D(d) },
      data,
    );
  // S1 has 3 eligible variants; consecutive days pick distinct indices.
  const idx = [mk(1).variantIndex, mk(2).variantIndex, mk(3).variantIndex];
  assert.equal(new Set(idx).size, 3, `expected 3 distinct variants, got ${idx}`);
  // And the rendered text differs day to day.
  assert.notEqual(mk(1).text, mk(2).text);
});

// ── Every state, every day: no unfilled placeholder, disclaimer always present ────
test("no resolved narrative ever leaves an unfilled placeholder", () => {
  const scenarios = [
    { coins: [coin({ passLabel: "PASS", score: 90, riskReward: 3.0 })] },
    { coins: [coin({ passLabel: "PASS", score: 86, riskReward: null })] }, // rr absent -> skip {rr} variant
    { coins: [coin({ passLabel: "HIDE", whyNotCheckId: "regime", change24h: 5 })] },
    { coins: [coin({ passLabel: "WATCH", score: 84 })] },
    { coins: [coin({ passLabel: "HIDE", whyNotCheckId: "score" })] },
  ];
  for (const s of scenarios) {
    for (let d = 1; d <= 40; d++) {
      const r = resolveNarrative({ ...s, date: D(d) }, data);
      assert.doesNotMatch(r.text, NO_UNFILLED, `unfilled in ${r.code} day ${d}: ${r.text}`);
      assert.equal(r.disclaimer, data.disclaimer);
    }
  }
});

test("dayOfYear is stable and UTC-based", () => {
  assert.equal(dayOfYear(new Date(Date.UTC(2026, 0, 1))), 1);
  assert.equal(dayOfYear(new Date(Date.UTC(2026, 0, 31))), 31);
});
