# FINARODA SaaS — ROADMAP

> מפת דרכים מלאה מהמצב הנוכחי ועד production מלא עם finaroda.com.
> **שני יעדים נפרדים:** (A) **Staging** — live לשחק, יומיים, אתה בלבד. (B) **Production** — לקוחות משלמים.
> עדכן מצב פה כשמשלימים שלב. מקור אמת: PRD/SPEC/UX/LEGAL.

---

## 0. מקרא

- ✅ הושלם · 🔄 בתהליך · ⬜ טרם · 🔴 חוסם production · 🟡 חוסם staging · ⚪ לא-חוסם (ערך)
- **תלות:** מה חייב להיות מוכן לפני שאפשר להתחיל.

---

## 1. מצב נוכחי (הושלם)

| שלב | תיאור | Commit |
|---|---|---|
| ✅ P0 | ניקוי שכבת קריירה, סכמה נקייה, שלד | e58a83d |
| ✅ git infra | .git נוקה, remote, main נקי, dev מסונכרן | — |
| ✅ P1 | auth (magic-link/Google/JWT/beta gate) + Cardcom (TEST) + deploy prep | d43d975 |
| ✅ P1.5 | placeholder מנוע | b011b83 |
| ✅ P2 | ליבת סריקה: SCAN→Bybit client-side→Blueprint (טרמינולוגיה רגולטורית) | — |
| ✅ מנוע | scoring-engine.js (levels) + scorer.js (scoreDirection verbatim v25.80), 12/12 טסטים | fcd145b |
| ✅ רגולציה | טרמינולוגיה (Trigger/Risk Level/Blueprint), עדשה, סגנון סיכון, קו אדום | b9b75b5 |
| 🔄 הטמעת סקורר | חיווט הציון האמיתי + הדלקת סף 85/82 | — |

---

## 2. גרף התלויות (מה חוסם מה)

```
הטמעת סקורר (S1) ──┬──→ P3 למידה (S2) ──────────────┐
                   │                                  │
                   └──→ STAGING DEPLOY (D1) ───────→  אתה משחק (יומיים) ✓
                          │
                          ├── Resend production DNS (I1)
                          └── Railway deploy (I2)

P4 מסחרי (S3) ──┐
Design סבב 2 (X1)├──→ P5 מנהל (S4) ──┐
LEGAL עו"ד (L1) ─┘                    ├──→ PRODUCTION DEPLOY (D2) ──→ לקוחות ✓
Stripe LIVE (C1) ────────────────────┤
דומיין finaroda.com (I3) ────────────┘
```

---

## 3. מסלול A — STAGING (יומיים, לשחק, אתה בלבד)

> מטרה: מערכת חיה בענן שאתה יכול לשחק בה. **לא** דורש עו"ד / Stripe live / כל המסכים.

| ID | שלב | תלות | חוסם | פרטים |
|---|---|---|---|---|
| **S1** | הטמעת הסקורר | מנוע מוכן ✅ | 🟡 | חיווט scoreDirection (momentum) לסריקה, הדלקת SCORE_GATE_ENABLED, סף 85/82, שאר פרופילים ל-score_log (לא מוצג) |
| **I1** | Resend production | — | 🟡 | דומיין שולח מאומת (SPF/DKIM), API key חי. בלי זה — magic-link login לא עובד |
| **I2** | Railway deploy (staging) | S1 | 🟡 | deploy מ-dev/staging, env vars, Litestream→R2, subdomain זמני של Railway |
| **D1** | **STAGING LIVE** | S1+I1+I2 | 🟡 | אתה נכנס דרך subdomain של Railway, סורק, רואה Blueprint אמיתי. **← היעד ליומיים** |

**מה לא צריך ל-staging:** דומיין finaroda.com (subdomain של Railway מספיק), Stripe live (test mode בסדר — פשוט לא תבדוק תשלום אמיתי), עו"ד, מסכי admin/paywall מלאים.

---

## 4. מסלול B — PRODUCTION (לקוחות משלמים)

### 4.1 פיצ'רים

| ID | שלב | תלות | חוסם | פרטים |
|---|---|---|---|---|
| **S2** | P3 — למידה + הגדרות | S1 | ⚪ | cron backtest "מה היה קורה", מגבלת מטבעות/פלאן (2/5/10 מ-system_settings), דאשבורד לקוח |
| **S3** | P4 — מסחרי | S1 | 🔴 | 3 פלאנים חיים **+ Free tier** (D2), paywall (עם "Continue on Free"), **trial 14 יום ללא כרטיס** (D1), קופונים, referral (50%/3-חודשים+אישור). **✅ D1 backend מומש (v0.5.0):** `start_trial` ללא כרטיס/tokenization + `next_billing_at` NULL; `expire_trials`→Free (לא expired); renewal batch מחייב רק `active`; תזכורת יום 11 (`TRIAL_REMINDER_LEAD_DAYS`); migration 022 (`trial_ended_to_free`). לכידת כרטיס = `initiate_checkout` בהמרה בלבד. **⬜ נותר ל-P4:** הפעלת פלאנים חיים + paywall מלא, **אכיפת מגבלות Free** (סריקה 1/יום · F3 7 ימים · ייצוא) מ-`system_settings`, קופונים, referral. |
| **S4** | P5 — מנהל + קהילה | S3, X1 | 🔴 | דאשבורד מנהל (MRR/churn/סיבת עזיבה), טיקטים, ברודקאסט, academy, onboarding survey |

### 4.2 עיצוב

