# CHANGELOG — FINARODA SaaS

> כל משימה מוסיפה entry לפי הפורמט ב-CLAUDE.md §3. החדש למעלה.

---

## [UPGRADE-STAGE3 / Live Billing (Cardcom)] — 2026-07-14
- GOAL: לסגור את לולאת החיוב המלאה מול Cardcom sandbox, production-ready אך NOT live: checkout + tokenization, חיוב חוזר + dunning, ביטול end-of-period + churn survey, מסמכי חיוב, ומכונת-מצבים חיוב שרתית שממנה נגזרות ההרשאות. LIVE SWITCH מחוץ ל-scope (שינוי env + אישור עו"ד, ידני ע"י נדב). OUT OF SCOPE: coupons + referral (Stage 4, אבל סכימה מוכנה D-B7), שינוי מחירים UI, proration, שנתי, PWA/domain.
- STOP POINTS (כולם נבדקו, אף אחד לא חסם את הבנייה, כולם מדווחים):
  - **S1 (credentials ל-sandbox) — הופעל:** אין `CARDCOM_TERMINAL_ID`/`CARDCOM_API_NAME`/`CARDCOM_API_PASSWORD`/`CARDCOM_WEBHOOK_SECRET` ב-env (placeholders בלבד). לפי S1 בניתי הכל מול MOCK אפס-רשת (הכל מגודר ב-`FEATURE_CARDCOM_LIVE=false`), הבדיקות ירוקות, והרשימה המדויקת של מה שנדב חייב להשיג מ-Cardcom נמצאת ב-SESSION_HANDOFF (terminal + API name/password + webhook secret + הפעלת מודול חשבוניות).
  - **S2 (קונפליקט state machine) — אין קונפליקט:** ה-CHECK הקיים של `users.subscription_status` (mig 001) כבר מכיל `none/trial/active/cancelled/past_due/expired` — מכסה את D-B4 אחד-לאחד, רק איות שונה (D-B4 "trialing"→`trial`, "canceled"→`cancelled`). לכן תיקננתי את מכונת-המצבים על אוצר-המילים הקיים; המיפוי מתועד, לא מיגרציה. אין קונפליקט עם entitlements (breadth נגזר מ-tier; ה-state קובע אם ה-tier בתשלום בכלל).
  - **S3 (הגדרות מודול חשבוניות) — CONFIG + שאלות לרו"ח:** אין חשבון Cardcom, אז נתיב ה-live של יצירת מסמך scaffold-מגודר; סוג-המסמך הוא CONFIG (`system_settings.billing_document_type`, ברירת-מחדל `receipt`). השאלות המדויקות לרו"ח (osek murshe/patur, receipt מול invoice_receipt, מספור) ב-SESSION_HANDOFF. offline = MOCK doc.
- SOLUTION:
  - **מכונת-מצבים אחת** `backend/core/billing_state.py` (D-B4, server-authoritative): מצבים none/trial/active/past_due/cancelled/expired; `ALLOWED_TRANSITIONS` (מטריצה) + `assert_transition` שזורק `IllegalTransition` על מעבר לא-חוקי; `effective_tier(status,tier)` — הרשאות נגזרות מה-state בלבד (past_due/cancelled שומרים גישה, expired/none→free); `apply_transition` הוא הנתיב היחיד לשינוי סטטוס (guard + UPDATE + audit ל-`subscription_events`).
  - **מסמכי חיוב** `backend/core/cardcom_invoice.py` (D-B3): `issue_document` לכל חיוב מוצלח (ראשון + חוזר), idempotent per-transaction (UNIQUE על `billing_documents.transaction_id`); סוג-מסמך CONFIG; offline יוצר MOCK (מספר יציב מה-tx, אפס רשת), live קורא `Documents/Create` (מגודר `FEATURE_CARDCOM_LIVE`). מייל receipt עם קישור למסמך (`_send_or_log`, כיבוד `email_product`).
  - **checkout** (`cardcom_service.handle_webhook`, D-B8): אימות HMAC constant-time; הצלחה מאשרת צד-שרת בלבד → `apply_transition`→active + tier + token + next_billing + מסמך + מייל; idempotent (dedupe by `cardcom_tx_id` + guard pending→success). redirect לבד לא מפעיל; חתימה פגומה/חסרה נדחית (200 אבל אין שינוי).
  - **חיוב חוזר + dunning** (`run_renewal_batch` + `_charge_succeeded`/`_charge_failed`, D-B5): מחייב `active`-due (`next_billing_at<=now`) + `past_due`-retry-due (`dunning_next_retry_at<=now`). כשל 1 → active→past_due + retry ב-+24h; כשל 2 → reschedule +48h (⇒ +72h מהכשל הראשון); כשל 3 → past_due→expired + tier→free. מייל `payment_failed` + פעמון לכל כשל. הצלחה → מסמך + מייל, past_due→active (recovery) או active→active (renew). idempotent: ריצה כפולה מוצאת 0 due.
  - **ביטול** (`cancel_subscription` + `drop_cancelled_to_free`, D-B6): status→cancelled, `subscription_cancelled_pending_at`=paid-through (או trial_ends_at ל-trial), מייל ביטול; cron מוריד ל-Free בתום התקופה. ביטול-כפול idempotent (מחזיר "already cancelled"). churn survey מחווט מ-`ChurnSurvey` (`api.cancelSubscription()` ואז `/api/churn/survey`).
  - **cron** `POST /api/cron/billing` (`api/cron.py` + `billing_batch_task`, D-B9): expire_trials → drop_cancelled → renewal, X-Cron-Secret, idempotent. Railway wiring ידני (HANDOFF).
  - **Frontend:** `lib/app/billing.ts` (helpers טהורים: `billingBanner`, `formatAgorotIls`, `isEntitled`, unit-tested); `components/app/BillingBanner.tsx` (past_due/cancelled/expired) ב-scan + settings; `ChurnSurvey` מבצע ביטול-אמת; מחירים ₪ מ-`/api/plans` + הערת "prices include VAT" (D-B2).
- FILES CREATED: `backend/migrations/034_billing_stage3.py`, `backend/core/billing_state.py`, `backend/core/cardcom_invoice.py`, `backend/tests/test_stage3_billing.py`, `frontend/src/lib/app/billing.ts`, `frontend/src/components/app/BillingBanner.tsx`, `frontend/tests/billing.unit.test.ts`.
- FILES MODIFIED: `backend/core/cardcom_service.py` (state machine + docs + dunning + cancel drop), `backend/core/email.py` (receipt/dunning/cancel renderers + `format_agorot_ils`), `backend/config.py` (`BILLING_PERIOD_DAYS`, `DUNNING_RETRY_OFFSETS_HOURS`), `backend/app/tasks/billing_tasks.py` (`billing_batch_task`), `backend/api/cron.py` (`/api/cron/billing`), `backend/.env.example`, `frontend/src/lib/api.ts` (`cancelSubscription`), `frontend/src/components/app/ChurnSurvey.tsx`, `frontend/src/app/(profile)/settings/page.tsx`, `frontend/src/app/(scan)/scan/page.tsx`, `frontend/src/app/subscribe/page.tsx`, `frontend/src/lib/version.ts`.
- DB CHANGES: mig 034 — טבלה `billing_documents`; `payment_transactions += coupon_code/referral_source/kind`; `users += dunning_next_retry_at`; `subscription_events` CHECK מורחב (rebuild, 5 event-types חדשים); seed `billing_document_type=receipt`. הכול additive/לא-הרסני.
- CONFIG ADDED: `BILLING_PERIOD_DAYS`, `DUNNING_RETRY_OFFSETS_HOURS`.
- VALIDATION: pytest **129/129** (112 + 17 Stage-3), tsc clean, eslint clean (`next lint`), frontend unit **51/51** (45 + 6). כל קריאות Cardcom mocked, אפס רשת (AC8). אין em-dash ב-copy חדש.
- ATP: TC-B3-01..09 (state matrix incl. illegal, agorot, documents + inert coupon/referral, webhook sig+idempotency, recurring double-run, dunning ladder + recovery, cancel end-of-period + double-cancel + trial-cancel, billing cron auth, no-live-terminal).
- VERSION: v0.14.0
- BRANCH: dev
- COMMIT: 24e5097
- IMPACT: לולאת חיוב מלאה עובדת מקצה-לקצה מול sandbox/mock — checkout, חיוב חוזר, dunning, ביטול, מסמכים — עם הרשאות שרתיות. אין טרמינל אמיתי מחובר; go-live = משימת נדב.
- DECISIONS: (1) מכונת-המצבים על אוצר-המילים הקיים של ה-DB (S2, בלי rename/מיגרציית ערכים). (2) מיילי receipt + dunning מכבדים `email_product` (Stage-5 discipline). (3) dunning schedule config-driven (+24h/+48h ⇒ +24h/+72h מהכשל הראשון). (4) offline document = MOCK מסומן ברור, אף פעם לא מסמך פיסקלי אמיתי.

## [UPGRADE-STAGE6 / Academy 2.0] — 2026-07-14
- GOAL: בניית האקדמיה מחדש (4 deliverables בריצה אחת): (A) card grid במקום רשימה, (B) חיפוש+פילטרים צד-לקוח, (C) שיעורי וידאו (embed), (D) ניהול שיעורים באדמין (create/edit/reorder/archive/video/tags/gating). תוכן השיעורים עצמו = משימת נדב (נשלח עם 12 שיעורים קיימים + מבנה-seed מוכן). OUT OF SCOPE: שינוי כללי XP (נעול), payments, referral, push/PWA, community.
- STOP POINTS (כולם נבדקו, אף אחד לא חסם):
  - **S1 (מבנה מתנגש) — לא נדרשה עצירה:** האקדמיה המשווקת (B6, PRD F6) שטוחה (12 מודולים), ותואמת card grid. הטבלאות `academy_bundles`/`academy_episodes` (mig 009, מבנה bundle→episode דו-שכבתי מה-template) קיימות אך **רדומות** — אף קוד חי לא קורא/כותב אליהן (רק test_smoke בודק קיום). זהו legacy מת, לא "הרשימה הנוכחית". המשכתי שטוח ומדווח.
  - **S2 (עמימות פלאן) — לא נדרשה עצירה:** בקוד `tier IN (free,basic,advanced,pro)` אך `advanced` רדום (mig 029 מיגר ל-basic, נסבל ב-CHECK). 3 מסלולים פעילים (free/basic/pro). min_plan={free,basic,pro}; `advanced` מטופל כ-paid(>=basic); `trial`=גישת Pro. אין עמימות אמיתית.
  - **S3 (סיכון מיגרציה) — לא נדרשה עצירה:** ההשלמות חיות כולן ב-`xp_events` (source=`academy_lesson`, ref=`module_id`). המיגרציה **purely additive** (יוצרת טבלה, אפס נגיעה ב-`xp_events`), וזורעת את 12 השיעורים עם `slug`==module_id הישן — כל השלמה+XP נשמרת לפי אותו slug. count-match מובטח.
- SOLUTION:
  - **Backend — מנוע DB (mig 033 `academy_lessons`):** מחליף את רשימת `_MODULES` הקשיחה של B6. `slug` (מפתח השלמה) · title/description · content_type(text/video) · body · video_url · duration · tags(JSON) · **min_plan + min_rank** (D-AC1) · sort_index · awards_xp(0 ל-stubs) · archived_at (archive-not-delete).
  - **שער-כפול (`core/academy_gate.py`):** `is_unlocked = plan_ok AND rank_ok`. rank = STATUS (‏`xp_total>=min_rank`), לא הוצאת XP. `lock_reason` בשפה פשוטה (דרגה נקראת ראשונה). `validate_video_url` — YouTube/Vimeo בלבד, מנרמל ל-embed URL, דוחה אחר (400).
  - **תוכן נשלט-שרת (D-AC7):** `GET /api/academy` = מטא-דאטה+lock_reason בלבד (ללא body/video). `GET /api/academy/{slug}` = תוכן מלא רק אם פתוח, אחרת **403** (נבדק שאין דליפת body/video). `POST /{slug}/complete` = +100 חד-פעמי (unique), awards_xp=0→0.
  - **Admin (`api/admin_academy.py`, admin-only→403, audited ל-`admin_events`):** `GET/POST /lessons`, `PUT /lessons/{id}`, `POST /{id}/archive|restore`, `POST /reorder` (ordered_ids, up/down — D-AC5). auto-slug ייחודי, ולידציית וידאו/gates.
  - **Frontend:** `academy/page.tsx` = card grid רספונסיבי (maxWidth 1040 + grid auto-fill) + search + פילטרי type/state (‏`lib/app/academy.ts` — `filterLessons`/`lessonState`/`videoEmbed`, טהור, unit-tested). `academy/[moduleId]/page.tsx` = fetch תוכן gated, render טקסט/וידאו, mark-complete. `components/academy/VideoEmbed.tsx` = נגן lazy (iframe רק בלחיצה, poster ל-YouTube). `components/admin/AcademyAdmin.tsx` = ניהול מלא, מחובר כסקשן "academy" ב-admin. types + APP_VERSION→0.13.0.
- FILES CREATED: `backend/migrations/033_academy_lessons.py`, `backend/core/academy_gate.py`, `backend/api/admin_academy.py`, `backend/tests/test_academy_v2.py`, `frontend/src/lib/app/academy.ts`, `frontend/src/components/academy/VideoEmbed.tsx`, `frontend/src/components/admin/AcademyAdmin.tsx`, `frontend/tests/academy.unit.test.ts`.
- FILES MODIFIED: `backend/api/academy.py` (rewrite DB-backed), `backend/models/academy.py` (rewrite), `backend/main.py` (register admin_academy_router), `frontend/src/app/(academy)/academy/page.tsx` + `[moduleId]/page.tsx` (rewrite), `frontend/src/app/(admin)/admin/page.tsx` (academy section), `frontend/src/lib/app/types.ts`, `frontend/src/lib/version.ts`, docs (PRD F6 / SPEC §3.1+§5.12 / UX / ATP / VERSIONS / SESSION_HANDOFF).
- DB CHANGES: mig 033 (`academy_lessons` + index + 12-lesson seed). `xp_events` **לא נגעתי** (השלמות נשמרות).
- CONFIG ADDED: אין.
- VALIDATION: pytest **112/112** (100 + 12 חדש), tsc clean, eslint clean (`next lint`), frontend unit **45/45** (37 + 8 חדש, כולל viewport.regression), shared 14/14 (untouched).
- ATP: TC-AC6-01..14 (13 auto + 1 manual browser).
- VERSION: v0.13.0
- BRANCH: dev
- COMMIT: 17bd07b
- IMPACT: האקדמיה עברה ל-card grid עם חיפוש/פילטרים ווידאו; אדמין מנהל שיעורים בלי קוד; gating עבר לשער-כפול plan+rank נשלט-שרת. כל ההשלמות/XP הקיימות נשמרו. אין שינוי במסלול המשתמש להשלמה (+100 חד-פעמי).
- DECISIONS: (1) min_rank מאוחסן כסף-XP int (0/1000/3000/8000), ישיר להשוואה מול xp_total. (2) `awards_xp` boolean per-lesson שומר התנהגות B6 stub (3 seeds=0) → כל הבדיקות הקיימות נשארות ירוקות. (3) reorder = כפתורי up/down ששולחים סדר מלא (D-AC5). (4) body נזרע מ-concept JSON (guarded read, fallback ריק) לשימור תוכן קיים בשליטת-שרת. (5) locked-content = 403 עם reason (לא 404).
- AC9 (em-dash lint report): ראה SESSION_HANDOFF — הממצא מ-Stage 7 דווח במלואו.

