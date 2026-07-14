"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

import { C } from "@/lib/onboarding/types";
import { REFERRAL_KEY } from "@/lib/app/promotions";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";

// /r/<code> — store the referral code client-side (D-S6) and send the visitor to sign in.
// Binding happens once, server-side, when a NEW account is created with this code.
export default function ReferralLanding() {
  const router = useRouter();
  const params = useParams<{ code: string }>();

  useEffect(() => {
    const raw = Array.isArray(params?.code) ? params.code[0] : params?.code;
    const code = (raw ?? "").trim().toUpperCase();
    if (code && typeof window !== "undefined") {
      try {
        window.localStorage.setItem(REFERRAL_KEY, code);
      } catch {
        // localStorage may be unavailable (private mode) — binding just will not apply.
      }
    }
    router.replace("/login");
  }, [params, router]);

  return (
    <main style={{ minHeight: "100vh", background: C.bg, color: C.fg, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: MONO }}>
      <span style={{ font: `400 12px ${MONO}`, color: C.muted, letterSpacing: 1 }}>Loading your invite…</span>
    </main>
  );
}