| ID | שלב | תלות | חוסם | פרטים |
|---|---|---|---|---|
| **X1** | סבב Design שני | — | 🔴 | מסכים שלא עוצבו: auth/onboarding, **F13 "First 60 Seconds" onboarding simulation (12 מסכים — `FINARODA_ONBOARDING_SPEC.md` v1.1)**, paywall/פלאנים (Free + 3 בתשלום, "Continue on Free", **טבלת השוואה מוצגת בעמוד ה-Subscribe — E3**), profile+שלבי יוקרה, admin, ייצוא, טיקטים. **חדש (E, 2026-07-11):** תפריט המבורגר אחרי תשלום (Dashboard/Profile/Academy/Settings — **E5**), Concept Tooltip אחיד (**F14/E1**), Live Chart + overlays פר-מטבע (Free=chart+EMA200 / בתשלום=כל השכבות — **F15/E7**), **Horizon selector בשורת הבקרים pre-scan (SWING פעיל / POSITION נעול — F1c/E9)**. (ליבה — scan/blueprint/what-if/empty — כבר עוצבה) |

### 4.3 תשתית הפעלה

| ID | שלב | תלות | חוסם | פרטים |
|---|---|---|---|---|
| **I3** | דומיין finaroda.com | — | 🔴 | רכישה, DNS, SSL, חיבור ל-Railway |
| **C1** | Stripe LIVE | S3 | 🔴 | Stripe live keys + webhook secret, `FEATURE_STRIPE_LIVE=true`, chosen `INVOICE_PROVIDER`, seed live Stripe Prices, webhook production, בדיקת חיוב אמיתי אחת |
| **I4** | Railway production | S3,S4,I3 | 🔴 | deploy מ-main (branch gate!), env vars production, Litestream→R2, scaling |

### 4.4 משפטי + QA

| ID | שלב | תלות | חוסם | פרטים |
|---|---|---|---|---|
| **L1** | אישור עו"ד | LEGAL.md ✅ | 🔴 | עו"ד מאשר/מתקן ToS + דיסקליימר "ניתוח לא ייעוץ" + הסכמת פרטיות. **הסיכון הכי גדול — התחל מוקדם, במקביל** |
| **Q1** | QA + ATP | הכל | 🔴 | הרצת TC-A→TC-J בענן, תיקון באגים, smoke בפרודקשן |
| **D2** | **PRODUCTION LIVE** | כל ה-🔴 | 🔴 | לקוחות נכנסים ל-finaroda.com, משלמים, סורקים |

---

## 5. מה חוסם production — צ'קליסט קריטי (8)

לפני שלקוח אמיתי משלם ב-finaroda.com:

- [ ] **S3** P4 מסחרי (פלאנים/trial/paywall)
- [ ] **X1** מסכים חסרים (Design סבב 2)
- [ ] **C1** Stripe LIVE (live keys + webhook secret + chosen `INVOICE_PROVIDER` + הפעלה)
- [ ] **I1** Resend production (DNS מאומת)
- [ ] **I3** דומיין finaroda.com + SSL
- [ ] **I4** Railway production (deploy מ-main)
- [ ] **L1** אישור עו"ד
- [ ] **Q1** QA + ATP בענן

---

## 6. משימות לא-קוד (אתה, במקביל — לא תלויות בפיתוח)

התחל אותן **עכשיו** כדי שלא יהיו צוואר בקבוק בסוף:

| משימה | למה עכשיו |
|---|---|
| **העבר LEGAL.md לעו"ד** | הסיכון הכי גדול, לוקח זמן, לא תלוי בקוד |
| **רכוש finaroda.com** | מיידי, זול, נחוץ ל-production |
| **אמת דומיין ב-Resend** (DNS) | נחוץ אפילו ל-staging (login) |
| **אמת מחירים מול רו"ח** | 50/100/150 — לפני P4 |
| **Stripe account + live keys** | פתיחת חשבון Stripe + live keys/webhook secret; ובחירת ספק חשבוניות ישראלי (`INVOICE_PROVIDER`: Green Invoice / iCount / EZcount, טרם נבחר) |

---

## 7. סדר מומלץ

**עכשיו → יומיים (staging):**
1. S1 הטמעת סקורר (רץ)
2. I1 Resend DNS (אתה)
3. I2 Railway staging deploy
4. → **D1 STAGING LIVE** — אתה משחק ✓

**במקביל (אתה, לא-קוד):** L1 עו"ד · I3 דומיין · רו"ח

**אחרי staging → production:**
5. X1 Design סבב 2 + S3 P4 מסחרי (במקביל)
6. S4 P5 מנהל
7. C1 Stripe live + I4 Railway production
8. Q1 QA
9. → **D2 PRODUCTION LIVE** ✓

**מה שיישאר אחרון (כדבריך):** עו"ד + Stripe live — שני החוסמים ה"אנושיים", לא הטכניים.

---

## 8. הערכת התקדמות

```
ליבה טכנית:     ~80% ████████████████░░░░
מסחרי (P4):       0% ░░░░░░░░░░░░░░░░░░░░
תשתית הפעלה:    ~30% ██████░░░░░░░░░░░░░░  (test מוכן, live לא)
עיצוב:          ~40% ████████░░░░░░░░░░░░
משפטי:          ~20% ████░░░░░░░░░░░░░░░░
─────────────────────────────────────────
Staging (D1):   קרוב — חסר S1+I1+I2 (יומיים)
Production(D2): חסר 8 חוסמים
```

---

_ROADMAP v1.0. עדכן מצבי ✅/🔄/⬜ כשמשלימים. Staging ≠ Production — אל תבלבל._
