"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Package B B2 replaced the P1 paywall with /subscribe (4-plan comparison + D1
// trial). This legacy route now redirects so old links / onboarding forks land on
// the canonical Subscribe page.
export default function PaywallRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/subscribe");
  }, [router]);
  return null;
}
