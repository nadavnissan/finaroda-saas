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

## TC — DOCS E (החלטות מוצר 2026-07-11) — spec-level; ⬜ pending implementation

> נובעים מיישום section E של `ALIGNMENT_2026-07-09.md` (E1 Concept Tooltip · E2 free-coin V2 · E3 comparison table on Subscribe · E5 hamburger nav · E6 SCAN vibrate · E7 live chart · E8 ticker banner rejected). מתועדים עכשיו כדי שהמימוש ייבדק מולם.

### TC-J-002 — Subscribe page: Free-vs-paid comparison table (copy-guard, E3)
- Feature: F7 (PRD) · UX §6 · TC-J (Legal/copy guard)
- Precondition: משתמש נכנס לעמוד ה-Subscribe/paywall
- Steps: 1) טעינת עמוד ה-Subscribe 2) בדיקת נוכחות הטבלה 3) בדיקת קופי שורת ה-Free
- Expected: טבלת ההשוואה מוצגת בעמוד עצמו עם כל 4 המסלולים (Free + Basic/Advanced/Pro); שורת ה-Free מתויגת "Free forever" עם התנאים המדויקים (1 scan/day · 2 coins · full Blueprint · journal last 7 days · no export); אין ניסוח שמבטיח רווח/ייעוץ; דיסקליימר "Analysis, not financial advice" נוכח
- Status: ⬜ not-run (pending implementation)

### TC-DOCS-E01 — Concept Tooltip אחיד (E1/F14)
- Feature: F14 (PRD) · UX §3/§8 · F6 (Academy)
- Precondition: מסך כלשהו עם מונח מקצועי (onboarding/scan/Blueprint/dashboard)
- Steps: 1) פתיחת בועת מונח 2) בדיקת מקור התוכן 3) בדיקת שיתוף קומפוננטה בין מסכים
- Expected: קומפוננטה אחת משותפת; תוכן מהאקדמיה (F6), לא כפול/מפוברק; מונח בלי ערך אקדמיה → אין בועה ריקה; display-only — לא נוגע בציון/סף (RED LINE)
- Status: ⬜ not-run (pending implementation)

### TC-DOCS-E02 — Live Chart gating פר-פלאן (E7/F15)
- Feature: F15 (PRD) · UX §3 · SPEC §5.5
- Precondition: מטבע נסרק, משתמש Free מול משתמש בתשלום
- Steps: 1) פתיחת הגרף כ-Free 2) פתיחת הגרף כמשתמש בתשלום
- Expected: Free = גרף + EMA200 בלבד; בתשלום = כל השכבות (EMA7 + רמות Blueprint על הגרף); הגרף מרונדר מ-kline (recharts) — לא צילום TradingView/Bybit; gating נקרא מ-`system_settings`; overlays הצגה בלבד (RED LINE)
- Status: ⬜ not-run (pending implementation)

### TC-DOCS-E03 — SCAN vibrate + silent fallback (E6)
- Feature: SPEC §6.2
- Precondition: לחיצת SCAN בדפדפן תומך ובדפדפן לא-תומך (iOS Safari)
- Steps: 1) לחיצת SCAN בדפדפן עם Vibration API 2) לחיצת SCAN ב-iOS Safari
- Expected: `navigator.vibrate` נקרא כשנתמך; ב-iOS Safari (לא נתמך) — אין רטט, **אין שגיאה**, הסריקה ממשיכה כרגיל
- Status: ⬜ not-run (pending implementation)

### TC-DOCS-E04 — Ticker banner נדחה (E8, doc-check)
- Feature: PRD §17 (REJECTED)
- Precondition: —
- Steps: 1) קריאת PRD §17 "פריטים שנדחו"
- Expected: באנר טיקר רץ מתועד כ-REJECTED (סותר trust-not-engagement + רישוי דאטה); החלופה = שורת marketContext סטטית פר-סריקה; פתיחה מחדש רק כ-opt-in כבוי-כברירת-מחדל
- Status: ✅ pass (doc check — PRD §17 REJECTED present)

### TC-DOCS-E05 — free-coin analysis = V2 בלבד + תווית חובה (E2, doc-check)
- Feature: PRD V2 backlog
- Precondition: —
- Steps: 1) קריאת PRD "V2 (מתועד, לא MVP)"
- Expected: ניתוח מטבע מחוץ ליקום 10 מתועד כ-**V2 בלבד**, בפלאנים בתשלום, אחרי ולידציה+אישור נדב, עם תווית חובה "Learning mode — outside the validated universe". לא v1
- Status: ✅ pass (doc check — PRD V2 present)

### TC-DOCS-E06 — Horizon selector: SWING active / POSITION locked (E9/F1c)
- Feature: F1c (PRD) · UX §3/§8
- Precondition: מסך הסריקה, שורת הבקרים pre-scan
- Steps: 1) בדיקת בקר Horizon 2) בדיקת מצב POSITION + קופי/tooltip 3) בדיקת honesty guardrail 4) בדיקת RED LINE פר-יקום
- Expected: SWING (1–7 days) פעיל ונשלח; POSITION (weeks+) מרונדר **נעול** (לא-אינטראקטיבי) עם "In validation. Unlocks when it earns it." + tooltip מאושר; **honesty guardrail (principle 8):** קופי "in validation" מוצג רק אם קיים מודל POSITION שרושם תוצאות ל-`score_log` — אחרת "planned" ולא "in validation"; אין ETA (POSITION עשוי לעולם לא להיפתח, פתיחה = 30+/2+ משטרים); SWING/POSITION יקומים נפרדים, הבקר לא משנה ציון/סף בתוך יקום (RED LINE)
- Status: ⬜ not-run (pending implementation) · ⚠ open: honesty-guardrail copy decision (AC2) ממתין להכרעת נדב

