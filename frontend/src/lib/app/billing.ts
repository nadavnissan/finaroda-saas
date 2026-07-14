// Billing UI helpers (Stage 3). Pure + unit-tested — no React, no network. Money is
// agorot ints end-to-end (matches the backend, D-B10); the display converts to a final
// VAT-inclusive shekel string (D-B2).

export type SubStatus =
  | "none"
  | "trial"
  | "active"
  | "past_due"
  | "cancelled"
  | "expired";

export interface BillingBannerModel {
  kind: "past_due" | "cancelled" | "expired";
  title: string;
  message: string;
  cta: string;
}

// The in-app banner for a subscription that needs the user's attention (D-B5/D-B6).
// Returns null for healthy states (none/trial/active) — nothing to show.
export function billingBanner(
  status: string,
  accessUntil?: string | null,
): BillingBannerModel | null {
  switch (status) {
    case "past_due":
      return {
        kind: "past_due",
        title: "Payment issue",
        message:
          "We could not process your last payment. We will retry automatically. " +
          "Update your card to keep your plan.",
        cta: "Update payment",
      };
    case "cancelled":
      return {
        kind: "cancelled",
        title: "Subscription cancelled",
        message: accessUntil
          ? `You keep full access until ${accessUntil}, then your account moves to Free.`
          : "You keep access until the end of the current period, then move to Free.",
        cta: "Re-subscribe",
      };
    case "expired":
      return {
        kind: "expired",
        title: "Subscription ended",
        message:
          "Your subscription ended and your account is on Free. " +
          "Re-subscribe any time to restore the full toolkit.",
        cta: "Re-subscribe",
      };
    default:
      return null;
  }
}

// Agorot int -> final shekel string, e.g. 14900 -> "₪149.00". No float rounding: the
// integer division keeps the shekels and the remainder is the agorot, zero-padded.
export function formatAgorotIls(agorot: number): string {
  const n = Math.trunc(agorot);
  const shekels = Math.trunc(Math.abs(n) / 100);
  const rem = Math.abs(n) % 100;
  const sign = n < 0 ? "-" : "";
  return `${sign}₪${shekels}.${String(rem).padStart(2, "0")}`;
}

// True when the state should still grant the paid plan tier (access retained). Mirrors
// the backend billing_state.ENTITLED_STATES.
export function isEntitled(status: string): boolean {
  return (
    status === "trial" ||
    status === "active" ||
    status === "past_due" ||
    status === "cancelled"
  );
}
