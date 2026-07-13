// Pure-logic unit tests for Package B phase 2 (B4 reveal-gating display).
// The headline contract: an UNREVEALED scenario yields no outcome to render, so a
// blurred row cannot carry outcome data in the DOM (same guarantee as S10).
// Run: node --test --experimental-strip-types tests/pkgb2.unit.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";

import { scenarioOutcome } from "../src/lib/app/scenario.ts";
import type { ScenarioView } from "../src/lib/app/types.ts";

test("reveal-gating: an unrevealed scenario yields NO outcome (nothing to render)", () => {
  const s: ScenarioView = { id: 1, type: "pass", coin: "BTCUSDT", direction: "short", score: 86, revealed: false };
  assert.equal(scenarioOutcome(s), null);
});

test("reveal-gating: a revealed win shows +R and WIN", () => {
  const s: ScenarioView = { id: 2, type: "pass", coin: "ADAUSDT", direction: "short", score: 86, revealed: true, status: "win", r_result: 3 };
  const o = scenarioOutcome(s);
  assert.equal(o?.top, "+3.00R");
  assert.equal(o?.bottom, "WIN · REVEALED");
  assert.equal(o?.tone, "green");
});

test("reveal-gating: a revealed save is symmetric with a win (co-equal SAVE)", () => {
  const s: ScenarioView = { id: 3, type: "pass", coin: "LINKUSDT", direction: "short", score: 86, revealed: true, status: "save", r_result: 0 };
  const o = scenarioOutcome(s);
  assert.equal(o?.top, "SAVE");
  assert.equal(o?.bottom, "LOSS AVOIDED");
  assert.equal(o?.tone, "green");
});

test("reveal-gating: a revealed loss shows -1R in the red tone", () => {
  const s: ScenarioView = { id: 4, type: "pass", coin: "BTCUSDT", direction: "long", score: 86, revealed: true, status: "loss", r_result: -1 };
  const o = scenarioOutcome(s);
  assert.equal(o?.top, "-1.00R");
  assert.equal(o?.tone, "red");
});