### TC-DOCS-XP01 — XP economy נעולה: tiers = XP בלבד + xp_events idempotent (`XP_ECONOMY.md` v1.0)
- Feature: UX §5 (Status Tiers) · PRD F5/F6 · SPEC §5.6 · Onboarding §4/§8 · `XP_ECONOMY.md`
- Precondition: מסמכי מקור-אמת אחרי סגירת החוב (docs-only)
- Steps: 1) UX §5 + PRD F5 — קריטריון "מדייק"/Precise 2) PRD F6 — קישור ל-XP_ECONOMY + מודולי בונוס 3) Onboarding §4/§8 — חוב מסומן סגור + קישור 4) SPEC §5.6 — סכמת xp_events
- Expected: (a) שלב "מדייק"/Precise = **סף XP בלבד**, אין קריטריון מבוסס what-if באף מסמך; איכות what-if = סטטיסטיקת דשבורד בלבד. (b) F6 מפנה ל-`XP_ECONOMY.md` ומתאר דרגות פותחות מודולי בונוס אורתוגונלית לפלאן. (c) Onboarding §8 מסומן ✅ נסגר → `XP_ECONOMY.md`; §4 מפנה למקורות הסגורים. (d) SPEC §5.6 `xp_events` עם `UNIQUE (user_id, source, ref)`, כתיבה **צד-שרת בלבד**, מקורות מרשימה סגורה, אין תגמול על רווח/תדירות/רצף.
- Status: ✅ doc-check (docs-only; מימוש xp_events ⬜ pending — P3/P4)

### TC-DOCS-SYNC01 — יישור מסמכי מקור-אמת למצב Package B הממומש (v0.8.x–v0.9.0)
- Feature: PRD F1/F1c/F2/F3/F5–F7/F9–F15 · SPEC §5.9/§6.1/§12 · UX §3/§5/§6/§8 · `journal_scenarios` (mig 028)
- Precondition: PRD/SPEC/UX אחרי DOCS-SYNC (docs-only)
- Steps: 1) PRD F3 — מודל journal_scenarios + CAPITAL SAVES 2) SPEC §5.9 — data model + endpoints + system_settings keys 3) SPEC §6.1 — swing canon 4) סימוני SHIPPED 5) open items 6) stale-claim sweep
- Expected: (a) PRD F3 מתאר `journal_scenarios` (‏`pass`/`no_setups_day`, **WATCH לעולם לא תרחיש**), resolution צד-שרת, status enum, reveal-gating; **CAPITAL SAVES = trigger-never-filled (r=0)** מוגדר, ושורת ה-SAVE הפר-מטבע-לא-עובר מסומנת **הרחבה עתידית ⬜**. (b) SPEC §5.9 כולל DDL של `journal_scenarios` + `ticket_replies`/`notifications_log`/`user_settings`, `admin_events` כ-audit, ו-endpoints `GET /api/scan/entitlements` + `GET /api/plans` + מפתחות `chart_layers_*`/`scan_coins_free`/`scans_per_day_*`. (c) SPEC §6.1: `findRecentSwingLevels` = S/R קנוני equivalence-tested, `computeRangeLevels` **הוסר**. (d) F13/F14/F15/E7b/E9 (+F1/F2/F3/F5–F11) מסומנים ✅ SHIPPED עם version refs; charts=in-app SVG (לא recharts) עקבי ב-3 המסמכים. (e) open items = follow-ups מ-HANDOFF (resolve cron · call-sign · email stubs · fonts). (f) אין הפניית recharts שסותרת את המימוש; "מסך P2" מסומן מוחלף.
- Status: ✅ doc-check (docs-only; אפס שינוי קוד/DB — pytest 66/66 ללא רגרסיה)

## TC — P3 (F13 "First 60 Seconds" onboarding) — automated (backend/tests/test_p3_onboarding.py) + build-verified (frontend)

### TC-P3-ONB-01 — Episode seed + אמת אמפירית (E1 BTC / E3 ADA / E4 ETH)
- Feature: Episode Library (SPEC §5.5/§5.8) · `EPISODES_AND_VERIFIED_NUMBERS.md`
- Steps: 1) build seed מ-Bybit עם assertions 2) `GET /api/onboarding/episodes`
- Expected: 3 אפיזודות (E1 trap, E3 valid_setup, E4 patience) נזרעו מנרות אמיתיים ומתוארכים; ה-builder **נכשל** אם הנרות לא תומכים בכניסה/תוצאה (E1 fade ≥5%, E3 short מגיע ל-target, E4 long מגיע ל-target). E3 חושף score=86.
- Status: ✅ automated (test_episodes_seeded, test_trap_outcome_is_a_real_loss)

### TC-P3-ONB-02 — Server-side outcome withholding (S1 trap / S10 time-machine)
- Feature: withholding AC · SPEC §5.8
- Steps: 1) `GET …/episodes/E4` 2) בדיקת ה-payload 3) `POST …/episodes/E4/reveal`
- Expected: תגובת ה-setup **אינה מכילה** `outcome`, ולא את נרות ה-reveal, ולא את הערכים המוסתרים (+3.33R / 1770 / 10%); `reveal_count>0`. ה-reveal מחזיר את הנרות שהוסתרו + `outcome` (resolved=win, r=3.33, pct=10). **הערך אינו ב-DOM לפני reveal.**
- Status: ✅ automated (test_setup_withholds_outcome_pre_reveal, test_reveal_returns_withheld_outcome)

### TC-P3-ONB-03 — XP idempotency + amounts צד-שרת (סה"כ 300)
- Feature: XP_ECONOMY §1 · SPEC §5.6
- Steps: 1) `POST /xp {ref:s2_scan}` פעמיים 2) ארבעת ה-refs 3) `POST /xp {ref:hack…}`
- Expected: award כפול לא מכפיל (total=50, event יחיד); ארבעת ה-refs = **300**; ref לא-מוכר → 400; ללא cookie → 401; הלקוח לא שולח amount.
- Status: ✅ automated (test_xp_award_idempotent_and_server_priced, test_full_onboarding_xp_totals_300, test_xp_rejects_unknown_ref, test_xp_requires_auth, test_xp_events_unique_constraint)

