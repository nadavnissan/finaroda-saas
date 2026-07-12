"use client";

import { useState } from "react";

import { getTerm, renderNow } from "@/lib/onboarding/concepts";
import { C } from "@/lib/onboarding/types";

interface Pos {
  left: number;
  top: number;
  placement: "below" | "above";
}

// Dotted-underline term. Tap opens a bubble: what it measures (locked content) +
// what it means here-right-now (rendered from ctx) + Learn more (Academy module).
// The bubble is viewport-clamped and flips above when there is no room below, so
// it is never clipped on mobile. Closes via the X button or a tap outside.
export function ConceptTooltip({
  id,
  ctx,
  label,
  pill,
}: {
  id: string;
  ctx?: Record<string, unknown>;
  label?: string; // custom trigger text (e.g. a chart annotation "Spike day")
  pill?: boolean; // render the trigger as a small pill (chart annotations)
}) {
  const [pos, setPos] = useState<Pos | null>(null);
  const term = getTerm(id);
  if (!term) return <span>{label ?? id}</span>;

  const W = 260;
  const EST_H = 180;

  function open(e: React.MouseEvent<HTMLButtonElement>) {
    if (pos) {
      setPos(null);
      return;
    }
    const r = e.currentTarget.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const left = Math.max(8, Math.min(r.left, vw - W - 8));
    const roomBelow = vh - r.bottom;
    const placement: Pos["placement"] = roomBelow < EST_H && r.top > EST_H ? "above" : "below";
    const top = placement === "below" ? r.bottom + 6 : Math.max(8, r.top - EST_H - 6);
    setPos({ left, top, placement });
  }

  const nowLine = ctx ? renderNow(term.now, ctx) : "";

  return (
    <span style={{ position: "relative", display: "inline" }}>
      <button
        type="button"
        onClick={open}
        aria-expanded={pos != null}
        style={
          pill
            ? {
                background: C.panel,
                border: `1px solid ${C.green}`,
                borderRadius: 10,
                padding: "1px 7px",
                fontSize: 10,
                fontFamily: "monospace",
                color: C.green,
                cursor: "pointer",
                whiteSpace: "nowrap",
              }
            : {
                background: "none",
                border: "none",
                padding: 0,
                cursor: "help",
                color: "inherit",
                font: "inherit",
                borderBottom: `1px dotted ${C.muted}`,
              }
        }
      >
        {label ?? term.term}
      </button>
      {pos && (
        <>
          <span
            onClick={() => setPos(null)}
            style={{ position: "fixed", inset: 0, zIndex: 49, background: "transparent" }}
          />
          <span
            role="tooltip"
            style={{
              position: "fixed",
              left: pos.left,
              top: pos.top,
              zIndex: 50,
              width: W,
              maxWidth: "calc(100vw - 16px)",
              background: C.panel,
              border: `1px solid ${C.green}`,
              borderRadius: 8,
              padding: "12px 12px 10px",
              textAlign: "left",
              fontFamily: "system-ui, sans-serif",
              fontSize: 12,
              lineHeight: 1.45,
              color: C.fg,
              boxShadow: "0 8px 24px rgba(0,0,0,0.55)",
            }}
          >
            <button
              type="button"
              onClick={() => setPos(null)}
              aria-label="Close"
              style={{
                position: "absolute",
                top: 6,
                right: 8,
                background: "none",
                border: "none",
                color: C.muted,
                cursor: "pointer",
                fontSize: 14,
                lineHeight: 1,
              }}
            >
              ×
            </button>
            <strong style={{ color: C.green, display: "block", paddingRight: 16 }}>{term.term}</strong>
            <span style={{ display: "block", marginTop: 6 }}>{term.what}</span>
            {nowLine && <span style={{ display: "block", marginTop: 6, color: C.muted }}>{nowLine}</span>}
            <a
              href={`/academy#${term.academy}`}
              style={{ display: "block", marginTop: 8, color: C.green, textDecoration: "none" }}
            >
              Learn more
            </a>
          </span>
        </>
      )}
    </span>
  );
}
