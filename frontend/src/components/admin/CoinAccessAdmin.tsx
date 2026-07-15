"use client";

// FX4 admin — per-plan coin access. A checklist of the managed coin universe per plan,
// plus a wildcard toggle (Pro = all coins, auto-includes any coin added later). Admin-only
// on the server (require_admin). Changes are read per request, so they take effect on the
// next scan without a deploy. Coin access is breadth only, never a score or verdict knob.

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import { C } from "@/lib/onboarding/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'Space Grotesk', system-ui, sans-serif";

interface PlanAccess {
  plan: string;
  coins: string[];
  wildcard: boolean;
}

const PLAN_LABEL: Record<string, string> = { free: "Free", basic: "Basic", pro: "Pro" };

export function CoinAccessAdmin() {
  const [universe, setUniverse] = useState<string[]>([]);
  const [plans, setPlans] = useState<PlanAccess[]>([]);
  const [savedPlan, setSavedPlan] = useState<string | null>(null);

  const load = useCallback(async () => {
    const r = await apiFetch<{ universe: string[]; plans: PlanAccess[] }>("/api/admin/coin-access");
    if (r.ok && r.data) {
      setUniverse(r.data.universe);
      setPlans(r.data.plans);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  function setPlan(plan: string, next: Partial<PlanAccess>) {
    setPlans((prev) => prev.map((p) => (p.plan === plan ? { ...p, ...next } : p)));
  }

  function toggleCoin(plan: string, coin: string) {
    setPlans((prev) =>
      prev.map((p) => {
        if (p.plan !== plan) return p;
        const has = p.coins.includes(coin);
        return { ...p, coins: has ? p.coins.filter((c) => c !== coin) : [...p.coins, coin] };
      }),
    );
  }

  async function save(plan: string) {
    const p = plans.find((x) => x.plan === plan);
    if (!p) return;
    const r = await apiFetch(`/api/admin/coin-access/${plan}`, {
      method: "PUT",
      body: JSON.stringify({ coins: p.coins, wildcard: p.wildcard, note: "admin console edit" }),
    });
    if (r.ok) {
      setSavedPlan(plan);
      await load();
    }
  }

  return (
    <div style={{ flex: 1, padding: "20px clamp(16px,4vw,24px)", display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ font: `700 17px ${SANS}`, color: C.fg }}>
        Coin access{" "}
        <span style={{ font: `400 10px ${MONO}`, color: C.muted }}>
          · per-plan coin allowlist, live without a deploy
        </span>
      </div>
      <div style={{ font: `400 9px/1.5 ${MONO}`, color: C.muted }}>
        Which of our coins each plan can scan. Breadth only, never a score or verdict. Pro
        wildcard includes every coin, and auto-includes any coin added later. Trial equals Pro.
      </div>

      {plans.map((p) => (
        <div
          key={p.plan}
          style={{ background: C.panel, border: `1px solid rgba(233,238,243,.08)`, borderRadius: 10, padding: 15, display: "flex", flexDirection: "column", gap: 12 }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span style={{ font: `700 13px ${SANS}`, color: C.fg }}>{PLAN_LABEL[p.plan] ?? p.plan}</span>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 6, font: `500 10px ${MONO}`, color: p.wildcard ? C.green : C.muted, cursor: "pointer" }}>
                <input type="checkbox" checked={p.wildcard} onChange={(e) => setPlan(p.plan, { wildcard: e.target.checked })} />
                all coins (wildcard)
              </label>
              <button
                type="button"
                onClick={() => void save(p.plan)}
                style={{ font: `600 10px ${MONO}`, color: C.bg, background: C.green, borderRadius: 8, padding: "7px 14px", border: "none", cursor: "pointer" }}
              >
                SAVE
              </button>
            </div>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 7, opacity: p.wildcard ? 0.4 : 1, pointerEvents: p.wildcard ? "none" : "auto" }}>
            {universe.map((coin) => {
              const on = p.wildcard || p.coins.includes(coin);
              return (
                <button
                  key={coin}
                  type="button"
                  onClick={() => toggleCoin(p.plan, coin)}
                  style={{ font: `600 10px ${MONO}`, color: on ? C.bg : C.fg, background: on ? C.green : C.bg, border: `1px solid ${on ? C.green : C.border}`, borderRadius: 14, padding: "5px 11px", cursor: "pointer" }}
                >
                  {on ? "✓ " : ""}
                  {coin}
                </button>
              );
            })}
          </div>

          {savedPlan === p.plan && (
            <span style={{ font: `400 9px ${MONO}`, color: C.green }}>Saved. Applies on the next scan.</span>
          )}
        </div>
      ))}
    </div>
  );
}
