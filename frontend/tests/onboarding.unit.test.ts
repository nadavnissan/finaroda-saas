// Pure-logic unit tests for onboarding round-2 fixes.
// Run: node --test --experimental-strip-types tests/onboarding.unit.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";

import { crossedLevel, levelFor } from "../src/lib/onboarding/xp.ts";
import { renderNow } from "../src/lib/onboarding/tooltipTemplate.ts";
import { createOnce } from "../src/lib/onboarding/once.ts";

// ── item 8: LEVEL framing math (300 / 1,000) ──────────────────────────────────
test("levelFor: 300 XP is Level 1 Strategy Apprentice, 300/1000 toward Risk Manager", () => {
  const s = levelFor(300);
  assert.equal(s.level, 1);
  assert.equal(s.name, "Strategy Apprentice");
  assert.equal(s.next?.floor, 1000);
  assert.equal(s.next?.name, "Risk Manager");
  assert.equal(s.progressPct, 30); // 300 / 1000
  assert.equal(s.toNext, 700);
});

test("levelFor: rank thresholds 1000/3000/8000", () => {
  assert.equal(levelFor(0).level, 1);
  assert.equal(levelFor(999).level, 1);
  assert.equal(levelFor(1000).level, 2);
  assert.equal(levelFor(3000).level, 3);
  assert.equal(levelFor(8000).level, 4);
  assert.equal(levelFor(8000).next, null);
  assert.equal(levelFor(99999).progressPct, 100);
});

test("crossedLevel: true only on a threshold crossing (never within a level)", () => {
  assert.equal(crossedLevel(999, 1000), true); // rank up
  assert.equal(crossedLevel(0, 300), false); // onboarding stays in Level 1
  assert.equal(crossedLevel(300, 999), false);
  assert.equal(crossedLevel(2999, 3000), true);
});

// ── item 4: tooltip context-suppression ──────────────────────────────────────
test("renderNow: suppresses the whole line when a simple placeholder is missing", () => {
  assert.equal(renderNow("This setup's direction is {direction}.", {}), "");
  assert.equal(renderNow("This setup's direction is {direction}.", { direction: "LONG" }), "This setup's direction is LONG.");
});

test("renderNow: static templates (no placeholders) always render", () => {
  assert.equal(renderNow("The score is fixed until the next candle closes.", {}), "The score is fixed until the next candle closes.");
});

test("renderNow: conditional branch selected by a truthy ctx flag", () => {
  const tpl = "Price is {distance_pct}% {above_below} the average. {above: 'Healthy.' | below: 'Negative.'}";
  assert.equal(renderNow(tpl, { distance_pct: 20, above_below: "below", below: true }), "Price is 20% below the average. Negative.");
  // missing simple key -> suppressed even if a branch would match
  assert.equal(renderNow(tpl, { below: true }), "");
});

// ── item 2: single-shot transition guard ─────────────────────────────────────
test("createOnce: runs the action exactly once (no double transition)", () => {
  const once = createOnce();
  let count = 0;
  const first = once.run(() => { count += 1; });
  const second = once.run(() => { count += 1; });
  assert.equal(first, true);
  assert.equal(second, false);
  assert.equal(count, 1);
  assert.equal(once.done(), true);
});
