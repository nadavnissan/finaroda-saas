"use client";

import { useRouter } from "next/navigation";

import { C } from "@/lib/onboarding/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

// Consistent post-auth header (B1/B2/B3). Left slot is either the hamburger (opens
// the nav drawer) or a close ✕ (dismisses a modal screen). Right slot is the compact
// LevelMeter chip (XP). Kills the old per-page header.
export function AppHeader({
  xp,
  left = "menu",
  onLeft,
  freeBadge = false,
  trialBadge = false,
}: {
  xp: number;
  left?: "menu" | "close";
  onLeft?: () => void;
  freeBadge?: boolean;
  trialBadge?: boolean;
}) {
  const router = useRouter();
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "16px 18px 10px",
      }}
    >
      <button
        type="button"
        onClick={onLeft}
        aria-label={left === "menu" ? "Open menu" : "Close"}
        style={{ background: "none", border: "none", cursor: "pointer", color: C.muted, font: `400 16px ${MONO}`, padding: 0 }}
      >
        {left === "menu" ? "≡" : "✕"}
      </button>
      <button
        type="button"
        onClick={() => router.push("/scan")}
        aria-label="Go to scan"
        style={{ background: "none", border: "none", cursor: "pointer", padding: 0, font: `700 13px ${SANS}`, letterSpacing: 4, color: C.fg }}
      >
        FINARODA
      </button>
      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {trialBadge && (
          <span style={{ font: `700 9px ${MONO}`, color: C.amber, border: `1px solid rgba(224,145,63,.5)`, borderRadius: 4, padding: "3px 7px" }}>
            TRIAL
          </span>
        )}
        {freeBadge && !trialBadge && (
          <span style={{ font: `600 9px ${MONO}`, color: C.muted, border: `1px solid ${C.border}`, borderRadius: 4, padding: "3px 7px" }}>
            FREE
          </span>
        )}
        <span style={{ display: "flex", alignItems: "center", gap: 5, font: `600 10px ${MONO}`, color: C.green }}>
          <span style={{ width: 6, height: 6, background: C.green, borderRadius: 1 }} />
          XP {xp.toLocaleString()}
        </span>
      </span>
    </div>
  );
}

export function Disclaimer() {
  return (
    <div
      style={{
        padding: 12,
        textAlign: "center",
        font: `400 10px ${MONO}`,
        color: C.muted,
        borderTop: `1px solid rgba(233,238,243,.07)`,
      }}
    >
      Analysis, not financial advice.
    </div>
  );
}
