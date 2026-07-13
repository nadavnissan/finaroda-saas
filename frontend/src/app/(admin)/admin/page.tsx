"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import { useMe } from "@/lib/app/session";
import { useIsMobile } from "@/lib/app/useIsMobile";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

type Section = "overview" | "users" | "tickets" | "broadcast" | "settings" | "notifications";
const SECTIONS: Section[] = ["overview", "users", "tickets", "broadcast", "settings", "notifications"];

/* eslint-disable @typescript-eslint/no-explicit-any */

// RESPONSIVE PASS: the admin console is desktop-first (B7 frames use a fixed left
// rail + wide multi-pane sections) but must be USABLE on a phone. On mobile the rail
// becomes a sticky top tab bar, master/detail panes swap instead of sitting side by
// side, wide tables scroll horizontally with a sticky first column, and dense grids
// reflow. No admin data or action changes — layout only.

function Rail({ section, setSection, ticketCount, onExit, mobile }: { section: Section; setSection: (s: Section) => void; ticketCount: number; onExit: () => void; mobile: boolean }) {
  if (mobile) {
    // Sticky top bar + a horizontally scrollable tab strip (never clipped).
    return (
      <div style={{ position: "sticky", top: 0, zIndex: 20, background: C.panel, borderBottom: `1px solid rgba(233,238,243,.08)` }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px 10px" }}>
          <button type="button" onClick={onExit} aria-label="Back to app" style={{ background: "none", border: "none", cursor: "pointer", textAlign: "left", font: `700 12px ${SANS}`, letterSpacing: 3, color: C.fg, padding: 0 }}>
            FINARODA <span style={{ font: `600 8px ${MONO}`, color: C.amber, border: `1px solid rgba(224,145,63,.4)`, borderRadius: 3, padding: "2px 5px", marginLeft: 4 }}>ADMIN</span>
          </button>
          <button type="button" onClick={onExit} style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 10px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, font: `600 9px ${MONO}`, letterSpacing: 1, color: C.muted, cursor: "pointer" }}>
            ← APP
          </button>
        </div>
        <div style={{ display: "flex", gap: 6, overflowX: "auto", padding: "0 12px 10px", WebkitOverflowScrolling: "touch" }}>
          {SECTIONS.map((s) => {
            const active = s === section;
            return (
              <button key={s} type="button" onClick={() => setSection(s)} style={{ flex: "none", display: "flex", alignItems: "center", gap: 5, minHeight: 36, padding: "7px 13px", background: active ? "rgba(31,178,134,.1)" : C.bg, border: `1px solid ${active ? C.green : C.border}`, borderRadius: 16, font: `${active ? 600 : 500} 11px ${SANS}`, color: active ? C.green : C.muted, cursor: "pointer", textTransform: "capitalize", whiteSpace: "nowrap" }}>
                {s}
                {s === "tickets" && ticketCount > 0 && <span style={{ font: `600 8px ${MONO}`, color: C.bg, background: C.amber, borderRadius: 7, padding: "1px 6px" }}>{ticketCount}</span>}
              </button>
            );
          })}
        </div>
      </div>
    );
  }
  return (
    <div style={{ width: 200, flex: "none", background: C.panel, borderRight: `1px solid rgba(233,238,243,.08)`, display: "flex", flexDirection: "column", padding: "18px 0" }}>
      <button type="button" onClick={onExit} aria-label="Back to app" style={{ padding: "0 20px 18px", background: "none", border: "none", cursor: "pointer", textAlign: "left", font: `700 12px ${SANS}`, letterSpacing: 3, color: C.fg }}>
        FINARODA <span style={{ font: `600 8px ${MONO}`, color: C.amber, border: `1px solid rgba(224,145,63,.4)`, borderRadius: 3, padding: "2px 5px", marginLeft: 4 }}>ADMIN</span>
      </button>
      <button type="button" onClick={onExit} style={{ display: "flex", alignItems: "center", gap: 6, margin: "0 20px 12px", padding: "7px 10px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, font: `600 9px ${MONO}`, letterSpacing: 1, color: C.muted, cursor: "pointer", textAlign: "left" }}>
        ← BACK TO APP
      </button>
      {SECTIONS.map((s) => {
        const active = s === section;
        return (
          <button key={s} type="button" onClick={() => setSection(s)} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "11px 20px", background: active ? "rgba(31,178,134,.07)" : "none", borderLeft: `2px solid ${active ? C.green : "transparent"}`, border: "none", borderLeftStyle: "solid", borderLeftWidth: 2, borderLeftColor: active ? C.green : "transparent", font: `${active ? 600 : 500} 11.5px ${SANS}`, color: active ? C.fg : C.muted, cursor: "pointer", textAlign: "left", textTransform: "capitalize" }}>
            {s}
            {s === "tickets" && ticketCount > 0 && <span style={{ font: `600 8px ${MONO}`, color: C.bg, background: C.amber, borderRadius: 7, padding: "1px 6px" }}>{ticketCount}</span>}
          </button>
        );
      })}
      <div style={{ marginTop: "auto", padding: "14px 20px 0", font: `400 8.5px ${MONO}`, color: C.muted }}>Analysis, not financial advice.</div>
    </div>
  );
}

