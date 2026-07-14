# FINARODA SaaS — UX / חוויית משתמש (v1.2)

> מסמך אפיון חוויה, מלווה ל-`FINARODA_SAAS_SPEC.md`. מיועד לכניסה ל-**Claude Design** לאישור מסע לקוח, עיצוב וכפתורים.
> עיקרון-על: **trust-not-engagement** — מתגמלים דיוק ודילוג, לא תדירות. כל מסך מתויג "ניתוח, לא ייעוץ".
> שפה: **אנגלית מלאה** (קהל V1 ישראלי, אבל UI אנגלי לקראת התרחבות גלובלית).
> **v1.2 — Regulatory reframing (front-end only; engine unchanged).** Calculator terminology, the **Trading Blueprint** (was decision card), an **Analysis Lens** (display-only) and a **Risk Style** choice. Canonical terminology + RED LINE live in PRD §3.5.

---

## 1. עקרונות חוויה (לא מתפשרים)

1. **שליטה ובחירה.** אנשים אוהבים לבחור — 3 פלאנים, לא אחד. הגדרות, ייצוא, פרופיל בשליטת הלקוח.
2. **דאטה ומספרים — אבל ללא חשיפת המערכת.** אנשים אוהבים מספרים; ניתן לייצא תוצאות סריקה (לא את הלוגיקה/המשקלים).
3. **מחסור מכובד.** "כלום לא עובר היום" הוא מסך לגיטימי וחיובי, לא כישלון. מעצבים אותו כהישג של משמעת.
4. **יוקרה מבוססת משמעת.** מעמד/שלבים מתגמלים דבקות בסף ודילוג חכם — **לא** מספר סריקות/כניסות.
5. **מינימליזם פעולתי.** כפתור אחד, מסך אחד, החלטה ברורה. בלי עומס.

---

## 2. מסע הלקוח (Customer Journey)

| שלב | מסך | מטרה |
|---|---|---|
| 1. נחיתה | `coming-soon` / landing | הסבר ערך + הרשמה/waitlist |
| 2. הרשמה | magic-link / Google | כניסה ללא חיכוך |
| 3. שאלון onboarding | survey (עריך) | היכרות + התאמה ראשונית |
| 4. trial | 14 יום **ללא כרטיס** | התנסות מלאה; בסוף בחירה אקטיבית (פלאן בתשלום או Free) |
| 5. סריקה ראשונה | מסך הסריקה | רגע ה-"אהה" — הכפתור והעיגולים |
| 6. Trading Blueprint | trading blueprint (was decision card) | הערך המרכזי — דיוק תזמון |
| 7. דאשבורד | "מה היה קורה" | הוכחת ערך מצטברת |
| 8. שדרוג | paywall | המרה לתשלום |
| 9. נאמנות | profile + שלבי יוקרה | שייכות ומעמד |

---

## 3. מסך הסריקה — הלב

> **✅ מומש v0.8.0 (Package B B1):** מסך הסריקה המלא — שורת בקרים pre-scan (Horizon SWING/POSITION-locked · Lens display-only · Risk Style geometry-only), אנימציית 4-צעדים נעולה, תוצאות ring/list, Chart Standard v1 עם E7 layer gating, E7b why-not לכל מטבע, first-scan XP chip, empty-state F1b. הניווט (header אחיד + hamburger drawer) והיומן (F3/B4) מומשו ב-v0.8.0/v0.9.0.

### זרימה
Pre-scan the user sets a light, remembered controls row: **Horizon** (SWING 1–7 days = active · POSITION weeks+ = **locked**, "In validation. Unlocks when it earns it." — PRD F1c), **Analysis Lens** (EMA200/RSI/Volume/Full — display only, **Full = recommended default**) and **Risk Style** (Conservative/Balanced/Aggressive — output geometry only, **Balanced = recommended default**). The controls mark the recommended defaults (Decision E, v0.10.0 shipped 2026-07-13). **Coin selection (Decision C, v0.10.0):** the user also picks WHICH coins to scan, within the plan's coin count (all plans), a remembered pre-scan control. None of these changes the score or which coins pass within the active horizon (RED LINE, PRD §3.5.5). Then: כפתור עגול גדול במרכז → לחיצה → **אנימציית סריקה במילים** (Downloading tickers… / Analyzing candles… / Computing volume… / Scoring…) → **טבעת עיגולים** מסביב לכפתור, כל עיגול = מטבע שעבר סף → לחיצה על עיגול → **Trading Blueprint**.

