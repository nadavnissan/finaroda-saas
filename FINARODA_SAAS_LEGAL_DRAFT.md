# FINARODA SaaS — Legal Draft (for lawyer review)

> ⚠️ **טיוטה לעורך דין בלבד.** Claude אינו עורך דין וזו אינה חוות דעת משפטית. המסמך מסמן את הסיכונים והניסוחים הנדרשים; עו"ד חייב לאשר/לתקן לפני פרסום. דין ישראלי (V1), עם מבט לעתיד גלובלי.

---

## 0. מפת הסיכון המשפטי (למה זה קריטי)

המוצר מחשב **Mathematical Trigger Point / Calculated Risk Level / Calculated Target Level / Dynamic Risk Level** (former Entry/SL/TP/Trailing) וציון על מסחר קריפטו ממונף, בתשלום, לקהל שעשוי לכלול מתחילים. **הסיכון:** רשות ני"ע / רגולטור עלול לראות בזה **ייעוץ השקעות / שיווק השקעות** — פעילות מפוקחת בישראל (חוק הסדרת העיסוק בייעוץ השקעות, התשנ"ה-1995). חשיפה לתביעות לקוחות על הפסדים.

> **v2 reframing (front-end only; the calculation engine is unchanged).** To reinforce
> the **utility-calculator** framing (not advisory): (a) calculator terminology (§1);
> (b) a "how it was computed" transparency note beside every level; (c) the user
> operates the tool on **their own configuration** — an **Analysis Lens** (what is
> displayed) and a **Risk Style** (Conservative/Balanced/Aggressive, which shifts only
> the risk geometry). The system executes the user's chosen configuration; it does not
> tell the user what to do. The verified edge, score, and threshold are never
> client-modifiable (see §6 RED LINE).

**שלוש שכבות הגנה (חייבות לעבוד יחד):**
1. **מסגור** — "מערכת ניתוח/חינוך", לא "המלצות".
2. **דיסקליימר** — נוכח בכל מסך רלוונטי, לא רק ב-ToS.
3. **אכיפה בקוד ובקופי** — אין מילים כמו "המלצה", "תיכנס", "קנה".

---

## 1. עקרונות הניסוח (לאכוף בכל המוצר)

- **כן:** "analysis", "data", "score", "calculated levels", "what the system flagged", "mathematical trigger point", "calculated risk/target level", "calculated via …".
- **לא:** "recommendation", "buy", "enter now", "you should", "advice", "signal-to-trade".
- **Calculator terminology (canonical — PRD §3.5.1):** Entry → **Mathematical Trigger Point** · Stop Loss → **Calculated Risk Level** · Take Profit → **Calculated Target Level** · Trailing → **Dynamic Risk Level** · the card → **Trading Blueprint**.
- Each calculated level carries a short **formula-transparency** note (e.g. "Calculated via ATR14 on your selected chart") — framing the tool as a calculator, not an adviser.
- כל תוצאה מתויגת: **"Analysis, not financial advice."**
- כל "מה היה קורה" מתויג: **"Hypothetical result. Not a prediction. Not advice."**

---

## 2. Terms of Service — נקודות חובה (שלד לעו"ד)

