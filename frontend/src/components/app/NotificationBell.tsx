"use client";

// Stage 5 bell (D-N3). Lives in the hamburger drawer. Server-authoritative: the badge
// and read-state come from the API, so they survive refresh. Opening the panel marks the
// visible unread items read. Arrival sound/vibration apply only while the app is open and
// only after a first user interaction (autoplay policy, D-N4); both degrade gracefully.
import { useEffect, useRef, useState } from "react";

import { C } from "@/lib/onboarding/types";
import { apiFetch } from "@/lib/api";
import { addBreadcrumb } from "@/lib/breadcrumbs";
import type { NotificationFeed, NotificationItem, NotificationPrefs } from "@/lib/app/types";
import {
  formatBadge,
  shouldPlaySound,
  shouldVibrate,
  unreadIds,
  vibrateSafe,
} from "@/lib/notifications";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

// Sound only after a first interaction (no autoplay-policy fights, D-N4).
let soundUnlocked = false;
if (typeof window !== "undefined") {
  const unlock = () => {
    soundUnlocked = true;
    window.removeEventListener("pointerdown", unlock);
    window.removeEventListener("keydown", unlock);
  };
  window.addEventListener("pointerdown", unlock);
  window.addEventListener("keydown", unlock);
}

function beep(): void {
  if (!soundUnlocked || typeof window === "undefined") return;
  try {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = 660;
    gain.gain.value = 0.04;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.12);
  } catch {
    /* audio not available — silent no-op */
  }
}

export function NotificationBell({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [prefs, setPrefs] = useState<NotificationPrefs | null>(null);
  const prevUnread = useRef(0);
  const prefsRef = useRef<NotificationPrefs | null>(null);
  prefsRef.current = prefs;

  useEffect(() => {
    void apiFetch<NotificationPrefs>("/api/notifications/prefs").then((r) => {
      if (r.ok && r.data) setPrefs(r.data);
    });
  }, []);

  useEffect(() => {
    let alive = true;
    async function load() {
      const r = await apiFetch<NotificationFeed>("/api/notifications");
      if (!alive || !r.ok || !r.data) return;
      setItems(r.data.notifications);
      setUnread(r.data.unread_count);
      // Arrival feedback: only when unread grew while the app is open.
      const p = prefsRef.current;
      if (p && r.data.unread_count > prevUnread.current) {
        if (shouldVibrate(p)) vibrateSafe(30);
        if (shouldPlaySound(p)) beep();
      }
      prevUnread.current = r.data.unread_count;
    }
    void load();
    const id = setInterval(load, 60_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (!next) return;
    addBreadcrumb("notif_open");
    const ids = unreadIds(items);
    if (ids.length === 0) return;
    const r = await apiFetch<{ unread_count: number }>("/api/notifications/read", {
      method: "POST",
      body: JSON.stringify({ ids }),
    });
    if (r.ok && r.data) {
      setUnread(r.data.unread_count);
      prevUnread.current = r.data.unread_count;
    }
    const now = new Date().toISOString();
    setItems((prev) => prev.map((i) => ({ ...i, read_at: i.read_at ?? now })));
  }

  const badge = formatBadge(unread);

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <button
        type="button"
        onClick={toggle}
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 12px",
          background: open ? "rgba(31,178,134,.08)" : "rgba(233,238,243,.03)",
          border: `1px solid ${open ? "rgba(31,178,134,.35)" : "rgba(233,238,243,.08)"}`,
          borderRadius: 10,
          color: C.fg,
          cursor: "pointer",
          font: `600 11px ${SANS}`,
        }}
      >
        <span style={{ position: "relative", font: `400 15px ${MONO}` }}>
          🔔
          {badge && (
            <span
              style={{
                position: "absolute",
                top: -6,
                right: -10,
                minWidth: 15,
                textAlign: "center",
                font: `700 8px ${MONO}`,
                color: C.bg,
                background: C.red,
                borderRadius: 8,
                padding: "1px 4px",
              }}
            >
              {badge}
            </span>
          )}
        </span>
        <span>Notifications</span>
        <span style={{ marginLeft: "auto", font: `400 11px ${MONO}`, color: C.muted }}>{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div
          style={{
            marginTop: 6,
            maxHeight: 260,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {items.length === 0 ? (
            <div style={{ font: `400 10px ${MONO}`, color: C.muted, padding: "10px 12px" }}>
              No notifications yet.
            </div>
          ) : (
            items.map((n) => (
              <button
                key={n.id}
                type="button"
                onClick={() => n.link_path && onNavigate(n.link_path)}
                style={{
                  textAlign: "left",
                  background: C.bg,
                  border: `1px solid rgba(233,238,243,.07)`,
                  borderRadius: 9,
                  padding: "9px 11px",
                  cursor: n.link_path ? "pointer" : "default",
                  display: "flex",
                  flexDirection: "column",
                  gap: 3,
                }}
              >
                <span style={{ font: `600 10.5px ${SANS}`, color: C.fg }}>{n.title}</span>
                <span style={{ font: `400 9.5px/1.5 ${SANS}`, color: C.muted }}>{n.body}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
