// F16 Market Narrative — deterministic state resolver (mentor-amended 15/07).
//
// HARD RULE (amendment B3): the resolver reads ONLY fields already present in the scan
// payload and performs NO new financial computation. It maps a scan result to exactly one
// state (first match wins, S2 fallback), then fills a date-rotated DRAFT variant.
//
// State -> payload field map (reported in SESSION_HANDOFF):
//   S1 regime_blocked_spike : passLabel, whyNotCheckId==="regime" (all coins), change24h
//   S2 no_setups_quiet      : passLabel (fallback)
//   S3 transition_flicker   : passLabel, ema7SlopePct>0, whyNotCheckId==="regime"
//                             (DEGRADED: no reversal/short-EMA-reclaim flag exists in the
//                              payload, so a positive short-average slope is the proxy)
//   S4 pass_with_context    : passLabel==="PASS", score, riskReward
//   S5 watch_only           : passLabel==="WATCH", score
//   S6 daily_limit_reached  : the quota state (rendered inside the 429 screen, B2)
//
// The resolver is pure and takes the locked narratives data as an argument so it can be
// unit-tested without a JSON import. Coin identity, scores and slopes are the scan's own
// numbers; the resolver never recomputes an indicator or moves a score (RED LINE).

export type PassLabel = "PASS" | "WATCH" | "HIDE";

export interface NarrativeCoin {
  coin: string; // e.g. "LINKUSDT"
  passLabel: PassLabel;
  score: number;
  ema7SlopePct: number;
  riskReward: number | null;
  change24h: number; // percent, already computed by the market fetch
  whyNotCheckId: string | null; // set only when HIDE (e.g. "regime")
}

export interface NarrativeInput {
  coins: NarrativeCoin[];
  unrevealed?: number; // optional; a variant using {unrevealed} is skipped when absent
  date?: Date; // for deterministic variant rotation (defaults to now)
}

export interface NarrativeVariantState {
  id: string;
  variants: string[];
}

export interface NarrativesFile {
  disclaimer: string;
  states: Record<string, NarrativeVariantState>;
}

export interface NarrativeResult {
  stateId: string; // e.g. "regime_blocked_spike"
  code: string; // e.g. "S1"
  variantIndex: number; // index into the ELIGIBLE variants (deterministic)
  text: string; // filled variant, [[concept]] markers intact, no disclaimer
  disclaimer: string;
}

const SPIKE_PCT = 3; // S1: "any coin's 24h move > +3%"
const FLICKER_MIN = 3; // S3: ">= 3 coins show reversal-style readings"

function base(coin: string): string {
  const c = coin.toUpperCase();
  return c.endsWith("USDT") ? c.slice(0, -4) : c;
}

function regimeFailed(c: NarrativeCoin): boolean {
  return c.passLabel !== "PASS" && c.whyNotCheckId === "regime";
}

// UTC day-of-year, so variant rotation is deterministic and timezone-stable.
export function dayOfYear(d: Date): number {
  const start = Date.UTC(d.getUTCFullYear(), 0, 0);
  const today = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  return Math.floor((today - start) / 86400000);
}

const _PLACEHOLDER = /\{([a-z0-9_]+)\}/g;

function placeholders(variant: string): string[] {
  const out: string[] = [];
  let m: RegExpExecArray | null;
  _PLACEHOLDER.lastIndex = 0;
  while ((m = _PLACEHOLDER.exec(variant)) !== null) out.push(m[1]);
  return out;
}

function fill(variant: string, ctx: Record<string, string>): string {
  return variant.replace(_PLACEHOLDER, (_, k) => (k in ctx ? ctx[k] : `{${k}}`));
}

// Pick the date-rotated variant among those whose placeholders the ctx can fill.
function chooseVariant(
  variants: string[],
  ctx: Record<string, string>,
  day: number,
): { text: string; index: number } {
  const keys = new Set(Object.keys(ctx));
  const eligible = variants.filter((v) => placeholders(v).every((p) => keys.has(p)));
  const pool = eligible.length > 0 ? eligible : variants;
  const index = ((day % pool.length) + pool.length) % pool.length;
  return { text: fill(pool[index], ctx), index };
}