### TC-P3-ONB-04 — Funnel + completion (Onboarding Spec §5)
- Steps: 1) `POST /funnel` anon (branch_1a_to_s2) 2) `POST /funnel` user (fork_choice) 3) `POST /complete`
- Expected: אירוע anon נרשם ללא auth; אירוע user נרשם עם auth; complete מסמן `onboarding_completed_at` ו-`/me` מחזיר `onboarding_completed=true`.
- Status: ✅ automated (test_funnel_accepts_anon_and_user, test_complete_marks_user_and_logs_completion)

### TC-P3-ONB-05 — זרימת 12 המסכים + ACs חזותיים (frontend)
- Feature: `/onboarding` (S0–S11 + S1a) · UX §7 palette
- Steps: מעבר S0 (auto)→S1 (BUY/SELL)→S1a (erosion)→S1 (SCAN מודגש)→S2 (אנימציה)→S3 (EMA200 lesson)→S4 (+100)→S5 (signup ללא כרטיס)→S6→S7→S8 (PASS+Blueprint)→S9 (call-sign)→S10 (reveal-gated)→S11 (fork+טבלה)
- Expected: תווית "Analysis, not financial advice." על **כל** מסך; גרפים מרונדרים in-app מנרות אמת (SVG, לא צילומים); `navigator.vibrate` על SCAN עם fallback שקט (iOS); Concept Tooltip (קו מקווקו) על מונחים; מד XP בכותרת; S11 מציג טבלת Free-vs-paid (TC-J-002).
- Status: ✅ build/tsc/eslint verified (next build 17/17, /onboarding 7.63kB) · ⬜ manual runtime click-through pending (Design סבב 2 לליטוש חזותי)

## TC — P3 onboarding validation round 1 (fixes + content, 12/07)

### TC-P3-ONB-06 — Concept Tooltip content wiring (46 terms)
- Feature: `concept_tooltips_content.json` (root, locked) · ConceptTooltip · concepts.ts renderer
- Expected: כל 46 המונחים נטענים (term/what/now/academy); עותק ה-frontend זהה למקור (drift-guard); `now` מרונדר עם placeholders מההקשר, placeholder חסר → ריק בחן; Learn more → `/academy#{academy}`. בועה: לא נחתכת במובייל (clamp/flip), כפתור X + סגירה בהקשה בחוץ.
- Status: ✅ automated (test_tooltip_content_loads_46_terms, test_frontend_tooltip_copy_matches_root) · bubble UX build-verified · ⬜ manual mobile check

### TC-P3-ONB-07 — XP once per user ever (anti-farming) [REGRESSION]
- Expected: השלמה מזכה 300 פעם אחת; השלמה חוזרת מזכה 0 (event יחיד); אינדקס `ux_xp_onboarding_once` חוסם שורת onboarding שנייה; pre-signup לא מטבע XP; `/xp` דורש auth.
- Status: ✅ automated (test_onboarding_xp_granted_once_at_completion, test_onboarding_xp_replay_grants_zero, test_xp_partial_unique_blocks_second_onboarding_row, test_xp_onboarding_once_per_user_index, test_xp_requires_auth)

### TC-P3-ONB-08 — No em dashes in product copy (lint)
- Expected: אין U+2014 במחרוזות/JSX ב-frontend/src (הערות מוחרגות). המסמך הנעול נקי גם הוא.
- Status: ✅ automated (test_no_em_dash_in_product_copy)

### TC-P3-ONB-09 — Returning-user routing
- Expected: משתמש מאומת שהשלים אונבורדינג → `/scan` (router.replace); back מהמוצר לא חוזר לאונבורדינג; יציאה מ-S11 = replace ל-`/paywall`(trial)/`/scan`(free).
- Status: ✅ implemented (mount guard on /me + replace navigation) · ⬜ manual click-through

### TC-P3-ONB-10 — LONG/SHORT + שני ענפי S1a (נתוני אמת)
- Expected: כפתורי S1 = LONG/SHORT; ענף LONG = fade (‎−10% ל-57,802); ענף SHORT = squeeze (‎+2.06% ל-65,624 נגד השורט) ואז fade — **שניהם מנרות אמת** (assertion בזמן build של ה-seed). tooltips `long_short`/`fade`/`squeeze`.
- Status: ✅ seed assertion automated (builder throws אם אין squeeze≥1.5% ו-fade≤−5%) · UI build-verified

### TC-P3-ONB-11 — Chart Standard v1 (רכיב בסיס Package B)
- Expected: כותרת הקשר (symbol/price/range/"Daily candles"); EMA200+EMA7 עם תוויות; swing S/R (computeRangeLevels); Blueprint levels (S8); תגי Spike/Entry שפותחים tooltip; הקשה על נר → OHLC (ohlc). מרונדר in-app מנרות אמת.
- Status: ✅ build/tsc/eslint verified · ⬜ manual interaction check

### TC-P3-ONB-12 — Bug fixes (scan-again, signup flash, orphans)
- Expected: "new scan" בתוצאת הסריקה החיה חוזר למסך הבקרים (idle), לא סורק מיד; אין מסך מהבהב בין S5→S6 (מעבר יחיד עם guard); אין יתומי שורה (noOrphan + text-wrap balance).
- Status: ✅ scan-again fixed (setPhase idle) · signup single guarded transition · noOrphan applied · ⬜ manual visual

## TC — P3 onboarding validation round 2 (polish, 13/07) — unit tests: frontend/tests (node --test)

### TC-P3-ONB-13 — S0 LET'S START (no auto-advance)
- Expected: מסך 0 מציג כפתור **LET'S START** (terminal, primary); אין היעלמות מתוזמנת; מעבר ל-S1 רק בלחיצה.
- Status: ✅ implemented (auto-advance effect הוסר) · ⬜ manual

### TC-P3-ONB-14 — Signup transition guard (no flash) [REGRESSION]
- Expected: מעבר S5→S6 יחיד; render-gate פותר routing לפני שהזרימה מרונדרת (redirect מאוחר לא חוטף מסך); `createOnce` מריץ את המעבר פעם אחת.
- Status: ✅ automated unit (createOnce runs once) · render-gate + guard implemented · ⬜ manual click-through

