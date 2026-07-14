"use client";

// Academy 2.0 admin (deliverable D): create / edit / reorder (up-down) / archive / restore
// lessons, including video URL attachment, tag editing, and dual-gate (plan + rank)
// assignment. All calls hit /api/admin/academy/* (admin-only; 403 otherwise). Ordering uses
// explicit up/down buttons (D-AC5) that POST the full new order.

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import type { AdminLesson } from "@/lib/app/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

type Draft = {
  id?: number;
  title: string;
  description: string;
  content_type: "text" | "video";
  body: string;
  video_url: string;
  duration_minutes: number;
  tagsText: string;
  min_plan: "free" | "basic" | "pro";
  min_rank: number;
  awards_xp: boolean;
};

const BLANK: Draft = {
  title: "", description: "", content_type: "text", body: "", video_url: "",
  duration_minutes: 0, tagsText: "", min_plan: "free", min_rank: 0, awards_xp: true,
};

const RANKS: { v: number; label: string }[] = [
  { v: 0, label: "No rank gate" },
  { v: 1000, label: "Risk Manager (1,000)" },
  { v: 3000, label: "Regime Reader (3,000)" },
  { v: 8000, label: "Master Strategist (8,000)" },
];

function inputStyle(): React.CSSProperties {
  return { width: "100%", boxSizing: "border-box", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, padding: "9px 11px", font: `400 12px ${SANS}`, color: C.fg };
}
function label(text: string) {
  return <div style={{ font: `600 8px ${MONO}`, letterSpacing: 1, color: C.muted, marginBottom: 4 }}>{text.toUpperCase()}</div>;
}

function toDraft(l: AdminLesson): Draft {
  return {
    id: l.id, title: l.title, description: l.description, content_type: l.content_type,
    body: l.body, video_url: l.video_url ?? "", duration_minutes: l.duration_minutes,
    tagsText: (l.tags ?? []).join(", "), min_plan: l.min_plan, min_rank: l.min_rank,
    awards_xp: l.awards_xp,
  };
}