function result(
  data: NarrativesFile,
  stateId: string,
  ctx: Record<string, string>,
  day: number,
): NarrativeResult {
  const state = data.states[stateId];
  const { text, index } = chooseVariant(state.variants, ctx, day);
  return { stateId, code: state.id, variantIndex: index, text, disclaimer: data.disclaimer };
}

/**
 * Resolve the ring/list scan result to exactly one narrative state (S1, S3, S4, S5, or the
 * S2 fallback). S6 is resolved separately by resolveDailyLimit (rendered in the 429 screen).
 */
export function resolveNarrative(input: NarrativeInput, data: NarrativesFile): NarrativeResult {
  const coins = input.coins;
  const day = dayOfYear(input.date ?? new Date());
  const scanned = coins.length;
  const passers = coins.filter((c) => c.passLabel === "PASS");
  const watchers = coins.filter((c) => c.passLabel === "WATCH");

  // S4 pass_with_context — a PASS is the headline (mutually exclusive with the 0-PASS states).
  if (passers.length > 0) {
    const top = [...passers].sort((a, b) => b.score - a.score)[0];
    const ctx: Record<string, string> = {
      scanned: String(scanned),
      pass_coins: passers.map((c) => base(c.coin)).join(", "),
      pass_coin: base(top.coin),
      score: String(Math.round(top.score)),
    };
    if (top.riskReward != null) ctx.rr = `${top.riskReward.toFixed(1)} to 1`;
    return result(data, "pass_with_context", ctx, day);
  }

  // ── 0 PASS below. First match wins, in spec order, S2 as the fallback. ──
  const spike = [...coins].sort((a, b) => b.change24h - a.change24h)[0];

  // S1 regime_blocked_spike — every coin regime-failed AND a tempting spike (> +3% / 24h).
  if (scanned > 0 && coins.every(regimeFailed) && spike && spike.change24h > SPIKE_PCT) {
    return result(
      data,
      "regime_blocked_spike",
      { scanned: String(scanned), spike_coin: base(spike.coin), spike_pct: `+${spike.change24h.toFixed(1)}%` },
      day,
    );
  }

  // S3 transition_flicker (DEGRADED) — >= 3 coins with the short average turning up while
  // the regime check still fails. No reversal/short-EMA-reclaim flag exists in the payload,
  // so a positive ema7 slope is the proxy (amendment B3).
  const flicker = coins.filter((c) => c.ema7SlopePct > 0 && regimeFailed(c));
  if (flicker.length >= FLICKER_MIN) {
    return result(
      data,
      "transition_flicker",
      { scanned: String(scanned), flicker_count: String(flicker.length) },
      day,
    );
  }

  // S5 watch_only — nothing passed, but a coin sits in the 82 to 84 watch band.
  if (watchers.length > 0) {
    const top = [...watchers].sort((a, b) => b.score - a.score)[0];
    return result(
      data,
      "watch_only",
      { scanned: String(scanned), watch_coin: base(top.coin), watch_score: String(Math.round(top.score)) },
      day,
    );
  }

  // S2 no_setups_quiet — fallback.
  const ctx: Record<string, string> = { scanned: String(scanned) };
  if (input.unrevealed != null) ctx.unrevealed = String(input.unrevealed);
  return result(data, "no_setups_quiet", ctx, day);
}

/** Resolve the S6 daily-limit narrative (rendered inside the 429 / quota screen, B2). */
export function resolveDailyLimit(
  dailyLimit: number,
  data: NarrativesFile,
  date?: Date,
): NarrativeResult {
  const day = dayOfYear(date ?? new Date());
  return result(data, "daily_limit_reached", { daily_limit: String(dailyLimit) }, day);
}
