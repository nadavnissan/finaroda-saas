"use client";

import type { Blueprint } from "@/lib/scan/types";

function coinDot(bp: Blueprint, onClick: () => void) {
  // Border reflects the SaaS gate (PASS green / WATCH amber); arrow shows direction.
  const gate = bp.passLabel === "PASS" ? "#1FB286" : "#E0913F";
  const dirColor = bp.direction === "long" ? "#1FB286" : "#E0913F";
  const symbol = bp.coin.replace("USDT", "");
  return (
    <button
      key={bp.coin}
      type="button"
      onClick={onClick}
      style={{
        width: 64,
        height: 64,
        borderRadius: "50%",
        border: `2px solid ${gate}`,
        background: "#0b0d12",
        color: "#E9EEF3",
        fontFamily: "monospace",
        fontSize: 12,
        cursor: "pointer",
      }}
    >
      {symbol}
      <div style={{ color: dirColor, fontSize: 11 }}>
        {bp.direction === "long" ? "↑" : "↓"} {bp.score}
      </div>
    </button>
  );
}

// Passers as circles: ring when ≤5, list when >5 (UX.md §3, locked layout).
export function Results({
  passers,
  scanned,
  onOpen,
}: {
  passers: Blueprint[];
  scanned: number;
  onOpen: (bp: Blueprint) => void;
}) {
  const layout: React.CSSProperties =
    passers.length <= 5
      ? { display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }
      : { display: "flex", flexDirection: "column", gap: 8, alignItems: "center" };

  return (
    <div>
      <div style={{ fontFamily: "monospace", color: "#8593A2", marginBottom: 10 }}>
        {passers.length} PASS · {scanned} SCANNED
      </div>
      <div style={layout}>{passers.map((bp) => coinDot(bp, () => onOpen(bp)))}</div>
    </div>
  );
}

// Empty state (F1b) — the skip is the edge. Positive, never a failure.
export function EmptyState({ disciplinedDays }: { disciplinedDays: number }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ color: "#1FB286", fontSize: 32 }}>✓</div>
      <p>No setups pass right now.</p>
      <small style={{ color: "#8593A2" }}>Most days are skip days, and the skip is the edge.</small>
      <div style={{ marginTop: 8, fontFamily: "monospace", color: "#5c6672" }}>
        Disciplined · {disciplinedDays} skip-aware scans
      </div>
      <small style={{ display: "block", color: "#5c6672" }}>
        The market moves, re-check when it does. Precision, not habit.
      </small>
    </div>
  );
}