function Stat({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div style={{ background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, padding: 14, display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ font: `600 8px ${MONO}`, letterSpacing: 1, color: C.muted }}>{label}</span>
      <span style={{ font: `700 22px ${MONO}`, color: color ?? C.fg }}>{value}</span>
      {sub && <span style={{ font: `400 8.5px ${MONO}`, color: C.muted }}>{sub}</span>}
    </div>
  );
}

function Overview() {
  const [d, setD] = useState<any>(null);
  useEffect(() => { void apiFetch<any>("/api/admin/overview").then((r) => r.ok && setD(r.data)); }, []);
  if (!d) return <Loading />;
  return (
    <div style={{ flex: 1, minWidth: 0, padding: "20px clamp(16px,4vw,24px)", display: "flex", flexDirection: "column", gap: 12 }}>
      <H title="Overview" note="first-100 vitals, live data" />
      {/* auto-fit: 5 across on desktop, reflows to 2 on a phone, never clipped. */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px,1fr))", gap: 10 }}>
        <Stat label="USERS" value={String(d.users.total)} sub={`+${d.users.new_this_week} this week`} color={C.green} />
        <Stat label="TRIALS ACTIVE" value={String(d.trials.active)} sub={`${d.trials.expiring_3d} end within 3 days`} color={C.green} />
        <Stat label="TRIALS EXPIRED" value={String(d.trials.expired)} />
        <Stat label="MRR" value={`₪${d.mrr_ils}`} sub={`${d.mrr_breakdown.basic} basic · ${d.mrr_breakdown.pro} pro`} color={C.green} />
        <Stat label="SCANS / DAY" value={String(d.scans.avg_7d)} sub={`today ${d.scans.today}`} />
      </div>
      <div style={{ background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, padding: 16 }}>
        <span style={{ font: `600 8px ${MONO}`, letterSpacing: 1, color: C.muted }}>CHURN · LEAVE REASONS (EXIT PROMPT)</span>
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
          {d.churn.length === 0 && <span style={{ font: `400 10px ${MONO}`, color: C.muted }}>No churn recorded yet.</span>}
          {d.churn.map((c: any) => (
            <div key={c.reason} style={{ display: "flex", justifyContent: "space-between", font: `400 10.5px ${MONO}`, color: C.fg }}>
              <span>{c.reason}</span><span style={{ color: C.muted }}>{c.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Users() {
  const mobile = useIsMobile();
  const [rows, setRows] = useState<any[]>([]);
  const [sel, setSel] = useState<any | null>(null);
  const [q, setQ] = useState("");
  const [note, setNote] = useState("");
  const load = useCallback(async () => {
    const r = await apiFetch<any>(`/api/admin/users${q ? `?search=${encodeURIComponent(q)}` : ""}`);
    if (r.ok && r.data) setRows(r.data.users);
  }, [q]);
  useEffect(() => { void load(); }, [load]);

  async function override(action: string, value?: string) {
    if (!sel) return;
    if (!note.trim()) { alert("An audit note is required for every override."); return; }
    await apiFetch(`/api/admin/users/${sel.id}/override`, { method: "POST", body: JSON.stringify({ action, value, note: note.trim() }) });
    setNote("");
    await load();
  }

  const detail = sel && (
    <div style={mobile
      ? { background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, padding: "16px 16px", display: "flex", flexDirection: "column", gap: 12 }
      : { width: 280, flex: "none", background: C.panel, borderLeft: `1px solid rgba(233,238,243,.08)`, padding: "20px 18px", display: "flex", flexDirection: "column", gap: 12 }}>
      {mobile && (
        <button type="button" onClick={() => setSel(null)} style={{ alignSelf: "flex-start", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, padding: "6px 10px", font: `600 9px ${MONO}`, color: C.muted, cursor: "pointer" }}>← BACK TO LIST</button>
      )}
      <div style={{ font: `600 12px ${MONO}`, color: C.fg }}>{sel.call_sign ?? sel.email}</div>
      <div style={{ font: `600 8px ${MONO}`, letterSpacing: 1, color: C.amber }}>ADMIN-ONLY OVERRIDES</div>
      <input placeholder="audit note (required)" value={note} onChange={(e) => setNote(e.target.value)} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, padding: "7px 9px", font: `400 9px ${MONO}`, color: C.fg, width: "100%", boxSizing: "border-box" }} />
      <OverrideRow label="Plan → Pro" onClick={() => override("plan_override", "pro")} />
      <OverrideRow label="Plan → Free" onClick={() => override("plan_override", "free")} />
      <OverrideRow label="Extend trial +7 days" onClick={() => override("extend_trial", "7")} />
      <OverrideRow label="Grant +250 XP (support)" onClick={() => override("grant_xp", "250")} />
      <OverrideRow label={sel.suspended ? "Unsuspend account" : "Suspend account"} danger onClick={() => override(sel.suspended ? "unsuspend" : "suspend")} />
      <div style={{ font: `400 8.5px/1.5 ${MONO}`, color: C.muted }}>Every override is logged with admin id and reason (audit trail).</div>
    </div>
  );

  // On mobile, the detail replaces the list (master/detail swap) so no fixed side
  // panel forces horizontal overflow.
  if (mobile && sel) {
    return <div style={{ flex: 1, padding: "16px 16px", minWidth: 0 }}>{detail}</div>;
  }

  return (
    <div style={{ flex: 1, display: "flex", minWidth: 0 }}>
      <div style={{ flex: 1, padding: "20px clamp(16px,4vw,20px)", minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
        <H title="Users" note={`${rows.length}`} />
        <input placeholder="search call-sign / email" value={q} onChange={(e) => setQ(e.target.value)} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, padding: "7px 10px", font: `400 10px ${MONO}`, color: C.fg, width: "100%", maxWidth: 260, boxSizing: "border-box" }} />
        {mobile ? (
          // Stacked cards — the 5-column table is unreadable at 360px.
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {rows.map((u) => (
              <button key={u.id} type="button" onClick={() => setSel(u)} style={{ textAlign: "left", background: C.panel, border: `1px solid ${sel?.id === u.id ? "rgba(31,178,134,.4)" : "rgba(233,238,243,.08)"}`, borderRadius: 10, padding: "12px 14px", display: "flex", flexDirection: "column", gap: 6, cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ font: `600 12px ${MONO}`, color: C.fg }}>{u.call_sign ?? u.email}</span>
                  <span style={{ font: `600 10px ${MONO}`, color: C.green }}>{u.tier.toUpperCase()}</span>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "2px 12px", font: `400 9px ${MONO}`, color: C.muted }}>
                  <span>{u.subscription_status === "trial" ? "TRIAL" : u.subscription_status === "expired" ? "EXPIRED" : "ACTIVE"}</span>
                  <span>LAST {u.last_scan_at ? String(u.last_scan_at).slice(0, 10) : "·"}</span>
                  <span>XP {u.xp}</span>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div style={{ background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, overflow: "hidden", font: `400 10px ${MONO}` }}>
            <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr .9fr 1.1fr 1fr", padding: "10px 14px", borderBottom: `1px solid rgba(233,238,243,.08)`, fontWeight: 600, fontSize: 8, letterSpacing: 1, color: C.muted }}>
              <span>CALL-SIGN</span><span>PLAN</span><span>TRIAL</span><span>LAST SCAN</span><span>XP</span>
            </div>
            {rows.map((u) => (
              <button key={u.id} type="button" onClick={() => setSel(u)} style={{ width: "100%", textAlign: "left", display: "grid", gridTemplateColumns: "1.5fr 1fr .9fr 1.1fr 1fr", padding: "11px 14px", borderBottom: `1px solid rgba(233,238,243,.05)`, alignItems: "center", background: sel?.id === u.id ? "rgba(31,178,134,.05)" : "none", border: "none", cursor: "pointer", font: `400 10px ${MONO}` }}>
                <span style={{ color: C.fg, fontWeight: 600 }}>{u.call_sign ?? u.email}</span>
                <span style={{ color: C.green }}>{u.tier.toUpperCase()}</span>
                <span style={{ color: C.muted }}>{u.subscription_status === "trial" ? "TRIAL" : u.subscription_status === "expired" ? "EXPIRED" : "·"}</span>
                <span style={{ color: C.fg }}>{u.last_scan_at ? String(u.last_scan_at).slice(0, 10) : "·"}</span>
                <span style={{ color: C.muted }}>{u.xp}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      {!mobile && detail}
    </div>
  );
}

function OverrideRow({ label, onClick, danger }: { label: string; onClick: () => void; danger?: boolean }) {
  return (
    <button type="button" onClick={onClick} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: C.bg, border: `1px solid ${danger ? "rgba(224,88,79,.25)" : "rgba(233,238,243,.1)"}`, borderRadius: 8, padding: "9px 11px", font: `400 10px ${MONO}`, color: danger ? C.red : C.fg, cursor: "pointer", textAlign: "left" }}>
      <span>{label}</span><span>▸</span>
    </button>
  );
}

function Tickets() {
  const mobile = useIsMobile();
  const [list, setList] = useState<any[]>([]);
  const [counts, setCounts] = useState<any>({});
  const [sel, setSel] = useState<any | null>(null);
  const [replies, setReplies] = useState<any[]>([]);
  const [reply, setReply] = useState("");
  const load = useCallback(async () => {
    const r = await apiFetch<any>("/api/admin/tickets");
    if (r.ok && r.data) { setList(r.data.tickets); setCounts(r.data.counts); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function open(t: any) {
    setSel(t);
    const r = await apiFetch<any>(`/api/admin/tickets/${t.id}`);
    if (r.ok && r.data) setReplies(r.data.replies);
  }
  async function sendReply(status?: string) {
    if (!sel || !reply.trim()) return;
    await apiFetch(`/api/admin/tickets/${sel.id}/reply`, { method: "POST", body: JSON.stringify({ body: reply.trim(), status }) });
    setReply("");
    await open(sel);
    await load();
  }

  const listPane = (
    <div style={mobile
      ? { flex: 1, padding: "16px 16px", display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }
      : { width: 340, flex: "none", borderRight: `1px solid rgba(233,238,243,.08)`, padding: "20px 16px", display: "flex", flexDirection: "column", gap: 8, overflow: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ font: `700 15px ${SANS}`, color: C.fg }}>Tickets</span>
        <span style={{ font: `600 8px ${MONO}`, color: C.amber }}>OPEN {counts.open ?? 0}</span>
      </div>
      {list.map((t) => (
        <button key={t.id} type="button" onClick={() => open(t)} style={{ textAlign: "left", background: C.panel, border: `1px solid ${sel?.id === t.id ? "rgba(31,178,134,.45)" : "rgba(233,238,243,.08)"}`, borderRadius: 10, padding: "11px 13px", display: "flex", flexDirection: "column", gap: 4, cursor: "pointer" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, font: `600 10px ${MONO}` }}>
            <span style={{ color: C.fg, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>#{String(t.id).padStart(4, "0")} · {t.call_sign ?? t.email}</span>
            <span style={{ flex: "none", color: t.status === "open" ? C.amber : t.status === "resolved" ? C.green : C.fg }}>{t.status.toUpperCase()}</span>
          </div>
          <span style={{ font: `400 10.5px ${SANS}`, color: C.muted }}>{t.subject}</span>
          <span style={{ font: `400 8px ${MONO}`, color: C.muted }}>via Report a problem · {t.tier?.toUpperCase()} {t.subscription_status === "trial" ? "TRIAL" : ""}</span>
        </button>
      ))}
    </div>
  );

  const detailPane = (
    <div style={{ flex: 1, padding: "20px clamp(16px,4vw,20px)", display: "flex", flexDirection: "column", minWidth: 0 }}>
      {!sel ? <span style={{ font: `400 11px ${MONO}`, color: C.muted }}>Select a ticket.</span> : (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, paddingBottom: 12, borderBottom: `1px solid rgba(233,238,243,.08)` }}>
            <div style={{ minWidth: 0 }}>
              {mobile && (
                <button type="button" onClick={() => { setSel(null); setReplies([]); }} style={{ marginBottom: 8, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, padding: "6px 10px", font: `600 9px ${MONO}`, color: C.muted, cursor: "pointer" }}>← BACK</button>
              )}
              <div style={{ font: `600 13px ${MONO}`, color: C.fg }}>#{String(sel.id).padStart(4, "0")} · {sel.subject}</div>
              <div style={{ font: `400 9px ${MONO}`, color: C.muted, marginTop: 2 }}>{sel.call_sign ?? sel.email} · {sel.tier?.toUpperCase()}</div>
            </div>
            <button type="button" onClick={() => sendReply("resolved")} style={{ flex: "none", font: `600 9px ${MONO}`, color: C.bg, background: C.green, borderRadius: 6, padding: "6px 10px", border: "none", cursor: "pointer" }}>RESOLVE ✓</button>
          </div>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10, padding: "14px 0", overflow: "auto" }}>
            <div style={{ maxWidth: "90%", background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, padding: "10px 13px" }}>
              <div style={{ font: `600 8px ${MONO}`, color: C.muted, paddingBottom: 3 }}>{sel.call_sign ?? sel.email}</div>
              <div style={{ font: `400 11px/1.5 ${SANS}`, color: C.fg }}>{sel.body}</div>
            </div>
            {replies.map((r) => (
              <div key={r.id} style={{ maxWidth: "90%", alignSelf: r.is_admin ? "flex-end" : "flex-start", background: r.is_admin ? "rgba(31,178,134,.08)" : C.panel, border: `1px solid ${r.is_admin ? "rgba(31,178,134,.3)" : "rgba(233,238,243,.08)"}`, borderRadius: 10, padding: "10px 13px" }}>
                <div style={{ font: `600 8px ${MONO}`, color: r.is_admin ? C.green : C.muted, paddingBottom: 3 }}>{r.is_admin ? "ADMIN" : "USER"}</div>
                <div style={{ font: `400 11px/1.5 ${SANS}`, color: C.fg }}>{r.body}</div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8, borderTop: `1px solid rgba(233,238,243,.08)`, paddingTop: 12 }}>
            <input value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Reply (email send is a logged stub)" style={{ flex: 1, minWidth: 0, background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: "10px 13px", font: `400 10.5px ${MONO}`, color: C.fg }} />
            <button type="button" onClick={() => sendReply()} style={{ flex: "none", background: C.green, borderRadius: 8, padding: "0 16px", font: `600 10px ${MONO}`, color: C.bg, border: "none", cursor: "pointer" }}>SEND</button>
          </div>
        </>
      )}
    </div>
  );

  // Mobile: show the list, or the conversation when one is picked (swap, no split).
  if (mobile) {
    return <div style={{ flex: 1, display: "flex", minWidth: 0 }}>{sel ? detailPane : listPane}</div>;
  }
  return (
    <div style={{ flex: 1, display: "flex", minWidth: 0 }}>
      {listPane}
      {detailPane}
    </div>
  );
}

function Broadcast() {
  const mobile = useIsMobile();
  const [counts, setCounts] = useState<any>({});
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState<"all" | "plan" | "trial_ending">("all");
  const [targetTier, setTargetTier] = useState("basic");
  const [inApp, setInApp] = useState(true);
  const [email, setEmail] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [preview, setPreview] = useState<{ recipients: number; email_optin: number } | null>(null);
  useEffect(() => { void apiFetch<any>("/api/admin/broadcasts").then((r) => r.ok && setCounts(r.data.audience_counts)); }, []);

  // Confirm-step preview: audience size + how many will actually receive an email
  // (opted in to broadcast email). Refreshes when the audience selection changes.
  useEffect(() => {
    const q = new URLSearchParams({ audience, ...(audience === "plan" ? { target_tier: targetTier } : {}) });
    void apiFetch<{ recipients: number; email_optin: number }>(`/api/admin/broadcasts/preview?${q}`).then((r) => {
      if (r.ok && r.data) setPreview(r.data);
    });
    setConfirming(false);
  }, [audience, targetTier]);

  async function send() {
    if (!title.trim() || !body.trim()) return;
    const r = await apiFetch<{ delivered_inapp: number; delivered_email: number }>("/api/admin/broadcasts", { method: "POST", body: JSON.stringify({ title: title.trim(), body: body.trim(), audience, target_tier: audience === "plan" ? targetTier : null, channel_in_app: inApp, channel_email: email }) });
    if (r.ok && r.data) {
      setSent(`Sent. In-app: ${r.data.delivered_inapp}, email: ${r.data.delivered_email}.`);
      setTitle(""); setBody(""); setConfirming(false);
    }
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: mobile ? "column" : "row", minWidth: 0 }}>
      <div style={{ flex: 1, padding: "20px clamp(16px,4vw,22px)", display: "flex", flexDirection: "column", gap: 12, minWidth: 0 }}>
        <H title="Broadcast" note="compose announcement" />
        <Label text="AUDIENCE" />
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, font: `600 9px ${MONO}` }}>
          {(["all", "plan", "trial_ending"] as const).map((a) => (
            <button key={a} type="button" onClick={() => setAudience(a)} style={pill(audience === a)}>
              {a === "all" ? `ALL · ${counts.all ?? 0}` : a === "plan" ? "BY PLAN" : `TRIAL ENDING · ${counts.trial_ending ?? 0}`}
            </button>
          ))}
          {audience === "plan" && (
            <select value={targetTier} onChange={(e) => setTargetTier(e.target.value)} style={{ background: C.bg, color: C.fg, border: `1px solid ${C.border}`, borderRadius: 14, padding: "6px 12px", font: `600 9px ${MONO}` }}>
              {["free", "basic", "pro"].map((t) => <option key={t} value={t}>{t.toUpperCase()}</option>)}
            </select>
          )}
        </div>
        <Label text="CHANNEL" />
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, font: `600 9px ${MONO}` }}>
          <button type="button" onClick={() => setInApp(!inApp)} style={pill(inApp)}>{inApp ? "✓ " : ""}IN-APP</button>
          <button type="button" onClick={() => setEmail(!email)} style={pill(email)}>{email ? "✓ " : ""}EMAIL</button>
        </div>
        {preview && (
          <div style={{ font: `400 9px/1.5 ${MONO}`, color: C.muted }}>
            Audience: {preview.recipients}. Email opted-in: {preview.email_optin}. Every update email carries a one-click unsubscribe link.
          </div>
        )}
        <Label text="MESSAGE" />
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: "10px 13px", font: `400 11px ${SANS}`, color: C.fg, width: "100%", boxSizing: "border-box" }} />
        <textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder="Your message. It never covers the scan button or the disclaimer." rows={4} style={{ background: C.panel, border: `1px solid rgba(31,178,134,.35)`, borderRadius: 10, padding: "13px 15px", font: `400 11.5px/1.6 ${SANS}`, color: C.fg, resize: "vertical", width: "100%", boxSizing: "border-box" }} />
        <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 8 }}>
          {sent && <span style={{ font: `400 9px ${MONO}`, color: C.green, alignSelf: "center" }}>{sent}</span>}
          {confirming && (
            <span style={{ font: `400 9px ${MONO}`, color: C.amber, alignSelf: "center" }}>
              Send to {preview?.recipients ?? 0}{email ? ` (${preview?.email_optin ?? 0} email)` : ""}?
            </span>
          )}
          {confirming && (
            <button type="button" onClick={() => setConfirming(false)} style={{ font: `600 10px ${MONO}`, color: C.muted, background: "none", borderRadius: 8, padding: "9px 12px", border: `1px solid ${C.border}`, cursor: "pointer" }}>CANCEL</button>
          )}
          <button
            type="button"
            onClick={() => { if (!title.trim() || !body.trim()) return; if (confirming) { void send(); } else { setSent(null); setConfirming(true); } }}
            style={{ font: `600 10px ${MONO}`, color: C.bg, background: confirming ? C.amber : C.green, borderRadius: 8, padding: "9px 16px", border: "none", cursor: "pointer" }}
          >
            {confirming ? "CONFIRM SEND" : "SEND BROADCAST"}
          </button>
        </div>
      </div>
      <div style={{ width: mobile ? "auto" : 300, flex: "none", padding: mobile ? "0 16px 20px" : "20px 20px", display: "flex", flexDirection: "column", gap: 10 }}>
        <Label text="LIVE PREVIEW · IN-APP BANNER" />
        <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
          <div style={{ background: "rgba(31,178,134,.09)", border: `1px solid rgba(31,178,134,.4)`, borderRadius: 9, padding: "9px 11px", display: "flex", gap: 8 }}>
            <span aria-hidden>📣</span>
            <span style={{ font: `400 9px/1.5 ${SANS}`, color: C.fg }}>{body || "Your message preview appears here."}</span>
          </div>
        </div>
        <div style={{ font: `400 8.5px/1.5 ${MONO}`, color: C.muted }}>Banner is dismissible and never blocks the scan button or the disclaimer.</div>
      </div>
    </div>
  );
}

