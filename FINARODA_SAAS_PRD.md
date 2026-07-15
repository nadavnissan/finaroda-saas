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
8. **אמת אמפירית בקופי.** אפס סטטיסטיקות מומצאות, אפס הוכחה חברתית מפוברקת — בשום surface (מוצר **וגם** שיווק). מספרים נחשפים רק ממקורות מאומתים: בקטסטים / לוג הטריידים. אין מספר אמיתי → ניסוח איכותי בלי אחוז.

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

## F1 — סריקה בלחיצה (Core) — ✅ SHIPPED v0.8.0 (Package B B1)

**תיאור.** כפתור עגול מרכזי. לחיצה → משיכה client-side טרייה מ-Bybit → אנימציית log → תוצאות (עוברי-סף בלבד).

> **מומש v0.8.0 (B1):** מסך הסריקה המלא (החליף את מסך P2). gating server-authoritative — `GET /api/scan/entitlements` binding, `POST /api/scan/events` דוחה סריקה מעל מכסת המטבעות (403 `PLAN_COIN_LIMIT`); first-scan-of-day XP (+50, מהשרת בלבד, idempotent per day). ראו SPEC §5.9 (endpoints) + §12 (system_settings keys).

**Flow:**
1. idle: כפתור "SCAN · N MARKETS" (N לפי פלאן) + pulse. Pre-scan, the user's **Horizon** (F1c — SWING active / POSITION locked), **Analysis Lens** and **Risk Style** (§3.5.3–3.5.4) are shown as light, remembered controls — none changes the score or which coins pass within the active horizon (RED LINE §3.5.5). **Coin selection (Decision C, v0.10.0 shipped 2026-07-13):** the user picks WHICH coins to scan, within the plan's coin count (all plans); the selection is a remembered pre-scan control and never changes the score or threshold.
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

## F1c — Horizon Selector (E9, נדב 2026-07-11) — ✅ SHIPPED v0.8.0 (Package B B1)

> **מומש v0.8.0 (B1):** בקר ה-Horizon מרונדר בשורת הבקרים pre-scan — SWING פעיל ונשלח, POSITION מרונדר נעול (לא-אינטראקטיבי) עם הקופי + tooltip המאושרים. honesty guardrail (AC2): כל עוד אין מודל POSITION שרושם תוצאות, הקופי נשאר "planned" — ⬜ פתוח להכרעת נדב (ראו §17 open items).

**תיאור.** בקר Horizon מדורג במסך הסריקה (pre-scan, בשורת הבקרים לצד Analysis Lens ו-Risk Style):
- **SWING (1–7 days)** — **פעיל מ-v1.** ה-edge המאומת (שיפוע EMA7) הוא edge בטווח סווינג; זו הסריקה שנשלחת.
- **POSITION (weeks+)** — **מוצג נעול** ב-v1 (לא-אינטראקטיבי). קופי נעילה (מאושר נדב): **"In validation. Unlocks when it earns it."** · tooltip (מאושר נדב): "Our position-trading engine is being validated against live outcomes across market regimes. We don't ship what we haven't proven."
- **קריטריון פתיחה:** 30+ תוצאות שהתבשלו על פני 2+ משטרים (אותו כלל-ברזל של §13). בפתיחה — מועמד לפיצ'ר **Pro**.

**⚠ הבחנה קונספטואלית (חשוב):** Horizon **אינו** בחירת-לקוח קוסמטית כמו Lens (תצוגה) או Risk Style (גאומטריה). SWING ו-POSITION הם **שני יקומי-מדידה נפרדים**, לכל אחד **סף ו-base-rate מאומתים משלו**. הבקר בוחר יקום — אך לעולם אינו נותן ללקוח לשנות את הציון/הסף *בתוך* יקום נתון (RED LINE §3.5.5 נשמר פר-יקום).

**AC:**
- AC1: SWING פעיל; POSITION מרונדר נעול (לא-אינטראקטיבי) עם הקופי + tooltip המאושרים.
- AC2 (**honesty guardrail — principle 8, §3**): קופי ה-"in validation" אמיתי **רק** ברגע שקיים מודל POSITION שמלוֹג בפועל תוצאות שהתבשלו ל-`score_log`. **כל עוד אין מודל POSITION שרושם תוצאות — POSITION הוא "planned", לא "in validation"**; אסור שהקופי יטען validation פעיל שאינו מתרחש. ⬜ פתוח להכרעת נדב: או לבנות position-outcome log לפני שהקופי מוצג, או לרכך את הקופי ל-future-tense.
- AC3: הפתיחה מותנית ב-30+/2+ משטרים; **אין התחייבות ל-ETA** — לפי הקריטריון, תוצאות POSITION מתבשלות על פני שבועות, כך ש-2+ משטרים ≈ טווח רב-שנתי; **POSITION עשוי לעולם לא להיפתח**, וזו התנהגות תקינה (משמעת, לא באג).
- AC4: SWING/POSITION = יקומים נפרדים; הבקר לעולם אינו משנה את הציון/הסף בתוך יקום פעיל (RED LINE).
**UX:** ראו UX §3 (שורת הבקרים pre-scan) + §8. **Design:** סבב 2 (ROADMAP X1). **POSITION (המימוש):** V2 backlog.

## F1b — Empty State ("מחסור מכובד")

**תיאור.** כשאף מטבע לא עובר — מסך שחוגג דילוג כמשמעת.
**תוכן:** ✓ ירוק · "No setups pass right now" · "Most days are skip days, and the skip is the edge." · באדג' "Skipped X of last Y days · Disciplined" · "The market moves — re-check when it does. Precision, not habit."
**AC:** AC1: מופיע ב-0 עוברי-סף. AC2: אין CTA שמעודד סריקה כפייתית. AC3: הבאדג' מבוסס `scan_events` אמיתי.

## F2 — Trading Blueprint (formerly "decision card") — ✅ SHIPPED v0.8.0 (Package B B1)

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

## F3 — דאשבורד "What Would Have Happened" — ✅ SHIPPED v0.9.0 (Package B B4)

**תיאור.** על כל ה-PASS שהלקוח קיבל: תשואה היפותטית.
**תוכן:** רשימת setups (סמל/כיוון/R/WIN-STOP-SAVE-OPEN) + AVG R + CAPITAL SAVES + discipline meter · "Hypothetical · not advice · never entries-per-day".

**מודל המימוש — `journal_scenarios` (mig 028, `backend/core/journal.py`).** במקום לגזור את הדשבורד ישירות מ-`score_log`, כל סריקה יוצרת רשומות תרחיש דרגה-ראשונה:
- **`pass`** — תרחיש אחד לכל setup שעבר סף (שורת `momentum` עם `passed_threshold=1`). נושא את הגאומטריה (entry/sl/tp/trailing) בזמן הסריקה.
- **`no_setups_day`** — רשומת משמעת אחת ליום דילוג (סריקה ללא PASS). "הדילוג הוא ה-edge". נחשפת מיד (‏`status='skip'`), לא מנפחת את ה-badge.
- **WATCH לעולם אינו תרחיש** (AC2) — לא נספר כפוזיציה מאושרת ולא מזהם את ה-base-rate.

