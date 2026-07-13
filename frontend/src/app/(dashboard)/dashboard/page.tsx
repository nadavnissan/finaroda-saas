"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { NavDrawer } from "@/components/scan/NavDrawer";
import { BroadcastBanner } from "@/components/app/BroadcastBanner";
import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import { useMe } from "@/lib/app/session";
import { scenarioOutcome } from "@/lib/app/scenario";
import type { JournalResponse, ScenarioView } from "@/lib/app/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
function prettyDate(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso + "T00:00:00Z");
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

function StatCard({ value, label, color, border }: { value: string; label: string; color: string; border?: string }) {
  return (
    <div style={{ background: C.panel, border: `1px solid ${border ?? "rgba(233,238,243,.08)"}`, borderRadius: 10, padding: "10px 8px", textAlign: "center", display: "flex", flexDirection: "column", gap: 2 }}>
      <span style={{ font: `700 17px ${MONO}`, color }}>{value}</span>
      <span style={{ font: `600 7px ${MONO}`, letterSpacing: 1, color: C.muted, whiteSpace: "pre-line" }}>{label}</span>
    </div>
  );
}

// One journal row. CRITICAL (reveal-gating): an unrevealed scenario has NO outcome
// data in its payload, so this component literally cannot render an outcome for it —
// it draws a blurred placeholder + "scan to reveal". Symmetric framing: a capital SAVE
// row is visually peer to a WIN. R only, never money.
function ScenarioRow({ s }: { s: ScenarioView }) {
  const dirLabel = s.direction === "short" ? "↓ SHORT" : s.direction === "long" ? "↑ LONG" : "";
  const dirColor = s.direction === "short" ? C.red : C.green;

  if (!s.revealed) {
    return (
      <div data-testid="scenario-row" data-revealed="false" style={{ background: C.panel, border: `1px solid rgba(224,145,63,.35)`, borderRadius: 10, padding: "12px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={{ font: `600 12px ${MONO}`, color: C.fg }}>{s.coin} <span style={{ color: dirColor }}>{dirLabel}</span></span>
          <span style={{ font: `400 9px ${MONO}`, color: C.muted }}>{prettyDate(s.scan_date)} · PASS {s.score}</span>
        </div>
        <div style={{ textAlign: "right", display: "flex", flexDirection: "column", gap: 2 }}>
          {/* No outcome value exists in the payload; render a blurred placeholder only. */}
          <span aria-hidden style={{ filter: "blur(5px)", font: `600 13px ${MONO}`, color: C.muted }}>••••</span>
          <span style={{ font: `600 8px ${MONO}`, color: C.amber }}>🔒 SCAN TO REVEAL</span>
        </div>
      </div>
    );
  }

  // Revealed outcome (pure helper — returns null for unrevealed, handled above).
  const outcome = scenarioOutcome(s)!;
  const rightTop = outcome.top;
  const rightBottom = outcome.bottom;
  const rightColor: string = outcome.tone === "red" ? C.red : outcome.tone === "muted" ? C.muted : C.green;
  const borderCol = s.status === "save" ? "rgba(31,178,134,.35)" : "rgba(233,238,243,.08)";

  return (
    <div data-testid="scenario-row" data-revealed="true" style={{ background: C.panel, border: `1px solid ${borderCol}`, borderRadius: 10, padding: "12px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <span style={{ font: `600 12px ${MONO}`, color: C.fg }}>{s.coin} <span style={{ color: dirColor }}>{dirLabel}</span></span>
        <span style={{ font: `400 9px ${MONO}`, color: C.muted }}>{prettyDate(s.scan_date)} · PASS {s.score}</span>
      </div>
      <div style={{ textAlign: "right", display: "flex", flexDirection: "column", gap: 2 }}>
        <span style={{ font: `600 13px ${MONO}`, color: rightColor }}>{rightTop}</span>
        <span style={{ font: `600 8px ${MONO}`, color: C.muted }}>{rightBottom}</span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { me, loading } = useMe();
  const [data, setData] = useState<JournalResponse | null>(null);
  const [xp, setXp] = useState(0);
  const [drawer, setDrawer] = useState(false);

  const load = useCallback(async () => {
    const r = await apiFetch<JournalResponse>("/api/journal");
    if (r.ok && r.data) setData(r.data);
    const xr = await apiFetch<{ total: number }>("/api/onboarding/xp");
    if (xr.ok && xr.data) setXp(xr.data.total);
  }, []);

  useEffect(() => {
    if (!me) return;
    void load();
  }, [me, load]);

  // Viewing a revealed outcome earns +25 XP once per scenario (idempotent server-side).
  useEffect(() => {
    if (!data) return;
    const toView = data.scenarios.filter((s) => s.type === "pass" && s.revealed && !s.viewed);
    if (toView.length === 0) return;
    let bump = 0;
    void (async () => {
      for (const s of toView) {
        const r = await apiFetch<{ xp_awarded: number }>(`/api/journal/scenarios/${s.id}/view`, { method: "POST" });
        if (r.ok && r.data) bump += r.data.xp_awarded;
      }
      if (bump > 0) setXp((x) => x + bump);
    })();
  }, [data]);

  if (loading || !me) {
    return <main style={{ minHeight: "100vh", background: C.bg }} />;
  }

  const stats = data?.stats;
  const scenarios = data?.scenarios ?? [];
  const hasAny = scenarios.length > 0;

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 440, display: "flex", flexDirection: "column" }}>
        <AppHeader xp={xp} left="menu" onLeft={() => setDrawer(true)} freeBadge={me.tier === "free"} />
        <BroadcastBanner />

        <div style={{ padding: "8px 20px 0" }}>
          <div style={{ font: `700 20px/1.3 ${SANS}`, color: C.fg }}>What Would Have Happened</div>
          <div style={{ font: `400 10.5px ${MONO}`, color: C.muted, marginTop: 3 }}>Hypothetical · not advice · never entries-per-day</div>
        </div>

        {/* Headline stats: capital SAVES is co-equal with wins (symmetric framing). */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, padding: "14px 16px 0" }}>
          <StatCard value={`${(stats?.cumulative_r_revealed ?? 0) >= 0 ? "+" : ""}${(stats?.cumulative_r_revealed ?? 0).toFixed(2)}R`} label={"CUMULATIVE R\n(REVEALED)"} color={C.green} border="rgba(31,178,134,.3)" />
          <StatCard value={String(stats?.capital_saves ?? 0)} label={"CAPITAL\nSAVES"} color={C.fg} />
          <StatCard value={String(stats?.awaiting_reveal ?? 0)} label={"AWAITING\nREVEAL"} color={C.amber} />
        </div>

        {/* Discipline meter (real skip data, no fabricated ratio). */}
        <div style={{ margin: "12px 16px 0", background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, padding: "11px 14px", display: "flex", flexDirection: "column", gap: 7 }}>
          <div style={{ display: "flex", justifyContent: "space-between", font: `600 8.5px ${MONO}`, letterSpacing: 1 }}>
            <span style={{ color: C.muted }}>DISCIPLINE · SMART-SKIP</span>
            <span style={{ color: C.green }}>SKIPPED {stats?.skip_days ?? 0} OF LAST {stats?.tracked_days ?? 0} DAYS</span>
          </div>
          <div style={{ height: 6, background: C.bg, borderRadius: 3, overflow: "hidden" }}>
            <div style={{ width: `${stats?.discipline_pct ?? 0}%`, height: "100%", background: C.green, borderRadius: 3 }} />
          </div>
          <div style={{ font: `400 9px ${MONO}`, color: C.muted }}>Skips count toward discipline, the skip is the edge.</div>
        </div>

        {/* Scenario journal. */}
        <div style={{ margin: "12px 16px 0", display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ font: `600 9px ${MONO}`, letterSpacing: 2, color: C.muted }}>SCENARIO JOURNAL</span>
            {(stats?.awaiting_reveal ?? 0) > 0 && (
              <span style={{ font: `600 8px ${MONO}`, color: C.bg, background: C.green, borderRadius: 8, padding: "2px 8px" }}>{stats?.awaiting_reveal} UPDATE</span>
            )}
          </div>
          {!hasAny && (
            <div style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 10, padding: "18px 14px", textAlign: "center", font: `400 11px ${MONO}`, color: C.muted }}>
              Not enough resolved setups yet. Keep scanning.
            </div>
          )}
          {scenarios
            .filter((s) => s.type === "pass")
            .map((s) => <ScenarioRow key={s.id} s={s} />)}
        </div>

        <div style={{ padding: "12px 20px 0", font: `400 9.5px/1.5 ${MONO}`, color: C.muted, textAlign: "center" }}>
          Results reveal on your next scan, never by push.
        </div>
        <div style={{ marginTop: "auto" }}>
          <Disclaimer />
        </div>
      </div>

      {drawer && (
        <NavDrawer
          xp={xp}
          tier={me.tier}
          onClose={() => setDrawer(false)}
          onNavigate={(path) => {
            setDrawer(false);
            router.push(path);
          }}
        />
      )}
    </main>
  );
}
