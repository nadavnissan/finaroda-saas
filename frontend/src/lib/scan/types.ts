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
  t?: number[]; // candle start epoch ms (daily; used to draw the Chart Standard)
}

// The marketData contract (shared/scoring-engine.api.md) + scorer inputs
// (weekly, oi, oiChangePct) and the coin's 24h change (for marketContext).
export interface MarketData {
  daily: OHLCV;
  hourly: OHLCV;
  weekly: OHLCV;
  price: number;
  funding: number;
  oi: number | null;
  oiChangePct: number | null;
  change24h: number; // percent
}

export type Profile = "momentum" | "pullback" | "continuation";
export type PassLabel = "PASS" | "WATCH" | "HIDE";

// E7b — why a non-passing coin did not PASS. Names the blocking check in plain
// language via a locked concept label + its Concept Tooltip. NEVER exposes a
// score, weight or formula (RED LINE). Deterministic, sourced from verified data.
export interface WhyNot {
  checkId: string;   // short blocking-check id (e.g. "regime")
  checkLabel: string; // locked concept label shown after "blocking check:"
  tooltipId: string;  // Concept Tooltip id for the dotted term
  term: string;       // the dotted term inside the sentence (e.g. "the 200-day average")
  text: string;       // the plain-language why-not sentence (term rendered as a tooltip)
}

// One calculated level on the Trading Blueprint, with its transparency note.
export interface Level {
  value: number;
  pct?: number;
  note: string; // formula-transparency note (PRD §3.5.2)
}

// The Trading Blueprint (PRD §3.5.1). `score` is the REAL momentum-profile score
// from scoreDirection. Pullback/continuation scores are logged, not displayed.
export interface Blueprint {
  coin: string;
  direction: Direction;
  score: number; // real momentum-profile score (0–110)
  signal: "EXECUTE" | "WAIT" | "NO TRADE";
  passLabel: PassLabel; // SaaS 85/82 gate (RED LINE: never client-touchable)
  // Other-profile scores — LOGGED for measure-first, NOT displayed:
  profileScores: Record<Profile, number | null>;
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
  ema200: number; // regime reference (drawn on the chart; sources E7b why-not)
  price: number;
  riskStyle: RiskStyle;
  whyNot: WhyNot | null; // set only when passLabel === "HIDE" (E7b)
}

export interface CoinScanResult {
  coin: string;
  blueprint: Blueprint | null; // null when levels are invalid (skipped)
  error?: string;
}
