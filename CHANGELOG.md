# CHANGELOG — FINARODA SaaS

> כל משימה מוסיפה entry לפי הפורמט ב-CLAUDE.md §3. החדש למעלה.

---

## [P1 / תשתית חיה — auth + Cardcom + deploy] — 2026-07-01
- GOAL: לחווט את שכבת התשתית החיה על גבי השלד הנקי — auth מלא ומוקשח, Cardcom v11 ב-TEST mode, קונפיג deploy ל-Railway, וחיבור frontend בסיסי. בלי פיצ'רים, בלי חיוב אמיתי, בלי פריסה חיה. (SPEC §3.1, §4, §9, §11)
- SOLUTION: פורט דפוסי התשתית מ-hamakpetza (רפרנס read-only) והותאמו לסכמה הנקייה + הקשחות SPEC §4. שכבת קריירה לא נגעה.
- FILES CREATED:
  - Auth: backend/core/{auth.py, database.py, google_oauth.py, apple_oauth.py, email.py}, backend/api/{auth.py, waitlist.py}, backend/models/{auth.py, cardcom.py}.
  - Cardcom: backend/core/cardcom_service.py (חווט מלא: initiate/webhook/ChargeToken/trial/renewal/expire), backend/api/cardcom.py (initiate/webhook/status/cancel — הוסר 501).
  - Crons: backend/app/tasks/billing_tasks.py + backend/scripts/run_{expire_trials,subscription_renewal,trial_ending_soon}.py.
  - Deploy: railway.toml, nixpacks.toml, litestream.yml, Dockerfile.
  - Frontend: src/lib/api.ts + דפי login/verify/coming-soon/paywall/checkout(success,cancelled) מחוברים ל-endpoints; frontend/.env.example.
  - Tests: backend/tests/test_p1_auth_billing.py (12 מקרים).
