// Minimal API client for the FINARODA backend.
// Uses httpOnly cookie auth → every request sends credentials.
import { addBreadcrumb } from "@/lib/breadcrumbs";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ApiError {
  code?: string;
  message?: string;
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<{ ok: boolean; status: number; data: T | null; error: ApiError | null }> {
  try {
    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    });
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    if (!res.ok) {
      addBreadcrumb("api_error", { path, code: res.status });
      const detail = (body as { detail?: ApiError } | null)?.detail ?? null;
      return { ok: false, status: res.status, data: null, error: detail ?? { message: "Request failed" } };
    }
    // Record scan submits from the one call site (no journal outcome values involved).
    if (path === "/api/scan/events" && (options.method ?? "GET").toUpperCase() === "POST") {
      addBreadcrumb("scan_submit", { path });
    }
    return { ok: true, status: res.status, data: body as T, error: null };
  } catch {
    addBreadcrumb("api_error", { path, code: 0 });
    return { ok: false, status: 0, data: null, error: { message: "Network error" } };
  }
}

export const api = {
  // referralCode: bound once at signup from a /r/<code> visit (D-S6). Harmless on login.
  requestMagicLink: (email: string, referralCode?: string | null) =>
    apiFetch("/api/auth/magic-link", {
      method: "POST",
      body: JSON.stringify(referralCode ? { email, referral_code: referralCode } : { email }),
    }),
  verify: (token: string) =>
    apiFetch(`/api/auth/verify?token=${encodeURIComponent(token)}`, { method: "GET" }),
  me: () => apiFetch("/api/auth/me", { method: "GET" }),
  logout: () => apiFetch("/api/auth/logout", { method: "POST" }),
  joinWaitlist: (email: string) =>
    apiFetch("/api/waitlist", { method: "POST", body: JSON.stringify({ email }) }),
  // Start a Stripe Checkout session (returns { redirect_url } to the hosted checkout).
  // promotionCode is validated our-side for the plan before the session is created (D-S1).
  initiateCheckout: (plan: string, promotionCode?: string | null) =>
    apiFetch("/api/billing/checkout", {
      method: "POST",
      body: JSON.stringify(promotionCode ? { plan, promotion_code: promotionCode } : { plan }),
    }),
  startTrial: () => apiFetch("/api/billing/trial", { method: "POST" }),
  getPlans: () => apiFetch("/api/plans", { method: "GET" }),
  // Cancel at period end (D-B6). Returns { access_until, message }.
  cancelSubscription: () => apiFetch("/api/billing/cancel", { method: "POST" }),
  // Persist the onboarding S9 call-sign (identity) to the profile.
  saveCallSign: (callSign: string) =>
    apiFetch("/api/profile/settings", { method: "PUT", body: JSON.stringify({ call_sign: callSign }) }),
  // Stage 4 — referral + coupons.
  getReferral: () => apiFetch("/api/referral", { method: "GET" }),
  validateCoupon: (code: string, plan: string) =>
    apiFetch("/api/billing/coupon/validate", { method: "POST", body: JSON.stringify({ code, plan }) }),
  adminListCoupons: () => apiFetch("/api/admin/coupons", { method: "GET" }),
  adminCreateCoupon: (body: unknown) =>
    apiFetch("/api/admin/coupons", { method: "POST", body: JSON.stringify(body) }),
  adminDeactivateCoupon: (id: number) =>
    apiFetch(`/api/admin/coupons/${id}/deactivate`, { method: "POST" }),
  adminListReferrals: () => apiFetch("/api/admin/referrals", { method: "GET" }),
  adminVoidReferral: (id: number, note: string) =>
    apiFetch(`/api/admin/referrals/${id}/void`, { method: "POST", body: JSON.stringify({ note }) }),
};
