# SESSION HANDOFF — FINARODA SaaS

> מוחלף בסוף כל סשן. מסמך "איך להיכנס", לא ארכיון.

---

> NOTE: from 2026-07-01 this handoff is written in **English** (terminal mangles Hebrew).

## Where we are now
- **Active branch:** dev
- **Last commit (dev):** Package B phase 2 — B4 dashboard + B5 profile + B6 academy + B7 admin (v0.9.0) — closes Package B, on top of phase 1 (v0.8.0).
- **Validation:** ✅ all green — **pytest 66/66**, **frontend unit 18/18** (node --test type-strip), **shared node --test 14/14**, **tsc clean**, **eslint clean**, **next build clean (20/20)**, em-dash lint 0.
- **main:** = `1338a26` (P2 scorer). Everything since (v0.4.2–v0.9.0) is **dev only** — Nadav merges to main manually.

## Latest — Package B phase 2: B4 dashboard + B5 profile + B6 academy + B7 admin (v0.9.0, code + migration 028)
- **What shipped:** the whole post-scan shell. **B4** "What Would Have Happened" (F3, the retention core) with real reveal-gating; **B5** profile + rank ladder; **B6** academy shell (12 modules); **B7** admin console (6 sections). Backend pytest **66/66**; frontend builds clean (20 routes).
- **B4 reveal-gating (the AC that matters):** `journal_scenarios` (mig 028) is created from each scan — one `pass` scenario per PASS momentum row, one `no_setups_day` per skip day; **WATCH is never a scenario**. A server-side job (`backend/app/tasks/journal_tasks.py` + `scripts/run_resolve_scenarios.py`) resolves open scenarios against subsequent Bybit daily candles (trigger fill → target/risk/7-day expiry) into an honest hypothetical R. **Outcomes are withheld from every client payload until the user's next scan reveals them** (`core/journal.on_scan` reveals-then-creates); unrevealed rows carry zero outcome data in the payload AND the DOM (regression: backend `test_journal_withholds_outcome_until_reveal` asserts the value/label are absent from the whole response; frontend `scenarioOutcome()` returns null when unrevealed). Nav badge = `/api/journal/badge` count only. +25 XP on viewing a revealed outcome (idempotent per scenario).
- **B5/B6/B7:** profile (`/api/profile`, call-sign in `user_settings` with email fallback, ladder from `levelFor`, Lens/Risk settings persist); academy (12 modules = the 12 `academy` ids in the tooltip JSON, seeded from each term's `what`; +100 only for real-content modules ≥3 terms, stubs award 0; tooltip `/academy#<id>` deep-link highlights the module; plan + rank gating); admin (`require_admin`→403, real-data overview/MRR/churn, user overrides audited to `admin_events`, ticket queue+reply with email-stub, `system_settings` editor with score-gate/card-off shown LOCKED, broadcast→in-app banner that never covers SCAN/disclaimer, notifications log).
- **⚠ DECISIONS MADE THIS SESSION (need Nadav sign-off):**
  1. **CAPITAL SAVES** implemented as a **PASS whose trigger never filled in the window** (capital preserved, no entry) — faithful to the prompt's "scenario per PASS + no-setups only; WATCH never a scenario", but different from the design frame's per-coin non-passer SAVE row (LINK). Extendable to per-coin saves later if you prefer the frame's literal reading.
  2. **Academy "real content" = ≥3 seed terms** → 9 completable lessons (+100), 3 reference stubs (0 XP: volume_basics, positioning_basics, regime_transitions).
  3. **Module titles use colons** (no-em-dash rule) instead of the frame's em-dash titles.
  4. **Admin shows real DB data** (not the frames' SAMPLE); churn is a real-but-placeholder query until exit-survey data accrues.
  5. **New XP source `admin_grant`** (B7 "Grant XP (support)") added to `XP_ECONOMY.md` §1 as an audited admin-only source (not user-earnable, not shown in "How XP is earned").
- **⬜ Gaps / follow-ups:** the resolution job is server-side and needs the cron wired in the deploy (`python -m backend.scripts.run_resolve_scenarios`, daily) — it is NOT auto-run; scenarios stay `open` until it runs. Call-sign is not yet persisted from onboarding S9 (profile owns it with an email fallback; wiring S9→`/api/profile/settings` is a small follow-up). Admin console is desktop-first (no mobile layout). Email sends (ticket reply, broadcast email, day-11) are logged stubs. Fonts still system-fallback (Design round 2).
- **Ready for production?** Not yet — recommend a manual click-through: B4 reveal flow (scan → resolve job → next scan reveals), B7 admin as an admin user, B6 deep-link from a tooltip. Nadav decides the dev→main merge.
- **Untouched (as required):** RED LINE §3.5.5, 85/82 threshold, scoring engine/scorer, calculator terminology, main branch.

## Latest — Package B phase 1: B1 scan + B2 subscribe + B3 nav (v0.8.0, code + migration 027)
- **What shipped:** the full scan screen (B1a–B1g, the product's heart) replacing the P2 page; the Subscribe page (B2); and the post-auth hamburger nav + unified header (B3). Backend gating is now server-authoritative.
- **Shared engine (S/R canon):** ported the personal tool's `findRecentSwingLevels` ({swingHigh,swingLow}) into `@finaroda/scoring-engine` byte-faithfully — it is the one S/R source the scorer measures against. Deleted `frontend/src/lib/onboarding/levels.ts` (the week-old SaaS pivot approximation) and repointed EpisodeChart + the new B1 chart to a shared `swingLevels` adapter. Added an **equivalence test** (shared/scoring-engine.test.js) that asserts identical swings vs a verbatim copy of engine.mjs across many deterministic vectors. Per your decision, the onboarding chart's drawn S/R may shift slightly — intended, so the chart draws exactly what the engine scores.
- **B1 gating (server-authoritative, your decision):** the scan stays client-side, but `GET /api/scan/entitlements` is binding (coins/scan, chart_layers, scans/day per tier from system_settings, mig 027), and `POST /api/scan/events` rejects an over-limit scan (403 PLAN_COIN_LIMIT). First-scan-of-day XP (+50) is credited server-side, idempotent per calendar day (source=daily_first_scan, ref=date); the client only learns whether it was awarded (drives the chip). Chart layers gate EMA7 + Blueprint levels (Free=EMA200 only + SEE PLANS).
- **E7b:** every scanned coin (incl. non-passers) is tappable → the same Chart Standard v1 + a plain-language "why not" line naming only the blocking check (regime = price vs EMA200, else the threshold) with its Concept Tooltip. No score/weight/formula is exposed; snapshot header is timestamped (not live).
- **B2:** 4-plan comparison table (TC-J-002, Free first + always visible), D1 no-card trial CTA + 3 trust shields, "same engine, same threshold" line. Prices/coins come from system_settings via `GET /api/plans`. Legacy `/paywall` now redirects to `/subscribe`; the onboarding trial fork routes to `/subscribe`.
- **B3:** unified header (≡ / FINARODA / LevelMeter chip) that kills the old per-page header; hamburger drawer (Dashboard[UPDATE]/Profile/Academy/Settings) with a LevelMeter identity block; "Report a problem" files a real ticket (`POST /api/support/tickets`).
- **⚠ DECISIONS ALREADY MADE BY NADAV (this session):** (1) gating = server-as-authority + client compute (unpersisted local computation is acceptable leakage). (2) swing canon = the personal-tool algorithm (not the SaaS pivot). (3) journal scenarios from scans **deferred** — F3 plumbing does NOT exist yet; scans persist to score_log + decision_snapshots as before. (4) B7 admin console (settings editor + ticket queue) = phase 2.
- **⬜ Gaps / follow-ups:** F3 journal-scenario creation (score_log→journal) still to be built; scans_per_day is exposed in entitlements but only coins/scan + chart_layers are HARD-gated this phase (Free 1-scan/day not enforced — matches B1c "scan again always allowed"); the empty-state discipline badge shows a real scan count, NOT a fabricated "skipped X of Y days" ratio (no scan_events per-day skip endpoint yet — honest per §8); B7 admin console (edit prices/coins, ticket queue) is phase 2; fonts still system-fallback (Design round 2). Nav routes /profile, /settings are stubs (may 404 until built).
- **Untouched (as required):** RED LINE §3.5.5, 85/82 threshold, scoring engine/scorer, calculator terminology, main branch.
- **Ready for production?** Not yet — recommend a manual mobile click-through of B1/B2/B3 first (charts, tooltips, gating visuals, trial CTA). Nadav decides the dev→main merge.

## Latest — F13 validation round 2 polish (v0.7.1, frontend-focused)
- Applied Nadav's 10 click-through polish items.
- **S0** now has a **LET'S START** button (no auto-advance). **Header** redesigned: the XP bar + gray caption became a compact terminal **LevelMeter** (hexagon rank badge + rank + XP + progress toward the next rank, XP_ECONOMY ladder 1000/3000/8000).
- **Signup flash (reopened):** fixed with a **render-gate** — the flow does not render until the `/me` routing check resolves, so a late async redirect can't yank a mid-flow screen (the concrete cause for a returning/completed user during repeated testing). S5→S6 also consolidated to a single `createOnce` transition. Unit-tested.
- **Tooltip context guard:** `renderNow` now suppresses the whole `now` line when a simple placeholder is missing (long_short shows nothing before a choice is made; fixes the premature-direction glitch). Unit-tested.
- **Chart:** symbol is a prominent separate badge (all charts incl. S10); Trigger/Risk/Target + EMA/S-R labels are decluttered (no overlap). **S8:** pre-scan framing line ("Real case: ADA, 25 Jun 2026. Press SCAN..."), the verified **Calculated Risk Level 0.1511** is seeded + drawn, and a **Why PASS** popover lists the stored passed checks (regime/weekly/timing/volume) using the locked concept labels.
- **XP = LEVEL framing** with a **level-up celebration** (distinct vibration + terminal animation) that fires ONLY on rank crossings; ordinary XP gains get the subtle E6 buzz. Onboarding tops out at 300 (Level 1) so the celebration is dormant here but implemented + unit-tested.
- **S10 copy** made unambiguous ("revealed on your NEXT scan"). **S11 table** wrapped in overflow-x synced to the frame.
- **New frontend unit-test harness:** `frontend/tests/*.test.ts` via `node --test --experimental-strip-types` (`npm run test:unit`), covering level math, tooltip suppression, and the transition guard. `allowImportingTsExtensions` added to tsconfig for the `.ts` test imports.
- **⚠ Carried-over, still open for Nadav:** EpisodeChart is in-app SVG (not recharts); Google/Apple OAuth SDK is round-2 (magic-link fully wired, closes the loop in dev); E1 = BTC (LINK was a curation error). Fonts (IBM Plex Mono / Space Grotesk) are referenced via CSS font-family but not yet self-hosted/imported — they fall back to system mono; loading them is a Design-round-2 item.
- **⬜ Still pending:** manual mobile click-through (header, tooltip clipping, chart interactions, level-up visual). 
- **Untouched (as required):** RED LINE §3.5.5, 85/82 threshold, scoring engine/scorer, calculator terminology, main branch.

## Latest — F13 validation round 1 + tooltip content (v0.7.0, code + migration 026)
- Applied Nadav's click-through notes + wired the Concept Tooltip content + built Chart Standard v1.
- **Tooltips:** `concept_tooltips_content.json` (root, locked, 46 terms) is now wired. `concepts.ts` loads it + a `now`-template engine (`{key}` and `{cond:'a'|c2:'b'}`, missing placeholder renders empty). Bubble is viewport-clamped/flips (never clipped on mobile), has an X and closes on tap-outside. A pytest drift-guard asserts the bundled frontend copy matches root.
- **Bug fixes:** (a) **XP anti-farming** — onboarding XP is now a single lifetime grant (300) credited at completion; migration 026 adds a partial unique index on `xp_events(user_id) WHERE source='onboarding'`; replaying grants 0 (regression test). (b) **Routing** — /onboarding guards on `/me` and `router.replace('/scan')` for completed users; S11 exit uses replace; back never re-enters. (c) **Signup flash** — removed a side-effect-in-state-updater anti-pattern + added a `signingUp` guard = one clean S5→S6 transition. (d) Live **"new scan"** returns to the controls (idle), not an immediate re-scan. (e) Line-orphan control via `noOrphan()` + CSS text-balance.
- **Product decisions (Nadav 12/07):** BUY/SELL → **LONG/SHORT**. **Two different S1a branches, both real candles:** LONG = the fade (−10%), SHORT = the **squeeze** (+2.06% against the short to 65,624, then fade). E1's decision candle was moved to the 20 Jun surge so both branches are empirically true; the seed builder asserts squeeze ≥1.5% and fade ≤−5%. **No-em-dash copy rule** enforced across all copy + a pytest lint that fails on U+2014.
- **Chart Standard v1** (one component, the Package B base): on-chart context header, EMA200+EMA7 with labels, swing S/R (`computeRangeLevels`, pivots), Blueprint levels (S8), Spike/Entry annotation pills that open tooltips, candle-tap OHLC.
- **⚠ Carried-over decisions still open for Nadav** (from v0.6.0): EpisodeChart is in-app SVG (not recharts); Google/Apple OAuth SDK is round-2 (magic-link fully wired, closes the loop in dev); E1 = BTC (LINK was a curation error).
- **⬜ Still pending:** manual mobile click-through (tooltip clipping, chart interactions, the 12-screen flow); visual polish (fonts/animations) = Design round 2.
- **Untouched (as required):** RED LINE §3.5.5, 85/82 threshold, scoring engine/scorer, calculator terminology, main branch.

## Latest — F13 onboarding implemented (v0.6.0, code + migrations 023–025)
- **What shipped:** the full "First 60 Seconds" onboarding — episode engine, 12 screens (S0–S11) + the S1a failure branch, XP, funnel, server-side outcome withholding. Backend **pytest 39/39**; frontend **builds clean**.
- **Episode engine:** `episodes` table (mig 023) seeded from **real Bybit daily klines** (`backend/data/onboarding_episodes.json`) with **empirical-truth assertions in the builder** — it throws if the real klines don't support the documented entry/outcome. Each candle carries real EMA7/EMA200. Charts render **in-app as SVG** from stored klines — never external captures.
- **Withholding (AC):** `GET /api/onboarding/episodes/{id}` returns only the pre-decision setup candles; the outcome (win/loss, R, %) and reveal candles are returned ONLY by `POST …/{id}/reveal` (S1 trap, S10 time-machine). Verified by test that the withheld numbers are absent from the setup payload.
- **XP:** `xp_events` (mig 024) — amounts are server-authoritative (closed map 50/100/50/100 = 300), award is idempotent via `UNIQUE(user,source,ref)`. **Funnel:** `onboarding_funnel_events` (mig 025), anon before signup / user after. `POST /complete` marks `onboarding_completed_at`.
- **⚠ DECISIONS THAT NEED NADAV'S SIGN-OFF:**
  1. **E1 trap re-picked LINK → BTCUSDT 25/06.** The original LINK 30/06→02/07 window actually *rose* in real klines (LINK's fade came after 02/07 — a curation error), which would have broken the trap lesson + violated empirical-truth. Per your call I used the 25 Jun BTC anchor-DIR-FAIL (61,753 → 57,802, −6.4%; green spike 06-22 → fade), which is our own verified material. LINK is now history-only in the docs. Documented in `EPISODES_AND_VERIFIED_NUMBERS.md`.
  2. **EpisodeChart uses an in-app SVG candlestick, NOT recharts** (the spec named recharts). Reason: recharts has no native candlestick and adds a React-19 peer-dependency risk to the Vercel build; SVG is the spec's own "v25.67 engine" reference, zero-dep, real klines. Same visual outcome. Revert to recharts if you prefer.
  3. **Concept Tooltip definitions are placeholders** (keyed by term id) — you supply the 35+ plain-language definitions from the internal guide; I did not write financial definitions.
  4. **S5 signup:** magic-link path is fully wired (in dev it closes the loop in-session so XP/completion persist); Google/Apple are present as buttons but full OAuth-SDK wiring is the round-2 auth bundle.
- **⬜ Still pending:** manual runtime click-through of all 12 screens (needs both servers + browser); visual polish (Space Grotesk / IBM Plex Mono fonts, animations) = Design round 2; Google/Apple OAuth SDK.
- **Untouched (as required):** RED LINE §3.5.5, 85/82 threshold, scoring engine/scorer, calculator terminology, main branch.

## Latest — DOCS XP economy anchored + debt closed (v0.5.3, docs only, no code)
- Anchored **`XP_ECONOMY.md` v1.0** (locked, repo root) into the source-of-truth docs; closed the XP-economy debt (Onboarding §8 / ALIGNMENT D3). **No app/engine/scorer/backend change.**
- **UX §5 + PRD F5 — tier contradiction fixed:** the "מדייק"/Precise tier no longer keys on "positive what-if history" (that rewarded outcomes → broke trust-not-engagement). Now **XP threshold only**; what-if quality stays a **dashboard statistic**, never a tier criterion. Explicit correction note cites `XP_ECONOMY.md` §4.
- **PRD F6 (Academy):** links `XP_ECONOMY.md` — +100 XP/lesson; XP ranks unlock **bonus knowledge modules** (Spike Autopsies, Regime Transitions) **orthogonal to plan gates**. New AC4.
- **SPEC §5.6 (new):** `xp_events (user_id, source, ref, amount, ts)` with `UNIQUE (user_id, source, ref)` (idempotent farming-guard), closed-list sources, **server-side write only**, ranks derived from `SUM(amount)` (no stored rank column).
- **Onboarding §4/§8:** §8 marked **✅ closed → `XP_ECONOMY.md`**; §4 points to the closed XP sources (+50 first daily scan · +100 lesson · +25 journal reveal · no streak in v1).
- **ATP:** +TC-DOCS-XP01 (doc-check).
- **⚠ FLAG for Nadav (scope):** the instruction named only **UX §5** for the tier fix, but the identical "positive what-if history" contradiction lived in **PRD F5** too. I fixed both — leaving PRD F5 would keep a RED-LINE contradiction between two source-of-truth docs. If you'd rather I'd stayed strictly in UX §5, say so and I'll revert the F5 edit.
- **Untouched (as required):** RED LINE §3.5.5, 85/82 threshold, client-side fetch, calculator terminology, engine/scorer/backend. `xp_events` migration ⬜ pending (P3/P4).

## Latest — DOCS E9 Horizon selector (v0.5.2, docs only, no code)
- Applied **E9** of `ALIGNMENT_2026-07-09.md` to the source-of-truth docs. **No app/engine/scorer/backend change.**
- **New PRD F1c — Horizon Selector:** pre-scan control. **SWING (1–7 days) active** in v1 (the verified EMA7-slope edge is a swing edge). **POSITION (weeks+) locked** — approved copy "In validation. Unlocks when it earns it." + tooltip. Unlock = 30+ outcomes / 2+ regimes; candidate Pro feature. POSITION engine → PRD V2 backlog.
- **UX §3 + §8:** Horizon added to the pre-scan controls row (next to Lens/Risk Style). Documented that POSITION is a **separate validated universe**, not a cosmetic toggle; added a minimalism ceiling note (3 controls).
- **ROADMAP X1:** Horizon selector added to Design round-2 scope. **ATP:** +TC-DOCS-E06.
- **⚠ OPEN — honesty guardrail (needs Nadav's call):** the approved tooltip claims the position engine "is being validated against live outcomes" — but **there is no position engine** (the only verified edge is swing/EMA7; nothing logs position outcomes). Per Principle 8 (empirical truth in copy) this claim isn't currently true. Baked into **F1c AC2 + TC-DOCS-E06**: copy is truthful only once a position-outcome log actually exists; until then POSITION is "planned," not "in validation." Also flagged: by the 30+/2+regimes criterion, position outcomes resolve over weeks → ~multi-year to unlock → **POSITION may never unlock; no ETA promised.** Decision needed: (a) build a position-outcome log before showing the copy, or (b) soften the copy to future-tense.
- **Untouched (as required):** RED LINE §3.5.5 (preserved per-universe), 85/82 threshold, client-side fetch, calculator terminology, engine/scorer/backend.

## Latest — DOCS section-E alignment (v0.5.1, docs only, no code)
- Applied **section E** of `ALIGNMENT_2026-07-09.md` (Nadav's 2026-07-11 product decisions) to the source-of-truth docs. **No app/engine/scorer/backend change.**
- **E1 — Concept Tooltip:** new **PRD F14** (F-education) — one shared learn-bubble on every term from onboarding onward, content sourced from Academy (F6), display-only. UX §3 + §8.
- **E2 — free-coin analysis:** added to PRD **V2 backlog only** (paid plans, after validation + Nadav approval, mandatory "Learning mode — outside the validated universe" label). Not v1.
- **E3 — comparison table on Subscribe:** PRD F7 + UX §6 — the Free-vs-paid table ("Free forever": 1 scan/day · 2 coins · full Blueprint · journal 7 days · no export) MUST render on the Subscribe page. New paywall AC + **ATP TC-J-002** copy-guard.
- **E5 — post-payment hamburger nav** (Dashboard/Profile/Academy/Settings): into Design round-2 scope (ROADMAP X1). UX §8.
- **E6 — SCAN vibrate:** SPEC §6.2 — `navigator.vibrate` with silent fallback (iOS Safari unsupported → no buzz, no error).
- **E7 — Live Chart + overlays per coin:** new **PRD F15** + UX §3 — recharts-from-kline chart with explanation layers; gating Free = chart+EMA200 / paid = all layers (EMA7 + Blueprint levels). Design round-2. display-only.
- **E8 — running ticker banner: REJECTED** — recorded in PRD §17 (new "פריטים שנדחו" subsection): conflicts with trust-not-engagement + index/commodity data licensing; alternative = existing static per-scan marketContext line; reopen only as an off-by-default opt-in.
- **E4** (leveraged-ETF research) — personal-tool research track only, **does not touch SaaS**; SaaS docs deliberately unchanged.
- **ATP:** +TC-J-002 (E3 copy-guard) + TC-DOCS-E01..E05 (E01-E03 ⬜ pending implementation; E04/E05 ✅ doc-check).
- **⬜ Still pending (implementation):** F14 tooltip, F15 live chart, the Subscribe-page table, SCAN vibrate, hamburger nav — all land under ROADMAP **X1** (Design round-2) / **P4**.
- **Untouched (as required):** RED LINE §3.5.5, 85/82 threshold, client-side fetch, calculator terminology, engine/scorer/backend.

## Latest — D1 trial WITHOUT card implemented (v0.5.0, code + migration 022)
- **Model change (SPEC §9/§12.3, PRD F7):** trial no longer needs a card. Card capture happens ONLY at explicit paid conversion (`initiate_checkout`, Cardcom LowProfile). Still TEST mode (`FEATURE_CARDCOM_LIVE=false` → 503 on initiate, dry-run renewal).
- **`start_trial`** (`core/cardcom_service.py`): no card/tokenization; `next_billing_at=NULL`; default plan `pro` (full 14-day Pro). Re-trial → 409.
- **`expire_trials`**: trial end → **Free** (`tier='free'`, `subscription_status='none'`, `next_billing_at=NULL`) — never expired/blocked, never charged. New event `trial_ended_to_free`. Returns `{"moved_to_free": N}`.
- **`run_renewal_batch`**: narrowed to `subscription_status='active'` — trials are never billing candidates.
- **Day-11 reminder:** `trial_ending_soon_task` fires `TRIAL_REMINDER_LEAD_DAYS` (default 3) before end (day 11 of 14). New config `TRIAL_REMINDER_LEAD_DAYS`. railway.toml comment day-13→day-11.
- **Migration 022** (`022_subscription_events_trial_to_free.py`): rebuilds `subscription_events` to add `event_type='trial_ended_to_free'` to the CHECK (SQLite can't ALTER a CHECK). Table count unchanged.
- **Frontend:** `paywall/page.tsx` copy fixed ("no credit card / card only at paid plan / continue on Free"); button "Start trial"→"Choose plan".
- **Free representation:** `tier='free' + subscription_status='none'` (the existing free state) — no users-table rebuild needed. `'free'` is not a valid `subscription_status` (CHECK), by design.
- **Tests:** TC-F-005/006 rewritten (no-card trial + Free downgrade), TC-F-007 (re-trial 409), TC-F-008 (renewal never charges trials). ATP TC-DOCS-001/002 → ✅.
- **⬜ Still pending for P4 (ROADMAP S3):** live plans + full paywall, **Free-tier limit enforcement** (1 scan/day, F3 7-day window, export gate) from `system_settings`, coupons, referral. This task did the trial/billing spine only.

## Latest — DOCS alignment to ALIGNMENT_2026-07-09 (v0.4.8, docs only, no code)
- Aligned all source-of-truth docs to Nadav's 2026-07-09 decisions. **No app/engine/scorer/backend change.**
- **D1 — Trial WITHOUT card** (approved change order, supersedes the locked "trial with card"): SPEC §9/§12.3, PRD F7 (flow + AC1/AC2 rewritten) + §17, UX journey step 4 + §6, LEGAL §2.6. 14 days · no tokenization at signup · no auto-charge · day-11 reminder · active choice at end (paid plan or Free) · card capture moves to the paid-conversion moment.
  - ⚠ **Code still tokenizes:** `start_trial`/renewal in `core/cardcom_service.py` are UNCHANGED and still set `next_billing` (card-based). Reworking them is **⬜ pending implementation** under ROADMAP **S3** (not done in this docs task). TC-F-005/006 still reflect the old code (✅); new spec is TC-DOCS-001/002 (⬜).
- **D2 — Free tier** (new, approved): Free row in PRD F7 / SPEC §9 / UX §6 — 1 scan/day · 2 coins · full Trading Blueprint · F3 limited to last 7 days · no export · basic academy, all `system_settings`-controlled. Paywall/fork copy: secondary "Continue on Free". SPEC §12 decision 8.
- **D3 — XP:** OPEN, **not implemented** — added to PRD §17 open items (conflict with UX §9.4; proposed +XP on first scan of the day only).
- **F13 onboarding simulation** registered in PRD (spec = FINARODA_ONBOARDING_SPEC.md v1.1, complements F12); ROADMAP X1 gains the 12 onboarding screens.
- **F3 reveal-gating (B3):** outcome revealed on the next scan + "journal has an update" teaser (pull-not-push).
- **Schema notes (docs only, not migrated):** SPEC §5.2 future `score_log.regime_state TEXT` (bear/bull/transition, BTC, N=5 hysteresis); SPEC §5.5 new `episodes` table (real dated kline, recharts render, never TradingView/Bybit). PRD §3 principle 8 — empirical truth in copy.
- **Untouched (as required):** RED LINE §3.5.5, 85/82 threshold, client-side fetch, calculator terminology.

## 🟢 STAGING — LIVE (deployed from `dev`)
- **Frontend (Vercel):** https://finaroda-saas.vercel.app  — Root Directory `frontend`, pnpm workspace, Production Branch = `dev`.
- **Backend (Railway):** https://finaroda-saas-production.up.railway.app  — nixpacks Python, volume `/app/data`, plain uvicorn (no Litestream). `ENVIRONMENT=staging`.
- **Cardcom:** TEST mode (`FEATURE_CARDCOM_LIVE=false`) — no real charges.
- **Login on staging (no email):** `DEV_RETURN_MAGIC_LINK=true` + `FEATURE_PUBLIC_SIGNUPS_OPEN=true`. To log in: `POST {backend}/api/auth/magic-link {"email":"..."}` → the response's `dev_magic_link` contains the token → open it (or `GET {backend}/api/auth/verify?token=...`) to set the `access_token` cookie. `rodanis@gmail.com` is a bootstrap admin (is_admin=true).
- **Smoke test (2026-07-01, all PASS):** health 200 (env=staging) · magic-link→verify→/me authenticated as rodanis (is_admin) · authenticated `POST /api/scan/events` → 200, persisted `scan_event_id=1` + `score_log` BTCUSDT · unauthenticated `/api/scan/events` → 401 (expected, auth-required — not CORS).
- **Not deployed:** Litestream/R2 backups (skipped for staging), Resend email (dev-return link instead), production domain (finaroda.com), lawyer/accountant sign-off.

## מה נעשה בסשן האחרון (P1 — תשתית חיה)
- **Auth (מוקשח, SPEC §4):** magic-link (Resend, console fallback בdev) + Google OAuth (iss תמיד, aud כשיש CLIENT_ID) + Apple stub(501). JWT ב-httpOnly cookie + get_current_user. magic-link token נשמר כ-**SHA-256 hash**. admin כ-role ב-DB (users.is_admin) עם bootstrap לפי ADMIN_BOOTSTRAP_EMAILS. beta gate + allowlist + waitlist. endpoints: /api/auth/{magic-link,verify,google,apple,logout,me} + /api/waitlist.
- **Cardcom v11 (TEST mode בלבד):** initiate(LowProfile)/webhook(HMAC)/status/cancel + charge_recurring(ChargeToken) + start_trial(14 יום, כרטיס) + run_renewal_batch + expire_trials. מיפוי basic/advanced/pro, מחירים מ-system_settings. **הכל dry-run/503 עד FEATURE_CARDCOM_LIVE=true.** migration 019 (billing_failure_count + מחירי פלאנים).
- **Deploy (מוכן, לא פרוס):** railway.toml (+3 crons), nixpacks.toml, litestream.yml (finaroda.db→R2), Dockerfile.
- **Frontend:** src/lib/api.ts + login/verify/coming-soon/paywall/checkout(success,cancelled) מחוברים ל-endpoints. UI אנגלית.

## מה עודכן ע"י נדב (לא Claude): scoring-engine
- **🟢 levels engine חולץ** מהכלי האישי (v25.80) ל-`shared/scoring-engine.js`: calcEMA/RSI/ATR/ADX/closedCandles/ema7Slope/computeSlTp/computeReversalAnchor — byte-faithful, node --test 8/8.
- **🟡 scoreDirection עדיין stub שזורק** — pass 2, דורש golden vectors מהכלי האישי (ראו `shared/scoring-engine.api.md`).

## Latest change — DOCS regulatory reframing (docs only, no code)
- Reframed the FRONT-END as a utility calculator. **Engine/score/edge/threshold unchanged.**
- New calculator terminology (Mathematical Trigger Point / Calculated Risk Level / Calculated Target Level / Dynamic Risk Level / Trading Blueprint), formula-transparency notes, an **Analysis Lens** (display only) and a **Risk Style** (Conservative/Balanced/Aggressive → `computeSlTp` opt only).
- **RED LINE:** client never changes score/weights/edge/85-82 threshold — only what's displayed + risk geometry. Authoritative spec: **PRD §3.5**; legal spine: **LEGAL §6**.
- **One product-scope change:** the per-user "personal threshold" was removed (violated the RED LINE). `users.default_threshold` stays for admin-only per-user overrides.
- Docs: PRD v2.1, UX v1.2, LEGAL v2.

## Latest — P2 scorer wired (real score live, dev only)
- **Real scorer wired:** `scoreDirection` (momentum profile = `MOMENTUM_CAL`) imported from `@finaroda/scoring-engine/scorer.js` (verbatim v25.80, untouched). `SCORE_GATE_ENABLED=true` — the live **85 PASS / 82-84 WATCH** gate on the numeric score; a `blocked` macro-gate result is hidden.
- **Direction:** score both long+short (momentum); prefer non-blocked, then higher score.
- **3 profiles logged (measure-first):** momentum (displayed) + pullback (`DEFAULT_CALIBRATION`) + continuation (`{...DEFAULT_CALIBRATION, entryMode:'continuation'}`) → `score_log` (migration 021 added `profile`). Only momentum is displayed.
- **RED LINE kept:** score uses fixed inputs (`DEFAULT_RISK`+`MOMENTUM_CAL`); Risk Style feeds only `computeSlTp` opt (levels). Analysis Lens is now display-only (no longer gates).
- **marketData extended client-side:** weekly (derived), open interest + oiChangePct (best-effort), change24h; marketContext (coinChanges/mean/std) built per scan.

## P2 scan core (base, done, dev only)
- **Scan flow:** central SCAN button + Lens/Risk-Style toggles → streaming log (4 steps) → client-side Bybit fetch (user IP, no shared cache; thin `/api/market/proxy` CORS fallback) → passers as circles (ring ≤5 / list >5) → **Trading Blueprint** → empty state (F1b).
- **Engine imported** as `@finaroda/scoring-engine` (symlink to `shared/`, `transpilePackages`, ambient d.ts). Levels only: computeSlTp / computeReversalAnchor / ema7Slope / indicators. **scoreDirection never called.**
- **Score-pending:** every coin recorded with `score=NULL` (migration 020); card shows "Score pending — engine pass 2 (levels are real)". Real 85/82 gate wired behind `SCORE_GATE_ENABLED=false` in `engine.ts`.
- **Interim rules (documented):** direction = sign of verified EMA7 slope; visibility = levels valid + Analysis-Lens condition (`lens.ts`).
- **Persistence (SPEC §5):** `POST /api/scan/events` (scan_events + score_log) and `POST /api/scan/snapshot` (decision_snapshots), auth-required, best-effort from the client.
- **RED LINE honored:** Lens = display only; Risk Style = `computeSlTp` opt only; score/weights/edge/threshold never client-touchable.

## Next step — P3 (learning loop)
- **Score is live** — no longer blocked (scorer extracted + wired).
- **P3 (SPEC §11):** backtest cron over `score_log` (outcome NULL) → "what would have happened" dashboard (F3). The 3 profiles now in `score_log` enable base-rate per profile.
- **Still open:** per-plan coin limit (2/5/10 from system_settings) not yet wired into the scan universe (currently a fixed 10-coin default). Open-interest/marketContext are best-effort — revisit accuracy in P3.

## מוכן לפריסה (ממתין להפעלה ידנית של נדב)
- **Cardcom live:** להזין credentials אמיתיים (sandbox→prod) + FEATURE_CARDCOM_LIVE=true. עד אז אין חיוב.
- **Railway deploy:** לחבר repo, למפות volume ל-/app/data, להזין env vars (backend/.env.example), להפעיל. CI (pytest+tsc) — עוד לא נכתב (אפשר ב-P2+).
- **Resend/Google/R2:** להזין מפתחות אמיתיים ב-env הפרודקשן.

## פתוחים / חוסמים
- אישור PRD מנדב; אישור עו"ד ל-LEGAL; אימות מחירים מול רו"ח; פלט Claude Design ל-UX.
- scoreDirection pass 2 (golden vectors) — חוסם ציון אמיתי ב-P2.

---

## תזכורת Branch Gate
Claude עובד על dev בלבד. נדב ממזג dev→main ידנית. אסור ל-Claude לגעת ב-main/production.

## איך מריצים מקומית
- Backend: `.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --port 8000`
- Frontend: `cd frontend && pnpm dev`  (צריך `NEXT_PUBLIC_API_URL`, ברירת מחדל localhost:8000)
- Validation: `.venv/Scripts/python.exe -m pytest` · `cd frontend && pnpm exec tsc --noEmit && pnpm run lint` · `cd shared && node --test`
