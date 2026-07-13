// Stage 5 notification helpers — pure logic, unit-tested (tests/notifications.unit.test.ts).
// Kept free of React/DOM globals so they run under node:test; the browser bits
// (AudioContext beep, navigator.vibrate) are isolated in NotificationBell.tsx.
import type { NotificationPrefs } from "@/lib/app/types";

/** Bell badge label: empty when zero, capped at "9+" (D-N3). */
export function formatBadge(unread: number): string {
  if (unread <= 0) return "";
  return unread > 9 ? "9+" : String(unread);
}

/** Flip one boolean pref, returning a new object (pure — for optimistic UI). */
export function togglePref(
  prefs: NotificationPrefs,
  key: keyof NotificationPrefs,
): NotificationPrefs {
  return { ...prefs, [key]: !prefs[key] };
}

type Vibrator = { vibrate?: (pattern: number | number[]) => boolean };

/** Vibrate where supported; graceful no-op otherwise (e.g. iOS Safari). Returns true
 *  only when a vibration was actually requested. `nav` is injectable for testing. */
export function vibrateSafe(pattern: number | number[] = 30, nav?: Vibrator): boolean {
  const v = nav ?? (typeof navigator !== "undefined" ? (navigator as Vibrator) : undefined);
  if (v && typeof v.vibrate === "function") {
    v.vibrate(pattern);
    return true;
  }
  return false;
}

/** Arrival feedback is gated by in-app being on AND the specific channel being on (D-N4). */
export function shouldVibrate(prefs: NotificationPrefs): boolean {
  return prefs.inapp_enabled && prefs.vibration_enabled;
}
export function shouldPlaySound(prefs: NotificationPrefs): boolean {
  return prefs.inapp_enabled && prefs.sound_enabled;
}

/** Ids of the currently-unread items — the set the bell marks read on open. */
export function unreadIds(items: { id: number; read_at?: string | null }[]): number[] {
  return items.filter((i) => !i.read_at).map((i) => i.id);
}
