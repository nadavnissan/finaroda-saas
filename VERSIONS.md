# VERSIONS — FINARODA SaaS

> מעקב גרסאות (SemVer). כל bump נרשם כאן. החדש למעלה.

| גרסה | תאריך | תקציר | Commit |
|------|-------|--------|--------|
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
