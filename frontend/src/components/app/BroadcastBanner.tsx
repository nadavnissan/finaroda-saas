"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";
const DISMISS_KEY = "finaroda_banner_dismissed";

interface Banner {
  id: number;
  title: string;
  body: string;
}

// In-app broadcast banner (B7d). Dismissible, and rendered inline at the top of a
// screen so it never covers the SCAN button or the disclaimer. Dismissal is per-banner
// (localStorage) so it does not nag on every open.
export function BroadcastBanner() {
  const [banner, setBanner] = useState<Banner | null>(null);

  useEffect(() => {
    void apiFetch<{ banner: Banner | null }>("/api/broadcasts/active").then((r) => {
      const b = r.ok ? r.data?.banner ?? null : null;
      if (!b) return;
      if (typeof window !== "undefined" && localStorage.getItem(DISMISS_KEY) === String(b.id)) return;
      setBanner(b);
    });
  }, []);

  if (!banner) return null;

  return (
    <div style={{ padding: "0 16px", marginTop: 6 }}>
      <div
        style={{
          background: "rgba(31,178,134,.09)",
          border: `1px solid rgba(31,178,134,.4)`,
          borderRadius: 9,
          padding: "9px 11px",
          display: "flex",
          gap: 8,
          alignItems: "flex-start",
        }}
      >
        <span style={{ fontSize: 11 }} aria-hidden>
          📣
        </span>
        <span style={{ flex: 1, font: `400 11px/1.5 ${SANS}`, color: C.fg }}>{banner.body}</span>
        <button
          type="button"
          aria-label="Dismiss"
          onClick={() => {
            if (typeof window !== "undefined") localStorage.setItem(DISMISS_KEY, String(banner.id));
            setBanner(null);
          }}
          style={{ background: "none", border: "none", cursor: "pointer", color: C.muted, font: `400 11px ${MONO}` }}
        >
          ✕
        </button>
      </div>
    </div>
  );
}