### TC-P3-ONB-15 — Tooltip context suppression + wording
- Expected: `renderNow` מחזיר "" כשחסר placeholder פשוט (long_short לפני בחירה → אין שורת now); עם direction → "This setup's direction is LONG."; conditional נבחר לפי דגל truthy.
- Status: ✅ automated unit (renderNow suppression + conditional)

### TC-P3-ONB-16 — LEVEL framing math (300/1,000) + celebration gating
- Expected: `levelFor(300)` = LVL 01 Strategy Apprentice, 300/1,000 → 02 Risk Manager, progress 30%; ספי 1,000/3,000/8,000; `crossedLevel` true רק בחציית סף (‏0→300 = false); חגיגה נורית רק בחצייה, רטט עדין על צבירה.
- Status: ✅ automated unit (levelFor, crossedLevel) · LevelMeter + LevelUp implemented

### TC-P3-ONB-17 — S8 risk level drawn + Why PASS
- Expected: E3 reveal מחזיר `risk_price=0.1511` + `checks` (regime/weekly/ema7/volume); הגרף מצייר trigger/**risk**/target עם תוויות ללא חפיפה; "Why PASS" מציג שורה לכל check מתוך תוכן ה-concepts.
- Status: ✅ automated backend (test_valid_setup_reveal_has_risk_and_checks) · UI build-verified

### TC-P3-ONB-18 — Header redesign + chart header + S10 copy + S11 table
- Expected: כותרת = מד LEVEL קומפקטי mono (ללא caption אפור נמוך-ניגודיות); כותרת גרף עם סימבול בולט נפרד (כולל S10); קופי S10 חד-משמעי ("revealed on your NEXT scan"); טבלת S11 עם overflow-x מסונכרן למסגרת.
- Status: ✅ build/tsc/eslint verified · ⬜ manual mobile visual

---

## TC — Package B phase 1 (B1 scan + B2 subscribe + B3 nav) — v0.8.0

### TC-B-101 — Scan gating: coin count enforced server-side
- Feature: B1 / E3 · PRD §3.5.5
- Precondition: משתמש Free (2 מטבעות), משתמש Pro (10).
- Steps: 1) POST /api/scan/events עם 3 מטבעות כ-Free. 2) POST עם 10 מטבעות כ-Pro.
- Expected: (1) 403 code=PLAN_COIN_LIMIT, coins_per_scan=2. (2) 200. הלקוח חותך את היקום ל-coins_per_scan.
- Status: ✅ automated (backend test_b1_gating: gating_rejects_over_limit_for_free / allows_more_coins_for_pro; frontend scan.unit: universe slice)

### TC-B-102 — Entitlements endpoint per plan
- Feature: B1
- Steps: GET /api/scan/entitlements כ-Free וכ-Pro.
- Expected: Free = {coins 2, chart_layers ema200_only, scans/day 1}; Pro = {coins 10, chart_layers full, scans/day 0}.
- Status: ✅ automated (test_b1_gating: entitlements_free_defaults / pro_full_layers)

### TC-B-103 — Chart layer gating (E7)
- Feature: B1d/B1e
- Steps: פתח Blueprint כ-Free וכ-paid.
- Expected: Free = גרף + EMA200 בלבד, chips EMA7/LEVELS נעולים + SEE PLANS; paid = כל השכבות (EMA7 + Blueprint levels + swing S/R). ה-Blueprint עצמו מלא בשני המקרים.
- Status: ✅ build/tsc verified (BlueprintChart gating) · ⬜ manual visual

### TC-B-104 — E7b non-passer why-not sourcing
- Feature: B1g · E7b
- Precondition: מטבע שלא עבר (HIDE).
- Steps: הקש על מטבע non-passer בתוצאות.
- Expected: אותו גרף (שכבות לפי פלאן) + שורת "why not" בשפה פשוטה עם Concept Tooltip; הבדיקה החוסמת מזוהה מנתון מאומת (regime = מחיר מול EMA200); אין ציון/משקל/נוסחה בטקסט. header = SNAPSHOT + timestamp (לא live).
- Status: ✅ automated (frontend scan.unit: deriveWhyNot regime/methodology/threshold, no digits leaked) · ⬜ manual visual

### TC-B-105 — First-scan-of-day XP (D3)
- Feature: B1c · XP_ECONOMY §1
- Steps: סרוק פעמיים באותו יום.
- Expected: סריקה 1 → first_scan_of_day=true, xp_awarded=50, chip "+50 XP"; סריקה 2 → false, 0, ללא chip. השרת בעל-הסמכות על הכמות; idempotent per calendar day.
- Status: ✅ automated (test_b1_gating: first_scan_of_day_awards_xp_once)

### TC-B-106 — F1b empty state (no scan CTA)
- Feature: B1f
- Steps: סריקה עם 0 עוברי-סף.
- Expected: ✓ ירוק, "No setups pass right now", "Most days are skip days...", badge משמעת מבוסס נתון-אמיתי (ללא יחס-דילוג מומצא), "Precision, not habit"; אין CTA שמעודד סריקה כפייתית.
- Status: ✅ build verified (Results.EmptyState, no CTA) · ⬜ manual visual

### TC-B-107 — New scan returns to controls (no auto re-scan)
- Feature: B1c AC · F1b
- Steps: לחץ "new scan" מהתוצאות/empty. לחץ back/refresh.
- Expected: חוזר למסך הבקרות (idle), לעולם לא re-scan מיידי; back/refresh לא נכנס לאונבורדינג.
- Status: ✅ build verified (phase→idle) · ⬜ manual

### TC-B-108 — Report a problem files a ticket
- Feature: B3
- Steps: drawer → Report a problem → מלא + שלח.
- Expected: POST /api/support/tickets → 200 {id, status:"open"}; דורש auth (401 בלי).
- Status: ✅ automated (test_b1_gating: support_ticket_filed / requires_auth)

