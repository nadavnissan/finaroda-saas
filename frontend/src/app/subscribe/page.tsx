"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ConceptTooltip } from "@/components/onboarding/ConceptTooltip";
import { AppHeader, Disclaimer } from "@/components/scan/AppHeader";
import { api, apiFetch } from "@/lib/api";
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
// settings, admin-editable). Blueprint / journal / export are product copy (F7), not
// admin-tunable. Free column is FIRST and always visible (TC-J-002). Three tiers only:
// Free / Basic (RECOMMENDED) / Pro. Advanced is retired.
type RowFn = (p: Record<string, Plan>) => [string, string, string];

function scansCell(p: Plan): string {
  return p.scans_per_day === 0 ? "Unltd" : String(p.scans_per_day);
}
function layersCell(p: Plan): string {
  return p.chart_layers === "full" ? "All" : "EMA200";
}
function priceCell(p: Plan): string {
  return "₪" + p.price_ils;
}

const ROWS: { label: string; get: RowFn }[] = [
  { label: "Price / month", get: (p) => [priceCell(p.free), priceCell(p.basic), priceCell(p.pro)] },
  { label: "Coins per scan", get: (p) => [String(p.free.coins_per_scan), String(p.basic.coins_per_scan), String(p.pro.coins_per_scan)] },
  { label: "Scans per day", get: (p) => [scansCell(p.free), scansCell(p.basic), scansCell(p.pro)] },
  { label: "Trading Blueprint", get: () => ["Full", "Full", "Full"] },
  { label: "Journal / F3", get: () => ["7 days", "Full", "Full"] },
  { label: "Chart layers", get: (p) => [layersCell(p.free), layersCell(p.basic), layersCell(p.pro)] },
  { label: "Export CSV/PNG", get: () => ["–", "✓", "✓"] },
];

