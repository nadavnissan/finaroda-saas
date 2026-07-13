// Shared client types for Package B phase 2 (B4 dashboard, B5 profile, B6 academy,
// B7 admin). Mirror the backend Pydantic models. Outcome fields on a scenario are
// present ONLY when revealed (reveal-gating) — the server omits them otherwise, so an
// unrevealed row simply has no status/r_result to render.

export interface ScenarioView {
  id: number;
  type: "pass" | "no_setups_day";
  coin?: string | null;
  direction?: "long" | "short" | null;
  score?: number | null;
  scan_date?: string | null;
  revealed: boolean;
  // Present only when revealed:
  status?: string | null;       // win | loss | save | expired | skip
  r_result?: number | null;     // hypothetical R, never money
  resolved_at?: string | null;
  viewed?: boolean | null;
}

export interface JournalStats {
  cumulative_r_revealed: number;
  capital_saves: number;
  awaiting_reveal: number;
  skip_days: number;
  tracked_days: number;
  discipline_pct: number;
}

export interface JournalResponse {
  stats: JournalStats;
  scenarios: ScenarioView[];
}

export interface TrialState {
  active: boolean;
  day: number;
  total: number;
  no_card: boolean;
}

export interface ProfileSettings {
  analysis_lens: "ema200" | "rsi" | "volume" | "full";
  risk_style: "conservative" | "balanced" | "aggressive";
  coin_prefs: string[];
  palette: string;
}

export interface ProfileResponse {
  call_sign: string;
  email: string;
  tier: string;
  subscription_status: string;
  trial?: TrialState | null;
  xp_total: number;
  settings: ProfileSettings;
}

export interface AcademyModule {
  id: string;
  title: string;
  minutes: number;
  term_count: number;
  has_lesson: boolean;
  tier: string;
  rank_unlock?: number | null;
  unlocked: boolean;
  completed: boolean;
}

export interface AcademyResponse {
  modules: AcademyModule[];
  xp_total: number;
}

export interface Me {
  internal_id: number;
  email: string;
  is_admin: boolean;
  tier: string;
  subscription_status: string;
  onboarding_completed: boolean;
}
