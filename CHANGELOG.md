# CHANGELOG — FINARODA SaaS

> כל משימה מוסיפה entry לפי הפורמט ב-CLAUDE.md §3. החדש למעלה.

---

## [DOCS-ALIGN-E-2026-07-11 / יישום section E — החלטות מוצר 11/07] — 2026-07-11
- GOAL: ליישם את section E של `ALIGNMENT_2026-07-09.md` (החלטות נדב 11/07) על מסמכי מקור-האמת. **דוקים בלבד — אפס שינוי קוד/מנוע/סקורר/backend.**
- SOLUTION (מה עשינו בפועל):
  - **E1 — Concept Tooltip (F-education):** נוסף **F14** ל-PRD — קומפוננטת בועת-לימוד אחידה על כל מונח מהאונבורדינג ואילך, תוכן מהאקדמיה (F6), display-only (לא נוגע ב-RED LINE). UX §3 (בתוך ה-Blueprint) + §8 (אינטראקציה).
  - **E2 — free-coin analysis:** נוסף ל-PRD backlog **V2 בלבד** — ניתוח מטבע מעבר ליקום 10, בפלאנים בתשלום, אחרי ולידציה+אישור נדב, עם **תווית חובה "Learning mode — outside the validated universe"**. לא v1.
  - **E3 — טבלת השוואה בעמוד Subscribe:** PRD F7 + UX §6 — הטבלה (Free forever: 1 scan/day · 2 coins · full Blueprint · journal 7 days · no export) **חייבת להיות מוצגת בעמוד ה-Subscribe**. נוסף AC ל-paywall + **TC-J-002** copy-guard.
  - **E5 — תפריט המבורגר אחרי תשלום** (Dashboard/Profile/Academy/Settings): נכנס להיקף Design סבב 2 (ROADMAP X1). UX §8.
  - **E6 — רטט SCAN:** SPEC §6.2 — `navigator.vibrate` עם fallback שקט (iOS Safari לא נתמך → לא ירטוט, בלי שגיאה).
  - **E7 — Live Chart + overlays פר-מטבע:** נוסף **F15** ל-PRD + UX §3 — גרף חי (recharts מ-kline) עם שכבות הסבר; gating: Free=chart+EMA200 / בתשלום=כל השכבות. Design סבב 2. display-only (RED LINE).
  - **E8 — באנר טיקר רץ:** נרשם כ-**REJECTED** ב-PRD §17 (סותר trust-not-engagement + רישוי דאטה למדדים/סחורות); החלופה = שורת marketContext סטטית פר-סריקה (קיימת); פתיחה מחדש רק כ-opt-in כבוי-כברירת-מחדל.
  - **E4** — ETF ממונפים: מסלול מחקר בכלי האישי בלבד, **לא נוגע ב-SaaS** — לא שונה דבר במסמכי ה-SaaS (מכוון).
  - **Consistency pass:** F14/F15 מזהים ייחודיים (F1–F13 קיימים); grep ל-ticker/hamburger/vibrate/Learning mode — אין סתירות. RED LINE §3.5.5, סף 85/82, client-side fetch, טרמינולוגיית המחשבון — לא נגעתי.
- FILES MODIFIED: FINARODA_SAAS_PRD.md, FINARODA_SAAS_UX.md, FINARODA_SAAS_SPEC.md, ROADMAP.md, ATP.md, CHANGELOG.md, VERSIONS.md, SESSION_HANDOFF.md. (ALIGNMENT_2026-07-09.md — section E נכנס כמקור.)
- APP/ENGINE/SCORER/BACKEND: **unchanged** (docs only).
- DB CHANGES: אין.
- CONFIG ADDED: אין.
- VALIDATION: docs-only (אפס שינוי קוד), אך הורץ לאימות: pytest **27/27** ✅ · shared node --test **12/12** ✅ · tsc clean ✅ · eslint clean ✅.
- ATP: נוספו TC-J-002 (copy-guard, E3) + TC-DOCS-E01..E05 (E01-E03 ⬜ pending implementation; E04/E05 ✅ doc-check).
- VERSION: v0.5.1 (PATCH — יישור דוקים, אפס קוד)
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: מסמכי מקור-האמת עקביים עם החלטות נדב 11/07. המימוש בפועל (F14 tooltip, F15 live chart, טבלה בעמוד Subscribe, vibrate, hamburger) ⬜ pending — ROADMAP X1 / P4.
- DECISIONS: free-coin analysis (E2) נרשם כ-V2 מפורש (לא MVP) כדי לא לזהם את יקום ה-base-rate המאומת; ticker banner (E8) נדחה במפורש ב-§17 (חדש: subsection "פריטים שנדחו") ולא רק הושמט, כדי שלא ייפתח מחדש בטעות.

## [D1-TRIAL-NO-CARD / trial ללא כרטיס + downgrade ל-Free] — 2026-07-09
- GOAL: לממש את D1 (trial ללא כרטיס) בקוד ה-billing, לפי SPEC §9/§12.3 + PRD F7 שיושרו במשימת הדוקים. trial בלי כרטיס/tokenization, בלי חיוב אוטומטי; בסוף ה-trial המשתמש עובר ל-Free (D2) — לעולם לא מחויב. לכידת כרטיס רק בהמרה אקטיבית לתשלום.
- SOLUTION (מה עשינו בפועל):
  - **`start_trial`** (`core/cardcom_service.py`): ללא כרטיס/tokenization; `next_billing_at=NULL` (אין חיוב אוטו). ברירת מחדל plan=`pro` (14 ימי Pro מלא, לפי onboarding). event `trial_started` נשמר. re-trial → 409.
  - **`expire_trials`**: trial שפג → `tier='free'`, `subscription_status='none'` (מצב ה-Free הקנוני; לא expired/blocked, `next_billing_at=NULL`); event חדש `trial_ended_to_free`. הפונקציה מחזירה `{"moved_to_free": N}`.
  - **`run_renewal_batch`**: הצטמצם ל-`subscription_status='active'` בלבד — trial (חסר כרטיס/next_billing) לעולם לא נכנס למועמדי החיוב.
  - **תזכורת יום 11**: `trial_ending_soon_task` יורה `TRIAL_REMINDER_LEAD_DAYS` (ברירת מחדל 3) לפני סוף ה-trial (יום 11 מתוך 14) בחלון יומי; config חדש `TRIAL_REMINDER_LEAD_DAYS`. railway.toml cron comment עודכן day-13→day-11.
  - **לכידת כרטיס בהמרה**: `initiate_checkout` (Cardcom LowProfile) — ללא שינוי לוגי; זהו רגע לכידת הכרטיס היחיד. נשאר בגייטינג TEST (503 עד `FEATURE_CARDCOM_LIVE=true`).
  - **Frontend**: `paywall/page.tsx` — הקופי "card on file" הוחלף ב"no credit card / card only at paid plan / continue on Free"; כפתור "Start trial"→"Choose plan".
  - **Webhook/HMAC/charge_recurring**: ללא שינוי מעבר לצמצום ה-WHERE של ה-renewal.
