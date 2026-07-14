# ATP_V1 — FINARODA SaaS Acceptance Test Procedure (full-product)

> Scope: v0.10.x → v0.17.0 (Stage 4). Depth: CI/CD. This is the runnable acceptance
> procedure — every automatable item is CODE (pytest / node:test), executed on every
> future stage, not once. Manual-only items (visual flash, real-device touch, pixel
> judgement, live-Stripe/live-Resend) are listed at the bottom for the founder.
>
> Companion report: `VALIDATION_REPORT_2026-07-14.md` (findings + fixes + pass/fail).

## 0. How to run

```bash
# Backend (from repo root, venv active)
python -m pytest                       # 182 checks

# Frontend (from frontend/)
npx tsc --noEmit                       # types
npx eslint src --ext .ts,.tsx          # lint
node --test --experimental-strip-types "tests/**/*.test.ts"   # 58 checks

# Production build (fresh-env gate; a build failure is a P0)
cd frontend && npx next build
```

## 1. Honest count (S3)

The founder's brief targeted ~400–500 checks. Per stop-point S3, this ATP is the
**honest maximum without padding**, prioritising the red-line invariants (the product's
constitution) as dedicated suites over duplicate trivial assertions.

| Layer | Test cases | Notes |
|---|---|---|
| Backend pytest | **182** | 146 pre-existing (absorbed) + 36 new V1 checks |
| Frontend node:test | **58** | pure-logic unit + viewport regression |
| Static gates | tsc, eslint, `next build` | typed + linted + production build |
| **Total automated test cases** | **240** | comprising ~700+ individual assertions |

Coverage is proven by the matrix in §3 (every Stage 3R/4/5/6/7 AC maps to ≥1 check),
not by a raw number. Where an AC is genuinely un-automatable it is in the MANUAL-ONLY
section (§6), not silently skipped.

## 2. Red-line invariant suites (the constitution, tested as laws)

These are the dedicated suites added in V1. Each red line has its own file.

| Suite | File | Checks | The law |
|---|---|---|---|
| Reveal-gating | `test_v1_redline_reveal.py` | 9 | An unrevealed outcome (status/r_result/resolved_at) never serialises into ANY client payload — journal, scan, history, notifications, emails, breadcrumbs, admin tickets. |
| XP economy | `test_v1_redline_xp.py` | 7 | Closed 5-source list; no spend/mutation path (static guard over all backend); exact locked amounts (300/50/100/25); idempotency schema; rank ladder 0/1000/3000/8000. |
| Entitlements | `test_v1_redline_entitlements.py` | 7 | Server-authoritative: 401 without session, 403 for non-admin (incl. Stage-4 promos), plan matrix buys breadth only (never a verdict), state machine collapses to Free, academy dual-gate, suspended account blocked. |
| Money (agorot) | `test_v1_redline_money.py` | 6 | Integer agorot only — static float-guard over money files (no `float()`, no Decimal/Fraction, no float literal), integer-exact formatter, int plan prices, INTEGER DB columns. |
| Lint / hygiene | `test_v1_redline_lint.py` | 2 | No committed secret-key material (sk_live/sk_test/whsec/rk_live/pk_live+value); zero Cardcom in live code. |
| Copy lint | `test_content_copy.py` | 4 | Tooltip content shape + drift guard + **em-dash guard (now JSX-comment-trustworthy)** + a meta-test proving the guard ignores comments and catches real copy. |

E2E journeys (`test_v1_e2e.py`, 4): onboarding→scan→reveal→academy XP=475 · subscribe(DEV)
→webhook activate→cancel→churn→admin · referral bind→friend paid→reward→bell→read ·
coupon admin-create→validate→wrong-plan-checkout-reject.

## 3. Coverage matrix — every stage AC → ≥1 check

Legend: `TC-V1-*` = new this run. Bare `test_*` / `TC-*` = pre-existing absorbed check.
`MANUAL` = §6 manual-only.

### Stage 3R — Stripe Checkout + Billing (v0.16.0)
| AC | Assertion | Check |
|---|---|---|
| 3R-C1/C2/API1 | DEV fake Checkout Session, zero network | TC-V1-E2E-02, test_stage3r_stripe |
| 3R-C4 | activation ONLY via webhook, never redirect | TC-V1-E2E-02, test_stage3r_stripe |
| 3R-W1/W2/W3 | signed webhook, event-id dedup, event set | test_stage3r_stripe, TC-S4-18 |
| 3R-W4/W5/W6/W7/W8 | activate/recurring/failed/cancel/expire handlers | test_stage3r_stripe |
| 3R-R3/R4 | state machine + active→expired edge | TC-V1-ENT-05, test_stage3r_stripe |
| 3R-CX1/CX2 | cancel at period end → cancelled | TC-V1-E2E-02, test_stage3r_stripe |
| 3R-T1..T5 | card-free trial, expiry→Free, day-11 reminder | test_b1_gating (trial_expires_to_free), test_stage5 |
| 3R-IX4/IX5 | one tax doc per amount>0; zero-amount → no doc | TC-S4-15, test_stage3r_stripe |
| 3R-M1..M6 | migration 035 renames + processed_webhook_events | test_stage3r_stripe, test_smoke |
| 3R-E1/E2 | Stripe env in; Cardcom env out | TC-V1-LINT-02, TC-R3-12 |
| 3R-GL* | live keys / provider / webhook wiring | MANUAL (go-live) |