### TC-B-201 — Subscribe comparison table + D1 trial (TC-J-002)
- Feature: B2 / E3 / D1
- Steps: פתח /subscribe.
- Expected: 4 עמודות Free/Basic/Advanced/Pro, Free ראשון ותמיד גלוי; מחירים 0/50/100/150 ומטבעות 2/2/5/10 מ-system_settings; 3 trust shields; CTA "START 14 DAYS OF PRO — NO CREDIT CARD"; "same engine, same threshold"; "Continue on Free". CTA מפעיל trial ללא כרטיס (409 אם כבר נוצל).
- Status: ✅ automated (test_b1_gating: plans_public_comparison_table / trial_start_no_card) · ⬜ manual visual

### TC-B-301 — Nav drawer + header (E5)
- Feature: B3
- Expected: header אחיד (≡/FINARODA/LevelMeter chip) בכל מסכי B; drawer עם Dashboard[UPDATE]/Profile/Academy/Settings + identity LevelMeter + Report a problem נפרד בתחתית; דיסקליימר בכל מסך.
- Status: ✅ build/tsc verified · ⬜ manual visual

### TC-B-401 — Swing S/R equivalence (shared engine = personal tool)
- Feature: shared engine port
- Steps: הרץ shared/scoring-engine.test.js.
- Expected: findRecentSwingLevels המשותף מפיק swings זהים למימוש האישי (engine.mjs) על עשרות סדרות דטרמיניסטיות ופרמטרים; lib/onboarding/levels.ts נמחק; הגרפים משתמשים ב-swingLevels.
- Status: ✅ automated (shared node --test: equivalent to personal-tool engine.mjs)

---

## TC — Package B phase 2 (B4 dashboard + B5 profile + B6 academy + B7 admin) — v0.9.0
> Automated: backend/tests/test_pkg_b_phase2.py (13) + frontend/tests/pkgb2.unit.test.ts (4).

### TC-B4-101 — Scenario creation: PASS → scenario, WATCH never, skip recorded
- Feature: F3 (AC1/AC2)
- Steps: POST /api/scan/events עם coin PASS (passed_threshold=1) → נוצר תרחיש `pass`. POST עם non-passer (0) → אין `pass`, נוצר `no_setups_day`.
- Expected: WATCH/non-passer לעולם לא הופך לתרחיש; יום דילוג נרשם.
- Status: ✅ automated (test_watch_is_never_a_scenario_and_skip_is_recorded)

### TC-B4-102 — Resolution evaluator (pure): win/loss/save/expired/open
- Feature: F3 (resolution)
- Steps: evaluate_outcome עם נרות סינתטיים (short entry100/sl110/tp80).
- Expected: target→win +R · risk→loss -1 · trigger לא נורה בחלון מלא→save 0 · חלון לא-מלא ללא פגיעה→open · trigger ללא target/risk בחלון מלא→expired (R חתום).
- Status: ✅ automated (test_evaluate_outcome_win_loss_save_expired)

### TC-B4-103 — Reveal-withholding regression (S10 pattern)
- Feature: F3 (AC5)
- Precondition: תרחיש PASS נפתר צד-שרת (win 2.60) אך לא נחשף.
- Steps: GET /api/journal.
- Expected: השורה `revealed=false`, **ללא status/r_result/resolved_at**; הערך 2.60 ו-"win" **לא מופיעים בכל ה-payload**; awaiting_reveal=1; cumulative_r=0; badge=1.
- Status: ✅ automated (test_journal_withholds_outcome_until_reveal + frontend scenarioOutcome=null)

### TC-B4-104 — Reveal on next scan
- Feature: F3 (AC5)
- Steps: אחרי פתרון-לא-חשוף, POST /api/scan/events (סריקה חדשה) → GET /api/journal.
- Expected: התרחיש כעת `revealed=true` עם status=win, r_result=2.60; cumulative_r=2.60; badge=0.
- Status: ✅ automated (test_next_scan_reveals_outcome)

### TC-B4-105 — +25 XP on viewing a revealed outcome (idempotent)
- Feature: F3 / XP_ECONOMY §1
- Steps: POST view על תרחיש חשוף פעמיים; ניסיון view על לא-חשוף.
- Expected: ראשון +25, שני 0 (idempotent per scenario); view על לא-חשוף → 409.
- Status: ✅ automated (test_journal_view_awards_25_xp_once, test_cannot_view_unrevealed_scenario)

### TC-I-101 — Profile: call-sign fallback + settings persist (F5)
- Steps: GET /api/profile; PUT /api/profile/settings.
- Expected: call-sign נגזר מ-email (NIGHTHAWK) כשלא הוגדר; risk_style/call-sign נשמרים.
- Status: ✅ automated (test_profile_call_sign_fallback_and_settings_persist)

### TC-B6-101 — Academy: 12 modules + lesson XP + stub awards nothing (F6)
- Steps: GET /api/academy; complete regime_ema200 פעמיים; complete volume_basics (stub).
- Expected: 12 מודולים; שיעור-אמת +100 חד-פעמי (replay=0); stub=0 XP, completed=false.
- Status: ✅ automated (test_academy_twelve_modules_and_lesson_xp)

### TC-B6-102 — Academy plan gating (full module locked for Free)
- Steps: Free user → complete smart_skip ('full').
- Expected: 403.
- Status: ✅ automated (test_academy_full_module_locked_for_free)

