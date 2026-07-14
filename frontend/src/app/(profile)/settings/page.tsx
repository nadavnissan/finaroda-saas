"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { BillingBanner } from "@/components/app/BillingBanner";
import { ChurnSurvey } from "@/components/app/ChurnSurvey";
import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import { useMe } from "@/lib/app/session";
import type { NotificationPrefs, ProfileResponse } from "@/lib/app/types";
import { togglePref } from "@/lib/notifications";

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

function Toggle({ label, on, onClick }: { label: string; on: boolean; onClick: () => void }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", font: `400 11px ${MONO}` }}>
      <span style={{ color: C.fg }}>{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-label={label}
        onClick={onClick}
        style={{ width: 44, height: 24, borderRadius: 12, border: `1px solid ${on ? C.green : C.border}`, background: on ? "rgba(31,178,134,.25)" : C.bg, position: "relative", cursor: "pointer", padding: 0 }}
      >
        <span style={{ position: "absolute", top: 2, left: on ? 22 : 2, width: 18, height: 18, borderRadius: 9, background: on ? C.green : C.muted, transition: "left .12s" }} />
      </button>
    </div>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const { me, loading } = useMe();
  const [p, setP] = useState<ProfileResponse | null>(null);
  const [prefs, setPrefs] = useState<NotificationPrefs | null>(null);

  useEffect(() => {
    if (!me) return;
    void apiFetch<ProfileResponse>("/api/profile").then((r) => {
      if (r.ok && r.data) setP(r.data);
    });
    void apiFetch<NotificationPrefs>("/api/notifications/prefs").then((r) => {
      if (r.ok && r.data) setPrefs(r.data);
    });
  }, [me]);

  async function saveSetting(patch: Record<string, unknown>) {
    const r = await apiFetch<ProfileResponse>("/api/profile/settings", { method: "PUT", body: JSON.stringify(patch) });
    if (r.ok && r.data) setP(r.data);
  }

  async function flipPref(key: keyof NotificationPrefs) {
    if (!prefs) return;
    const next = togglePref(prefs, key);
    setPrefs(next); // optimistic
    const r = await apiFetch<NotificationPrefs>("/api/notifications/prefs", { method: "PUT", body: JSON.stringify({ [key]: next[key] }) });
    if (r.ok && r.data) setPrefs(r.data);
  }

  if (loading || !me || !p) {
    return <main style={{ minHeight: "100vh", background: C.bg }} />;
  }

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 440, display: "flex", flexDirection: "column" }}>
        <AppHeader xp={p.xp_total} left="close" onLeft={() => router.push("/scan")} freeBadge={me.tier === "free"} />

        <BillingBanner />

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

        {/* Notification preferences (cross-device, stored server-side) */}
        <Card>
          <span style={{ font: `600 8.5px ${MONO}`, letterSpacing: 1, color: C.muted }}>NOTIFICATIONS</span>
          {prefs ? (
            <>
              <Toggle label="IN-APP NOTIFICATIONS" on={prefs.inapp_enabled} onClick={() => flipPref("inapp_enabled")} />
              <Toggle label="ARRIVAL SOUND" on={prefs.sound_enabled} onClick={() => flipPref("sound_enabled")} />
              <Toggle label="VIBRATION" on={prefs.vibration_enabled} onClick={() => flipPref("vibration_enabled")} />
              <Toggle label="PRODUCT EMAILS" on={prefs.email_product} onClick={() => flipPref("email_product")} />
              <Toggle label="UPDATE EMAILS" on={prefs.email_broadcast} onClick={() => flipPref("email_broadcast")} />
              <div style={{ font: `400 9px/1.5 ${MONO}`, color: C.muted }}>
                Sound and vibration apply to arrivals while the app is open. Update emails always carry a one-click unsubscribe link.
              </div>
            </>
          ) : (
            <div style={{ font: `400 9px/1.5 ${MONO}`, color: C.muted }}>Loading preferences.</div>
          )}
        </Card>

        {/* Manage plan: cancel at period end (D-B6) + exit survey (D-A5). */}
        <Card>
          <span style={{ font: `600 8.5px ${MONO}`, letterSpacing: 1, color: C.muted }}>MANAGE PLAN</span>
          <ChurnSurvey subscriptionStatus={p.subscription_status} />
        </Card>

        <div style={{ marginTop: "auto" }}>
          <Disclaimer />
        </div>
      </div>
    </main>
  );
}
