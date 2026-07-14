// Pure-logic unit tests for Stage 4 (coupons + referral) UI helpers.
// Run: node --test --experimental-strip-types tests/promotions.unit.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  REFERRAL_KEY,
  couponIsRedeemable,
  couponReasonMessage,
  formatCouponDiscount,
  inviteSummaryLine,
  type CouponMirror,
} from "../src/lib/app/promotions.ts";

// ── coupon discount rendering (percent + fixed agorot) ───────────────────────
test("formatCouponDiscount: percent and fixed render human strings", () => {
  assert.equal(formatCouponDiscount("percent", 20, null), "20% off");
  assert.equal(formatCouponDiscount("fixed", null, 1000), "₪10.00 off");
  assert.equal(formatCouponDiscount("fixed", null, 14900), "₪149.00 off");
  assert.equal(formatCouponDiscount("percent", null, null), "discount");
});

// ── redeemable gate: active + under cap + not expired ────────────────────────
function coupon(over: Partial<CouponMirror>): CouponMirror {
  return {
    id: 1, code: "X", discount_type: "percent", percent_off: 10,
    redeemed_count: 0, active: true, ...over,
  };
}

test("couponIsRedeemable: inactive is never redeemable", () => {
  assert.equal(couponIsRedeemable(coupon({ active: false })), false);
});

test("couponIsRedeemable: max redemptions reached blocks", () => {
  assert.equal(couponIsRedeemable(coupon({ max_redemptions: 3, redeemed_count: 3 })), false);
  assert.equal(couponIsRedeemable(coupon({ max_redemptions: 3, redeemed_count: 2 })), true);
  assert.equal(couponIsRedeemable(coupon({ max_redemptions: null, redeemed_count: 999 })), true);
});

test("couponIsRedeemable: expired coupon blocks", () => {
  assert.equal(couponIsRedeemable(coupon({ expires_at: "2000-01-01T00:00:00Z" })), false);
  assert.equal(couponIsRedeemable(coupon({ expires_at: "2999-01-01T00:00:00Z" })), true);
});

// ── rejection messages mirror backend reason codes ───────────────────────────
test("couponReasonMessage: each reason has a plain-language message", () => {
  assert.ok(couponReasonMessage("WRONG_PLAN").toLowerCase().includes("plan"));
  assert.ok(couponReasonMessage("EXPIRED").toLowerCase().includes("expired"));
  assert.ok(couponReasonMessage("MAX_REDEEMED").toLowerCase().includes("limit"));
  assert.ok(couponReasonMessage("NOT_FOUND").length > 0);
  assert.ok(couponReasonMessage(undefined).length > 0);
});

// ── invite section: link + credit counts summary ─────────────────────────────
test("REFERRAL_KEY is the stable localStorage key", () => {
  assert.equal(REFERRAL_KEY, "finaroda_referral_source");
});

test("inviteSummaryLine: pluralization + rewards + banked", () => {
  assert.equal(
    inviteSummaryLine({ code: "A", share_link: "l", referred_count: 1, rewarded_count: 0, credits_banked: 0 }),
    "1 friend joined.",
  );
  assert.equal(
    inviteSummaryLine({ code: "A", share_link: "l", referred_count: 3, rewarded_count: 2, credits_banked: 1 }),
    "3 friends joined, 2 free months earned, 1 banked.",
  );
  assert.equal(
    inviteSummaryLine({ code: "A", share_link: "l", referred_count: 0, rewarded_count: 0, credits_banked: 0 }),
    "0 friends joined.",
  );
});
