"use client";

import { useEffect, useState } from "react";

import { LevelMeter } from "@/components/onboarding/LevelMeter";
import { NotificationBell } from "@/components/app/NotificationBell";
import { C } from "@/lib/onboarding/types";
import { apiFetch } from "@/lib/api";
import { getBreadcrumbs } from "@/lib/breadcrumbs";
import { APP_VERSION } from "@/lib/version";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

// E5 hamburger nav (B3). Four destinations + a "Report a problem" item at the foot
// that files a support ticket (→ B7 queue). Opens over a dimmed scan screen.
const ITEMS: { label: string; icon: string; path: string }[] = [
  { label: "Dashboard", icon: "◫", path: "/dashboard" },
  { label: "Recent scans", icon: "≣", path: "/history" },
  { label: "Profile", icon: "◈", path: "/profile" },
  { label: "Academy", icon: "▤", path: "/academy" },
  { label: "Settings", icon: "⚙", path: "/settings" },
];

function ReportProblem({ onDone }: { onDone: () => void }) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function submit() {
    if (!subject.trim() || !body.trim()) return;
    setState("sending");
    const res = await apiFetch("/api/support/tickets", {
      method: "POST",
      // app_version + breadcrumbs are captured so admin can debug blind (server also
      // attaches the reporter's id/email/plan + last 20 logged events on the ticket view).
      // Breadcrumbs are re-sanitized server-side: never any journal outcome value.
      body: JSON.stringify({ subject: subject.trim(), body: body.trim(), category: "bug", app_version: APP_VERSION, breadcrumbs: getBreadcrumbs() }),
    });
    setState(res.ok ? "sent" : "error");
  }

  if (state === "sent") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ font: `600 11px ${MONO}`, color: C.green }}>Thanks - your report was filed.</div>
        <button type="button" onClick={onDone} style={btn(C.muted)}>
          Close
        </button>
      </div>
    );
  }

  const field: React.CSSProperties = {
    background: C.bg,
    border: `1px solid ${C.border}`,
    borderRadius: 8,
    padding: "9px 11px",
    font: `400 12px ${SANS}`,
    color: C.fg,
    width: "100%",
    boxSizing: "border-box",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <input placeholder="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} style={field} />
      <textarea placeholder="What went wrong?" value={body} onChange={(e) => setBody(e.target.value)} rows={3} style={{ ...field, resize: "vertical" }} />
      {state === "error" && <div style={{ font: `400 10px ${MONO}`, color: C.red }}>Could not file the report - please try again.</div>}
      <div style={{ display: "flex", gap: 8 }}>
        <button type="button" onClick={submit} disabled={state === "sending"} style={btn(C.green, true)}>
          {state === "sending" ? "Sending…" : "Send report"}
        </button>
        <button type="button" onClick={onDone} style={btn(C.muted)}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function btn(color: string, filled = false): React.CSSProperties {
  return {
    font: `600 10px ${MONO}`,
    color: filled ? C.bg : color,
    background: filled ? color : "none",
    border: filled ? "none" : `1px solid ${C.border}`,
    borderRadius: 8,
    padding: "8px 12px",
    cursor: "pointer",
  };
}

export function NavDrawer({
  xp,
  tier,
  onClose,
  onNavigate,
}: {
  xp: number;
  tier: string;
  onClose: () => void;
  onNavigate: (path: string) => void;
}) {
  const [reporting, setReporting] = useState(false);
  // Reveal badge = count of unrevealed resolved outcomes (content-free, never push).
  const [unrevealed, setUnrevealed] = useState(0);
  useEffect(() => {
    void apiFetch<{ unrevealed: number }>("/api/journal/badge").then((r) => {
      if (r.ok && r.data) setUnrevealed(r.data.unrevealed);
    });
  }, []);
  const isTrial = tier !== "free"; // simplified plan pill for phase 1

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 60, display: "flex" }}>
      {/* dimmed backdrop over the scan screen */}
      <button type="button" aria-label="Close menu" onClick={onClose} style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,.55)", border: "none", cursor: "pointer" }} />

      <div style={{ position: "relative", width: 296, maxWidth: "86vw", height: "100%", background: C.panel, borderRight: `1px solid rgba(233,238,243,.1)`, boxShadow: "18px 0 44px rgba(0,0,0,.55)", display: "flex", flexDirection: "column" }}>
        {/* identity block - LevelMeter (hex rank + XP progress) */}
        <div style={{ padding: "22px 22px 18px", borderBottom: `1px solid rgba(233,238,243,.08)`, display: "flex", flexDirection: "column", gap: 12 }}>
          <LevelMeter xp={xp} />
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(31,178,134,.08)", border: `1px solid rgba(31,178,134,.35)`, borderRadius: 8, padding: "7px 11px", font: `600 9px ${MONO}` }}>
            <span style={{ color: C.green }}>{tier.toUpperCase()}{isTrial ? " PLAN" : " PLAN"}</span>
            <span style={{ color: C.muted }}>{isTrial ? "" : "1 SCAN / DAY"}</span>
          </div>
          {/* Notification bell + panel (server-authoritative badge) */}
          <NotificationBell onNavigate={onNavigate} />
        </div>

        {/* destinations */}
        <div style={{ display: "flex", flexDirection: "column", padding: "10px 0" }}>
          {ITEMS.map((it, i) => (
            <button
              key={it.label}
              type="button"
              onClick={() => onNavigate(it.path)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "15px 22px",
                background: i === 0 ? "rgba(31,178,134,.07)" : "none",
                borderLeft: i === 0 ? `2px solid ${C.green}` : "2px solid transparent",
                border: "none",
                borderLeftWidth: 2,
                borderLeftStyle: "solid",
                borderLeftColor: i === 0 ? C.green : "transparent",
                font: `${i === 0 ? 600 : 500} 13px ${SANS}`,
                color: C.fg,
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              <span style={{ font: `400 13px ${MONO}`, color: i === 0 ? C.green : C.muted }}>{it.icon}</span>
              {it.label}
              {it.path === "/dashboard" && unrevealed > 0 && (
                <span style={{ marginLeft: "auto", font: `600 8px ${MONO}`, color: C.bg, background: C.green, borderRadius: 8, padding: "2px 7px" }}>{unrevealed} UPDATE</span>
              )}
            </button>
          ))}
        </div>

        {/* report a problem (files a ticket) */}
        <div style={{ marginTop: "auto", borderTop: `1px solid rgba(233,238,243,.08)`, padding: reporting ? "14px 22px" : "6px 0" }}>
          {reporting ? (
            <ReportProblem onDone={() => setReporting(false)} />
          ) : (
            <button type="button" onClick={() => setReporting(true)} style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 22px", width: "100%", background: "none", border: "none", font: `500 12px ${SANS}`, color: C.muted, cursor: "pointer", textAlign: "left" }}>
              <span style={{ font: `400 12px ${MONO}` }}>⚑</span>Report a problem
            </button>
          )}
        </div>
        <div style={{ padding: "0 22px 16px", font: `400 9px ${MONO}`, color: C.muted }}>Analysis, not financial advice.</div>
      </div>
    </div>
  );
}
