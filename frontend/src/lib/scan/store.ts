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

const SCANS_KEY = "finaroda_scans";

// Disciplined counter — total scans performed (used by the empty-state badge).
export function incScanCount(): number {
  if (typeof window === "undefined") return 0;
  const n = (parseInt(window.localStorage.getItem(SCANS_KEY) ?? "0", 10) || 0) + 1;
  window.localStorage.setItem(SCANS_KEY, String(n));
  return n;
}
