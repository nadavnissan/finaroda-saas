// FX4 — per-plan coin allowlist for the scan selector. Fetched from the server
// (/api/scan/coin-access); the server is authoritative (a gated scan is rejected in
// /events with 403 COIN_GATED). The UI shows locked coins with the plan that unlocks
// them and routes a tap to /subscribe (show the door). Trial = Pro. Coin access is
// breadth only, never a score or verdict.

import { apiFetch } from "@/lib/api";

export interface CoinAccess {
  plan: string;
  coins: string[]; // allowed base symbols (ignored when wildcard)
  wildcard: boolean;
  universe: string[]; // all managed base symbols
  locked: Record<string, string>; // base symbol -> plan name that unlocks it
}

// Fallback when the fetch fails: nothing is locked in the UI (never over-restrict the
// selector). The server still enforces, and recordScan handles a COIN_GATED rejection.
export const OPEN_ACCESS: CoinAccess = {
  plan: "pro",
  coins: [],
  wildcard: true,
  universe: [],
  locked: {},
};

export async function fetchCoinAccess(): Promise<CoinAccess> {
  const res = await apiFetch<CoinAccess>("/api/scan/coin-access", { method: "GET" });
  return res.ok && res.data ? res.data : OPEN_ACCESS;
}

export function baseSymbol(coin: string): string {
  const c = coin.toUpperCase();
  return c.endsWith("USDT") ? c.slice(0, -4) : c;
}

export function isCoinLocked(coin: string, access: CoinAccess): boolean {
  if (access.wildcard) return false;
  const b = baseSymbol(coin);
  // Only managed-universe coins are gated; unknown symbols are never locked.
  if (access.universe.length > 0 && !access.universe.includes(b)) return false;
  return !access.coins.includes(b);
}

export function coinLockReason(coin: string, access: CoinAccess): string | null {
  if (!isCoinLocked(coin, access)) return null;
  const plan = access.locked[baseSymbol(coin)];
  return plan ? `Available on ${plan}` : "Available on a higher plan";
}
