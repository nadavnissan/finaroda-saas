// Client-side Bybit market fetch (SPEC §6.2). Fresh pull from the user's browser,
// user IP, NO shared cache. Direct fetch first; thin backend proxy only as a CORS
// fallback (no data merge). Shapes into the MarketData contract + scorer inputs.

import type { MarketContext } from "@finaroda/scoring-engine/scorer.js";

import type { MarketData, OHLCV } from "./types";

const BYBIT_BASE = "https://api.bybit.com/v5/market";
const PROXY_BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/market/proxy`;

// Default scan universe (liquid linear perpetuals). Per-plan slicing happens upstream.
export const SCAN_UNIVERSE = [
  "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
  "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "DOTUSDT",
];

type BybitResp = { result?: { list?: unknown[] } };

async function fetchJson(endpoint: string, params: Record<string, string>): Promise<BybitResp> {
  const qs = new URLSearchParams(params).toString();
  try {
    const res = await fetch(`${BYBIT_BASE}/${endpoint}?${qs}`, { cache: "no-store" });
    if (res.ok) return (await res.json()) as BybitResp;
  } catch {
    // fall through to proxy
  }
  const res = await fetch(`${PROXY_BASE}/${endpoint}?${qs}`, { cache: "no-store", credentials: "include" });
  if (!res.ok) throw new Error(`market fetch failed: ${endpoint}`);
  return (await res.json()) as BybitResp;
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
    t: rows.map((r) => parseInt(r[0], 10)), // candle start ms (for the chart)
  };
}

// Weekly is derived from daily by sampling every 7th candle (HTF bias input).
function toWeekly(d: OHLCV): OHLCV {
  const keep = <T>(a: T[]) => a.filter((_, i) => i % 7 === 0);
  return { o: keep(d.o), h: keep(d.h), l: keep(d.l), c: keep(d.c), v: keep(d.v) };
}

export async function fetchMarketData(symbol: string): Promise<MarketData> {
  const [dailyRaw, hourlyRaw, ticker, oiRaw] = await Promise.all([
    fetchJson("kline", { category: "linear", symbol, interval: "D", limit: "220" }),
    fetchJson("kline", { category: "linear", symbol, interval: "60", limit: "220" }),
    fetchJson("tickers", { category: "linear", symbol }),
    fetchJson("open-interest", { category: "linear", symbol, intervalTime: "1d", limit: "2" }).catch(
      () => ({ result: { list: [] } }) as BybitResp,
    ),
  ]);

  const daily = shapeKline((dailyRaw.result?.list ?? []) as string[][]);
  const hourly = shapeKline((hourlyRaw.result?.list ?? []) as string[][]);

  const t = (ticker.result?.list?.[0] ?? {}) as {
    lastPrice?: string;
    fundingRate?: string;
    price24hPcnt?: string;
  };
  const price = t.lastPrice ? parseFloat(t.lastPrice) : daily.c[daily.c.length - 1] ?? 0;
  const funding = t.fundingRate ? parseFloat(t.fundingRate) : 0;
  const change24h = t.price24hPcnt ? parseFloat(t.price24hPcnt) * 100 : 0;

  // Open interest (weak background for the scorer). Best-effort; default neutral.
  const oiList = (oiRaw.result?.list ?? []) as { openInterest?: string }[];
  let oi: number | null = null;
  let oiChangePct = 0;
  if (oiList.length >= 2 && oiList[0].openInterest && oiList[1].openInterest) {
    const now = parseFloat(oiList[0].openInterest);
    const prev = parseFloat(oiList[1].openInterest);
    oi = now;
    oiChangePct = prev > 0 ? ((now - prev) / prev) * 100 : 0;
  }

  return { daily, hourly, weekly: toWeekly(daily), price, funding, oi, oiChangePct, change24h };
}

// Cross-coin context (isolation-Z input). Built once per scan from all coins' 24h change.
export function buildMarketContext(data: Map<string, MarketData>): MarketContext {
  const coinChanges: Record<string, number> = {};
  const changes: number[] = [];
  data.forEach((md, coin) => {
    coinChanges[coin] = md.change24h;
    changes.push(md.change24h);
  });
  const meanChange = changes.length ? changes.reduce((a, b) => a + b, 0) / changes.length : 0;
  const variance = changes.length
    ? changes.reduce((a, b) => a + (b - meanChange) ** 2, 0) / changes.length
    : 0;
  return { coinChanges, meanChange, stdChange: Math.sqrt(variance) };
}
