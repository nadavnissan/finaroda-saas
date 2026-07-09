# ATP — Acceptance Test Plan (FINARODA SaaS)

> תוכנית בדיקות קבלה. כל פיצ'ר → TC חדש. כל באג מתוקן → מקרה רגרסיה. הרצה מייצרת ATR-{date}.md.

---

## מבנה מקרה בדיקה
```
### TC-XXX — שם
- Feature: F-נ (מ-PRD)
- Precondition: תנאי כניסה
- Steps: 1) ... 2) ...
- Expected: התוצאה הצפויה
- Status: ⬜ not-run | ✅ pass | ❌ fail
```

---

## קבוצות בדיקה (ימולאו לפי הפאזות)
- **TC-A — Auth & onboarding** (magic-link, Google, beta gate, survey)
- **TC-B — Scan core** (כפתור, אנימציה, עיגולים, מחסור/empty state)
- **TC-C — Decision card** (Entry/SL/Trailing/TP, תלת-דרגתי, תיוג ניתוח-לא-ייעוץ)
- **TC-D — Score log & backtest** (רישום כל מטבע, cron, "מה היה קורה")
- **TC-E — Client dashboard** (תשואה היפותטית, ייצוא תוצאות)
- **TC-F — Billing & trial** (Cardcom, **trial ללא כרטיס** — change order 2026-07-09, בחירה אקטיבית בסוף, ביטול)
- **TC-G — Referral** (קוד, 3-חודשים, בקרת אדמין)
- **TC-H — Admin** (לקוחות, MRR/churn, טיקטים, ברודקאסט, קופונים, סף נשלט)
- **TC-I — Profile & status tiers** (מבוסס משמעת לא תדירות)
- **TC-J — Legal/copy guard** (אין מילים אסורות, דיסקליימר בכל מסך)

---

## TC — P0 (שלד נקי) — אוטומטיים (backend/tests/test_smoke.py)

### TC-P0-001 — סכמה נקייה מיושמת במלואה
- Feature: F-תשתית (SPEC §5)
- Precondition: DB ריק
- Steps: 1) apply_migrations על DB זמני 2) שאילתת sqlite_master
- Expected: 29 הטבלאות הצפויות קיימות (users..support_tickets)
- Status: ✅ pass

### TC-P0-002 — אין דליפת טבלאות קריירה
- Feature: F-תשתית (SPEC §3.3)
- Precondition: סכמה הוחלה
- Steps: 1) בדיקת קבוצת FORBIDDEN_TABLES מול הסכמה
- Expected: אף טבלת קריירה/Agent (conversations, cv_versions, simulation_*, panel_*, pending_questions...) לא קיימת
- Status: ✅ pass

### TC-P0-003 — האפליקציה עולה ו-health מחזיר 200
- Feature: F-תשתית (SPEC §11)
- Precondition: —
- Steps: 1) TestClient(app) 2) GET /api/health
- Expected: 200, status=ok, version=0.2.0; lifespan מריץ migrations נקי
- Status: ✅ pass

### TC-P0-004 — Cardcom placeholder מחווט (501)
- Feature: F-תשלום (SPEC §9)
- Precondition: —
- Steps: 1) POST /api/cardcom/initiate
- Expected: 501, code=NOT_IMPLEMENTED (חיווט מלא ב-P1)
- Status: ✅ pass

## TC — P1.5 (מנוע סריקה — placeholder) — אוטומטי (shared/scoring-engine.test.js)

### TC-P1.5-001 — placeholder של scoring-engine חשוף ומחזיר TODO
- Feature: F-סריקה (SPEC §6.1)
- Precondition: —
- Steps: 1) ייבוא shared/scoring-engine.js 2) בדיקת חתימות 3) הפעלת כל stub
- Expected: TODO sentinel קפוא; ema7Slope/scoreDirection/computeReversalAnchor/computeSL/computeTP קיימות; כל אחת מחזירה TODO (בלי מימוש/חיבור Bybit)
- Status: ✅ pass (node --test 3/3)

## TC — P1 (תשתית חיה) — אוטומטי (backend/tests/test_p1_auth_billing.py)

### TC-A — Auth
| TC | תיאור | Expected | Status |
|----|-------|----------|--------|
| TC-A-001 | magic-link signup+login+/me | user נוצר, cookie נקבע, /me מחזיר email | ✅ |
| TC-A-002 | /me בלי cookie | 401 | ✅ |
| TC-A-003 | magic-link token נשמר כ-hash | stored == sha256(raw), != raw (SPEC §4) | ✅ |
| TC-A-004 | bootstrap admin (founder) | is_admin=true בהרשמה (DB role) | ✅ |
| TC-A-005 | Apple stub | 501 | ✅ |
| TC-A-006 | beta gate סגור | allowlisted עובר, אחר נחסם | ✅ |
| TC-A-007 | waitlist join | 200 + email | ✅ |

