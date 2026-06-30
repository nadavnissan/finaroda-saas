# FINARODA SaaS — Legal Draft (for lawyer review)

> ⚠️ **טיוטה לעורך דין בלבד.** Claude אינו עורך דין וזו אינה חוות דעת משפטית. המסמך מסמן את הסיכונים והניסוחים הנדרשים; עו"ד חייב לאשר/לתקן לפני פרסום. דין ישראלי (V1), עם מבט לעתיד גלובלי.

---

## 0. מפת הסיכון המשפטי (למה זה קריטי)

המוצר מציג Entry/SL/TP/Trailing וציון על מסחר קריפטו ממונף, בתשלום, לקהל שעשוי לכלול מתחילים. **הסיכון:** רשות ני"ע / רגולטור עלול לראות בזה **ייעוץ השקעות / שיווק השקעות** — פעילות מפוקחת בישראל (חוק הסדרת העיסוק בייעוץ השקעות, התשנ"ה-1995). חשיפה לתביעות לקוחות על הפסדים.

**שלוש שכבות הגנה (חייבות לעבוד יחד):**
1. **מסגור** — "מערכת ניתוח/חינוך", לא "המלצות".
2. **דיסקליימר** — נוכח בכל מסך רלוונטי, לא רק ב-ToS.
3. **אכיפה בקוד ובקופי** — אין מילים כמו "המלצה", "תיכנס", "קנה".

---

## 1. עקרונות הניסוח (לאכוף בכל המוצר)

- **כן:** "analysis", "data", "score", "levels", "what the system flagged".
- **לא:** "recommendation", "buy", "enter now", "you should", "advice", "signal-to-trade".
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

---

_טיוטה לעו"ד. לא לפרסום לפני אישור משפטי. נדב מעביר לעו"ד; התיקונים חוזרים ל-SPEC/PRD._