### TC-H-201 — Admin routes 403 for non-admins
- Feature: F (admin gate)
- Steps: משתמש רגיל → GET כל route תחת /api/admin/*.
- Expected: 403 בכולם.
- Status: ✅ automated (test_admin_routes_403_for_non_admin)

### TC-H-202 — Admin overview (real data) + user override with audit
- Steps: admin GET /api/admin/overview; POST override plan_override.
- Expected: overview sample=false + mrr_ils; override מחיל tier=pro + שורת admin_events.
- Status: ✅ automated (test_admin_overview_and_override)

### TC-H-203 — Settings editor guards non-editable (RED LINE)
- Steps: PUT /api/admin/settings על מפתח editable ועל score_gate.
- Expected: editable→200; score_gate→400 (נעול).
- Status: ✅ automated (test_admin_settings_edit_rejects_non_editable)

### TC-H-204 — Broadcast compose → in-app banner
- Steps: admin POST /api/admin/broadcasts (audience all, in-app) → GET /api/broadcasts/active.
- Expected: banner מוחזר עם הכותרת; נשמר; email=stub לוגי.
- Status: ✅ automated (test_broadcast_create_and_active_banner)

## FIX-R3R4 (validations 3+4) — v0.10.0

### TC-A-101 — 3-plan public table (Decision A)
- Steps: GET /api/plans.
- Expected: tiers = {free, basic, pro} בלבד (Advanced הוסר); prices 0/59/149; coins 2/5/10; free chart_layers=ema200_only, basic/pro=full.
- Status: ✅ automated (test_plans_public_comparison_table)

### TC-A-102 — Daily scan cap enforced (Bug 3)
- Entry: משתמש Free (scans_per_day=1).
- Steps: POST /api/scan/events פעמיים באותו יום; ואז משתמש pro חוזר 3 פעמים.
- Expected: Free — סריקה 1 = 200, סריקה 2 = 429 (`DAILY_SCAN_LIMIT`, scans_per_day=1); pro — כל 3 = 200 (unlimited).
- Status: ✅ automated (test_daily_scan_cap_free_blocks_second, test_daily_scan_cap_unlimited_for_paid)

### TC-A-103 — Trial activation → Free on expiry (Bug 4)
- Steps: POST /api/cardcom/trial → trial(pro); דחיפת trial_ends_at לעבר; expire_trials.
- Expected: moved_to_free≥1; status → tier=free, subscription_status=none (לא חויב, לא נחסם).
- Status: ✅ automated (test_trial_expires_to_free); day-11 → notifications_log idempotent (בדיקת cron ידנית).

### TC-A-104 — Recent scans history (Decision B)
- Steps: POST /api/scan/events; GET /api/scan/history; GET /api/scan/history/{id}; משתמש אחר מנסה את אותו id.
- Expected: history מחזיר את הסריקה (time/coins/passes); detail מחזיר את שורות ה-momentum השמורות; משתמש אחר → 404 (owner-scoped).
- Status: ✅ automated (test_scan_history_lists_and_stores, test_scan_history_owner_scoped)

### TC-A-105 — Onboarding flash + XP@S9 (Bugs 1+2)
- Steps (ידני, incognito): לרוץ S0→S11; לצפות ב-S8/S10 שאין מסך ביניים בין SCAN ל-reveal; לצאת ב-S11; לבדוק ש-XP=300 נחת גם אם יוצאים מיד אחרי S9.
- Expected: אין flash ב-S8/S10; XP 300 נחת ב-S9 (call-sign submit) ולא תלוי ב-S11; call-sign מופיע בפרופיל+greeting.
- Status: ⬜ manual (S5→S6 flash — אימות דפדפן; reveal-gap = תוקן בקוד).

### TC-A-106 — Coin selection within plan (Decision C)
- Steps: במסך idle לבחור מטבעות; לוודא cap לפי coins_per_scan; לסרוק.
- Expected: הבחירה נשמרת (localStorage) והסריקה רצה על המטבעות שנבחרו בלבד; מעבר ל-cap מחליף את הפריט הישן.
- Status: ⬜ manual.

### TC-A-107 — Paid why-not enrichment + defaults + copy (Decisions D+E, Bugs 7+8)
- Steps: coin לא-עובר בתשלום → "THE ACTUAL NUMBERS" (price vs EMA200 %, EMA7 slope, volume); Free → הפניה לתשלום. Lens/Style מסמנים default. כפתור SCAN = "N COINS". S1 כותרת 2 שורות.
- Expected: כמתואר; ללא weights/formulas.
- Status: ⬜ manual.

### TC-A-108 — Login DEV SIGN-IN + admin back + Profile≠Settings (Bugs 9,10,11)
- Steps: login עם DEV_RETURN_MAGIC_LINK → כפתור DEV SIGN-IN מופיע ומחבר; admin → "Back to app"→/scan; /profile מול /settings תוכן שונה.
- Expected: כמתואר.
- Status: ⬜ manual.

### TC-RESP-01 — Responsive pass · no horizontal overflow 360–430px (RESPONSIVE PASS v0.10.1)
- Feature: UX (mobile-first product screens; admin usable on phone)
- Precondition: dev build, DevTools device toolbar (or a real phone).
- Steps (ידני, לכל route): onboarding S0–S11, scan (controls/results/Blueprint/charts), subscribe, dashboard, profile, settings, academy (list+module), history, login — ולכל מסך אדמין (overview/users/tickets/broadcast/settings/notifications) — לרנדר ב-**390px** וב-**1280px**; לגלול כל מסך.
- Expected: אין גלילה אופקית של העמוד באף מסך ב-360–430px; אין טבלה/מסגרת חתוכה; טבלאות רחבות (S11 comparison, admin notifications, admin tab strip) גוללות אופקית ולא נחתכות; ה-Rail של האדמין הופך לפס טאבים עליון + master/detail מתחלף (users/tickets); charts מתאימים לרוחב; targets ≥44px. ב-≥1024px: מסכי מוצר ממורכזים בעמודת max-width, האדמין רוחב-מלא לפי מסגרות B7.
- Status: ⬜ manual (Nadav phone validation)

### TC-RESP-02 — Structural-lint viewport guard (אוטומטי · frontend/tests/viewport.regression.test.ts)
- Feature: רגרסיה — מונע חזרה של דפוסי overflow.
- Precondition: אין.
- Steps: `cd frontend && node --test --experimental-strip-types "tests/**/*.test.ts"`.
- Expected: 6 בדיקות ה-viewport עוברות — אין fixed width ≥360 ללא maxWidth/vw/mobile; כל route מוצר עם maxWidth; admin עם useIsMobile; טבלאות רחבות ב-overflowX scroller; chart width=100%+viewBox; globals.css עם overflow-x hidden + main padding clamp.
- Status: ✅ pass (24/24 frontend unit)

