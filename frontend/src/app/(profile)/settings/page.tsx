"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import { useMe } from "@/lib/app/session";
import type { ProfileResponse } from "@/lib/app/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

const LENSES = ["ema200", "rsi", "volume", "full"] as const;
const STYLES = ["conservative", "balanced", "aggressive"] as const;

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ margin: "12px 16px 0", background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 12, padding: "13px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
      {children}
    </div>
  );
}

export default function SettingsPage() {
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

  if (loading || !me || !p) {
    return <main style={{ minHeight: "100vh", background: C.bg }} />;
  }

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 440, display: "flex", flexDirection: "column" }}>
        <AppHeader xp={p.xp_total} left="close" onLeft={() => router.push("/scan")} freeBadge={me.tier === "free"} />

        {/* Page heading */}
        <div style={{ padding: "14px 20px 0", display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ font: `700 17px ${MONO}`, color: C.fg }}>SETTINGS</div>
          <div style={{ font: `400 9.5px/1.5 ${MONO}`, color: C.muted }}>Remembered scan settings</div>
          <div style={{ font: `400 9px/1.5 ${MONO}`, color: C.muted }}>
            Display and geometry defaults reused on every scan. They never change what counts as an opportunity.
          </div>
        </div>

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

        {/* Notifications placeholder (future toggles) */}
        <Card>
          <span style={{ font: `600 8.5px ${MONO}`, letterSpacing: 1, color: C.muted }}>NOTIFICATIONS</span>
          <div style={{ font: `400 9px/1.5 ${MONO}`, color: C.muted }}>More settings coming soon.</div>
        </Card>

        <div style={{ marginTop: "auto" }}>
          <Disclaimer />
        </div>
      </div>
    </main>
  );
}