**Resolution (cron צד-שרת, `app/tasks/journal_tasks.py`).** job (‏`resolve_scenarios_task` דרך `scripts/run_resolve_scenarios.py`) מריץ תרחישי `pass` פתוחים מול נרות ה-Bybit היומיים הבאים — trigger fill → target / risk / 7-day expiry — ומחשב `r_result` היפותטי (**R בלבד, לעולם לא כסף**, AC4). ה-`evaluate_outcome` פונקציה טהורה (unit-testable עם נרות סינתטיים). מצבי ה-`status` (‏server-only): `open` · `win` (target ראשון, r=+reward/risk) · `loss` (risk ראשון, r=−1) · `save` (‏**CAPITAL SAVES** — trigger לא נורה בחלון, r=0) · `expired` (נורה, אך ללא target/risk בחלון, r=signed-at-last-close).

**CAPITAL SAVES (הגדרה נעולה למימוש הנוכחי).** SAVE = **תרחיש PASS שה-trigger שלו לא נורה בחלון ה-7 ימים** — אף כניסה לא נפתחה, ההון נשמר (r_result=0). זה יושר עם ה-frame "תרחיש לכל PASS + no-setups-day; WATCH לעולם לא תרחיש" (לא יוצרים תרחישים ל-non-passers). ⬜ **הרחבה עתידית (F3 extension):** שורת ה-SAVE הפר-מטבע-**לא-עובר** (הקריאה המילולית של פריים B4, LINK) — save שנרשם על מטבע שלא עבר סף — היא הרחבה מתוכננת, לא במימוש v0.9.0. טעונה אישור/כיוון נדב.

**Reveal-gating (ALIGNMENT B3 · 2026-07-09 · מומש v0.9.0).** התוצאה מחושבת בשרת אך **אינה נכללת בשום payload ללקוח עד הסריקה הבאה שלו** — אירוע החשיפה הוא הסריקה עצמה (‏`core/journal.on_scan` חושף קודם resolutions קודמות, ואז יוצר תרחישים חדשים שמתחילים `open`). שורות לא-חשופות נושאות **אפס דאטת תוצאה** ב-payload וב-DOM (regression, אותה תבנית כמו S10 באונבורדינג). כשיש תוצאה חדשה שהתבשלה, teaser שקט **"Your journal has an update"** ממתין; ה-Nav badge = ספירת לא-חשופים בלבד (‏`GET /api/journal/badge`), לעולם לא תוכן/פוש. **משיכה, לא פוש.** +25 XP על צפייה בתוצאה חשופה (‏`journal_reveal_viewed`, idempotent per scenario — SPEC §5.6).
**AC:** AC1: מ-`journal_scenarios` (‏`pass` בלבד) אחרי resolution. AC2: WATCH לא נספר. AC3: discipline meter מ-`no_setups_day` אמיתי (ללא יחס-דילוג מומצא); ADHERENCE=% הצמדות. AC4: היפותטי בכל מקום, רק R (לא כסף). AC5 (reveal-gating): תוצאה שהתבשלה נחשפת רק בסריקה הבאה, דרך teaser "journal has an update" — **אין** נוטיפיקציית פוש יזומה (trust-not-engagement §3.3); שורה לא-חשופה נטולת דאטת תוצאה גם ב-DOM.
**מצב קצה:** אין מספיק תוצאות → "Not enough resolved setups yet. Keep scanning."
**⬜ תלוי-פריסה:** job ה-resolution צד-שרת, לא auto-run — יש לחווט את ה-cron בפריסה (`python -m backend.scripts.run_resolve_scenarios`, יומי); עד אז תרחישים נשארים `open`.

## F3b - Recent scans (היסטוריית סריקות, read-only) - ✅ SHIPPED v0.10.0 (Decision B, shipped 2026-07-13)
**תיאור.** עמוד היסטוריה **קריא-בלבד** נגיש מתפריט ההמבורגר: רשימת הסריקות האחרונות (זמן, מטבעות שנסרקו, כמה עברו) עם הקשה לתוך תצוגת תוצאה שמורה. **מקור:** `GET /api/scan/history` + `GET /api/scan/history/{id}` (נגזר מ-`score_log`/`scan_events`). **אין** דאטת reveal/outcome (זו נשארת ב-F3/reveal-gating בלבד), זו אפורדנס היסטוריה, לא יומן.
**עדכון v0.17.2 (FX3):** תצוגת התוצאה השמורה מציגה כעת את **ה-Trading Blueprint המלא** — גרף Chart Standard (עם gating שכבות לפי plan, כמו כרטיס הסריקה) + ארבע הרמות המחושבות במינוח **הקנוני בלבד**: Mathematical Trigger Point / Calculated Risk Level / Dynamic Risk Level / Calculated Target Level, עם הערות שקיפות-נוסחה + Risk:Reward + כותרת TIMING VERIFIED/WATCH · score. אלו ערכי **setup-time שכבר הוצגו בעת הסריקה** (לא outcome מוסתר) ולכן מותרים; ה-reveal/outcome נשאר ב-F3 בלבד. הגרף נמשך מהשוק החי (נרות היסטוריים אינם נשמרים) עם הרמות כפי שנרשמו. **אסור לחלוטין** בכל טקסט מול-משתמש: המילים SL / TP / ENTRY (guard ב-`test_content_copy.py`).
**AC:** AC1: read-only, ללא כל mutation. AC2: מציג זמן/מטבעות/passes + ה-Blueprint השמור (רמות setup-time + גרף) במינוח הקנוני; אין חשיפת תוצאה/reveal מעבר למה שכבר הוצג; המילים SL/TP/ENTRY נעדרות. AC3: נגיש מתפריט ההמבורגר (הכולל כעת גם כניסת "Scan" מפורשת — FX2).

## F4 — ייצוא תוצאות (בלי חשיפת המערכת)

**תיאור.** ייצוא דאטה, לא לוגיקה.
**כן:** symbol/direction/score/Mathematical Trigger Point/Calculated Risk Level/Calculated Target Level/timestamp → CSV/PNG. **לא:** weights/formulas/threshold/logic.
**AC:** AC1: זמין מפלאן Basic+ (בתשלום). AC2: אפס פרמטר פנימי בקובץ. AC3: PNG בפלטת terminal.

## F5 — פרופיל ושלבי יוקרה — ✅ SHIPPED v0.9.0 (Package B B5)
> **מומש v0.9.0 (B5):** `GET /api/profile` — call-sign (ב-`user_settings`, נגזר מ-email אם לא הוגדר), כרטיס דרגה + סולם (‏`XP_ECONOMY.md` 1000/3000/8000), "HOW XP IS EARNED" (ארבעת המקורות הנעולים), הגדרות Lens/Risk Style נשמרות (‏`PUT /api/profile/settings`, display+geometry בלבד), sign-out. ⬜ follow-up: התמדת call-sign מ-onboarding S9 (הפרופיל בעליו עם fallback מ-email).

