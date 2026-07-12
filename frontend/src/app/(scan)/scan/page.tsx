"use client";

import { useEffect, useRef, useState } from "react";

import type { MarketContext } from "@finaroda/scoring-engine/scorer.js";

import { LensToggle, RiskStyleToggle } from "@/components/scan/Controls";
import { Results, EmptyState } from "@/components/scan/Results";
import { SCAN_STEPS, ScanningLog } from "@/components/scan/ScanningLog";
import { TradingBlueprint } from "@/components/scan/TradingBlueprint";
import { vibrateScan } from "@/lib/onboarding/haptics";
import { buildMarketContext, fetchMarketData, SCAN_UNIVERSE } from "@/lib/scan/bybit";
import { buildBlueprint, PASS_THRESHOLD } from "@/lib/scan/engine";
import { recordScan, recordSnapshot, toScoreLogItems } from "@/lib/scan/persist";
import {
  getLens,
  getRiskStyle,
  incScanCount,
  setLens,
  setRiskStyle,
} from "@/lib/scan/store";
import type { Blueprint, Lens, MarketData, RiskStyle } from "@/lib/scan/types";

type Phase = "idle" | "scanning" | "results" | "empty";

export default function ScanPage() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [step, setStep] = useState(0);
  const [lens, setLensState] = useState<Lens>("Full");
  const [riskStyle, setRiskStyleState] = useState<RiskStyle>("Balanced");
  const [passers, setPassers] = useState<Blueprint[]>([]);
  const [scanned, setScanned] = useState(0);
  const [selected, setSelected] = useState<Blueprint | null>(null);
  const [disciplined, setDisciplined] = useState(0);

  const mdRef = useRef<Map<string, MarketData>>(new Map());
  const ctxRef = useRef<MarketContext>({ coinChanges: {}, meanChange: 0, stdChange: 0 });
  const idRef = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    setLensState(getLens());
    setRiskStyleState(getRiskStyle());
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
    vibrateScan(); // haptic on SCAN; silent fallback where unsupported (iOS Safari)
    setPhase("scanning");
    setSelected(null);
    setStep(0);
    const timer = setInterval(
      () => setStep((s) => Math.min(s + 1, SCAN_STEPS.length - 1)),
      350,
    );

    const settled = await Promise.allSettled(SCAN_UNIVERSE.map(fetchMarketData));
    clearInterval(timer);
    setStep(SCAN_STEPS.length - 1);

    // Collect market data, then build cross-coin context (isolation-Z input).
    mdRef.current.clear();
    SCAN_UNIVERSE.forEach((coin, i) => {
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

    // Real gate (SCORE_GATE_ENABLED): PASS ≥85 / WATCH 82–84 shown; HIDE not shown.
    const pass = blueprints.filter((b) => b.passLabel !== "HIDE");
    setScanned(SCAN_UNIVERSE.length);
    setPassers(pass);

    // Persistence (SPEC §5): 3 profile rows per coin. Best-effort (401 = silent no-op).
    const rec = await recordScan(
      SCAN_UNIVERSE.length,
      pass.length,
      PASS_THRESHOLD,
      blueprints.flatMap(toScoreLogItems),
    );
    idRef.current.clear();
    rec?.score_logs.forEach((sl) => idRef.current.set(sl.coin, sl.id));

    setDisciplined(incScanCount());
    setPhase(pass.length > 0 ? "results" : "empty");
  }

  function openBlueprint(bp: Blueprint) {
    setSelected(bp);
    const id = idRef.current.get(bp.coin);
    if (id) void recordSnapshot(id, JSON.stringify(bp)); // evidentiary, best-effort
  }

  // Risk Style change on the card → rebuild LEVELS only (score is unchanged — RED LINE).
  function rebuildRiskStyle(style: RiskStyle) {
    chooseRiskStyle(style);
    if (!selected) return;
    const md = mdRef.current.get(selected.coin);
    if (!md) return;
    const bp = buildBlueprint(selected.coin, md, style, ctxRef.current);
    if (!bp) return;
    setSelected(bp);
    setPassers((prev) => prev.map((p) => (p.coin === bp.coin ? bp : p)));
  }

  return (
    <main>
      <h1>Scan</h1>

      {phase === "idle" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
          <LensToggle value={lens} onChange={chooseLens} />
          <RiskStyleToggle value={riskStyle} onChange={chooseRiskStyle} />
          <button
            type="button"
            onClick={runScan}
            style={{
              width: 158,
              height: 158,
              borderRadius: "50%",
              border: "2px solid #1FB286",
              background: "radial-gradient(circle at 50% 30%, #16261f, #0b0d12)",
              color: "#E9EEF3",
              fontFamily: "monospace",
              cursor: "pointer",
            }}
          >
            SCAN · {SCAN_UNIVERSE.length} MARKETS
          </button>
          <small style={{ color: "#5c6672" }}>Analysis, not financial advice.</small>
        </div>
      )}

      {phase === "scanning" && <ScanningLog step={step} />}

      {phase === "results" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
          <Results passers={passers} scanned={scanned} onOpen={openBlueprint} />
          <button type="button" onClick={() => setPhase("idle")} style={{ color: "#8593A2", background: "none", border: "none", cursor: "pointer" }}>
            ↻ new scan
          </button>
        </div>
      )}

      {phase === "empty" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
          <EmptyState disciplinedDays={disciplined} />
          <button type="button" onClick={() => setPhase("idle")} style={{ color: "#8593A2", background: "none", border: "none", cursor: "pointer" }}>
            ↻ new scan
          </button>
        </div>
      )}

      {selected && (
        <TradingBlueprint bp={selected} lens={lens} onRiskStyle={rebuildRiskStyle} onClose={() => setSelected(null)} />
      )}
    </main>
  );
}
