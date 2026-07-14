// Stage 4 — coupons + referral UI helpers. Pure + unit-tested — no React, no network.
// Money is agorot ints end-to-end (matches the backend, D-B10).
import { formatAgorotIls } from "./billing.ts";

// Client-side key for the /r/<code> referral binding (stored on visit, sent at signup).
export const REFERRAL_KEY = "finaroda_referral_source";

export interface CouponMirror {
  id: number;
  code: string;
  discount_type: "percent" | "fixed";
  percent_off?: number | null;
  amount_off_agorot?: number | null;
  plan_restriction?: string | null;
  max_redemptions?: number | null;
  redeemed_count: number;
  expires_at?: string | null;
  active: boolean;
}

export interface ReferralSummary {
  code: string;
  share_link: string;
  referred_count: number;
  rewarded_count: number;
  credits_banked: number;
}

// Human-readable discount, e.g. "20% off" or "₪10.00 off" (first charge only).
export function formatCouponDiscount(
  discountType: string,
  percentOff?: number | null,
  amountOffAgorot?: number | null,
): string {
  if (discountType === "percent" && percentOff) return `${percentOff}% off`;
  if (discountType === "fixed" && amountOffAgorot) return `${formatAgorotIls(amountOffAgorot)} off`;
  return "discount";
}

// A coupon is usable at checkout only while active and under any redemption cap.
export function couponIsRedeemable(c: CouponMirror): boolean {
  if (!c.active) return false;
  if (c.max_redemptions != null && c.redeemed_count >= c.max_redemptions) return false;
  if (c.expires_at) {
    const exp = Date.parse(c.expires_at);
    if (!Number.isNaN(exp) && exp < Date.now()) return false;
  }
  return true;
}

// Plain-language reason for a rejected coupon (mirrors the backend reason codes).
export function couponReasonMessage(reason: string | null | undefined): string {
  switch (reason) {
    case "NOT_FOUND":
      return "That code is not recognized.";
    case "INACTIVE":
      return "That code is no longer active.";
    case "EXPIRED":
      return "That code has expired.";
    case "MAX_REDEEMED":
      return "That code has reached its usage limit.";
    case "WRONG_PLAN":
      return "That code does not apply to this plan.";
    default:
      return "That code cannot be applied.";
  }
}

// One-line summary for the invite card: how many friends and rewards so far.
export function inviteSummaryLine(s: ReferralSummary): string {
  const friends = `${s.referred_count} ${s.referred_count === 1 ? "friend" : "friends"} joined`;
  const rewards = s.rewarded_count > 0
    ? `, ${s.rewarded_count} free ${s.rewarded_count === 1 ? "month" : "months"} earned`
    : "";
  const banked = s.credits_banked > 0 ? `, ${s.credits_banked} banked` : "";
  return `${friends}${rewards}${banked}.`;
}