// Column accent: Free muted, Basic (recommended) green, Pro foreground.
const COL_COLORS: [string, string, string] = [C.muted, C.green, C.fg];

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
  const [trialUsed, setTrialUsed] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    void api.getPlans().then((r) => { if (r.ok && r.data) setData(r.data as PlansResponse); });
    void apiFetch<{ total: number }>("/api/onboarding/xp").then((r) => { if (r.ok && r.data) setXp(r.data.total); });
  }, []);

  // Bug 4: trial CTA starts the no-card Pro trial and lands on /scan (trial chip
  // shown there). 409 = already used → inline note only, no navigation.
  async function startTrial() {
    setStarting(true);
    setErr("");
    setTrialUsed(false);
    const res = await api.startTrial();
    setStarting(false);
    if (res.ok) {
      router.push("/scan");
    } else if (res.status === 401) {
      router.push("/login");
    } else if (res.status === 409) {
      setTrialUsed(true);
    } else {
      setErr("Could not start the trial, please try again.");
    }
  }

  // Paid conversion path (unchanged). May 503 in test mode.
  async function choosePlan(tier: string) {
    const res = await api.initiateCheckout(tier);
    if (res.ok && res.data) {
      const url = (res.data as { redirect_url?: string }).redirect_url;
      if (url) { window.location.href = url; return; }
    }
    if (res.status === 401) { router.push("/login"); return; }
    setErr("Checkout is unavailable right now, please try again later.");
  }

  const byTier: Record<string, Plan> = {};
  (data?.plans ?? []).forEach((p) => { byTier[p.tier] = p; });
  const ready = Boolean(data && byTier.free && byTier.basic && byTier.pro);

  // Three columns sized to fit a 375px phone without horizontal scroll.
  const gridCols = "1.25fr .82fr .82fr .82fr";
  const HEADERS: [string, string, string] = ["FREE", "BASIC", "PRO"];

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg }}>
      <div style={{ maxWidth: 480, margin: "0 auto", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <AppHeader xp={xp} left="close" onLeft={() => router.back()} />

        <div style={{ padding: "8px 20px 0", textAlign: "center" }}>
          <div style={{ font: `700 22px ${SANS}`, color: C.fg, lineHeight: 1.3 }}>Choose your plan</div>
          <div style={{ font: `400 11.5px ${SANS}`, color: C.muted, marginTop: 4, lineHeight: 1.5 }}>
            Same engine, same threshold, on every plan. You choose breadth and depth.
          </div>
        </div>

        <div style={{ padding: "14px 20px 0", display: "flex", flexDirection: "column", gap: 8 }}>
          <button
            type="button"
            onClick={startTrial}
            disabled={starting}
            style={{ height: 54, display: "flex", alignItems: "center", justifyContent: "center", background: C.green, borderRadius: 10, border: "none", font: `600 12.5px ${MONO}`, letterSpacing: 1, color: C.bg, boxShadow: "0 0 26px rgba(31,178,134,.3)", cursor: starting ? "default" : "pointer", opacity: starting ? 0.7 : 1 }}
          >
            {starting ? "STARTING…" : "START 14 DAYS OF PRO, NO CREDIT CARD"}
          </button>
          {trialUsed && <div style={{ font: `400 10px ${MONO}`, color: C.amber, textAlign: "center" }}>Trial already used.</div>}
          {err && <div style={{ font: `400 10px ${MONO}`, color: C.amber, textAlign: "center" }}>{err}</div>}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
            <Shield icon="🛡️" text="NO AUTO-CHARGE EVER" />
            <Shield icon="🔔" text="REMINDER ON DAY 11" />
            <Shield icon="⚖️" text="YOU DECIDE AT THE END" />
          </div>
        </div>

        {ready ? (
          <div style={{ margin: "14px 14px 0", background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 12, overflow: "hidden", font: `400 9.5px ${MONO}` }}>
            {/* Header row with the RECOMMENDED ribbon over BASIC. */}
            <div style={{ display: "grid", gridTemplateColumns: gridCols, padding: "12px 10px 8px", borderBottom: `1px solid rgba(233,238,243,.07)`, alignItems: "end" }}>
              <span style={{ font: `500 8.5px ${MONO}`, color: C.muted, alignSelf: "center" }}>Free forever</span>
              {HEADERS.map((h, i) => (
                <span key={h} style={{ position: "relative", textAlign: "center", color: COL_COLORS[i], fontWeight: 700, fontSize: 10, letterSpacing: 0.5 }}>
                  {i === 1 && (
                    <span style={{ position: "absolute", top: -13, left: "50%", transform: "translateX(-50%)", background: C.green, color: C.bg, font: `700 6.5px ${MONO}`, letterSpacing: 0.4, borderRadius: 4, padding: "2px 5px", whiteSpace: "nowrap" }}>
                      RECOMMENDED
                    </span>
                  )}
                  {h}
                </span>
              ))}
            </div>

            {ROWS.map((row) => {
              const cells = row.get(byTier);
              return (
                <div key={row.label} style={{ display: "grid", gridTemplateColumns: gridCols, padding: "7px 10px", borderBottom: `1px solid rgba(233,238,243,.05)`, alignItems: "center" }}>
                  <span style={{ color: C.fg, fontFamily: SANS, fontSize: 10 }}>{row.label}</span>
                  {cells.map((cell, i) => (
                    <span key={i} style={{ color: COL_COLORS[i], textAlign: "center", fontWeight: i === 1 ? 600 : 400 }}>{cell}</span>
                  ))}
                </div>
              );
            })}

            {/* Per-plan action row. Free = stay, Basic/Pro = paid checkout. */}
            <div style={{ display: "grid", gridTemplateColumns: gridCols, padding: "10px 10px 12px", gap: 5, alignItems: "center" }}>
              <span />
              <span />
              <button
                type="button"
                onClick={() => choosePlan("basic")}
                style={{ height: 32, background: C.green, color: C.bg, border: "none", borderRadius: 7, font: `700 9px ${MONO}`, letterSpacing: 0.5, cursor: "pointer" }}
              >
                CHOOSE
              </button>
              <button
                type="button"
                onClick={() => choosePlan("pro")}
                style={{ height: 32, background: "none", color: C.fg, border: `1px solid ${C.border}`, borderRadius: 7, font: `700 9px ${MONO}`, letterSpacing: 0.5, cursor: "pointer" }}
              >
                UPGRADE
              </button>
            </div>
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
