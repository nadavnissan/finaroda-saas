// Client view of the server-authoritative scan entitlements (B1 gating).
// The scan runs in the browser, but these are binding: the coin count slices the
// scan universe and the chart-layers flag gates EMA7 / Blueprint layers (E7).
// Falls back to Free on any error (never over-grants).
import { apiFetch } from "@/lib/api";

export type ChartLayers = "ema200_only" | "full";

export interface Entitlements {
  tier: string;
  coins_per_scan: number;
  chart_layers: ChartLayers;
  scans_per_day: number; // 0 = unlimited
}

export const FREE_ENTITLEMENTS: Entitlements = {
  tier: "free",
  coins_per_scan: 2,
  chart_layers: "ema200_only",
  scans_per_day: 1,
};

export async function fetchEntitlements(): Promise<Entitlements> {
  const res = await apiFetch<Entitlements>("/api/scan/entitlements", { method: "GET" });
  return res.ok && res.data ? res.data : FREE_ENTITLEMENTS;
}