### TC-F — Billing / Cardcom (TEST mode)
| TC | תיאור | Expected | Status |
|----|-------|----------|--------|
| TC-F-001 | initiate בלי auth | 401 | ✅ |
| TC-F-002 | initiate ב-test mode (authed) | 503 (אין חיוב אמיתי) | ✅ |
| TC-F-003 | status אחרי login | subscription_status=none, tier=free | ✅ |
| TC-F-004 | webhook עם חתימה שגויה | 200 received, בלי שינוי state | ✅ |
| TC-F-005 | start_trial (**ללא כרטיס**, D1) | trial 14 יום · tier=pro · `next_billing_at` **NULL** · `cardcom_token` NULL (אין חיוב אוטו) | ✅ |
| TC-F-006 | expire_trials (**→ Free**, D1/D2) | trial שפג → tier=free, subscription_status=none, `next_billing_at` NULL, event `trial_ended_to_free` (לא expired/blocked, אף פעם לא מחויב) | ✅ |
| TC-F-007 | start_trial פעם שנייה | 409 (trial already used) | ✅ |
| TC-F-008 | renewal batch לא מחייב trials | רק `subscription_status='active'` מחויב; trial (גם עם next_billing עבר) אף פעם לא | ✅ |

> **מומש (2026-07-09, change order D1 — v0.5.0):** TC-F-005/006 **נכתבו מחדש** ל-trial ללא כרטיס + downgrade ל-Free. הקוד (`start_trial`/`expire_trials`/`run_renewal_batch`) שונה בהתאם; migration 022 הוסיפה את event_type `trial_ended_to_free`. TC-DOCS-001/002 עברו ל-✅.

## TC — ENGINE (shared scoring-engine) — automated (shared/scoring-engine.test.js)

### TC-ENGINE-001 — levels engine extracted, byte-faithful, scorer still a stub
- Feature: F-scan (SPEC §6.1)
- Precondition: —
- Steps: 1) `cd shared && node --test`
- Expected: 8/8 pass. calcEMA/RSI/ATR/ADX, closedCandles, ema7Slope (signed),
  computeSlTp (SL on correct side), computeReversalAnchor (floor/fires) verified against
  golden vectors from the personal tool v25.80. `scoreDirection` is a guarded stub that
  throws (pass-2 extraction pending golden vectors).
- Status: ✅ pass (node --test 8/8)

## TC — P2 (scan core)

### TC-B — Scan flow & persistence (automated: backend/tests/test_p2_scan.py)
| TC | Description | Expected | Status |
|----|-------------|----------|--------|
| TC-B-001 | Scan records events + score_log | scan_event + one score_log per coin, score NULL | ✅ |
| TC-B-002 | Scan events require auth | 401 without cookie | ✅ |
| TC-B-003 | Blueprint snapshot persisted | decision_snapshot created for owner | ✅ |
| TC-B-004 | Snapshot ownership | can't snapshot another user's score_log → 404 | ✅ |
| TC-B-005 | CORS proxy whitelist | disallowed endpoint → 400 | ✅ |
| TC-B-006 | score_log.score nullable (migration 020) | PRAGMA notnull=0 | ✅ |

### TC-C — Trading Blueprint (validated by build + tsc; UI)
| TC | Description | Expected | Status |
|----|-------------|----------|--------|
| TC-C-001 | Terminology (PRD §3.5.1) | Mathematical Trigger Point / Calculated Risk Level / Calculated Target Level / Dynamic Risk Level / "Trading Blueprint" | ✅ (build) |
| TC-C-002 | Formula-transparency note per level (§3.5.2) | each level shows "Calculated via …" | ✅ (build) |
| TC-C-003 | Score pending, real levels; Lens display-only; Risk Style geometry-only | "Score pending — engine pass 2"; scoreDirection never called; RED LINE honored | ✅ (build) |

> Since the scorer landed (v0.4.1), `SCORE_GATE_ENABLED=true`: visibility is the real
> 85/82 gate on the numeric score; the interim rule is retired. The lens is now display-only.

### TC-SCORER — real score wired (shared/scorer.test.js + backend/tests/test_p2_scorer.py)
| TC | Description | Expected | Status |
|----|-------------|----------|--------|
| TC-SCORER-001 | Scorer runs end-to-end (JS) | node --test 12/12 (8 engine + 4 scorer); score 0–110, valid signal, 11 components | ✅ |
| TC-SCORER-002 | 3 profiles logged, momentum only returned | momentum+pullback+continuation rows; only momentum linked for snapshot | ✅ |
| TC-SCORER-003 | Real score persisted + profile column | score non-null on momentum; score_log.profile present (mig 021) | ✅ |
| TC-SCORER-004 | 85/82 gate + RED LINE (build/tsc) | PASS ≥85 / WATCH 82-84 / blocked hidden; Risk Style changes levels not score | ✅ (build) |

## TC — DOCS ALIGNMENT 2026-07-09 (spec-level; ⬜ pending implementation — code unchanged)

> נובעים ממשימת יישור הדוקים ל-ALIGNMENT_2026-07-09 (D1 trial ללא כרטיס, D2 Free tier, F13 onboarding, B3 reveal-gating). כולם ⬜ not-run עד מימוש בקוד (ROADMAP S3/X1). מתועדים עכשיו כדי שהמימוש ייבדק מולם.

