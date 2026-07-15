"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { api, apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import { levelFor, RANKS, two } from "@/lib/onboarding/xp";
import { useMe } from "@/lib/app/session";
import type { ProfileResponse } from "@/lib/app/types";
import { inviteSummaryLine, type ReferralSummary } from "@/lib/app/promotions";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";
const HEX = "polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)";

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
  const [invite, setInvite] = useState<ReferralSummary | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!me) return;
    void apiFetch<ProfileResponse>("/api/profile").then((r) => {
      if (r.ok && r.data) setP(r.data);
    });
    void apiFetch<ReferralSummary>("/api/referral").then((r) => {
      if (r.ok && r.data) setInvite(r.data);
    });
  }, [me]);

  async function copyLink() {
    if (!invite) return;
    try {
      await navigator.clipboard.writeText(invite.share_link);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard blocked — the link is shown in full for manual copy.
    }
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
      <div style={{ width: "100%", maxWidth: 480, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
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

        {/* Invite a friend (referral). A friend's first paid charge earns you one free month. */}
        {invite && (
          <Card>
            <span style={{ font: `600 8.5px ${MONO}`, letterSpacing: 1, color: C.muted }}>INVITE A FRIEND · ONE FREE MONTH PER PAID SIGNUP</span>
            <div style={{ font: `400 10px/1.6 ${MONO}`, color: C.muted }}>
              Share your link. When a friend you invite makes their first paid charge, you get one free month. If you are not on a paid plan yet, we bank it for you.
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input readOnly value={invite.share_link} onFocus={(e) => e.currentTarget.select()} style={{ flex: 1, minWidth: 0, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, padding: "8px 10px", font: `400 10px ${MONO}`, color: C.fg }} />
              <button type="button" onClick={copyLink} style={{ flex: "none", background: copied ? "rgba(31,178,134,.12)" : C.green, color: copied ? C.green : C.bg, border: copied ? `1px solid ${C.green}` : "none", borderRadius: 6, padding: "8px 12px", font: `600 9px ${MONO}`, letterSpacing: 1, cursor: "pointer" }}>{copied ? "COPIED" : "COPY"}</button>
            </div>
            <div style={{ font: `400 9px ${MONO}`, color: C.muted }}>{inviteSummaryLine(invite)}</div>
          </Card>
        )}

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
