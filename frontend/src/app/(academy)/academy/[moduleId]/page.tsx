"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { apiFetch } from "@/lib/api";
import { termsByAcademy, type AcademyTerm } from "@/lib/onboarding/concepts";
import { C } from "@/lib/onboarding/types";
import { useMe } from "@/lib/app/session";
import type { AcademyModule, AcademyResponse } from "@/lib/app/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

export default function AcademyModulePage({ params }: { params: Promise<{ moduleId: string }> }) {
  const { moduleId } = use(params);
  const router = useRouter();
  const { me, loading } = useMe();
  const [mod, setMod] = useState<AcademyModule | null>(null);
  const [xp, setXp] = useState(0);
  const [terms, setTerms] = useState<AcademyTerm[]>([]);
  const [completing, setCompleting] = useState(false);

  useEffect(() => {
    if (!me) return;
    setTerms(termsByAcademy(moduleId));
    void apiFetch<AcademyResponse>("/api/academy").then((r) => {
      if (r.ok && r.data) {
        setXp(r.data.xp_total);
        setMod(r.data.modules.find((m) => m.id === moduleId) ?? null);
      }
    });
  }, [me, moduleId]);

  async function complete() {
    if (!mod?.has_lesson || mod.completed) return;
    setCompleting(true);
    const r = await apiFetch<{ xp_awarded: number; completed: boolean }>(`/api/academy/${moduleId}/complete`, { method: "POST" });
    if (r.ok && r.data) {
      setXp((x) => x + r.data!.xp_awarded);
      setMod((m) => (m ? { ...m, completed: true } : m));
    }
    setCompleting(false);
  }

  if (loading || !me) {
    return <main style={{ minHeight: "100vh", background: C.bg }} />;
  }

  if (mod && !mod.unlocked) {
    return (
      <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex", justifyContent: "center" }}>
        <div style={{ width: "100%", maxWidth: 440, display: "flex", flexDirection: "column" }}>
          <AppHeader xp={xp} left="close" onLeft={() => router.push("/academy")} />
          <div style={{ padding: 24, textAlign: "center", font: `400 12px ${MONO}`, color: C.muted }}>
            {mod.rank_unlock != null ? `Bonus module. Unlocks at ${mod.rank_unlock.toLocaleString()} XP.` : "This module is available on Advanced and Pro plans."}
          </div>
          <div style={{ marginTop: "auto" }}><Disclaimer /></div>
        </div>
      </main>
    );
  }

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 440, display: "flex", flexDirection: "column" }}>
        <AppHeader xp={xp} left="close" onLeft={() => router.push("/academy")} />

        <div style={{ padding: "8px 20px 0" }}>
          <div style={{ font: `700 19px/1.3 ${SANS}`, color: C.fg }}>{mod?.title ?? moduleId}</div>
          <div style={{ font: `400 10px ${MONO}`, color: C.muted, marginTop: 3 }}>
            {mod?.has_lesson ? `${mod.minutes} MIN · ${mod.completed ? "COMPLETED" : "+100 XP on completion"}` : "Reference module"}
          </div>
        </div>

        <div style={{ margin: "14px 16px 0", display: "flex", flexDirection: "column", gap: 8 }}>
          {terms.map((t) => (
            <div key={t.id} style={{ background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, padding: "13px 15px", display: "flex", flexDirection: "column", gap: 5 }}>
              <span style={{ font: `600 11.5px ${MONO}`, color: C.green }}>{t.term}</span>
              <span style={{ font: `400 12px/1.6 ${SANS}`, color: C.fg }}>{t.what}</span>
            </div>
          ))}
          {terms.length === 0 && (
            <div style={{ font: `400 11px ${MONO}`, color: C.muted, padding: 12, textAlign: "center" }}>Content is being prepared for this module.</div>
          )}
        </div>

        {mod?.has_lesson && (
          <div style={{ padding: "16px 16px 0" }}>
            <button
              type="button"
              onClick={complete}
              disabled={mod.completed || completing}
              style={{ width: "100%", background: mod.completed ? "none" : C.green, border: mod.completed ? `1px solid ${C.border}` : "none", borderRadius: 8, padding: "12px", font: `600 11px ${MONO}`, color: mod.completed ? C.muted : C.bg, cursor: mod.completed ? "default" : "pointer" }}
            >
              {mod.completed ? "✓ LESSON COMPLETED" : completing ? "Saving…" : "MARK LESSON COMPLETE · +100 XP"}
            </button>
          </div>
        )}

        <div style={{ marginTop: "auto" }}><Disclaimer /></div>
      </div>
    </main>
  );
}
