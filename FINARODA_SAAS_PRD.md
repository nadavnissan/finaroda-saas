# FINARODA SaaS — Product Requirements Document (PRD v2.1)

> מסמך מוצר מפורט, מעוגן בעיצוב המאושר (Claude Design) ובמסמכי המקור (SPEC/UX/LEGAL). לאישור נדב.
> כל פיצ'ר כולל: תיאור · user flow · acceptance criteria · מצבי קצה. מסמך שמפתח (או Claude Code) בונה ממנו ישירות.
> **קהל יעד: כל מי שרוצה לייצר הון** (לא קהילת המקפצה). גלובלי, נייד-first, UI אנגלית.
> **v2.1 — Regulatory reframing (front-end only; the calculation engine is unchanged).** New calculator terminology, formula transparency, an Analysis Lens (display-only), and a Risk Style client choice (affects output geometry, never the score). See §3.5 and the RED LINE. Written in English (see §3.5).

---

# חלק א' — מוצר וחזון

## 1. הבעיה והפתרון

**הבעיה.** מי שרוצה לבנות הון דרך מסחר קריפטו מתמודד עם שלושה כשלים: (1) אובר-טריידינג ו-FOMO, (2) היעדר משמעת בכניסה/יציאה, (3) הצפת מידע או "סיגנלים" חסרי בסיס אמפירי. רוב הכלים מעמיסים דאטה או מוכרים הבטחות.

**הפתרון.** FINARODA הוא כלי **ניתוח** מינימליסטי שמזקק את השוק להחלטה ברורה, מבוסס על ה-edge היחיד שאומת אמפירית (שיפוע EMA7) ועל ניהול סיכון — ומתגמל **משמעת ודילוג**, לא תדירות. לחיצה אחת → סריקה → מה שעבר סף → כרטיס החלטה מדויק.

**ההבטחה ללקוח:** לא "תרוויח". אלא — "תדע מתי המערכת מזהה הזדמנות שעברה סף, תקבל רמות מדויקות לניהול סיכון, ותלמד מתי **לא** לסחור. ההחלטה והאחריות שלך."

## 2. קהל יעד ופרסונות

**מי:** בוני-הון — אנשים שרוצים להשתמש בקריפטו ככלי לצמיחת הון, ברצינות ובמשמעת. רמת ביניים ומעלה. גלובלי.

| פרסונה | צורך | מה FINARODA נותן |
|---|---|---|
| "הסוחר המתוסכל" | מפסיד מאובר-טריידינג ו-FOMO | מחסור — רוב הימים "אל תסחר" |
| "בונה ההון המתודי" | רוצה תהליך, לא הימור | ציון מאומת + ניהול סיכון + "מה היה קורה" |
| "המתחיל הזהיר" | פוחד לטעות, צריך מסגרת | כרטיס ברור + חינוך (academy) + תיוג "ניתוח לא ייעוץ" |

## 3. עקרונות-על (חוזה המוצר — נאכף בקוד, קופי ומשפט)

1. **ניתוח לא ייעוץ.** אין "המלצה/תיכנס/קנה". מתויג בכל מסך.
2. **ליבה דטרמיניסטית.** חישוב, לא LLM. אסור ל-LLM להזיז ציון.
3. **trust-not-engagement.** מתגמלים דיוק ודילוג. אין פוש לסחור, ספירת רצפים מלחיצה, gamification של תדירות.
4. **רק מדדים מאומתים נחשפים** — שיפוע EMA7 (verified) + volume (collected). לא funding/OI.
5. **מחסור מכובד.** "כלום לא עובר" = מסך חיובי, הישג של משמעת.
6. **מנוע משותף** — אותו `scoring-engine.js` בכלי האישי וב-SaaS.
7. **שליטה ובחירה** — 3 פלאנים, הגדרות, ייצוא, פרופיל בשליטת הלקוח.

---

## 3.5 Regulatory Reframing — Calculator Framing, Terminology & Client Choices (v2.1)

> **This is a FRONT-END reframing. The calculation engine (`scoring-engine.js`), the
> verified EMA7-slope edge, the filter weights, and the 85/82 score threshold DO NOT
> CHANGE.** Only terminology, what is displayed, and the risk geometry the client
> requests change. Purpose: present FINARODA unambiguously as a **utility calculator**
> the user operates on their own inputs — not an advisory service.

