// Pure-logic unit tests for Stage 3 billing UI helpers (price render, banner states,
// cancel entitlement). Run: node --test --experimental-strip-types tests/billing.unit.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";

import { billingBanner, formatAgorotIls, isEntitled } from "../src/lib/app/billing.ts";

// ── price rendering from agorot (AC7 / D-B2) ─────────────────────────────────
test("formatAgorotIls: agorot -> final shekel string, exact (no float drift)", () => {
  assert.equal(formatAgorotIls(5900), "₪59.00");
  assert.equal(formatAgorotIls(14900), "₪149.00");
  assert.equal(formatAgorotIls(99), "₪0.99");
  assert.equal(formatAgorotIls(100), "₪1.00");
  assert.equal(formatAgorotIls(0), "₪0.00");
  assert.equal(formatAgorotIls(12345), "₪123.45");
});

// ── in-app banner state machine (D-B5 / D-B6) ────────────────────────────────
test("billingBanner: healthy states render nothing", () => {
  assert.equal(billingBanner("none"), null);
  assert.equal(billingBanner("trial"), null);
  assert.equal(billingBanner("active"), null);
});

test("billingBanner: past_due surfaces an update-payment banner", () => {
  const b = billingBanner("past_due");
  assert.ok(b);
  assert.equal(b?.kind, "past_due");
  assert.equal(b?.cta, "Update payment");
});

test("billingBanner: cancelled shows the access-until date when known", () => {
  const withDate = billingBanner("cancelled", "31/07/2026");
  assert.ok(withDate?.message.includes("31/07/2026"));
  const noDate = billingBanner("cancelled");
  assert.ok(noDate?.message.length && !noDate.message.includes("undefined"));
  assert.equal(withDate?.cta, "Re-subscribe");
});

test("billingBanner: expired tells the user they are on Free", () => {
  const b = billingBanner("expired");
  assert.equal(b?.kind, "expired");
  assert.ok(b?.message.toLowerCase().includes("free"));
});

// ── cancel gating: only entitled states have something to cancel (AC5) ───────
test("isEntitled: paid/trial/grace states are entitled; none/expired are not", () => {
  assert.equal(isEntitled("trial"), true);
  assert.equal(isEntitled("active"), true);
  assert.equal(isEntitled("past_due"), true);
  assert.equal(isEntitled("cancelled"), true);
  assert.equal(isEntitled("none"), false);
  assert.equal(isEntitled("expired"), false);
  assert.equal(isEntitled(""), false);
});
