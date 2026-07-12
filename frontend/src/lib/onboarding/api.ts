// Onboarding F13 API client. Reuses the shared httpOnly-cookie fetch wrapper.
import { apiFetch } from "@/lib/api";

import type { EpisodeReveal, EpisodeSetup, XPState } from "./types";

export const onboardingApi = {
  // Episode SETUP — outcome + reveal candles are withheld server-side (AC).
  getEpisode: (extId: string) =>
    apiFetch<EpisodeSetup>(`/api/onboarding/episodes/${extId}`, { method: "GET" }),

  // Explicit reveal — returns the withheld outcome + playback candles.
  revealEpisode: (extId: string) =>
    apiFetch<EpisodeReveal>(`/api/onboarding/episodes/${extId}/reveal`, { method: "POST" }),

  // XP is granted once, server-side, at completion (see complete()). Read-only here.
  getXp: () => apiFetch<XPState>("/api/onboarding/xp", { method: "GET" }),

  // Funnel event (optional-auth: anon before signup, user after).
  funnel: (stage: string, detail?: Record<string, unknown>, anonId?: string) =>
    apiFetch("/api/onboarding/funnel", {
      method: "POST",
      body: JSON.stringify({ stage, detail: detail ?? null, anon_id: anonId ?? null }),
    }),

  complete: () => apiFetch("/api/onboarding/complete", { method: "POST" }),
};
