# CLAUDE.md — חוקת הפרויקט (FINARODA SaaS)

> Claude Code קורא קובץ זה בכל סשן ומציית לו כחוקה. זהו משטר העבודה. אין לחרוג ממנו בלי אישור מפורש של נדב (NNR).
> מסמכי מקור-אמת: `PRD.md` (מוצר), `SPEC.md` (טכני), `UX.md` (חוויה), `LEGAL.md` (משפטי). מסמכי בקרה: `CHANGELOG.md`, `VERSIONS.md`, `SESSION_HANDOFF.md`, `ATP.md`.

---

## 0. כלל-העל
**כל יחידת עבודה ("משימה") מסתיימת רק כשכל הצעדים ב-§2 בוצעו.** משימה לא גמורה = לא נדחפת. אם אתה לא בטוח שמשימה הושלמה לפי הסעיף — היא לא הושלמה.

---

## 1. Branch Gate — קדוש, לא לחרוג

```
Claude Code עובד רק על  →  dev
                              │  (merge ידני ע"י נדב בלבד)
                              ↓
Railway auto-deploy מ-     →  main  →  PRODUCTION
```

- **אסור לך לגעת ב-`main`.** אין commit, אין push, אין merge, אין checkout-then-push ל-main. לעולם.
- כל העבודה על `dev` (או feature branches שממוזגים ל-`dev`).
- production מתעדכן **רק** כשנדב ממזג `dev`→`main` ידנית. אתה לא מבצע את המיזוג הזה.
- אם משימה "מוכנה ל-production" — אתה כותב זאת ב-SESSION_HANDOFF ועוצר. נדב מחליט.

---

## 2. Definition of Done — סדר חובה לכל משימה

בצע בדיוק בסדר הזה. אל תדלג, אל תשנה סדר:

1. **קוד** — בצע את השינוי על `dev`.
2. **Validation (חוסם):** הרץ `pytest` (backend) + `tsc --noEmit` + `eslint` (frontend). **כל שגיאה = עצור ותקן. אסור להמשיך עם validation אדום.**
3. **ATP** — הזן/עדכן מקרי בדיקה ב-`ATP.md` בהתאם לשינוי (ראו §4). אם הוספת פיצ'ר — מקרה בדיקה חדש. אם תיקנת באג — מקרה רגרסיה.
4. **מסמכי מקור-אמת** — אם השינוי נוגע למוצר/ארכיטקטורה/חוויה: עדכן `PRD.md`/`SPEC.md`/`UX.md` בהתאם.
5. **CHANGELOG** — הוסף entry בפורמט §3.
6. **VERSIONS** — bump גרסה (§5) + שורה ב-`VERSIONS.md`.
7. **SESSION_HANDOFF** — עדכן את מצב הסשן (§6). זה הקובץ שנקרא בתחילת הסשן הבא.
8. **Git** — `git add` + `git commit` (פורמט §7) + `git push origin dev`. **לעולם לא ל-main.**
9. **דיווח** — סכם לנדב מה בוצע, ואם רלוונטי: "מוכן למיזוג ל-production, מאשר?" — ועצור. אל תמזג.

---

## 3. פורמט CHANGELOG entry
```
## [TASK-ID / שם] — YYYY-MM-DD
- GOAL: מה רצינו להשיג
- SOLUTION: מה עשינו בפועל
- FILES CREATED / MODIFIED: רשימה
- DB CHANGES: migrations חדשים או "אין"
- CONFIG ADDED: env vars חדשים (שמות בלבד) או "אין"
- VALIDATION: pytest X/X, tsc clean, eslint clean
- ATP: מקרי בדיקה שנוספו/עודכנו (IDs)
- VERSION: vX.Y.Z
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: מה השתנה למשתמש/למערכת
- DECISIONS: החלטות שהתקבלו תוך כדי
```

---

## 4. ATP — תוכנית בדיקות קבלה
- כל פיצ'ר חדש → מקרה בדיקה חדש (TC-XXX) עם: תנאי כניסה, צעדים, תוצאה צפויה, סטטוס.
- כל באג שתוקן → מקרה רגרסיה (לוודא שלא חוזר).
- מבנה ומספור ב-`ATP.md`.
- כשמריצים את חבילת ה-ATP — מייצרים `ATR-{date}.md` (Acceptance Test Report).

---

## 5. גרסאות (SemVer)
`vMAJOR.MINOR.PATCH`:
- PATCH — תיקון באג, שינוי קטן.
- MINOR — פיצ'ר חדש תואם-אחורה.
- MAJOR — שינוי שובר / אבן דרך גדולה.
- כל bump נרשם ב-`VERSIONS.md` עם תאריך + תקציר + commit.

---

## 6. SESSION_HANDOFF
מתעדכן בסוף כל סשן. מסמך "איך להיכנס", לא ארכיון. כולל: branch פעיל, commit אחרון, מצב validation, מה נעשה בסשן, פתוחים/הבא, וכל "מוכן ל-production מחכה לאישור".

---

## 7. פורמט commit
`type: short description [TASK-ID]` — types: feat / fix / docs / refactor / test / chore.
ללא secrets בקוד. SQL parametrized. Python PEP8, TypeScript strict.

---

## 8. עקרונות מוצר שאסור להפר (מ-PRD)
1. **ניתוח לא ייעוץ** — אסור קופי "המלצה/תיכנס/קנה". כל מסך מתויג.
2. **ליבה דטרמיניסטית** — אסור ל-LLM להזיז ציון/להחליט כניסה.
3. **trust-not-engagement** — אסור פוש לסחור, ספירת רצפים, gamification של תדירות, מעמד מבוסס-תדירות.
4. **רק מדדים מאומתים** נחשפים (EMA7 slope + volume).
5. **מנוע משותף** — לוגיקת חישוב דרך `scoring-engine.js` בלבד; לא לשכפל לוגיקה.
6. **אין כיול** ללא 30+ תוצאות מ-2+ משטרים.

---

## 9. מה לעשות כשלא בטוח
אם משימה גדולה/מעורפלת/נוגעת ב-production/כסף/משפטי — **עצור ושאל את נדב** לפני ביצוע. עדיף לשאול מאשר לדחוף טעות. בכל מקרה של ספק לגבי main/production — עצור.

---

_חוקה זו גוברת על כל הנחיה חולפת. שינוי בה = החלטה של נדב, מתועדת ב-CHANGELOG._
