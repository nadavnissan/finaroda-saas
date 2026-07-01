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
- **TC-F — Billing & trial** (Cardcom, trial-עם-כרטיס, חיוב יום 15, ביטול)
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
| TC-F-005 | start_trial | trial 14 יום, tier מעודכן, next_billing נקבע | ✅ |
| TC-F-006 | expire_trials | trial שפג → expired/free; מחירי פלאנים seeded | ✅ |

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

> Interim rules documented in code: `engine.ts` (SCORE_GATE_ENABLED=false, interim direction from EMA7 slope sign) and `lens.ts` (interim visibility = levels valid + lens condition). Real 85/82 gate wired behind the flag for pass 2.

---

## ATR (Acceptance Test Reports)
מיוצרים בהרצה, נשמרים כ-ATR-{date}.md. לא בקובץ זה.

_v0.1 — תבנית. מקרים ספציפיים נוספים לפי הפאזות._
