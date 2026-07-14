# VALIDATION REPORT — FINARODA SaaS (pre-Stage-8 quality gate)

**Date:** 2026-07-14 · **Branch:** dev · **Target version:** v0.17.1
**Procedure:** `validation/ATP_V1.md` · **Author:** Claude Code (automated ATP run)

---

## ⚑ TOP OF REPORT — red-line status (stop-point S2)

No reveal-leak, no XP spend path, no money-float, no entitlement PLAN/RANK bypass was
found in shipped code. The reveal-gating, XP-economy, and money red lines are **intact**
and now guarded by dedicated suites.

**One entitlement-STATE gap was found and fixed** (not a value leak): the admin
**suspend** action set `suspended_at`/`active=0` but no endpoint enforced it, so a
suspended account kept full access. This is a moderation-control no-op, not a
reveal/XP/money violation — but the founder should know it existed. Fixed this run
(FINDING-1) with a one-line server-authoritative check + regression test.

---

## 1. Environment fingerprint

| Field | Value |
|---|---|
| Git HEAD (pre-run) | `fa6057d` (dev) |
| Python | 3.13.5 |
| Node | v22.11.0 |
| Next.js | 15.5.19 |
| Backend suite | 182 pytest checks (146 pre-existing + 36 new V1) |
| Frontend suite | 58 node:test checks |
| Static gates | tsc clean · eslint clean · `next build` OK |
| Fresh-env run | clean `python -m venv` + `pip install -r requirements.txt` → **182 passed** |
| Run timestamp | 2026-07-14 (local) |

Fresh-environment execution (clean venv, clean install, production build) all passed —
no missing-dependency or build finding. All runtime deps are correctly declared in
`backend/requirements.txt` (verified aiosqlite, stripe, resend, sentry-sdk, etc.).

## 2. Findings (measured before any fix — P2)

| ID | Severity | Area | Finding | Detected by |
|---|---|---|---|---|
| FINDING-1 | **P1** | Entitlements (state) | Admin `suspend` sets `suspended_at`/`active=0`, but `get_current_user` never checked it → a suspended account retained access to every protected endpoint. Silent no-op of a moderation control. | TC-V1-ENT-09 |

No P0 findings. No other P1 findings. Production build passed (not a P0).

### Known-issue register re-verification (from HANDOFFs)
| Reported drift | Re-verified result | Classification |
|---|---|---|
| Stage-5 email templates contain em-dashes (5-DRIFT1) | Backend rendered email copy uses hyphens; em-dashes are only in Python comment dividers / dev docstrings (not user-facing). No user-facing violation. | Closed (not a defect) |
| em-dash lint flags JSX block comments (5-DRIFT2/6-FU3) | Reproduced as a guard fragility. **Fixed** (pre-approved): the guard now strips `/* */` and `{/* */}` comments before scanning, with a meta-test proving it. | Fixed |
| `next build` unverified locally (3R-ISSUE1/4-FU5) | Ran clean: `next build` exit 0, all 21 routes compiled. | Closed |
| stripe pin vs venv drift (3R-DRIFT1) | requirements pins `stripe>=9,<13`; behaviour verified via mocked SDK; no runtime break. | Noted (ops) |
| Referral zero-XP (AC8) | Re-asserted: zero xp_events writes in any Stage-4 path. | Confirmed |

## 3. Fixes applied (P3)

### FINDING-1 — enforce account suspension (minimal diff)
- **File:** `backend/core/auth.py` (`get_current_user`)
- **Change:** added `suspended_at` to the user SELECT; if set, raise
  `403 {code: ACCOUNT_SUSPENDED}`. Single chokepoint → covers all ~47 authenticated
  endpoints. `unsuspend` (sets `suspended_at=NULL`) restores access.
- **Regression test:** `TC-V1-ENT-09` (`test_suspended_account_is_blocked`) — an existing
  session loses access the moment an admin suspends the account.
- **Blast radius:** only users with a non-null `suspended_at` (set solely by the audited
  admin override) are affected; default users have NULL and are unchanged.

### Pre-approved hardening — em-dash guard trustworthiness
- **File:** `backend/tests/test_content_copy.py`
- **Change:** refactored `test_no_em_dash_in_product_copy` to strip block/JSX/line comments
  via a shared `_strip_comments` helper before scanning; added
  `test_em_dash_guard_ignores_comments_but_catches_copy` (meta-test) so the lint is
  provably trustworthy (ignores comments, catches real copy).

## 4. Post-fix results — final pass/fail

| Suite | Result |
|---|---|
| Backend pytest (project venv) | **182 / 182 pass** |
| Backend pytest (fresh clean venv) | **182 / 182 pass** |
| Frontend node:test | **58 / 58 pass** |
| tsc --noEmit | clean |
| eslint src | clean |
| next build (production) | OK (21 routes) |
| **Red-line suites** | RVL 9/9 · XP 7/7 · ENT 7/7 · MON 6/6 · LINT 2/2 · copy 4/4 |
| **E2E journeys** | 4/4 |

**Suite is GREEN (P2-debt-only remaining).**

## 5. P2-debt register (accepted)

| ID | Item | Rationale |
|---|---|---|
| DEBT-1 | `require_active_trial` dependency defined but not wired to an endpoint | Trial expiry already handled by daily cron → Free + `effective_tier` collapse. Wiring it to `/billing/*` is a product-flow decision (would 402 an expired-trial user mid-flow) — out of scope for a validation run; flagged for the founder. |
| DEBT-3 | No rate-limit on `/api/market/proxy` and auth endpoints | Hardening-phase concern (slowapi is a dep, not yet applied); not a shipped-feature regression. |

DEBT-2 (email em-dash) was investigated and **closed** — no user-facing violation exists.

## 6. Sign-off

- ATP built as code (runs every future stage): `validation/ATP_V1.md` + 6 new test files.
- All P0/P1 fixed; suite green on a fresh clean install and a production build.
- No product-behaviour decision was made unilaterally; DEBT-1 is escalated, not decided.
- **Ready for founder review; not merged to main (per CLAUDE.md §1).**