### TC-RESP-03 — Free journal reveal caption (copy)
- Feature: F3 (journal reveal) — daily-limit implication.
- Precondition: משתמש Free מול משתמש בתשלום/trial, dashboard.
- Steps: לפתוח /dashboard כ-Free ואז כ-paid; לקרוא את שורת ה-caption התחתונה.
- Expected: Free → "Revealed on tomorrow's scan, never by push."; paid/trial → "Revealed on your next scan, never by push."
- Status: ⬜ manual.

### TC-N5 — Stage 5: Notifications + Bell + Preferences + Real Resend (v0.11.0)
> חבילת בדיקות אוטומטית: `backend/tests/test_stage5_notifications.py` (pytest) + `frontend/tests/notifications.unit.test.ts` (node --test). כל האימיילים רצים ב-DEV mode → אפס קריאות רשת ל-Resend (AC8).

- **TC-N5-01 — feed + read-marking (AC1):** יוצר notification → `GET /api/notifications` מראה unread_count=1 + read_at=null → `POST /api/notifications/read {ids}` → unread_count=0 → refresh שומר על המצב (server-authoritative). ✅ auto.
- **TC-N5-02 — mark-all (ids מושמט):** 3 notifications → `POST /read {}` → unread_count=0. ✅ auto.
- **TC-N5-03 — prefs CRUD (AC2):** defaults כולם true → `PUT /prefs {sound_enabled:false}` → sound=false, שאר לא נגעו → refetch עקבי. ✅ auto.
- **TC-N5-04 — inapp gate (AC3):** `inapp_enabled=false` → `create_notification` מחזיר None, feed ריק. ✅ auto.
- **TC-N5-05 — day-11 boundary (AC4):** משתמשי trial ב-day 10/11/12 → `trial_ending_soon_task` יורה **רק** ל-day 11 (3 ימים לפני הסוף, חלון half-open). ✅ auto.
- **TC-N5-06 — cron idempotency (AC4):** ריצה ראשונה notified=1, שנייה notified=0; בדיוק שורת פעמון trial_reminder אחת. ✅ auto.
- **TC-N5-07 — email_product opt-out:** trial user שביטל product email → notified=1 (in-app + audit עדיין), אך ללא מייל. ✅ auto.
- **TC-N5-08 — reveal-teaser no-outcome (AC5):** `render_reveal_teaser` — ה-copy נטול win/loss/profit/gain/target/%/$ ומכיל את הטקסט הקבוע "a journal reveal is waiting / run your next scan to unlock it". ✅ auto.
- **TC-N5-09 — reveal-teaser sweep dedup (AC5):** תרחיש resolved-unrevealed → sweep יוצר teaser אחד + `teaser_sent_at` מסומן; sweep שני = אפס למשתמש; body content-free. ✅ auto.
- **TC-N5-10 — broadcast 403 (AC6):** משתמש לא-אדמין → `POST /api/admin/broadcasts` = 403. ✅ auto.
- **TC-N5-11 — broadcast filtering + preview (AC6):** משתמש שביטל email_broadcast מוחרג מ-`_broadcast_recipients(email_only=True)`; `preview.email_optin` יורד ב-1 אחרי opt-out בעוד `recipients` לא משתנה; `delivered_email` = email_optin; opted-out עדיין מקבל שורת פעמון (channel_in_app). ✅ auto.
- **TC-N5-12 — unsubscribe token (AC7):** טוקן מזויף → 400; תקין → 200 + הדגל כבוי (ללא login); חזרה → 200 idempotent, נשאר כבוי. ✅ auto.
- **TC-N5-13 — cron auth (D-N9):** ללא/עם secret שגוי → 403; secret נכון → 200 עם trial_reminder + reveal_teaser. ✅ auto.
- **TC-N5-14 — em-dash lint (D-N10):** `render_trial_reminder` ללא em-dash; "no automatic charge" בקופי. ✅ auto.
- **TC-N5-15 — unit: bell/prefs/vibration:** `formatBadge` (ריק ב-0, "9+" מעל 9), `togglePref` immutable, `vibrateSafe` יורה כשיש vibrate ו-no-op כשאין (iOS), gating של shouldVibrate/shouldPlaySound על inapp_enabled, `unreadIds`. ✅ auto (6 בדיקות).
- **TC-N5-16 — manual (browser):** לפתוח פעמון בטלפון + desktop, לוודא badge/mark-read; 5 ה-toggles ב-Settings; admin broadcast preview+confirm; לחיצת unsubscribe מדף המייל. ⬜ manual (Nadav).

### TC-A7 — Stage 7: Admin v1.1 + Sentry + Ticket Breadcrumbs (v0.12.0)
> אוטומטי: `backend/tests/test_stage7_admin.py` + `frontend/tests/admin.unit.test.ts`. Sentry מנוטרל בבדיקות (אין DSN) → אפס רשת.