### TC-DOCS-001 — Trial ללא כרטיס (D1)
- Feature: F7 (PRD) · SPEC §9/§12.3
- Precondition: משתמש חדש נרשם (פרטים אישיים בלבד)
- Steps: 1) הרשמה 2) הפעלת trial 3) בדיקת מצב חיוב
- Expected: trial 14 יום מופעל **ללא כרטיס ו-ללא tokenization**; אין `next_billing` לחיוב אוטומטי; תזכורת מתוזמנת ליום 11 (`TRIAL_REMINDER_LEAD_DAYS=3`); בסוף התקופה המשתמש נדרש לבחור אקטיבית (פלאן בתשלום או Free) — אין חיוב אוטומטי
- Status: ✅ pass (v0.5.0 — `start_trial` no-card; automated: TC-F-005)

### TC-DOCS-002 — Trial end → Free fallback (D1)
- Feature: F7 (PRD)
- Precondition: trial הגיע לסופו והמשתמש לא בחר פלאן בתשלום
- Steps: 1) הרצת expire/end-of-trial 2) בדיקת tier
- Expected: המשתמש נופל ל-**Free** (tier=free, subscription_status=none; לא חיוב, לא expired/blocked); לכידת כרטיס מתרחשת רק בהמרה אקטיבית לתשלום; renewal batch אף פעם לא מחייב trial
- Status: ✅ pass (v0.5.0 — `expire_trials`→Free + renewal excludes trials; automated: TC-F-006, TC-F-008)

### TC-DOCS-003 — Free tier limits (D2)
- Feature: F7 (PRD) · SPEC §9 · UX §6
- Precondition: משתמש במסלול Free
- Steps: 1) לבצע 2 סריקות באותו יום 2) לפתוח F3 3) לנסות ייצוא
- Expected: סריקה 2/יום נחסמת (1/יום); 2 מטבעות; Blueprint מלא זמין; F3 מוגבל ל-7 הימים האחרונים; ייצוא חסום; academy בסיסי. **כל המגבלות נקראות מ-`system_settings`** (ניתנות לכיול אדמין בלי קוד)
- Status: ⬜ not-run (pending implementation)

### TC-DOCS-004 — Paywall "Continue on Free" (D2)
- Feature: F7 (PRD) · Onboarding §3 מסך 11
- Precondition: משתמש במסך paywall/פיצול
- Steps: 1) הצגת מסך הפיצול
- Expected: אפשרות ראשית "Start 14 days — no credit card"; אפשרות **משנית "Continue on Free"** נוכחת
- Status: ⬜ not-run (pending implementation)

### TC-DOCS-005 — F13 onboarding simulation — אמת אמפירית + טרמינולוגיה
- Feature: F13 (PRD) · `FINARODA_ONBOARDING_SPEC.md` v1.1 · SPEC §5.5
- Precondition: סימולציית 60 השניות רצה על `episodes`
- Steps: 1) מעבר על המסכים 2) בדיקת קופי ומספרים 3) בדיקת מקור הגרפים
- Expected: כל מספר מגיע מ-`episodes.real_stats_ref` מאומת (אפס סטטיסטיקות מומצאות/הוכחה חברתית מפוברקת); טרמינולוגיה קנונית (Trading Blueprint / PASS-WATCH / "Analysis, not financial advice" על כל מסך); גרפים מרונדרים מ-kline (recharts) — **לא** צילומי TradingView/Bybit; הרשמה ללא כרטיס; אין קנס XP על BUY/SELL
- Status: ⬜ not-run (pending implementation)

### TC-DOCS-006 — F3 reveal-gating (B3)
- Feature: F3 (PRD) · Onboarding §3 מסך 10
- Precondition: setup עם תוצאת backtest שהתבשלה
- Steps: 1) התוצאה מוכנה 2) המשתמש נכנס וסורק שוב 3) בדיקת חשיפה
- Expected: התוצאה נחשפת **רק בסריקה הבאה** דרך teaser שקט "Your journal has an update"; **אין** נוטיפיקציית פוש יזומה (trust-not-engagement, pull-not-push)
- Status: ⬜ not-run (pending implementation)

### TC-DOCS-007 — regime_state / Episode Library schema notes (B2/B4)
- Feature: SPEC §5.2 (regime_state) · §5.5 (episodes)
- Precondition: —
- Steps: 1) קריאת SPEC §5
- Expected: מתועדת תוספת `score_log.regime_state TEXT` (bear/bull/transition, BTC, N=5 hysteresis) לפני צבירת דאטה; מתועדת טבלת `episodes` (kline אמיתי מתוארך, רינדור recharts, לא צילומי מסך)
- Status: ✅ pass (doc check — SPEC §5.2/§5.5 present)

---

## ATR (Acceptance Test Reports)
מיוצרים בהרצה, נשמרים כ-ATR-{date}.md. לא בקובץ זה.

_v0.1 — תבנית. מקרים ספציפיים נוספים לפי הפאזות._