## [UPGRADE-STAGE7 / Admin v1.1 + Sentry + Ticket Breadcrumbs] — 2026-07-14
- GOAL: (A) שדרוג טבלת משתמשים באדמין (עמודות עשירות, פילטרים צד-שרת, CSV, churn survey), (B) Sentry backend+frontend env-gated, (C) breadcrumbs לכל טיקט. + drift-fix מאושר: הסרת em-dashes מתבניות welcome/beta email (דווח ב-Stage 5). OUT OF SCOPE: לוגיקת referral (עמודה placeholder 0), payments (Stage 3 חסום), Academy, כל שינוי XP.
- STOP POINTS: **S1** — אין קונפליקט: SPEC F9/B7 מגדיר churn=שיעור+סיבת-עזיבה-משאלון, tickets, MRR; D-A2/D-A3 מוסיפים פירוט (XP/scans/active-days) בלי לסתור. לא נדרשה עצירה. **S2** — breadcrumbs לא נוגעים ב-reveal-gating: sanitizer allowlist בצד-שרת מוודא שאף ערך תוצאה לא נכנס; הלקוח ממילא לא מחזיק ערכים לא-חשופים. לא נדרשה עצירה.
- SOLUTION:
  - **Admin v1.1 (`api/admin.py`):** `list_users` נכתב מחדש עם כל עמודות D-A2 (email, call_sign, plan, status, signup, last_active, scans_total, scans_week, xp, rank, active_days_7d/30d, referrals=0, churn_survey flag). פילטרים צד-שרת AND (`_user_filters`): plan/status(trial/active/expired/churned)/signup-range/last-active-range/min_scans. **CSV** `GET /users/export.csv` (StreamingResponse, אותו filter, row-cap 5000, admin-only). rank מחושב server-side (`core/ranks.py`, מראה מ-lib/onboarding/xp.ts). **active-days = ADMIN ANALYTICS בלבד (D-A1)**: distinct calendar days עם scan, read-only מ-scan_events, לא user-facing, לא XP, לא gate.
  - **Churn (D-A5):** אין UI ביטול (Stage 3 חסום) → endpoint מנותק `POST /api/churn/survey` (‏`api/churn.py`), נשמר ל-`churn_reasons` (mig 006, כבר קיים). מוצג ב-Settings ("Cancel plan or leave"), admin רואה ב-`GET /api/admin/churn` + flag בטבלה + סינון status=churned.
  - **Sentry (D-A6):** backend `core/monitoring.py` — env-gated (‏`SENTRY_DSN_BACKEND` או `SENTRY_DSN`), `before_send=scrub_event` (מסיר email/ip/cookies/auth, שומר user.id בלבד), `set_request_user(id)` ב-get_current_user. frontend `lib/sentry.ts` — `shouldInitSentry` טהור + dynamic import של `@sentry/nextjs` (env-gated, אפס-תלות-בבנייה), `src/instrumentation.ts` + `src/instrumentation-client.ts`. בלי DSN — אפס קריאות רשת (בדיקות רצות כך).
  - **Breadcrumbs (D-A7):** `lib/breadcrumbs.ts` ring buffer (20) — route_change/scan_submit/api_error/notif_open (hooks ב-layout/apiFetch/NotificationBell), מצורף ל-`POST /api/support/tickets`. sanitizer צד-שרת (`core/breadcrumbs.py`, allowlist) לפני אחסון (mig 032 `support_tickets.breadcrumbs`). admin ticket view מרנדר timeline (client trail + server events). **RED LINE:** אף ערך תוצאה לא נכנס (test assert).
  - **drift-fix:** em-dashes הוסרו מ-welcome/beta emails (`core/email.py`).
- FILES CREATED: `backend/migrations/032_ticket_breadcrumbs.py`, `backend/core/ranks.py`, `backend/core/breadcrumbs.py`, `backend/core/monitoring.py`, `backend/api/churn.py`, `backend/tests/test_stage7_admin.py`, `frontend/src/lib/breadcrumbs.ts`, `frontend/src/lib/sentry.ts`, `frontend/src/lib/adminFilters.ts`, `frontend/src/components/app/RouteBreadcrumbs.tsx`, `frontend/src/components/app/ChurnSurvey.tsx`, `frontend/src/instrumentation.ts`, `frontend/src/instrumentation-client.ts`, `frontend/tests/admin.unit.test.ts`.
- FILES MODIFIED: `backend/api/admin.py` (users v1.1 + CSV + churn list + ticket breadcrumbs), `backend/api/support.py` (sanitize+store breadcrumbs), `backend/models/support.py`, `backend/core/auth.py` (sentry user id), `backend/core/email.py` (em-dash fix), `backend/config.py` (SENTRY_DSN fallback), `backend/main.py` (init_sentry + churn router). frontend: `lib/api.ts` (breadcrumb hooks + export API_URL), `app/layout.tsx`, `components/scan/NavDrawer.tsx`, `components/app/NotificationBell.tsx`, `app/(admin)/admin/page.tsx` (users filters/columns/CSV + ticket breadcrumbs), `app/(profile)/settings/page.tsx` (churn card), `package.json` (@sentry/nextjs), `lib/version.ts`.
- DB CHANGES: migration 032 (`support_tickets.breadcrumbs` TEXT + `idx_churn_user`). `churn_reasons` (mig 006) כבר היה קיים — לא נדרש schema חדש.
- CONFIG ADDED: `SENTRY_DSN` (backend fallback, קיים גם `SENTRY_DSN_BACKEND`), `NEXT_PUBLIC_SENTRY_DSN` (frontend). כולם absent=disabled.
- VALIDATION: pytest **100/100** (86→100, +14), tsc clean, eslint clean, frontend unit **37/37** (30→37, +7), shared **14/14**.
- ATP: TC-A7-01..TC-A7-14 (filters AND, columns+rank, active-days boundary, active-days-not-user-facing, CSV auth+content, churn CRUD+admin+flag+filter, Sentry disabled zero-network, PII scrub, breadcrumb red-line, breadcrumb cap, ticket breadcrumbs stored/rendered, admin 403, unit: filters↔URL/rows/ring/sentry-gate).
- VERSION: v0.12.0
- BRANCH: dev
- COMMIT: 617e4b3
- IMPACT: אדמין רואה טבלת משתמשים עשירה עם פילטרים משותפים-URL + CSV; churn survey נלכד ומוצג; Sentry מוכן (env-gated, ללא PII); כל טיקט נושא breadcrumb trail לדיבוג. משתמש קצה: אין שינוי גלוי פרט ל-"Cancel plan or leave" ב-Settings.
- DECISIONS: (1) D-A8 = **הרחבת** מערכת טיקטים קיימת (support_tickets/ticket_replies). (2) D-A5 hook = endpoint churn מנותק מ-Settings (אין דף ביטול; Stage 3 חסום). (3) churned = יש שורת churn_reasons (שונה מ-expired שקט). (4) Sentry frontend דרך dynamic import כדי לא לחסום tsc/build ללא התקנת החבילה.
- DRIFT FOUND (מדווח, לא תוקן בשקט): הלינט em-dash סורק גם הערות JSX (`{/* */}`) כ-copy — לא-אינטואיטיבי אך התנהגות קיימת (נשמרתי ממנה בקוד החדש). אין drift חדש נוסף.

---

