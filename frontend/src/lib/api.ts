// Minimal API client for the FINARODA backend.
// Uses httpOnly cookie auth → every request sends credentials.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
      const detail = (body as { detail?: ApiError } | null)?.detail ?? null;
      return { ok: false, status: res.status, data: null, error: detail ?? { message: "Request failed" } };
    }
    return { ok: true, status: res.status, data: body as T, error: null };
  } catch {
    return { ok: false, status: 0, data: null, error: { message: "Network error" } };
  }
}

export const api = {
  requestMagicLink: (email: string) =>
    apiFetch("/api/auth/magic-link", { method: "POST", body: JSON.stringify({ email }) }),
  verify: (token: string) =>
    apiFetch(`/api/auth/verify?token=${encodeURIComponent(token)}`, { method: "GET" }),
  me: () => apiFetch("/api/auth/me", { method: "GET" }),
  logout: () => apiFetch("/api/auth/logout", { method: "POST" }),
  joinWaitlist: (email: string) =>
    apiFetch("/api/waitlist", { method: "POST", body: JSON.stringify({ email }) }),
  initiateCheckout: (plan: string) =>
    apiFetch("/api/cardcom/initiate", { method: "POST", body: JSON.stringify({ plan }) }),
  startTrial: () => apiFetch("/api/cardcom/trial", { method: "POST" }),
  getPlans: () => apiFetch("/api/plans", { method: "GET" }),
};
