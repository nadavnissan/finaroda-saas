"use client";

import { ConceptTooltip } from "@/components/onboarding/ConceptTooltip";
import { C } from "@/lib/onboarding/types";
import type { Blueprint } from "@/lib/scan/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

function CoinDot({ bp, onClick, size }: { bp: Blueprint; onClick: () => void; size: number }) {
  const gate = bp.passLabel === "PASS" ? C.green : C.amber;
  const dirColor = bp.direction === "long" ? C.green : C.red;
  const symbol = bp.coin.replace("USDT", "");
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: C.panel,
        border: `2px solid ${gate}`,
        boxShadow: `0 0 38px rgba(31,178,134,.20)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 3,
        cursor: "pointer",
      }}
    >
      <span style={{ font: `700 ${Math.round(size / 7.7)}px ${MONO}`, color: C.fg }}>{symbol}</span>
      <span style={{ font: `600 12px ${MONO}`, color: dirColor }}>
        {bp.direction === "long" ? "↑ LONG" : "↓ SHORT"}
      </span>
      <span style={{ font: `600 11px ${MONO}`, color: gate }}>
        {bp.score} · {bp.passLabel}
      </span>
    </button>
  );
}

// Scan results (B1c). Passers as a ring (≤5) or list (>5). Every OTHER scanned coin
// is tappable too (E7b → why-not). First-scan-of-day XP chip only when the server
// awarded it (D3). "New scan" returns to the controls screen - never an auto re-scan.
export function Results({
  passers,
  nonPassers,
  scanned,
  timestamp,
  xpAwarded,
  onOpen,
  onOpenWhyNot,
  onNewScan,
}: {
  passers: Blueprint[];
  nonPassers: Blueprint[];
  scanned: number;
  timestamp: string;
  xpAwarded: boolean;
  onOpen: (bp: Blueprint) => void;
  onOpenWhyNot: (bp: Blueprint) => void;
  onNewScan: () => void;
}) {
  const single = passers.length === 1;
  const ring = passers.length <= 5;
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
      {xpAwarded && (
        <div style={{ display: "flex", justifyContent: "center", paddingTop: 8 }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              background: "rgba(31,178,134,.12)",
              border: `1px solid rgba(31,178,134,.5)`,
              borderRadius: 20,
              padding: "5px 13px",
              font: `600 10.5px ${MONO}`,
              color: C.green,
            }}
          >
            +50 XP · FIRST SCAN OF THE DAY
          </span>
        </div>
      )}

      <div style={{ padding: "22px 20px 0", textAlign: "center" }}>
        <div style={{ font: `700 26px ${MONO}`, color: C.fg }}>
          {passers.length}{" "}
          <span style={{ color: C.green }}>
            <ConceptTooltip id="pass_watch" label="PASS" />
          </span>{" "}
          · {scanned} SCANNED
        </div>
        <div style={{ font: `400 11px ${MONO}`, color: C.muted, marginTop: 6 }}>{timestamp} · fresh pull</div>
      </div>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, padding: "8px 20px" }}>
        {passers.length > 0 ? (
          <>
            <div style={ring ? { display: "flex", gap: 14, justifyContent: "center", flexWrap: "wrap" } : { display: "flex", flexDirection: "column", gap: 10, width: "100%", alignItems: "center" }}>
              {passers.map((bp) => (
                <CoinDot key={bp.coin} bp={bp} onClick={() => onOpen(bp)} size={single ? 132 : 96} />
              ))}
            </div>
            <div style={{ font: `400 11px ${MONO}`, color: C.muted }}>tap for the Trading Blueprint</div>
          </>
        ) : (
          <div style={{ font: `400 12px ${SANS}`, color: C.muted, textAlign: "center" }}>
            No coin passed this scan - tap any scanned market below to see why.
          </div>
        )}
        <div style={{ font: `400 10px ${MONO}`, color: C.muted, border: `1px solid rgba(233,238,243,.1)`, borderRadius: 16, padding: "5px 12px" }}>
          <ConceptTooltip id="scan_snapshot" label="market context recorded with this scan" />
        </div>
      </div>

      {nonPassers.length > 0 && (
        <div style={{ padding: "0 16px 6px" }}>
          <div style={{ font: `400 9px ${MONO}`, color: C.muted, textAlign: "center", paddingBottom: 6 }}>
            {nonPassers.length} scanned · tap any to see why it did not pass
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center" }}>
            {nonPassers.map((bp) => (
              <button
                key={bp.coin}
                type="button"
                onClick={() => onOpenWhyNot(bp)}
                style={{ font: `600 9.5px ${MONO}`, color: C.muted, background: C.panel, border: `1px solid ${C.border}`, borderRadius: 14, padding: "5px 11px", cursor: "pointer" }}
              >
                {bp.coin.replace("USDT", "")} · NO PASS
              </button>
            ))}
          </div>
        </div>
      )}

      <div style={{ padding: "10px 20px 4px", textAlign: "center" }}>
        <button
          type="button"
          onClick={onNewScan}
          style={{ font: `500 12px ${MONO}`, color: C.muted, background: "none", border: "none", borderBottom: `1px solid rgba(133,147,162,.5)`, paddingBottom: 2, cursor: "pointer" }}
        >
          ↻ new scan
        </button>
      </div>
    </div>
  );
}

// Empty state (F1b) - the skip is the edge. Positive, never a failure, no scan CTA.
// Discipline is sourced from the user's REAL scan count (no invented skip ratio).
export function EmptyState({ scanCount }: { scanCount: number }) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 18, padding: "0 32px", textAlign: "center" }}>
      <div style={{ width: 64, height: 64, borderRadius: "50%", border: `1.5px solid ${C.green}`, display: "flex", alignItems: "center", justifyContent: "center", color: C.green, fontSize: 26, fontWeight: 600 }}>
        ✓
      </div>
      <div style={{ font: `700 24px ${SANS}`, color: C.fg, lineHeight: 1.3 }}>No setups pass right now</div>
      <div style={{ font: `400 13.5px ${SANS}`, color: C.muted, lineHeight: 1.6 }}>Most days are skip days, and the skip is the edge.</div>
      <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "rgba(31,178,134,.1)", border: `1px solid rgba(31,178,134,.45)`, borderRadius: 20, padding: "7px 16px", font: `600 10.5px ${MONO}`, color: C.green }}>
        <ConceptTooltip id="smart_skip" label={`DISCIPLINED · ${scanCount} SKIP-AWARE SCANS`} />
      </div>
      <div style={{ font: `400 12px ${SANS}`, color: C.muted, lineHeight: 1.6 }}>
        The market moves - re-check when it does.
        <br />
        Precision, not habit.
      </div>
    </div>
  );
}
