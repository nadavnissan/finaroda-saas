// Stage 7 unit tests — admin filters/rows, breadcrumb ring buffer, Sentry gating.
// Run: node --test --experimental-strip-types tests/admin.unit.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  EMPTY_FILTERS,
  filtersToQuery,
  queryToFilters,
  userRow,
  type AdminUser,
} from "../src/lib/adminFilters.ts";
import { ringPush, MAX_BREADCRUMBS } from "../src/lib/breadcrumbs.ts";
import { shouldInitSentry } from "../src/lib/sentry.ts";

// ── filter state ↔ URL (AC2) ─────────────────────────────────────────────────
test("filtersToQuery serializes only non-empty fields", () => {
  const q = filtersToQuery({ ...EMPTY_FILTERS, plan: "pro", min_scans: "5" });
  const p = new URLSearchParams(q);
  assert.equal(p.get("plan"), "pro");
  assert.equal(p.get("min_scans"), "5");
  assert.equal(p.get("status"), null);
  assert.equal(filtersToQuery(EMPTY_FILTERS), "");
});

test("queryToFilters round-trips filtersToQuery", () => {
  const f = { ...EMPTY_FILTERS, search: "nadav", plan: "basic", status: "churned", min_scans: "3" };
  const back = queryToFilters(filtersToQuery(f));
  assert.deepEqual(back, f);
});

test("queryToFilters tolerates a leading '?' and missing keys", () => {
  const f = queryToFilters("?plan=free");
  assert.equal(f.plan, "free");
  assert.equal(f.status, "");
});

// ── table render with new columns (AC1) ──────────────────────────────────────
test("userRow formats the v1.1 columns", () => {
  const u: AdminUser = {
    id: 1, email: "a@b.com", call_sign: "NADAV", tier: "pro", subscription_status: "active",
    signup_at: "2026-01-01T00:00:00", last_active: "2026-07-14T12:00:00",
    xp: 1500, rank_level: 2, rank_name: "Risk Manager",
    scans_total: 40, scans_week: 6, active_days_7d: 3, active_days_30d: 5,
    referrals: 0, churn_survey: true,
  };
  const c = userRow(u);
  assert.equal(c.name, "NADAV");
  assert.equal(c.plan, "PRO");
  assert.equal(c.lastActive, "2026-07-14");
  assert.equal(c.scans, "40 (6w)");
  assert.equal(c.rank, "L2 Risk Manager");
  assert.equal(c.activeDays, "3/5");
  assert.equal(c.referrals, "0");
  assert.equal(c.churn, "YES");
});

test("userRow falls back to email when no call sign, and shows churn dot", () => {
  const c = userRow({
    id: 2, email: "x@y.com", call_sign: null, tier: "free", subscription_status: "trial",
    last_active: null, xp: 0, rank_level: 1, rank_name: "Strategy Apprentice",
    scans_total: 0, scans_week: 0, active_days_7d: 0, active_days_30d: 0,
    referrals: 0, churn_survey: false,
  });
  assert.equal(c.name, "x@y.com");
  assert.equal(c.lastActive, "·");
  assert.equal(c.churn, "·");
});

// ── breadcrumb ring buffer overflow at 20 (AC7) ──────────────────────────────
test("ringPush caps at max, keeping the newest entries", () => {
  let buf: number[] = [];
  for (let i = 0; i < 25; i++) buf = ringPush(buf, i, MAX_BREADCRUMBS);
  assert.equal(buf.length, 20);
  assert.equal(buf[0], 5);   // oldest kept
  assert.equal(buf[19], 24); // newest
});

// ── Sentry client init gating (AC6) ──────────────────────────────────────────
test("shouldInitSentry requires a DSN and a non-test env", () => {
  assert.equal(shouldInitSentry("https://x@sentry.io/1", "production"), true);
  assert.equal(shouldInitSentry("", "production"), false);
  assert.equal(shouldInitSentry(undefined, "production"), false);
  assert.equal(shouldInitSentry("https://x@sentry.io/1", "test"), false);
});
