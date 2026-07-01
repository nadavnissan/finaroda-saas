// Client-side Bybit market fetch (SPEC §6.2). Fresh pull from the user's browser,
// user IP, NO shared cache. Direct fetch first; thin backend proxy only as a CORS
// fallback (no data merge). Shapes into the MarketData contract.

import type { MarketData, OHLCV } from "./types";

const BYBIT_BASE = "https://api.bybit.com/v5/market";
const PROXY_BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/market/proxy`;

// Default scan universe (liquid linear perpetuals). Per-plan slicing happens upstream.
export const SCAN_UNIVERSE = [
  "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
  "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "DOTUSDT",
];

type BybitList = { result?: { list?: string[][] } };

async function fetchJson(endpoint: string, params: Record<string, string>): Promise<BybitList> {
  const qs = new URLSearchParams(params).toString();
  // 1) direct (client IP, no cache)
  try {
    const res = await fetch(`${BYBIT_BASE}/${endpoint}?${qs}`, { cache: "no-store" });
    if (res.ok) return (await res.json()) as BybitList;
  } catch {
    // fall through to proxy
  }
  // 2) CORS fallback — thin passthrough, no merge
  const res = await fetch(`${PROXY_BASE}/${endpoint}?${qs}`, { cache: "no-store", credentials: "include" });
  if (!res.ok) throw new Error(`market fetch failed: ${endpoint}`);
  return (await res.json()) as BybitList;
}

// Bybit kline rows: [start, open, high, low, close, volume, turnover], newest-first.
function shapeKline(list: string[][]): OHLCV {
  const rows = [...list].reverse(); // → oldest-to-newest (engine contract)
  return {
    o: rows.map((r) => parseFloat(r[1])),
    h: rows.map((r) => parseFloat(r[2])),
    l: rows.map((r) => parseFloat(r[3])),
    c: rows.map((r) => parseFloat(r[4])),
    v: rows.map((r) => parseFloat(r[5])),
  };
}

export async function fetchMarketData(symbol: string): Promise<MarketData> {
  const [dailyRaw, hourlyRaw, ticker] = await Promise.all([
    fetchJson("kline", { category: "linear", symbol, interval: "D", limit: "220" }),
    fetchJson("kline", { category: "linear", symbol, interval: "60", limit: "220" }),
    fetchJson("tickers", { category: "linear", symbol }),
  ]);

  const daily = shapeKline(dailyRaw.result?.list ?? []);
  const hourly = shapeKline(hourlyRaw.result?.list ?? []);
  const t = ticker.result?.list?.[0] as unknown as { lastPrice?: string; fundingRate?: string } | undefined;
  const price = t?.lastPrice ? parseFloat(t.lastPrice) : daily.c[daily.c.length - 1] ?? 0;
  const funding = t?.fundingRate ? parseFloat(t.fundingRate) : 0;

  return { daily, hourly, price, funding };
}
