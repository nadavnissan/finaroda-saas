// F16b Outcome Narratives — deterministic resolved-scenario mapping (R1..R5).
// Run: node --test --experimental-strip-types tests/outcome_narrative.unit.test.ts
//
// Contract under test (mentor-amended 16/07):
//   - R1 win / R2 loss / R3 expired ship LIVE.
//   - R4 save / R5 skip are gated behind FEATURE_ARENA (default OFF) -> null when off.
//   - The resolver reads ONLY existing resolution-record fields (status, r_result,
//     coin, direction, score). No new computation.
//   - Foreseeability line renders "not_marked" unless a logged flag is passed (none today).
//   - Every rendered narrative fills all placeholders and carries the disclaimer.
//   - No new XP source is introduced by the narratives file or the resolver output.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  resolveOutcomeNarrative,
  type NarrativesFile,
  type OutcomeInput,
} from "../src/lib/scan/narrative.ts";

const data = JSON.parse(
  readFileSync(new URL("../src/lib/scan/market_narratives.json", import.meta.url), "utf-8"),
) as NarrativesFile;

const D = (dayNum: number) => new Date(Date.UTC(2026, 0, dayNum)); // day-of-year == dayNum
const NO_UNFILLED = /\{[a-z0-9_]+\}/;

function outcome(p: Partial<OutcomeInput>): OutcomeInput {
  return {
    status: p.status ?? "win",
    coin: p.coin ?? "LINKUSDT",
    direction: p.direction ?? "long",
    score: p.score ?? 88,
    rMultiple: p.rMultiple ?? 2.6,
    foreseeFlag: p.foreseeFlag ?? null,
    date: p.date,
  };
}

// ── R1 target_hit (win) — LIVE ────────────────────────────────────────────────
test("R1 fires on a win, restates the R math and names coin", () => {
  const r = resolveOutcomeNarrative(outcome({ status: "win", coin: "AVAXUSDT", rMultiple: 2.6, date: D(10) }), data);
  assert.ok(r);
  assert.equal(r!.stateId, "target_hit");
  assert.equal(r!.code, "R1");
  assert.match(r!.text, /AVAX/);
  assert.match(r!.text, /2\.6R/);
  assert.doesNotMatch(r!.text, NO_UNFILLED);
  assert.equal(r!.disclaimer, data.disclaimer);
});

// ── R2 stop_hit (loss) — LIVE, foreseeability appended ─────────────────────────
test("R2 fires on a loss, frames variance-not-error, appends the honest foreseeability line", () => {
  const r = resolveOutcomeNarrative(outcome({ status: "loss", rMultiple: -1.0, date: D(10) }), data);
  assert.ok(r);
  assert.equal(r!.stateId, "stop_hit");
  assert.equal(r!.code, "R2");
  assert.match(r!.text, /-1\.0R/);
  // No flag exists today -> the honest "nothing marked this in advance" line renders.
  assert.match(r!.text, /Nothing in the data marked this in advance\./);
  assert.doesNotMatch(r!.text, NO_UNFILLED);
});

// ── R3 expired_flat — LIVE, signed R, foreseeability appended ──────────────────
test("R3 fires on expiry, shows a signed R and the 7 day window", () => {
  const r = resolveOutcomeNarrative(outcome({ status: "expired", rMultiple: 0.2, date: D(10) }), data);
  assert.ok(r);
  assert.equal(r!.stateId, "expired_flat");
  assert.equal(r!.code, "R3");
  assert.match(r!.text, /\+0\.2R/); // signed for the flat/expired state
  assert.match(r!.text, /7 day/);
  assert.match(r!.text, /Nothing in the data marked this in advance\./);
  assert.doesNotMatch(r!.text, NO_UNFILLED);
});

test("R3 shows a negative sign when the expiry closed below flat", () => {
  const r = resolveOutcomeNarrative(outcome({ status: "expired", rMultiple: -0.3, date: D(10) }), data);
  assert.match(r!.text, /-0\.3R/);
});

// ── R4 save_confirmed — GATED behind FEATURE_ARENA ─────────────────────────────
test("R4 (save) is null when FEATURE_ARENA is off (the default)", () => {
  const r = resolveOutcomeNarrative(outcome({ status: "save", rMultiple: 0, date: D(10) }), data);
  assert.equal(r, null);
});

test("R4 (save) renders the capital-save story when FEATURE_ARENA is on, and never leaves {avoided_pct} unfilled", () => {
  for (let d = 1; d <= 30; d++) {
    const r = resolveOutcomeNarrative(
      outcome({ status: "save", rMultiple: 0, date: D(d) }),
      data,
      { featureArena: true },
    );
    assert.ok(r);
    assert.equal(r!.code, "R4");
    assert.doesNotMatch(r!.text, NO_UNFILLED, `unfilled in R4 day ${d}: ${r!.text}`);
  }
});