- FILES MODIFIED: backend/core/cardcom_service.py, backend/config.py, backend/app/tasks/billing_tasks.py, backend/tests/test_p1_auth_billing.py, railway.toml, frontend/src/app/paywall/page.tsx, ATP.md, ROADMAP.md, CHANGELOG.md, VERSIONS.md, SESSION_HANDOFF.md.
- FILES CREATED: backend/migrations/022_subscription_events_trial_to_free.py.
- DB CHANGES: **migration 022** — rebuild של `subscription_events` להוספת `event_type='trial_ended_to_free'` ל-CHECK (SQLite לא תומך ALTER ל-CHECK; שורות/עמודות/index נשמרו). ספירת הטבלאות ללא שינוי.
- CONFIG ADDED (שמות בלבד): `TRIAL_REMINDER_LEAD_DAYS`.
- VALIDATION: pytest **27/27** ✅ · shared node --test 12/12 ✅ · tsc clean ✅ · eslint clean ✅.
- ATP: TC-F-005/006 נכתבו מחדש (no-card trial + Free downgrade); נוספו TC-F-007 (re-trial 409) + TC-F-008 (renewal לא מחייב trial); TC-DOCS-001/002 → ✅.
- VERSION: v0.5.0 (MINOR — פיצ'ר תואם-אחורה: מודל trial חדש)
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: משתמש מתחיל trial בלי כרטיס ובלי סיכון חיוב; בסוף ה-trial עובר ל-Free (המשך שימוש, לא חסום). חיוב קורה רק אחרי בחירה אקטיבית של פלאן בתשלום. staging נשאר TEST mode — אין חיוב אמיתי.
- DECISIONS: Free מיוצג כ-`tier='free' + subscription_status='none'` (מצב ה-Free הקיים) — בלי להרחיב את CHECK של subscription_status (נמנע rebuild של טבלת users הכבדה); event `trial_ended_to_free` כן נוסף כי הוא נחוץ ל-audit/analytics. ברירת מחדל trial plan הועברה ל-`pro` (Pro מלא, תואם onboarding).

## [DOCS-ALIGN-2026-07-09 / יישור מסמכי מקור-אמת ל-ALIGNMENT] — 2026-07-09
- GOAL: ליישר את כל מסמכי מקור-האמת (PRD/SPEC/UX/LEGAL/ROADMAP/ATP) להכרעות נדב ב-`ALIGNMENT_2026-07-09.md` ו-`FINARODA_ONBOARDING_SPEC.md` (v1.1). **דוקים בלבד — אפס שינוי קוד/מנוע/סקורר.**
- SOLUTION (מה עשינו בפועל):
  - **D1 — Trial ללא כרטיס** (change order מאושר, מחליף את "trial עם כרטיס" הנעול): SPEC §9 + §12.3 → 14 יום, ללא tokenization בהרשמה, ללא חיוב אוטומטי, תזכורת יום 11, בסוף בחירה אקטיבית (פלאן/Free), לכידת כרטיס ברגע ההמרה. PRD F7 (flow + AC1/AC2 שוכתבו) + §17. UX journey שלב 4 + §6. LEGAL §2.6. ROADMAP S3 (⬜ pending implementation — start_trial לעיבוד מחדש).
  - **D2 — Free tier חדש:** שורת Free בטבלאות PRD F7 / SPEC §9 / UX §6 — סריקה 1/יום · 2 מטבעות · Blueprint מלא · F3 מוגבל 7 ימים · ללא ייצוא · academy בסיסי, נשלט `system_settings`. paywall/fork: "Continue on Free". SPEC §12 החלטה 8.
  - **D3 — XP:** נותר פתוח, **לא מומש**. נוסף ל-PRD §17 open items ("XP economy pending — conflict with UX §9.4; proposed +XP on first scan of the day only").
  - **D4 — English UI:** נעול, ללא שינוי.
  - **F13 — "First 60 Seconds" onboarding simulation:** נרשם ב-PRD (spec = `FINARODA_ONBOARDING_SPEC.md` v1.1, משלים F12), Design סבב 2 (ROADMAP X1 — נוספו מסכי האונבורדינג).
  - **F3 reveal-gating (B3):** תוצאה נחשפת בסריקה הבאה + teaser "journal has an update" (pull-not-push).
  - **Data/learning (B2/B4):** SPEC §5.2 — note לעמודת `regime_state TEXT` עתידית (bear/bull/transition, BTC, N=5 hysteresis). SPEC §5.5 — טבלת `episodes` (kline אמיתי מתוארך, רינדור recharts, לא צילומי TradingView/Bybit). PRD §3 principle 8 — אמת אמפירית בקופי.
  - **Consistency pass:** grep ל-"עם כרטיס"/"with card" — כל ההיטים שנותרו הם הפניות מכוונות ל"מה שהוחלף" או ה-CHANGELOG ההיסטורי. RED LINE (§3.5.5), סף 85/82, client-side fetch, וטרמינולוגיית המחשבון — לא נגעתי.
- FILES MODIFIED: FINARODA_SAAS_SPEC.md, FINARODA_SAAS_PRD.md, FINARODA_SAAS_UX.md, FINARODA_SAAS_LEGAL_DRAFT.md, ROADMAP.md, ATP.md, CHANGELOG.md, VERSIONS.md, SESSION_HANDOFF.md. (ALIGNMENT_2026-07-09.md + FINARODA_ONBOARDING_SPEC.md — נכנסו ל-repo כמקור.)
- APP/ENGINE/SCORER/BACKEND: **unchanged** (docs only).
- DB CHANGES: אין (רק *תיעוד* של migration עתידי ל-regime_state + טבלת episodes — לא מיושם).
- CONFIG ADDED: אין.
- VALIDATION: pytest 25/25 ✅ · shared node --test 12/12 ✅ · tsc clean ✅ · eslint clean ✅.
- ATP: TC-F group + TC-F-005/006 note עודכנו; נוספו TC-DOCS-001..007 (001-006 ⬜ pending implementation, 007 ✅ doc-check).
- VERSION: v0.4.8
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: מסמכי מקור-האמת עקביים עם הכרעות 2026-07-09 (trial ללא כרטיס, Free tier, F13, reveal-gating). המימוש בפועל (start_trial, Free limits, מסכי onboarding) ⬜ pending — ROADMAP S3/X1.
- DECISIONS: לא לשכתב היסטוריית CHANGELOG/קוד קיים; "trial עם כרטיס" נשמר כהפניה מפורשת ל"מה שהוחלף"; ATP TC-F-005 הקיים נשמר ✅ (מתעד קוד לא-משונה) לצד TC-DOCS החדשים.

## [STAGING / Live deploy from dev + smoke test PASS] — 2026-07-01
- GOAL: Stand up a live staging environment (not production) and validate end-to-end.
- ENVIRONMENT: Frontend on Vercel (Root `frontend`, pnpm workspace, branch `dev`) = https://finaroda-saas.vercel.app ; Backend on Railway (nixpacks Python, volume `/app/data`, plain uvicorn, `ENVIRONMENT=staging`, Cardcom TEST) = https://finaroda-saas-production.up.railway.app. No Litestream/R2, no Resend (DEV_RETURN_MAGIC_LINK), no production domain.
- SMOKE TEST (all PASS): health 200 (env=staging); magic-link→verify→/me authenticated as rodanis@gmail.com (is_admin=true — bootstrap admin works live); authenticated `POST /api/scan/events` → 200 persisted scan_event_id=1 + score_log; unauthenticated `/api/scan/events` → 401 (auth-required by design, not CORS).
- CODE: none (validation + SESSION_HANDOFF only).
- BRANCH: dev. main untouched. Cardcom TEST — no real charges. Nothing deployed by Claude (Nadav ran the Railway/Vercel deploys).

## [CHORE / pnpm workspace — resolve shared engine without a toggle] — 2026-07-01
- GOAL: Vercel's "Include files outside the root directory" toggle is gone from the current UI, so `link:../shared` still couldn't resolve. Convert to a proper **pnpm workspace** so Vercel (and any tool) resolves `@finaroda/scoring-engine` → `shared/` natively.
- SOLUTION (config + package.json metadata only):
  - `pnpm-workspace.yaml` (new, repo root): packages `frontend`, `shared`. (Backend is Python-only, no manifest — not a member.)
  - `frontend/package.json`: dependency `@finaroda/scoring-engine` changed `link:../shared` → `workspace:*`.
  - `shared/package.json`: added an `exports` map (`.` → scoring-engine.js, `./scorer.js`, `./scoring-engine.js`, `./package.json`) so both the root import and the subpath resolve explicitly; kept `main`, `name`, `type: module`.
  - Lockfile regenerated as a **workspace** lockfile at the repo root (`pnpm-lock.yaml`); removed `frontend/pnpm-lock.yaml`.
  - No root `package.json` needed (pnpm 10 handled it) → the backend's Railway Python/nixpacks build sees no Node manifest and is unaffected.
- FILES: pnpm-workspace.yaml (new), pnpm-lock.yaml (new at root), frontend/pnpm-lock.yaml (removed), frontend/package.json (workspace:*), shared/package.json (exports). transpilePackages in next.config kept.
- APP/ENGINE/SCORER/BACKEND LOGIC: unchanged (only package.json metadata + workspace config).
- VALIDATION: node --test 12/12 ✅ | tsc clean ✅ | eslint clean ✅ | `cd frontend && pnpm build` 16 routes, both `@finaroda/scoring-engine` AND `.../scorer.js` resolve ✅ | pytest 25/25 (backend unaffected) ✅.
- VERSION: v0.4.7
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: The shared engine resolves as a workspace package — Vercel deploys the frontend with Root Directory `frontend` and no toggle needed.

## [CHORE / Frontend → Vercel (monorepo shared package)] — 2026-07-01
- GOAL: Fix `Module not found: @finaroda/scoring-engine` in the Railway frontend build. Root cause: Railway with Root Directory=`frontend` does NOT include the sibling `../shared` on disk, so the `link:../shared` symlink dangles and webpack can't resolve the engine. The only Railway root-context option (Docker, Root=`/`) inherits the backend's `/api/health` healthcheck + Python crons from the root railway.toml.
- DECISION: **Move the frontend to Vercel** (backend stays on Railway). Vercel clones the whole repo and has a documented "Include files outside the root directory" toggle for monorepos, so `link:../shared` resolves cleanly — no healthcheck/cron landmine. (Nadav already runs hamakpetza-frontend on Vercel.)
- SOLUTION (config only): Added `frontend/vercel.json` pinning `installCommand: pnpm install --no-frozen-lockfile` + `buildCommand: pnpm build`. No change to how the frontend imports the engine (kept `link:../shared` + transpilePackages). Railway frontend configs (nixpacks.toml, frontend.Dockerfile) retained but unused.
- FILES MODIFIED: frontend/vercel.json (new).
- APP/ENGINE/SCORER/BACKEND: unchanged.
- VALIDATION: verified the `@finaroda/scoring-engine` symlink resolves + clean `next build` (16 routes) locally — this mirrors Vercel with files-outside-root included. tsc/eslint clean.
- VERSION: v0.4.6
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: Frontend deploys on Vercel with the shared engine resolving; backend remains on Railway. Cross-URL/CORS finalized once the Vercel URL exists.

## [CHORE / Frontend Railway build — nix-provided pnpm] — 2026-07-01
- GOAL: Fix `pnpm: command not found` (exit 127) — `npm i -g pnpm` in one nixpacks phase didn't leave pnpm on PATH for the next phase (nix Node's global-npm bin isn't on PATH).
- SOLUTION (config only): Provide pnpm via **nix** — `nixPkgs = ['nodejs_22', 'pnpm']` in `frontend/nixpacks.toml`. A nix package is on PATH for install, build, AND runtime, so it fixes the PATH error, needs no corepack (no keyid error), and no npm-global hack. Removed the `npm install -g pnpm` step. Kept Root Directory=`frontend` (Node-only; avoids the root railway.toml healthcheck/crons).
- The `$NIXPACKS_PATH` undefined-var line is a benign nixpacks Docker-lint warning, not the failure cause; no action needed.
- FILES MODIFIED: frontend/nixpacks.toml. (frontend.Dockerfile fallback from v0.4.4 retained.)
- APP/ENGINE/SCORER/BACKEND: unchanged.
- VALIDATION: tsc clean ✅ | eslint clean ✅ | next build 16 routes ✅. (nixpacks build itself is Railway-only — can't run nixpacks/Docker here.)
- VERSION: v0.4.5
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: pnpm is on PATH across all build phases + runtime via nix; the command-not-found error is resolved without corepack or PATH hacks.

## [CHORE / Frontend Railway build — fix corepack keyid] — 2026-07-01
- GOAL: Fix the frontend Railway build failing at `corepack enable` with "Cannot find matching keyid" (corepack signature verification, Node 22).
- SOLUTION (config only): Install pnpm **directly via npm** (`npm install -g pnpm@10.33.1`) instead of `corepack enable`, in `frontend/nixpacks.toml`; removed the `packageManager` field from `frontend/package.json` so nixpacks doesn't auto-invoke corepack. Kept the Node-only nixpacks path with **Root Directory = `frontend`** — which also avoids the repo-root railway.toml's `/api/health` healthcheck and Python crons (a landmine a root-context Docker build would hit).
- Also added `frontend.Dockerfile` (repo-root context; pnpm via npm; COPY shared/+frontend/) as a documented **fallback** if a Docker build is preferred (requires Root Directory `/` + `RAILWAY_DOCKERFILE_PATH` + clearing the inherited healthcheck).
- FILES MODIFIED: frontend/nixpacks.toml (corepack→npm), frontend/package.json (removed packageManager), frontend.Dockerfile (new fallback).
- APP/ENGINE/SCORER/BACKEND: unchanged.
- VALIDATION: tsc clean ✅ | eslint clean ✅ | next build 16 routes ✅.
- VERSION: v0.4.4
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: Frontend nixpacks build no longer calls corepack, so the keyid error is gone. Recommended path stays Root Directory `frontend` (Node-only, no root config inherited).

## [CHORE / Frontend Railway build — force Node-only] — 2026-07-01
- GOAL: Fix the Railway frontend build failing with `externally-managed-environment` / `get-pip.py` — nixpacks was building the monorepo's Python backend for the Next.js frontend service.
- ROOT CAUSE: With the frontend service Root Directory at repo root, Railway read the repo-root `nixpacks.toml` (Python provider) and tried to `pip install` for a Node app.
- SOLUTION (config only): Added `frontend/nixpacks.toml` with `providers = ['node']` (Node-only, pins nodejs_22, pnpm via corepack, `pnpm install`+`pnpm build`, start `next start -p $PORT`), and a `packageManager: pnpm@10.33.1` field in `frontend/package.json` so nixpacks uses pnpm not npm. The frontend service must set **Root Directory = `frontend`** so Railway reads THIS config, not the root Python one. `link:../shared` still resolves (Railway includes the whole repo in the build).
- FILES MODIFIED: frontend/nixpacks.toml (new), frontend/package.json (packageManager field).
- APP/ENGINE/SCORER: unchanged.
- VALIDATION: tsc clean ✅ | eslint clean ✅ | next build 16 routes ✅.
- VERSION: v0.4.3
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: Frontend Railway service builds as a pure Node/Next app; no Python provider triggered. Backend service (Root Directory `/`) still uses the root nixpacks.toml unchanged.

## [CHORE / Next.js security bump for Railway staging] — 2026-07-01
- GOAL: Unblock the Railway staging build, which rejected next@15.5.4 (CVE-2025-66478, CRITICAL).
- SOLUTION: Dependency bump only — no app logic, engine, or scorer changes.
- FILES MODIFIED: frontend/package.json, frontend/pnpm-lock.yaml.
- DEPS: next 15.5.4 → 15.5.19 (^15.5.9, includes the CVE fix); eslint-config-next 15.5.4 → 15.5.19 (kept in lockstep with next). Stayed within 15.5.x — non-breaking, no React/Next major bump.
- AUDIT: `pnpm audit --audit-level high` → 0 high/critical after the bump. 1 remaining **moderate** (transitive `postcss <8.5.10` via next) — not critical/high, does not block Railway; left as-is per the critical/high-only scope.
- VALIDATION: tsc clean ✅ | eslint clean ✅ | next build 16 routes ✅ | pytest 25/25 ✅ (backend unaffected) | shared node 12/12 (unchanged).
- VERSION: v0.4.2
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: Railway frontend build no longer blocked by the critical Next.js advisory. No functional change.

## [P2 / Scorer wired — real 85/82 gate live] — 2026-07-01
- GOAL: Wire the real scorer (`shared/scorer.js`, verbatim v25.80) into the scan core: momentum profile displayed, real 85 PASS / 82-84 WATCH gate on, pullback/continuation profiles logged (measure-first), score pending removed. Engine files not modified.
- SOLUTION: Import `scoreDirection` + `MOMENTUM_CAL` + `DEFAULT_CALIBRATION` + `DEFAULT_RISK` from `@finaroda/scoring-engine/scorer.js`. Score both directions per coin with the momentum profile; also score pullback/continuation for logging. Levels still via `computeSlTp` with Risk Style (RED LINE).
- FILES CREATED: backend/migrations/021_score_log_profile.py, backend/tests/test_p2_scorer.py.
- FILES MODIFIED: frontend/src/lib/scan/{engine,bybit,persist,lens,types}.ts, frontend/src/app/(scan)/scan/page.tsx, frontend/src/components/scan/{TradingBlueprint,Results}.tsx, frontend/src/types/scoring-engine.d.ts, backend/models/scan.py, backend/api/scan.py.
- DB CHANGES: migration 021 — `score_log.profile` column (momentum/pullback/continuation) + index. score is now populated (real), no longer null.
- ENGINE: **imported, not modified.** `shared/scorer.js` + `shared/scoring-engine.js` untouched (verified: no diff). scoreDirection is now CALLED with the momentum default profile.
- VALIDATION: node --test 12/12 (8 engine + 4 scorer) ✅ | pytest 25/25 ✅ | tsc clean ✅ | eslint clean ✅ | next build 16 routes (/scan 12.3 kB, scorer bundled) ✅ | boot smoke (health 200, scan/events 401, migrations 020+021 apply) ✅
- ATP: TC-SCORER-001..004 added.
- VERSION: v0.4.1
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: The scan now shows a REAL score with the live 85/82 PASS/WATCH gate. Three profiles are recorded per coin for base-rate research; only momentum is displayed. "Score pending" placeholder removed.
- DECISIONS (non-trivial):
  1. **`SCORE_GATE_ENABLED=true`.** Visibility gate is now the numeric score: PASS ≥85, WATCH 82-84, else hidden; a `blocked` (macro hard-gate) result is always hidden. The Analysis Lens no longer gates visibility (it's now purely a display panel — strengthens the RED LINE).
  2. **Direction selection:** score both long+short with the momentum profile; prefer the non-blocked result, then the higher score. That decides the displayed direction (replaces the interim EMA7-sign rule).
  3. **Profiles via the tool's own `entryMode` switch (no invented numbers):** momentum = `MOMENTUM_CAL`; pullback = `DEFAULT_CALIBRATION` (entryMode 'pullback'); continuation = `{...DEFAULT_CALIBRATION, entryMode:'continuation'}`. There are no separate PULLBACK/CONTINUATION exports in scorer.js — these are the documented calibration variants.
  4. **RED LINE kept:** the score uses FIXED inputs (`DEFAULT_RISK` + `MOMENTUM_CAL`); Risk Style feeds ONLY `computeSlTp` opt (displayed levels). Changing Risk Style on the card recomputes levels, never the score.
  5. **marketData extended (client-side):** added `weekly` (derived from daily every 7th candle, matching the scorer's test), open interest + `oiChangePct` (best-effort from Bybit open-interest; neutral default), and `change24h`; `marketContext` (coinChanges/mean/std) built once per scan from all coins' 24h change.
  6. **Persistence:** 3 rows per coin (profiles); only the momentum row is returned for snapshot linking; momentum row carries the displayed levels, the other two log score only.

## [P2 / Scan core — client-side fetch + Trading Blueprint] — 2026-07-01
- GOAL: Build the full scan flow and Trading Blueprint on the LEVELS engine (imported from `shared/scoring-engine.js`), to the binding reframing in PRD §3.5. The numeric SCORE is not available (scoreDirection throws, pass 2) — surfaced as pending, never invented.
- SOLUTION: Client-side Bybit fetch (user IP, no shared cache) → shared levels engine → results (ring/list) → Trading Blueprint. Persistence to scan_events/score_log/decision_snapshots. Backend adds scan endpoints + a thin CORS-fallback proxy.
- FILES CREATED:
  - Backend: backend/api/{scan.py, market_proxy.py}, backend/models/scan.py, backend/migrations/020_score_log_nullable.py, backend/tests/test_p2_scan.py.
  - Frontend: src/lib/scan/{types,bybit,engine,lens,store,persist}.ts, src/components/scan/{Controls,ScanningLog,Results,TradingBlueprint}.tsx, src/types/scoring-engine.d.ts. Rewrote src/app/(scan)/scan/page.tsx.
- FILES MODIFIED: backend/main.py (scan + market routers), frontend/package.json (link `@finaroda/scoring-engine`), frontend/next.config.ts (transpilePackages).
- DB CHANGES: migration 020 — `score_log.score` made NULLABLE (score pending until pass 2). No other schema change.
- CONFIG ADDED: none new (BYBIT_PUBLIC_BASE_URL already existed).
- ENGINE: **imported, never reimplemented.** Linked `shared/` as `@finaroda/scoring-engine` (workspace symlink) + ambient d.ts. Used calcEMA/RSI/ATR/ADX, ema7Slope, closedCandles, computeSlTp, computeReversalAnchor. **scoreDirection is never called.**
- VALIDATION: pytest 22/22 ✅ | tsc clean ✅ | eslint clean ✅ | next build 16 routes (/scan 5.89 kB, engine bundled) ✅ | shared node --test 8/8 ✅ | boot smoke (health 200, scan/events 401, proxy whitelist 400) ✅
- ATP: TC-B-001..006 (scan persistence, auth, snapshot ownership, proxy whitelist, score_log nullable) + TC-C-001..003 (Blueprint terminology / formula notes / score-pending — validated by build+tsc).
- VERSION: v0.4.0
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: A working scan core: press → streaming log → passers as circles → Trading Blueprint with real calculated levels, formula-transparency notes, Analysis Lens (display), Risk Style (geometry). Score cleanly marked pending; real 85/82 gate wired behind `SCORE_GATE_ENABLED` (off).
- DECISIONS (non-trivial):
  1. **Score-pending handling:** every scanned coin is recorded with `score=NULL`; the card shows "Score pending — engine pass 2 (levels below are real)". scoreDirection is never invoked. The real 85 PASS / 82 WATCH gate is wired but behind `SCORE_GATE_ENABLED=false` (engine.ts) — flip it on when pass 2 lands.
  2. **Interim visibility rule (documented):** while the score is pending, a coin is shown if its LEVELS are valid (ema7Slope non-null, ATR>0, ≥30 closed candles) AND the Analysis Lens condition holds (lens.ts). This is display-gating, not a score.
  3. **Interim direction rule:** direction derived from the sign of the VERIFIED EMA7 slope (long if >0, short if <0) purely to orient level geometry — not a recommendation, not a score.
  4. **Risk Style → `computeSlTp` opt only** (Conservative 1.0/1.0/2.0 · Balanced=defaults · Aggressive 2.0/2.0/4.0). Levels move; score untouched (RED LINE).
  5. **Engine link:** used `link:../shared` + `transpilePackages` + a frontend ambient d.ts (types only) rather than touching `shared/` — engine files untouched.
  6. **Persistence is best-effort:** scan endpoints require auth; a signed-out scan still works (persistence silently no-ops on 401).
- RED LINE: honored — client Lens changes display only; Risk Style changes geometry only; score/weights/edge/threshold are never client-touchable.

## [DOCS / Regulatory reframing — calculator framing] — 2026-07-01
- GOAL: Reframe the FRONT-END as a utility calculator (not advice) for regulatory protection. **The calculation engine, the verified EMA7-slope edge, filter weights, and the 85/82 threshold DO NOT change** — only terminology, what is displayed, and client-selected risk geometry.
- SOLUTION: Docs-only update to PRD/UX/LEGAL. Added an authoritative reframing section (PRD §3.5) that governs all surfaces, plus targeted term updates and a RED LINE.
- FILES MODIFIED: FINARODA_SAAS_PRD.md (v2.0→v2.1), FINARODA_SAAS_UX.md (v1.1→v1.2), FINARODA_SAAS_LEGAL_DRAFT.md (v2 reframing), CHANGELOG/VERSIONS/SESSION_HANDOFF.
- CODE CHANGES: NONE. scoring-engine.js and all scorer logic untouched (verified: no shared/ or backend/ diff).
- WHAT CHANGED (front-end only):
  1. **Terminology (calculator, not advice):** Entry → Mathematical Trigger Point · Stop Loss → Calculated Risk Level · Take Profit → Calculated Target Level · Trailing → Dynamic Risk Level · decision card → Trading Blueprint. "Analysis, not financial advice" labels kept.
  2. **Formula transparency:** each level shows a "how it was computed" note (e.g. "Calculated via ATR14 on your selected chart").
  3. **Analysis Lens (client choice — display only):** EMA200 / RSI / Volume / Full, chosen pre-scan, remembered, one scan press. Engine + score unchanged; lens only changes what is displayed.
  4. **Risk Style (client choice — output not score):** Conservative / Balanced / Aggressive → changes ONLY `computeSlTp` `opt` (slAtrMult / tp1Mult / tp2Mult). Levels move; score does NOT. Balanced == engine defaults.
  5. **RED LINE (PRD §3.5.5 + LEGAL §6):** client NEVER modifies score / filter weights / EMA7 edge / 85-82 threshold. Client choices live only in (a) what is displayed and (b) risk geometry — never in what counts as an opportunity. Protects measure-first + shared base-rate.
- VALIDATION: docs-only (no code) — pytest/tsc/eslint/node unaffected; last green state stands (P1: pytest 16/16, node 8/8, tsc/eslint clean).
- ATP: no new automated TC (docs). Reframing acceptance criteria captured in PRD §3.5 (AC per feature).
- VERSION: v0.3.1 (docs) · PRD v2.1 · UX v1.2 · LEGAL v2 reframing
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: Stronger "utility calculator, not adviser" posture with real client-executed configuration, while the verified edge and base-rate stay intact.
- DECISIONS:
  1. **Per-user score threshold REMOVED** (old F5 "personal threshold" + UX §5): it would let the client change what counts as an opportunity → violates the RED LINE. `users.default_threshold` stays in the schema but is reserved for admin per-user overrides, never client-editable. (Flagged as the one real product-scope change forced by the RED LINE.)
  2. **Risk Style defaults** proposed (Conservative 1.0/1.0/2.0 · Balanced 1.5/1.5/3.0 = engine defaults · Aggressive 2.0/2.0/4.0) — admin-tunable, passed only as `computeSlTp` `opt`; engine code untouched.
  3. New reframing content written in **English** (per the permanent English-only directive + it is the canonical UI/terminology language). Existing Hebrew prose left as historical.

## [P1 / תשתית חיה — auth + Cardcom + deploy] — 2026-07-01
- GOAL: לחווט את שכבת התשתית החיה על גבי השלד הנקי — auth מלא ומוקשח, Cardcom v11 ב-TEST mode, קונפיג deploy ל-Railway, וחיבור frontend בסיסי. בלי פיצ'רים, בלי חיוב אמיתי, בלי פריסה חיה. (SPEC §3.1, §4, §9, §11)
- SOLUTION: פורט דפוסי התשתית מ-hamakpetza (רפרנס read-only) והותאמו לסכמה הנקייה + הקשחות SPEC §4. שכבת קריירה לא נגעה.
- FILES CREATED:
  - Auth: backend/core/{auth.py, database.py, google_oauth.py, apple_oauth.py, email.py}, backend/api/{auth.py, waitlist.py}, backend/models/{auth.py, cardcom.py}.
  - Cardcom: backend/core/cardcom_service.py (חווט מלא: initiate/webhook/ChargeToken/trial/renewal/expire), backend/api/cardcom.py (initiate/webhook/status/cancel — הוסר 501).
  - Crons: backend/app/tasks/billing_tasks.py + backend/scripts/run_{expire_trials,subscription_renewal,trial_ending_soon}.py.
  - Deploy: railway.toml, nixpacks.toml, litestream.yml, Dockerfile.
  - Frontend: src/lib/api.ts + דפי login/verify/coming-soon/paywall/checkout(success,cancelled) מחוברים ל-endpoints; frontend/.env.example.
  - Tests: backend/tests/test_p1_auth_billing.py (12 מקרים).
- FILES MODIFIED: backend/{config.py, main.py, .env.example, api/cardcom.py, core/cardcom_service.py}, backend/tests/{conftest.py, test_smoke.py}, frontend placeholders → wired.
- DB CHANGES: migration 019 — users.billing_failure_count + seed מחירי 3 פלאנים ב-system_settings (basic 5000 / advanced 10000 / pro 15000 agorot) + trial_days.
- CONFIG ADDED (שמות בלבד): ADMIN_BOOTSTRAP_EMAILS (החליף ADMIN_USER_IDS). Cardcom/Google/Resend/R2 כבר קיימים כ-placeholders. **FEATURE_CARDCOM_LIVE=false נשאר — TEST mode.**
- VALIDATION: pytest 16/16 ✅ | tsc clean ✅ | eslint clean ✅ | next build 16 routes ✅ | uvicorn boot (health 200, auth/me 401, cardcom 401, waitlist 200) ✅ | shared node --test 8/8 ✅
- ATP: נוספו TC-A-001..007 (auth) + TC-F-001..006 (billing/Cardcom test-mode).
- VERSION: v0.3.0
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: auth חי (magic-link+Google+beta gate+waitlist), Cardcom מחווט מלא ומוכן להפעלה (dry-run עד credentials+FEATURE_CARDCOM_LIVE), deploy config מוכן. אין חיוב אמיתי, אין פריסה.
- DECISIONS:
  1. **Cardcom נשאר TEST mode לחלוטין:** כל קריאת רשת חסומה מאחורי FEATURE_CARDCOM_LIVE=false → initiate מחזיר 503, renewal/charge מחזירים dry-run. אפס סיכוי לחיוב אמיתי. credentials = placeholders ב-.env.example בלבד.
  2. **הקשחות SPEC §4:** magic-link token נשמר כ-SHA-256 hash (לא plaintext); admin כ-role ב-DB (users.is_admin) עם bootstrap לפי ADMIN_BOOTSTRAP_EMAILS (לא רשימת env ids); Google — אכיפת iss תמיד + aud כשיש CLIENT_ID, ובפרודקשן CLIENT_ID ריק = שגיאה (לא דילוג שקט); dev-secret fallback כבר נחסם בפרודקשן ב-config (P0).
  3. **אוצר מילים פלאנים = basic/advanced/pro** (מיפוי plan==tier), מחירים מ-system_settings (admin בלי קוד).
  4. **trial עם כרטיס:** start_trial קובע trial 14 יום + next_billing; tokenization דרך זרימת ה-checkout; חיוב יום 15 = cron renewal (dry-run עד live).
  5. **suspension על 3 כשלונות** נכתב כ-subscription_status='past_due' + suspended_at (מכבד את ה-CHECK constraint; אין ערך 'suspended').
  6. **לא נגעתי ב-scoring-engine** — נשאר לפי הנחיה. (חילוץ ה-levels ע"י נדב תועד בנפרד למטה.)

## [ENGINE / חילוץ levels engine מהכלי האישי — pass 1] — 2026-07-01
- GOAL: לחלץ את מנוע ה-levels המאומת מהכלי האישי (finaroda-offline.html v25.80) ל-scoring-engine.js המשותף.
- SOLUTION: **סופק ע"י נדב** (לא Claude) במקביל ל-P1. חולצו byte-faithful: calcEMA/calcRSI/calcATR/calcADX/closedCandles/ema7Slope/computeSlTp/computeReversalAnchor. scoreDirection נשאר stub שזורק (pass 2 — דורש golden vectors).
- FILES MODIFIED: shared/scoring-engine.js, shared/scoring-engine.test.js, shared/scoring-engine.api.md.
- VALIDATION: node --test 8/8 ✅.
- VERSION: (חלק מ-shared, לא bump ל-repo).
- BRANCH: dev
- IMPACT: כרטיס ההחלטה יוכל להציג levels אמיתיים (Entry/SL/TP/Trailing/R:R/EMA7 slope/reversal anchor) ב-P2. הציון (PASS≥85/WATCH) עדיין חסום עד pass 2.
- NOTE: Claude לא כתב/שינה קוד זה; נדחף כ-commit נפרד לשקיפות.

## [P1.5 / חילוץ תשתית מנוע הסריקה — placeholder] — 2026-07-01
- GOAL: להכין את תשתית המנוע המשותף (`scoring-engine.js`) לפני P2, בלי מימוש. המנוע האמיתי עדיין שזור בכלי האישי (React מקומפל) ויסופק ע"י נדב. (SPEC §6.1, §12 החלטה 7)
- SOLUTION: נוצרה תיקיית `shared/` עם placeholder בלבד — חתימות פונקציות שמחזירות sentinel `TODO`, קובץ הגדרת API, ו-node:test שמאמת חתימות+התנהגות. **לא הומצא מנוע, לא נעשה חיבור ל-Bybit.** `shared/package.json` (`type:module`) מאפשר ל-`.js` לשמש כ-ESM גם בדפדפן (כלי אישי) וגם ב-Next (SaaS), ומכין את נתיב ה-npm package המשותף.
- FILES CREATED: shared/scoring-engine.js (stubs: ema7Slope, scoreDirection, computeReversalAnchor, computeSL, computeTP + TODO sentinel), shared/scoring-engine.api.md (חוזה API), shared/scoring-engine.test.js (node:test), shared/package.json.
- DB CHANGES: אין
- CONFIG ADDED: אין
- VALIDATION: node --test 3/3 ✅ | node --check parse ✅ | pytest 3/3 ✅ | tsc clean ✅ | eslint clean ✅
- ATP: נוסף TC-P1.5-001 (placeholder חשוף, חתימות קיימות, כל stub מחזיר TODO).
- VERSION: v0.2.1
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: תשתית המנוע המשותף מוכנה כשלד. P2 (ליבת סריקה) יוכל לייבא את הקובץ ברגע שהמימוש האמיתי יחולץ מהכלי האישי.
- DECISIONS:
  1. **stubs מחזירים sentinel `TODO`** (אובייקט קפוא, truthy ולא-מספר) במקום לזרוק — כדי שכל שימוש מוקדם ייחשף מייד ולא יזרים ערך שגוי לסריקה.
  2. **`shared/package.json` עם `type:module`** — כדי ש-`.js` (כפי שנדב ביקש, לא `.mjs`) יעבוד כ-ESM בשני הצרכנים. גם מניח את הבסיס ל-npm package משותף (SPEC §6.1).
  3. **`computeSL/TP` פוצל ל-`computeSL` + `computeTP`** נפרדים; ייתכן שיתאחדו כשהמימוש האמיתי יגיע (מתועד בחוזה כ"provisional").

## [P0 / ניקוי והקמת שלד נקי] — 2026-06-30
- GOAL: לרשת מ-hamakpetza את שכבת התשתית בלבד ולהקים שלד FINARODA נקי — בלי שכבת קריירה/Agent, סכמה אחת מודרנית, תשלום אחד (Cardcom), אפליקציה עולה נקייה. (SPEC §3, §4, §5, §11)
- SOLUTION: השורש היה ריק מקוד (רק מסמכים + עותק רפרנס read-only). לכן P0 בוצע כ**בנייה נקייה מאפס** ולא כ"העתק-ואז-מחק": נכתבה תשתית חדשה שלא כוללת מלכתחילה את שכבת הקריירה. נבנה backend (FastAPI) + frontend (Next.js 15 route groups, placeholders) + 18 migrations נקיות על internal_id + Cardcom placeholder יחיד.
- FILES CREATED:
  - Backend: backend/{config.py, main.py, requirements.txt, .env.example}, backend/core/{logging_config.py, cardcom_service.py}, backend/api/cardcom.py, backend/migrations/{run_migrations.py + 001..018}, backend/tests/{conftest.py, test_smoke.py}, __init__.py בכל החבילות.
  - Frontend: frontend/{package.json, tsconfig.json, next.config.ts, .eslintrc.json, .gitignore}, frontend/src/app/{layout.tsx, globals.css, page.tsx}, route groups (scan)/(dashboard)/(admin)/(academy)/(auth) + checkout/paywall/legal/coming-soon (placeholders), frontend/src/lib/strings.ts.
  - Root: .gitignore (כולל hamakpetza-audit-copy/), pytest.ini.
- FILES DELETED: אין — לא היה קוד למחוק בשורש. שכבת הקריירה לא נכנסה מלכתחילה (ראו DECISIONS).
- DB CHANGES: 18 migrations נקיות חדשות (סכמה בלבד, ללא קוד פיצ'ר):
  001 users (נקי — בלי telegram_id/קריירה; +default_threshold/last_scan_at/is_admin), 002 billing (payment_transactions+subscription_events), 003 coupons(+applications), 004 referral (REST, הנחה כספית — לא טוקנים), 005 notifications+consent_log, 006 customer_segments+churn_reasons+admin_events, 007 feature_flags(+overrides), 008 system_settings (+seed: coins-per-plan, threshold), 009 academy, 010 oauth_states, 011 beta_allowlist (seed founder), 012 waitlist, 013 broadcasts, 014 onboarding, 015 scan_events, 016 score_log, 017 decision_snapshots, 018 support_tickets (מודרני). כל ההתנגשויות (users/coupons/consents/tickets) נפתרו לטובת הווריאנט המודרני.
- CONFIG ADDED (שמות בלבד): DATABASE_URL, FEATURE_CARDCOM_LIVE, CARDCOM_TERMINAL_ID/TEST_TERMINAL/API_NAME/API_PASSWORD/WEBHOOK_SECRET/BASE_URL/REDIRECT_RETURN_URL, BYBIT_PUBLIC_BASE_URL, DEFAULT_SCAN_THRESHOLD, TRIAL_DAYS, FEATURE_PUBLIC_SIGNUPS_OPEN, R2_*, RESEND_*, EMAIL_*, SENTRY_*, JWT_*, GOOGLE_*/APPLE_*. (כל הקריירה/Morning/Stripe/RAG הוסרו.)
- VALIDATION: pytest 3/3 ✅ | tsc --noEmit clean ✅ | eslint (next lint) clean ✅ | uvicorn boot → /api/health 200, /api/cardcom 501 ✅ | next build → 13 routes ✅
- ATP: נוספו TC-P0-001..004 (migrations נקיות, אין טבלאות קריירה, health, cardcom placeholder).
- VERSION: v0.2.0
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: שלד נקי ופורס. אין שכבת קריירה, אין core/db.py, אין סכמה כפולה, אין Morning/Stripe/Telegram, אין תלויות chromadb/voyage/openai/rank_bm25/pdfplumber/python-docx/reportlab. בסיס מוכן ל-P1 (תשתית חיה).
- DECISIONS:
  1. **git מושרש בטעות ב-C:\Users\rodan (כל תיקיית הבית), branch master, ללא commits** — commit שם היה לוכד .ssh/סודות/NTUSER.DAT. אותחל repo ייעודי בתוך finaroda-saas על branch `dev`. לא נגעתי ב-repo של הבית ולא ב-main.
  2. **אין remote (`origin`)** — בוצע commit מקומי על dev בלבד; push חסום עד שנדב יגדיר remote (CLAUDE.md §2.8 דורש push origin dev — לא ניתן לבצע ללא remote).
  3. **השורש ריק מקוד** → P0 בוצע כבנייה נקייה (לא העתק-ואז-מחק). תוצאה זהה, נתיב נקי יותר.
  4. **scope = שלד+סכמה בלבד** לפי ההנחיה ("placeholder", "סכמה בלבד"). פורט מלא של auth/cardcom/admin = P1+.
  5. **אוצר מילים פלאנים אוחד** ל-free/basic/advanced/pro (מול premium/b2b/pro/unlimited הישנים; SPEC §3.2).
  6. **is_admin כעמודה ב-users** הוכן לקראת הקשחת SPEC §4 (admin כתפקיד DB, לא רשימת env).

## [INIT / Project scaffolding] — YYYY-MM-DD
- GOAL: הקמת repo finaroda-saas מ-template hamakpetza + הנחתת מסמכי מקור-אמת ובקרה
- SOLUTION: יצירת repo נפרד, הנחת CLAUDE/PRD/SPEC/UX/LEGAL + CHANGELOG/VERSIONS/SESSION_HANDOFF/ATP
- FILES CREATED: CLAUDE.md, PRD.md, SPEC.md, UX.md, LEGAL.md, CHANGELOG.md, VERSIONS.md, SESSION_HANDOFF.md, ATP.md
- DB CHANGES: אין (P0 ניקוי מגיע בנפרד)
- CONFIG ADDED: אין
- VALIDATION: לא רלוונטי (מסמכים בלבד)
- ATP: 0/0 (sprint תשתית)
- VERSION: v0.1.0
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: הפרויקט מוכן עם משטר עבודה מלא ומסמכי מקור-אמת
- DECISIONS: branch gate (Claude→dev, נדב ממזג ל-main); קהל יעד = בוני-הון (לא המקפצה)
