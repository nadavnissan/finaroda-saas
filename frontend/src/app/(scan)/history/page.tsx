"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { BlueprintChart } from "@/components/scan/BlueprintChart";
import { ConceptTooltip } from "@/components/onboarding/ConceptTooltip";
import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import { toChartCandles } from "@/lib/scan/chart";
import { fetchMarketData } from "@/lib/scan/bybit";
import type { ChartLayers } from "@/lib/scan/entitlements";
import type { MarketData } from "@/lib/scan/types";
import { useMe } from "@/lib/app/session";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

// Read-only scan log (Decision B). Lists the user's past scans and lets them tap into
// a stored result view. Never re-runs a scan and never shows reveal/outcome data.
// Outcomes stay reveal-gated on the dashboard. This is a log, not advice.

interface HistoryItem {
  scan_event_id: number;
  scanned_at: string;
  coins_scanned: number;
  coins_passed: number;
}

interface DetailRow {
  coin: string;
  direction: string;
  score: number;
  passed_threshold: boolean;
  price: number | null;
  entry: number | null;
  sl: number | null;
  tp: number | null;
  trailing_pct: number | null;
}

interface HistoryDetail {
  scan_event_id: number;
  scanned_at: string;
  coins_scanned: number;
  coins_passed: number;
  rows: DetailRow[];
}

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
function prettyTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()} · ${hh}:${mm}`;
}

function fmtNum(n: number | null): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "--";
  const abs = Math.abs(n);
  const decimals = abs >= 100 ? 2 : abs >= 1 ? 3 : 5;
  return n.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

// Formula-transparency notes (PRD §3.5.2) — mirror the live Trading Blueprint card.
const TRIGGER_NOTE = "Calculated from live price relative to EMA structure.";
const RISK_NOTE = "Calculated via ATR14 on your selected chart.";
const DYNAMIC_NOTE = "Calculated from ATR-based trailing geometry.";
const TARGET_NOTE = "Calculated as an R-multiple of the risk distance.";

function riskReward(entry: number | null, sl: number | null, tp: number | null): number | null {
  if (entry === null || sl === null || tp === null) return null;
  const risk = Math.abs(entry - sl);
  const reward = Math.abs(tp - entry);
  if (risk <= 0) return null;
  return Math.round((reward / risk) * 10) / 10;
}

// One calculated level in the stored Trading Blueprint. Uses the approved canonical
// terminology (PRD §3.5.1) via Concept Tooltips — NEVER the words SL / TP / ENTRY.
function LevelCard({ tooltip, label, value, accent, note, suffix }: { tooltip: string; label: string; value: number | null; accent: string; note: string; suffix?: string }) {
  return (
    <div style={{ background: C.panel, border: `1px solid ${accent}`, borderRadius: 8, padding: "9px 11px", display: "flex", flexDirection: "column", gap: 2 }}>
      <div style={{ font: `600 7.5px ${MONO}`, letterSpacing: 0.8, color: C.muted }}>
        <ConceptTooltip id={tooltip} label={label} />
      </div>
      <div style={{ font: `600 15px ${MONO}`, color: accent === C.border ? C.fg : accent }}>
        {value === null ? "--" : `${fmtNum(value)}${suffix ?? ""}`}
      </div>
      <div style={{ font: `400 8.5px ${SANS}`, color: C.muted, lineHeight: 1.4 }}>{note}</div>
    </div>
  );
}

// Stored-scan detail (F3b). Same presentation as the live scan result card: chart +
// Trading Blueprint using the canonical calculator terminology. These are SETUP-time
// levels that were already shown at scan time — NOT withheld outcomes — so redisplay
// is reveal-gating-safe (outcomes stay on the F3 dashboard). The chart re-pulls the
// current market (historical candles are not stored) and draws the levels as logged.
function ScanDetailCard({ r, layers, onSeePlans }: { r: DetailRow; layers: ChartLayers; onSeePlans: () => void }) {
  const [md, setMd] = useState<MarketData | null>(null);
  const [chartFailed, setChartFailed] = useState(false);
  useEffect(() => {
    let alive = true;
    fetchMarketData(r.coin)
      .then((data) => { if (alive) setMd(data); })
      .catch(() => { if (alive) setChartFailed(true); });
    return () => { alive = false; };
  }, [r.coin]);

  const dirLabel = r.direction === "short" ? "↓ SHORT" : r.direction === "long" ? "↑ LONG" : r.direction.toUpperCase();
  const dirColor = r.direction === "short" ? C.red : C.green;
  const gate = r.passed_threshold ? C.green : C.amber;
  const rr = riskReward(r.entry, r.sl, r.tp);
  const bpLevels = { trigger: r.entry, risk: r.sl, target: r.tp };

  return (
    <div style={{ background: C.bg, border: `1px solid ${r.passed_threshold ? "rgba(31,178,134,.3)" : "rgba(233,238,243,.08)"}`, borderRadius: 10, padding: "10px 12px 12px", display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ font: `600 13px ${MONO}`, color: C.fg }}>
          {r.coin} <span style={{ color: dirColor }}>{dirLabel}</span>
        </span>
        <span style={{ font: `600 9.5px ${MONO}`, color: gate }}>
          {r.passed_threshold ? "TIMING VERIFIED" : "WATCH"} · {r.score}/100
        </span>
      </div>

      {/* Chart Standard v1 — same component/gating as the live scan card. */}
      {md ? (
        <BlueprintChart candles={toChartCandles(md)} symbol={r.coin} layers={layers} blueprint={bpLevels} onSeePlans={onSeePlans} />
      ) : (
        <div style={{ margin: "2px 4px", font: `400 9px ${MONO}`, color: C.muted, textAlign: "center", padding: "10px 0" }}>
          {chartFailed ? "Chart unavailable right now." : "Loading chart…"}
        </div>
      )}

      {/* Trading Blueprint — canonical calculator terminology (never SL / TP / ENTRY). */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <LevelCard tooltip="trigger_point" label="MATHEMATICAL TRIGGER POINT" value={r.entry} accent={C.border} note={TRIGGER_NOTE} />
        <LevelCard tooltip="risk_level" label="CALCULATED RISK LEVEL" value={r.sl} accent={C.red} note={RISK_NOTE} />
        <LevelCard tooltip="dynamic_risk" label="DYNAMIC RISK LEVEL" value={r.trailing_pct} accent={C.border} note={DYNAMIC_NOTE} suffix="%" />
        <LevelCard tooltip="target_level" label="CALCULATED TARGET LEVEL" value={r.tp} accent={C.green} note={TARGET_NOTE} />
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", font: `500 10px ${MONO}` }}>
        <span style={{ color: C.muted }}>
          <ConceptTooltip id="risk_reward" label="RISK:REWARD" />{" "}
          <span style={{ color: C.fg, fontWeight: 600 }}>{rr != null ? `1:${rr}` : "-"}</span>
        </span>
        <span style={{ color: C.muted }}>chart is live; levels as recorded</span>
      </div>
    </div>
  );
}

export default function HistoryPage() {
  const router = useRouter();
  const { me, loading } = useMe();
  const [xp, setXp] = useState(0);
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const [detail, setDetail] = useState<HistoryDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(async () => {
    const r = await apiFetch<{ scans: HistoryItem[] }>("/api/scan/history");
    setItems(r.ok && r.data ? r.data.scans : []);
    const xr = await apiFetch<{ total: number }>("/api/onboarding/xp");
    if (xr.ok && xr.data) setXp(xr.data.total);
  }, []);

  useEffect(() => {
    if (!me) return;
    void load();
  }, [me, load]);

  const openScan = useCallback(async (id: number) => {
    if (openId === id) {
      setOpenId(null);
      setDetail(null);
      return;
    }
    setOpenId(id);
    setDetail(null);
    setDetailLoading(true);
    const r = await apiFetch<HistoryDetail>(`/api/scan/history/${id}`);
    setDetail(r.ok && r.data ? r.data : null);
    setDetailLoading(false);
  }, [openId]);

  if (loading || !me) {
    return <main style={{ minHeight: "100vh", background: C.bg }} />;
  }

  const hasAny = (items?.length ?? 0) > 0;
  // Chart layers mirror the live scan card's plan gating (Free = EMA200 only).
  const chartLayers: ChartLayers = me.tier === "free" ? "ema200_only" : "full";

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 480, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <AppHeader xp={xp} left="close" onLeft={() => router.push("/scan")} freeBadge={me.tier === "free"} />

        <div style={{ padding: "8px 20px 0" }}>
          <div style={{ font: `700 20px/1.3 ${SANS}`, color: C.fg }}>RECENT SCANS</div>
          <div style={{ font: `400 10.5px ${MONO}`, color: C.muted, marginTop: 3 }}>
            Read only. This is your scan log, not advice.
          </div>
        </div>

        <div style={{ margin: "16px 16px 0", display: "flex", flexDirection: "column", gap: 8 }}>
          {items === null && (
            <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 10, padding: "18px 14px", textAlign: "center", font: `400 11px ${MONO}`, color: C.muted }}>
              Loading…
            </div>
          )}

          {items !== null && !hasAny && (
            <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 10, padding: "24px 16px", textAlign: "center", display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
              <span style={{ font: `400 12px ${MONO}`, color: C.muted }}>No scans yet. Run your first scan.</span>
              <button
                type="button"
                onClick={() => router.push("/scan")}
                style={{ font: `600 11px ${MONO}`, color: C.bg, background: C.green, border: "none", borderRadius: 8, padding: "9px 18px", cursor: "pointer" }}
              >
                RUN A SCAN
              </button>
            </div>
          )}

          {items?.map((it) => {
            const passLabel = it.coins_passed === 1 ? "1 pass" : `${it.coins_passed} passes`;
            const coinLabel = it.coins_scanned === 1 ? "1 coin" : `${it.coins_scanned} coins`;
            const isOpen = openId === it.scan_event_id;
            return (
              <div key={it.scan_event_id} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <button
                  type="button"
                  onClick={() => void openScan(it.scan_event_id)}
                  style={{
                    background: C.panel,
                    border: `1px solid ${isOpen ? "rgba(31,178,134,.35)" : "rgba(233,238,243,.08)"}`,
                    borderRadius: 10,
                    padding: "12px 14px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    cursor: "pointer",
                    textAlign: "left",
                    width: "100%",
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    <span style={{ font: `600 11px ${MONO}`, color: C.fg }}>{prettyTimestamp(it.scanned_at)}</span>
                    <span style={{ font: `400 9px ${MONO}`, color: C.muted }}>{coinLabel} · {passLabel}</span>
                  </div>
                  <span style={{ font: `600 12px ${MONO}`, color: isOpen ? C.green : C.muted }}>{isOpen ? "▾" : "▸"}</span>
                </button>

                {isOpen && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: "0 4px 4px" }}>
                    {detailLoading && (
                      <div style={{ font: `400 10px ${MONO}`, color: C.muted, textAlign: "center", padding: "8px 0" }}>Loading…</div>
                    )}
                    {!detailLoading && detail === null && (
                      <div style={{ font: `400 10px ${MONO}`, color: C.red, textAlign: "center", padding: "8px 0" }}>Could not load this scan.</div>
                    )}
                    {!detailLoading && detail?.rows.length === 0 && (
                      <div style={{ font: `400 10px ${MONO}`, color: C.muted, textAlign: "center", padding: "8px 0" }}>No coins recorded for this scan.</div>
                    )}
                    {!detailLoading && detail?.rows.map((r, i) => (
                      <ScanDetailCard key={`${r.coin}-${i}`} r={r} layers={chartLayers} onSeePlans={() => router.push("/subscribe")} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div style={{ padding: "16px 20px 0", font: `400 9.5px/1.5 ${MONO}`, color: C.muted, textAlign: "center" }}>
          Read only. This is your scan log, not advice.
        </div>

        <div style={{ marginTop: "auto" }}>
          <Disclaimer />
        </div>
      </div>
    </main>
  );
}
