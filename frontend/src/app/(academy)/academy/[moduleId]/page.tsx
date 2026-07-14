"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { VideoEmbed } from "@/components/academy/VideoEmbed";
import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import { useMe } from "@/lib/app/session";
import type { AcademyLesson, AcademyResponse, LessonContent } from "@/lib/app/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

// Render the seeded markdown-ish body (## heading + paragraphs). Content is server-served
// (gated) so a locked lesson never reaches this render path.
function Body({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/).filter((b) => b.trim());
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {blocks.map((b, i) =>
        b.startsWith("## ") ? (
          <div key={i} style={{ font: `600 12px ${MONO}`, color: C.green, marginTop: i ? 6 : 0 }}>{b.slice(3).trim()}</div>
        ) : (
          <div key={i} style={{ font: `400 12px/1.65 ${SANS}`, color: C.fg }}>{b.trim()}</div>
        ),
      )}
      {blocks.length === 0 && (
        <div style={{ font: `400 11px ${MONO}`, color: C.muted }}>Content is being prepared for this lesson.</div>
      )}
    </div>
  );
}

export default function AcademyLessonPage({ params }: { params: Promise<{ moduleId: string }> }) {
  const { moduleId } = use(params);
  const router = useRouter();
  const { me, loading } = useMe();
  const [lesson, setLesson] = useState<AcademyLesson | null>(null);
  const [content, setContent] = useState<LessonContent | null>(null);
  const [xp, setXp] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [completing, setCompleting] = useState(false);

  useEffect(() => {
    if (!me) return;
    void apiFetch<AcademyResponse>("/api/academy").then((r) => {
      if (r.ok && r.data) {
        setXp(r.data.xp_total);
        const l = r.data.modules.find((m) => m.slug === moduleId) ?? null;
        setLesson(l);
        setCompleted(l?.completed ?? false);
        if (l?.unlocked) {
          void apiFetch<LessonContent>(`/api/academy/${moduleId}`).then((c) => {
            if (c.ok && c.data) setContent(c.data);
          });
        }
      }
    });
  }, [me, moduleId]);

  async function complete() {
    if (!lesson?.awards_xp || completed) return;
    setCompleting(true);
    const r = await apiFetch<{ xp_awarded: number; completed: boolean }>(`/api/academy/${moduleId}/complete`, { method: "POST" });
    if (r.ok && r.data) {
      setXp((x) => x + r.data!.xp_awarded);
      setCompleted(true);
    }
    setCompleting(false);
  }

  if (loading || !me) {
    return <main style={{ minHeight: "100vh", background: C.bg }} />;
  }

  const locked = lesson != null && !lesson.unlocked;

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 640, display: "flex", flexDirection: "column" }}>
        <AppHeader xp={xp} left="close" onLeft={() => router.push("/academy")} />

        {locked ? (
          <div style={{ padding: 24, textAlign: "center", font: `400 12px ${MONO}`, color: C.muted }}>
            {lesson?.lock_reason ?? "This lesson is locked."}
          </div>
        ) : (
          <>
            <div style={{ padding: "8px 20px 0" }}>
              <div style={{ font: `700 19px/1.3 ${SANS}`, color: C.fg }}>{lesson?.title ?? content?.title ?? moduleId}</div>
              <div style={{ font: `400 10px ${MONO}`, color: C.muted, marginTop: 3 }}>
                {lesson?.duration_minutes ?? 0} MIN · {lesson?.content_type === "video" ? "VIDEO" : "READ"} · {completed ? "COMPLETED" : lesson?.awards_xp ? "+100 XP on completion" : "Reference lesson"}
              </div>
            </div>

            <div style={{ margin: "14px 16px 0", display: "flex", flexDirection: "column", gap: 12 }}>
              {content?.content_type === "video" && content.video_url && (
                <VideoEmbed url={content.video_url} title={content.title} />
              )}
              <div style={{ background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, padding: "15px 16px" }}>
                <Body text={content?.body ?? ""} />
              </div>
            </div>

            {lesson?.awards_xp && (
              <div style={{ padding: "16px 16px 0" }}>
                <button
                  type="button"
                  onClick={complete}
                  disabled={completed || completing}
                  style={{ width: "100%", background: completed ? "none" : C.green, border: completed ? `1px solid ${C.border}` : "none", borderRadius: 8, padding: "12px", font: `600 11px ${MONO}`, color: completed ? C.muted : C.bg, cursor: completed ? "default" : "pointer" }}
                >
                  {completed ? "✓ LESSON COMPLETED" : completing ? "Saving…" : "MARK LESSON COMPLETE · +100 XP"}
                </button>
              </div>
            )}
          </>
        )}

        <div style={{ marginTop: "auto" }}><Disclaimer /></div>
      </div>
    </main>
  );
}
