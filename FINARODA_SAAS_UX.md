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

### זרימה
Pre-scan the user sets a light, remembered controls row: **Horizon** (SWING 1–7 days = active · POSITION weeks+ = **locked**, "In validation. Unlocks when it earns it." — PRD F1c), **Analysis Lens** (EMA200/RSI/Volume/Full — display only) and **Risk Style** (Conservative/Balanced/Aggressive — output geometry only). None changes the score or which coins pass within the active horizon (RED LINE, PRD §3.5.5). Then: כפתור עגול גדול במרכז → לחיצה → **אנימציית סריקה במילים** (Downloading tickers… / Analyzing candles… / Computing volume… / Scoring…) → **טבעת עיגולים** מסביב לכפתור, כל עיגול = מטבע שעבר סף → לחיצה על עיגול → **Trading Blueprint**.

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
- **Live Chart + Explanation Overlays (PRD F15):** גרף חי לכל מטבע נסרק (מרונדר מ-kline דרך recharts — לא צילום TradingView/Bybit), עם שכבות הסבר. **Gating:** Free = גרף + EMA200 · בתשלום = כל השכבות (EMA7, רמות ה-Blueprint על הגרף). השכבות הצגה בלבד — לא משנות ציון (RED LINE). **Design סבב 2.**
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

| | Free 0₪ | בסיס 50₪ | מתקדם 100₪ | פרו 150₪ |
|---|---|---|---|---|
| מטבעות בסריקה | 2 (סריקה 1/יום) | 2 | 5 | 10 |
| Trading Blueprint מלא | ✓ | ✓ | ✓ | ✓ |
| דאשבורד "מה היה קורה" | 7 ימים אחרונים | ✓ | ✓ | ✓ |
| ייצוא תוצאות | — | — | ✓ | ✓ |
| Academy (וידאו) | בסיסי | בסיסי | מלא | מלא |
| (V2) Copy-to-LLM | — | — | — | ✓ |

> כל המספרים נשלטים מהאדמין בלי קוד. הטבלה היא ברירת מחדל מוצעת — לאישור נדב.
> **Free tier (D2, נדב 2026-07-09):** מסלול חינמי קבוע — סריקה 1/יום, 2 מטבעות, Blueprint מלא, F3 מוגבל ל-7 ימים, ללא ייצוא, academy בסיסי. במסך paywall/פיצול — אפשרות משנית **"Continue on Free"**.
> **טבלת ההשוואה — חובה בעמוד ה-Subscribe (E3, נדב 2026-07-11):** טבלת ה-Free-מול-בתשלום שלמעלה **חייבת להיות מוצגת ללקוח בעמוד ה-Subscribe/paywall עצמו** — כדי שהמשתמש רואה בדיוק מה כלול בכל מסלול לפני החלטה. שורת ה-Free מתויגת "Free forever" (1 סריקה/יום · 2 מטבעות · Blueprint מלא · יומן 7 ימים · ללא ייצוא). ראו PRD F7 (AC paywall) + copy-guard ATP TC-J-002.
> **שליטה ובחירה** = ארבעה מסלולים (Free + 3 בתשלום) נותנים ללקוח תחושת בקרה. **trial 14 יום ללא כרטיס** בכל הפלאנים בתשלום; אין חיוב אוטומטי — בסוף התקופה בחירה אקטיבית.

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
- **Concept Tooltip (PRD F14):** אינדיקטור עדין (מקווקו / אייקון "?") על מונחים; לחיצה/ריחוף → בועה קצרה מהאקדמיה. קומפוננטה אחת משותפת בכל המסכים. **Design סבב 2.**
- **תפריט המבורגר אחרי תשלום (E5, נדב 2026-07-11):** אחרי המרה לתשלום — ניווט המבורגר עם **Dashboard / Profile / Academy / Settings**. נכנס להיקף **Design סבב 2 (ROADMAP X1)**.
- **CTA שדרוג:** נוכח אך לא אגרסיבי (trust-not-engagement).
- מצבי ריק: "No setups pass right now" מעוצב כהישג, לא כשגיאה.

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
