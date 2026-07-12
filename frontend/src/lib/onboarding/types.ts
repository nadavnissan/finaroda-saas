// Onboarding F13 — shared types + terminal palette (mirrors UX §7 / globals.css).

export interface Candle {
  t: number; // epoch ms (daily)
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
  ema7?: number | null;
  ema200?: number | null;
}

export type ScenarioType = "trap" | "valid_setup" | "discipline_save" | "patience";

export interface EpisodeSetup {
  ext_id: string;
  coin: string;
  date_range: string;
  scenario_type: ScenarioType;
  lesson_flag: string | null;
  direction: "long" | "short" | null;
  entry_index: number;
  entry_price: number | null;
  spike_index: number | null;
  setup_klines: Candle[];
  reveal_count: number;
  score: number | null;
}

export interface EpisodeOutcome {
  resolved: "win" | "loss";
  direction: string;
  entry_price: number | null;
  exit_price: number | null;
  r_multiple: number | null;
  pct: number | null;
  squeeze_pct: number | null;
  score: number | null;
  real_stats_ref: string | null;
}

export interface EpisodeReveal {
  ext_id: string;
  reveal_klines: Candle[];
  outcome: EpisodeOutcome;
}

export interface XPState {
  total: number;
  events: { source: string; ref: string; amount: number }[];
}

// Onboarding XP refs — amounts mirror the server (which is authoritative).
export const XP_AMOUNTS: Record<string, number> = {
  s2_scan: 50,
  s4_first_decision: 100,
  s8_scan: 50,
  s8_lesson: 100,
};
export const XP_TARGET = 300;

// Terminal palette (locked, UX §7).
export const C = {
  bg: "#0b0d12",
  panel: "#161B22",
  border: "#2a2f37",
  fg: "#E9EEF3",
  green: "#1FB286",
  amber: "#E0913F",
  red: "#E0584F",
  muted: "#8593A2",
  subtle: "#5c6672",
} as const;
