// Pure-logic unit tests for Stage 5 notification helpers.
// Run: node --test --experimental-strip-types tests/notifications.unit.test.ts
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  formatBadge,
  shouldPlaySound,
  shouldVibrate,
  togglePref,
  unreadIds,
  vibrateSafe,
} from "../src/lib/notifications.ts";
import type { NotificationPrefs } from "../src/lib/app/types.ts";

const PREFS: NotificationPrefs = {
  inapp_enabled: true,
  sound_enabled: true,
  vibration_enabled: true,
  email_product: true,
  email_broadcast: true,
};

// ── badge render + 9+ cap (D-N3) ──────────────────────────────────────────────
test("formatBadge: empty at zero, plain under ten, capped at 9+", () => {
  assert.equal(formatBadge(0), "");
  assert.equal(formatBadge(-3), "");
  assert.equal(formatBadge(1), "1");
  assert.equal(formatBadge(9), "9");
  assert.equal(formatBadge(10), "9+");
  assert.equal(formatBadge(250), "9+");
});

// ── prefs toggle wiring ───────────────────────────────────────────────────────
test("togglePref flips exactly one key and is immutable", () => {
  const next = togglePref(PREFS, "sound_enabled");
  assert.equal(next.sound_enabled, false);
  assert.equal(next.vibration_enabled, true); // untouched
  assert.equal(PREFS.sound_enabled, true); // original unchanged
});

// ── vibration: fires where supported, graceful no-op otherwise (D-N4) ─────────
test("vibrateSafe fires when navigator.vibrate exists", () => {
  let called: number | number[] | null = null;
  const nav = { vibrate: (p: number | number[]) => { called = p; return true; } };
  assert.equal(vibrateSafe(30, nav), true);
  assert.equal(called, 30);
});

test("vibrateSafe is a no-op when vibrate is unsupported (iOS Safari path)", () => {
  assert.equal(vibrateSafe(30, {}), false); // no vibrate method
  assert.doesNotThrow(() => vibrateSafe(30, {}));
});

// ── arrival feedback gating ───────────────────────────────────────────────────
test("arrival feedback requires in-app on AND the channel on", () => {
  assert.equal(shouldVibrate(PREFS), true);
  assert.equal(shouldPlaySound(PREFS), true);
  assert.equal(shouldVibrate({ ...PREFS, vibration_enabled: false }), false);
  assert.equal(shouldPlaySound({ ...PREFS, sound_enabled: false }), false);
  // in-app off suppresses both channels even if their own flags are on.
  assert.equal(shouldVibrate({ ...PREFS, inapp_enabled: false }), false);
  assert.equal(shouldPlaySound({ ...PREFS, inapp_enabled: false }), false);
});

// ── read-marking set ──────────────────────────────────────────────────────────
test("unreadIds selects only the unread rows", () => {
  const ids = unreadIds([
    { id: 1, read_at: null },
    { id: 2, read_at: "2026-07-14T00:00:00Z" },
    { id: 3, read_at: undefined },
  ]);
  assert.deepEqual(ids, [1, 3]);
});