### Stage 4 — Coupons + Referral (v0.17.0)
| AC | Assertion | Check |
|---|---|---|
| 4-CP1/CP2/CP3 | Stripe coupon+promo, admin drives, mirror row | TC-S4-02/03/05, TC-V1-E2E-04 |
| 4-CP5 | plan restriction enforced our-side before session | TC-S4-04, TC-V1-E2E-04 |
| 4-CP4/CP8 | redemption sync + max/expiry enforced | TC-S4-06/07 |
| 4-RF1/RF2/RF3 | permanent code, bind once, self-referral blocked | TC-S4-08/09 |
| 4-RF4/RF5/RF6 | first paid → reward (balance credit / banked) | TC-S4-10/11, TC-V1-E2E-03 |
| 4-RF7/RF8 | reward idempotent; 100%-coupon month≠reward | TC-S4-10/12 |
| 4-RF9 | admin void (compensating / plain) | TC-S4-14 |
| 4-M1..M5 | migration 036 reshape + audit CHECK | TC-S4-01, test_smoke |
| 4-TAX1/TAX2 | zero-total → no doc; amount>0 → doc | TC-S4-15 |
| 4-AC8 | zero XP writes in any Stage-4 path | TC-S4-16, TC-V1-XP-06 |
| 4-FU* | admin/referral browser click-throughs | MANUAL |

### Stage 5 — Notifications + Prefs + Resend (v0.11.0)
| AC | Assertion | Check |
|---|---|---|
| 5-B1..B5 | bell feed, 9+ cap, mark-read, type set, pref gate | test_stage5, TC-V1-E2E-03 |
| 5-P1..P5 | prefs table, 5 flags, respected at send | test_stage5 |
| 5-T1..T4 | day-11 reminder once, opted-in, no CTA pressure | test_stage5 |
| 5-RT1..RT5 | teaser dedup + **no outcome values** | TC-V1-RVL-06, test_stage5 |
| 5-R1..R5 | Resend renderers, DEV fallback, unsubscribe link | test_stage5, TC-V1-RVL-06 |
| 5-C1..C6 | cron sweeps idempotent, fail-closed | test_stage5 |
| 5-BC1..BC5 | broadcast preview/send/audience/banner | test_pkg_b_phase2, test_stage5 |
| 5-EC1..EC4 | unsubscribe endpoint token, spam-act | test_stage5 |
| 5-FU*/DRIFT1 | live send, sound/vibration, email em-dash | MANUAL / P2-debt (§5) |

### Stage 6 — Academy 2.0 (v0.13.0)
| AC | Assertion | Check |
|---|---|---|
| 6-AC1/AC2/AC3 | dual-gate; locked → 403 body/video withheld | TC-V1-ENT-06, test_academy_v2 |
| 6-AC4/AC5/AC6 | +100 once; stubs 0; migration additive | test_pkg_b_phase2, test_academy_v2, TC-V1-XP-05 |
| 6-V1/V3 | video URL validation; gated content | test_academy_v2 |
| 6-R1/AR1..AR3 | reorder; archive/restore; XP never revoked | test_academy_v2 |
| 6-ADM1..ADM4 | admin CRUD 403 + audited | test_academy_v2, TC-V1-ENT-02 |
| 6-SEED1..5 | 12 lessons, slug==module_id, B6 parity | test_pkg_b_phase2, test_academy_v2 |
| 6-E2 | rank = status, never currency | TC-V1-XP-01/02, TC-V1-XP-07 |
| 6-FU* | responsive/video browser click-through | MANUAL |

### Stage 7 — Admin v1.1 + Sentry + Breadcrumbs (v0.12.0)
| AC | Assertion | Check |
|---|---|---|
| 7-AU1..AU5 | columns, AND filters, CSV, active-days analytics-only, churn flag | test_stage7_admin |
| 7-CH1..CH5 | churn survey, stored, decoupled from billing | TC-V1-E2E-02, test_stage7_admin |
| 7-S1..S6 | Sentry env-gated, PII scrub, zero-network off | test_stage7_admin |
| 7-BC1..BC5 | breadcrumbs ring, allowlist, **no outcome value** | TC-V1-RVL-01/02/05, test_stage7_admin |
| 7-ADMIN1/2 | admin-gated; score-gate LOCKED | TC-V1-ENT-02, test_pkg_b_phase2 |
| 7-XP1/XP2 | admin grant XP audited (admin_grant source) | TC-V1-XP-05, test_academy_v2 |
| 7-AUD1/2 | admin_events audit trail | test_pkg_b_phase2, test_stage7_admin |
| **suspend enforcement** | suspended account blocked (was a no-op) | **TC-V1-ENT-09 (finding, fixed)** |
| 7-FU* | responsive/Sentry-live browser | MANUAL |

