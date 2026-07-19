"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import type { MarketContext } from "@finaroda/scoring-engine/scorer.js";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { BillingBanner } from "@/components/app/BillingBanner";
import { BroadcastBanner } from "@/components/app/BroadcastBanner";
import { HorizonSelector, LensSelect, RedLineCaption, RiskStyleSelect } from "@/components/scan/Controls";
import { NavDrawer } from "@/components/scan/NavDrawer";
import { NonPasser } from "@/components/scan/NonPasser";
import { Results, EmptyState } from "@/components/scan/Results";
import { SCAN_STEPS, ScanningLog } from "@/components/scan/ScanningLog";
import { TradingBlueprint } from "@/components/scan/TradingBlueprint";
import { vibrateScan } from "@/lib/onboarding/haptics";
import { C } from "@/lib/onboarding/types";
import { buildMarketContext, fetchMarketData, SCAN_UNIVERSE } from "@/lib/scan/bybit";
import { buildBlueprint, PASS_THRESHOLD } from "@/lib/scan/engine";
import { fetchEntitlements, FREE_ENTITLEMENTS, type Entitlements } from "@/lib/scan/entitlements";
import { coinLockReason, fetchCoinAccess, isCoinLocked, OPEN_ACCESS, type CoinAccess } from "@/lib/scan/coinAccess";
import { MarketNarrative } from "@/components/scan/MarketNarrative";
import narrativesData from "@/lib/scan/market_narratives.json";
import { resolveDailyLimit, resolveNarrative, type NarrativeCoin, type NarrativesFile } from "@/lib/scan/narrative";
import { recordScan, recordSnapshot, toScoreLogItems } from "@/lib/scan/persist";
import {
  getCoinPrefs,
  getLens,
  getRiskStyle,
  incScanCount,
  INITIAL_SCAN_PHASE,
  setCoinPrefs,
  setLens,
  setRiskStyle,
} from "@/lib/scan/store";
import type { Blueprint, Lens, MarketData, RiskStyle } from "@/lib/scan/types";
import { apiFetch } from "@/lib/api";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";

type Phase = "idle" | "scanning" | "results" | "empty" | "limit";
type Modal = { kind: "blueprint" | "whynot"; bp: Blueprint } | null;

