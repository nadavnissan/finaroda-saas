# SESSION HANDOFF — FINARODA SaaS

> מוחלף בסוף כל סשן. מסמך "איך להיכנס", לא ארכיון.

---

## איפה אנחנו עכשיו
- **Branch פעיל:** dev
- **Commit אחרון:** <hash> — P1.5 scoring-engine placeholder (על גבי P0)
- **מצב validation:** ✅ ירוק מלא — pytest 3/3, node --test (shared) 3/3, tsc clean, eslint clean, uvicorn boot (health 200), next build (13 routes)
- **Production (main):** ריק / לא נפרס עדיין. **לא מוזג ל-main — נדב ממזג ידנית.**

## מה נעשה בסשן האחרון (P0 — ניקוי והקמת שלד נקי)
- הוקם שלד FINARODA נקי **מאפס** (השורש היה ריק מקוד — ראו "החלטות" למטה).
- Backend (FastAPI): config.py נקי, main.py (health + Cardcom placeholder), logging, requirements ללא תלויות קריירה.
- 18 migrations נקיות על internal_id (סכמה בלבד) — תשתית מודרנית + 4 טבלאות FINARODA חדשות (scan_events/score_log/decision_snapshots/support_tickets).
- תשלום יחיד: Cardcom placeholder (api/cardcom.py + core/cardcom_service.py). אין Morning/Stripe/legacy/Telegram.
- Frontend (Next.js 15): route groups (scan)/(dashboard)/(admin)/(academy)/(auth) + checkout/paywall/legal/coming-soon — placeholders בלבד.
- אותחל git repo ייעודי בתוך finaroda-saas על dev (ראו החלטה #1).

## מה נעשה אחרי P0 (P1.5 — תשתית מנוע הסריקה)
- נוצרה `shared/` עם **placeholder בלבד** ל-`scoring-engine.js` (חתימות: ema7Slope, scoreDirection, computeReversalAnchor, computeSL, computeTP — כולן מחזירות sentinel `TODO`) + `scoring-engine.api.md` (חוזה) + `scoring-engine.test.js` (node:test) + `package.json` (type:module).
- **🟡 ממתין לחילוץ:** המימוש האמיתי של `scoring-engine` עדיין שזור בכלי האישי (React מקומפל). **נדב יספק אותו.** אין להמציא מנוע ואין להתחבר ל-Bybit עד אז. צ'ק-ליסט חילוץ ב-`shared/scoring-engine.api.md`.

## הצעד הבא — P1 (תשתית חיה)
לפי SPEC §11:
- חיבור Cardcom v11 מלא (credentials + LowProfile/Create + ChargeToken + webhook HMAC + trial tokenization).
- פורט auth מ-hamakpetza **עם הקשחות SPEC §4** (revocation/jti, hash ל-magic-link, הסרת dev-secret בפרוד, אכיפת aud/iss ב-Google, admin כתפקיד DB דרך users.is_admin).
- פורט שכבת התשתית (storage R2, email Resend, beta gate/waitlist, academy, admin).
- deploy Railway + nixpacks + Litestream + CI (pytest+tsc) — לא נכלל ב-P0.

## פתוחים / חוסמים
- **🔴 חוסם push:** אין remote (`origin`) מוגדר. ה-commit מקומי על dev בלבד. נדב צריך ליצור repo finaroda-saas ב-GitHub ולהגדיר remote לפני push (CLAUDE.md §2.8).
- **⚠️ git של הבית:** קיים repo מושרש בטעות ב-C:\Users\rodan (branch master, ללא commits). לא נגעתי בו. כדאי שנדב יבדוק/ינקה אותו בנפרד.
- אישור PRD מנדב; אישור עו"ד ל-LEGAL; אימות מחירים מול רו"ח; פלט Claude Design ל-UX.

## מוכן ל-production מחכה לאישור
- **P0 הושלם על dev.** ממתין לאישור נדב למיזוג ל-main + הגדרת remote + התחלת P1.

---

## תזכורת Branch Gate
Claude עובד על dev בלבד. נדב ממזג dev→main ידנית. אסור ל-Claude לגעת ב-main.

## איך מריצים מקומית
- Backend: `.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --port 8000`
- Frontend: `cd frontend && pnpm dev`
- Validation: `.venv/Scripts/python.exe -m pytest` · `cd frontend && pnpm typecheck && pnpm lint`