1. **אופי השירות:** כלי ניתוח/חינוך טכני. אינו ייעוץ השקעות, אינו שיווק השקעות, אינו ניהול תיקים. המשתמש מקבל החלטות באופן עצמאי ועל אחריותו בלבד.
2. **אין אחריות לתוצאות:** המידע "as-is". אין הבטחה לרווח. מסחר ממונף בקריפטו = סיכון גבוה לאובדן מלא של ההון. תשואות עבר ≠ עתיד.
3. **הגבלת אחריות (Limitation of Liability):** החברה לא תישא באחריות להפסדי מסחר, ישירים/עקיפים. תקרת אחריות = דמי המנוי ששולמו (לעו"ד לכמת).
4. **שיפוי (Indemnification):** המשתמש משפה את החברה מתביעות צד ג' הנובעות משימושו.
5. **כשירות:** גיל 18+, כשירות משפטית, לא תושב/אזרח של תחום שיפוט שבו השירות אסור.
6. **מנוי וחיוב:** trial 14 יום עם כרטיס, חיוב אוטומטי מתחדש, מדיניות ביטול/החזר (לעו"ד — חוק הגנת הצרכן, זכות ביטול עסקה).
7. **קניין רוחני:** הלוגיקה/הציון/הנוסחאות קניין החברה. אסור reverse-engineering. ייצוא תוצאות מותר; ייצוא/חשיפת המערכת אסור.
8. **שינוי תנאים, סיום, סמכות שיפוט (ישראל), דין חל.**

---

## 3. Disclaimer — הנוסח שמופיע במוצר (קצר, בכל מסך)

**גרסה קצרה (תחתית כרטיס/סריקה):**
> "Analysis, not financial advice. Leveraged crypto trading carries high risk of total loss. You decide; you are responsible."

**גרסה מלאה (מסך כניסה ראשון + עמוד נפרד):**
> "FINARODA is a technical analysis and education tool. It does not provide investment advice, investment marketing, or portfolio management. Nothing here is a recommendation to buy, sell, or enter any position. Scores and levels are algorithmic analysis of public market data, not predictions. Leveraged cryptocurrency trading is extremely high-risk and may result in the total loss of your capital. Past performance does not indicate future results. All trading decisions are yours alone and made at your own risk."

**אישור חד-פעמי:** checkbox בהרשמה — "I understand FINARODA is analysis, not advice, and I trade at my own risk." נשמר ב-`consent_log` (consent_type='tos_risk', version, timestamp, ip).

---

## 4. Privacy / הגנת פרטיות — נקודות חובה

חוק הגנת הפרטיות (ישראל) + מבט ל-GDPR (התרחבות גלובלית).

1. **מה נאסף:** אימייל, פרטי מנוי, **לוג ציר-זמן של ציוני סריקה ותוצאות** (score_log), היסטוריית סריקות, נתוני שימוש.
2. **למה — שקיפות מלאה:** הדאטה משמשת **לשיפור המערכת ולמחקר** (base-rate, איכות הציון). **חובה הסכמה מפורשת** (checkbox נפרד בהרשמה) — "I consent to my scan data being used to improve and research the system."
3. **מה לא נאסף:** אין חיבור לחשבון Bybit, אין מפתחות API, אין רישום פוזיציות אמיתי, אין IP מלא (אזור בלבד).
4. **זכויות המשתמש:** עיון, תיקון, מחיקה (right to erasure). מנגנון מחיקת חשבון + דאטה.
5. **אחסון ואבטחה:** הצפנה, מיקום שרתים (Railway/R2), שמירת חשבוניות לפי דרישת רשויות המס גם אחרי מחיקה.
6. **צד ג':** Cardcom (תשלום), Resend (מייל), Cloudflare R2, Sentry — לפרט במדיניות.
7. **Cookies:** JWT ב-httpOnly cookie לצורך התחברות — להזכיר.

---

## 5. נקודות ספציפיות לעו"ד להכריע

1. האם הצגת Entry/SL/TP בתשלום חוצה לקו "ייעוץ השקעות" המפוקח? אם כן — האם מסגור "חינוכי" + דיסקליימר מספיק, או צריך רישוי/שינוי מודל?
2. האם "מערכת ניתוח" פותרת, או שעצם ההמלצה על רמות = שיווק השקעות?
3. מדיניות ביטול/החזר למנוי מתחדש (חוק הגנת הצרכן).
4. referral עם תגמול כספי (50% הנחה) — השלכות מס/רגולציה?
5. חבות על נתוני מחקר (score_log) אם דולפים.
6. ניסוח שמגן בלי "להרוג" את ערך המוצר (לקוח עדיין צריך להרגיש שהכלי שימושי).
7. **Reframing (v2):** does presenting the product as a **utility calculator the user
   operates on their own configuration** (Analysis Lens + Risk Style), with formula
   transparency and calculator terminology, materially strengthen the "not advice"
   position? Is the "the system executed the configuration the user chose" framing
   (§6) helpful for limiting liability, and is it drafted defensibly?

---

## 6. 🔴 RED LINE — client configuration boundary (calculator framing)

This boundary is the legal spine of the calculator framing. It is enforced in code and
copy, and mirrored in PRD §3.5.5.

- The client **operates** the tool but **never modifies what counts as an opportunity**:
  the **score**, the **filter weights**, the **verified EMA7-slope edge**, and the
  **85 PASS / 82 WATCH threshold** are not client-editable. There is **no per-user score
  threshold**.
- Client choices are strictly limited to **(a) what is displayed** (Analysis Lens) and
  **(b) risk geometry** (Risk Style → `computeSlTp` `opt`: `slAtrMult`/`tp1Mult`/`tp2Mult`).
- Legal effect: for any calculated level the client sees, **the system executed the
  configuration the client selected** — it is a calculator producing outputs from the
  user's chosen parameters, not an adviser issuing a recommendation. The verified edge
  and the shared research base-rate remain identical across all users (measure-first),
  because no client choice changes the opportunity set.

> Drafting note for the lawyer: consider pairing this with an explicit ToS clause —
> "levels are computed from parameters you select; the system performs a calculation,
> it does not advise" — and a per-Blueprint record of the configuration used
> (`decision_snapshots.card_json`).

---

_טיוטה לעו"ד. לא לפרסום לפני אישור משפטי. נדב מעביר לעו"ד; התיקונים חוזרים ל-SPEC/PRD._
