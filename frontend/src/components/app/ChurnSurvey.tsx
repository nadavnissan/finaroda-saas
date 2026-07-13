"use client";

// Stage 7 exit / churn survey (D-A5). No cancel/downgrade page exists (Stage 3 payments
// blocked), so this is surfaced from Settings as "Cancel plan or leave". One required
// question + optional free text, skippable. Posts to POST /api/churn/survey; admin sees
// it in the console. This does not itself cancel a subscription (payments are blocked).
import { useState } from "react";

import { C } from "@/lib/onboarding/types";
import { apiFetch } from "@/lib/api";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

const REASONS: { value: string; label: string }[] = [
  { value: "too_expensive", label: "Too expensive" },
  { value: "not_enough_value", label: "Not enough value" },
  { value: "too_complex", label: "Too complex" },
  { value: "found_alternative", label: "Found an alternative" },
  { value: "just_exploring", label: "Just exploring" },
  { value: "other", label: "Other" },
];

export function ChurnSurvey() {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [text, setText] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "done">("idle");

  async function submit() {
    if (!reason) return;
    setState("sending");
    await apiFetch("/api/churn/survey", {
      method: "POST",
      body: JSON.stringify({ reason_category: reason, reason_free_text: text.trim() || null }),
    });
    setState("done");
  }

  const ctl: React.CSSProperties = { background: C.bg, color: C.fg, border: `1px solid ${C.border}`, borderRadius: 6, padding: "7px 9px", font: `400 11px ${MONO}`, width: "100%", boxSizing: "border-box" };

  if (state === "done") {
    return <div style={{ font: `400 10px/1.6 ${MONO}`, color: C.green }}>Thanks for the feedback. It helps us improve.</div>;
  }

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)} style={{ alignSelf: "flex-start", background: "none", border: `1px solid ${C.border}`, borderRadius: 8, padding: "8px 12px", font: `600 10px ${MONO}`, color: C.muted, cursor: "pointer" }}>
        Cancel plan or leave
      </button>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ font: `400 10px/1.5 ${MONO}`, color: C.muted }}>Sorry to see you go. What is the main reason?</div>
      <select value={reason} onChange={(e) => setReason(e.target.value)} style={{ ...ctl, color: C.green, font: `600 11px ${MONO}` }}>
        <option value="">Choose a reason</option>
        {REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
      </select>
      <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Anything else? (optional)" rows={2} style={{ ...ctl, font: `400 11px ${SANS}`, resize: "vertical" }} />
      <div style={{ display: "flex", gap: 8 }}>
        <button type="button" onClick={submit} disabled={!reason || state === "sending"} style={{ font: `600 10px ${MONO}`, color: C.bg, background: reason ? C.green : C.border, borderRadius: 8, padding: "8px 14px", border: "none", cursor: reason ? "pointer" : "default" }}>
          {state === "sending" ? "Sending" : "Submit"}
        </button>
        <button type="button" onClick={() => setOpen(false)} style={{ font: `600 10px ${MONO}`, color: C.muted, background: "none", border: `1px solid ${C.border}`, borderRadius: 8, padding: "8px 14px", cursor: "pointer" }}>
          Skip
        </button>
      </div>
    </div>
  );
}
