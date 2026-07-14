"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { apiFetch } from "@/lib/api";
import {
  EMPTY_LESSON_FILTER,
  filterLessons,
  lessonState,
  type LessonFilter,
  type LessonState,
  type LessonType,
} from "@/lib/app/academy";
import { C } from "@/lib/onboarding/types";
import { useMe } from "@/lib/app/session";
import type { AcademyLesson, AcademyResponse } from "@/lib/app/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

function badge(l: AcademyLesson): { text: string; color: string } {
  const st = lessonState(l);
  if (st === "locked") return { text: l.lock_reason ?? "Locked", color: C.amber };
  if (st === "completed") return { text: "Completed +100 XP", color: C.green };
  return { text: `${l.duration_minutes} MIN`, color: C.muted };
}

function chip(active: boolean): React.CSSProperties {
  return {
    flex: "none",
    padding: "6px 12px",
    borderRadius: 14,
    background: active ? "rgba(31,178,134,.12)" : C.bg,
    border: `1px solid ${active ? C.green : C.border}`,
    font: `${active ? 600 : 500} 10px ${MONO}`,
    color: active ? C.green : C.muted,
    cursor: "pointer",
    whiteSpace: "nowrap",
    textTransform: "capitalize",
  };
}

export default function AcademyPage() {
  const router = useRouter();
  const { me, loading } = useMe();
  const [data, setData] = useState<AcademyResponse | null>(null);
  const [xp, setXp] = useState(0);
  const [focus, setFocus] = useState<string | null>(null);
  const [filter, setFilter] = useState<LessonFilter>(EMPTY_LESSON_FILTER);

  useEffect(() => {
    if (!me) return;
    void apiFetch<AcademyResponse>("/api/academy").then((r) => {
      if (r.ok && r.data) {
        setData(r.data);
        setXp(r.data.xp_total);
      }
    });
    // Deep-link from a Concept Tooltip: /academy#<slug> highlights that lesson.
    if (typeof window !== "undefined" && window.location.hash) {
      const id = window.location.hash.slice(1);
      setFocus(id);
      setTimeout(() => document.getElementById(id)?.scrollIntoView({ block: "center" }), 60);
    }
  }, [me]);

  const visible = useMemo(
    () => (data ? filterLessons(data.modules, filter) : []),
    [data, filter],
  );

  if (loading || !me || !data) {
    return <main style={{ minHeight: "100vh", background: C.bg }} />;
  }

  const types: LessonType[] = ["all", "text", "video"];
  const states: LessonState[] = ["all", "locked", "unlocked", "completed"];

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 1040, display: "flex", flexDirection: "column" }}>
        <AppHeader xp={xp} left="close" onLeft={() => router.push("/scan")} freeBadge={me.tier === "free"} />

        <div style={{ padding: "8px 20px 0" }}>
          <div style={{ font: `700 20px/1.3 ${SANS}`, color: C.fg }}>Academy</div>
          <div style={{ font: `400 10.5px ${MONO}`, color: C.muted, marginTop: 3 }}>Each lesson +100 XP, knowledge is the only shortcut</div>
        </div>

        {/* Search + filters (client-side, instant, no server round-trip) */}
        <div style={{ padding: "12px 16px 0", display: "flex", flexDirection: "column", gap: 8 }}>
          <input
            value={filter.q}
            onChange={(e) => setFilter((f) => ({ ...f, q: e.target.value }))}
            placeholder="Search lessons, topics, tags"
            aria-label="Search lessons"
            style={{ width: "100%", boxSizing: "border-box", background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: "10px 12px", font: `400 12px ${SANS}`, color: C.fg }}
          />
          <div style={{ display: "flex", gap: 6, overflowX: "auto", paddingBottom: 2 }}>
            {types.map((t) => (
              <button key={t} type="button" style={chip(filter.type === t)} onClick={() => setFilter((f) => ({ ...f, type: t }))}>
                {t === "all" ? "All types" : t}
              </button>
            ))}
            <span style={{ flex: "none", width: 1, background: C.border, margin: "2px 4px" }} />
            {states.map((s) => (
              <button key={s} type="button" style={chip(filter.state === s)} onClick={() => setFilter((f) => ({ ...f, state: s }))}>
                {s === "all" ? "All" : s}
              </button>
            ))}
          </div>
        </div>

        {/* Card grid: 1 column on a phone, reflow to multi-column on desktop */}
        <div style={{ margin: "14px 16px 0", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))", gap: 10 }}>
          {visible.map((l) => {
            const b = badge(l);
            const highlighted = focus === l.slug;
            const st = lessonState(l);
            return (
              <button
                key={l.slug}
                id={l.slug}
                type="button"
                onClick={() => router.push(`/academy/${l.slug}`)}
                style={{
                  scrollMarginTop: 16,
                  textAlign: "left",
                  background: C.panel,
                  border: `1px solid ${highlighted ? C.green : "rgba(233,238,243,.08)"}`,
                  boxShadow: highlighted ? "0 0 18px rgba(31,178,134,.15)" : "none",
                  borderRadius: 12,
                  padding: "14px 15px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                  cursor: "pointer",
                  opacity: st === "locked" ? 0.78 : 1,
                  minHeight: 128,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                  <span style={{ font: `600 8px ${MONO}`, letterSpacing: 1, color: C.muted, border: `1px solid ${C.border}`, borderRadius: 4, padding: "2px 6px" }}>
                    {l.content_type === "video" ? "▶ VIDEO" : "TEXT"}
                  </span>
                  <span style={{ font: `600 11px ${MONO}`, color: st === "locked" ? C.amber : st === "completed" ? C.muted : C.green }}>
                    {st === "locked" ? "🔒" : st === "completed" ? "↻" : "OPEN"}
                  </span>
                </div>
                <span style={{ font: `600 13px/1.35 ${SANS}`, color: C.fg }}>{l.title}</span>
                <span style={{ font: `400 10.5px/1.5 ${SANS}`, color: C.muted, flex: 1 }}>{l.description}</span>
                <span style={{ font: `400 9px ${MONO}`, color: b.color }}>{highlighted ? "◉ FROM TOOLTIP · " : ""}{b.text}</span>
              </button>
            );
          })}
          {visible.length === 0 && (
            <div style={{ gridColumn: "1 / -1", font: `400 11px ${MONO}`, color: C.muted, padding: 24, textAlign: "center" }}>
              No lessons match this search or filter.
            </div>
          )}
        </div>

        <div style={{ padding: "14px 20px 0", font: `400 9.5px/1.5 ${MONO}`, color: C.muted, textAlign: "center" }}>
          {me.subscription_status === "trial" ? "Included in your Pro trial, full library open for 14 days." : "Ranks unlock bonus lessons, orthogonal to your plan."}
        </div>
        <div style={{ marginTop: "auto" }}>
          <Disclaimer />
        </div>
      </div>
    </main>
  );
}
