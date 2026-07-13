"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";
import { useMe } from "@/lib/app/session";
import type { AcademyModule, AcademyResponse } from "@/lib/app/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

function stateChip(m: AcademyModule): { text: string; color: string } {
  if (!m.unlocked) {
    return m.rank_unlock != null
      ? { text: `🔒 BONUS · ${m.rank_unlock.toLocaleString()} XP`, color: C.amber }
      : { text: "🔒 ADVANCED+", color: C.amber };
  }
  if (m.completed) return { text: "✓ COMPLETED · +100 XP", color: C.green };
  if (!m.has_lesson) return { text: `${m.minutes} MIN · READ`, color: C.muted };
  return { text: `${m.minutes} MIN`, color: C.muted };
}

export default function AcademyPage() {
  const router = useRouter();
  const { me, loading } = useMe();
  const [data, setData] = useState<AcademyResponse | null>(null);
  const [xp, setXp] = useState(0);
  const [focus, setFocus] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    void apiFetch<AcademyResponse>("/api/academy").then((r) => {
      if (r.ok && r.data) {
        setData(r.data);
        setXp(r.data.xp_total);
      }
    });
    // Deep-link from a Concept Tooltip: /academy#<academy_id> highlights that module.
    if (typeof window !== "undefined" && window.location.hash) {
      const id = window.location.hash.slice(1);
      setFocus(id);
      setTimeout(() => document.getElementById(id)?.scrollIntoView({ block: "center" }), 60);
    }
  }, [me]);

  if (loading || !me || !data) {
    return <main style={{ minHeight: "100vh", background: C.bg }} />;
  }

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, fontFamily: SANS, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 440, display: "flex", flexDirection: "column" }}>
        <AppHeader xp={xp} left="close" onLeft={() => router.push("/scan")} freeBadge={me.tier === "free"} />

        <div style={{ padding: "8px 20px 0" }}>
          <div style={{ font: `700 20px/1.3 ${SANS}`, color: C.fg }}>Academy</div>
          <div style={{ font: `400 10.5px ${MONO}`, color: C.muted, marginTop: 3 }}>Each lesson +100 XP · knowledge is the only shortcut</div>
        </div>

        <div style={{ margin: "14px 16px 0", display: "flex", flexDirection: "column", gap: 8 }}>
          {data.modules.map((m) => {
            const chip = stateChip(m);
            const highlighted = focus === m.id;
            return (
              <button
                key={m.id}
                id={m.id}
                type="button"
                onClick={() => router.push(`/academy/${m.id}`)}
                style={{
                  scrollMarginTop: 16,
                  textAlign: "left",
                  background: C.panel,
                  border: `1px solid ${highlighted ? C.green : "rgba(233,238,243,.08)"}`,
                  boxShadow: highlighted ? "0 0 18px rgba(31,178,134,.15)" : "none",
                  borderRadius: 10,
                  padding: "13px 14px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  cursor: "pointer",
                  opacity: m.unlocked ? 1 : 0.7,
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <span style={{ font: `600 12.5px ${SANS}`, color: C.fg }}>{m.title}</span>
                  <span style={{ font: `400 9px ${MONO}`, color: chip.color }}>{highlighted ? "◉ OPENED FROM TOOLTIP · " : ""}{chip.text}</span>
                </div>
                <span style={{ font: `600 9px ${MONO}`, color: m.completed ? C.muted : C.green }}>{m.completed ? "↻" : m.unlocked ? "OPEN" : "🔒"}</span>
              </button>
            );
          })}
        </div>

        <div style={{ padding: "12px 20px 0", font: `400 9.5px/1.5 ${MONO}`, color: C.muted, textAlign: "center" }}>
          {me.subscription_status === "trial" ? "Included in your Pro trial, full library open for 14 days." : "Ranks unlock bonus modules, orthogonal to your plan."}
        </div>
        <div style={{ marginTop: "auto" }}>
          <Disclaimer />
        </div>
      </div>
    </main>
  );
}
