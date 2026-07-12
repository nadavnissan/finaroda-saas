"use client";

import { useState } from "react";

import { getTerm } from "@/lib/onboarding/concepts";
import { C, type PassCheck } from "@/lib/onboarding/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";

// "Why PASS" popover on the PASS chip: one line per top passed check, labelled from
// the locked concept content (no new financial copy invented). Clamped + tap-outside.
export function WhyPass({ checks }: { checks: PassCheck[] }) {
  const [open, setOpen] = useState<{ left: number; top: number } | null>(null);
  if (!checks?.length) return null;

  function toggle(e: React.MouseEvent<HTMLButtonElement>) {
    if (open) {
      setOpen(null);
      return;
    }
    const r = e.currentTarget.getBoundingClientRect();
    const vw = typeof window !== "undefined" ? window.innerWidth : 360;
    setOpen({ left: Math.max(8, Math.min(r.left, vw - 232)), top: r.bottom + 6 });
  }

  return (
    <span style={{ position: "relative" }}>
      <button
        type="button"
        onClick={toggle}
        style={{ background: "none", border: "none", padding: 0, marginLeft: 6, color: C.muted, cursor: "help", fontFamily: MONO, fontSize: 10, borderBottom: `1px dotted ${C.muted}` }}
      >
        Why PASS?
      </button>
      {open && (
        <>
          <span onClick={() => setOpen(null)} style={{ position: "fixed", inset: 0, zIndex: 49 }} />
          <span
            role="tooltip"
            style={{
              position: "fixed",
              left: open.left,
              top: open.top,
              zIndex: 50,
              width: 224,
              maxWidth: "calc(100vw - 16px)",
              background: C.panel,
              border: `1px solid ${C.green}`,
              borderRadius: 8,
              padding: 12,
              textAlign: "left",
              fontFamily: MONO,
              fontSize: 11,
              color: C.fg,
              boxShadow: "0 8px 24px rgba(0,0,0,0.55)",
            }}
          >
            <strong style={{ color: C.green, display: "block", marginBottom: 6 }}>Top passed checks</strong>
            {checks.map((c) => (
              <span key={c.id} style={{ display: "flex", justifyContent: "space-between", padding: "3px 0" }}>
                <span>{getTerm(c.id)?.term ?? c.id}</span>
                <span style={{ color: c.pass ? C.green : C.red }}>{c.pass ? "PASS" : "FAIL"}</span>
              </span>
            ))}
          </span>
        </>
      )}
    </span>
  );
}
