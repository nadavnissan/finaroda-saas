// Best-effort scan persistence (SPEC §5). If the user isn't signed in, these no-op
// silently (401) — the scan UX still works; it just isn't logged.
//
// Every scanned coin logs THREE rows (momentum/pullback/continuation) for
// measure-first base-rate research. Only momentum is displayed. Levels are logged on
// the momentum row (the displayed geometry); the other profiles log score only.

import { apiFetch } from "@/lib/api";

import { WATCH_THRESHOLD } from "./engine";
import type { Blueprint, Profile } from "./types";

export interface ScoreLogItemPayload {
  coin: string;
  direction: "long" | "short";
  profile: Profile;
  score: number | null;
  passed_threshold: number;
  ema7_slope_pct: number | null;
  volume_ratio: number | null;
  price: number | null;
  entry: number | null;
  sl: number | null;
  tp: number | null;
  trailing_pct: number | null;
}

// One coin → three profile rows (momentum displayed; pullback/continuation logged only).
export function toScoreLogItems(bp: Blueprint): ScoreLogItemPayload[] {
  const base = (profile: Profile, score: number | null, withLevels: boolean): ScoreLogItemPayload => ({
    coin: bp.coin,
    direction: bp.direction,
    profile,
    score,
    passed_threshold: score != null && score >= WATCH_THRESHOLD ? 1 : 0,
    ema7_slope_pct: bp.ema7SlopePct,
    volume_ratio: bp.volumeRatio,
    price: bp.price,
    entry: withLevels ? bp.mathematicalTriggerPoint.value : null,
    sl: withLevels ? bp.calculatedRiskLevel.value : null,
    tp: withLevels ? bp.calculatedTargetLevel.value : null,
    trailing_pct: withLevels ? bp.dynamicRiskLevel.pct ?? null : null,
  });
  return [
    base("momentum", bp.profileScores.momentum, true),
    base("pullback", bp.profileScores.pullback, false),
    base("continuation", bp.profileScores.continuation, false),
  ];
}

export interface RecordScanResult {
  scan_event_id: number;
  score_logs: { coin: string; id: number }[];
  first_scan_of_day: boolean;
  xp_awarded: number;
}

// The scan may be rejected by the server-side daily cap (Bug 3). We surface that so
// the client can show a friendly limit state instead of the results.
export interface RecordScanOutcome {
  result: RecordScanResult | null;
  dailyLimit: { scans_per_day: number } | null;
  // FX4: a coin outside the plan's allowlist was submitted (server-authoritative). The UI
  // normally prevents this (locked coins route to /subscribe); this covers the edge case.
  coinGated: { blocked: string[]; plan: string } | null;
}

export async function recordScan(
  coinsScanned: number,
  coinsPassed: number,
  threshold: number | null,
  coins: ScoreLogItemPayload[],
): Promise<RecordScanOutcome> {
  const res = await apiFetch<RecordScanResult>("/api/scan/events", {
    method: "POST",
    body: JSON.stringify({
      coins_scanned: coinsScanned,
      coins_passed: coinsPassed,
      threshold,
      coins,
    }),
  });
  if (res.ok) return { result: res.data, dailyLimit: null, coinGated: null };
  const err = res.error as
    | { code?: string; scans_per_day?: number; blocked?: string[]; plan?: string }
    | null;
  if (res.status === 429 && err?.code === "DAILY_SCAN_LIMIT") {
    return { result: null, dailyLimit: { scans_per_day: err.scans_per_day ?? 1 }, coinGated: null };
  }
  if (res.status === 403 && err?.code === "COIN_GATED") {
    return {
      result: null,
      dailyLimit: null,
      coinGated: { blocked: err.blocked ?? [], plan: err.plan ?? "" },
    };
  }
  return { result: null, dailyLimit: null, coinGated: null };
}

export async function recordSnapshot(scoreLogId: number, cardJson: string): Promise<void> {
  await apiFetch("/api/scan/snapshot", {
    method: "POST",
    body: JSON.stringify({ score_log_id: scoreLogId, card_json: cardJson }),
  });
}