**הגדרות:** **Analysis Lens** (EMA200/RSI/Volume/Full — display only, §3.5.3), **Risk Style** (Conservative/Balanced/Aggressive — output geometry only, §3.5.4), מטבעות מועדפים (בגבולות פלאן), פלטה. **אין** סף-ציון אישי — הלקוח לא משנה מה נחשב הזדמנות (RED LINE §3.5.5).
**שלבי יוקרה (משמעת, לא תדירות):** Newcomer (הרשמה) → Disciplined (X ימי דבקות כולל דילוגים) → Precise (סף XP על משמעת ולמידה — `XP_ECONOMY.md`) → Veteran (ותק+התמדה). **תיקון `XP_ECONOMY.md` §4:** שלבים = XP בלבד, לעולם לא תוצאות what-if; איכות ה-what-if = סטטיסטיקת דשבורד בלבד.
**AC:** AC1: מעמד ממדדי משמעת/XP, **לא** ממספר סריקות/כניסות **ולא** מתוצאות what-if. AC2: עליית שלב = נוטיפיקציה חיובית (לא פוש לסחור).
**אסור (חוסם קוד-רוויו):** מעמד שמתגמל תדירות.

## F6 — Academy (וידאו למידה) — ✅ SHIPPED v0.9.0 (B6 shell) · Academy 2.0 v0.13.0 (Stage 6)
> **מומש v0.9.0 (B6):** מעטפת אקדמיה עם 12 מודולים = 12 ה-`academy` ids ב-`concept_tooltips_content.json`, כל מודול מרונדר את תוכן ה-`what` של המונחים שלו. +100 XP לשיעור רק לתוכן-אמת (≥3 מונחים) — 9 מזכים, 3 stubs=0. plan-gating + מודולי בונוס לפי דרגה.
> **מומש v0.13.0 (Academy 2.0, Stage 6):** מעבר מרשימה קשיחה ל-**טבלת DB `academy_lessons` (mig 033)** — כרטיסי-רשת (card grid) רספונסיביים במקום רשימה, חיפוש+פילטרים בצד-לקוח (סוג/מצב-נעילה/הושלם, AND), **שיעורי וידאו** (URL של YouTube/Vimeo בלבד, ללא העלאות, נגן lazy-embed), ו**ניהול אדמין** מלא (create/edit/reorder-up-down/archive/restore, tags, gating). **שער-כפול (D-AC1):** כל שיעור נושא `min_plan` (free/basic/pro) + `min_rank` (0/1000/3000/8000), שניהם חייבים לעבור — נעילת-דרגה היא **סטטוס** (אתה מחזיק בדרגה), לא "הוצאת XP". שיעור נעול: המטא-דאטה גלויה + סיבת-נעילה בשפה פשוטה ("Unlocks at <rank>" / "Available on <plan> plan"), אך ה**תוכן נשלט-שרת** (‏`GET /api/academy/{slug}` מחזיר 403 לשיעור נעול — D-AC7). **השלמה/XP ללא שינוי:** +100 חד-פעמי לשיעור ב-`xp_events` (source=`academy_lesson`, ref=`slug`) — המיגרציה שומרת כל השלמה קיימת לפי אותו slug (S3 בטוח, ללא נגיעה ב-`xp_events`). archive-not-delete: XP שהוענק לעולם לא נשלל. **תוכן השיעורים עצמו = משימת נדב** (נשלח עם 12 השיעורים הקיימים + מבנה-seed מוכן). ⬜ אין שינוי בכלכלת ה-XP (נעולה).

**תיאור.** YouTube/Vimeo unlisted — איך לקרוא כרטיס, מהו שיפוע EMA7, ניהול סיכון, משמעת. טקסט או וידאו לכל שיעור.
**כלכלת XP (`XP_ECONOMY.md`, נעול 11/07/2026):** השלמת שיעור אקדמיה = **+100 XP** (פעם אחת לשיעור, מלאי סופי). דרגות ה-XP פותחות **מודולי ידע בונוס** בתוך האקדמיה (Spike Autopsies, Regime Transitions) — **אורתוגונלי לשערי הפלאן** (הפתיחה היא תוכן-בונוס, לא הרשאת פלאן). מקורות ה-XP וספי הדרגות המלאים: `XP_ECONOMY.md`.
**AC:** AC1: גישה לפי שער-כפול plan+rank (D-AC1), שניהם חייבים לעבור; שיעור נעול גלוי עם סיבה בשפה פשוטה. AC2: נגן וידאו embed (YouTube/Vimeo), lazy-load; URL לא-תקין נדחה עם שגיאת-אדמין ברורה. AC3: תוכן נשלט-שרת — 403 על fetch ישיר של שיעור נעול (D-AC7). AC4: השלמת שיעור מזכה +100 XP חד-פעמי לשיעור (`xp_events`, unique); השלמה שנייה = 0; אין מסלול XP-כמטבע. AC5: אדמין create/edit/reorder/archive/restore (admin-only, 403); archive מסתיר מהמשתמש בלי לשלול XP. AC6: מיגרציה שומרת כל שיעור+השלמה קיימים (count-match).

## F7 — מנוי, Trial ותשלום — ✅ SHIPPED (trial spine v0.5.0 · Subscribe/B2 v0.8.0 · admin editor B7 v0.9.0 · Decision A + trial fix v0.10.0 shipped 2026-07-13)
> **מומש:** trial 14 יום ללא כרטיס (v0.5.0, TEST mode). עמוד ה-Subscribe (B2, v0.8.0) — עמודות Free/Basic/Pro, **טבלת השוואה חובה** (TC-J-002, Free ראשון+תמיד גלוי), D1 no-card trial CTA + 3 trust shields, "same engine, same threshold", "Continue on Free"; מחירים/מטבעות מ-`system_settings` דרך `GET /api/plans`. עורך ה-settings (‏`system_settings`) ב-B7 (v0.9.0). **Decision A (v0.10.0, shipped 2026-07-13):** Advanced הוסר; הקטלוג הוא Free/Basic/Pro בלבד; Basic ירש את רוחב ה-Advanced (5 מטבעות, כל שכבות הגרף, academy מלא, יומן מלא, ייצוא). migration 029 ממיין כל משתמש `advanced` קיים ל-`basic`. **BUG 3 (v0.10.0):** מגבלת Free 1-scan/day נאכפת כעת בשרת (‏`POST /api/scan/events` → HTTP 429 `DAILY_SCAN_LIMIT`; Free=1/יום, בתשלום=unlimited; admin-editable דרך `scans_per_day_*`; הלקוח מציג מצב מגבלה ידידותי). ⬜ follow-up: Stripe live (keys + webhook secret + `FEATURE_STRIPE_LIVE=true` + chosen `INVOICE_PROVIDER`; PSP switched to Stripe in Stage 3R, v0.16.0), קופונים/referral.

| פלאן | ₪/חודש | מטבעות | ייצוא | Academy | דאשבורד F3 |
|---|---|---|---|---|---|
| **Free** | 0 | 2 (סריקה 1/יום) | — | בסיסי | 7 ימים אחרונים |
| Basic | 59 (PENDING-ACCOUNTANT) | 5 | ✓ | מלא | מלא |
| Pro | 149 (PENDING-ACCOUNTANT) | 10 | ✓ | מלא | מלא |

