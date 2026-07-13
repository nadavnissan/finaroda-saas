"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
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

function DetailRowView({ r }: { r: DetailRow }) {
  const dirLabel = r.direction === "short" ? "↓ SHORT" : r.direction === "long" ? "↑ LONG" : r.direction.toUpperCase();
  const dirColor = r.direction === "short" ? C.red : C.green;
  const passColor = r.passed_threshold ? C.green : C.muted;
  const hasLevels = r.entry !== null || r.sl !== null || r.tp !== null;

  return (
    <div style={{ background: C.bg, border: `1px solid ${r.passed_threshold ? "rgba(31,178,134,.3)" : "rgba(233,238,243,.08)"}`, borderRadius: 8, padding: "10px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ font: `600 12px ${MONO}`, color: C.fg }}>
          {r.coin} <span style={{ color: dirColor }}>{dirLabel}</span>
        </span>
        <span style={{ font: `600 9px ${MONO}`, color: passColor }}>
          {r.passed_threshold ? "PASS" : "skip"} · {r.score}
        </span>
      </div>
      {hasLevels && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6 }}>
          <Level label="ENTRY" value={r.entry} color={C.fg} />
          <Level label="SL" value={r.sl} color={C.red} />
          <Level label="TP" value={r.tp} color={C.green} />
        </div>
      )}
      {r.trailing_pct !== null && (
        <span style={{ font: `400 9px ${MONO}`, color: C.muted }}>TRAIL {r.trailing_pct}%</span>
      )}
    </div>
  );
}

function Level({ label, value, color }: { label: string; value: number | null; color: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <span style={{ font: `600 7px ${MONO}`, letterSpacing: 1, color: C.muted }}>{label}</span>
      <span style={{ font: `600 11px ${MONO}`, color }}>{fmtNum(value)}</span>
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

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 480, display: "flex", flexDirection: "column" }}>
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
                    {!detailLoading && detail?.rows.map((r, i) => <DetailRowView key={`${r.coin}-${i}`} r={r} />)}
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
