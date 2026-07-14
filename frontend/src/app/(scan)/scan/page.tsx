"use client";

import { useEffect, useRef, useState } from "react";
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
import { recordScan, recordSnapshot, toScoreLogItems } from "@/lib/scan/persist";
import {
  clearScanSession,
  getCoinPrefs,
  getLens,
  getRiskStyle,
  incScanCount,
  loadScanSession,
  saveScanSession,
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
  const [phase, setPhase] = useState<Phase>("idle");
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

  const mdRef = useRef<Map<string, MarketData>>(new Map());
  const ctxRef = useRef<MarketContext>({ coinChanges: {}, meanChange: 0, stdChange: 0 });
  const idRef = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    setLensState(getLens());
    setRiskStyleState(getRiskStyle());
    void fetchEntitlements().then(setEnt);
    void apiFetch<{ total: number }>("/api/onboarding/xp").then((r) => {
      if (r.ok && r.data) setXp(r.data.total);
    });
    // Trial chip (Bug 4): show TRIAL in the header while the no-card trial is active.
    void apiFetch<{ subscription_status: string }>("/api/cardcom/status").then((r) => {
      if (r.ok && r.data) setOnTrial(r.data.subscription_status === "trial");
    });
    // Bug 5: restore the last scan so returning from /subscribe (SEE PLANS) lands back
    // on the RESULTS state, not the controls. Rebuild the market-data + id maps so the
    // restored coins stay tappable.
    const s = loadScanSession();
    if (s) {
      mdRef.current = new Map(s.md);
      idRef.current = new Map(s.ids);
      ctxRef.current = buildMarketContext(mdRef.current);
      setPassers(s.passers);
      setNonPassers(s.nonPassers);
      setScanned(s.scanned);
      setTimestamp(s.timestamp);
      setXpAwarded(s.xpAwarded);
      setScanCount(s.scanCount);
      setPhase(s.phase);
    }
  }, []);

  // Decision C: reconcile the coin selection with the plan's coin count once the
  // entitlements load. Use the saved preference (clamped to the count), else default
  // to the first N of the universe.
  useEffect(() => {
    const n = ent.coins_per_scan;
    const saved = getCoinPrefs().filter((c) => SCAN_UNIVERSE.includes(c));
    const next = (saved.length > 0 ? saved : SCAN_UNIVERSE).slice(0, n);
    setSelectedCoins(next);
  }, [ent.coins_per_scan]);

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
    // Bug 5: persist so a SEE PLANS round-trip restores the results (coins tappable).
    saveScanSession({
      phase: nextPhase === "results" ? "results" : "empty",
      passers: pass,
      nonPassers: fail,
      scanned: universe.length,
      timestamp: ts,
      xpAwarded: rec?.first_scan_of_day ?? false,
      scanCount: sc,
      md: Array.from(mdRef.current.entries()),
      ids: Array.from(idRef.current.entries()),
    });
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
                    const on = selectedCoins.includes(coin);
                    return (
                      <button
                        key={coin}
                        type="button"
                        onClick={() => toggleCoin(coin)}
                        style={{
                          font: `600 9.5px ${MONO}`,
                          letterSpacing: 0.3,
                          color: on ? C.bg : C.fg,
                          background: on ? C.green : C.panel,
                          border: `1px solid ${on ? C.green : C.border}`,
                          borderRadius: 14,
                          padding: "5px 10px",
                          cursor: "pointer",
                        }}
                      >
                        {coin.replace("USDT", "")}
                      </button>
                    );
                  })}
                </div>
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
              onNewScan={() => { clearScanSession(); setPhase("idle"); }}
            />
            <Disclaimer />
          </>
        )}

        {phase === "empty" && (
          <>
            <EmptyState scanCount={scanCount} />
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