// ── R5 save_missed — GATED behind FEATURE_ARENA ────────────────────────────────
test("R5 (skip) is null when FEATURE_ARENA is off (the default)", () => {
  const r = resolveOutcomeNarrative(outcome({ status: "skip", date: D(10) }), data);
  assert.equal(r, null);
});

test("R5 (skip) renders discipline framing when FEATURE_ARENA is on, never regret language", () => {
  for (let d = 1; d <= 30; d++) {
    const r = resolveOutcomeNarrative(outcome({ status: "skip", date: D(d) }), data, { featureArena: true });
    assert.ok(r);
    assert.equal(r!.code, "R5");
    assert.doesNotMatch(r!.text, NO_UNFILLED);
    // Never framed as regret / "you should have".
    assert.doesNotMatch(r!.text, /should have|regret|missed out/i);
  }
});

// ── Fallback: open / unknown status -> null ────────────────────────────────────
test("open or unknown status yields no F16b card", () => {
  assert.equal(resolveOutcomeNarrative(outcome({ status: "open" }), data), null);
  assert.equal(resolveOutcomeNarrative(outcome({ status: "banana" }), data), null);
});

// ── Foreseeability: affirmative line ONLY from a logged flag ────────────────────
test("foreseeability affirmative line renders only when a flag is supplied (never today)", () => {
  // Default (no flag) -> honest negative.
  const noFlag = resolveOutcomeNarrative(outcome({ status: "loss", date: D(5) }), data);
  assert.match(noFlag!.text, /Nothing in the data marked this in advance\./);
  assert.doesNotMatch(noFlag!.text, /already on the record/);
  // With a (hypothetical, F17) flag -> affirmative line, flag value filled, no unfilled token.
  const withFlag = resolveOutcomeNarrative(outcome({ status: "loss", date: D(5), foreseeFlag: "regime" }), data);
  assert.match(withFlag!.text, /already on the record/);
  assert.match(withFlag!.text, /regime/);
  assert.doesNotMatch(withFlag!.text, NO_UNFILLED);
});

// ── Determinism + date rotation ────────────────────────────────────────────────
test("resolution is deterministic for a given payload and date", () => {
  const mk = () => resolveOutcomeNarrative(outcome({ status: "win", date: D(7) }), data);
  assert.deepEqual(mk(), mk());
});

test("R1 variants rotate by date across its 3 variants", () => {
  const idx = [1, 2, 3].map((d) => resolveOutcomeNarrative(outcome({ status: "win", date: D(d) }), data)!.variantIndex);
  assert.equal(new Set(idx).size, 3, `expected 3 distinct variants, got ${idx}`);
});

// ── Every live state, every day: no unfilled placeholder, disclaimer present ────
test("no live outcome narrative ever leaves an unfilled placeholder", () => {
  const live: OutcomeInput[] = [
    outcome({ status: "win", rMultiple: 3.1 }),
    outcome({ status: "loss", rMultiple: -1.0 }),
    outcome({ status: "expired", rMultiple: 0.0 }),
  ];
  for (const s of live) {
    for (let d = 1; d <= 40; d++) {
      const r = resolveOutcomeNarrative({ ...s, date: D(d) }, data);
      assert.ok(r);
      assert.doesNotMatch(r!.text, NO_UNFILLED, `unfilled in ${r!.code} day ${d}: ${r!.text}`);
      assert.equal(r!.disclaimer, data.disclaimer);
    }
  }
});

// ── Zero new XP sources: the narratives file and resolver output carry no XP ────
test("F16b introduces no XP source (no 'xp' key in resolved copy, no xp field on the result)", () => {
  const blob = readFileSync(new URL("../src/lib/scan/market_narratives.json", import.meta.url), "utf-8");
  // The resolved_states / foreseeability copy must not mention XP at all.
  const resolvedBlob = JSON.stringify(data.resolved_states) + JSON.stringify(data.foreseeability);
  assert.doesNotMatch(resolvedBlob, /\bxp\b/i, "F16b copy must not reference XP");
  assert.ok(blob.length > 0);
  // The result shape has no XP-bearing field.
  const r = resolveOutcomeNarrative(outcome({ status: "win" }), data)!;
  assert.deepEqual(Object.keys(r).sort(), ["code", "disclaimer", "stateId", "text", "variantIndex"]);
});