### 3.5.1 Terminology (calculator, not advice) — canonical mapping
This mapping governs ALL product surfaces (UI, PRD, UX, LEGAL). Where an older term
still appears elsewhere in this doc, it is read through this table.

| Advice-flavored term (old) | Calculator term (new, canonical) |
|---|---|
| Entry | **Mathematical Trigger Point** |
| Stop Loss / SL | **Calculated Risk Level** |
| Take Profit / TP | **Calculated Target Level** |
| Trailing | **Dynamic Risk Level** |
| Decision Card (the whole card) | **Trading Blueprint** |

The **"Analysis, not financial advice."** label is retained on every surface.

### 3.5.2 Formula transparency (new)
Every calculated level shows a short, plain-language "how it was computed" note beside
it — reinforcing the utility-tool framing. Proposed copy (final wording pending lawyer):

| Level | Transparency note |
|---|---|
| Mathematical Trigger Point | "Calculated from live price relative to EMA structure." |
| Calculated Risk Level | "Calculated via ATR14 on your selected chart." |
| Calculated Target Level | "Calculated as an R-multiple of the risk distance." |
| Dynamic Risk Level | "Calculated from ATR-based trailing geometry." |

### 3.5.3 Analysis Lens — client choice, DISPLAY ONLY
Before scanning, the user picks a lens: **EMA200 / RSI / Volume / Full**. The **engine
and the score are identical regardless of lens** — the lens only changes WHAT IS
DISPLAYED on the Trading Blueprint (e.g. pick RSI → see the RSI reading alongside the
calculated risk levels and the Blueprint). Minimal: a light toggle, remembered per
user, applied on the next single scan press. User-initiated — no proactive "enter now"
push (trust-not-engagement, §3.3).

**AC:** (a) lens changes displayed panels only, never `score`/PASS-WATCH selection;
(b) same coins pass the threshold under any lens; (c) remembered across sessions;
(d) one scan press honors the current lens.

### 3.5.4 Risk Style — client choice, affects OUTPUT (not the score)
The user picks **Conservative / Balanced / Aggressive**. This changes ONLY the risk
geometry passed to `computeSlTp`'s `opt` (`slAtrMult` / `tp1Mult` / `tp2Mult`) — so the
calculated levels move, but the **score, filter, edge and threshold are untouched**.
This gives genuine "the system executed the configuration I chose" standing (LEGAL)
while the verified edge and the shared base-rate stay intact.

