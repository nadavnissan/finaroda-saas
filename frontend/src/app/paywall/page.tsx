"use client";

import { useState } from "react";

import { api } from "@/lib/api";

// paywall — 3 FINARODA plans (SPEC §9). Wires to Cardcom initiate.
const PLANS = [
  { id: "basic", name: "Basic", price: "₪50/mo", coins: "2 coins per scan" },
  { id: "advanced", name: "Advanced", price: "₪100/mo", coins: "5 coins per scan" },
  { id: "pro", name: "Pro", price: "₪150/mo", coins: "10 coins per scan" },
];

export default function PaywallPage() {
  const [message, setMessage] = useState("");

  async function choose(plan: string) {
    setMessage("");
    const res = await api.initiateCheckout(plan);
    if (res.ok && res.data && typeof res.data === "object" && "redirect_url" in res.data) {
      window.location.href = (res.data as { redirect_url: string }).redirect_url;
    } else if (res.status === 503) {
      setMessage("Payments are in test mode right now. Check back soon.");
    } else if (res.status === 401) {
      window.location.href = "/login";
    } else {
      setMessage(res.error?.message ?? "Could not start checkout.");
    }
  }

  return (
    <main>
      <h1>Choose a plan</h1>
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", justifyContent: "center" }}>
        {PLANS.map((p) => (
          <div key={p.id} style={{ border: "1px solid #333", borderRadius: 12, padding: "1rem", minWidth: 160 }}>
            <h2>{p.name}</h2>
            <p>{p.price}</p>
            <small>{p.coins}</small>
            <div>
              <button onClick={() => choose(p.id)} style={{ marginTop: "0.75rem" }}>
                Start trial
              </button>
            </div>
          </div>
        ))}
      </div>
      {message && <p>{message}</p>}
      <small>14-day trial, card on file. Analysis, not advice.</small>
    </main>
  );
}