function fmtTimestamp(d: Date): string {
  const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()} · ${hh}:${mm}`;
}

export default function ScanPage() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>(INITIAL_SCAN_PHASE);
  const [step, setStep] = useState(0);
  const [lens, setLensState] = useState<Lens>("Full");
  const [riskStyle, setRiskStyleState] = useState<RiskStyle>("Balanced");
  const [passers, setPassers] = useState<Blueprint[]>([]);
  const [nonPassers, setNonPassers] = useState<Blueprint[]>([]);
  const [scanned, setScanned] = useState(0);
  const [timestamp, setTimestamp] = useState("");
  const [xpAwarded, setXpAwarded] = useState(false);
  const [modal, setModal] = useState<Modal>(null);
  const [scanCount, setScanCount] = useState(0);
  const [ent, setEnt] = useState<Entitlements>(FREE_ENTITLEMENTS);
  const [xp, setXp] = useState(0);
  const [drawer, setDrawer] = useState(false);
  const [dailyLimit, setDailyLimit] = useState<number>(1);
  const [onTrial, setOnTrial] = useState(false);
  const [selectedCoins, setSelectedCoins] = useState<string[]>([]);
  const [coinAccess, setCoinAccess] = useState<CoinAccess>(OPEN_ACCESS);
  const [unrevealed, setUnrevealed] = useState(0);

  const mdRef = useRef<Map<string, MarketData>>(new Map());
  const ctxRef = useRef<MarketContext>({ coinChanges: {}, meanChange: 0, stdChange: 0 });
  const idRef = useRef<Map<string, number>>(new Map());

  // FX1 safety net: a signed-in user who never finished onboarding (e.g. reached /scan
  // by direct navigation) is routed into it. The primary entry paths (/login, /verify)
  // already route via routeAfterAuth; this catches the rest.
  useEffect(() => {
    void apiFetch<{ data: { onboarding_completed?: boolean } }>("/api/auth/me").then((r) => {
      if (r.ok && r.data?.data && r.data.data.onboarding_completed === false) {
        router.replace("/onboarding");
      }
    });
  }, [router]);

  useEffect(() => {
    setLensState(getLens());
    setRiskStyleState(getRiskStyle());
    void fetchEntitlements().then(setEnt);
    void fetchCoinAccess().then(setCoinAccess);
    // F16 S2: the unrevealed-journal count enriches the quiet-day narrative when present.
    void apiFetch<{ unrevealed: number }>("/api/journal/badge").then((r) => {
      if (r.ok && r.data) setUnrevealed(r.data.unrevealed);
    });
    void apiFetch<{ total: number }>("/api/onboarding/xp").then((r) => {
      if (r.ok && r.data) setXp(r.data.total);
    });
    // Trial chip (Bug 4): show TRIAL in the header while the no-card trial is active.
    void apiFetch<{ subscription_status: string }>("/api/billing/status").then((r) => {
      if (r.ok && r.data) setOnTrial(r.data.subscription_status === "trial");
    });
    // HOTFIX v0.18.2: the scan route always lands on the INPUT screen. A completed
    // result is never restored on mount — it is reachable via /history (Recent scans),
    // never the forced landing state (see store.ts INITIAL_SCAN_PHASE). This replaces
    // the old "Bug 5" sessionStorage restore that trapped users in the last result.
  }, []);

  // Decision C: reconcile the coin selection with the plan's coin count once the
  // entitlements load. Use the saved preference (clamped to the count), else default
  // to the first N of the universe.
  useEffect(() => {
    const n = ent.coins_per_scan;
    // FX4: never auto-select a coin the plan cannot scan (locked coins route to /subscribe).
    const allowed = (c: string) => !isCoinLocked(c, coinAccess);
    const saved = getCoinPrefs().filter((c) => SCAN_UNIVERSE.includes(c) && allowed(c));
    const pool = SCAN_UNIVERSE.filter(allowed);
    const next = (saved.length > 0 ? saved : pool).slice(0, n);
    setSelectedCoins(next);
  }, [ent.coins_per_scan, coinAccess]);

  function toggleCoin(coin: string) {
    setSelectedCoins((prev) => {
      let next: string[];
      if (prev.includes(coin)) {
        next = prev.filter((c) => c !== coin);
      } else if (prev.length < ent.coins_per_scan) {
        next = [...prev, coin];
      } else {
        // At the cap: replace the oldest pick so a tap always does something.
        next = [...prev.slice(1), coin];
      }
      setCoinPrefs(next);
      return next;
    });
  }

  function chooseLens(l: Lens) {
    setLens(l);
    setLensState(l);
  }
  function chooseRiskStyle(s: RiskStyle) {
    setRiskStyle(s);
    setRiskStyleState(s);
  }

  // F16: resolve the Market Narrative for the current scan (deterministic, reads only the
  // scan payload + the already-computed 24h change). Null before any scan completes.
  const narrative = useMemo(() => {
    const all = [...passers, ...nonPassers];
    if (all.length === 0) return null;
    const coins: NarrativeCoin[] = all.map((bp) => ({
      coin: bp.coin,
      passLabel: bp.passLabel,
      score: bp.score,
      ema7SlopePct: bp.ema7SlopePct,
      riskReward: bp.riskReward,
      change24h: mdRef.current.get(bp.coin)?.change24h ?? 0,
      whyNotCheckId: bp.whyNot?.checkId ?? null,
    }));
    return resolveNarrative(
      { coins, unrevealed: unrevealed > 0 ? unrevealed : undefined },
      narrativesData as NarrativesFile,
    );
  }, [passers, nonPassers, unrevealed]);

  async function runScan() {
    vibrateScan();
    setPhase("scanning");
    setModal(null);
    setStep(0);
    const timer = setInterval(() => setStep((s) => Math.min(s + 1, SCAN_STEPS.length - 1)), 350);

    // Server-authoritative coin count: scan only the plan's breadth. Decision C: the
    // user picks WHICH coins (within the plan count); fall back to the first N.
    const picked = selectedCoins.filter((c) => SCAN_UNIVERSE.includes(c)).slice(0, ent.coins_per_scan);
    const universe = picked.length > 0 ? picked : SCAN_UNIVERSE.slice(0, ent.coins_per_scan);
    const settled = await Promise.allSettled(universe.map(fetchMarketData));
    clearInterval(timer);
    setStep(SCAN_STEPS.length - 1);

    mdRef.current.clear();
    universe.forEach((coin, i) => {
      const r = settled[i];
      if (r.status === "fulfilled") mdRef.current.set(coin, r.value);
    });
    const ctx = buildMarketContext(mdRef.current);
    ctxRef.current = ctx;

    const blueprints: Blueprint[] = [];
    mdRef.current.forEach((md, coin) => {
      const bp = buildBlueprint(coin, md, riskStyle, ctx);
      if (bp) blueprints.push(bp);
    });

    const pass = blueprints.filter((b) => b.passLabel !== "HIDE");
    const fail = blueprints.filter((b) => b.passLabel === "HIDE");
    const ts = fmtTimestamp(new Date());

    const outcome = await recordScan(universe.length, pass.length, PASS_THRESHOLD, blueprints.flatMap(toScoreLogItems));
    // Bug 2/3: the server enforces the daily scan cap. On rejection we withhold the
    // results and show a friendly limit state (never a raw error).
    if (outcome.dailyLimit) {
      setDailyLimit(outcome.dailyLimit.scans_per_day);
      setPhase("limit");
      return;
    }
    // FX4: a gated coin slipped through (e.g. coin-access fetch failed). Show the door.
    if (outcome.coinGated) {
      router.push("/subscribe");
      return;
    }
    const rec = outcome.result;

    setScanned(universe.length);
    setPassers(pass);
    setNonPassers(fail);
    setTimestamp(ts);
    idRef.current.clear();
    rec?.score_logs.forEach((sl) => idRef.current.set(sl.coin, sl.id));
    setXpAwarded(rec?.first_scan_of_day ?? false);
    if (rec?.xp_awarded) setXp((x) => x + rec.xp_awarded);

    const sc = incScanCount();
    setScanCount(sc);
    const nextPhase: Phase = pass.length > 0 ? "results" : "empty";
    setPhase(nextPhase);
  }

  function openBlueprint(bp: Blueprint) {
    setModal({ kind: "blueprint", bp });
    const id = idRef.current.get(bp.coin);
    if (id) void recordSnapshot(id, JSON.stringify(bp));
  }
  function openWhyNot(bp: Blueprint) {
    setModal({ kind: "whynot", bp });
  }

  // Risk Style on the card → rebuild LEVELS only (score unchanged, RED LINE).
  function rebuildRiskStyle(style: RiskStyle) {
    chooseRiskStyle(style);
    if (!modal || modal.kind !== "blueprint") return;
    const md = mdRef.current.get(modal.bp.coin);
    if (!md) return;
    const bp = buildBlueprint(modal.bp.coin, md, style, ctxRef.current);
    if (!bp) return;
    setModal({ kind: "blueprint", bp });
    setPassers((prev) => prev.map((p) => (p.coin === bp.coin ? bp : p)));
  }

  const modalMd = modal ? mdRef.current.get(modal.bp.coin) : undefined;

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg }}>
      <div style={{ maxWidth: 480, margin: "0 auto", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <AppHeader xp={xp} left="menu" onLeft={() => setDrawer(true)} freeBadge={ent.tier === "free"} trialBadge={onTrial} />
        <BroadcastBanner />
        <BillingBanner />

        {phase === "idle" && (
          <>
            <div style={{ padding: "14px 20px 0" }}>
              <HorizonSelector />
            </div>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14 }}>
              <button
                type="button"
                onClick={runScan}
                style={{
                  width: 190,
                  height: 190,
                  borderRadius: "50%",
                  background: "radial-gradient(circle at 38% 32%,#1c2530,#10151c 70%)",
                  border: `1.5px solid rgba(31,178,134,.6)`,
                  boxShadow: "0 0 52px rgba(31,178,134,.22), inset 0 0 34px rgba(31,178,134,.08)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 4,
                  cursor: "pointer",
                }}
              >
                <span style={{ font: `700 22px ${MONO}`, letterSpacing: 3, color: C.green }}>SCAN</span>
                <span style={{ font: `500 9.5px ${MONO}`, letterSpacing: 1.5, color: C.muted }}>{ent.coins_per_scan} COINS</span>
              </button>
              <div style={{ font: `400 10.5px ${MONO}`, color: C.muted }}>fresh pull · no cache · your connection</div>
            </div>
            <div style={{ padding: "0 20px 12px", display: "flex", flexDirection: "column", gap: 10 }}>
              {/* Decision C: pick WHICH coins to scan, within the plan's coin count. */}
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <span style={{ font: `600 7.5px ${MONO}`, letterSpacing: 1.5, color: C.muted }}>YOUR COINS</span>
                  <span style={{ font: `600 7.5px ${MONO}`, letterSpacing: 0.5, color: selectedCoins.length === ent.coins_per_scan ? C.green : C.amber }}>
                    {selectedCoins.length}/{ent.coins_per_scan} PICKED
                  </span>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {SCAN_UNIVERSE.map((coin) => {
                    const locked = isCoinLocked(coin, coinAccess);
                    const on = !locked && selectedCoins.includes(coin);
                    // FX4 show-the-door: a locked coin stays visible with a lock + reason;
                    // tapping it routes to /subscribe (never toggles, never errors silently).
                    const reason = locked ? coinLockReason(coin, coinAccess) : null;
                    return (
                      <button
                        key={coin}
                        type="button"
                        title={reason ?? undefined}
                        onClick={() => (locked ? router.push("/subscribe") : toggleCoin(coin))}
                        style={{
                          font: `600 9.5px ${MONO}`,
                          letterSpacing: 0.3,
                          color: on ? C.bg : locked ? C.muted : C.fg,
                          background: on ? C.green : C.panel,
                          border: `1px solid ${on ? C.green : C.border}`,
                          borderRadius: 14,
                          padding: "5px 10px",
                          cursor: "pointer",
                          opacity: locked ? 0.7 : 1,
                        }}
                      >
                        {locked ? "🔒 " : ""}
                        {coin.replace("USDT", "")}
                      </button>
                    );
                  })}
                </div>
                {SCAN_UNIVERSE.some((c) => isCoinLocked(c, coinAccess)) && (
                  <div style={{ font: `400 8.5px ${MONO}`, color: C.muted, marginTop: 2 }}>
                    Locked coins are available on a higher plan. Tap to see plans.
                  </div>
                )}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <LensSelect value={lens} onChange={chooseLens} />
                <RiskStyleSelect value={riskStyle} onChange={chooseRiskStyle} />
              </div>
              <RedLineCaption />
            </div>
            <Disclaimer />
          </>
        )}

        {phase === "scanning" && (
          <>
            <ScanningLog step={step} markets={ent.coins_per_scan} />
            <Disclaimer />
          </>
        )}

        {phase === "results" && (
          <>
            <Results
              passers={passers}
              nonPassers={nonPassers}
              scanned={scanned}
              timestamp={timestamp}
              xpAwarded={xpAwarded}
              onOpen={openBlueprint}
              onOpenWhyNot={openWhyNot}
              onNewScan={() => setPhase("idle")}
              narrative={narrative}
            />
            <Disclaimer />
          </>
        )}

        {phase === "empty" && (
          <>
            <EmptyState scanCount={scanCount} narrative={narrative} />
            {nonPassers.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center", padding: "0 16px 10px" }}>
                {nonPassers.map((bp) => (
                  <button
                    key={bp.coin}
                    type="button"
                    onClick={() => openWhyNot(bp)}
                    style={{ font: `600 9.5px ${MONO}`, color: C.muted, background: C.panel, border: `1px solid ${C.border}`, borderRadius: 14, padding: "5px 11px", cursor: "pointer" }}
                  >
                    {bp.coin.replace("USDT", "")} · why not
                  </button>
                ))}
              </div>
            )}
            <Disclaimer />
          </>
        )}

        {phase === "limit" && (
          <>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14, padding: "0 28px", textAlign: "center" }}>
              <div style={{ fontSize: 34 }}>🛡️</div>
              <div style={{ font: `700 15px ${MONO}`, letterSpacing: 1, color: C.fg }}>
                {dailyLimit === 1 ? "That is today's scan" : `Daily scans used (${dailyLimit})`}
              </div>
              <div style={{ font: `400 12.5px 'Space Grotesk', system-ui, sans-serif`, color: C.muted, lineHeight: 1.6, maxWidth: 320 }}>
                Your plan includes {dailyLimit} scan{dailyLimit === 1 ? "" : "s"} per day. Discipline is one clear read a day, not many. Your journal resets tomorrow. Paid plans scan without a daily limit.
              </div>
              {/* F16 S6: the daily_limit_reached narrative renders INSIDE this quota screen (B2). */}
              <div style={{ width: "100%", maxWidth: 360, textAlign: "left" }}>
                <MarketNarrative result={resolveDailyLimit(dailyLimit, narrativesData as NarrativesFile)} />
              </div>
              <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
                <button
                  type="button"
                  onClick={() => router.push("/subscribe")}
                  style={{ font: `600 11px ${MONO}`, color: C.bg, background: C.green, border: "none", borderRadius: 8, padding: "10px 16px", cursor: "pointer" }}
                >
                  SEE PLANS
                </button>
                <button
                  type="button"
                  onClick={() => router.push("/dashboard")}
                  style={{ font: `600 11px ${MONO}`, color: C.fg, background: C.panel, border: `1px solid ${C.border}`, borderRadius: 8, padding: "10px 16px", cursor: "pointer" }}
                >
                  VIEW JOURNAL
                </button>
              </div>
            </div>
            <Disclaimer />
          </>
        )}
      </div>

      {modal && modalMd && modal.kind === "blueprint" && (
        <TradingBlueprint
          bp={modal.bp}
          md={modalMd}
          lens={lens}
          layers={ent.chart_layers}
          xp={xp}
          onRiskStyle={rebuildRiskStyle}
          onSeePlans={() => router.push("/subscribe")}
          onClose={() => setModal(null)}
        />
      )}
      {modal && modalMd && modal.kind === "whynot" && (
        <NonPasser
          bp={modal.bp}
          md={modalMd}
          layers={ent.chart_layers}
          xp={xp}
          timestamp={timestamp}
          onSeePlans={() => router.push("/subscribe")}
          onClose={() => setModal(null)}
        />
      )}

      {drawer && (
        <NavDrawer
          xp={xp}
          tier={ent.tier}
          onClose={() => setDrawer(false)}
          onNavigate={(path) => {
            setDrawer(false);
            router.push(path);
          }}
        />
      )}
    </main>
  );
}
