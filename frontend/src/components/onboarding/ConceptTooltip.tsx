"use client";

import { useState } from "react";

import { getConcept } from "@/lib/onboarding/concepts";
import { C } from "@/lib/onboarding/types";

// Dotted-underline term → bubble: what it measures (from the content file, Nadav-
// supplied) + what it means here-right-now (contextual, passed by the caller) +
// a link to the full Academy lesson (F6). Applies retroactively to every term.
export function ConceptTooltip({ id, hereRightNow }: { id: string; hereRightNow?: string }) {
  const [open, setOpen] = useState(false);
  const concept = getConcept(id);

  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        style={{
          background: "none",
          border: "none",
          padding: 0,
          cursor: "help",
          color: "inherit",
          font: "inherit",
          borderBottom: `1px dotted ${C.muted}`,
        }}
      >
        {concept.term}
      </button>
      {open && (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            left: 0,
            top: "1.6em",
            zIndex: 50,
            width: 240,
            background: C.panel,
            border: `1px solid ${C.green}`,
            borderRadius: 8,
            padding: 12,
            textAlign: "left",
            fontFamily: "system-ui, sans-serif",
            fontSize: 12,
            color: C.fg,
            boxShadow: "0 6px 20px rgba(0,0,0,0.5)",
          }}
        >
          <strong style={{ color: C.green }}>{concept.term}</strong>
          <span style={{ display: "block", marginTop: 6, color: C.fg }}>
            {concept.whatItMeasures || "Plain-language definition — sourced from the Academy (coming soon)."}
          </span>
          {hereRightNow && (
            <span style={{ display: "block", marginTop: 6, color: C.muted }}>Here, right now: {hereRightNow}</span>
          )}
          <a
            href={concept.academyHref}
            style={{ display: "block", marginTop: 8, color: C.green, textDecoration: "none" }}
          >
            Learn more →
          </a>
        </span>
      )}
    </span>
  );
}
