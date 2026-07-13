// Remembered client choices — Analysis Lens + Risk Style (localStorage, SSR-safe).
import type { Blueprint, Lens, MarketData, RiskStyle } from "./types";

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

// ── Scan session (Bug 5) ─────────────────────────────────────────────────────
// The scan results live in local component state, so leaving /scan for /subscribe
// (SEE PLANS) and coming back reset the page to the controls. We persist the last
// scan to sessionStorage so returning restores the RESULTS state (coins still
// tappable — the market data is restored too). sessionStorage = tab-scoped, so it
// clears when the tab closes; a fresh scan overwrites it.
const SESSION_KEY = "finaroda_scan_session";

export interface ScanSession {
  phase: "results" | "empty";
  passers: Blueprint[];
  nonPassers: Blueprint[];
  scanned: number;
  timestamp: string;
  xpAwarded: boolean;
  scanCount: number;
  md: [string, MarketData][]; // rebuilds the mdRef map (coin → market data)
  ids: [string, number][];    // rebuilds the score_log id map (coin → id)
}

export function saveScanSession(session: ScanSession): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    // Quota or serialization failure is non-fatal; the live scan still works.
  }
}

export function loadScanSession(): ScanSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as ScanSession) : null;
  } catch {
    return null;
  }
}

export function clearScanSession(): void {
  if (typeof window !== "undefined") window.sessionStorage.removeItem(SESSION_KEY);
}
