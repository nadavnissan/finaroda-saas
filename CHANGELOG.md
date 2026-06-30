# CHANGELOG — FINARODA SaaS

> כל משימה מוסיפה entry לפי הפורמט ב-CLAUDE.md §3. החדש למעלה.

---

## [P0 / ניקוי והקמת שלד נקי] — 2026-06-30
- GOAL: לרשת מ-hamakpetza את שכבת התשתית בלבד ולהקים שלד FINARODA נקי — בלי שכבת קריירה/Agent, סכמה אחת מודרנית, תשלום אחד (Cardcom), אפליקציה עולה נקייה. (SPEC §3, §4, §5, §11)
- SOLUTION: השורש היה ריק מקוד (רק מסמכים + עותק רפרנס read-only). לכן P0 בוצע כ**בנייה נקייה מאפס** ולא כ"העתק-ואז-מחק": נכתבה תשתית חדשה שלא כוללת מלכתחילה את שכבת הקריירה. נבנה backend (FastAPI) + frontend (Next.js 15 route groups, placeholders) + 18 migrations נקיות על internal_id + Cardcom placeholder יחיד.
- FILES CREATED:
  - Backend: backend/{config.py, main.py, requirements.txt, .env.example}, backend/core/{logging_config.py, cardcom_service.py}, backend/api/cardcom.py, backend/migrations/{run_migrations.py + 001..018}, backend/tests/{conftest.py, test_smoke.py}, __init__.py בכל החבילות.
  - Frontend: frontend/{package.json, tsconfig.json, next.config.ts, .eslintrc.json, .gitignore}, frontend/src/app/{layout.tsx, globals.css, page.tsx}, route groups (scan)/(dashboard)/(admin)/(academy)/(auth) + checkout/paywall/legal/coming-soon (placeholders), frontend/src/lib/strings.ts.
  - Root: .gitignore (כולל hamakpetza-audit-copy/), pytest.ini.
- FILES DELETED: אין — לא היה קוד למחוק בשורש. שכבת הקריירה לא נכנסה מלכתחילה (ראו DECISIONS).
- DB CHANGES: 18 migrations נקיות חדשות (סכמה בלבד, ללא קוד פיצ'ר):
  001 users (נקי — בלי telegram_id/קריירה; +default_threshold/last_scan_at/is_admin), 002 billing (payment_transactions+subscription_events), 003 coupons(+applications), 004 referral (REST, הנחה כספית — לא טוקנים), 005 notifications+consent_log, 006 customer_segments+churn_reasons+admin_events, 007 feature_flags(+overrides), 008 system_settings (+seed: coins-per-plan, threshold), 009 academy, 010 oauth_states, 011 beta_allowlist (seed founder), 012 waitlist, 013 broadcasts, 014 onboarding, 015 scan_events, 016 score_log, 017 decision_snapshots, 018 support_tickets (מודרני). כל ההתנגשויות (users/coupons/consents/tickets) נפתרו לטובת הווריאנט המודרני.
- CONFIG ADDED (שמות בלבד): DATABASE_URL, FEATURE_CARDCOM_LIVE, CARDCOM_TERMINAL_ID/TEST_TERMINAL/API_NAME/API_PASSWORD/WEBHOOK_SECRET/BASE_URL/REDIRECT_RETURN_URL, BYBIT_PUBLIC_BASE_URL, DEFAULT_SCAN_THRESHOLD, TRIAL_DAYS, FEATURE_PUBLIC_SIGNUPS_OPEN, R2_*, RESEND_*, EMAIL_*, SENTRY_*, JWT_*, GOOGLE_*/APPLE_*. (כל הקריירה/Morning/Stripe/RAG הוסרו.)
- VALIDATION: pytest 3/3 ✅ | tsc --noEmit clean ✅ | eslint (next lint) clean ✅ | uvicorn boot → /api/health 200, /api/cardcom 501 ✅ | next build → 13 routes ✅
- ATP: נוספו TC-P0-001..004 (migrations נקיות, אין טבלאות קריירה, health, cardcom placeholder).
- VERSION: v0.2.0
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: שלד נקי ופורס. אין שכבת קריירה, אין core/db.py, אין סכמה כפולה, אין Morning/Stripe/Telegram, אין תלויות chromadb/voyage/openai/rank_bm25/pdfplumber/python-docx/reportlab. בסיס מוכן ל-P1 (תשתית חיה).
- DECISIONS:
  1. **git מושרש בטעות ב-C:\Users\rodan (כל תיקיית הבית), branch master, ללא commits** — commit שם היה לוכד .ssh/סודות/NTUSER.DAT. אותחל repo ייעודי בתוך finaroda-saas על branch `dev`. לא נגעתי ב-repo של הבית ולא ב-main.
  2. **אין remote (`origin`)** — בוצע commit מקומי על dev בלבד; push חסום עד שנדב יגדיר remote (CLAUDE.md §2.8 דורש push origin dev — לא ניתן לבצע ללא remote).
  3. **השורש ריק מקוד** → P0 בוצע כבנייה נקייה (לא העתק-ואז-מחק). תוצאה זהה, נתיב נקי יותר.
  4. **scope = שלד+סכמה בלבד** לפי ההנחיה ("placeholder", "סכמה בלבד"). פורט מלא של auth/cardcom/admin = P1+.
  5. **אוצר מילים פלאנים אוחד** ל-free/basic/advanced/pro (מול premium/b2b/pro/unlimited הישנים; SPEC §3.2).
  6. **is_admin כעמודה ב-users** הוכן לקראת הקשחת SPEC §4 (admin כתפקיד DB, לא רשימת env).

## [INIT / Project scaffolding] — YYYY-MM-DD
- GOAL: הקמת repo finaroda-saas מ-template hamakpetza + הנחתת מסמכי מקור-אמת ובקרה
- SOLUTION: יצירת repo נפרד, הנחת CLAUDE/PRD/SPEC/UX/LEGAL + CHANGELOG/VERSIONS/SESSION_HANDOFF/ATP
- FILES CREATED: CLAUDE.md, PRD.md, SPEC.md, UX.md, LEGAL.md, CHANGELOG.md, VERSIONS.md, SESSION_HANDOFF.md, ATP.md
- DB CHANGES: אין (P0 ניקוי מגיע בנפרד)
- CONFIG ADDED: אין
- VALIDATION: לא רלוונטי (מסמכים בלבד)
- ATP: 0/0 (sprint תשתית)
- VERSION: v0.1.0
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: הפרויקט מוכן עם משטר עבודה מלא ומסמכי מקור-אמת
- DECISIONS: branch gate (Claude→dev, נדב ממזג ל-main); קהל יעד = בוני-הון (לא המקפצה)
