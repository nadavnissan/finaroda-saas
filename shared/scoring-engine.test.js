// P1.5 placeholder validation — the scoring-engine stub exposes the expected
// signatures and every function returns the TODO sentinel (no logic yet).
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  TODO,
  ema7Slope,
  scoreDirection,
  computeReversalAnchor,
  computeSL,
  computeTP,
} from "./scoring-engine.js";

test("TODO sentinel is a frozen marker object", () => {
  assert.equal(TODO.__todo, true);
  assert.equal(typeof TODO.message, "string");
  assert.ok(Object.isFrozen(TODO));
});

test("all expected functions are exported", () => {
  for (const fn of [
    ema7Slope,
    scoreDirection,
    computeReversalAnchor,
    computeSL,
    computeTP,
  ]) {
    assert.equal(typeof fn, "function");
  }
});

test("every stub returns the TODO sentinel (not-yet-implemented)", () => {
  assert.equal(ema7Slope([1, 2, 3]), TODO);
  assert.equal(scoreDirection({}, "long"), TODO);
  assert.equal(computeReversalAnchor({}, "short"), TODO);
  assert.equal(computeSL(100, {}, "long"), TODO);
  assert.equal(computeTP(100, 95, "long"), TODO);
});
