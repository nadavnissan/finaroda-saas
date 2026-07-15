"use client";

// F16 Market Narrative card. Renders the resolved DRAFT narrative for the current scan,
// with concept terms wired to their Concept Tooltip. Position: after the ring/list, before
// the Blueprint. Free = paid (no gating). The card is descriptive only, never advice, and
// always ends with the disclaimer line. DRAFT copy is a placeholder; the final mentor copy
// is a later content-only swap (locked-file flow).

import { Fragment, type ReactNode } from "react";

import { ConceptTooltip } from "@/components/onboarding/ConceptTooltip";
import { C } from "@/lib/onboarding/types";
import type { NarrativeResult } from "@/lib/scan/narrative";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

const _MARKER = /\[\[([a-z0-9_]+)\|([^\]]+)\]\]/g;

// Turn "[[regime|regime]] check" into text with an inline Concept Tooltip on the term.
function renderCopy(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0;
  let key = 0;
  let m: RegExpExecArray | null;
  _MARKER.lastIndex = 0;
  while ((m = _MARKER.exec(text)) !== null) {
    if (m.index > last) nodes.push(<Fragment key={key++}>{text.slice(last, m.index)}</Fragment>);
    nodes.push(<ConceptTooltip key={key++} id={m[1]} label={m[2]} />);
    last = m.index + m[0].length;
  }
  if (last < text.length) nodes.push(<Fragment key={key++}>{text.slice(last)}</Fragment>);
  return nodes;
}

export function MarketNarrative({ result }: { result: NarrativeResult | null }) {
  if (!result) return null;
  // The "DRAFT." governance marker lives in the locked file; the card shows a DRAFT chip
  // instead of the literal prefix so the copy reads cleanly.
  const body = result.text.replace(/^DRAFT\.\s*/, "");
  return (
    <div style={{ margin: "12px 16px 0", background: C.panel, border: `1px solid rgba(233,238,243,.1)`, borderRadius: 14, padding: "13px 15px", display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ font: `600 8.5px ${MONO}`, letterSpacing: 2, color: C.muted }}>MARKET NARRATIVE</span>
        <span style={{ font: `600 7.5px ${MONO}`, letterSpacing: 1, color: C.amber, border: `1px solid rgba(224,145,63,.4)`, borderRadius: 3, padding: "1px 5px" }}>DRAFT</span>
      </div>
      <div style={{ font: `400 13px ${SANS}`, color: C.fg, lineHeight: 1.6 }}>{renderCopy(body)}</div>
      <div style={{ font: `400 9px ${MONO}`, color: C.muted }}>{result.disclaimer}</div>
    </div>
  );
}