- FILES MODIFIED: backend/{config.py, main.py, .env.example, api/cardcom.py, core/cardcom_service.py}, backend/tests/{conftest.py, test_smoke.py}, frontend placeholders → wired.
- DB CHANGES: migration 019 — users.billing_failure_count + seed מחירי 3 פלאנים ב-system_settings (basic 5000 / advanced 10000 / pro 15000 agorot) + trial_days.
- CONFIG ADDED (שמות בלבד): ADMIN_BOOTSTRAP_EMAILS (החליף ADMIN_USER_IDS). Cardcom/Google/Resend/R2 כבר קיימים כ-placeholders. **FEATURE_CARDCOM_LIVE=false נשאר — TEST mode.**
- VALIDATION: pytest 16/16 ✅ | tsc clean ✅ | eslint clean ✅ | next build 16 routes ✅ | uvicorn boot (health 200, auth/me 401, cardcom 401, waitlist 200) ✅ | shared node --test 8/8 ✅
- ATP: נוספו TC-A-001..007 (auth) + TC-F-001..006 (billing/Cardcom test-mode).
- VERSION: v0.3.0
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: auth חי (magic-link+Google+beta gate+waitlist), Cardcom מחווט מלא ומוכן להפעלה (dry-run עד credentials+FEATURE_CARDCOM_LIVE), deploy config מוכן. אין חיוב אמיתי, אין פריסה.
- DECISIONS:
  1. **Cardcom נשאר TEST mode לחלוטין:** כל קריאת רשת חסומה מאחורי FEATURE_CARDCOM_LIVE=false → initiate מחזיר 503, renewal/charge מחזירים dry-run. אפס סיכוי לחיוב אמיתי. credentials = placeholders ב-.env.example בלבד.
  2. **הקשחות SPEC §4:** magic-link token נשמר כ-SHA-256 hash (לא plaintext); admin כ-role ב-DB (users.is_admin) עם bootstrap לפי ADMIN_BOOTSTRAP_EMAILS (לא רשימת env ids); Google — אכיפת iss תמיד + aud כשיש CLIENT_ID, ובפרודקשן CLIENT_ID ריק = שגיאה (לא דילוג שקט); dev-secret fallback כבר נחסם בפרודקשן ב-config (P0).
  3. **אוצר מילים פלאנים = basic/advanced/pro** (מיפוי plan==tier), מחירים מ-system_settings (admin בלי קוד).
  4. **trial עם כרטיס:** start_trial קובע trial 14 יום + next_billing; tokenization דרך זרימת ה-checkout; חיוב יום 15 = cron renewal (dry-run עד live).
  5. **suspension על 3 כשלונות** נכתב כ-subscription_status='past_due' + suspended_at (מכבד את ה-CHECK constraint; אין ערך 'suspended').
  6. **לא נגעתי ב-scoring-engine** — נשאר לפי הנחיה. (חילוץ ה-levels ע"י נדב תועד בנפרד למטה.)

## [ENGINE / חילוץ levels engine מהכלי האישי — pass 1] — 2026-07-01
- GOAL: לחלץ את מנוע ה-levels המאומת מהכלי האישי (finaroda-offline.html v25.80) ל-scoring-engine.js המשותף.
- SOLUTION: **סופק ע"י נדב** (לא Claude) במקביל ל-P1. חולצו byte-faithful: calcEMA/calcRSI/calcATR/calcADX/closedCandles/ema7Slope/computeSlTp/computeReversalAnchor. scoreDirection נשאר stub שזורק (pass 2 — דורש golden vectors).
- FILES MODIFIED: shared/scoring-engine.js, shared/scoring-engine.test.js, shared/scoring-engine.api.md.
- VALIDATION: node --test 8/8 ✅.
- VERSION: (חלק מ-shared, לא bump ל-repo).
- BRANCH: dev
- IMPACT: כרטיס ההחלטה יוכל להציג levels אמיתיים (Entry/SL/TP/Trailing/R:R/EMA7 slope/reversal anchor) ב-P2. הציון (PASS≥85/WATCH) עדיין חסום עד pass 2.
- NOTE: Claude לא כתב/שינה קוד זה; נדחף כ-commit נפרד לשקיפות.

## [P1.5 / חילוץ תשתית מנוע הסריקה — placeholder] — 2026-07-01
- GOAL: להכין את תשתית המנוע המשותף (`scoring-engine.js`) לפני P2, בלי מימוש. המנוע האמיתי עדיין שזור בכלי האישי (React מקומפל) ויסופק ע"י נדב. (SPEC §6.1, §12 החלטה 7)
- SOLUTION: נוצרה תיקיית `shared/` עם placeholder בלבד — חתימות פונקציות שמחזירות sentinel `TODO`, קובץ הגדרת API, ו-node:test שמאמת חתימות+התנהגות. **לא הומצא מנוע, לא נעשה חיבור ל-Bybit.** `shared/package.json` (`type:module`) מאפשר ל-`.js` לשמש כ-ESM גם בדפדפן (כלי אישי) וגם ב-Next (SaaS), ומכין את נתיב ה-npm package המשותף.
- FILES CREATED: shared/scoring-engine.js (stubs: ema7Slope, scoreDirection, computeReversalAnchor, computeSL, computeTP + TODO sentinel), shared/scoring-engine.api.md (חוזה API), shared/scoring-engine.test.js (node:test), shared/package.json.
- DB CHANGES: אין
- CONFIG ADDED: אין
- VALIDATION: node --test 3/3 ✅ | node --check parse ✅ | pytest 3/3 ✅ | tsc clean ✅ | eslint clean ✅
- ATP: נוסף TC-P1.5-001 (placeholder חשוף, חתימות קיימות, כל stub מחזיר TODO).
- VERSION: v0.2.1
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: תשתית המנוע המשותף מוכנה כשלד. P2 (ליבת סריקה) יוכל לייבא את הקובץ ברגע שהמימוש האמיתי יחולץ מהכלי האישי.
- DECISIONS:
  1. **stubs מחזירים sentinel `TODO`** (אובייקט קפוא, truthy ולא-מספר) במקום לזרוק — כדי שכל שימוש מוקדם ייחשף מייד ולא יזרים ערך שגוי לסריקה.
  2. **`shared/package.json` עם `type:module`** — כדי ש-`.js` (כפי שנדב ביקש, לא `.mjs`) יעבוד כ-ESM בשני הצרכנים. גם מניח את הבסיס ל-npm package משותף (SPEC §6.1).
  3. **`computeSL/TP` פוצל ל-`computeSL` + `computeTP`** נפרדים; ייתכן שיתאחדו כשהמימוש האמיתי יגיע (מתועד בחוזה כ"provisional").

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
