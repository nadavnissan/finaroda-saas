"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ConceptTooltip } from "@/components/onboarding/ConceptTooltip";
import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

interface Plan {
  tier: string;
  price_ils: number;
  coins_per_scan: number;
  scans_per_day: number;
  chart_layers: string;
}
interface PlansResponse {
  currency: string;
  plans: Plan[];
}

// Comparison rows. Price / scans / coins / chart-layers come from the API (system_
// settings, admin-editable). Blueprint / journal / export / academy are product copy
// (F7), not admin-tunable. Free column is FIRST and always visible (TC-J-002).
type Cell = string;
type RowFn = (p: Record<string, Plan>) => Cell;

function scansCell(p: Plan): string {
  return p.scans_per_day === 0 ? "Unltd" : String(p.scans_per_day);
}
function layersCell(p: Plan): string {
  return p.chart_layers === "full" ? "All" : "EMA200";
}

const ROWS: { label: string; term?: string; get: RowFn }[] = [
  { label: "₪ / month", get: (p) => String(p.free.price_ils) + "|" + p.basic.price_ils + "|" + p.advanced.price_ils + "|" + p.pro.price_ils },
  { label: "Scans per day", get: (p) => [scansCell(p.free), scansCell(p.basic), scansCell(p.advanced), scansCell(p.pro)].join("|") },
  { label: "Coins per scan", get: (p) => [p.free.coins_per_scan, p.basic.coins_per_scan, p.advanced.coins_per_scan, p.pro.coins_per_scan].join("|") },
  { label: "Trading Blueprint", get: () => "Full|Full|Full|Full" },
  { label: "Chart layers", get: (p) => [layersCell(p.free), layersCell(p.basic), layersCell(p.advanced), layersCell(p.pro)].join("|") },
  { label: "Journal history", get: () => "7 days|Full|Full|Full" },
  { label: "Export (CSV/PNG)", get: () => "-|-|✓|✓" },
  { label: "Academy", get: () => "Basic|Basic|Full|Full" },
];

const COL_COLORS = [C.muted, C.fg, C.fg, C.green];

function Shield({ icon, text }: { icon: string; text: string }) {
  return (
    <div style={{ background: C.panel, border: `1px solid rgba(233,238,243,.1)`, borderRadius: 9, padding: 8, display: "flex", flexDirection: "column", alignItems: "center", gap: 3, textAlign: "center" }}>
      <span style={{ fontSize: 12 }}>{icon}</span>
      <span style={{ font: `500 8px ${MONO}`, color: C.muted, lineHeight: 1.35 }}>{text}</span>
    </div>
  );
}

export default function SubscribePage() {
  const router = useRouter();
  const [data, setData] = useState<PlansResponse | null>(null);
  const [xp, setXp] = useState(0);
  const [starting, setStarting] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    void apiFetch<PlansResponse>("/api/plans").then((r) => { if (r.ok && r.data) setData(r.data); });
    void apiFetch<{ total: number }>("/api/onboarding/xp").then((r) => { if (r.ok && r.data) setXp(r.data.total); });
  }, []);

  async function startTrial() {
    setStarting(true);
    setErr("");
    const res = await apiFetch("/api/cardcom/trial", { method: "POST" });
    setStarting(false);
    if (res.ok) router.push("/scan");
    else if (res.status === 401) router.push("/login");
    else if (res.status === 409) setErr("Your trial was already used. You can continue on Free.");
    else setErr("Could not start the trial - please try again.");
  }

  const byTier: Record<string, Plan> = {};
  (data?.plans ?? []).forEach((p) => { byTier[p.tier] = p; });
  const ready = data && byTier.free && byTier.basic && byTier.advanced && byTier.pro;

  const gridCols = "1.35fr .8fr .8fr .95fr .8fr";

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg }}>
      <div style={{ maxWidth: 480, margin: "0 auto", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <AppHeader xp={xp} left="close" onLeft={() => router.push("/scan")} />

        <div style={{ padding: "8px 20px 0", textAlign: "center" }}>
          <div style={{ font: `700 22px ${SANS}`, color: C.fg, lineHeight: 1.3 }}>Choose your plan</div>
          <div style={{ font: `400 11.5px ${SANS}`, color: C.muted, marginTop: 4, lineHeight: 1.5 }}>
            Same engine, same threshold, on every plan - you choose breadth and depth.
          </div>
        </div>

        <div style={{ padding: "14px 20px 0", display: "flex", flexDirection: "column", gap: 8 }}>
          <button
            type="button"
            onClick={startTrial}
            disabled={starting}
            style={{ height: 54, display: "flex", alignItems: "center", justifyContent: "center", background: C.green, borderRadius: 10, border: "none", font: `600 12.5px ${MONO}`, letterSpacing: 1, color: C.bg, boxShadow: "0 0 26px rgba(31,178,134,.3)", cursor: "pointer" }}
          >
            {starting ? "STARTING…" : "START 14 DAYS OF PRO - NO CREDIT CARD"}
          </button>
          {err && <div style={{ font: `400 10px ${MONO}`, color: C.amber, textAlign: "center" }}>{err}</div>}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
            <Shield icon="🛡️" text="NO AUTO-CHARGE EVER" />
            <Shield icon="🔔" text="REMINDER ON DAY 11" />
            <Shield icon="⚖️" text="YOU DECIDE AT THE END" />
          </div>
        </div>

        {ready ? (
          <div style={{ margin: "14px 14px 0", background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 12, overflow: "hidden", font: `400 9.5px ${MONO}` }}>
            <div style={{ display: "grid", gridTemplateColumns: gridCols, padding: "10px 12px", borderBottom: `1px solid rgba(233,238,243,.07)`, fontWeight: 600, fontSize: 8, letterSpacing: 0.5 }}>
              <span />
              {["FREE", "BASIC", "ADVANCED", "PRO"].map((h, i) => (
                <span key={h} style={{ color: COL_COLORS[i], textAlign: "center" }}>{h}</span>
              ))}
            </div>
            {ROWS.map((row) => {
              const cells = row.get(byTier).split("|");
              return (
                <div key={row.label} style={{ display: "grid", gridTemplateColumns: gridCols, padding: "8px 12px", borderBottom: `1px solid rgba(233,238,243,.05)`, alignItems: "center" }}>
                  <span style={{ color: C.fg, fontFamily: SANS, fontSize: 10.5 }}>{row.label}</span>
                  {cells.map((cell, i) => (
                    <span key={i} style={{ color: COL_COLORS[i], textAlign: "center", fontWeight: i === 3 ? 600 : 400 }}>{cell}</span>
                  ))}
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ padding: 24, textAlign: "center", color: C.muted, font: `400 11px ${MONO}` }}>Loading plans…</div>
        )}

        <div style={{ padding: "12px 20px 0", font: `400 10px ${MONO}`, color: C.muted, textAlign: "center", lineHeight: 1.6 }}>
          Every plan sees the same coins pass the same verified{" "}
          <ConceptTooltip id="pass_watch" label="85+ threshold" />.
        </div>
        <div style={{ padding: "10px 20px 0", textAlign: "center" }}>
          <button type="button" onClick={() => router.push("/scan")} style={{ font: `500 12px ${SANS}`, color: C.muted, background: "none", border: "none", borderBottom: `1px solid rgba(133,147,162,.5)`, paddingBottom: 2, cursor: "pointer" }}>
            Continue on Free
          </button>
        </div>

        <div style={{ marginTop: "auto" }}>
          <Disclaimer />
        </div>
      </div>
    </main>
  );
}
