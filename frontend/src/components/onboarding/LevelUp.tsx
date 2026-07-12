"use client";

import { useEffect } from "react";

import { vibrateLevelUp } from "@/lib/onboarding/haptics";
import { C } from "@/lib/onboarding/types";
import { two } from "@/lib/onboarding/xp";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";

// Rank-up celebration: short vibration + terminal animation. Mounted ONLY when a
// rank threshold is crossed (crossedLevel), never on ordinary XP gains.
export function LevelUp({ level, name, onDone }: { level: number; name: string; onDone: () => void }) {
  useEffect(() => {
    vibrateLevelUp();
    const t = window.setTimeout(onDone, 1900);
    return () => window.clearTimeout(t);
  }, [onDone]);

  return (
    <div
      onClick={onDone}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(11,13,18,0.72)",
      }}
    >
      <div
        className="onb-levelup"
        style={{
          textAlign: "center",
          fontFamily: MONO,
          color: C.green,
          border: `1px solid ${C.green}`,
          borderRadius: 14,
          padding: "22px 34px",
          background: C.panel,
          boxShadow: `0 0 40px ${C.green}`,
        }}
      >
        <div style={{ fontSize: 10, letterSpacing: 3, color: C.muted }}>RANK UP</div>
        <div style={{ fontSize: 30, fontWeight: 700, margin: "6px 0" }}>LVL {two(level)}</div>
        <div style={{ fontSize: 13, letterSpacing: 2 }}>{name.toUpperCase()}</div>
      </div>
    </div>
  );
}