Proposed defaults (admin-tunable; **Balanced == the engine's built-in defaults**):

| Style | slAtrMult | tp1Mult | tp2Mult | Effect |
|---|---|---|---|---|
| Conservative | 1.0 | 1.0 | 2.0 | Tighter Calculated Risk Level, nearer Target |
| Balanced (default) | 1.5 | 1.5 | 3.0 | Engine defaults |
| Aggressive | 2.0 | 2.0 | 4.0 | Wider Risk Level, further Target |

**AC:** (a) style changes only `computeSlTp` `opt`; (b) `score` and PASS/WATCH are
byte-identical across styles; (c) the chosen style is logged into
`decision_snapshots.card_json` for the "system executed my choice" record;
(d) engine code is NOT modified — only the `opt` argument.

### 3.5.5 🔴 RED LINE (non-negotiable; also in LEGAL §6)
The client **NEVER** modifies: the **score**, the **filter weights**, the **EMA7-slope
edge**, or the **85 PASS / 82 WATCH threshold**. Client choices live ONLY in **(a) what
is displayed** (Analysis Lens) and **(b) risk geometry** (Risk Style via `computeSlTp`
`opt`) — never in **what counts as an opportunity**. This protects measure-first and the
shared base-rate: every user, whatever their lens/style, sees the same coins pass the
same verified threshold, so the base-rate stays clean and comparable.

> Consequence: the previously-proposed **per-user score threshold** (old F5 "personal
> threshold") is **removed** — it would let the client change what counts as an
> opportunity, violating the RED LINE. The global threshold stays admin-controlled only.
> (`users.default_threshold` remains in the schema but is reserved for admin per-user
> overrides, never client-editable.)

---

# חלק ב' — תכונות מפורטות (Features)

> כל פיצ'ר: תיאור · flow · acceptance criteria (AC) · מצבי קצה.

## F1 — סריקה בלחיצה (Core)

**תיאור.** כפתור עגול מרכזי. לחיצה → משיכה client-side טרייה מ-Bybit → אנימציית log → תוצאות (עוברי-סף בלבד).

**Flow:**
1. idle: כפתור "SCAN · N MARKETS" (N לפי פלאן) + pulse. Pre-scan, the user's **Analysis Lens** and **Risk Style** (§3.5.3–3.5.4) are shown as light, remembered toggles — neither changes the score or which coins pass (RED LINE §3.5.5).
2. לחיצה → scanning: log זורם — Downloading tickers → Analyzing candles → Computing volume → Scoring setups (checkmark לכל שלב).
3. משיכה client-side מ-`api.bybit.com/v5/market/*` (IP של הלקוח, אין קאש משותף). חישוב דרך `scoring-engine.js`.
4. results: "X PASS · N SCANNED" + עיגולי מטבעות שעברו (ring עד 5, list מעבר).
5. כל מטבע: סמל, כיוון (↑/↓), ציון, צבע (ירוק PASS / אמבר WATCH).
6. "↻ scan again" — מותר תמיד (דיוק תזמון), אין cooldown מלאכותי.

**AC:**
- AC1: כל לחיצה = fetch חדש מ-Bybit (לא קאש). כשל → error נקי + retry.
- AC2: רק ≥82 מוצגים. ≥85 = PASS ירוק. 82-84 = WATCH אמבר. <82 לא מוצג.
- AC3: מספר נסרקים = מגבלת הפלאן (2/5/10), נקרא מ-`system_settings`.
- AC4: כל סריקה → `scan_events` + שורת `score_log` לכל מטבע נסרק (גם שלא עבר).
- AC5: ring כש-passes ≤5, list כש->5.

**מצבי קצה:** 0 עוברים → F1b. rate-limit/שגיאה → הודעה + retry, לא קורס. מטבע בודד → ring עם עיגול אחד.

## F1b — Empty State ("מחסור מכובד")

**תיאור.** כשאף מטבע לא עובר — מסך שחוגג דילוג כמשמעת.
**תוכן:** ✓ ירוק · "No setups pass right now" · "Most days are skip days, and the skip is the edge." · באדג' "Skipped X of last Y days · Disciplined" · "The market moves — re-check when it does. Precision, not habit."
**AC:** AC1: מופיע ב-0 עוברי-סף. AC2: אין CTA שמעודד סריקה כפייתית. AC3: הבאדג' מבוסס `scan_events` אמיתי.

## F2 — Trading Blueprint (formerly "decision card")

**תיאור.** bottom-sheet בלחיצה על מטבע. The card as a whole is the **Trading Blueprint** (§3.5.1).
**תוכן (לפי העיצוב):** pair title + direction badge + "Timing verified · score X/100" · EMA7 SLOPE (signed) + POSITION row · grid of the four calculated levels, each with a formula-transparency note (§3.5.2):
- **Mathematical Trigger Point** (was Entry) — "Calculated from live price relative to EMA structure."
- **Calculated Risk Level** (was Stop Loss, +%) — "Calculated via ATR14 on your selected chart."
- **Dynamic Risk Level** (was Trailing) — "Calculated from ATR-based trailing geometry."
- **Calculated Target Level** (was Take Profit, +%) — "Calculated as an R-multiple of the risk distance."

· RISK:REWARD "1:X.X" · Volume "collected" (intel ▾) · the panels shown reflect the active **Analysis Lens** (§3.5.3) · levels reflect the active **Risk Style** (§3.5.4) · "Analysis, not financial advice."
**AC:**
- AC1: all levels come from `scoring-engine.js` (`computeSlTp` / `computeReversalAnchor`).
- AC2: Calculated Risk Level is always on the correct side (corrected floor geometry, personal tool v25.80).
- AC3: EMA7 slope is signed. volume = "collected" (not verified).
- AC4: labels present. No "recommendation/buy/enter".
- AC5: open → `decision_snapshots` (card_json, incl. the active lens + risk style — §3.5.4 AC-c).
- AC6: switching Analysis Lens or Risk Style never changes `score`/PASS-WATCH (RED LINE §3.5.5).
**מצב קצה:** WATCH → Blueprint tagged "WATCH — below the calculated threshold, monitor only", not counted in "what would have happened".

## F3 — דאשבורד "What Would Have Happened"

**תיאור.** על כל ה-PASS שהלקוח קיבל: תשואה היפותטית.
**תוכן:** רשימת setups (סמל/כיוון/R/WIN-STOP-OPEN) + AVG R + ADHERENCE + SMART-SKIP · "Hypothetical · not advice · never entries-per-day".
**AC:** AC1: מ-`score_log` (PASS בלבד) אחרי backtest. AC2: WATCH לא נספר. AC3: SMART-SKIP=% ימי דילוג כשאין PASS; ADHERENCE=% הצמדות. AC4: היפותטי בכל מקום, רק R (לא כסף).
**מצב קצה:** אין מספיק תוצאות → "Not enough resolved setups yet. Keep scanning."

## F4 — ייצוא תוצאות (בלי חשיפת המערכת)

**תיאור.** ייצוא דאטה, לא לוגיקה.
**כן:** symbol/direction/score/Mathematical Trigger Point/Calculated Risk Level/Calculated Target Level/timestamp → CSV/PNG. **לא:** weights/formulas/threshold/logic.
**AC:** AC1: זמין מפלאן Advanced+. AC2: אפס פרמטר פנימי בקובץ. AC3: PNG בפלטת terminal.

## F5 — פרופיל ושלבי יוקרה

**הגדרות:** **Analysis Lens** (EMA200/RSI/Volume/Full — display only, §3.5.3), **Risk Style** (Conservative/Balanced/Aggressive — output geometry only, §3.5.4), מטבעות מועדפים (בגבולות פלאן), פלטה. **אין** סף-ציון אישי — הלקוח לא משנה מה נחשב הזדמנות (RED LINE §3.5.5).
**שלבי יוקרה (משמעת, לא תדירות):** Newcomer (הרשמה) → Disciplined (X ימי דבקות כולל דילוגים) → Precise (היסטוריית "מה היה קורה" חיובית) → Veteran (ותק+התמדה).
**AC:** AC1: מעמד ממדדי משמעת, **לא** ממספר סריקות/כניסות. AC2: עליית שלב = נוטיפיקציה חיובית (לא פוש לסחור).
**אסור (חוסם קוד-רוויו):** מעמד שמתגמל תדירות.

## F6 — Academy (וידאו למידה)
**תיאור.** YouTube unlisted — איך לקרוא כרטיס, מהו שיפוע EMA7, ניהול סיכון, משמעת.
**AC:** AC1: גישה לפי פלאן (אדמין). AC2: נגן 9:16. AC3: צפייה נרשמת.

## F7 — מנוי, Trial ותשלום

| פלאן | ₪/חודש | מטבעות | ייצוא | Academy |
|---|---|---|---|---|
| Basic | 50 | 2 | — | בסיסי |
| Advanced | 100 | 5 | ✓ | מלא |
| Pro | 150 | 10 | ✓ | מלא |

**Trial:** הרשמה → כרטיס (tokenization) → 14 יום → יום 13 תזכורת → יום 15 חיוב אוטו אלא אם ביטל.
**AC:** AC1: trial עם כרטיס. AC2: חיוב יום 15. AC3: ביטול לפני 14 = אין חיוב. AC4: מגבלות נשלטות מאדמין בלי קוד. AC5: קופונים.
**מצבי קצה:** כשל חיוב → downgrade + נוטיפיקציה. ביטול → שאלון יציאה (F9).

## F8 — חבר מביא חבר
**תיאור.** מגייס מקבל 50% הנחה לחודש — רק אחרי 3 חודשי התמדה של המגויס + אישור אדמין.
**Flow:** קוד → מגויס נרשם → 3 חודשי מנוי רצוף → סימון זכאות → **אישור אדמין** → הנחה.
**AC:** AC1: מעקב referrer→referred. AC2: בדיקת 3 חודשים רצופים. AC3: gate אישור אדמין. AC4: תגמול = הנחה (לא טוקנים). AC5: אין הפניה עצמית.

## F9 — דאשבורד מנהל
**מסכים:** לקוחות (כניסה/נטישה/סטטוס/MRR) · churn (שיעור + סיבת עזיבה משאלון יציאה) · טיקטים · ברודקאסט · קופונים · referral approvals · academy · system_settings (סף, מטבעות/פלאן) · beta/waitlist.
**AC:** AC1: MRR מכבד קופונים/trial/הנחות. AC2: churn = שיעור עם חלון. AC3: כל מוטציה ל-admin log. AC4: סף ומטבעות/פלאן נערכים בלי קוד.

## F10 — מערכת טיקטים
**Flow:** לקוח פותח (קטגוריה+תיאור) → מייל למנהל → מנהל עונה → מייל ללקוח → open→resolved.
**AC:** AC1: סטטוסים open/in_progress/resolved/closed. AC2: Resend. AC3: לקוח רואה היסטוריה.

## F11 — נוטיפיקציות + ברודקאסט
**תיאור.** מערכתיות (חיוב/טיקט/וידאו/שלב יוקרה) + ברודקאסט מנהל.
**אסור:** "מטבע X עבר סף, היכנס!".
**AC:** AC1: מערכתיות בלבד. AC2: in-app + email. AC3: ברודקאסט ל-admin log.

## F12 — שאלון Onboarding עריך
**AC:** AC1: נשמר ב-onboarding_responses. AC2: לקוח יכול לעדכן. AC3: מנהל עורך שאלות בלי קוד.

## V2 (מתועד, לא MVP)
Stripe גלובלי · "Copy to LLM" · PWA push · daylight light-mode · סבב Design למסכים שלא עוצבו.

---

# חלק ג' — לולאת למידה, מדדים, סיכונים

## 13. לולאת הלמידה (Measure-First)
- כל סריקה רושמת **כל** המטבעות + הרמות ל-`score_log`.
- cron יומי מריץ מחיר קדימה וממלא win/loss/avgR (בלי רישום Bybit).
- שני שימושים: מנהל (base-rate, תיקוף הסף) + לקוח ("מה היה קורה").
- **כלל ברזל:** אין כיול סף/ציון לפני 30+ תוצאות מ-2+ משטרים. נשלט מאדמין.

## 14. מדדי הצלחה (KPIs)
| מודדים | לא מודדים |
|---|---|
| Adherence | entries/day |
| Smart-skip rate | זמן-במסך |
| avgR היפותטי לאורך זמן | תדירות סריקה כמטרה |
| trial→paid conversion | DAU כמטרה |
| churn rate + סיבת עזיבה | — |

## 15. Out of Scope (V1)
חיבור Bybit/מסחר אוטומטי · רישום פוזיציות אמיתי · LLM בליבה · שכבת הקריירה/Jobby (נמחקת) · אחסון וידאו מאובטח · Stripe.

## 16. סיכונים
| סיכון | מיטיגציה |
|---|---|
| רגולציה (ייעוץ השקעות) | מסגור ניתוח + דיסקליימרים + עו"ד (LEGAL.md) |
| edge תקף לדובי בלבד | תיוג, אין כיול עד 2+ משטרים, אין הבטחת רווח |
| Bybit rate-limit | client-side (IP לקוח), proxy fallback |
| חוב טכני מהירושה | P0 ניקוי, סכמה נקייה |
| over-reliance | trust-not-engagement, חינוך, דיסקליימר |
| WATCH מזהם base-rate | WATCH לא נספר כפוזיציה מאושרת |

## 17. החלטות נעולות
3 פלאנים 50/100/150 · מטבעות 2/5/10 נשלט-אדמין · trial עם כרטיס · referral 50%/3-חודשים+אישור · UI אנגלית · Cardcom V1/Stripe V2 · YouTube וידאו · מנוע JS משותף · פלטה terminal · פריסה ring/list · אנימציה log · **סף 85 PASS / 82-84 WATCH** · קהל בוני-הון · **(v2.1) calculator terminology (§3.5.1) · formula transparency (§3.5.2) · Analysis Lens display-only (§3.5.3) · Risk Style output-only via `computeSlTp` opt (§3.5.4) · RED LINE: client never touches score/weights/edge/threshold (§3.5.5) · per-user score threshold removed**.

## 18. סדר בנייה (פאזות)
P0 ניקוי → P1 תשתית (Cardcom/auth/deploy) → P2 ליבה (F1/F1b/F2) → P3 למידה (F3/F5) → P4 מסחרי (F7/F8/F4) → P5 מנהל+קהילה (F9/F10/F11/F12/F6) → V2.

---

_PRD v2.0 — מפורט, מעוגן בעיצוב המאושר. לאישור נדב. אחרי אישור → repo כמקור אמת לצד SPEC/UX/LEGAL._
