// XP rank ladder (XP_ECONOMY.md v1.0). Pure, dependency-free (unit-tested).
// Ranks unlock knowledge only, never signals. Onboarding tops out at 300 (Level 1).

export interface Rank {
  level: number; // 1..4
  name: string;
  floor: number; // XP at which this rank begins
}

export const RANKS: Rank[] = [
  { level: 1, name: "Strategy Apprentice", floor: 0 },
  { level: 2, name: "Risk Manager", floor: 1000 },
  { level: 3, name: "Regime Reader", floor: 3000 },
  { level: 4, name: "Master Strategist", floor: 8000 },
];

export interface LevelState {
  level: number;
  name: string;
  floor: number;
  next: Rank | null; // null at the top rank
  progressPct: number; // fill within the current level (0..100)
  toNext: number; // XP remaining to the next rank (0 at top)
}

export function levelFor(xp: number): LevelState {
  let idx = 0;
  for (let i = 0; i < RANKS.length; i++) {
    if (xp >= RANKS[i].floor) idx = i;
  }
  const cur = RANKS[idx];
  const next = idx < RANKS.length - 1 ? RANKS[idx + 1] : null;
  const span = next ? next.floor - cur.floor : 1;
  const into = xp - cur.floor;
  const progressPct = next ? Math.max(0, Math.min(100, Math.round((into / span) * 100))) : 100;
  const toNext = next ? Math.max(0, next.floor - xp) : 0;
  return { level: cur.level, name: cur.name, floor: cur.floor, next, progressPct, toNext };
}

// True only when a rank threshold is crossed (drives the level-up celebration).
export function crossedLevel(prevXp: number, newXp: number): boolean {
  return levelFor(newXp).level > levelFor(prevXp).level;
}

export function two(n: number): string {
  return String(n).padStart(2, "0");
}
