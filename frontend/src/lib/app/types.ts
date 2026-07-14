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

// Academy 2.0 (Stage 6): DB-backed lessons, flat card grid, dual gating, text/video.
export interface AcademyLesson {
  slug: string;
  title: string;
  description: string;
  content_type: "text" | "video";
  duration_minutes: number;
  tags: string[];
  min_plan: "free" | "basic" | "pro";
  min_rank: number;
  sort_index: number;
  unlocked: boolean;
  completed: boolean;
  awards_xp: boolean;
  lock_reason?: string | null;
  // Backward-compatible aliases (== slug / duration_minutes).
  id: string;
  minutes: number;
}

// The list endpoint keeps the key `modules` for backward compatibility.
export interface AcademyResponse {
  modules: AcademyLesson[];
  xp_total: number;
}

// Full gated content from GET /api/academy/{slug} (403 when locked).
export interface LessonContent {
  slug: string;
  title: string;
  description: string;
  content_type: "text" | "video";
  duration_minutes: number;
  tags: string[];
  body: string;
  video_url?: string | null;
  completed: boolean;
  awards_xp: boolean;
}

// Admin lesson row (create/edit/reorder/archive).
export interface AdminLesson {
  id: number;
  slug: string;
  title: string;
  description: string;
  content_type: "text" | "video";
  body: string;
  video_url?: string | null;
  duration_minutes: number;
  tags: string[];
  min_plan: "free" | "basic" | "pro";
  min_rank: number;
  sort_index: number;
  awards_xp: boolean;
  archived: boolean;
}

export interface Me {
  internal_id: number;
  email: string;
  is_admin: boolean;
  tier: string;
  subscription_status: string;
  onboarding_completed: boolean;
}

// Stage 5 — in-app notifications (bell feed) + prefs. Mirror the backend rows.
export interface NotificationItem {
  id: number;
  type: string;                 // trial_reminder | reveal_teaser | broadcast
  title: string;
  body: string;
  link_path?: string | null;    // in-app deep link
  created_at: string;
  read_at?: string | null;      // null => unread
}

export interface NotificationFeed {
  notifications: NotificationItem[];
  unread_count: number;
}

export interface NotificationPrefs {
  inapp_enabled: boolean;
  sound_enabled: boolean;
  vibration_enabled: boolean;
  email_product: boolean;
  email_broadcast: boolean;
}