### כללי עיצוב
- **פריסה (נעול):** ring עד 5 מטבעות, list מעבר ל-5.
- **אנימציית סריקה (נעול):** log — סטרימינג טרמינל של 4 שלבים (Downloading tickers / Analyzing candles / Computing volume / Scoring setups).
- **סף ציון (נעול):** **85+ = PASS** (ירוק, בטבעת) · **82-84 = WATCH** (אמבר, מעקב בלבד, לא נספר כפוזיציה מאושרת) · **<82 לא מוצג**. הסף נשלט מהאדמין, מועמד לכיול אחרי 30+ תוצאות.
- רוב הימים 0-2 עוברים. מסך "No setups pass — disciplined" כשאין.
- **דיוק תזמון ללא הגבלה:** אפשר ללחוץ שוב לבדוק שוב (השוק זז). זה לא "tap כפייתי" — זה דיוק תזמון על הזדמנות שכבר עברה סף. הציון/הסף שומר על המחסור.
- **אנימציה מספקת אך לא ממכרת** — מסמנת שעבודה אמיתית קרתה (משיכה client-side אמיתית מ-Bybit), בלי מכאניקת מזל.

### Trading Blueprint (was "decision card")
- **רובד עליון (החלטה):** כיוון + ציון + ירוק/כתום/אדום.
- **תזמון מאומת:** שיפוע EMA7, מרחק Calculated Risk Level.
- **Calculated levels (each with a "how computed" note — PRD §3.5.2):**
  - **Mathematical Trigger Point** (was Entry)
  - **Calculated Risk Level** (was SL)
  - **Dynamic Risk Level** (was Trailing)
  - **Calculated Target Level** (was TP)  + R:R.
