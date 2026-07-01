// Shared types for the client-side scan core (P2).

export type Direction = "long" | "short";
export type Lens = "EMA200" | "RSI" | "Volume" | "Full";
export type RiskStyle = "Conservative" | "Balanced" | "Aggressive";

export interface OHLCV {
  o: number[];
  h: number[];
  l: number[];
  c: number[];
  v: number[];
}

// The marketData contract from shared/scoring-engine.api.md.
export interface MarketData {
  daily: OHLCV;
  hourly: OHLCV;
  price: number;
  funding: number;
}

// One calculated level on the Trading Blueprint, with its transparency note.
export interface Level {
  value: number;
  pct?: number;
  note: string; // formula-transparency note (PRD §3.5.2)
}

// The Trading Blueprint (PRD §3.5.1). NOTE: `score` is intentionally null — the
// numeric score is blocked until engine pass 2. It is NEVER invented here.
export interface Blueprint {
  coin: string;
  direction: Direction;
  score: null; // pending engine pass 2 — see scorePending
  scorePending: true;
  // Calculated levels (calculator terminology — PRD §3.5.1):
  mathematicalTriggerPoint: Level; // was Entry
  calculatedRiskLevel: Level; // was Stop Loss
  calculatedTargetLevel: Level; // was Take Profit
  dynamicRiskLevel: Level; // was Trailing
  riskReward: number | null;
  // Verified / collected indicators:
  ema7SlopePct: number; // signed, verified edge
  volumeRatio: number; // collected
  rsi: number;
  adx: { adx: number; plusDI: number; minusDI: number } | null;
  price: number;
  riskStyle: RiskStyle;
  interimPassed: boolean; // interim visibility gate (levels valid + lens condition)
}

export interface CoinScanResult {
  coin: string;
  blueprint: Blueprint | null; // null when levels are invalid (skipped)
  error?: string;
}
