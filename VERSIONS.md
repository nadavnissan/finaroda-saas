# VERSIONS — FINARODA SaaS

> מעקב גרסאות (SemVer). כל bump נרשם כאן. החדש למעלה.

| גרסה | תאריך | תקציר | Commit |
|------|-------|--------|--------|
| v0.6.0 | 2026-07-12 | MINOR — F13 "First 60 Seconds" onboarding. Episode engine (mig 023 episodes + real Bybit klines seed with empirical-truth assertions; E1 re-picked LINK→BTC 25/06), server-side outcome withholding (setup vs reveal), xp_events (mig 024, server-priced + idempotent, 300 total), onboarding_funnel_events (mig 025). Router api/onboarding.py (episodes/reveal/xp/funnel/complete). Frontend /onboarding: OnboardingFlow S0–S11+S1a, in-app SVG EpisodeChart (real klines, not recharts — avoids React-19 peer-dep), ConceptTooltip (placeholder content), XPMeter, Disclaimer every screen, SCAN vibrate+silent iOS fallback. pytest 39/39 · tsc/eslint clean · next build 17/17. | <hash> |
| v0.5.3 | 2026-07-11 | PATCH — DOCS: XP_ECONOMY.md v1.0 anchored + debt closed. UX §5 + PRD F5 tier fix ("מדייק"/Precise = XP threshold, **not** what-if outcomes; what-if quality = dashboard stat only) · PRD F6 links XP_ECONOMY (+100/lesson, ranks unlock bonus modules orthogonal to plan gates) · SPEC §5.6 new `xp_events` table (UNIQUE user+source+ref, server-side only, closed-list sources) · Onboarding §4/§8 debt marked closed · ATP TC-DOCS-XP01. Also fixed the identical contradiction in PRD F5 (instruction named only UX §5) — flagged for Nadav. Docs only, אפס קוד. | <hash> |
| v0.5.2 | 2026-07-11 | PATCH — DOCS: E9 Horizon selector. PRD F1c (SWING 1–7d active / POSITION weeks+ locked, "In validation. Unlocks when it earns it.") + V2 backlog (position engine) · UX §3/§8 pre-scan controls row · ROADMAP X1 · ATP TC-DOCS-E06. Honesty guardrail baked into AC2 (no position engine yet → "planned" not "in validation"; ⚠ open for Nadav). Docs only. | <hash> |
| v0.5.1 | 2026-07-11 | PATCH — DOCS: יישום section E של ALIGNMENT (11/07). E1 Concept Tooltip (F14) · E2 free-coin V2+"Learning mode" label · E3 טבלת השוואה חובה בעמוד Subscribe (F7/UX §6 + TC-J-002) · E5 hamburger nav (X1) · E6 SCAN navigator.vibrate+fallback (SPEC §6.2) · E7 Live Chart+overlays (F15, Free=chart+EMA200/paid=all) · E8 ticker banner REJECTED (PRD §17). Docs only, אפס קוד. | <hash> |
| v0.5.0 | 2026-07-09 | MINOR — D1 trial ללא כרטיס: start_trial בלי כרטיס/tokenization + next_billing NULL, expire_trials→Free (לא expired), renewal מחייב רק active, תזכורת יום 11 (TRIAL_REMINDER_LEAD_DAYS), migration 022 (trial_ended_to_free), paywall copy. TEST mode. pytest 27/27. | <hash> |
| v0.4.8 | 2026-07-09 | DOCS — יישור מסמכי מקור-אמת ל-ALIGNMENT_2026-07-09: D1 trial ללא כרטיס (change order), D2 Free tier, F13 onboarding simulation, F3 reveal-gating, notes ל-regime_state + episodes, empirical-truth principle. Docs only, אפס קוד/מנוע. | <hash> |
| v0.4.7 | 2026-07-01 | CHORE — pnpm workspace (workspace:* + exports + root lockfile) so @finaroda/scoring-engine resolves natively on Vercel (no toggle). Metadata/config only. | <hash> |
| v0.4.6 | 2026-07-01 | CHORE — frontend → Vercel (vercel.json); resolves the link:../shared monorepo engine that Railway root=frontend couldn't. Backend stays on Railway. | <hash> |
| v0.4.5 | 2026-07-01 | CHORE — frontend build: nix-provided pnpm (nixPkgs) to fix `pnpm: command not found` PATH error. Config only. | <hash> |
| v0.4.4 | 2026-07-01 | CHORE — frontend build: pnpm via npm (not corepack) to fix keyid error; +frontend.Dockerfile fallback. Config only. | <hash> |
| v0.4.3 | 2026-07-01 | CHORE — frontend/nixpacks.toml (Node-only) + packageManager, so Railway frontend builds as Node not Python. Config only. | <hash> |
| v0.4.2 | 2026-07-01 | CHORE — Next.js 15.5.4→15.5.19 (CVE-2025-66478 fix) + eslint-config-next, to unblock Railway staging. Dep bump only. | <hash> |
| v0.4.1 | 2026-07-01 | P2 scorer wired — real scoreDirection (momentum profile) live, 85/82 PASS/WATCH gate on, pullback/continuation logged; score_log.profile (mig 021) | <hash> |
| v0.4.0 | 2026-07-01 | P2 — scan core: client-side Bybit fetch + Trading Blueprint (levels engine imported), Analysis Lens, Risk Style, persistence; score marked pending (pass 2) | <hash> |
| v0.3.1 | 2026-07-01 | DOCS — regulatory reframing (calculator terminology, formula transparency, Analysis Lens, Risk Style, RED LINE). PRD v2.1 · UX v1.2 · LEGAL v2. Engine unchanged. | <hash> |
| v0.3.0 | 2026-07-01 | P1 — תשתית חיה: auth מוקשח (magic-link+Google+beta gate), Cardcom v11 (TEST mode), deploy config, frontend מחובר | <hash> |
| v0.2.1 | 2026-07-01 | P1.5 — placeholder ל-scoring-engine המשותף (shared/), ממתין לחילוץ מהכלי האישי | <hash> |
| v0.2.0 | 2026-06-30 | P0 — שלד נקי: backend+frontend, 18 migrations מודרניות, Cardcom יחיד, validation ירוק | <hash> |
| v0.1.0 | YYYY-MM-DD | Init — scaffolding + מסמכי מקור-אמת ובקרה | <hash> |
