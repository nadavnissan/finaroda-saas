"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { api, apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import { levelFor, RANKS, two } from "@/lib/onboarding/xp";
import { useMe } from "@/lib/app/session";
import type { ProfileResponse } from "@/lib/app/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";
const HEX = "polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)";

const LENSES = ["ema200", "rsi", "volume", "full"] as const;
const STYLES = ["conservative", "balanced", "aggressive"] as const;

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ margin: "12px 16px 0", background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 12, padding: "13px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
      {children}
    </div>
  );
}

export default function ProfilePage() {
  const router = useRouter();
  const { me, loading } = useMe();
  const [p, setP] = useState<ProfileResponse | null>(null);

  useEffect(() => {
    if (!me) return;
    void apiFetch<ProfileResponse>("/api/profile").then((r) => {
      if (r.ok && r.data) setP(r.data);
    });
  }, [me]);

  async function saveSetting(patch: Record<string, unknown>) {
    const r = await apiFetch<ProfileResponse>("/api/profile/settings", { method: "PUT", body: JSON.stringify(patch) });
    if (r.ok && r.data) setP(r.data);
  }

  async function signOut() {
    await api.logout();
    router.replace("/login");
  }

  if (loading || !me || !p) {
    return <main style={{ minHeight: "100vh", background: C.bg }} />;
  }

  const lvl = levelFor(p.xp_total);

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 440, display: "flex", flexDirection: "column" }}>
        <AppHeader xp={p.xp_total} left="close" onLeft={() => router.push("/scan")} freeBadge={me.tier === "free"} />

        {/* Identity */}
        <div style={{ padding: "14px 20px 0", display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ width: 58, height: 64, flex: "none", background: "rgba(31,178,134,.08)", border: `1.5px solid rgba(31,178,134,.55)`, clipPath: HEX, display: "flex", alignItems: "center", justifyContent: "center", font: `700 17px ${MONO}`, color: C.green }}>{two(lvl.level)}</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <div style={{ font: `700 19px ${MONO}`, color: C.fg }}>{p.call_sign}</div>
            <div style={{ font: `600 9.5px ${MONO}`, letterSpacing: 2, color: C.green }}>{lvl.name.toUpperCase()}</div>
            <div style={{ font: `400 9px ${MONO}`, color: C.muted }}>
              {p.trial ? `PRO TRIAL · DAY ${p.trial.day} OF ${p.trial.total} · NO CARD` : `${p.tier.toUpperCase()} PLAN`}
            </div>
          </div>
        </div>

        {/* Rank ladder (earned on discipline, never on frequency) */}
        <Card>
          <span style={{ font: `600 8.5px ${MONO}`, letterSpacing: 1, color: C.muted }}>RANK LADDER · EARNED ON DISCIPLINE, NEVER ON FREQUENCY</span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {RANKS.map((r) => {
              const active = p.xp_total >= r.floor;
              return (
                <div key={r.level} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4, opacity: active ? 1 : 0.5 }}>
                  <div style={{ width: 34, height: 38, background: active ? "rgba(31,178,134,.12)" : C.bg, border: `${active ? 1.5 : 1}px solid ${active ? C.green : "rgba(233,238,243,.2)"}`, clipPath: HEX, display: "flex", alignItems: "center", justifyContent: "center", font: `700 11px ${MONO}`, color: active ? C.green : C.muted }}>{two(r.level)}</div>
                  <span style={{ font: `500 6.5px ${MONO}`, letterSpacing: 0.5, color: active ? C.green : C.muted, textAlign: "center" }}>
                    {r.name.toUpperCase()}<br />{r.floor > 0 ? `${r.floor.toLocaleString()} XP` : ""}
                  </span>
                </div>
              );
            })}
          </div>
          <div style={{ height: 5, background: C.bg, borderRadius: 3, overflow: "hidden" }}>
            <div style={{ width: `${lvl.progressPct}%`, height: "100%", background: C.green, borderRadius: 3 }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", font: `400 8.5px ${MONO}`, color: C.muted }}>
            <span>XP {p.xp_total.toLocaleString()}</span>
            <span>{lvl.next ? `${lvl.toNext.toLocaleString()} to ${lvl.next.name}` : "Top rank reached"}</span>
          </div>
        </Card>

        {/* How XP is earned (the four decided sources) */}
        <Card>
          <span style={{ font: `600 8.5px ${MONO}`, letterSpacing: 1, color: C.muted }}>HOW XP IS EARNED</span>
          {[["First scan of the day", "+50"], ["Lesson completed", "+100"], ["Journal outcome viewed", "+25"], ["Onboarding completed", "+300"]].map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", font: `400 11px ${MONO}`, color: C.fg }}>
              <span>{k}</span><span style={{ color: C.green }}>{v}</span>
            </div>
          ))}
          <div style={{ font: `400 9px/1.5 ${MONO}`, color: C.muted }}>Never from outcomes. Re-scans earn nothing.</div>
        </Card>

        {/* Remembered scan settings (display & geometry only) */}
        <Card>
          <span style={{ font: `600 8.5px ${MONO}`, letterSpacing: 1, color: C.muted }}>REMEMBERED SCAN SETTINGS</span>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", font: `400 11px ${MONO}` }}>
            <span style={{ color: C.fg }}>ANALYSIS LENS</span>
            <select value={p.settings.analysis_lens} onChange={(e) => saveSetting({ analysis_lens: e.target.value })} style={{ background: C.bg, color: C.green, border: `1px solid ${C.border}`, borderRadius: 6, padding: "4px 8px", font: `600 11px ${MONO}` }}>
              {LENSES.map((l) => <option key={l} value={l}>{l.toUpperCase()}</option>)}
            </select>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", font: `400 11px ${MONO}` }}>
            <span style={{ color: C.fg }}>RISK STYLE</span>
            <select value={p.settings.risk_style} onChange={(e) => saveSetting({ risk_style: e.target.value })} style={{ background: C.bg, color: C.green, border: `1px solid ${C.border}`, borderRadius: 6, padding: "4px 8px", font: `600 11px ${MONO}` }}>
              {STYLES.map((s) => <option key={s} value={s}>{s.toUpperCase()}</option>)}
            </select>
          </div>
          <div style={{ font: `400 9px/1.5 ${MONO}`, color: C.muted }}>Display and geometry only, never what counts as an opportunity.</div>
        </Card>

        <div style={{ padding: "16px 16px 0" }}>
          <button type="button" onClick={signOut} style={{ width: "100%", background: "none", border: `1px solid ${C.border}`, borderRadius: 8, padding: "11px", font: `600 11px ${MONO}`, color: C.muted, cursor: "pointer" }}>SIGN OUT</button>
        </div>

        <div style={{ marginTop: "auto" }}>
          <Disclaimer />
        </div>
      </div>
    </main>
  );
}