> **Decision A (נדב 2026-07-13):** Advanced הוסר מהקטלוג; Basic ירש את רוחב ה-Advanced (5 מטבעות, כל שכבות הגרף, academy מלא, יומן מלא, ייצוא). המחירים ₪59/₪149 מסומנים **PENDING-ACCOUNTANT** (טרם אומתו מול רו"ח). migration 029 ממיין משתמשי `advanced` קיימים ל-`basic`.

> **Free tier (D2, נדב 2026-07-09):** מסלול חינמי קבוע — סריקה 1/יום · 2 מטבעות · **Trading Blueprint מלא** · דאשבורד F3 מוגבל ל-7 הימים האחרונים · ללא ייצוא · academy בסיסי. כל המגבלות נשלטות מהאדמין דרך `system_settings` בלי קוד. במסכי paywall/פיצול — אפשרות משנית **"Continue on Free"**.

> **טבלת השוואה Free-מול-בתשלום — חובה בעמוד ה-Subscribe (E3, נדב 2026-07-11):** טבלת ההשוואה המלאה **חייבת להיות מוצגת ללקוח בעמוד ה-Subscribe/paywall** (לא רק בדוקים). שורת ה-Free ("Free forever"): 1 סריקה/יום · 2 מטבעות · Trading Blueprint מלא · יומן (F3) 7 ימים אחרונים · ללא ייצוא — לצד עמודות הפלאנים בתשלום. **AC (paywall):** (a) הטבלה מרונדרת בעמוד ה-Subscribe עם שלושת המסלולים (Free + Basic/Pro, אחרי Decision A); (b) שורת ה-Free מתויגת "Free forever"; (c) הקופי מדויק לתנאי הפלאן — נבדק ע"י copy-guard (ATP TC-J-002).

**Trial (ללא כרטיס — change order, נדב 2026-07-09; CTA fix BUG 4, v0.10.0 shipped 2026-07-13):** הרשמה עם פרטים אישיים בלבד (**ללא כרטיס, ללא tokenization**) → 14 יום Pro מלא → יום 11 תזכורת → **בסוף התקופה בחירה אקטיבית:** פלאן בתשלום (לכידת הכרטיס מתרחשת עכשיו) או המשך ב-Free. **אין חיוב אוטומטי.** **BUG 4 (v0.10.0):** ה-CTA "Start 14 days" באונבורדינג וה-CTA של ה-trial ב-Subscribe קוראים כעת ישירות ל-`POST /api/cardcom/trial` (**ללא כרטיס, ללא מסך checkout/tokenization ל-trial**) ומנחיתים את המשתמש על `/scan` עם TRIAL chip; תזכורת יום 11 נרשמת ב-`notifications_log` (idempotent); פקיעה מורידה ל-Free.
**AC:** AC1: trial מופעל **ללא כרטיס ו-ללא tokenization** בהרשמה. AC2: **אין חיוב אוטומטי** בסוף ה-trial — המשתמש בוחר אקטיבית פלאן בתשלום או Free; לכידת הכרטיס מתרחשת רק ברגע ההמרה לתשלום. AC3: תזכורת ביום 11 (‏`notifications_log`, idempotent). AC4: מגבלות (כולל Free) נשלטות מאדמין בלי קוד. AC5: קופונים.
**מצבי קצה:** לא בחר בסוף ה-trial → נופל אוטומטית ל-**Free** (לא downgrade עם חיוב). ביטול/עזיבה → שאלון יציאה (F9). המרה לתשלום שכרטיסה נכשל → נשאר ב-Free + נוטיפיקציה.

> **Stage 3R (2026-07-14, v0.16.0): PSP switched from Cardcom to Stripe (Stripe Checkout + Billing). The prior Cardcom design is superseded. Israeli tax documents are issued by a provider-agnostic invoice layer (`INVOICE_PROVIDER`), not by Stripe.** The operating entity is an Israeli LTD (in formation), VAT registered.

**✅ SHIPPED (Stage 3R): Stripe billing (v0.16.0):** the payment provider is now **Stripe**. **Checkout** is a hosted **Stripe Checkout Session** per plan (the card never touches our servers) with success/cancel redirect paths; **activation happens ONLY via the signature-verified webhook**, never the browser redirect. **Recurring + retries** are **Stripe Billing / Smart Retries** (the old homegrown recurring-charge + +24h/+72h dunning scheduler was DELETED); our own failure / recovery / cancel emails still fire from the webhook, so the copy stays ours. **Cancel** = Stripe `cancel_at_period_end`, keeping our end-of-period access + churn-survey hook. **Webhook** verifies the Stripe signature and is idempotent by event id (`processed_webhook_events`); handled events: `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `customer.subscription.updated`, `customer.subscription.deleted`. The **internal billing state machine** (`core/billing_state.py`, none/trial/active/past_due/cancelled/expired) SURVIVES as the single source of truth for entitlements, now fed exclusively by Stripe webhooks; entitlements logic is unchanged; one edge added: **active→expired** (involuntary `subscription.deleted`). **Trial stays OURS**: card-free, **NOT a Stripe trial** (Stripe knows nothing about trialing users), expiry via cron. **Israeli tax-invoice layer** (`core/invoice_provider.py`) issues one Israeli tax document per successful charge; provider is config (`INVOICE_PROVIDER`, `mock` default; interface ready for Green Invoice / iCount / EZcount, provider NOT chosen yet); document type default `tax_invoice_receipt`; Stripe's own invoices are NOT Israeli tax documents. **Endpoints** moved to `/api/billing/*` (checkout, trial, webhook, status, cancel). **Env:** `FEATURE_STRIPE_LIVE`, `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `INVOICE_PROVIDER`, `STRIPE_SUCCESS_PATH`, `STRIPE_CANCEL_PATH` (removed all `CARDCOM_*`, `FEATURE_CARDCOM_LIVE`, `DUNNING_RETRY_OFFSETS_HOURS`). DB migration **035** renames columns to Stripe (`users.cardcom_token → stripe_customer_id` + new `stripe_subscription_id`/`card_last4`/`card_expiry`; `payment_transactions.cardcom_tx_id → stripe_reference`, `cardcom_response_json → provider_response_json`; `billing_documents.cardcom_document_id → provider_document_id`; new `processed_webhook_events`; `billing_document_type` default → `tax_invoice_receipt`). **כסף=agorot ints, ILS, מחירים כולל VAT + footnote** (unchanged); Stripe Prices seeded from config by an idempotent script (`backend/scripts/seed_stripe_prices.py`, test mode). **go-live** (Stripe live keys + webhook secret + chosen `INVOICE_PROVIDER` + `FEATURE_STRIPE_LIVE=true` + Railway cron for trial-expiry + lawyer clearance) = משימה ידנית של נדב.

**⤷ Historical record (Stage 3): Live Billing (Cardcom), v0.14.0 (superseded by Stage 3R above; sandbox/mock only, אין טרמינל אמיתי):** לולאת החיוב המלאה מומשה מול Cardcom sandbox/mock, production-ready אך NOT live. **מכונת-מצבים שרתית אחת** (D-B4, `core/billing_state.py`): trial→active (חיוב ראשון) · active→past_due (כשל חיוב חוזר) · past_due→active (retry מוצלח) / →expired (dunning מוצה) · active/trial→cancelled (ביטול משתמש, גישה עד תום התקופה) · trial→Free (פקיעה). **ההרשאות נגזרות מה-state בלבד**; מגבלות reveal-gating/סריקות שומרות את סמנטיקת הפלאן. **checkout**: אישור צד-שרת בלבד (webhook HMAC), tokenization, מסמך חיוב + מייל אישור. **חיוב חוזר** דרך token שמור + **dunning** (retry +24h/+72h, מייל+באנר לכל כשל, מיצוי→Free). **ביטול end-of-period** (D-B6): גישה עד ה-paid-through, ואז Free; מפעיל את שאלון היציאה (F9). **מסמכי חיוב** (D-B3): receipt/invoice-receipt לכל חיוב מוצלח, סוג נשלט-CONFIG (רו"ח), נשלח במייל. **כסף=agorot ints** (D-B10). **מחירים מוצגים ₪ סופי כולל VAT** (D-B2). באנר `past_due` בתוך האפליקציה. **AC (Stage 3):** AC-חיוב: הפעלה רק דרך אישור צד-שרת (redirect לבד לא מפעיל, חתימה פגומה נדחית, callback כפול מעובד פעם אחת); AC-dunning: כשל→past_due+מייל+באנר, retry לפי לו"ז, מיצוי→expired→Free, recovery→active; AC-ביטול: גישה עד תום התקופה ואז Free, שאלון יציאה, ביטול-כפול בטוח; AC-כסף: agorot ints end-to-end, ₪ תקין ב-UI. **go-live** (credentials + מודול חשבוניות + סוג-מסמך של רו"ח + `FEATURE_CARDCOM_LIVE=true` + Railway cron + אישור עו"ד) = משימה ידנית של נדב (SESSION_HANDOFF). קופונים/referral = Stage 4 (עמודות קיימות, inert).

## F8 — חבר מביא חבר — ✅ SHIPPED v0.17.0 (Stage 4, Stripe-native)
> **הכרעת המייסד (2026-07-14, קבועה):** התגמול הוא **חודש חינם אחד** למגייס כאשר החבר המגויס מבצע את **החיוב הראשון בתשלום**. XP אינו מעורב בשום כיוון. המודל הישן (50% הנחה אחרי 3 חודשים + אישור אדמין) בוטל והוחלף.
**תיאור.** לכל משתמש **קוד קבוע** (8 תווים) + קישור שיתוף `/r/<code>`. חבר שנרשם דרך הקישור נקשר פעם אחת (immutable; הפניה-עצמית חסומה לפי id + email). כשהחבר המגויס משלם את חיובו הראשון בפועל (‏`invoice.paid` עם amount>0), המגייס מקבל חודש חינם.
**התגמול (D-S5):** אם המגייס על מנוי Stripe פעיל — **זיכוי יתרת לקוח** (`Customer.create_balance_transaction`, שלילי) בגובה חודש אחד של הפלאן הנוכחי שלו; Stripe מנכה מהחשבוניות הבאות. אם המגייס ב-trial/Free — הזיכוי **מוטמן** (`referral_credits`) ומיושם אוטומטית בחיוב-בתשלום הראשון שלו, לפי הפלאן שירכוש (זיכויים נערמים).
**Flow:** קוד קבוע → חבר נרשם דרך `/r/<code>` (קשירה חד-פעמית) → חיוב-בתשלום ראשון של החבר (amount>0) → זיכוי חודש חינם למגייס (מיידי או מוטמן).
**חודש 100%-קופון:** חיוב ראשון בסך 0 **אינו** מפעיל את התגמול — התגמול נדלק על החיוב הראשון בתשלום בפועל (ייתכן חודש 2).
**Admin (D-S10):** רשימת referrals (מגייס, מגויס, סטטוס, מצב תגמול) + פעולת **void** (מסירה זיכוי מוטמן, או מפרסמת תנועת-יתרה מפצה לזיכוי שכבר יושם; מבוקר). עמודת referrals בטבלת המשתמשים עלתה לספירה אמיתית.
**AC:** AC1: מעקב referrer→referred (קשירה חד-פעמית, immutable). AC2: תגמול = חודש חינם על חיוב-בתשלום ראשון (amount>0), idempotent תחת webhook כפול/לא-מסודר. AC3: זיכוי-יתרת-לקוח למגייס משלם / מוטמן ל-trial/Free (נערם, מיושם בהמרה). AC4: הפניה-עצמית חסומה (id + email). AC5: XP לא מעורב בשום כיוון (asserted).

## F8b — קופונים (Stripe-native) — ✅ SHIPPED v0.17.0 (Stage 4)
**תיאור.** קופון = **Stripe Coupon** (אחוז או סכום קבוע ב-₪, `duration=once` = חיוב ראשון בלבד) + **Promotion Code** מצורף (מחרוזת הקוד שהמשתמש מקליד). האדמין יוצר/משבית מהקונסולה שלנו (מפעיל את Stripe API), עם **שורת-מראה** אצלנו (קוד, פרמטרים, stripe ids, redeemed_count) לרשימות/audit ללא סיבוב ל-Stripe. Redemptions מסונכרנים מה-webhook.
**Checkout (D-S3):** ‏`allow_promotion_codes=true` על ה-Checkout Session — שדה ה-Stripe המתארח מטפל בהזנה/אימות. עמוד ה-checkout שלנו לא בונה שדה קופון משלו. **הגבלת פלאן (D-S1)** נאכפת **אצלנו** (`validate_coupon_for_plan`) לפני יצירת ה-session כשקוד מסופק ל-endpoint שלנו — קוד מוגבל-פלאן על הפלאן הלא-נכון נדחה 400.
**100%-קופון (D-S4):** רץ בזרם ה-Stripe הרגיל (מטמן כרטיס, יוצר מנוי אמיתי; חודש 2 מחייב כרגיל). ללא מסלול-טוקן מיוחד.
**מסמך מס (D-S8):** חשבונית בסך 0 (חודש 100%-קופון, או מחזור שכוסה במלואו בזיכוי) **אינה** מנפיקה מסמך מס ישראלי — שורת audit פנימית במקום.
**AC:** AC1: אדמין יוצר אחוז+קבוע → Stripe (mocked) מקבל פרמטרים נכונים, שורות-מראה נכונות, deactivate עובד, 403 ללא-אדמין. AC2: session נושא allow_promotion_codes; קוד מוגבל-פלאן על פלאן שגוי נדחה אצלנו לפני יצירת ה-session. AC3: webhook redemption מעדכן ספירה; max_redemptions/expiry נאכפים (Stripe + מראה עקבי).

## F9 — דאשבורד מנהל — ✅ SHIPPED v0.9.0 (B7) · v1.1 v0.12.0 (Stage 7)
> **מומש v0.9.0 (B7):** קונסולת אדמין admin-gated (‏`require_admin` → 403). Overview (vitals מדאטת-אמת: users/trials/MRR-מ-plan-prices/scans-day/churn), Users + override פר-משתמש (plan/extend-trial/grant-XP/suspend) עם audit ל-`admin_events` (mig 006), Settings editor (‏`system_settings`; score-gate + card-off מוצגים LOCKED), Broadcast compose+audience(all/plan/trial-ending)+channel → banner in-app (לעולם לא מכסה SCAN/disclaimer), Notifications log. XP source חדש `admin_grant` (audited, לא user-earnable — `XP_ECONOMY.md` §1).
> **מומש v0.12.0 (Stage 7 — Admin v1.1):** טבלת משתמשים מורחבת — עמודות scans total/week, **active-days 7d/30d** (‏ADMIN ANALYTICS בלבד: read-only מ-scan_events, לא user-facing, לא XP, לא gate — D-A1), XP, **rank** (server-side), referrals (ספירה אמיתית, Stage 4 v0.17.0), churn-flag. פילטרים צד-שרת AND (plan/status(trial/active/expired/churned)/signup-range/last-active-range/min_scans) URL-encoded shareable. **CSV export** (view מסונן, admin-only). **Churn survey** נלכד (‏`POST /api/churn/survey` → `churn_reasons`) ומוצג ב-admin (`/api/admin/churn` + flag בטבלה). **Sentry** env-gated (backend+frontend, ללא PII). **Breadcrumbs** לכל טיקט (ראה F10). ⬜ follow-up: email sends = stubs לוגיים (ticket-reply); referral logic (Stage 4).

**מסכים:** לקוחות (כניסה/נטישה/סטטוס/MRR) · churn (שיעור + סיבת עזיבה משאלון יציאה) · טיקטים · ברודקאסט · קופונים · referral approvals · academy · system_settings (סף, מטבעות/פלאן) · beta/waitlist.
**AC:** AC1: MRR מכבד קופונים/trial/הנחות. AC2: churn = שיעור עם חלון. AC3: כל מוטציה ל-admin log. AC4: סף ומטבעות/פלאן נערכים בלי קוד.

## F10 — מערכת טיקטים — ✅ SHIPPED (open v0.8.0 B3 · queue+reply v0.9.0 B7 · breadcrumbs v0.12.0 Stage 7)
> **מומש:** "Report a problem" מגיש טיקט אמיתי (‏`POST /api/support/tickets`, B3 v0.8.0). Queue + thread + reply של האדמין (‏`ticket_replies`, mig 028) + מעברי status (B7 v0.9.0).
> **מומש v0.12.0 (Stage 7):** לכל טיקט מצורף **breadcrumb trail** — 20 האירועים האחרונים בצד-לקוח (route_change/scan_submit/api_error/notif_open, ‏`lib/breadcrumbs.ts` ring buffer), נשמר ב-`support_tickets.breadcrumbs` (mig 032) אחרי **sanitizer allowlist** צד-שרת (‏`core/breadcrumbs.py`). admin ticket view מרנדר timeline (client trail + server events). **RED LINE:** אף ערך תוצאה של יומן לא-חשוף לא נכנס ל-breadcrumbs (allowlist + הלקוח לא מחזיק ערכים כאלה; נבדק). ⬜ follow-up: fan-out מייל = stub לוגי (‏`email_sent` דגל).

**Flow:** לקוח פותח (קטגוריה+תיאור) → מייל למנהל → מנהל עונה → מייל ללקוח → open→resolved.
**AC:** AC1: סטטוסים open/in_progress/resolved/closed. AC2: Resend. AC3: לקוח רואה היסטוריה.

## F11 — נוטיפיקציות + ברודקאסט — ✅ SHIPPED v0.9.0 (banner/log) · v0.11.0 (bell + prefs + real email)
> **מומש v0.9.0 (B7):** ברודקאסט אדמין (audience all/plan/trial-ending + channel) → banner in-app (‏`/api/broadcasts/active`, לעולם לא מכסה SCAN/disclaimer). `notifications_log` (mig 028) רושם את שני ה-system sends המוחלטים בלבד: day-11 trial reminder + journal-reveal teaser.
> **מומש v0.11.0 (Stage 5):** **פיד פעמון in-app** (‏`notifications`, mig 031) בהמבורגר — badge unread server-authoritative (cap "9+"), newest-first, מסמן נקרא בפתיחה, שורד refresh. **העדפות per-user** (‏`notification_prefs`): in-app / sound / vibration / email_product / email_broadcast, נערכות מ-Settings, מכובדות בכל שליחה. **Resend אמיתי** (‏`core/email.py`) עם DEV console-fallback (אפס קריאות רשת בבדיקות). **3 זרמי מייל:** day-11 trial reminder, **reveal-teaser ללא ערכי תוצאה** (pull-only red line), admin broadcast (רק ל-opted-in + unsubscribe חתום חובה — תאימות לחוק הספאם). scheduled sweeps ב-`POST /api/cron/notifications` (‏`CRON_SECRET`, idempotent). **מחוץ ל-scope:** web push/PWA (שלב 8), referral/payment emails (חסומים).

**תיאור.** מערכתיות (חיוב/טיקט/וידאו/שלב יוקרה) + ברודקאסט מנהל.
**אסור:** "מטבע X עבר סף, היכנס!". reveal-teaser לעולם ללא ערך תוצאה. אין פוש יזום לסחור (trust-not-engagement §3.3).
**AC:** AC1: מערכתיות בלבד. AC2: in-app (פעמון) + email (opt-in). AC3: ברודקאסט ל-admin log + unsubscribe חובה. AC4: prefs מכובדות (inapp_enabled=0 → אין שורות פעמון; email opt-out → אין מייל). AC5: reveal-teaser deduped ו-content-free.

## F12 — שאלון Onboarding עריך
**AC:** AC1: נשמר ב-onboarding_responses. AC2: לקוח יכול לעדכן. AC3: מנהל עורך שאלות בלי קוד.

## F13 — "First 60 Seconds" — סימולציית Onboarding — ✅ SHIPPED v0.6.0 (+ validation v0.7.0 / v0.7.1)
> **מומש:** מנוע האפיזודות (mig 023, seed מנרות Bybit אמיתיים עם assertions של אמת אמפירית; E1 נבחר-מחדש LINK→BTC 25/06), 12 המסכים S0–S11 + ענף S1a, XP צד-שרת (mig 024, מענק חד-פעמי 300), funnel (mig 025), withholding צד-שרת. Concept Tooltips (F14) חוברו ב-v0.7.0. הגרפים מרונדרים **in-app כ-SVG** (‏EpisodeChart) — לא recharts, כדי להימנע מ-peer-dep של React 19 (SPEC §5.8; החלטה פתוחה — revert ל-recharts אם נדב מעדיף). ⬜ פתוח: click-through ידני + ליטוש חזותי (Design סבב 2), OAuth SDK ל-Google/Apple.

**תיאור.** זרימת סימולציה לימודית של ~60 שניות **לפני** ההרשמה, על **אפיזודות אמת מתוארכות** (Episode Library, SPEC §5.5): trap → SCAN → empty-state ("No setups pass") → discipline-save → valid-setup → הרשמה → trial ללא כרטיס / Free. **משלים** את F12 (השאלון) — לא מחליף. מקור אמת מלא: **`FINARODA_ONBOARDING_SPEC.md` (v1.1)**.
**עקרונות (נאכפים):** אמת אמפירית בלבד (§3 principle 8) — כל מספר מאפיזודה מאומתת, אפס סטטיסטיקות מומצאות; טרמינולוגיה קנונית (§3.5.1 — Trading Blueprint, PASS/WATCH, "Analysis, not financial advice"); אנימציית 4 השלבים הנעולה; גרפים מרונדרים מ-kline דרך recharts (לא צילומי TradingView/Bybit); XP באונבורדינג בלבד (D3, ראו §17 open items); UI אנגלית.
**AC:** AC1: הסימולציה רצה על `episodes` אמיתיות בלבד. AC2: כל קופי מתויג "Analysis, not financial advice", אין "איתות/המלצה/קנה-מכור" מחוץ לכפתורי הסימולציה. AC3: הרשמה ללא כרטיס; ה-trial מופעל אקטיבית (F7). AC4: אין קנס XP על BUY/SELL; XP רק על SCAN/שיעור.
**Design:** סבב 2 (ROADMAP X1) — 12 המסכים לפי `FINARODA_ONBOARDING_SPEC.md` §3.

## F14 — Concept Tooltip ("What's this?") — F-education (E1, נדב 2026-07-11) — ✅ SHIPPED v0.7.0
> **מומש v0.7.0:** קומפוננטת ConceptTooltip אחת משותפת, מחוברת ל-`concept_tooltips_content.json` (root, נעול, 46 מונחים) עם מנוע `now`-template (placeholder חסר → ריק בחן). בועה viewport-clamped/flips (לא נחתכת במובייל), X + סגירה בהקשה בחוץ. pytest drift-guard מאמת שהעותק ב-frontend זהה ל-root. deep-link "Learn more" → `/academy#<id>` (מומש ב-B6, v0.9.0). בשימוש באונבורדינג + Trading Blueprint + non-passer why-not.

**תיאור.** קומפוננטת בועת-לימוד **אחידה** על **כל מונח מקצועי, מהאונבורדינג ואילך** — EMA7 slope, PASS/WATCH, Mathematical Trigger Point, Calculated Risk Level, R:R, volume וכו'. לחיצה/ריחוף על מונח → בועה קצרה בשפה פשוטה. **מקור התוכן: האקדמיה (F6)** — אותו גוף ידע, לא כפילות; הבועה היא תמצית + קישור "Learn more" לשיעור המלא.

**Flow:** מונח מוצג עם אינדיקטור עדין (מקווקו/אייקון "?") → פתיחה → תמצית (1-2 משפטים מהאקדמיה) → קישור אופציונלי לשיעור.

**AC:**
- AC1: קומפוננטה **אחת** משותפת בכל ה-surfaces (onboarding, scan, Trading Blueprint, dashboard, profile) — לא מימוש-פר-מסך.
- AC2: תוכן נשאב מהאקדמיה (F6) — אין טקסט לימודי מפוברק/כפול; מונח בלי ערך אקדמיה → אין בועה (לא placeholder ריק).
- AC3: פריסה מדורגת — מונחים חדשים מקבלים בועה ברגע החשיפה הראשונה למשתמש.
- AC4: display-only, חינוכי — **אינה** נוגעת בציון/סף/לוגיקה (עולה בקנה אחד עם RED LINE §3.5.5 ועם "ניתוח לא ייעוץ").
**UX:** ראו UX §3 (בתוך ה-Trading Blueprint) + §8 (אינטראקציה). **Design:** סבב 2 (ROADMAP X1).

## F15 — Live Chart + Explanation Overlays (per scanned coin) (E7, נדב 2026-07-11) — ✅ SHIPPED v0.8.0 (Chart Standard v1)
> **מומש v0.8.0 (B1):** גרף לכל מטבע נסרק כ-**Chart Standard v1** (רכיב אחד, `BlueprintChart`) עם EMA200+EMA7, swing S/R, רמות ה-Blueprint, candle-tap OHLC ו-annotation tooltips. **layer gating** נשלט-אדמין: Free = chart + EMA200 בלבד (‏`chart_layers_free='ema200_only'`) + "SEE PLANS"; בתשלום = כל השכבות (‏`chart_layers_*='full'`). ⚠ **מרונדר in-app כ-SVG** (לא recharts) — עקבי עם EpisodeChart של האונבורדינג (SPEC §5.8); recharts נשאר dependency רשום. **E7b (מומש v0.8.0):** כל מטבע נסרק — **כולל non-passers** — לחיץ → אותו גרף + שורת "why not" בשפה פשוטה המנקבת רק את ה-check החוסם (regime = price vs EMA200, אחרת הסף) עם Concept Tooltip; אין חשיפת ציון/משקל/נוסחה. **Decision D (v0.10.0, shipped 2026-07-13), paid "why not" enrichment:** בהקשה על מטבע שלא עבר, פלאנים בתשלום רואים את **המספרים בפועל** מאחורי ה-check החוסם (למשל price מול EMA200 ב-%, שיפוע EMA7, יחס volume); Free רואה את ה-why-not הפשוט בלבד. **אין חשיפת משקלים/נוסחאות** (RED LINE §3.5.5).

**תיאור.** לכל מטבע שנסרק — גרף חי (מרונדר מ-kline **in-app כ-SVG** — לא צילום TradingView/Bybit, ולא recharts; ראו SPEC §5.8) עם **שכבות הסבר** מוסברות (overlays). gating לפי פלאן:

| פלאן | שכבות גרף |
|---|---|
| **Free** | גרף + EMA200 בלבד |
| בתשלום (Basic/Pro) | **כל השכבות** — EMA7, רמות ה-Blueprint על הגרף (Mathematical Trigger Point / Calculated Risk Level / Calculated Target Level) |

**AC:**
- AC1: הגרף מרונדר client-side מ-kline (in-app SVG, Chart Standard v1) — לעולם לא צילום מסך חיצוני.
- AC2: gating נשלט-אדמין דרך `system_settings` (כמו שאר מגבלות הפלאן) — Free = chart+EMA200, בתשלום = כל השכבות.
- AC3: השכבות הן **הצגה בלבד** — אינן משנות ציון/סף/כניסה (RED LINE §3.5.5); overlays מלווים בהסבר חינוכי (משיק ל-F14).
- AC4: תיוג "Analysis, not financial advice." נשמר.
**UX:** ראו UX §3. **Design:** סבב 2 (ROADMAP X1).

## V2 (מתועד, לא MVP)
"Copy to LLM" · PWA push · daylight light-mode · סבב Design למסכים שלא עוצבו · **ניתוח מטבע חופשי מעבר ליקום 10 המטבעות המאומת (E2, נדב 2026-07-11):** בפלאנים בתשלום בלבד, **אחרי** ולידציה ואישור נדב, עם **תווית חובה "Learning mode — outside the validated universe"** על כל תוצאה מחוץ ליקום. **לא v1** — היקום המאומת (10 מטבעות) נשאר הבסיס לסף ול-base-rate · **POSITION horizon (weeks+) — מימוש מודל ה-position (E9, F1c):** מנוע position-trading נפרד + סף/base-rate משלו, נפתח רק אחרי 30+ תוצאות/2+ משטרים; מועמד לפיצ'ר Pro. **בלוק v1** מציג את הבקר נעול בלבד (ראו F1c) — המנוע עצמו הוא V2+ ועשוי לעולם לא להיפתח.

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
חיבור Bybit/מסחר אוטומטי · רישום פוזיציות אמיתי · LLM בליבה · שכבת הקריירה/Jobby (נמחקת) · אחסון וידאו מאובטח. (Stripe הוא ה-PSP מ-Stage 3R, v0.16.0, ואינו עוד out of scope.)

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
**3 פלאנים Free/Basic/Pro (Decision A, 2026-07-13, Advanced הוסר, Basic ירש את רוחבו): Basic ₪59 / Pro ₪149 (PENDING-ACCOUNTANT) + Free ₪0** · מטבעות 2/5/10 (Free/Basic/Pro) נשלט-אדמין · **trial ללא כרטיס (2026-07-09)** · referral 50%/3-חודשים+אישור · UI אנגלית · PSP = Stripe (Stage 3R, v0.16.0; מסמכי מס דרך `INVOICE_PROVIDER`) · YouTube וידאו · מנוע JS משותף · פלטה terminal · פריסה ring/list · אנימציה log · **סף 85 PASS / 82-84 WATCH** · קהל בוני-הון · **F13 onboarding simulation (spec = `FINARODA_ONBOARDING_SPEC.md` v1.1)** · **(v2.1) calculator terminology (§3.5.1) · formula transparency (§3.5.2) · Analysis Lens display-only (§3.5.3) · Risk Style output-only via `computeSlTp` opt (§3.5.4) · RED LINE: client never touches score/weights/edge/threshold (§3.5.5) · per-user score threshold removed**.

### פריטים פתוחים (open items)

**Implementation follow-ups (Package B, v0.9.0 — מ-SESSION_HANDOFF):**
- **resolve-scenarios cron** — job ה-resolution של F3 צד-שרת ולא auto-run; יש לחווט את ה-cron בפריסה (`python -m backend.scripts.run_resolve_scenarios`, יומי). עד אז תרחישי `pass` נשארים `open` והיומן לא נחשף.
- **call-sign persistence** — ה-call-sign בבעלות הפרופיל (‏`user_settings`) עם fallback מ-email; חיווט onboarding S9 → `PUT /api/profile/settings` הוא follow-up קטן שטרם בוצע.
- **email** — ✅ **v0.11.0:** day-11 reminder, reveal-teaser ו-broadcast email עברו ל-Resend אמיתי (‏`core/email.py`, DEV console-fallback). **נותר stub:** ticket-reply email fan-out (‏`ticket_replies.email_sent`) — לא בטווח Stage 5. **חוסם go-live לשליחה חיה:** אימות דומיין `finaroda.com` ב-Resend (‏hardening/שלב 8) + הגדרת `RESEND_API_KEY`/`CRON_SECRET` וחיווט Railway cron (‏SESSION_HANDOFF).
- **fonts** — IBM Plex Mono / Space Grotesk מיוחסים דרך CSS font-family אך לא self-hosted/imported → fallback ל-system mono. טעינה = Design סבב 2.
- **Free 1-scan/day enforcement** - ✅ נאכף בשרת (BUG 3, v0.10.0 shipped 2026-07-13): `POST /api/scan/events` דוחה מעל המכסה עם HTTP 429 `DAILY_SCAN_LIMIT` (Free=1/יום, בתשלום=unlimited); admin-editable דרך `scans_per_day_*`; הלקוח מציג מצב מגבלה ידידותי.
- **admin mobile layout** — קונסולת האדמין (B7) desktop-first, ללא layout מובייל.
- **charts = in-app SVG (not recharts)** — EpisodeChart + Chart Standard v1 מרונדרים כ-SVG; recharts נשאר dependency רשום. החלטה פתוחה — revert ל-recharts אם נדב מעדיף.

**Product/decision open items:**
- **POSITION honesty guardrail (F1c AC2)** — הבקר נעול מרונדר; קופי "in validation" אמיתי רק כשקיים מודל POSITION שרושם תוצאות ל-`score_log`. ⬜ הכרעת נדב: לבנות position-outcome log לפני הצגת הקופי, או לרכך ל-future-tense.
- **CAPITAL SAVES non-passer variant (F3)** — המימוש = SAVE כ-PASS שה-trigger לא נורה; שורת ה-SAVE הפר-מטבע-לא-עובר (פריים B4) = הרחבה עתידית, טעונה אישור נדב.
- **XP economy pending** — conflict with UX §9.4 under discussion (proposed: +XP on first scan of the day only). כלכלת ה-XP הנעולה = `XP_ECONOMY.md` v1.0; מומשו 4 מקורות (`daily_first_scan` +50 · `academy_lesson` +100 · `journal_reveal_viewed` +25 · `onboarding` 300) + `admin_grant` audited. לא מטבע רכישה, לא תגמול על רווח, זהה בכל הפלאנים.
- **Free tier — הגדרה סופית** (2/יום? מגבלות מדויקות) נשלטת `system_settings`; הערכים בטבלת F7 הם ברירת מחדל מאושרת, כיול פתוח לאדמין.

### פריטים שנדחו (REJECTED)
- **באנר טיקר רץ (running ticker banner) — ❌ נדחה (E8, נדב 2026-07-11).** באנר מחירים רץ למטבעות/מדדים/סחורות נדחה משתי סיבות: (1) **סותר trust-not-engagement** (§3 principle 3) — טיקר רץ הוא מכאניקת engagement/תנועה מתמדת שדוחפת מבט-מסך ותדירות, ההפך מדיוק ודילוג; (2) **רישוי דאטה** — נתוני מדדים/סחורות בזמן-אמת דורשים רישוי מסחרי (בניגוד ל-Bybit הציבורי-חינמי למטבעות). **החלופה המאושרת:** שורת `marketContext` **סטטית פר-סריקה** (כבר קיימת — coinChanges/mean/std הנבנית בכל סריקה). **פתיחה מחדש אפשרית רק** כ-opt-in כבוי-כברירת-מחדל בהגדרות (לא כברירת מחדל, לא רץ).

## 18. סדר בנייה (פאזות)
P0 ניקוי → P1 תשתית (Stripe/auth/deploy) → P2 ליבה (F1/F1b/F2) → P3 למידה (F3/F5) → P4 מסחרי (F7/F8/F4) → P5 מנהל+קהילה (F9/F10/F11/F12/F6) → V2.

---

_PRD v2.0 — מפורט, מעוגן בעיצוב המאושר. לאישור נדב. אחרי אישור → repo כמקור אמת לצד SPEC/UX/LEGAL._