function Settings() {
  const mobile = useIsMobile();
  const [rows, setRows] = useState<any[]>([]);
  const [locked, setLocked] = useState<any[]>([]);
  const [edited, setEdited] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  const load = useCallback(async () => {
    const r = await apiFetch<any>("/api/admin/settings");
    if (r.ok && r.data) { setRows(r.data.settings); setLocked(r.data.locked); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function save() {
    const updates = Object.entries(edited).map(([key, value]) => ({ key, value }));
    if (updates.length === 0) return;
    await apiFetch("/api/admin/settings", { method: "PUT", body: JSON.stringify({ updates, note: "admin console edit" }) });
    setEdited({});
    setSaved(true);
    await load();
  }

  return (
    <div style={{ flex: 1, padding: "20px clamp(16px,4vw,24px)", display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <H title="System settings" note="live values, editable without code" />
        <button type="button" onClick={save} style={{ font: `600 10px ${MONO}`, color: C.bg, background: C.green, borderRadius: 8, padding: "8px 15px", border: "none", cursor: "pointer" }}>SAVE &amp; APPLY</button>
      </div>
      {saved && <span style={{ font: `400 9px ${MONO}`, color: C.green }}>Saved. Changes apply on next app open.</span>}
      <div style={{ background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, overflow: "hidden" }}>
        {rows.map((s) => (
          <div key={s.key} style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 10, padding: "9px 16px", borderBottom: `1px solid rgba(233,238,243,.05)`, alignItems: "center", font: `400 10.5px ${MONO}` }}>
            <span style={{ color: C.fg }}>{s.description ?? s.key}</span>
            <input defaultValue={s.value} onChange={(e) => setEdited((p) => ({ ...p, [s.key]: e.target.value }))} style={{ background: C.bg, border: `1px solid rgba(31,178,134,.35)`, borderRadius: 5, padding: "4px 10px", color: C.fg, font: `400 10.5px ${MONO}`, width: "100%", maxWidth: 120, boxSizing: "border-box", justifySelf: "end" }} />
          </div>
        ))}
      </div>
      <div style={{ display: "flex", flexDirection: mobile ? "column" : "row", gap: 10 }}>
        {locked.map((l) => (
          <div key={l.key} style={{ flex: 1, background: C.panel, border: `1px solid rgba(224,88,79,.2)`, borderRadius: 10, padding: 13, display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ font: `600 8px ${MONO}`, letterSpacing: 1, color: C.muted }}>{l.key.toUpperCase()}</span>
            <span style={{ font: `600 11px ${MONO}`, color: C.red }}>{l.value} · LOCKED</span>
            <span style={{ font: `400 8.5px ${MONO}`, color: C.muted }}>{l.reason}</span>
          </div>
        ))}
      </div>
      <div style={{ font: `400 9px ${MONO}`, color: C.muted }}>The score gate and card-off are engine and policy constants, not settings.</div>
    </div>
  );
}

function Notifications() {
  const mobile = useIsMobile();
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { void apiFetch<any>("/api/admin/notifications").then((r) => r.ok && setRows(r.data.notifications)); }, []);
  const cols = "1.6fr 1.1fr 1.4fr .9fr";
  // Mobile: the 4-column log scrolls horizontally with a sticky first column so a
  // narrow phone never clips it (Nadav: "never cut off").
  const stickyFirst: React.CSSProperties = mobile ? { position: "sticky", left: 0, background: C.panel, zIndex: 1 } : {};
  return (
    <div style={{ flex: 1, padding: "20px clamp(16px,4vw,24px)", display: "flex", flexDirection: "column", gap: 12 }}>
      <H title="Notifications log" note="system sends" />
      <div style={{ font: `400 9px/1.5 ${MONO}`, color: C.muted }}>System notification log: the two automated sends (day-11 trial reminder, journal-reveal teaser). Broadcasts are separate (see Broadcast).</div>
      <div style={{ background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, overflow: "hidden", font: `400 10px ${MONO}` }}>
        <div style={{ overflowX: "auto", WebkitOverflowScrolling: "touch" }}>
          <div style={{ minWidth: mobile ? 440 : 0 }}>
            <div style={{ display: "grid", gridTemplateColumns: cols, padding: "10px 16px", borderBottom: `1px solid rgba(233,238,243,.08)`, fontWeight: 600, fontSize: 8, letterSpacing: 1, color: C.muted }}>
              <span style={stickyFirst}>TYPE</span><span>TO</span><span>CHANNEL · WHEN</span><span>STATUS</span>
            </div>
            {rows.length === 0 && <div style={{ padding: 16, font: `400 10px ${MONO}`, color: C.muted }}>No system sends yet. The two send types are the day-11 trial reminder and the journal-reveal teaser.</div>}
            {rows.map((n) => (
              <div key={n.id} style={{ display: "grid", gridTemplateColumns: cols, padding: "11px 16px", borderBottom: `1px solid rgba(233,238,243,.05)`, alignItems: "center" }}>
                <span style={{ color: C.fg, ...stickyFirst }}>{n.notif_type.replace(/_/g, " ").toUpperCase()}</span>
                <span style={{ color: C.muted }}>{n.email ?? "system"}</span>
                <span style={{ color: C.muted }}>{n.channel} · {String(n.created_at).slice(0, 16)}</span>
                <span style={{ color: n.status === "delivered" || n.status === "sent" ? C.green : n.status === "failed" ? C.red : C.muted, fontWeight: 600 }}>{n.status.toUpperCase()}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div style={{ font: `400 9px ${MONO}`, color: C.muted }}>Only two system send types exist by design, the day-11 trial reminder and the journal-reveal teaser (never a push that reveals).</div>
    </div>
  );
}

function H({ title, note }: { title: string; note?: string }) {
  return <div style={{ font: `700 17px ${SANS}`, color: C.fg }}>{title} {note && <span style={{ font: `400 10px ${MONO}`, color: C.muted }}>· {note}</span>}</div>;
}
function Label({ text }: { text: string }) {
  return <span style={{ font: `600 8px ${MONO}`, letterSpacing: 1, color: C.muted }}>{text}</span>;
}
function Loading() {
  return <div style={{ padding: 24, font: `400 11px ${MONO}`, color: C.muted }}>Loading…</div>;
}
function pill(active: boolean): React.CSSProperties {
  return { color: active ? C.green : C.muted, background: active ? "rgba(31,178,134,.1)" : "none", border: `1px solid ${active ? C.green : "rgba(233,238,243,.15)"}`, borderRadius: 14, padding: "6px 12px", cursor: "pointer" };
}

export default function AdminPage() {
  const router = useRouter();
  const { me, loading } = useMe("admin");
  const mobile = useIsMobile();
  const [section, setSection] = useState<Section>("overview");
  const [ticketCount, setTicketCount] = useState(0);

  useEffect(() => {
    if (!me) return;
    void apiFetch<any>("/api/admin/tickets?status=open").then((r) => r.ok && setTicketCount(r.data.tickets.length));
  }, [me]);

  if (loading || !me) return <main style={{ minHeight: "100vh", background: C.bg }} />;

  // Neutralize the global `main` rule (column flex + center + 2rem padding + centered
  // text) so the console lays out edge-to-edge: a top tab bar over a full-width column
  // on mobile, the fixed rail beside full-width content on desktop.
  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex", flexDirection: mobile ? "column" : "row", alignItems: "stretch", justifyContent: "flex-start", gap: 0, padding: 0, textAlign: "left" }}>
      <Rail section={section} setSection={setSection} ticketCount={ticketCount} onExit={() => router.push("/scan")} mobile={mobile} />
      <div style={{ flex: 1, display: "flex", minWidth: 0 }}>
        {section === "overview" && <Overview />}
        {section === "users" && <Users />}
        {section === "tickets" && <Tickets />}
        {section === "broadcast" && <Broadcast />}
        {section === "settings" && <Settings />}
        {section === "notifications" && <Notifications />}
      </div>
    </main>
  );
}
