"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { C } from "@/lib/onboarding/types";
import { apiFetch } from "@/lib/api";

// FX7: cross-component signal that the bell panel was opened (items marked read), so a
// mounted AppHeader can clear its hamburger dot immediately without a shared store.
export const NOTIF_READ_EVENT = "finaroda:notifications-read";

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
  // FX7: unread-notification hint. Only the hamburger (menu) header carries it — the
  // bell lives in the drawer, so the dot tells the user there is something to open.
  // Reuses the same server-authoritative unread count the bell uses; clears when the
  // bell panel is opened (NOTIF_READ_EVENT) or the count comes back zero.
  const [hasUnread, setHasUnread] = useState(false);
  useEffect(() => {
    if (left !== "menu") return;
    let alive = true;
    void apiFetch<{ unread_count: number }>("/api/notifications").then((r) => {
      if (alive && r.ok && r.data) setHasUnread(r.data.unread_count > 0);
    });
    const clear = () => setHasUnread(false);
    window.addEventListener(NOTIF_READ_EVENT, clear);
    return () => {
      alive = false;
      window.removeEventListener(NOTIF_READ_EVENT, clear);
    };
  }, [left]);
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
        aria-label={left === "menu" ? (hasUnread ? "Open menu, unread notifications" : "Open menu") : "Close"}
        style={{ position: "relative", background: "none", border: "none", cursor: "pointer", color: C.muted, font: `400 16px ${MONO}`, padding: 0 }}
      >
        {left === "menu" ? "≡" : "✕"}
        {left === "menu" && hasUnread && (
          <span
            aria-hidden
            style={{ position: "absolute", top: -2, right: -6, width: 7, height: 7, background: C.green, borderRadius: "50%", boxShadow: `0 0 6px ${C.green}` }}
          />
        )}
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
