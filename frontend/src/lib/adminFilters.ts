// Stage 7 admin user-table filters + row formatting. Pure logic, unit-tested.
// Filter state is URL-encodable (shareable / refreshable, AC2) and drives both the
// /api/admin/users query and the CSV export (same params → identical filtered view).

export interface UserFilters {
  search: string;
  plan: string; // "" | free | basic | pro
  status: string; // "" | trial | active | expired | churned
  signup_from: string; // YYYY-MM-DD
  signup_to: string;
  active_from: string;
  active_to: string;
  min_scans: string; // kept as string for the input; "" = unset
}

export const EMPTY_FILTERS: UserFilters = {
  search: "", plan: "", status: "",
  signup_from: "", signup_to: "", active_from: "", active_to: "", min_scans: "",
};

const _KEYS = Object.keys(EMPTY_FILTERS) as (keyof UserFilters)[];

/** Serialize non-empty filters to a URL query string (stable key order). */
export function filtersToQuery(f: UserFilters): string {
  const p = new URLSearchParams();
  for (const k of _KEYS) {
    const v = (f[k] ?? "").trim();
    if (v) p.set(k, v);
  }
  return p.toString();
}

/** Parse a query string back into a full filter object (missing keys → ""). */
export function queryToFilters(qs: string): UserFilters {
  const p = new URLSearchParams(qs.startsWith("?") ? qs.slice(1) : qs);
  const out: UserFilters = { ...EMPTY_FILTERS };
  for (const k of _KEYS) {
    const v = p.get(k);
    if (v !== null) out[k] = v;
  }
  return out;
}

export interface AdminUser {
  id: number;
  email: string;
  call_sign?: string | null;
  tier: string;
  subscription_status: string;
  signup_at?: string | null;
  last_active?: string | null;
  xp: number;
  rank_level: number;
  rank_name: string;
  scans_total: number;
  scans_week: number;
  active_days_7d: number;
  active_days_30d: number;
  referrals: number;
  churn_survey: boolean;
  suspended?: boolean;
}

/** Pure display mapping for one table row (new v1.1 columns). */
export function userRow(u: AdminUser) {
  return {
    name: u.call_sign ?? u.email,
    plan: u.tier.toUpperCase(),
    status: u.subscription_status.toUpperCase(),
    lastActive: u.last_active ? String(u.last_active).slice(0, 10) : "·",
    scans: `${u.scans_total} (${u.scans_week}w)`,
    xp: String(u.xp),
    rank: `L${u.rank_level} ${u.rank_name}`,
    activeDays: `${u.active_days_7d}/${u.active_days_30d}`,
    referrals: String(u.referrals),
    churn: u.churn_survey ? "YES" : "·",
  };
}
