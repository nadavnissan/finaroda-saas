"use client";

// In-app billing banner (Stage 3, D-B5/D-B6). Server-authoritative: reads
// /api/cardcom/status and shows a banner only for a state that needs attention
// (past_due / cancelled / expired). Healthy states render nothing. The CTA routes to
// /subscribe (update card or re-subscribe). Access itself is enforced server-side; this
// is the visible signal.
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/lib/api";
import { billingBanner, type BillingBannerModel } from "@/lib/app/billing";
import { C } from "@/lib/onboarding/types";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";

interface StatusResponse {
  subscription_status: string;
  cancelled_pending_at?: string | null;
}

function fmtDate(iso?: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString();
}

const ACCENT: Record<BillingBannerModel["kind"], string> = {
  past_due: C.amber,
  cancelled: C.muted,
  expired: C.amber,
};

export function BillingBanner() {
  const router = useRouter();
  const [model, setModel] = useState<BillingBannerModel | null>(null);

  useEffect(() => {
    let alive = true;
    void apiFetch<StatusResponse>("/api/cardcom/status").then((r) => {
      if (!alive || !r.ok || !r.data) return;
      setModel(billingBanner(r.data.subscription_status, fmtDate(r.data.cancelled_pending_at)));
    });
    return () => {
      alive = false;
    };
  }, []);

  if (!model) return null;
  const accent = ACCENT[model.kind];

  return (
    <div
      role="status"
      style={{
        margin: "10px 16px 0",
        background: C.panel,
        border: `1px solid ${accent}`,
        borderRadius: 10,
        padding: "10px 13px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <span style={{ font: `700 10px ${MONO}`, letterSpacing: 0.5, color: accent }}>
        {model.title.toUpperCase()}
      </span>
      <span style={{ font: `400 10px/1.5 ${MONO}`, color: C.fg }}>{model.message}</span>
      <button
        type="button"
        onClick={() => router.push("/subscribe")}
        style={{
          alignSelf: "flex-start",
          marginTop: 2,
          background: "none",
          border: `1px solid ${accent}`,
          borderRadius: 7,
          padding: "6px 12px",
          font: `700 9px ${MONO}`,
          letterSpacing: 0.5,
          color: accent,
          cursor: "pointer",
        }}
      >
        {model.cta.toUpperCase()}
      </button>
    </div>
  );
}