## [UPGRADE-STAGE5 / Notifications + Bell + Preferences + Real Resend] — 2026-07-14
- GOAL: מערכת נוטיפיקציות מלאה — פיד in-app עם פעמון בהמבורגר, העדפות per-user (sound/vibration/off + opt-in לאימייל), אינטגרציית Resend אמיתית (עם DEV fallback), ושלושה זרמי אימייל (day-11 trial reminder, reveal-teaser, admin broadcast). OUT OF SCOPE: web push/PWA (שלב 8), referral/payment emails (חסומים), כל שינוי XP.
- STOP POINTS: **S1 (trial length)** — SPEC §5 "Trial 14 יום" + `trial_reminder_day`=11 + `TRIAL_DAYS=14`/`TRIAL_REMINDER_LEAD_DAYS=3` ⇒ יום-11 = 3 ימים לפני הסוף. אושר, לא נדרשה עצירה. **S2 (sending domain)** — `EMAIL_FROM_BRAND` כבר מוגדר כברירת-מחדל `FINARODA <noreply@finaroda.com>`; לא הומצא דומיין. הבנייה והבדיקות רצות ב-DEV console-fallback (בלי RESEND_API_KEY) ⇒ אפס קריאות רשת. שליחה חיה דורשת אימות `finaroda.com` ב-Resend (hardening/שלב 8) — מתועד ב-HANDOFF.
- SOLUTION:
  - **DB (mig 031):** `notifications` (פיד פעמון: id/user_id/type/title/body/link_path/created_at/read_at, index על (user_id,read_at)), `notification_prefs` (PK user_id, 5 דגלים default true), `journal_scenarios.teaser_sent_at` (sent-flag ל-dedup per-reveal). ה-`notifications_log` (mig 028) נשאר כ-ledger idempotency/audit — נפרד מהפיד.
  - **Service (`core/notifications.py`):** get/update prefs (lazy defaults), create_notification (חסום ע"י inapp_enabled), list/unread/mark_read (server-authoritative), טוקני unsubscribe חתומים (HMAC על JWT_SECRET, per-category, TTL שנה).
  - **Email (`core/email.py`):** render+send ל-trial_reminder/reveal_teaser/broadcast (renderers טהורים לבדיקה); `_send_or_log` = Resend או log ב-DEV. **reveal-teaser = אפס ערכי תוצאה** (D-N5, נבדק על ה-body). unsubscribe link בכל broadcast.
  - **API:** `/api/notifications` (GET feed+unread, POST /read, GET/PUT /prefs); `/api/email/unsubscribe` (GET, ללא login, HMAC, idempotent, דף HTML); `/api/cron/notifications` (POST, X-Cron-Secret, idempotent). Admin broadcast: `GET /broadcasts/preview` (audience + email_optin), `POST /broadcasts` שולח מיילים אמיתיים לאופט-אין בלבד + unsubscribe + שורות פעמון (per-user gated).
  - **Tasks:** `trial_ending_soon_task` — חלון datetime() half-open [+3d,+4d) (boundary מדויק day-10/11/12), email מכבד email_product, שורת פעמון מכבדת inapp_enabled, idempotency דרך notifications_log. `journal_reveal_teasers_task` — per-user, teaser_sent_at כ-dedup, אימייל+פעמון content-free.
  - **Frontend:** `NotificationBell.tsx` (פעמון+badge cap 9+, panel newest-first, mark-read on open, arrival sound/vibration gated ל-prefs + first-interaction), `lib/notifications.ts` (helpers טהורים), settings toggles (5), admin Broadcast preview+confirm step, unsubscribe copy.
- FILES CREATED: `backend/migrations/031_notifications_prefs.py`, `backend/core/notifications.py`, `backend/api/notifications.py`, `backend/api/email.py`, `backend/api/cron.py`, `backend/tests/test_stage5_notifications.py`, `frontend/src/lib/notifications.ts`, `frontend/src/components/app/NotificationBell.tsx`, `frontend/tests/notifications.unit.test.ts`.
- FILES MODIFIED: `backend/config.py` (CRON_SECRET), `backend/core/email.py` (renderers+senders, unsubscribe_url, footer em-dash→hyphen), `backend/app/tasks/billing_tasks.py`, `backend/app/tasks/journal_tasks.py` (+ deprecate log_trial_reminders_task), `backend/scripts/run_resolve_scenarios.py`, `backend/api/admin.py` (broadcast preview+real send), `backend/main.py` (3 routers), `backend/tests/conftest.py` (CRON_SECRET), `frontend/src/lib/app/types.ts`, `frontend/src/components/scan/NavDrawer.tsx`, `frontend/src/app/(profile)/settings/page.tsx`, `frontend/src/app/(admin)/admin/page.tsx`, `frontend/src/lib/version.ts`.
- DB CHANGES: migration 031 (notifications, notification_prefs, journal_scenarios.teaser_sent_at). מיגרציה מנטרלת התנגשות: טבלת `notifications` הישנה מ-mig 005 (scheduled-outbox שאף קוד לא קורא/כותב) שונתה ל-`notifications_legacy_outbox` (לא-הרסני, שומר שורות).
- CONFIG ADDED: `CRON_SECRET` (חדש). `RESEND_API_KEY` / `EMAIL_FROM_BRAND` / `EMAIL_REPLY_TO` / `EMAIL_SENDING_ENABLED` — כבר היו קיימים ב-config.
- VALIDATION: pytest **86/86** (71→86, +15), tsc clean, eslint clean, frontend unit **30/30** (24→30, +6), shared **14/14** (לא נגעתי).
- ATP: TC-N5-01..TC-N5-12 (feed/read, prefs, inapp-gate, day-11 boundary, cron idempotency, reveal-teaser no-outcome+dedup, broadcast 403/filtering/preview, unsubscribe valid/tampered/repeat, cron auth, bell badge 9+/toggle/vibration no-op).
- VERSION: v0.11.0
- BRANCH: dev
- COMMIT: b714ca8
- IMPACT: משתמש רואה פעמון עם ספירת unread שורדת refresh, מסמן נקרא בפתיחה; שולט ב-sound/vibration/in-app + opt-in לאימיילים; מקבל תזכורת יום-11 ו-reveal-teaser (ללא ערכי תוצאה); אדמין שולח broadcast עם preview + confirm + unsubscribe חובה. אין שליחה חיה עד אימות דומיין.
- DECISIONS: (1) `notifications` (פיד) ≠ `notifications_log` (ledger) — קיום-משותף נקי. (2) reveal-teaser עם sent-flag על שורת ה-reveal + אימייל אחד למשתמש per-sweep (מכבד "one teaser per pending reveal" + לא ספאם). (3) `log_trial_reminders_task` deprecated — `trial_ending_soon_task` דרך endpoint הוא הנתיב הסמכותי היחיד ל-day-11.
- DRIFT FOUND (מדווח, לא תוקן בשקט): (a) טבלת `notifications` מתה מ-mig 005 (שונתה בצד, לא נמחקה); (b) em-dashes ב-copy קיים של welcome/beta emails (email.py:106,121,127) — לא נגעתי; (c) שני נתיבי day-11 עם ref שונה (billing vs journal task) — אוחדו.

---

## [RESPONSIVE-PASS / phone+desktop usability] — 2026-07-13
- GOAL: כל מסך במוצר שמיש במלואו בטלפון (~390px) וב-desktop (mandate של נדב). אפס גלילה אופקית של העמוד ב-360–430px, אפס טבלה/מסגרת חתוכה. dev בלבד, PATCH. אין שינוי פיצ'ר פרט לשורת copy אחת.
- SOLUTION (מה עשינו בפועל):
  1. **מיפוי מצב:** מסכי המוצר כבר בנויים mobile-first מהסבבים הקודמים (Package B / FIX-R3R4) — כל route מוצר ממורכז בעמודת `maxWidth` (scan 480, dashboard/profile/settings/academy 440, history/subscribe/blueprint 480, login 420, onboarding shell 480), charts כבר responsive (SVG viewBox + `width:100%`), tooltips clamped. ה-offender האמיתי היחיד: **קונסולת האדמין** (desktop-first, rail קבוע 200px + פאנלים צדדיים 280/340/300px + grids צפופים 5-טורים) — נשברה בטלפון.
  2. **`useIsMobile` hook** (`frontend/src/lib/app/useIsMobile.ts`) — `matchMedia`, mounted-guard (מחזיר desktop עד mount → אין hydration mismatch). קומפוננטות inline-styled לא יכולות media-queries, אז מסכים שצריכים להחליף layout מסתעפים על זה.
  3. **globals.css** — safety layer: `body { overflow-x: hidden }` (אין scrollbar אופקי לעמוד לעולם; טבלאות רחבות גוללות בתוך container משלהן), `main` padding → `clamp(0.9rem,4vw,2rem)` (משחרר רוחב בטלפון: היה 2rem=64px מתוך 360, עכשיו ~14px), ו-`img/svg/video/canvas/table/pre { max-width:100% }`.
  4. **קונסולת אדמין responsive** (`app/(admin)/admin/page.tsx`) — ה-`main` דורס את חוק ה-`main` הגלובלי (column+center+2rem+text-center שדלף) ופורש edge-to-edge. Rail → **פס טאבים עליון sticky + tab-strip נגלל** בטלפון / rail 200px ב-desktop. Overview grid → `repeat(auto-fit,minmax(140px,1fr))` (5 ל-2). Users/Tickets → **master/detail swap** בטלפון (בחירה מחליפה את הרשימה עם "← back", במקום פאנל צדדי קבוע שגולש); Users list → כרטיסים בטלפון. Broadcast → stack. Notifications log → overflowX scroller + **טור ראשון sticky** (לא נחתך). Settings locked cards → column. Desktop = מסגרות B7 רוחב-מלא כפי שהיה.
  5. **copy אחת:** caption ה-reveal ב-dashboard תלוי-tier — Free (‏1 סריקה/יום): **"Revealed on tomorrow's scan"**; בתשלום/trial (unlimited): **"on your next scan"**.
  6. **Harness רגרסיה (structural lint, בחירת נדב):** `frontend/tests/viewport.regression.test.ts` — רץ ב-`node --test` הקיים ללא deps חדשים (jsdom=אפס layout, Playwright/Next-server לא יציב במכונה הזו — ה-validations הידניים של נדב הם המדידה בדפדפן-אמת). רשימת `PATTERNS`+`MAXWIDTH_ROUTES`+`SCROLLER_FILES` ניתנת-להרחבה עם הערות: כל overflow שנדב ימצא ידנית מקודד כדפוס חדש. בודק: אין fixed width ≥360 ללא guard; כל route מוצר עם maxWidth; admin עם useIsMobile+main לא-ממורכז; טבלאות רחבות ב-overflowX; chart fluid; globals guards.
- FILES CREATED: `frontend/src/lib/app/useIsMobile.ts`, `frontend/tests/viewport.regression.test.ts`.
- FILES MODIFIED: `frontend/src/app/globals.css`, `frontend/src/app/(admin)/admin/page.tsx`, `frontend/src/app/(dashboard)/dashboard/page.tsx`, `frontend/src/lib/version.ts`, `ATP.md`, `CHANGELOG.md`, `VERSIONS.md`, `SESSION_HANDOFF.md`.
- DB CHANGES: אין.
- CONFIG ADDED: אין.
- VALIDATION: pytest 71/71 · tsc clean · eslint clean (`next lint` — No warnings/errors) · frontend unit **24/24** (18 קודמים + 6 viewport).
- ATP: TC-RESP-01 (ידני, no-overflow 360–430px + admin), TC-RESP-02 (אוטומטי, structural-lint 6/6), TC-RESP-03 (copy Free vs paid).
- VERSION: v0.10.1
- BRANCH: dev
- COMMIT: 3c58c38
- IMPACT: כל route שמיש בטלפון; קונסולת האדמין (offender ידוע) עוברת לטאבים עליונים + master/detail + טבלאות נגללות בטלפון, ונשארת רוחב-מלא ב-desktop; אין גלילה אופקית לעמוד; רגרסיה שומרת על זה. copy: Free רואה שה-reveal מגיע "מחר".
- DECISIONS: (1) לפי בחירת נדב — structural-lint ב-`node --test` במקום Playwright (gate שנכשל מסביבה מתעלמים ממנו; ה-validations הידניים = מדידת דפדפן-אמת). Playwright E2E מועמד ל-CI עתידי כשה-pipeline ירוץ במכונה שבה builds מסתיימים. (2) admin נשאר desktop-first אך שמיש בטלפון (master/detail swap במקום להצטופף). (3) לא נגעתי במסכי מוצר שכבר responsive — אין שינוי מיותר.

## [FIX-R3R4 / validations 3+4 fix round] — 2026-07-13
- GOAL: לתקן 11 באגים + ליישם 5 החלטות מאושרות (A–E) + תוספות UX מהוולידציות 3+4 של נדב. dev בלבד, MINOR.
- SOLUTION (מה עשינו בפועל):
  1. **Decision A — 3 פלאנים (Advanced הוסר):** Free/Basic/Pro, coins 2/5/10, prices basic ₪59 / pro ₪149 (**PENDING-ACCOUNTANT**). mig 029 ממגר משתמשי advanced→basic ומכייל system_settings (scan_coins_basic=5, plan_price_basic=5900, plan_price_pro=14900 agorot; מפתחות advanced_* נמחקו). `/api/plans` + entitlements defaults + cardcom VALID_PLANS + models Literals + admin editable/plan-override + academy full-access = basic+pro. ה-CHECK של users.tier לא נבנה מחדש ('advanced' נסבל כ-legacy).
  2. **Bug 3 — אכיפת scans/day:** `POST /api/scan/events` דוחה סריקה מעל המכסה היומית (429 `DAILY_SCAN_LIMIT`, ספירת `scan_events` של היום); Free=1/יום, בתשלום=unlimited; admin-editable (scans_per_day_*). קליינט: phase "limit" ידידותי (SEE PLANS / VIEW JOURNAL).
  3. **Bug 4 — trial ללא כרטיס:** "Start 14 days" (onboarding S11 + Subscribe) קורא ישירות `POST /api/cardcom/trial` ונוחת `/scan` עם **TRIAL chip** (אין מסך tokenizing). day-11 reminder נרשם ב-`notifications_log` (idempotent, email_in_app); expiry→Free (קיים).
  4. **Bug 2 — XP:** המענק (300) + call-sign persist + completion עברו ל-**S9** (call-sign submit); S11 chooseFork מפעיל complete() כ-idempotent safety-net → exit שבור לא עולה במענק.
  5. **Bug 1 — flash:** `runScan` מחזיק את ה-scanning overlay עד ש-reveal חוזר (onDone async, S2/S8/S10) — אין frame pre-scan ביניים. S5→S6: אין scan/redirect בקוד; מומלץ אימות דפדפן.
  6. **Bug 5 — SEE PLANS→חזור:** מצב הסריקה נשמר ב-sessionStorage (passers/nonPassers/md/ids) ומשוחזר ב-mount → חוזרים ל-RESULTS, המטבעות עדיין ניתנים ללחיצה.
  7. **Bugs 6/7/8:** S1 כותרת פיצול-2-שורות מכוון; S8 placeholders עקביים (E3 risk 0.1511 קיים); כפתור SCAN = "N COINS".
  8. **Decision B — Recent scans:** `GET /api/scan/history` + `/history/{id}` (read-only מ-scan_events/score_log), דף `/history` + פריט "Recent scans" ב-drawer.
  9. **Decision C — בחירת מטבעות:** picker במסך ה-idle, בחירה בתוך `coins_per_scan`, נשמר ב-localStorage, נאכף בסריקה.
  10. **Decision D — why-not בתשלום:** NonPasser מציג "THE ACTUAL NUMBERS" (price vs EMA200 %, EMA7 slope, volume ratio) ל-full-layers; Free רואה הפניה לתשלום. ללא weights/formulas.
  11. **Decision E — ברירות מחדל:** Lens=Full, Style=Balanced מסומנות (hint + outline).
  12. **UX:** לוגו→/scan (authed), greeting לפי call-sign (email fallback), dashboard "How is R measured?" (r_multiple tooltip + caption), Profile≠Settings (settings = remembered scan settings), login B6a + **DEV SIGN-IN** (dev_magic_link), admin back-to-app + notifications explainer, tickets מצרפים app_version (mig 030) + 20 אירועים אחרונים בתצוגת אדמין. `.env.example`: DEV_RETURN_MAGIC_LINK=true + production-guard note.
- FILES CREATED: backend/migrations/029_three_plan_model.py, backend/migrations/030_ticket_app_version.py, frontend/src/app/(scan)/history/page.tsx, frontend/src/lib/version.ts.
- FILES MODIFIED: backend (api/scan,plans,cardcom,admin,support,academy · core/entitlements,cardcom_service · app/tasks/billing_tasks · models/scan,cardcom,admin,support · tests · .env.example), frontend (scan/page, subscribe, login, profile, settings, admin, dashboard, OnboardingFlow, AppHeader/Controls/NavDrawer/NonPasser, lib api/store/persist), PRD/SPEC/UX, ATP, CHANGELOG, VERSIONS, SESSION_HANDOFF.
- DB CHANGES: mig 029 (retire Advanced: migrate advanced→basic, retune/prune system_settings), mig 030 (support_tickets.app_version).
- CONFIG ADDED: אין env חדש (DEV_RETURN_MAGIC_LINK כבר קיים; עודכן note+ברירת-מחדל dev).
- VALIDATION: pytest 71/71, tsc clean, eslint clean, frontend unit 18/18, shared 14/14. (next build: Windows .next lock timeout — לאימות ידני.)
- ATP: +TC-A-101 (3-plan gating), TC-A-102 (daily scan cap), TC-A-103 (trial→Free expiry), TC-A-104 (scan history + owner-scope), TC-A-105..A-110 (manual: flash, XP@S9, coin-pick, why-not enrich, defaults, login dev).
- VERSION: v0.10.0
- BRANCH: dev
- COMMIT: e2e49b8 (backend) + b852dd7 (frontend) + docs commit
- IMPACT: תוכנית 3-מסלולים אחת, אכיפת מכסה יומית אמיתית, trial חלק ל-/scan, XP שלא הולך לאיבוד, בחירת מטבעות, היסטוריית סריקות, ומסכי login/profile/settings/admin מתוקנים.
- DECISIONS: (1) לא בונים מחדש את CHECK של users.tier — 'advanced' נסבל כ-legacy וממוגר ל-basic (הפיך, לא-הרסני). (2) Basic יורש academy מלא של Advanced. (3) אכיפת scans/day דוחה סריקה 2 באותו יום — עודכנו 3 טסטים קיימים (journal reveal) לטיר unlimited. (4) גרנט ה-XP הוקדם ל-S9 לפי כוונת נדב.

---

## [DOCS-SYNC / reconcile source-of-truth docs with Package B implemented state] — 2026-07-13
- GOAL: ליישר את מסמכי המקור-אמת (PRD/SPEC/UX) עם המצב הממומש אחרי Package B phases 1+2 (v0.8.x–v0.9.0). docs only, dev, PATCH.
- SOLUTION (מה עשינו בפועל):
  1. **PRD F3 = מודל `journal_scenarios` הממומש:** תואר המודל (‏`pass` / `no_setups_day`, WATCH לעולם לא תרחיש), resolution צד-שרת, מצבי status, ו-reveal-gating. **CAPITAL SAVES הוגדר** = PASS שה-trigger לא נורה בחלון (הון נשמר, r=0), עם **הערה** ששורת ה-SAVE הפר-מטבע-לא-עובר היא **הרחבה עתידית** ל-F3 (לא v0.9.0).
  2. **SPEC data model הורחב (§5.9 חדש):** `journal_scenarios` (mig 028, DDL מלא) + `ticket_replies`/`notifications_log`/`user_settings`; `admin_events` (mig 006) כ-audit trail של B7; endpoints (`GET /api/scan/entitlements`, `GET /api/plans`, journal/profile/support/broadcasts); מפתחות `system_settings` (`scan_coins_free`, `chart_layers_*`, `scans_per_day_*`, trial/journal admin keys).
  3. **Shared engine (SPEC §6.1):** `findRecentSwingLevels` תועד כ-S/R הקנוני היחיד (equivalence-tested מול המימוש האישי); **`computeRangeLevels` סומן כהוסר** (יחד עם `lib/onboarding/levels.ts`).
  4. **סימון SHIPPED עם version refs:** F1/F1c(E9)/F2/F3/F5/F6/F7/F9/F10/F11/F13/F14/F15/E7b — כל אחד עם הגרסה בה נחת. גרפים = in-app SVG (לא recharts) תואם ב-PRD/SPEC/UX.
  5. **Open items = follow-ups מ-HANDOFF:** resolve-scenarios cron, call-sign persistence, email stubs, fonts, Free 1-scan/day enforcement, admin mobile, POSITION honesty guardrail, CAPITAL SAVES non-passer variant.
  6. **Stale-claim sweep:** תוקנו הפניות recharts שסתרו את המימוש (‏PRD F15/AC1, SPEC §5.5, UX §3); "מסך P2 הישן" מסומן כמוחלף.
- FILES CREATED: אין.
- FILES MODIFIED: FINARODA_SAAS_PRD.md, FINARODA_SAAS_SPEC.md, FINARODA_SAAS_UX.md, CHANGELOG.md, VERSIONS.md, ATP.md, SESSION_HANDOFF.md.
- DB CHANGES: אין (docs only).
- CONFIG ADDED: אין.
- VALIDATION: pytest 66/66, tsc clean, eslint clean (docs-only, ללא שינוי קוד).
- ATP: +TC-DOCS-SYNC01 (doc-check — journal_scenarios/CAPITAL SAVES, SPEC data model, swing canon, SHIPPED refs, open items).
- VERSION: v0.9.1
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: מסמכי המקור-אמת משקפים כעת את המצב הממומש; אין שינוי קוד/מנוע/DB. main/production לא נגעו.
- DECISIONS: (1) גרפים in-app SVG מתועדים כמצב הממומש עם recharts כ-dependency רשום + החלטה פתוחה (revert אם נדב מעדיף). (2) CAPITAL SAVES = trigger-never-filled מתועד כהגדרה הנעולה, non-passer variant כהרחבה עתידית מסומנת ⬜. (3) הורחב סימון SHIPPED גם ל-F1/F2/F5/F6/F7/F9/F10/F11 (מעבר לחמישה שנוקבו) כדי שה-PRD ישקף במלואו את Package B.

## [PKG-B-P2 / Package B phase 2: B4 dashboard + B5 profile + B6 academy + B7 admin] — 2026-07-13
- GOAL: לסגור את חבילת Design B — היומן "What Would Have Happened" עם reveal-gating (B4, לב ה-retention), הפרופיל + סולם הדרגות (B5), מעטפת האקדמיה (B6), וקונסולת האדמין (B7). MINOR.
- SOLUTION (מה עשינו בפועל):
  1. **B4 — journal + reveal-gating (F3):** טבלת `journal_scenarios` (mig 028) נוצרת מכל סריקה — תרחיש `pass` לכל PASS (שורת momentum, `passed_threshold=1`) + רשומת `no_setups_day` ליום דילוג. **WATCH לעולם לא תרחיש** (AC2). Job צד-שרת (`journal_tasks.resolve_scenarios_task` + `scripts/run_resolve_scenarios.py`) מריץ את הנרות הבאים מ-Bybit (‏trigger→target/risk/7-day expiry) ומחשב `r_result` היפותטי (R בלבד, לעולם לא כסף). **Reveal-gating (AC5):** התוצאה נכתבת לשרת אך **לא נכללת בשום payload ללקוח עד הסריקה הבאה** — אירוע החשיפה הוא הסריקה (`core/journal.on_scan` חושף קודם, ואז יוצר תרחישים חדשים). שורות לא-חשופות נושאות **אפס דאטת תוצאה** ב-payload וב-DOM (regression מגובה-טסט, תבנית S10). Nav badge = ספירת לא-חשופים בלבד (‏`/api/journal/badge`, לעולם לא תוכן/פוש). `+25 XP` על צפייה בתוצאה חשופה (`journal_reveal_viewed`, idempotent per scenario). מסך B4: R מצטבר (חשוף), CAPITAL SAVES שווה-ערך ל-wins, discipline meter מדאטת דילוג אמיתית, מסגור סימטרי.
  2. **B5 — profile (F5):** `/api/profile` — call-sign (ב-`user_settings`, נגזר מ-email אם לא הוגדר), כרטיס דרגה + סולם (XP_ECONOMY 1000/3000/8000, מ-`levelFor`), "HOW XP IS EARNED" (ארבעת המקורות הנעולים), הגדרות Lens/Risk Style נשמרות (`PUT /api/profile/settings`, display+geometry בלבד), sign-out.
  3. **B6 — academy shell (F6):** 12 מודולים = 12 ה-`academy` ids ב-`concept_tooltips_content.json`, כל אחד מרונדר את תוכן ה-`what` של המונחים שלו (אין שיעורים מומצאים). Deep-link של Concept Tooltip (`/academy#<id>`) נוחת ומדגיש את המודול. `+100 XP` לשיעור — **רק למודולים עם תוכן אמת (≥3 מונחים); מודולי-stub (volume/positioning/regime_transitions) לא מזכים** (`academy_lesson`, idempotent). Plan gating: basic פתוח לכולם · full ל-Advanced+/Pro-trial · שני מודולי בונוס (spike 1000XP, regime_transitions 3000XP) — אורתוגונלי לפלאן.
  4. **B7 — admin console (desktop-first, admin-gated):** כל route תלוי `require_admin` → 403 ל-non-admin. Overview (vitals מדאטת אמת, לא sample: users/trials/MRR-מ-plan prices/scans-day/churn), Users + override פר-משתמש (plan/extend-trial/grant-XP/suspend) עם audit ל-`admin_events`, Tickets queue+thread+reply (email=stub לוגי) + status, Settings editor (`system_settings` editable; score-gate + card-off מוצגים LOCKED), Broadcast compose+audience(all/plan/trial-ending)+channel → נשמר + banner in-app (‏`/api/broadcasts/active`, לעולם לא מכסה SCAN/disclaimer), Notifications log (day-11 reminder + reveal teaser, via `journal_tasks`).
- FILES CREATED: backend: `migrations/028_journal_scenarios_admin.py`, `core/journal.py`, `api/{journal,profile,academy,admin,broadcasts}.py`, `models/{journal,profile,academy,admin}.py`, `app/tasks/journal_tasks.py`, `scripts/run_resolve_scenarios.py`, `tests/test_pkg_b_phase2.py`. frontend: `app/(dashboard)/dashboard/page.tsx` (מומש), `app/(profile)/{profile,settings}/page.tsx`, `app/(academy)/academy/page.tsx`(+`[moduleId]/page.tsx`), `app/(admin)/admin/page.tsx` (מומש), `components/app/BroadcastBanner.tsx`, `lib/app/{types,session,scenario}.ts`, `tests/pkgb2.unit.test.ts`.
- FILES MODIFIED: backend/main.py (5 routers חדשים), api/scan.py (hook ל-`journal.on_scan`), core/entitlements.py (`get_setting_int`). frontend: components/scan/NavDrawer.tsx (badge אמיתי מ-`/api/journal/badge`), app/(scan)/scan/page.tsx (BroadcastBanner), lib/onboarding/concepts.ts (`termsByAcademy`).
- DB CHANGES: migration 028 — `journal_scenarios`, `ticket_replies`, `notifications_log`, `user_settings`; `admin_broadcasts` +audience/+channel columns; system_settings seeds (trial_reminder_day, journal_history_days_free). קיימים מראש: admin_events, admin_broadcasts, support_tickets, churn_reasons, xp_events.
- CONFIG ADDED: אין (jobs משתמשים ב-BYBIT_PUBLIC_BASE_URL + TRIAL_REMINDER_LEAD_DAYS הקיימים).
- VALIDATION: pytest 66/66, frontend unit 18/18, shared node --test 14/14, tsc clean, eslint clean, next build clean (20/20), em-dash lint 0.
- ATP: TC-B4-101..106 (scenario creation/WATCH-excluded, resolution evaluator, reveal-withholding, reveal-on-scan, +25 view idempotent, badge), TC-I-101/102 (profile fallback+settings), TC-B6-101/102 (12 modules, lesson XP + stub/locked), TC-H-201..205 (admin 403, overview, override+audit, settings-guard, broadcast+banner).
- VERSION: v0.9.0
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: המשתמש מקבל את מלוא המעטפת שאחרי הסריקה — יומן retention עם חשיפה נמשכת (pull), פרופיל+דרגות, אקדמיה, ולאדמין קונסולה מלאה לניהול ה-first-100. אין שינוי ב-main/production (dev בלבד).
- DECISIONS (התקבלו תוך כדי — טעונות סקירת נדב):
  1. **CAPITAL SAVES — הגדרה:** הפרומפט קובע "תרחיש לכל PASS + no-setups-day; WATCH לעולם לא תרחיש". במסגרת זו מימשתי SAVE כ-**PASS שה-trigger שלו לא נורה בחלון (אף כניסה לא נפתחה → הון נשמר)**. זה שונה משורת ה-SAVE הפר-מטבע-לא-עובר (LINK) שבפריים B4. שתי הגישות ישרות; בחרתי בכתובה בפרומפט (לא יוצרים תרחישים ל-non-passers). ניתן להרחיב ל-per-coin saves בהמשך. **מבקש אישור/כיוון.**
  2. **Academy "תוכן אמת" = ≥3 מונחים** (9 מודולים מזכים +100, 3 stubs=0). כלל אחיד וישר במקום "מומצא". **לאישור.**
  3. **כותרות מודול בנקודתיים (":") במקום em-dash** של הפריים — חוק ה-no-em-dash גובר.
  4. **Admin = דאטת אמת** (queries), לא ה-SAMPLE של הפריימים (churn=placeholder עד שתצטבר דאטה) — לפי הפרומפט.
  5. **call-sign** נשמר ב-`user_settings` והפרופיל בעליו (fallback מ-email). התמדה מ-onboarding S9 היא follow-up קטן (לא נגעתי בזרימת האונבורדינג).

## [PKG-B-P1 / Package B phase 1: B1 scan + B2 subscribe + B3 nav] — 2026-07-13
- GOAL: לממש את חבילת Design B שלב 1 — מסך הסריקה (B1a–B1g, לב המוצר), עמוד ה-Subscribe (B2), וניווט ההמבורגר + header (B3). Server-authoritative gating, first-scan XP, Chart Standard בגרף הסריקה, E7b why-not, מנוע swing משותף. MINOR.
- SOLUTION (מה עשינו בפועל):
  1. **Shared engine — swing S/R canon:** הועבר `findRecentSwingLevels` (‏{swingHigh,swingLow}) מהכלי האישי (`engine.mjs`) אל `@finaroda/scoring-engine` byte-faithfully — זהו מקור ה-S/R היחיד שהמנוע מודד מולו (liquidity check + כל הטריידים המתועדים). נמחק `lib/onboarding/levels.ts` (קירוב pivot בן שבוע); הגרפים (onboarding + B1) מצביעים כעת ל-`swingLevels` (adapter מעל השיתופי). **Equivalence test** מול העתק verbatim של המימוש האישי על עשרות סדרות דטרמיניסטיות (25×6×4 וקטורים) — swings זהים.
  2. **B1 — scan screen (החלפה מלאה של מסך P2):** בקרות pre-scan (Horizon: SWING פעיל / POSITION נעול + E9 tooltip · Analysis Lens display-only · Risk Style geometry-only · RED-LINE caption); כפתור SCAN (190px) עם ספירת מטבעות לפי הפלאן; אנימציית 4 צעדים נעולה (זהה ל-S2); תוצאות ring/list; **first-scan-of-day XP chip** (‏+50, מהשרת בלבד); **Chart Standard v1** בכל Blueprint (EMA200+EMA7, swing S/R, Blueprint levels, candle-tap OHLC, annotation tooltips) עם **layer gating** (Free=chart+EMA200, paid=all + SEE PLANS); Blueprint מלא בכל פלאן; **E7b** — כל מטבע (כולל non-passers) לחיץ → אותו גרף + שורת "why not" בשפה פשוטה עם Concept Tooltip, ללא ציון/משקל/נוסחה; empty state F1b (חגיגת דילוג, ללא CTA לסריקה); "new scan" חוזר למסך הבקרות (לא re-scan מיידי). כל סריקה נשמרת ל-score_log (יומן F3 — נדחה עד בניית F3, מתועד ב-HANDOFF).
  3. **B2 — Subscribe:** 4 עמודות Free/Basic/Advanced/Pro; **טבלת השוואה חובה** (TC-J-002) עם Free ראשון ותמיד גלוי; D1 trial CTA (‏"START 14 DAYS OF PRO — NO CREDIT CARD", ללא כרטיס); 3 trust shields (no auto-charge / reminder day 11 / you decide); "same engine, same threshold" line; "Continue on Free". מחירים/מטבעות/מטבעות-לסריקה נקראים מ-`system_settings` דרך `GET /api/plans` (admin-editable).
  4. **B3 — nav + header:** header אחיד (‏≡ / FINARODA / LevelMeter chip) שמחליף את הישן, בכל מסכי B; drawer המבורגר (Dashboard[UPDATE]/Profile/Academy/Settings) + identity block עם LevelMeter (תג משושה + דרגה + XP); "Report a problem" שמגיש טיקט אמיתי (`POST /api/support/tickets`).
  5. **Backend gating (server-authoritative):** `GET /api/scan/entitlements` (coins/scan + chart_layers + scans/day לפי tier) — binding; `POST /api/scan/events` דוחה סריקה מעל מכסת המטבעות (403 PLAN_COIN_LIMIT); first-scan XP (+50, source=daily_first_scan, ref=date, idempotent per day, השרת בעל-הסמכות על הכמות); `GET /api/plans` (public); `POST /api/support/tickets`; `POST /api/cardcom/trial` (D1 no-card trial route).
- FILES CREATED: shared: findRecentSwingLevels (scoring-engine.js) + test. frontend: lib/chart/swings.ts, lib/scan/{chart,entitlements}.ts, components/scan/{AppHeader,BlueprintChart,NavDrawer,NonPasser}.tsx, app/subscribe/page.tsx, tests/scan.unit.test.ts. backend: core/entitlements.py, api/{support,plans}.py, models/support.py, migrations/027_scan_entitlements.py, tests/test_b1_gating.py.
- FILES MODIFIED: shared/scoring-engine.js(+test), frontend/src/types/scoring-engine.d.ts, components/onboarding/EpisodeChart.tsx (swingLevels + emaMode "ema200"), components/scan/{Controls,Results,ScanningLog,TradingBlueprint}.tsx, app/(scan)/scan/page.tsx, app/paywall/page.tsx (→ redirect /subscribe), components/onboarding/OnboardingFlow.tsx (fork→/subscribe), lib/scan/{types,bybit,engine,persist}.ts, lib/api.ts, backend/main.py, api/scan.py, api/cardcom.py, models/scan.py. DELETED: frontend/src/lib/onboarding/levels.ts.
- DB CHANGES: migration 027_scan_entitlements (system_settings seeds: scan_coins_free, chart_layers_{free,basic,advanced,pro}, scans_per_day_{…}). support_tickets/xp_events tables pre-existed.
- CONFIG ADDED: אין (הכל דרך system_settings).
- VALIDATION: pytest 55/55, frontend unit 14/14, shared node --test 14/14, tsc clean, eslint clean, next build clean, em-dash lint 0.
- ATP: TC-B-101..108 (scan gating, chart layers, E7b why-not, first-scan XP, empty state, new-scan routing), TC-B-201 (subscribe table + trial), TC-B-301 (nav + report-a-problem), TC-B-401 (swing equivalence).
- VERSION: v0.8.0
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: המשתמש מקבל את מסך הסריקה המלא (הלב), עמוד מנויים אמיתי, וניווט — עם gating אכיף בשרת ו-XP אמין. הליבה הדטרמיניסטית, סף 85/82, וטרמינולוגיית המחשבון לא נגעו.
- DECISIONS: (1) gating = server-as-authority + client compute (הסריקה נשארת client-side; leakage לא-מתמשך מקובל). (2) swing canon = המימוש האישי (לא ה-pivot של ה-SaaS). (3) journal scenarios נדחו (אין F3 plumbing עדיין) — נשמר ל-score_log. (4) B7 admin console = שלב 2. (5) empty-state "skipped X of Y" הוחלף ב-badge מבוסס-נתון-אמיתי (ללא יחס-דילוג מומצא, §8).

## [F13-ONBOARDING-V2 / validation round 2 (polish)] — 2026-07-13
- GOAL: 10 פריטי ליטוש מ-click-through של נדב (frontend-focused). PATCH.
- SOLUTION (מה עשינו בפועל):
  1. **S0:** auto-advance הוחלף בכפתור **LET'S START** (terminal, primary); אין היעלמות מתוזמנת.
  2. **Signup flash (reopened):** התווסף **render-gate** — routing (‏`/me` → completed?) נפתר לפני שהזרימה מרונדרת, כך ש-redirect אסינכרוני מאוחר לא חוטף מסך באמצע (הגורם ל-flash אצל משתמש שהשלים אונבורדינג בבדיקות חוזרות). המעבר S5→S6 אוחד ל-`createOnce` (מעבר יחיד). +unit test.
  3. **Header redesign:** מד XP + caption אפור → רכיב **LevelMeter** קומפקטי (תג משושה + דרגה + XP + התקדמות), mono, ניגודיות גבוהה, ללא caption אפור.
  4. **Tooltip context guard:** `renderNow` מושתק לגמרי כשחסר placeholder פשוט (long_short לפני בחירה → אין שורת now, תוקן ה-glitch של direction מוקדם). +unit test.
  5. **Chart header:** סימבול בולט בשורה/badge נפרד ממחיר/טווח/רזולוציה — בכל הגרפים כולל S10.
  6. **S8 pre-scan framing:** "Real case: ADA, 25 Jun 2026. Press SCAN to see what the engine found." מעל הגרף.
  7. **S8 post-scan:** (a) `risk_price` נוסף לסכמת האפיזודה + seed 0.1511 (Calculated Risk Level) ומצויר; (b) תוויות Trigger/Risk/Target ללא חפיפה (declutter של תוויות צד); (c) "Why PASS" על ה-chip — שורה לכל check מאוחסן (regime/weekly/timing/volume) מלשון תוכן ה-concepts.
  8. **XP = LEVEL framing:** "LVL 01 · Strategy Apprentice" + התקדמות 300/1,000 → "LVL 02 · Risk Manager" (סולם `XP_ECONOMY.md`). **חגיגת level-up** (רטט ייעודי + אנימציה) רק בחציית סף דרגה, לעולם לא על צבירת XP; צבירה = רטט עדין (E6). +unit test (math + gating).
  9. **S10 copy:** נוסח חד-משמעי — "revealed on your NEXT scan. That is how the journal closes the loop" (לא ניתן לקריאה כ-"won't reveal").
  10. **S11 table:** נעטף ב-`overflow-x:auto` + `min-width`, מסונכרן למסגרת ברוחבי מובייל.
- FILES CREATED: frontend/src/lib/onboarding/{xp,tooltipTemplate,once}.ts, frontend/src/components/onboarding/{LevelMeter,LevelUp,WhyPass}.tsx, frontend/tests/onboarding.unit.test.ts.
- FILES MODIFIED: backend/{migrations/023_episodes,models/onboarding,migrations/seed_data/onboarding_episodes.json}, backend/tests/test_p3_onboarding.py, frontend onboarding {OnboardingFlow,OnboardingShell,EpisodeChart,ConceptTooltip,concepts,haptics,types}.* , frontend/{tsconfig,package.json}, globals.css, FINARODA_ONBOARDING_SPEC/SAAS_SPEC/ATP/CHANGELOG/VERSIONS/HANDOFF. DELETED: XPMeter.tsx.
- DB CHANGES: אין (risk_price/checks ב-outcome JSON של episodes; seed re-run). CONFIG ADDED: אין.
- VALIDATION: **pytest 43/43** (+risk/checks) · **frontend unit 7/7** (node --test, type-strip) · **tsc clean** · **eslint clean** · **next build 17/17** (/onboarding 16.8kB) · em-dash lint 0.
- ATP: +TC-P3-ONB-13..18.
- VERSION: v0.7.1 (PATCH).
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: אונבורדינג מלוטש — כניסה מפורשת, header טרמינלי עם LEVEL, tooltips נקיים ומושתקים בהקשר, גרף עם risk+Why PASS, קופי יומן חד-משמעי, טבלה תואמת-מסגרת. תשתית unit-tests ל-frontend (node --test).
- DECISIONS: (1) flash זוהה כ-yank אסינכרוני של redirect מ-`/me` (משתמש שהשלים, בבדיקות חוזרות) → נפתר ב-render-gate + guard; (2) unit-tests ב-`frontend/tests` דרך node `--experimental-strip-types` (Node 22) — פונקציות טהורות (xp/tooltipTemplate/once); `allowImportingTsExtensions` ל-tsc; (3) risk/checks ב-outcome (נחשפים post-scan עם ה-Blueprint), לא setup; (4) חגיגת level-up רדומה באונבורדינג (300<1,000) אך מנגנון קיים ונבדק.

## [F13-ONBOARDING-V1 / validation round 1 + tooltip content] — 2026-07-12
- GOAL: יישום הערות ה-click-through של נדב + חיווט תוכן ה-Concept Tooltips + Chart Standard v1. פיצ'ר/תיקונים (MINOR).
- SOLUTION (מה עשינו בפועל):
  - **Tooltip content:** `concept_tooltips_content.json` (root, נעול, 46 מונחים) חובר. `concepts.ts` טוען אותו + מנוע תבניות ל-`now` (‏`{key}` + `{cond:'a'|cond2:'b'}`, placeholder חסר → ריק בחן). `ConceptTooltip` מרנדר what+now+Learn more, ctx per-שימוש, בועה עם clamp/flip (לא נחתכת במובייל) + כפתור X + סגירה בהקשה בחוץ.
  - **Bugs:** (a) XP anti-farming — מענק אונבורדינג **חד-פעמי לכל החיים (300) בהשלמה**; migration **026** אינדקס unique חלקי על `xp_events(user_id) WHERE source='onboarding'`; הרצה חוזרת = 0 (+regression test). (b) Routing — guard ב-mount (`/me`→completed→`router.replace('/scan')`), יציאה מ-S11 ב-replace; back לא חוזר לאונבורדינג. (c) Signup flash — הוסר anti-pattern של side-effect ב-state-updater; מעבר יחיד עם `signingUp` guard. (d) "new scan" בסריקה החיה → `setPhase('idle')` (בקרים, לא re-scan מיידי). (e) יתומי שורה — `noOrphan()` + `text-wrap: balance/pretty`.
  - **Product decisions (נדב 12/07):** BUY/SELL → **LONG/SHORT** (S1/S1a/tooltip `long_short`). **שני ענפי S1a שונים מנרות אמת:** LONG=fade (‎−10%), SHORT=**squeeze** (‎+2.06% נגד השורט ל-65,624 ואז fade). E1 נבחר-מחדש לנר-החלטה 20/06 (surge) — assertion בבנייה מוודאת squeeze≥1.5% + fade≤−5%. **כלל קופי: אין em dashes** — הוסרו מכל copy/JSX; +lint (pytest) שנכשל על U+2014.
  - **Chart Standard v1** (רכיב אחד, בסיס Package B): כותרת הקשר (symbol/price/range/"Daily candles") · EMA200+EMA7 עם תוויות · swing S/R (`computeRangeLevels` חדש, pivots) · Blueprint levels (S8) · תגי Spike/Entry שפותחים tooltip · הקשה על נר → OHLC (`ohlc`).
- FILES CREATED: frontend/src/lib/onboarding/{levels,text}.ts, frontend/src/lib/onboarding/concept_tooltips_content.json (עותק bundled), backend/migrations/026_xp_onboarding_once.py, backend/tests/test_content_copy.py.
- FILES MODIFIED: backend/{api/onboarding,models/onboarding}.py, backend/migrations/{023,seed_data/onboarding_episodes.json}, backend/tests/test_p3_onboarding.py, frontend onboarding {OnboardingFlow,ConceptTooltip,EpisodeChart}.tsx + {concepts,api,types}.ts, scan/page.tsx + 10 placeholder pages (em-dash copy), globals.css, FINARODA_ONBOARDING_SPEC/SAAS_SPEC/EPISODES/ATP/CHANGELOG/VERSIONS/HANDOFF.
- DB CHANGES: migration 026 (partial unique index, anti-farming). CONFIG ADDED: אין.
- VALIDATION: **pytest 42/42** (was 39; +content/XP-replay) · **tsc clean** · **eslint clean** · **next build 17/17** (/onboarding 15.1kB).
- ATP: +TC-P3-ONB-06..12.
- VERSION: v0.7.0 (MINOR).
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: tooltips חיים עם 46 מונחים; XP חסין-farming; routing נכון; שני ענפי S1a אמיתיים; גרף סטנדרטי אחד לכל המסכים ובסיס ל-Package B.
- DECISIONS: (1) XP אונבורדינג = מענק בודד בהשלמה (unique user+source) במקום 4 refs — נאמן ל-"חד-פעמי" של XP_ECONOMY §1. (2) E1 נר-החלטה = 20/06 surge (מאפשר גם LONG-fade וגם SHORT-squeeze מאותם נרות אמת). (3) עותק ה-JSON ב-frontend + drift-guard ב-pytest (root = מקור-אמת). (4) em-dash lint על source (strings/JSX, הערות מוחרגות) = מעשי ל-built copy.

## [F13-ONBOARDING / "First 60 Seconds" — episode engine + 12 screens] — 2026-07-12
- GOAL: לממש את **F13** (`FINARODA_ONBOARDING_SPEC.md` v1.2) — 12 מסכי אונבורדינג + רכיבים משותפים, עם ליבת אפיזודות אמת, withholding צד-שרת, XP ו-funnel. פיצ'ר חדש (MINOR).
- SOLUTION (מה עשינו בפועל):
  - **Episode engine (backend):** migration **023** `episodes` (הורחב: `ext_id`/`direction`/`entry_index`/`entry_price`/`outcome`, כל נר עם `ema7`/`ema200` אמיתיים). **Seed** `backend/data/onboarding_episodes.json` נבנה מ-Bybit עם **assertions של אמת אמפירית** — הבנייה נכשלת אם הנרות לא תומכים בכניסה/תוצאה. E1 (trap) **נבחר-מחדש LINK→BTCUSDT 25/06** אחרי אימות klines (LINK עלה בחלון המקורי — שגיאת אצירה; מתועד ב-`EPISODES_AND_VERIFIED_NUMBERS.md`). E3 (ADA short +3R), E4 (ETH long +3.33R) תואמים את המסמך.
  - **Withholding + API:** migration **024** `xp_events`, **025** `onboarding_funnel_events`. router `api/onboarding.py`: `GET /episodes[/{id}]` מחזיר **רק setup** (ללא outcome/reveal candles); `POST …/{id}/reveal` חושף; `POST /xp` (amount צד-שרת, idempotent), `POST /funnel` (optional-auth), `POST /complete`.
  - **Frontend:** `/onboarding` route + `OnboardingFlow` (S0–S11 + ענף S1a) · `EpisodeChart` (SVG candlestick in-app מנרות אמת — **לא recharts**, נמנע peer-dep של React 19; רפרנס מנוע ה-SVG v25.67) · `ConceptTooltip` (תוכן placeholders keyed by term id — הגדרות פיננסיות יסופקו ע"י נדב, לא נכתבו) · `XPMeter` · `Disclaimer` על כל מסך · `vibrateScan()` (fallback שקט ל-iOS) חובר גם למסך הסריקה האמיתי.
  - **ACs מולאו:** "Analysis, not financial advice" על כל מסך · outcome של S10/S1 **לא ב-DOM** לפני reveal (נבדק) · vibrate+fallback · funnel §5 · טבלת Free-vs-paid ב-S11.
- FILES CREATED: backend/data/onboarding_episodes.json, backend/migrations/{023_episodes,024_xp_events,025_onboarding_funnel_events}.py, backend/models/onboarding.py, backend/api/onboarding.py, backend/tests/test_p3_onboarding.py, frontend/src/lib/onboarding/{types,api,haptics,anon,concepts}.ts, frontend/src/components/onboarding/{OnboardingFlow,OnboardingShell,EpisodeChart,ConceptTooltip,XPMeter,Disclaimer}.tsx, frontend/src/app/(onboarding)/onboarding/page.tsx.
- FILES MODIFIED: backend/main.py (router), backend/tests/test_smoke.py (+3 tables), backend/models/onboarding.py (ema fields), frontend scan/page.tsx (vibrate), FINARODA_SAAS_SPEC.md (§5.7/§5.8), EPISODES_AND_VERIFIED_NUMBERS.md (E1 re-pick), ATP/CHANGELOG/VERSIONS/SESSION_HANDOFF.
- DB CHANGES: migrations 023/024/025 (episodes, xp_events, onboarding_funnel_events). CONFIG ADDED: אין.
- VALIDATION: **pytest 39/39** (was 27; +12 onboarding) · **tsc clean** · **eslint clean** · **next build 17/17** (/onboarding 7.63kB). shared node --test 12/12 (unchanged).
- ATP: +TC-P3-ONB-01..05 (01–04 ✅ automated; 05 build-verified, manual click-through ⬜ pending — Design סבב 2).
- VERSION: v0.6.0 (MINOR — פיצ'ר חדש תואם-אחורה)
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: מסלול אונבורדינג עובד מקצה-לקצה על נתוני אמת; מנוע אפיזודות + withholding + XP idempotent מוכנים; מד XP + tooltip + haptics חוברו. ליטוש חזותי סופי (fonts/animations) = Design סבב 2.
- DECISIONS: (1) E1 נבחר-מחדש ל-BTC אחרי שהתגלה שנרות LINK 30/06 סתרו את שיעור ה-trap (אישור נדב בסשן). (2) EpisodeChart ב-SVG in-app במקום recharts — נמנע peer-dep של React 19 ב-build של Vercel; זהה בתוצאה (נרות אמת, ללא צילומים) — **מסומן לאישור נדב**. (3) הגדרות ה-tooltip הן placeholders — נדב יספק את התוכן. (4) signup ב-S5: נתיב magic-link מלא (בdev סוגר את הלולאה in-session); Google/Apple = כפתורים, wiring מלא של OAuth SDK = סבב 2 (auth bundle).

## [DOCS-XP-ECONOMY / XP_ECONOMY.md v1.0 — סגירת החוב + תיקון UX §5] — 2026-07-11
- GOAL: לעגן את `XP_ECONOMY.md` v1.0 (נעול, repo root) במסמכי מקור-האמת, לסגור את חוב כלכלת ה-XP (Onboarding §8 / ALIGNMENT D3), ולתקן את הסתירה ב-Status Tiers. **דוקים בלבד — אפס שינוי קוד/מנוע/סקורר/backend.**
- SOLUTION (מה עשינו בפועל):
  - **UX §5 (תיקון הסתירה):** קריטריון שלב "מדייק" שונה מ"היסטוריית מה-היה-קורה חיובית" (תגמול על תוצאות — סתר trust-not-engagement) ל-**סף XP על משמעת/למידה**. נוספה הערת תיקון מפורשת: שלבים = XP בלבד, איכות ה-what-if נשארת **סטטיסטיקת דשבורד בלבד**, לעולם לא קריטריון שלב. הפניה ל-`XP_ECONOMY.md`.
  - **PRD F5 (עקביות):** אותה סתירה תוקנה — "Precise" = סף XP, לא what-if; AC1 מחריג במפורש תגמול מתוצאות what-if.
  - **PRD F6 (Academy):** נוסף קישור ל-`XP_ECONOMY.md` — +100 XP לשיעור, דרגות פותחות מודולי בונוס (Spike Autopsies / Regime Transitions) **אורתוגונלית לשערי פלאן**; AC4 חדש.
  - **SPEC §5.6 (חדש):** טבלת `xp_events (user_id, source, ref, amount, ts)` עם `UNIQUE (user_id, source, ref)` (idempotent, הגנת farming), מקורות מרשימה סגורה, כתיבה **צד-שרת בלבד**, דרגות נגזרות מ-`SUM(amount)`.
  - **Onboarding §4/§8:** §8 סומן **✅ נסגר → `XP_ECONOMY.md`**; §4 מפנה למקורות ה-XP הסגורים (+50 סריקה ראשונה/יום · +100 שיעור · +25 יומן שנחשף · streak לא קיים ב-v1).
  - **ATP:** +TC-DOCS-XP01 (doc-check: tiers=XP בלבד · F6 קישור · §8 סגור · xp_events idempotent/server-side).
  - **סקופ מעבר להנחיה המפורשת:** תוקנה גם הסתירה הזהה ב-**PRD F5** (ההנחיה נקבה רק ב-UX §5) — הושארתה הייתה משאירה RED-LINE contradiction בין שני מסמכי מקור-אמת. מסומן לתשומת לב נדב.
- FILES CREATED: אין (XP_ECONOMY.md נחת בעבר, נעול).
- FILES MODIFIED: FINARODA_SAAS_UX.md, FINARODA_SAAS_PRD.md, FINARODA_SAAS_SPEC.md, FINARODA_ONBOARDING_SPEC.md, ATP.md, CHANGELOG.md, VERSIONS.md, SESSION_HANDOFF.md.
- APP/ENGINE/SCORER/BACKEND: **unchanged** (docs only).
- DB CHANGES: אין (סכמת `xp_events` תועדה ב-SPEC §5.6, מימוש/migration ⬜ pending — P3/P4). CONFIG ADDED: אין.
- VALIDATION: docs-only (אפס שינוי קוד). באסליין ירוק אחרון: pytest 27/27 · shared node --test 12/12 · tsc clean · eslint clean.
- ATP: +TC-DOCS-XP01 (✅ doc-check; מימוש xp_events ⬜ pending).
- VERSION: v0.5.3 (PATCH — יישור/תיקון דוקים, אפס קוד)
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: כלכלת ה-XP מעוגנת במקור-אמת יחיד ונעול; הוסרה סתירת ה-Status Tiers (what-if → XP) משני מסמכים; מתכנת המימוש מקבל סכמת `xp_events` מוכנה עם הגנת idempotency.
- DECISIONS: תיקנתי גם את PRD F5 (לא רק UX §5) לשמירת עקביות בין מסמכי מקור-אמת — סומן לאישור נדב. דרגות נגזרות מ-SUM(amount) ולא כעמודה נשמרת (למניעת סנכרון כפול).

## [DOCS-E9-HORIZON / Horizon selector — SWING active / POSITION locked] — 2026-07-11
- GOAL: ליישם את **E9** (`ALIGNMENT_2026-07-09.md`) — בקר Horizon במסך הסריקה. **דוקים בלבד — אפס שינוי קוד/מנוע.**
- SOLUTION (מה עשינו בפועל):
  - **PRD:** נוסף **F1c — Horizon Selector**. SWING (1–7 days) פעיל מ-v1; POSITION (weeks+) מוצג נעול עם קופי מאושר "In validation. Unlocks when it earns it." + tooltip. F1 flow step 1 עודכן (Horizon לצד Lens/Risk Style). POSITION (המנוע) נוסף ל-V2 backlog. קריטריון פתיחה 30+/2+ משטרים; מועמד Pro.
  - **UX §3 + §8:** Horizon נוסף לשורת הבקרים pre-scan (ליד Lens/Risk Style); הובהר ש-POSITION הוא **יקום נפרד** ולא toggle קוסמטי; נוספה הערת מינימליזם (3 בקרים = תקרה).
  - **ROADMAP X1:** Horizon selector נוסף להיקף Design סבב 2.
  - **ATP:** נוסף TC-DOCS-E06 (SWING active / POSITION locked + honesty guardrail + RED LINE פר-יקום).
  - **⚠ honesty guardrail (הוטמע ב-AC2 של F1c + TC-E06):** הקופי "in validation" אמיתי **רק** אם קיים מודל POSITION שרושם תוצאות ל-`score_log`. אין כרגע מנוע position (ה-edge המאומת = swing/EMA7 בלבד) — לכן POSITION הוא "planned", לא "in validation". **פתוח להכרעת נדב:** לבנות position-outcome log לפני הצגת הקופי, או לרכך ל-future-tense. תועד גם כי לפי הקריטריון POSITION עשוי לעולם לא להיפתח (אין ETA).
- FILES MODIFIED: FINARODA_SAAS_PRD.md, FINARODA_SAAS_UX.md, ROADMAP.md, ATP.md, CHANGELOG.md, VERSIONS.md, SESSION_HANDOFF.md. (ALIGNMENT_2026-07-09.md — E9 נכנס כמקור.)
- APP/ENGINE/SCORER/BACKEND: **unchanged** (docs only).
- DB CHANGES: אין. CONFIG ADDED: אין.
- VALIDATION: docs-only (אפס שינוי קוד). באסליין ירוק אחרון: pytest 27/27 · shared node --test 12/12 · tsc clean · eslint clean.
- ATP: +TC-DOCS-E06 (⬜ pending implementation; honesty-guardrail copy decision ⚠ open).
- VERSION: v0.5.2 (PATCH — יישור דוקים, אפס קוד)
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: מסך הסריקה יקבל בקר Horizon (SWING פעיל / POSITION נעול). המימוש ⬜ pending — ROADMAP X1. חובה לפתור את honesty-guardrail לפני שהקופי מוצג בפועל.
- DECISIONS: POSITION מוגדר כ**יקום-מדידה נפרד** (סף/base-rate משלו), לא toggle קוסמטי — כדי לא לטשטש את ה-RED LINE. honesty guardrail עוגן ב-AC (principle 8) במקום להעתיק את הקופי המאושר as-is בלי הסתייגות; הקופי המאושר תועד + הסתייגות מפורשת + open item לנדב.

## [DOCS-ALIGN-E-2026-07-11 / יישום section E — החלטות מוצר 11/07] — 2026-07-11
- GOAL: ליישם את section E של `ALIGNMENT_2026-07-09.md` (החלטות נדב 11/07) על מסמכי מקור-האמת. **דוקים בלבד — אפס שינוי קוד/מנוע/סקורר/backend.**
- SOLUTION (מה עשינו בפועל):
  - **E1 — Concept Tooltip (F-education):** נוסף **F14** ל-PRD — קומפוננטת בועת-לימוד אחידה על כל מונח מהאונבורדינג ואילך, תוכן מהאקדמיה (F6), display-only (לא נוגע ב-RED LINE). UX §3 (בתוך ה-Blueprint) + §8 (אינטראקציה).
  - **E2 — free-coin analysis:** נוסף ל-PRD backlog **V2 בלבד** — ניתוח מטבע מעבר ליקום 10, בפלאנים בתשלום, אחרי ולידציה+אישור נדב, עם **תווית חובה "Learning mode — outside the validated universe"**. לא v1.
  - **E3 — טבלת השוואה בעמוד Subscribe:** PRD F7 + UX §6 — הטבלה (Free forever: 1 scan/day · 2 coins · full Blueprint · journal 7 days · no export) **חייבת להיות מוצגת בעמוד ה-Subscribe**. נוסף AC ל-paywall + **TC-J-002** copy-guard.
  - **E5 — תפריט המבורגר אחרי תשלום** (Dashboard/Profile/Academy/Settings): נכנס להיקף Design סבב 2 (ROADMAP X1). UX §8.
  - **E6 — רטט SCAN:** SPEC §6.2 — `navigator.vibrate` עם fallback שקט (iOS Safari לא נתמך → לא ירטוט, בלי שגיאה).
  - **E7 — Live Chart + overlays פר-מטבע:** נוסף **F15** ל-PRD + UX §3 — גרף חי (recharts מ-kline) עם שכבות הסבר; gating: Free=chart+EMA200 / בתשלום=כל השכבות. Design סבב 2. display-only (RED LINE).
  - **E8 — באנר טיקר רץ:** נרשם כ-**REJECTED** ב-PRD §17 (סותר trust-not-engagement + רישוי דאטה למדדים/סחורות); החלופה = שורת marketContext סטטית פר-סריקה (קיימת); פתיחה מחדש רק כ-opt-in כבוי-כברירת-מחדל.
  - **E4** — ETF ממונפים: מסלול מחקר בכלי האישי בלבד, **לא נוגע ב-SaaS** — לא שונה דבר במסמכי ה-SaaS (מכוון).
  - **Consistency pass:** F14/F15 מזהים ייחודיים (F1–F13 קיימים); grep ל-ticker/hamburger/vibrate/Learning mode — אין סתירות. RED LINE §3.5.5, סף 85/82, client-side fetch, טרמינולוגיית המחשבון — לא נגעתי.
- FILES MODIFIED: FINARODA_SAAS_PRD.md, FINARODA_SAAS_UX.md, FINARODA_SAAS_SPEC.md, ROADMAP.md, ATP.md, CHANGELOG.md, VERSIONS.md, SESSION_HANDOFF.md. (ALIGNMENT_2026-07-09.md — section E נכנס כמקור.)
- APP/ENGINE/SCORER/BACKEND: **unchanged** (docs only).
- DB CHANGES: אין.
- CONFIG ADDED: אין.
- VALIDATION: docs-only (אפס שינוי קוד), אך הורץ לאימות: pytest **27/27** ✅ · shared node --test **12/12** ✅ · tsc clean ✅ · eslint clean ✅.
- ATP: נוספו TC-J-002 (copy-guard, E3) + TC-DOCS-E01..E05 (E01-E03 ⬜ pending implementation; E04/E05 ✅ doc-check).
- VERSION: v0.5.1 (PATCH — יישור דוקים, אפס קוד)
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: מסמכי מקור-האמת עקביים עם החלטות נדב 11/07. המימוש בפועל (F14 tooltip, F15 live chart, טבלה בעמוד Subscribe, vibrate, hamburger) ⬜ pending — ROADMAP X1 / P4.
- DECISIONS: free-coin analysis (E2) נרשם כ-V2 מפורש (לא MVP) כדי לא לזהם את יקום ה-base-rate המאומת; ticker banner (E8) נדחה במפורש ב-§17 (חדש: subsection "פריטים שנדחו") ולא רק הושמט, כדי שלא ייפתח מחדש בטעות.

## [D1-TRIAL-NO-CARD / trial ללא כרטיס + downgrade ל-Free] — 2026-07-09
- GOAL: לממש את D1 (trial ללא כרטיס) בקוד ה-billing, לפי SPEC §9/§12.3 + PRD F7 שיושרו במשימת הדוקים. trial בלי כרטיס/tokenization, בלי חיוב אוטומטי; בסוף ה-trial המשתמש עובר ל-Free (D2) — לעולם לא מחויב. לכידת כרטיס רק בהמרה אקטיבית לתשלום.
- SOLUTION (מה עשינו בפועל):
  - **`start_trial`** (`core/cardcom_service.py`): ללא כרטיס/tokenization; `next_billing_at=NULL` (אין חיוב אוטו). ברירת מחדל plan=`pro` (14 ימי Pro מלא, לפי onboarding). event `trial_started` נשמר. re-trial → 409.
  - **`expire_trials`**: trial שפג → `tier='free'`, `subscription_status='none'` (מצב ה-Free הקנוני; לא expired/blocked, `next_billing_at=NULL`); event חדש `trial_ended_to_free`. הפונקציה מחזירה `{"moved_to_free": N}`.
  - **`run_renewal_batch`**: הצטמצם ל-`subscription_status='active'` בלבד — trial (חסר כרטיס/next_billing) לעולם לא נכנס למועמדי החיוב.
  - **תזכורת יום 11**: `trial_ending_soon_task` יורה `TRIAL_REMINDER_LEAD_DAYS` (ברירת מחדל 3) לפני סוף ה-trial (יום 11 מתוך 14) בחלון יומי; config חדש `TRIAL_REMINDER_LEAD_DAYS`. railway.toml cron comment עודכן day-13→day-11.
  - **לכידת כרטיס בהמרה**: `initiate_checkout` (Cardcom LowProfile) — ללא שינוי לוגי; זהו רגע לכידת הכרטיס היחיד. נשאר בגייטינג TEST (503 עד `FEATURE_CARDCOM_LIVE=true`).
  - **Frontend**: `paywall/page.tsx` — הקופי "card on file" הוחלף ב"no credit card / card only at paid plan / continue on Free"; כפתור "Start trial"→"Choose plan".
  - **Webhook/HMAC/charge_recurring**: ללא שינוי מעבר לצמצום ה-WHERE של ה-renewal.
- FILES MODIFIED: backend/core/cardcom_service.py, backend/config.py, backend/app/tasks/billing_tasks.py, backend/tests/test_p1_auth_billing.py, railway.toml, frontend/src/app/paywall/page.tsx, ATP.md, ROADMAP.md, CHANGELOG.md, VERSIONS.md, SESSION_HANDOFF.md.
- FILES CREATED: backend/migrations/022_subscription_events_trial_to_free.py.
- DB CHANGES: **migration 022** — rebuild של `subscription_events` להוספת `event_type='trial_ended_to_free'` ל-CHECK (SQLite לא תומך ALTER ל-CHECK; שורות/עמודות/index נשמרו). ספירת הטבלאות ללא שינוי.
- CONFIG ADDED (שמות בלבד): `TRIAL_REMINDER_LEAD_DAYS`.
- VALIDATION: pytest **27/27** ✅ · shared node --test 12/12 ✅ · tsc clean ✅ · eslint clean ✅.
- ATP: TC-F-005/006 נכתבו מחדש (no-card trial + Free downgrade); נוספו TC-F-007 (re-trial 409) + TC-F-008 (renewal לא מחייב trial); TC-DOCS-001/002 → ✅.
- VERSION: v0.5.0 (MINOR — פיצ'ר תואם-אחורה: מודל trial חדש)
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: משתמש מתחיל trial בלי כרטיס ובלי סיכון חיוב; בסוף ה-trial עובר ל-Free (המשך שימוש, לא חסום). חיוב קורה רק אחרי בחירה אקטיבית של פלאן בתשלום. staging נשאר TEST mode — אין חיוב אמיתי.
- DECISIONS: Free מיוצג כ-`tier='free' + subscription_status='none'` (מצב ה-Free הקיים) — בלי להרחיב את CHECK של subscription_status (נמנע rebuild של טבלת users הכבדה); event `trial_ended_to_free` כן נוסף כי הוא נחוץ ל-audit/analytics. ברירת מחדל trial plan הועברה ל-`pro` (Pro מלא, תואם onboarding).

## [DOCS-ALIGN-2026-07-09 / יישור מסמכי מקור-אמת ל-ALIGNMENT] — 2026-07-09
- GOAL: ליישר את כל מסמכי מקור-האמת (PRD/SPEC/UX/LEGAL/ROADMAP/ATP) להכרעות נדב ב-`ALIGNMENT_2026-07-09.md` ו-`FINARODA_ONBOARDING_SPEC.md` (v1.1). **דוקים בלבד — אפס שינוי קוד/מנוע/סקורר.**
- SOLUTION (מה עשינו בפועל):
  - **D1 — Trial ללא כרטיס** (change order מאושר, מחליף את "trial עם כרטיס" הנעול): SPEC §9 + §12.3 → 14 יום, ללא tokenization בהרשמה, ללא חיוב אוטומטי, תזכורת יום 11, בסוף בחירה אקטיבית (פלאן/Free), לכידת כרטיס ברגע ההמרה. PRD F7 (flow + AC1/AC2 שוכתבו) + §17. UX journey שלב 4 + §6. LEGAL §2.6. ROADMAP S3 (⬜ pending implementation — start_trial לעיבוד מחדש).
  - **D2 — Free tier חדש:** שורת Free בטבלאות PRD F7 / SPEC §9 / UX §6 — סריקה 1/יום · 2 מטבעות · Blueprint מלא · F3 מוגבל 7 ימים · ללא ייצוא · academy בסיסי, נשלט `system_settings`. paywall/fork: "Continue on Free". SPEC §12 החלטה 8.
  - **D3 — XP:** נותר פתוח, **לא מומש**. נוסף ל-PRD §17 open items ("XP economy pending — conflict with UX §9.4; proposed +XP on first scan of the day only").
  - **D4 — English UI:** נעול, ללא שינוי.
  - **F13 — "First 60 Seconds" onboarding simulation:** נרשם ב-PRD (spec = `FINARODA_ONBOARDING_SPEC.md` v1.1, משלים F12), Design סבב 2 (ROADMAP X1 — נוספו מסכי האונבורדינג).
  - **F3 reveal-gating (B3):** תוצאה נחשפת בסריקה הבאה + teaser "journal has an update" (pull-not-push).
  - **Data/learning (B2/B4):** SPEC §5.2 — note לעמודת `regime_state TEXT` עתידית (bear/bull/transition, BTC, N=5 hysteresis). SPEC §5.5 — טבלת `episodes` (kline אמיתי מתוארך, רינדור recharts, לא צילומי TradingView/Bybit). PRD §3 principle 8 — אמת אמפירית בקופי.
  - **Consistency pass:** grep ל-"עם כרטיס"/"with card" — כל ההיטים שנותרו הם הפניות מכוונות ל"מה שהוחלף" או ה-CHANGELOG ההיסטורי. RED LINE (§3.5.5), סף 85/82, client-side fetch, וטרמינולוגיית המחשבון — לא נגעתי.
- FILES MODIFIED: FINARODA_SAAS_SPEC.md, FINARODA_SAAS_PRD.md, FINARODA_SAAS_UX.md, FINARODA_SAAS_LEGAL_DRAFT.md, ROADMAP.md, ATP.md, CHANGELOG.md, VERSIONS.md, SESSION_HANDOFF.md. (ALIGNMENT_2026-07-09.md + FINARODA_ONBOARDING_SPEC.md — נכנסו ל-repo כמקור.)
- APP/ENGINE/SCORER/BACKEND: **unchanged** (docs only).
- DB CHANGES: אין (רק *תיעוד* של migration עתידי ל-regime_state + טבלת episodes — לא מיושם).
- CONFIG ADDED: אין.
- VALIDATION: pytest 25/25 ✅ · shared node --test 12/12 ✅ · tsc clean ✅ · eslint clean ✅.
- ATP: TC-F group + TC-F-005/006 note עודכנו; נוספו TC-DOCS-001..007 (001-006 ⬜ pending implementation, 007 ✅ doc-check).
- VERSION: v0.4.8
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: מסמכי מקור-האמת עקביים עם הכרעות 2026-07-09 (trial ללא כרטיס, Free tier, F13, reveal-gating). המימוש בפועל (start_trial, Free limits, מסכי onboarding) ⬜ pending — ROADMAP S3/X1.
- DECISIONS: לא לשכתב היסטוריית CHANGELOG/קוד קיים; "trial עם כרטיס" נשמר כהפניה מפורשת ל"מה שהוחלף"; ATP TC-F-005 הקיים נשמר ✅ (מתעד קוד לא-משונה) לצד TC-DOCS החדשים.

## [STAGING / Live deploy from dev + smoke test PASS] — 2026-07-01
- GOAL: Stand up a live staging environment (not production) and validate end-to-end.
- ENVIRONMENT: Frontend on Vercel (Root `frontend`, pnpm workspace, branch `dev`) = https://finaroda-saas.vercel.app ; Backend on Railway (nixpacks Python, volume `/app/data`, plain uvicorn, `ENVIRONMENT=staging`, Cardcom TEST) = https://finaroda-saas-production.up.railway.app. No Litestream/R2, no Resend (DEV_RETURN_MAGIC_LINK), no production domain.
- SMOKE TEST (all PASS): health 200 (env=staging); magic-link→verify→/me authenticated as rodanis@gmail.com (is_admin=true — bootstrap admin works live); authenticated `POST /api/scan/events` → 200 persisted scan_event_id=1 + score_log; unauthenticated `/api/scan/events` → 401 (auth-required by design, not CORS).
- CODE: none (validation + SESSION_HANDOFF only).
- BRANCH: dev. main untouched. Cardcom TEST — no real charges. Nothing deployed by Claude (Nadav ran the Railway/Vercel deploys).

## [CHORE / pnpm workspace — resolve shared engine without a toggle] — 2026-07-01
- GOAL: Vercel's "Include files outside the root directory" toggle is gone from the current UI, so `link:../shared` still couldn't resolve. Convert to a proper **pnpm workspace** so Vercel (and any tool) resolves `@finaroda/scoring-engine` → `shared/` natively.
- SOLUTION (config + package.json metadata only):
  - `pnpm-workspace.yaml` (new, repo root): packages `frontend`, `shared`. (Backend is Python-only, no manifest — not a member.)
  - `frontend/package.json`: dependency `@finaroda/scoring-engine` changed `link:../shared` → `workspace:*`.
  - `shared/package.json`: added an `exports` map (`.` → scoring-engine.js, `./scorer.js`, `./scoring-engine.js`, `./package.json`) so both the root import and the subpath resolve explicitly; kept `main`, `name`, `type: module`.
  - Lockfile regenerated as a **workspace** lockfile at the repo root (`pnpm-lock.yaml`); removed `frontend/pnpm-lock.yaml`.
  - No root `package.json` needed (pnpm 10 handled it) → the backend's Railway Python/nixpacks build sees no Node manifest and is unaffected.
- FILES: pnpm-workspace.yaml (new), pnpm-lock.yaml (new at root), frontend/pnpm-lock.yaml (removed), frontend/package.json (workspace:*), shared/package.json (exports). transpilePackages in next.config kept.
- APP/ENGINE/SCORER/BACKEND LOGIC: unchanged (only package.json metadata + workspace config).
- VALIDATION: node --test 12/12 ✅ | tsc clean ✅ | eslint clean ✅ | `cd frontend && pnpm build` 16 routes, both `@finaroda/scoring-engine` AND `.../scorer.js` resolve ✅ | pytest 25/25 (backend unaffected) ✅.
- VERSION: v0.4.7
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: The shared engine resolves as a workspace package — Vercel deploys the frontend with Root Directory `frontend` and no toggle needed.

## [CHORE / Frontend → Vercel (monorepo shared package)] — 2026-07-01
- GOAL: Fix `Module not found: @finaroda/scoring-engine` in the Railway frontend build. Root cause: Railway with Root Directory=`frontend` does NOT include the sibling `../shared` on disk, so the `link:../shared` symlink dangles and webpack can't resolve the engine. The only Railway root-context option (Docker, Root=`/`) inherits the backend's `/api/health` healthcheck + Python crons from the root railway.toml.
- DECISION: **Move the frontend to Vercel** (backend stays on Railway). Vercel clones the whole repo and has a documented "Include files outside the root directory" toggle for monorepos, so `link:../shared` resolves cleanly — no healthcheck/cron landmine. (Nadav already runs hamakpetza-frontend on Vercel.)
- SOLUTION (config only): Added `frontend/vercel.json` pinning `installCommand: pnpm install --no-frozen-lockfile` + `buildCommand: pnpm build`. No change to how the frontend imports the engine (kept `link:../shared` + transpilePackages). Railway frontend configs (nixpacks.toml, frontend.Dockerfile) retained but unused.
- FILES MODIFIED: frontend/vercel.json (new).
- APP/ENGINE/SCORER/BACKEND: unchanged.
- VALIDATION: verified the `@finaroda/scoring-engine` symlink resolves + clean `next build` (16 routes) locally — this mirrors Vercel with files-outside-root included. tsc/eslint clean.
- VERSION: v0.4.6
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: Frontend deploys on Vercel with the shared engine resolving; backend remains on Railway. Cross-URL/CORS finalized once the Vercel URL exists.

## [CHORE / Frontend Railway build — nix-provided pnpm] — 2026-07-01
- GOAL: Fix `pnpm: command not found` (exit 127) — `npm i -g pnpm` in one nixpacks phase didn't leave pnpm on PATH for the next phase (nix Node's global-npm bin isn't on PATH).
- SOLUTION (config only): Provide pnpm via **nix** — `nixPkgs = ['nodejs_22', 'pnpm']` in `frontend/nixpacks.toml`. A nix package is on PATH for install, build, AND runtime, so it fixes the PATH error, needs no corepack (no keyid error), and no npm-global hack. Removed the `npm install -g pnpm` step. Kept Root Directory=`frontend` (Node-only; avoids the root railway.toml healthcheck/crons).
- The `$NIXPACKS_PATH` undefined-var line is a benign nixpacks Docker-lint warning, not the failure cause; no action needed.
- FILES MODIFIED: frontend/nixpacks.toml. (frontend.Dockerfile fallback from v0.4.4 retained.)
- APP/ENGINE/SCORER/BACKEND: unchanged.
- VALIDATION: tsc clean ✅ | eslint clean ✅ | next build 16 routes ✅. (nixpacks build itself is Railway-only — can't run nixpacks/Docker here.)
- VERSION: v0.4.5
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: pnpm is on PATH across all build phases + runtime via nix; the command-not-found error is resolved without corepack or PATH hacks.

## [CHORE / Frontend Railway build — fix corepack keyid] — 2026-07-01
- GOAL: Fix the frontend Railway build failing at `corepack enable` with "Cannot find matching keyid" (corepack signature verification, Node 22).
- SOLUTION (config only): Install pnpm **directly via npm** (`npm install -g pnpm@10.33.1`) instead of `corepack enable`, in `frontend/nixpacks.toml`; removed the `packageManager` field from `frontend/package.json` so nixpacks doesn't auto-invoke corepack. Kept the Node-only nixpacks path with **Root Directory = `frontend`** — which also avoids the repo-root railway.toml's `/api/health` healthcheck and Python crons (a landmine a root-context Docker build would hit).
- Also added `frontend.Dockerfile` (repo-root context; pnpm via npm; COPY shared/+frontend/) as a documented **fallback** if a Docker build is preferred (requires Root Directory `/` + `RAILWAY_DOCKERFILE_PATH` + clearing the inherited healthcheck).
- FILES MODIFIED: frontend/nixpacks.toml (corepack→npm), frontend/package.json (removed packageManager), frontend.Dockerfile (new fallback).
- APP/ENGINE/SCORER/BACKEND: unchanged.
- VALIDATION: tsc clean ✅ | eslint clean ✅ | next build 16 routes ✅.
- VERSION: v0.4.4
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: Frontend nixpacks build no longer calls corepack, so the keyid error is gone. Recommended path stays Root Directory `frontend` (Node-only, no root config inherited).

## [CHORE / Frontend Railway build — force Node-only] — 2026-07-01
- GOAL: Fix the Railway frontend build failing with `externally-managed-environment` / `get-pip.py` — nixpacks was building the monorepo's Python backend for the Next.js frontend service.
- ROOT CAUSE: With the frontend service Root Directory at repo root, Railway read the repo-root `nixpacks.toml` (Python provider) and tried to `pip install` for a Node app.
- SOLUTION (config only): Added `frontend/nixpacks.toml` with `providers = ['node']` (Node-only, pins nodejs_22, pnpm via corepack, `pnpm install`+`pnpm build`, start `next start -p $PORT`), and a `packageManager: pnpm@10.33.1` field in `frontend/package.json` so nixpacks uses pnpm not npm. The frontend service must set **Root Directory = `frontend`** so Railway reads THIS config, not the root Python one. `link:../shared` still resolves (Railway includes the whole repo in the build).
- FILES MODIFIED: frontend/nixpacks.toml (new), frontend/package.json (packageManager field).
- APP/ENGINE/SCORER: unchanged.
- VALIDATION: tsc clean ✅ | eslint clean ✅ | next build 16 routes ✅.
- VERSION: v0.4.3
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: Frontend Railway service builds as a pure Node/Next app; no Python provider triggered. Backend service (Root Directory `/`) still uses the root nixpacks.toml unchanged.

## [CHORE / Next.js security bump for Railway staging] — 2026-07-01
- GOAL: Unblock the Railway staging build, which rejected next@15.5.4 (CVE-2025-66478, CRITICAL).
- SOLUTION: Dependency bump only — no app logic, engine, or scorer changes.
- FILES MODIFIED: frontend/package.json, frontend/pnpm-lock.yaml.
- DEPS: next 15.5.4 → 15.5.19 (^15.5.9, includes the CVE fix); eslint-config-next 15.5.4 → 15.5.19 (kept in lockstep with next). Stayed within 15.5.x — non-breaking, no React/Next major bump.
- AUDIT: `pnpm audit --audit-level high` → 0 high/critical after the bump. 1 remaining **moderate** (transitive `postcss <8.5.10` via next) — not critical/high, does not block Railway; left as-is per the critical/high-only scope.
- VALIDATION: tsc clean ✅ | eslint clean ✅ | next build 16 routes ✅ | pytest 25/25 ✅ (backend unaffected) | shared node 12/12 (unchanged).
- VERSION: v0.4.2
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: Railway frontend build no longer blocked by the critical Next.js advisory. No functional change.

## [P2 / Scorer wired — real 85/82 gate live] — 2026-07-01
- GOAL: Wire the real scorer (`shared/scorer.js`, verbatim v25.80) into the scan core: momentum profile displayed, real 85 PASS / 82-84 WATCH gate on, pullback/continuation profiles logged (measure-first), score pending removed. Engine files not modified.
- SOLUTION: Import `scoreDirection` + `MOMENTUM_CAL` + `DEFAULT_CALIBRATION` + `DEFAULT_RISK` from `@finaroda/scoring-engine/scorer.js`. Score both directions per coin with the momentum profile; also score pullback/continuation for logging. Levels still via `computeSlTp` with Risk Style (RED LINE).
- FILES CREATED: backend/migrations/021_score_log_profile.py, backend/tests/test_p2_scorer.py.
- FILES MODIFIED: frontend/src/lib/scan/{engine,bybit,persist,lens,types}.ts, frontend/src/app/(scan)/scan/page.tsx, frontend/src/components/scan/{TradingBlueprint,Results}.tsx, frontend/src/types/scoring-engine.d.ts, backend/models/scan.py, backend/api/scan.py.
- DB CHANGES: migration 021 — `score_log.profile` column (momentum/pullback/continuation) + index. score is now populated (real), no longer null.
- ENGINE: **imported, not modified.** `shared/scorer.js` + `shared/scoring-engine.js` untouched (verified: no diff). scoreDirection is now CALLED with the momentum default profile.
- VALIDATION: node --test 12/12 (8 engine + 4 scorer) ✅ | pytest 25/25 ✅ | tsc clean ✅ | eslint clean ✅ | next build 16 routes (/scan 12.3 kB, scorer bundled) ✅ | boot smoke (health 200, scan/events 401, migrations 020+021 apply) ✅
- ATP: TC-SCORER-001..004 added.
- VERSION: v0.4.1
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: The scan now shows a REAL score with the live 85/82 PASS/WATCH gate. Three profiles are recorded per coin for base-rate research; only momentum is displayed. "Score pending" placeholder removed.
- DECISIONS (non-trivial):
  1. **`SCORE_GATE_ENABLED=true`.** Visibility gate is now the numeric score: PASS ≥85, WATCH 82-84, else hidden; a `blocked` (macro hard-gate) result is always hidden. The Analysis Lens no longer gates visibility (it's now purely a display panel — strengthens the RED LINE).
  2. **Direction selection:** score both long+short with the momentum profile; prefer the non-blocked result, then the higher score. That decides the displayed direction (replaces the interim EMA7-sign rule).
  3. **Profiles via the tool's own `entryMode` switch (no invented numbers):** momentum = `MOMENTUM_CAL`; pullback = `DEFAULT_CALIBRATION` (entryMode 'pullback'); continuation = `{...DEFAULT_CALIBRATION, entryMode:'continuation'}`. There are no separate PULLBACK/CONTINUATION exports in scorer.js — these are the documented calibration variants.
  4. **RED LINE kept:** the score uses FIXED inputs (`DEFAULT_RISK` + `MOMENTUM_CAL`); Risk Style feeds ONLY `computeSlTp` opt (displayed levels). Changing Risk Style on the card recomputes levels, never the score.
  5. **marketData extended (client-side):** added `weekly` (derived from daily every 7th candle, matching the scorer's test), open interest + `oiChangePct` (best-effort from Bybit open-interest; neutral default), and `change24h`; `marketContext` (coinChanges/mean/std) built once per scan from all coins' 24h change.
  6. **Persistence:** 3 rows per coin (profiles); only the momentum row is returned for snapshot linking; momentum row carries the displayed levels, the other two log score only.

## [P2 / Scan core — client-side fetch + Trading Blueprint] — 2026-07-01
- GOAL: Build the full scan flow and Trading Blueprint on the LEVELS engine (imported from `shared/scoring-engine.js`), to the binding reframing in PRD §3.5. The numeric SCORE is not available (scoreDirection throws, pass 2) — surfaced as pending, never invented.
- SOLUTION: Client-side Bybit fetch (user IP, no shared cache) → shared levels engine → results (ring/list) → Trading Blueprint. Persistence to scan_events/score_log/decision_snapshots. Backend adds scan endpoints + a thin CORS-fallback proxy.
- FILES CREATED:
  - Backend: backend/api/{scan.py, market_proxy.py}, backend/models/scan.py, backend/migrations/020_score_log_nullable.py, backend/tests/test_p2_scan.py.
  - Frontend: src/lib/scan/{types,bybit,engine,lens,store,persist}.ts, src/components/scan/{Controls,ScanningLog,Results,TradingBlueprint}.tsx, src/types/scoring-engine.d.ts. Rewrote src/app/(scan)/scan/page.tsx.
- FILES MODIFIED: backend/main.py (scan + market routers), frontend/package.json (link `@finaroda/scoring-engine`), frontend/next.config.ts (transpilePackages).
- DB CHANGES: migration 020 — `score_log.score` made NULLABLE (score pending until pass 2). No other schema change.
- CONFIG ADDED: none new (BYBIT_PUBLIC_BASE_URL already existed).
- ENGINE: **imported, never reimplemented.** Linked `shared/` as `@finaroda/scoring-engine` (workspace symlink) + ambient d.ts. Used calcEMA/RSI/ATR/ADX, ema7Slope, closedCandles, computeSlTp, computeReversalAnchor. **scoreDirection is never called.**
- VALIDATION: pytest 22/22 ✅ | tsc clean ✅ | eslint clean ✅ | next build 16 routes (/scan 5.89 kB, engine bundled) ✅ | shared node --test 8/8 ✅ | boot smoke (health 200, scan/events 401, proxy whitelist 400) ✅
- ATP: TC-B-001..006 (scan persistence, auth, snapshot ownership, proxy whitelist, score_log nullable) + TC-C-001..003 (Blueprint terminology / formula notes / score-pending — validated by build+tsc).
- VERSION: v0.4.0
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: A working scan core: press → streaming log → passers as circles → Trading Blueprint with real calculated levels, formula-transparency notes, Analysis Lens (display), Risk Style (geometry). Score cleanly marked pending; real 85/82 gate wired behind `SCORE_GATE_ENABLED` (off).
- DECISIONS (non-trivial):
  1. **Score-pending handling:** every scanned coin is recorded with `score=NULL`; the card shows "Score pending — engine pass 2 (levels below are real)". scoreDirection is never invoked. The real 85 PASS / 82 WATCH gate is wired but behind `SCORE_GATE_ENABLED=false` (engine.ts) — flip it on when pass 2 lands.
  2. **Interim visibility rule (documented):** while the score is pending, a coin is shown if its LEVELS are valid (ema7Slope non-null, ATR>0, ≥30 closed candles) AND the Analysis Lens condition holds (lens.ts). This is display-gating, not a score.
  3. **Interim direction rule:** direction derived from the sign of the VERIFIED EMA7 slope (long if >0, short if <0) purely to orient level geometry — not a recommendation, not a score.
  4. **Risk Style → `computeSlTp` opt only** (Conservative 1.0/1.0/2.0 · Balanced=defaults · Aggressive 2.0/2.0/4.0). Levels move; score untouched (RED LINE).
  5. **Engine link:** used `link:../shared` + `transpilePackages` + a frontend ambient d.ts (types only) rather than touching `shared/` — engine files untouched.
  6. **Persistence is best-effort:** scan endpoints require auth; a signed-out scan still works (persistence silently no-ops on 401).
- RED LINE: honored — client Lens changes display only; Risk Style changes geometry only; score/weights/edge/threshold are never client-touchable.

## [DOCS / Regulatory reframing — calculator framing] — 2026-07-01
- GOAL: Reframe the FRONT-END as a utility calculator (not advice) for regulatory protection. **The calculation engine, the verified EMA7-slope edge, filter weights, and the 85/82 threshold DO NOT change** — only terminology, what is displayed, and client-selected risk geometry.
- SOLUTION: Docs-only update to PRD/UX/LEGAL. Added an authoritative reframing section (PRD §3.5) that governs all surfaces, plus targeted term updates and a RED LINE.
- FILES MODIFIED: FINARODA_SAAS_PRD.md (v2.0→v2.1), FINARODA_SAAS_UX.md (v1.1→v1.2), FINARODA_SAAS_LEGAL_DRAFT.md (v2 reframing), CHANGELOG/VERSIONS/SESSION_HANDOFF.
- CODE CHANGES: NONE. scoring-engine.js and all scorer logic untouched (verified: no shared/ or backend/ diff).
- WHAT CHANGED (front-end only):
  1. **Terminology (calculator, not advice):** Entry → Mathematical Trigger Point · Stop Loss → Calculated Risk Level · Take Profit → Calculated Target Level · Trailing → Dynamic Risk Level · decision card → Trading Blueprint. "Analysis, not financial advice" labels kept.
  2. **Formula transparency:** each level shows a "how it was computed" note (e.g. "Calculated via ATR14 on your selected chart").
  3. **Analysis Lens (client choice — display only):** EMA200 / RSI / Volume / Full, chosen pre-scan, remembered, one scan press. Engine + score unchanged; lens only changes what is displayed.
  4. **Risk Style (client choice — output not score):** Conservative / Balanced / Aggressive → changes ONLY `computeSlTp` `opt` (slAtrMult / tp1Mult / tp2Mult). Levels move; score does NOT. Balanced == engine defaults.
  5. **RED LINE (PRD §3.5.5 + LEGAL §6):** client NEVER modifies score / filter weights / EMA7 edge / 85-82 threshold. Client choices live only in (a) what is displayed and (b) risk geometry — never in what counts as an opportunity. Protects measure-first + shared base-rate.
- VALIDATION: docs-only (no code) — pytest/tsc/eslint/node unaffected; last green state stands (P1: pytest 16/16, node 8/8, tsc/eslint clean).
- ATP: no new automated TC (docs). Reframing acceptance criteria captured in PRD §3.5 (AC per feature).
- VERSION: v0.3.1 (docs) · PRD v2.1 · UX v1.2 · LEGAL v2 reframing
- BRANCH: dev
- COMMIT: <hash>
- IMPACT: Stronger "utility calculator, not adviser" posture with real client-executed configuration, while the verified edge and base-rate stay intact.
- DECISIONS:
  1. **Per-user score threshold REMOVED** (old F5 "personal threshold" + UX §5): it would let the client change what counts as an opportunity → violates the RED LINE. `users.default_threshold` stays in the schema but is reserved for admin per-user overrides, never client-editable. (Flagged as the one real product-scope change forced by the RED LINE.)
  2. **Risk Style defaults** proposed (Conservative 1.0/1.0/2.0 · Balanced 1.5/1.5/3.0 = engine defaults · Aggressive 2.0/2.0/4.0) — admin-tunable, passed only as `computeSlTp` `opt`; engine code untouched.
  3. New reframing content written in **English** (per the permanent English-only directive + it is the canonical UI/terminology language). Existing Hebrew prose left as historical.

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