- **TC-A7-01 — filters AND (AC2):** plan/status/min_scans מסננים צד-שרת; שילוב = חיתוך (pro AND min_scans>=6 מחריג משתמש pro עם 0 סריקות). ✅ auto.
- **TC-A7-02 — columns + rank (AC1):** שורת משתמש מכילה signup/last_active/xp/rank/scans/active-days/referrals(=0)/churn; rank מ-`core/ranks.py` (0→L1, 1000→L2, 3000→L3, 8000→L4). ✅ auto.
- **TC-A7-03 — active-days boundary (D-A1/AC4):** סריקות בימים 0/-3/-6/-7/-10 → active_days_7d=3, active_days_30d=5. ✅ auto.
- **TC-A7-04 — active-days לא user-facing (AC4):** `GET /api/profile` payload ללא "active_days". ✅ auto.
- **TC-A7-05 — CSV auth + content (AC3):** non-admin→403; admin→200 text/csv + Content-Disposition attachment; קבוצת המיילים ב-CSV == ה-view המסונן ב-JSON. ✅ auto.
- **TC-A7-06 — churn CRUD + admin (AC5):** `POST /api/churn/survey`→200; מופיע ב-`/api/admin/churn`; flag churn_survey=true בטבלה; סינון status=churned כולל; ללא auth→401. ✅ auto.
- **TC-A7-07 — Sentry disabled zero-network (AC6):** בבדיקה `sentry_enabled()`=False, `init_sentry()`=False (אפס init/רשת). ✅ auto.
- **TC-A7-08 — Sentry PII scrub (AC6):** `scrub_event` משאיר user.id בלבד, מסיר email/ip/username + cookies + Cookie/Authorization headers. ✅ auto.
- **TC-A7-09 — breadcrumb red-line (AC7/S2):** `sanitize_breadcrumbs` מסיר r_result/status/coin/nested (allowlist); שומר event_type/path/route/code. ✅ auto.
- **TC-A7-10 — breadcrumb cap:** 50 → 20. ✅ auto.
- **TC-A7-11 — ticket breadcrumbs stored+rendered (AC7):** יצירת טיקט עם breadcrumb זדוני (r_result/status) → admin ticket_detail מחזיר breadcrumbs נקיים (ללא r_result/status/loss). ✅ auto.
- **TC-A7-12 — admin endpoints 403:** non-admin על tickets/churn/export.csv → 403. ✅ auto.
- **TC-A7-13 — unit (frontend):** filters↔URL round-trip; `userRow` עמודות v1.1; ring buffer overflow ב-20; `shouldInitSentry` gating (DSN + non-test). ✅ auto (7 בדיקות).
- **TC-A7-14 — manual (browser):** אדמין ב-390px+1280px: פילטרים משנים URL + נשמרים ב-refresh; טבלה רחבה גוללת אופקית; EXPORT CSV מוריד; טיקט מציג breadcrumbs timeline; Settings "Cancel plan or leave" שולח survey. ⬜ manual (Nadav).

### TC-AC6 — Stage 6: Academy 2.0 (v0.13.0)
> מנוע: `academy_lessons` (mig 033, DB-backed) מחליף את רשימת `_MODULES` הקשיחה של B6. השלמה/XP נשארים ב-`xp_events` (source=`academy_lesson`, ref=`slug`), ללא נגיעה — S3 בטוח.
- **TC-AC6-01 — seed = 12 lessons + backward-compat (AC7/AC8):** `GET /api/academy` מחזיר בדיוק 12 שיעורים; כל שורה נושאת גם aliases ישנים (`id`==`slug`, `minutes`==`duration_minutes`) וגם שדות 2.0 (content_type/description/tags/min_plan/min_rank). ✅ auto.
- **TC-AC6-02 — migration preserves completion by slug (AC7/S3):** רשומת השלמה שנכתבה תחת ה-module id הישן (==slug) עדיין נקראת `completed=true`; replay של complete מעניק 0 (idempotent, אין XP כפול). ✅ auto.
- **TC-AC6-03 — dual-gate matrix (AC4/D-AC1):** free-plan/no-rank → פתוח ל-free; basic-plan lesson → נעול ל-free עם `lock_reason`="Available on Basic plan"; bonus (min_rank 1000) → נעול עם "Unlocks at Risk Manager"; שדרוג ל-basic פותח את שער הפלאן אך לא את שער הדרגה; מענק 1000 XP פותח את הדרגה (STATUS-based, לא הוצאה). ✅ auto.
- **TC-AC6-04 — trial = full library (AC4):** `subscription_status='trial'` → שיעורי plan-full פתוחים (גישת Pro). ✅ auto.
- **TC-AC6-05 — server-authoritative gated content (AC4/D-AC7):** `GET /api/academy/{slug}` על שיעור פתוח → 200 עם body; על שיעור נעול → **403** ו-`body`/`video_url` אינם ב-payload. ✅ auto.
- **TC-AC6-06 — completion XP uniqueness (AC5):** complete ראשון → +100/`completed=true`; שני → +0. ✅ auto.
- **TC-AC6-07 — seed stub awards nothing (AC5):** `volume_basics` (`awards_xp=0`) → `{xp_awarded:0, completed:false}` (זהות התנהגותית ל-stub של B6). ✅ auto.
- **TC-AC6-08 — admin auth on every mutation (AC6):** non-admin על list/create/update/archive/restore/reorder של `/api/admin/academy/*` → 403. ✅ auto.
- **TC-AC6-09 — admin video create + invalid URL (AC3):** YouTube watch-URL → 200 + `video_url` מנורמל ל-`youtube.com/embed/{id}`; URL לא-YouTube/Vimeo → 400 `INVALID_VIDEO_URL`. ✅ auto.
- **TC-AC6-10 — archive hides from users + restore (AC6/D-AC6):** יצירה→נראה למשתמש; archive→נעלם מספריית המשתמש אך נשאר באדמין עם `archived=true`; restore→חוזר. ✅ auto.
- **TC-AC6-11 — archive never revokes XP (D-AC6):** משתמש משלים שיעור (+100), אדמין מארכב → שורת `xp_events` שורדת (XP לא נשלל). ✅ auto.
- **TC-AC6-12 — admin reorder (D-AC5):** POST reorder עם רשימת ids הפוכה → sort_index נכתב לפי מיקום; החזרה מסודרת בהתאם. ✅ auto.
- **TC-AC6-13 — unit (frontend):** `filterLessons` שילובי type×state×search (AND); `lessonState` locked/completed/open; `videoEmbed` YouTube poster / Vimeo / unknown. ✅ auto (8 בדיקות).
- **TC-AC6-14 — manual (browser):** Academy ב-390px+1280px: כרטיסים ב-grid (טור אחד בטלפון, מרובה במסך רחב), חיפוש+פילטרים מיידיים, נגן וידאו נטען בלחיצה (lazy), שיעור נעול מציג סיבה בשפה פשוטה, admin create/edit/reorder/archive. ⬜ manual (Nadav).

---

## ATR (Acceptance Test Reports)
מיוצרים בהרצה, נשמרים כ-ATR-{date}.md. לא בקובץ זה.

_v0.1 — תבנית. מקרים ספציפיים נוספים לפי הפאזות._
