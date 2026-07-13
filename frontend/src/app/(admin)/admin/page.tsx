"use client";

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import { useMe } from "@/lib/app/session";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

type Section = "overview" | "users" | "tickets" | "broadcast" | "settings" | "notifications";
const SECTIONS: Section[] = ["overview", "users", "tickets", "broadcast", "settings", "notifications"];

/* eslint-disable @typescript-eslint/no-explicit-any */

function Rail({ section, setSection, ticketCount }: { section: Section; setSection: (s: Section) => void; ticketCount: number }) {
  return (
    <div style={{ width: 200, flex: "none", background: C.panel, borderRight: `1px solid rgba(233,238,243,.08)`, display: "flex", flexDirection: "column", padding: "18px 0" }}>
      <div style={{ padding: "0 20px 18px", font: `700 12px ${SANS}`, letterSpacing: 3, color: C.fg }}>
        FINARODA <span style={{ font: `600 8px ${MONO}`, color: C.amber, border: `1px solid rgba(224,145,63,.4)`, borderRadius: 3, padding: "2px 5px", marginLeft: 4 }}>ADMIN</span>
      </div>
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
    <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 12 }}>
      <H title="Overview" note="first-100 vitals, live data" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 10 }}>
        <Stat label="USERS" value={String(d.users.total)} sub={`+${d.users.new_this_week} this week`} color={C.green} />
        <Stat label="TRIALS ACTIVE" value={String(d.trials.active)} sub={`${d.trials.expiring_3d} end within 3 days`} color={C.green} />
        <Stat label="TRIALS EXPIRED" value={String(d.trials.expired)} />
        <Stat label="MRR" value={`₪${d.mrr_ils}`} sub={`${d.mrr_breakdown.basic} basic · ${d.mrr_breakdown.advanced} adv · ${d.mrr_breakdown.pro} pro`} color={C.green} />
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

  return (
    <div style={{ flex: 1, display: "flex", minWidth: 0 }}>
      <div style={{ flex: 1, padding: "20px 20px", minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
        <H title="Users" note={`${rows.length}`} />
        <input placeholder="search call-sign / email" value={q} onChange={(e) => setQ(e.target.value)} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, padding: "7px 10px", font: `400 10px ${MONO}`, color: C.fg, width: 260 }} />
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
      </div>
      {sel && (
        <div style={{ width: 280, flex: "none", background: C.panel, borderLeft: `1px solid rgba(233,238,243,.08)`, padding: "20px 18px", display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ font: `600 12px ${MONO}`, color: C.fg }}>{sel.call_sign ?? sel.email}</div>
          <div style={{ font: `600 8px ${MONO}`, letterSpacing: 1, color: C.amber }}>ADMIN-ONLY OVERRIDES</div>
          <input placeholder="audit note (required)" value={note} onChange={(e) => setNote(e.target.value)} style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, padding: "7px 9px", font: `400 9px ${MONO}`, color: C.fg }} />
          <OverrideRow label="Plan → Pro" onClick={() => override("plan_override", "pro")} />
          <OverrideRow label="Plan → Free" onClick={() => override("plan_override", "free")} />
          <OverrideRow label="Extend trial +7 days" onClick={() => override("extend_trial", "7")} />
          <OverrideRow label="Grant +250 XP (support)" onClick={() => override("grant_xp", "250")} />
          <OverrideRow label={sel.suspended ? "Unsuspend account" : "Suspend account"} danger onClick={() => override(sel.suspended ? "unsuspend" : "suspend")} />
          <div style={{ font: `400 8.5px/1.5 ${MONO}`, color: C.muted }}>Every override is logged with admin id and reason (audit trail).</div>
        </div>
      )}
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

  return (
    <div style={{ flex: 1, display: "flex", minWidth: 0 }}>
      <div style={{ width: 340, flex: "none", borderRight: `1px solid rgba(233,238,243,.08)`, padding: "20px 16px", display: "flex", flexDirection: "column", gap: 8, overflow: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ font: `700 15px ${SANS}`, color: C.fg }}>Tickets</span>
          <span style={{ font: `600 8px ${MONO}`, color: C.amber }}>OPEN {counts.open ?? 0}</span>
        </div>
        {list.map((t) => (
          <button key={t.id} type="button" onClick={() => open(t)} style={{ textAlign: "left", background: C.panel, border: `1px solid ${sel?.id === t.id ? "rgba(31,178,134,.45)" : "rgba(233,238,243,.08)"}`, borderRadius: 10, padding: "11px 13px", display: "flex", flexDirection: "column", gap: 4, cursor: "pointer" }}>
            <div style={{ display: "flex", justifyContent: "space-between", font: `600 10px ${MONO}` }}>
              <span style={{ color: C.fg }}>#{String(t.id).padStart(4, "0")} · {t.call_sign ?? t.email}</span>
              <span style={{ color: t.status === "open" ? C.amber : t.status === "resolved" ? C.green : C.fg }}>{t.status.toUpperCase()}</span>
            </div>
            <span style={{ font: `400 10.5px ${SANS}`, color: C.muted }}>{t.subject}</span>
            <span style={{ font: `400 8px ${MONO}`, color: C.muted }}>via Report a problem · {t.tier?.toUpperCase()} {t.subscription_status === "trial" ? "TRIAL" : ""}</span>
          </button>
        ))}
      </div>
      <div style={{ flex: 1, padding: "20px 20px", display: "flex", flexDirection: "column", minWidth: 0 }}>
        {!sel ? <span style={{ font: `400 11px ${MONO}`, color: C.muted }}>Select a ticket.</span> : (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 12, borderBottom: `1px solid rgba(233,238,243,.08)` }}>
              <div>
                <div style={{ font: `600 13px ${MONO}`, color: C.fg }}>#{String(sel.id).padStart(4, "0")} · {sel.subject}</div>
                <div style={{ font: `400 9px ${MONO}`, color: C.muted, marginTop: 2 }}>{sel.call_sign ?? sel.email} · {sel.tier?.toUpperCase()}</div>
              </div>
              <button type="button" onClick={() => sendReply("resolved")} style={{ font: `600 9px ${MONO}`, color: C.bg, background: C.green, borderRadius: 6, padding: "6px 10px", border: "none", cursor: "pointer" }}>RESOLVE ✓</button>
            </div>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10, padding: "14px 0", overflow: "auto" }}>
              <div style={{ maxWidth: "78%", background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, padding: "10px 13px" }}>
                <div style={{ font: `600 8px ${MONO}`, color: C.muted, paddingBottom: 3 }}>{sel.call_sign ?? sel.email}</div>
                <div style={{ font: `400 11px/1.5 ${SANS}`, color: C.fg }}>{sel.body}</div>
              </div>
              {replies.map((r) => (
                <div key={r.id} style={{ maxWidth: "78%", alignSelf: r.is_admin ? "flex-end" : "flex-start", background: r.is_admin ? "rgba(31,178,134,.08)" : C.panel, border: `1px solid ${r.is_admin ? "rgba(31,178,134,.3)" : "rgba(233,238,243,.08)"}`, borderRadius: 10, padding: "10px 13px" }}>
                  <div style={{ font: `600 8px ${MONO}`, color: r.is_admin ? C.green : C.muted, paddingBottom: 3 }}>{r.is_admin ? "ADMIN" : "USER"}</div>
                  <div style={{ font: `400 11px/1.5 ${SANS}`, color: C.fg }}>{r.body}</div>
                </div>
              ))}
            </div>
            <div style={{ display: "flex", gap: 8, borderTop: `1px solid rgba(233,238,243,.08)`, paddingTop: 12 }}>
              <input value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Reply (email send is a logged stub)" style={{ flex: 1, background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: "10px 13px", font: `400 10.5px ${MONO}`, color: C.fg }} />
              <button type="button" onClick={() => sendReply()} style={{ background: C.green, borderRadius: 8, padding: "0 16px", font: `600 10px ${MONO}`, color: C.bg, border: "none", cursor: "pointer" }}>SEND</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Broadcast() {
  const [counts, setCounts] = useState<any>({});
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState<"all" | "plan" | "trial_ending">("all");
  const [targetTier, setTargetTier] = useState("basic");
  const [inApp, setInApp] = useState(true);
  const [email, setEmail] = useState(false);
  const [sent, setSent] = useState(false);
  useEffect(() => { void apiFetch<any>("/api/admin/broadcasts").then((r) => r.ok && setCounts(r.data.audience_counts)); }, []);

  async function send() {
    if (!title.trim() || !body.trim()) return;
    const r = await apiFetch("/api/admin/broadcasts", { method: "POST", body: JSON.stringify({ title: title.trim(), body: body.trim(), audience, target_tier: audience === "plan" ? targetTier : null, channel_in_app: inApp, channel_email: email }) });
    if (r.ok) { setSent(true); setTitle(""); setBody(""); }
  }

  return (
    <div style={{ flex: 1, display: "flex" }}>
      <div style={{ flex: 1, padding: "20px 22px", display: "flex", flexDirection: "column", gap: 12 }}>
        <H title="Broadcast" note="compose announcement" />
        <Label text="AUDIENCE" />
        <div style={{ display: "flex", gap: 6, font: `600 9px ${MONO}` }}>
          {(["all", "plan", "trial_ending"] as const).map((a) => (
            <button key={a} type="button" onClick={() => setAudience(a)} style={pill(audience === a)}>
              {a === "all" ? `ALL · ${counts.all ?? 0}` : a === "plan" ? "BY PLAN" : `TRIAL ENDING · ${counts.trial_ending ?? 0}`}
            </button>
          ))}
          {audience === "plan" && (
            <select value={targetTier} onChange={(e) => setTargetTier(e.target.value)} style={{ background: C.bg, color: C.fg, border: `1px solid ${C.border}`, borderRadius: 14, padding: "6px 12px", font: `600 9px ${MONO}` }}>
              {["free", "basic", "advanced", "pro"].map((t) => <option key={t} value={t}>{t.toUpperCase()}</option>)}
            </select>
          )}
        </div>
        <Label text="CHANNEL" />
        <div style={{ display: "flex", gap: 6, font: `600 9px ${MONO}` }}>
          <button type="button" onClick={() => setInApp(!inApp)} style={pill(inApp)}>{inApp ? "✓ " : ""}IN-APP BANNER</button>
          <button type="button" onClick={() => setEmail(!email)} style={pill(email)}>{email ? "✓ " : ""}EMAIL (stub)</button>
        </div>
        <Label text="MESSAGE" />
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" style={{ background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: "10px 13px", font: `400 11px ${SANS}`, color: C.fg }} />
        <textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder="Your message. It never covers the scan button or the disclaimer." rows={4} style={{ background: C.panel, border: `1px solid rgba(31,178,134,.35)`, borderRadius: 10, padding: "13px 15px", font: `400 11.5px/1.6 ${SANS}`, color: C.fg, resize: "vertical" }} />
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          {sent && <span style={{ font: `400 9px ${MONO}`, color: C.green, alignSelf: "center" }}>Broadcast stored.</span>}
          <button type="button" onClick={send} style={{ font: `600 10px ${MONO}`, color: C.bg, background: C.green, borderRadius: 8, padding: "9px 16px", border: "none", cursor: "pointer" }}>SEND BROADCAST</button>
        </div>
      </div>
      <div style={{ width: 300, flex: "none", padding: "20px 20px", display: "flex", flexDirection: "column", gap: 10 }}>
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
    <div style={{ flex: 1, padding: "20px 24px", display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <H title="System settings" note="live values, editable without code" />
        <button type="button" onClick={save} style={{ font: `600 10px ${MONO}`, color: C.bg, background: C.green, borderRadius: 8, padding: "8px 15px", border: "none", cursor: "pointer" }}>SAVE &amp; APPLY</button>
      </div>
      {saved && <span style={{ font: `400 9px ${MONO}`, color: C.green }}>Saved. Changes apply on next app open.</span>}
      <div style={{ background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, overflow: "hidden" }}>
        {rows.map((s) => (
          <div key={s.key} style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", padding: "9px 16px", borderBottom: `1px solid rgba(233,238,243,.05)`, alignItems: "center", font: `400 10.5px ${MONO}` }}>
            <span style={{ color: C.fg }}>{s.description ?? s.key}</span>
            <input defaultValue={s.value} onChange={(e) => setEdited((p) => ({ ...p, [s.key]: e.target.value }))} style={{ background: C.bg, border: `1px solid rgba(31,178,134,.35)`, borderRadius: 5, padding: "4px 10px", color: C.fg, font: `400 10.5px ${MONO}`, width: 100 }} />
          </div>
        ))}
      </div>
      <div style={{ display: "flex", gap: 10 }}>
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
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { void apiFetch<any>("/api/admin/notifications").then((r) => r.ok && setRows(r.data.notifications)); }, []);
  return (
    <div style={{ flex: 1, padding: "20px 24px", display: "flex", flexDirection: "column", gap: 12 }}>
      <H title="Notifications log" note="system sends" />
      <div style={{ background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, overflow: "hidden", font: `400 10px ${MONO}` }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1.1fr 1.4fr .9fr", padding: "10px 16px", borderBottom: `1px solid rgba(233,238,243,.08)`, fontWeight: 600, fontSize: 8, letterSpacing: 1, color: C.muted }}>
          <span>TYPE</span><span>TO</span><span>CHANNEL · WHEN</span><span>STATUS</span>
        </div>
        {rows.length === 0 && <div style={{ padding: 16, font: `400 10px ${MONO}`, color: C.muted }}>No system sends yet. The two send types are the day-11 trial reminder and the journal-reveal teaser.</div>}
        {rows.map((n) => (
          <div key={n.id} style={{ display: "grid", gridTemplateColumns: "1.6fr 1.1fr 1.4fr .9fr", padding: "11px 16px", borderBottom: `1px solid rgba(233,238,243,.05)`, alignItems: "center" }}>
            <span style={{ color: C.fg }}>{n.notif_type.replace(/_/g, " ").toUpperCase()}</span>
            <span style={{ color: C.muted }}>{n.email ?? "system"}</span>
            <span style={{ color: C.muted }}>{n.channel} · {String(n.created_at).slice(0, 16)}</span>
            <span style={{ color: n.status === "delivered" || n.status === "sent" ? C.green : n.status === "failed" ? C.red : C.muted, fontWeight: 600 }}>{n.status.toUpperCase()}</span>
          </div>
        ))}
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
  const { me, loading } = useMe("admin");
  const [section, setSection] = useState<Section>("overview");
  const [ticketCount, setTicketCount] = useState(0);

  useEffect(() => {
    if (!me) return;
    void apiFetch<any>("/api/admin/tickets?status=open").then((r) => r.ok && setTicketCount(r.data.tickets.length));
  }, [me]);

  if (loading || !me) return <main style={{ minHeight: "100vh", background: C.bg }} />;

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex" }}>
      <Rail section={section} setSection={setSection} ticketCount={ticketCount} />
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
