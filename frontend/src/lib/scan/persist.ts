// Best-effort scan persistence (SPEC §5). If the user isn't signed in, these no-op
// silently (401) — the scan UX still works; it just isn't logged.

import { apiFetch } from "@/lib/api";

import type { Blueprint } from "./types";

export interface ScoreLogItemPayload {
  coin: string;
  direction: "long" | "short";
  score: null;
  passed_threshold: number;
  ema7_slope_pct: number | null;
  volume_ratio: number | null;
  price: number | null;
  entry: number | null;
  sl: number | null;
  tp: number | null;
  trailing_pct: number | null;
}

export function toScoreLogItem(bp: Blueprint): ScoreLogItemPayload {
  return {
    coin: bp.coin,
    direction: bp.direction,
    score: null,
    passed_threshold: bp.interimPassed ? 1 : 0,
    ema7_slope_pct: bp.ema7SlopePct,
    volume_ratio: bp.volumeRatio,
    price: bp.price,
    entry: bp.mathematicalTriggerPoint.value,
    sl: bp.calculatedRiskLevel.value,
    tp: bp.calculatedTargetLevel.value,
    trailing_pct: bp.dynamicRiskLevel.pct ?? null,
  };
}

export async function recordScan(
  coinsScanned: number,
  coinsPassed: number,
  threshold: number | null,
  coins: ScoreLogItemPayload[],
): Promise<{ scan_event_id: number; score_logs: { coin: string; id: number }[] } | null> {
  const res = await apiFetch<{ scan_event_id: number; score_logs: { coin: string; id: number }[] }>(
    "/api/scan/events",
    {
      method: "POST",
      body: JSON.stringify({
        coins_scanned: coinsScanned,
        coins_passed: coinsPassed,
        threshold,
        coins,
      }),
    },
  );
  return res.ok ? res.data : null;
}

export async function recordSnapshot(scoreLogId: number, cardJson: string): Promise<void> {
  await apiFetch("/api/scan/snapshot", {
    method: "POST",
    body: JSON.stringify({ score_log_id: scoreLogId, card_json: cardJson }),
  });
}
