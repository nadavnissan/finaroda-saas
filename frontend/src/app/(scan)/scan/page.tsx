"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import type { MarketContext } from "@finaroda/scoring-engine/scorer.js";

import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
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
import { getLens, getRiskStyle, incScanCount, setLens, setRiskStyle } from "@/lib/scan/store";
import type { Blueprint, Lens, MarketData, RiskStyle } from "@/lib/scan/types";
import { apiFetch } from "@/lib/api";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";

type Phase = "idle" | "scanning" | "results" | "empty";
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
  }, []);

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

    // Server-authoritative coin count: scan only the plan's breadth.
    const universe = SCAN_UNIVERSE.slice(0, ent.coins_per_scan);
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
    setScanned(universe.length);
    setPassers(pass);
    setNonPassers(fail);
    setTimestamp(fmtTimestamp(new Date()));

    const rec = await recordScan(universe.length, pass.length, PASS_THRESHOLD, blueprints.flatMap(toScoreLogItems));
    idRef.current.clear();
    rec?.score_logs.forEach((sl) => idRef.current.set(sl.coin, sl.id));
    setXpAwarded(rec?.first_scan_of_day ?? false);
    if (rec?.xp_awarded) setXp((x) => x + rec.xp_awarded);

    setScanCount(incScanCount());
    setPhase(pass.length > 0 ? "results" : "empty");
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
        <AppHeader xp={xp} left="menu" onLeft={() => setDrawer(true)} freeBadge={ent.tier === "free"} />

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
                <span style={{ font: `500 9.5px ${MONO}`, letterSpacing: 1.5, color: C.muted }}>{ent.coins_per_scan} MARKETS</span>
              </button>
              <div style={{ font: `400 10.5px ${MONO}`, color: C.muted }}>fresh pull · no cache · your connection</div>
            </div>
            <div style={{ padding: "0 20px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
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
