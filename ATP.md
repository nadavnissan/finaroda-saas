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

---

## ATR (Acceptance Test Reports)
מיוצרים בהרצה, נשמרים כ-ATR-{date}.md. לא בקובץ זה.

_v0.1 — תבנית. מקרים ספציפיים נוספים לפי הפאזות._