- **Analysis Lens** decides which extra panel is shown (e.g. RSI reading) — display only; the levels/score are identical across lenses.
- **Risk Style** shifts the calculated levels via `computeSlTp` `opt` — the score is unchanged.
- **מודיעין מתקפל:** volume (נאסף).
- **Concept Tooltip ("What's this?", PRD F14):** כל מונח מקצועי בכרטיס (EMA7 slope, PASS/WATCH, Mathematical Trigger Point וכו') נושא בועת-לימוד אחידה — תמצית בשפה פשוטה מהאקדמיה + קישור לשיעור. חינוכי בלבד, לא נוגע בציון/סף. מהאונבורדינג ואילך על כל surface.
- **Live Chart + Explanation Overlays (PRD F15) — ✅ מומש v0.8.0 כ-Chart Standard v1:** גרף לכל מטבע נסרק (מרונדר מ-kline **in-app כ-SVG** — לא recharts, לא צילום TradingView/Bybit), עם שכבות הסבר. **Gating (נשלט-אדמין):** Free = גרף + EMA200 · בתשלום = כל השכבות (EMA7, רמות ה-Blueprint על הגרף). **E7b:** כל מטבע נסרק (כולל non-passers) לחיץ → אותו גרף + שורת "why not". **Decision D (v0.10.0 shipped 2026-07-13), paid "why not" enrichment:** בפלאנים בתשלום, הקשה על מטבע שלא עבר חושפת את **המספרים בפועל** מאחורי ה-check החוסם (למשל price מול EMA200 ב-%, שיפוע EMA7, יחס volume); Free רואה את ה-why-not הפשוט בלבד. **אין משקלים/נוסחאות.** השכבות הצגה בלבד — לא משנות ציון (RED LINE).
- **תיוג קבוע:** "Analysis, not financial advice."
- **(V2)** כפתור "Copy to LLM" — בלוק טקסט מובנה לחיזוק שיקול דעת חיצוני.

---

## 4. ייצוא תוצאות (פיצ'ר שביקש נדב)

הלקוח אוהב דאטה — נותנים לו לייצא **תוצאות**, בלי לחשוף את **המערכת**:
- **כן לייצא:** טבלת מטבעות שעברו + ציון + כיוון + רמות (Entry/SL/TP) + timestamp. פורמט CSV/PNG.
- **לא לחשוף:** המשקלים, הנוסחאות, סף-ההחלטה, לוגיקת הציון. ה"מתכון" נשאר קנייני.
- שימוש: הלקוח יכול לשמור/לשתף/לנתח בעצמו — תחושת בעלות על הדאטה בלי דליפת ה-IP.

---

## 5. פרופיל ושלבי יוקרה

> **✅ מומש v0.9.0 (Package B B5):** `/api/profile` — call-sign, כרטיס דרגה + סולם (‏`XP_ECONOMY.md` 1000/3000/8000), "HOW XP IS EARNED", הגדרות Lens/Risk Style נשמרות (display+geometry בלבד), sign-out.
> **✅ v0.10.0 (shipped 2026-07-13):** ה-call-sign שנבחר באונבורדינג S9 **מתמיד** לפרופיל ומשמש בברכות (fallback ל-email כשאין call-sign). **Profile ו-Settings הם מסכים נפרדים:** Profile = זהות (call-sign/דרגה/ותק); Settings = הגדרות הסריקה הנזכרות (Lens/Risk Style/מטבעות מועדפים).

### פרופיל
שם, תוכנית, ותק במערכת, הגדרות (**Analysis Lens** display-only, **Risk Style** output-only, מטבעות מועדפים בגבולות הפלאן — **אין סף-ציון אישי**, RED LINE PRD §3.5.5), היסטוריית סריקות, מדדי משמעת. Lens + Risk Style are remembered per user.

### שלבי יוקרה (Status Tiers) — מבוססי משמעת
מעמד שמעניק שייכות, **מתוגמל על התנהגות נכונה ולא על תדירות**:

| שלב | קריטריון (משמעת, לא תדירות) | תחושה |
|---|---|---|
| מתחיל | הרשמה + onboarding | "ברוך הבא" |
| ממושמע | X ימים של דבקות בסף (כולל ימי דילוג) | "אתה סומך על המערכת" |
| מדייק | צבירת XP על משמעת ולמידה (סף דרגה — `XP_ECONOMY.md`) | "התזמון שלך משתפר" |
| ותיק | ותק + התמדה | מעמד בקהילה |

> **אזהרת עיצוב קריטית:** אסור ש"מעמד" יינתן על מספר סריקות/כניסות — זה שובר את trust-not-engagement והופך את המוצר למכונת אקשן. המעמד מתגמל **דילוג חכם ודבקות בסף**.
>
> **תיקון (מקור: `XP_ECONOMY.md` §4, נעול 11/07/2026):** שלבי היוקרה נקבעים לפי **XP בלבד** (משמעת + למידה) — לעולם **לא** לפי תוצאות what-if. הקריטריון הקודם של "מדייק" ("היסטוריית מה-היה-קורה חיובית") היה תגמול על תוצאות וסתר את trust-not-engagement — הוסר. **איכות ה-"מה היה קורה" נשארת סטטיסטיקת דשבורד בלבד, לעולם לא קריטריון שלב.** סולם הדרגות המלא, ספי ה-XP, ומקורות ה-XP הסגורים: `XP_ECONOMY.md`.

---

## 6. פלאנים — מסך תמחור (3, לא 1)

> **Decision A (נדב 2026-07-13, v0.10.0):** Advanced הוסר; הקטלוג הוא Free/Basic/Pro. Basic ירש את רוחב ה-Advanced (5 מטבעות, ייצוא, academy מלא, יומן מלא). המחירים ₪59/₪149 מסומנים **PENDING-ACCOUNTANT**.

| | Free 0₪ | בסיס 59₪ (PENDING-ACCOUNTANT) | פרו 149₪ (PENDING-ACCOUNTANT) |
|---|---|---|---|
| מטבעות בסריקה | 2 (סריקה 1/יום) | 5 | 10 |
| Trading Blueprint מלא | ✓ | ✓ | ✓ |
| דאשבורד "מה היה קורה" | 7 ימים אחרונים | ✓ | ✓ |
| ייצוא תוצאות | — | ✓ | ✓ |
| Academy (טקסט/וידאו) | בסיסי | מלא | מלא |
| (V2) Copy-to-LLM | — | — | ✓ |

> **Academy 2.0 (Stage 6, v0.13.0):** ספריית האקדמיה עברה מרשימה ל-**card grid** רספונסיבי (טור אחד ב-390px, מרובה-טורים ב-1280px). כל כרטיס: כותרת, תיאור קצר, משך, תג-סוג (טקסט/וידאו), מצב-נעילה, מצב-הושלם. **חיפוש+פילטרים** בצד-לקוח (כותרת/תיאור/tags · סוג · נעול/פתוח/הושלם, מיידי). **שיעורי וידאו** עם נגן embed נטען-בלחיצה (lazy). **שיעור נעול** מציג מטא-דאטה + סיבה בשפה פשוטה ("Unlocks at <rank>" / "Available on <plan> plan") — "show the door, name the key", כמו E7b why-not ו-POSITION horizon lock; התוכן עצמו נשלט-שרת. deep-link מ-Concept Tooltip (`/academy#<slug>`) עדיין מדגיש. ניהול השיעורים (create/edit/reorder/archive/video/tags/gating) בקונסולת האדמין (סקשן "academy").

> כל המספרים נשלטים מהאדמין בלי קוד. הטבלה היא ברירת מחדל מוצעת — לאישור נדב.
> **Free tier (D2, נדב 2026-07-09):** מסלול חינמי קבוע — סריקה 1/יום, 2 מטבעות, Blueprint מלא, F3 מוגבל ל-7 ימים, ללא ייצוא, academy בסיסי. במסך paywall/פיצול — אפשרות משנית **"Continue on Free"**.
> **טבלת ההשוואה — חובה בעמוד ה-Subscribe (E3, נדב 2026-07-11):** טבלת ה-Free-מול-בתשלום שלמעלה **חייבת להיות מוצגת ללקוח בעמוד ה-Subscribe/paywall עצמו** — כדי שהמשתמש רואה בדיוק מה כלול בכל מסלול לפני החלטה. שורת ה-Free מתויגת "Free forever" (1 סריקה/יום · 2 מטבעות · Blueprint מלא · יומן 7 ימים · ללא ייצוא). ראו PRD F7 (AC paywall) + copy-guard ATP TC-J-002.
> **שליטה ובחירה** = שלושה מסלולים (Free + 2 בתשלום, אחרי Decision A) נותנים ללקוח תחושת בקרה. **trial 14 יום ללא כרטיס** בכל הפלאנים בתשלום; אין חיוב אוטומטי — בסוף התקופה בחירה אקטיבית. **BUG 4 (v0.10.0):** ה-CTA של ה-trial קורא ישירות ל-`POST /api/cardcom/trial` (ללא מסך checkout/כרטיס) ומנחית ל-`/scan` עם TRIAL chip.
> **✅ SHIPPED — Stage 3 billing UX (v0.14.0, sandbox/mock):** מחירים בעמוד ה-Subscribe מוצגים כ-**₪ סופי + הערת "prices include VAT"** (D-B2). **באנר חיוב בתוך האפליקציה** (`BillingBanner`, ב-scan + settings) למצבים past_due ("Payment issue — update payment"), cancelled ("access until <date>, then Free") ו-expired ("on Free — re-subscribe") — כל אחד עם CTA ל-`/subscribe`. **ביטול** מ-Settings ("Cancel plan or leave"): מבצע ביטול end-of-period אמיתי (`POST /api/cardcom/cancel`, גישה נשמרת עד תום התקופה ואז Free) ומיד לאחריו שאלון היציאה (F9), עם הודעת access-until; ביטול-כפול בטוח. חשבונית/קבלה נשלחת במייל לכל חיוב מוצלח. **RED LINE:** אין דחיפה לסחור/gamification; הבאנר הוא סיגנל מצב, לא engagement.

---

## 7. פלטת צבעים (להחלטה ב-Claude Design)

**נעול (אחרי Claude Design):** פלטת **terminal** (כהה) —
`--bg:#0E1116 · --panel:#161B22 · --ink:#E9EEF3 · --mut:#8593A2 · --green:#1FB286 · --amber:#E0913F · --red:#E0584F · --acc:#1FB286`.
טיפוגרפיה: Space Grotesk (display) + IBM Plex Mono (mono).
**daylight** (כתום-קרם, `#DA7756`/`#FBF6F1`/`#1D9E75`) שמור כ-light mode עתידי.
הקהל הוא בוני-הון גלובלי (לא המקפצה) — כהה = "חדר מסחר" רציני.

קוד צבע סמנטי קבוע (תלת-דרגתי): ירוק=מאומת · כתום=נאסף · אפור=מודיעין · אדום=סיכון/SL.

---

## 8. כפתורים ואינטראקציה (להחלטה ב-Claude Design)

- **כפתור הסריקה (נעול):** עגול 158px, מרכזי, gradient כהה, pulse ב-idle. מצבים: idle / scanning (log) / results.
- **Horizon / Analysis Lens / Risk Style toggles:** light, minimal segmented controls in one pre-scan row near the scan button. Remembered per user; applied on the next single scan press. **Horizon** = SWING (active) / POSITION (locked — a *separate* validated universe, not a cosmetic toggle; PRD F1c); **Lens** = display only; **Risk Style** = output geometry only. None touches the score within the active horizon (RED LINE). ⚠ **Minimalism note:** three pre-scan controls is the ceiling — keep the row light so it doesn't crowd the "one button, one decision" core (§1.5).
- **עיגולי מטבע:** קטנים, מסביב לכפתור, צבע לפי כיוון/ציון. לחיצה → Trading Blueprint.
- **כפתורי כרטיס:** משניים, נקיים. (V2: "Copy to LLM".)
- **Concept Tooltip (PRD F14) — ✅ מומש v0.7.0:** אינדיקטור עדין (מקווקו / אייקון "?") על מונחים; לחיצה/ריחוף → בועה קצרה מהאקדמיה (46 מונחים, מנוע `now`-template). קומפוננטה אחת משותפת בכל המסכים; deep-link "Learn more" → `/academy#<id>`.
- **תפריט המבורגר (E5, נדב 2026-07-11) — ✅ מומש v0.8.0 (B3):** ניווט המבורגר עם **Dashboard / Recent scans / Profile / Academy / Settings** + identity block עם LevelMeter, header אחיד (‏≡ / FINARODA / LevelMeter chip), "Report a problem" → טיקט אמיתי. (נכנס פעיל לכל המשתמשים המאומתים, לא רק אחרי תשלום.)
- **פעמון נוטיפיקציות (F11, Stage 5) — ✅ מומש v0.11.0:** ב-identity block של ההמבורגר — כפתור פעמון 🔔 עם badge unread (server-authoritative, cap "9+"), פאנל נפתח מתחתיו (newest-first), פתיחה מסמנת את הפריטים הגלויים כנקראים; לחיצה על פריט עם `link_path` מנווטת. arrival sound/vibration רק כשהאפליקציה פתוחה ורק אחרי אינטראקציה ראשונה (‏autoplay policy), degradation חיננית ב-iOS (‏`navigator.vibrate` no-op). **Settings** מקבל 5 toggles: IN-APP / ARRIVAL SOUND / VIBRATION / PRODUCT EMAILS / UPDATE EMAILS (נשמרים ב-`notification_prefs`, חוצה-מכשירים). **Admin → Broadcast:** preview של audience + נמענים opted-in לאימייל + שלב confirm; כל update-email נושא unsubscribe. **RED LINE:** reveal-teaser ללא ערך תוצאה, אין פוש יזום לסחור.
  - **Recent scans (Decision B, v0.10.0 shipped 2026-07-13):** עמוד היסטוריה **קריא-בלבד**: זמן, מטבעות שנסרקו, כמה עברו, הקשה לתוך תצוגת תוצאה שמורה (מ-`GET /api/scan/history` + `/history/{id}`). **אין** דאטת reveal/outcome (זו נשארת ביומן F3). זו אפורדנס היסטוריה, לא יומן.
  - **Profile ו-Settings הם כעת מסכים נפרדים (v0.10.0):** Profile = זהות (call-sign, דרגה, ותק); Settings = הגדרות הסריקה הנשמרות (Analysis Lens, Risk Style, מטבעות מועדפים).
  - **לוגו FINARODA לחיץ (v0.10.0):** הקשה על הלוגו ב-header מנווטת ל-`/scan` למשתמשים מאומתים.
- **CTA שדרוג:** נוכח אך לא אגרסיבי (trust-not-engagement).
- מצבי ריק: "No setups pass right now" מעוצב כהישג, לא כשגיאה.
- **Dashboard "How is R measured?" explainer (v0.10.0 shipped 2026-07-13):** מסביר את מודל ה-what-if: trigger fill → target / risk, פקיעה אחרי 7 ימים, ה-trailing אינו מסומלץ. חינוכי בלבד, לא נוגע בציון/סף.
- **DEV SIGN-IN button (v0.10.0):** מסך ה-login מרנדר כפתור DEV SIGN-IN כשה-backend מחזיר `dev_magic_link` (‏`DEV_RETURN_MAGIC_LINK`, **prod-guarded**, לעולם לא בפרודקשן). כלי פיתוח בלבד.
- **Admin back-to-app nav (v0.10.0):** קונסולת האדמין כוללת ניווט קבוע חזרה לאפליקציה.
- **Admin v1.1 + churn survey (Stage 7, v0.12.0):** טבלת המשתמשים באדמין מקבלת שורת פילטרים (search/plan/status/min-scans/signup-range) שמצב שלה מקודד ב-URL (shareable), עמודות נוספות (scans, active-days 7/30, rank, churn) בטבלה רחבה שגוללת אופקית ב-desktop (דפוס v0.10.1), וכפתור **EXPORT CSV**. פאנל הטיקט מציג **timeline של breadcrumbs** (מסלול הלקוח: route/scan/api_error/notif) לצד ה-server events. **Churn survey**: ב-Settings נוסף "Cancel plan or leave" — שאלה אחת + טקסט חופשי אופציונלי, **skippable**, נשמר לאדמין (אין פעולת חיוב כאן; Stage 3 חסום). **RED LINE:** active-days הן מטריקת-אדמין בלבד ולא מופיעות בשום מסך משתמש; breadcrumbs לעולם בלי ערך תוצאה.

---

## 9. 7 הדברים שאסור (מה-UX-SPEC, נאכף)

1. התראות תכופות "היכנס עכשיו".
2. ספירת/הצגת רצפים שמלחיצה.
3. פוש להיכנס לעסקה.
4. gamification של תדירות.
5. מעמד מבוסס כמות סריקות/כניסות.
6. הסתרת מצב "כלום לא עובר" (חייב להיות גלוי וחיובי).
7. חשיפת ה-IP/הנוסחאות בייצוא.

---

## 10. מדדי הצלחה (מה מודדים)
היצמדות לסף · שיעור דילוג חכם · avgR היפותטי לאורך זמן — **לא** entries/day, **לא** זמן-במסך, **לא** תדירות סריקה.

---

_v1.1 — עיצוב הליבה אושר (Claude Design). נעול: פלטה terminal, פריסה ring/list, אנימציה log, סף 85/82. סבב Design שני נדרש למסכים: auth/onboarding, paywall/3-פלאנים, פרופיל+שלבי יוקרה, אדמין, academy, ייצוא, טיקטים._
