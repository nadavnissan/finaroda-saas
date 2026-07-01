"use client";

import { useEffect, useRef, useState } from "react";

import { LensToggle, RiskStyleToggle } from "@/components/scan/Controls";
import { Results, EmptyState } from "@/components/scan/Results";
import { SCAN_STEPS, ScanningLog } from "@/components/scan/ScanningLog";
import { TradingBlueprint } from "@/components/scan/TradingBlueprint";
import { fetchMarketData, SCAN_UNIVERSE } from "@/lib/scan/bybit";
import {
  buildBlueprint,
  PASS_THRESHOLD,
  SCORE_GATE_ENABLED,
} from "@/lib/scan/engine";
import { lensCondition } from "@/lib/scan/lens";
import { recordScan, recordSnapshot, toScoreLogItem } from "@/lib/scan/persist";
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

    mdRef.current.clear();
    const blueprints: Blueprint[] = [];
    SCAN_UNIVERSE.forEach((coin, i) => {
      const r = settled[i];
      if (r.status !== "fulfilled") return;
      mdRef.current.set(coin, r.value);
      const bp = buildBlueprint(coin, r.value, riskStyle);
      if (!bp) return;
      bp.interimPassed = lensCondition(lens, bp);
      blueprints.push(bp);
    });

    const pass = blueprints.filter((b) => b.interimPassed);
    setScanned(SCAN_UNIVERSE.length);
    setPassers(pass);

    // Best-effort persistence (SPEC §5). Silent no-op if signed out.
    const rec = await recordScan(
      SCAN_UNIVERSE.length,
      pass.length,
      SCORE_GATE_ENABLED ? PASS_THRESHOLD : null,
      blueprints.map(toScoreLogItem),
    );
    idRef.current.clear();
    rec?.score_logs.forEach((sl) => idRef.current.set(sl.coin, sl.id));

    setDisciplined(incScanCount());
    setPhase(pass.length > 0 ? "results" : "empty");
  }

  function openBlueprint(bp: Blueprint) {
    setSelected(bp);
    const id = idRef.current.get(bp.coin);
    if (id) void recordSnapshot(id, JSON.stringify(bp)); // best-effort, evidentiary
  }

  // Risk Style change on the card → rebuild that coin's levels (NOT the score).
  function rebuildRiskStyle(style: RiskStyle) {
    chooseRiskStyle(style);
    if (!selected) return;
    const md = mdRef.current.get(selected.coin);
    if (!md) return;
    const bp = buildBlueprint(selected.coin, md, style);
    if (!bp) return;
    bp.interimPassed = lensCondition(lens, bp);
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
          <button type="button" onClick={runScan} style={{ color: "#8593A2", background: "none", border: "none", cursor: "pointer" }}>
            ↻ scan again
          </button>
        </div>
      )}

      {phase === "empty" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
          <EmptyState disciplinedDays={disciplined} />
          <button type="button" onClick={runScan} style={{ color: "#8593A2", background: "none", border: "none", cursor: "pointer" }}>
            ↻ scan again
          </button>
        </div>
      )}

      {selected && (
        <TradingBlueprint bp={selected} lens={lens} onRiskStyle={rebuildRiskStyle} onClose={() => setSelected(null)} />
      )}
    </main>
  );
}
