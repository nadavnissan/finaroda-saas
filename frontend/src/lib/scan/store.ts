// Remembered client choices — Analysis Lens + Risk Style (localStorage, SSR-safe).
import type { Lens, RiskStyle } from "./types";

const LENS_KEY = "finaroda_lens";
const RISK_KEY = "finaroda_risk_style";

export function getLens(): Lens {
  if (typeof window === "undefined") return "Full";
  return (window.localStorage.getItem(LENS_KEY) as Lens) ?? "Full";
}

export function setLens(lens: Lens): void {
  if (typeof window !== "undefined") window.localStorage.setItem(LENS_KEY, lens);
}

export function getRiskStyle(): RiskStyle {
  if (typeof window === "undefined") return "Balanced";
  return (window.localStorage.getItem(RISK_KEY) as RiskStyle) ?? "Balanced";
}

export function setRiskStyle(style: RiskStyle): void {
  if (typeof window !== "undefined") window.localStorage.setItem(RISK_KEY, style);
}

// Coin selection (Decision C) — which coins the user scans within their plan count.
// Persisted client-side; the plan count still hard-caps the scan server-side.
const COINS_KEY = "finaroda_coin_prefs";

export function getCoinPrefs(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(COINS_KEY);
    const arr = raw ? (JSON.parse(raw) as unknown) : [];
    return Array.isArray(arr) ? arr.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function setCoinPrefs(coins: string[]): void {
  if (typeof window !== "undefined") window.localStorage.setItem(COINS_KEY, JSON.stringify(coins));
}

const SCANS_KEY = "finaroda_scans";

// Disciplined counter — total scans performed (used by the empty-state badge).
export function incScanCount(): number {
  if (typeof window === "undefined") return 0;
  const n = (parseInt(window.localStorage.getItem(SCANS_KEY) ?? "0", 10) || 0) + 1;
  window.localStorage.setItem(SCANS_KEY, String(n));
  return n;
}

// ── Scan landing phase (HOTFIX v0.18.2) ──────────────────────────────────────
// The scan route ALWAYS opens on the INPUT screen. A completed scan result is
// reachable via /history (Recent scans) and must never be the forced landing state:
// the FINARODA logo, the hamburger "Scan" entry, and post-checkout redirects all
// re-enter /scan and must show a fresh input, ready for a new scan.
//
// This supersedes the earlier "Bug 5" behaviour, which persisted the last scan to
// sessionStorage and restored the RESULTS state on every mount — that restore
// hijacked navigation and trapped users in the last-result view (founder-reported).
// There is intentionally no completed-result restore API: re-introducing one would
// bring the trap back. In-flight scans are not resumed either (the request is gone
// on remount); the result is re-derived by running a new scan.
export type ScanPhase = "idle" | "scanning" | "results" | "empty" | "limit";
export const INITIAL_SCAN_PHASE: ScanPhase = "idle";