export function AcademyAdmin() {
  const [lessons, setLessons] = useState<AdminLesson[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const r = await apiFetch<AdminLesson[]>("/api/admin/academy/lessons");
    if (r.ok && r.data) setLessons(r.data);
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function save() {
    if (!draft) return;
    setSaving(true);
    setErr(null);
    const payload = {
      title: draft.title,
      description: draft.description,
      content_type: draft.content_type,
      body: draft.body,
      video_url: draft.content_type === "video" ? draft.video_url : null,
      duration_minutes: Number(draft.duration_minutes) || 0,
      tags: draft.tagsText.split(",").map((t) => t.trim()).filter(Boolean),
      min_plan: draft.min_plan,
      min_rank: draft.min_rank,
      awards_xp: draft.awards_xp,
    };
    const r = draft.id
      ? await apiFetch<AdminLesson>(`/api/admin/academy/lessons/${draft.id}`, { method: "PUT", body: JSON.stringify(payload) })
      : await apiFetch<AdminLesson>("/api/admin/academy/lessons", { method: "POST", body: JSON.stringify(payload) });
    setSaving(false);
    if (r.ok) {
      setDraft(null);
      await load();
    } else {
      setErr(r.error?.message ?? "Could not save this lesson.");
    }
  }

  async function reorder(index: number, dir: -1 | 1) {
    const next = [...lessons];
    const j = index + dir;
    if (j < 0 || j >= next.length) return;
    [next[index], next[j]] = [next[j], next[index]];
    setLessons(next);
    await apiFetch("/api/admin/academy/lessons/reorder", { method: "POST", body: JSON.stringify({ ordered_ids: next.map((l) => l.id) }) });
    await load();
  }

  async function toggleArchive(l: AdminLesson) {
    await apiFetch(`/api/admin/academy/lessons/${l.id}/${l.archived ? "restore" : "archive"}`, { method: "POST" });
    await load();
  }

  return (
    <div style={{ flex: 1, padding: 20, minWidth: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 14 }}>
        <div style={{ font: `700 15px ${SANS}`, color: C.fg }}>Academy lessons</div>
        <button type="button" onClick={() => { setErr(null); setDraft({ ...BLANK }); }} style={{ background: C.green, border: "none", borderRadius: 6, padding: "8px 14px", font: `600 10px ${MONO}`, color: C.bg, cursor: "pointer" }}>+ NEW LESSON</button>
      </div>

      {draft && (
        <div style={{ background: C.panel, border: `1px solid ${C.green}`, borderRadius: 10, padding: 16, marginBottom: 16, display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ font: `600 12px ${SANS}`, color: C.fg }}>{draft.id ? "Edit lesson" : "New lesson"}</div>
          <div>{label("Title")}<input style={inputStyle()} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} /></div>
          <div>{label("Short description (card)")}<input style={inputStyle()} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} /></div>

          <div style={{ display: "flex", gap: 8 }}>
            {(["text", "video"] as const).map((t) => (
              <button key={t} type="button" onClick={() => setDraft({ ...draft, content_type: t })} style={{ flex: 1, padding: "8px", borderRadius: 6, background: draft.content_type === t ? "rgba(31,178,134,.12)" : C.bg, border: `1px solid ${draft.content_type === t ? C.green : C.border}`, font: `600 10px ${MONO}`, color: draft.content_type === t ? C.green : C.muted, cursor: "pointer", textTransform: "uppercase" }}>{t}</button>
            ))}
          </div>

          {draft.content_type === "video" ? (
            <div>{label("Video URL (YouTube unlisted or Vimeo)")}<input style={inputStyle()} value={draft.video_url} placeholder="https://www.youtube.com/watch?v=..." onChange={(e) => setDraft({ ...draft, video_url: e.target.value })} /></div>
          ) : null}

          <div>{label(draft.content_type === "video" ? "Notes / transcript (optional)" : "Body")}
            <textarea style={{ ...inputStyle(), minHeight: 120, resize: "vertical", fontFamily: SANS }} value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value })} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 10 }}>
            <div>{label("Duration (min)")}<input type="number" style={inputStyle()} value={draft.duration_minutes} onChange={(e) => setDraft({ ...draft, duration_minutes: Number(e.target.value) })} /></div>
            <div>{label("Min plan")}
              <select style={inputStyle()} value={draft.min_plan} onChange={(e) => setDraft({ ...draft, min_plan: e.target.value as Draft["min_plan"] })}>
                <option value="free">Free</option><option value="basic">Basic</option><option value="pro">Pro</option>
              </select>
            </div>
            <div>{label("Min rank")}
              <select style={inputStyle()} value={draft.min_rank} onChange={(e) => setDraft({ ...draft, min_rank: Number(e.target.value) })}>
                {RANKS.map((r) => <option key={r.v} value={r.v}>{r.label}</option>)}
              </select>
            </div>
          </div>
          <div>{label("Tags (comma separated)")}<input style={inputStyle()} value={draft.tagsText} onChange={(e) => setDraft({ ...draft, tagsText: e.target.value })} /></div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, font: `400 11px ${SANS}`, color: C.fg, cursor: "pointer" }}>
            <input type="checkbox" checked={draft.awards_xp} onChange={(e) => setDraft({ ...draft, awards_xp: e.target.checked })} />
            Awards +100 XP on completion
          </label>

          {err && <div style={{ font: `400 10px ${MONO}`, color: C.red }}>{err}</div>}
          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" onClick={save} disabled={saving} style={{ flex: 1, background: C.green, border: "none", borderRadius: 6, padding: "10px", font: `600 10px ${MONO}`, color: C.bg, cursor: "pointer" }}>{saving ? "SAVING…" : "SAVE"}</button>
            <button type="button" onClick={() => { setDraft(null); setErr(null); }} style={{ flex: "none", background: "none", border: `1px solid ${C.border}`, borderRadius: 6, padding: "10px 16px", font: `600 10px ${MONO}`, color: C.muted, cursor: "pointer" }}>CANCEL</button>
          </div>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {lessons.map((l, i) => (
          <div key={l.id} style={{ background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, padding: "11px 13px", display: "flex", alignItems: "center", gap: 10, opacity: l.archived ? 0.55 : 1 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <button type="button" aria-label="Move up" onClick={() => reorder(i, -1)} disabled={i === 0} style={{ background: "none", border: `1px solid ${C.border}`, borderRadius: 4, color: C.muted, cursor: i === 0 ? "default" : "pointer", font: `600 9px ${MONO}`, lineHeight: 1, padding: "2px 5px" }}>▲</button>
              <button type="button" aria-label="Move down" onClick={() => reorder(i, 1)} disabled={i === lessons.length - 1} style={{ background: "none", border: `1px solid ${C.border}`, borderRadius: 4, color: C.muted, cursor: i === lessons.length - 1 ? "default" : "pointer", font: `600 9px ${MONO}`, lineHeight: 1, padding: "2px 5px" }}>▼</button>
            </div>
            <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 3 }}>
              <span style={{ font: `600 12px ${SANS}`, color: C.fg }}>{l.title} {l.archived && <span style={{ font: `600 8px ${MONO}`, color: C.amber }}>ARCHIVED</span>}</span>
              <span style={{ font: `400 9px ${MONO}`, color: C.muted }}>
                {l.content_type.toUpperCase()} · {l.duration_minutes}m · plan:{l.min_plan} · rank:{l.min_rank} · {l.awards_xp ? "+100 XP" : "no XP"}
              </span>
            </div>
            <button type="button" onClick={() => { setErr(null); setDraft(toDraft(l)); }} style={{ flex: "none", background: "none", border: `1px solid ${C.border}`, borderRadius: 6, padding: "6px 10px", font: `600 9px ${MONO}`, color: C.fg, cursor: "pointer" }}>EDIT</button>
            <button type="button" onClick={() => toggleArchive(l)} style={{ flex: "none", background: "none", border: `1px solid ${C.border}`, borderRadius: 6, padding: "6px 10px", font: `600 9px ${MONO}`, color: l.archived ? C.green : C.amber, cursor: "pointer" }}>{l.archived ? "RESTORE" : "ARCHIVE"}</button>
          </div>
        ))}
      </div>
    </div>
  );
}