### v0.10.x + Onboarding + XP
| AC | Assertion | Check |
|---|---|---|
| 10-XP1..XP3 / ON-XP1..4 | 300 once, S9 grant, idempotent | test_p3_onboarding, TC-V1-XP-04/05, TC-V1-E2E-01 |
| 10-429-1..3 | free 1/day → 429; paid unlimited | TC-V1-ENT-04, test_b1_gating |
| 10-REC1..3 | recent scans read-only, no outcome | TC-V1-RVL-04, test_b1_gating |
| 10-S11T1..3 | plan table Free/Basic/Pro accurate to config | test_b1_gating (plans), promotions.unit |
| ON-EP3 / ON-S10 | episode outcome withheld until reveal | test_p3_onboarding, TC-V1-RVL-03 |
| ON-TOOLTIP1..4 | 46 tooltip terms, shape, drift | test_content_copy |
| 10-FL1/FL2 | S5→S6 no flash | MANUAL |

## 4. Test-type coverage (matrix axis 2)

| Test type | Where |
|---|---|
| API contract | TC-V1-E2E-*, test_b1/p1/p2/stage* |
| Permission / 403 / 401 | TC-V1-ENT-01/02, test_pkg_b_phase2, test_academy_v2 |
| State machine | TC-V1-ENT-05, test_stage3r_stripe |
| Webhook idempotency | test_stage3r_stripe, TC-S4-06/10/18 |
| Gating red-lines | TC-V1-RVL-*, TC-V1-ENT-*, TC-V1-XP-* |
| XP economy invariants | TC-V1-XP-01..07 |
| Money integrity | TC-V1-MON-01..06 |
| Migration integrity | test_smoke, TC-S4-01, TC-V1-XP-04 |
| UI component render | frontend/tests/*.unit + viewport.regression |
| Copy lint | test_content_copy, TC-V1-LINT-* |
| Config / env fallback | entitlements defaults, DEV fallbacks in stage tests |

## 5. P2-debt register (accepted, not fixed this run)

| ID | Item | Why not fixed | Severity |
|---|---|---|---|
| DEBT-1 | `require_active_trial` defined but not wired to an endpoint | Trial expiry is handled by the daily cron → Free + `effective_tier`; the dependency is latent, not a gap. Wiring it is a product-flow decision. | P2 |
| DEBT-2 | Welcome/beta email templates historically flagged for em-dash | Backend rendered copy verified em-dash-free (hyphens used); dashes are in Python comment dividers/docstrings, not user-facing. No fix needed. | P2 (closed) |
| DEBT-3 | Market-proxy has no rate-limit; auth endpoints no throttle | Out of ATP scope (hardening phase); not a shipped-feature regression. | P2 |

## 6. MANUAL-ONLY (founder checklist — cannot be honestly automated)

Rendering judgement, real devices, and live third parties are not faked here.

**Visual / responsive (390px & 1280px):**
- [ ] S5→S6 onboarding transition: no stale pre-scan frame flashes (10-FL1/FL2) — fresh incognito user.
- [ ] All 12 onboarding screens + 1a branch render + tooltips (ON-FU1).
- [ ] Academy card grid / search / lazy video / locked-card reason (6-FU1).
- [ ] Admin filters / CSV / ticket breadcrumbs / responsive master-detail (7-FU1).
- [ ] Bell open/mark-read, 5 Settings toggles, broadcast preview (5-FU2).
- [ ] TRIAL chip on /scan; SEE PLANS→back restores results; currency selector (v0.10.0 sweep).

**Live third-party (blocked until go-live):**
- [ ] Real Stripe test account: /subscribe → hosted checkout → success/cancel → webhook → BillingBanner (3R-FU1).
- [ ] Coupon create/deactivate + referral void in real Stripe (4-FU1); hosted promotion-code field (4-FU4).
- [ ] Live Resend send (needs finaroda.com verified) (5-FU1).
- [ ] Sentry activation on built frontend (7-FU2).
- [ ] Arrival sound/vibration on real device (5-FU3).

**Blockers (not testable now):** Stripe live account, Israeli tax-invoice provider, attorney
sign-off, domain + DNS, accountant VAT review — tracked in SESSION_HANDOFF / OPEN_ITEMS.
