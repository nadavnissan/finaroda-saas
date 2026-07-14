# FINARODA SaaS — Technical Specification (v1.0)

> מקור אמת למוצר. נכתב על בסיס `INFRA_AUDIT.md` של `hamakpetza` (Career OS) — תשתית אמיתית, נבדקת, פרוסה.
> עיקרון-על: **ניתוח, לא ייעוץ. אמון, לא התמכרות. ליבה דטרמיניסטית.**
> מודל ה-repo: `finaroda-saas` נפרד, יורש את שכבת התשתית בלבד מ-`hamakpetza`, זורק את כל שכבת הקריירה/Agent.

---

## 1. מהות המוצר ועקרונות שלא מתפשרים עליהם

FINARODA SaaS הוא PWA נייד מינימליסטי לתמיכת-החלטה במסחר סווינג בקריפטו. **לא** משכפל את הכלי האישי (730KB, מעבדת מחקר). בונה מחדש את הליבה בלבד: סריקה → ציון → לוח החלטה.

עקרונות-יסוד (נאכפים בקוד ובקופי):
1. **ניתוח לא ייעוץ.** אין "המלצת כניסה". יש ציון, רמות, והקשר. כל מסך מתויג. מסגור משפטי — עו"ד.
2. **ליבה דטרמיניסטית.** הסריקה והציון הם חישוב, לא LLM. אסור ל-LLM להזיז ציון או להחליט כניסה.
3. **trust-not-engagement.** מתגמלים דיוק ודילוג, לא תדירות. אין התראות "היכנס עכשיו", אין ספירת רצפים, אין gamification של תדירות.
4. **רק מדדים מאומתים נחשפים ללקוח.** שיפוע EMA7 (78.7% ניצח אקראי, 10/10) + volume. **לא** funding/OI (רעש למתחיל).
5. **מחסור, לא מזנון.** הסריקה מחזירה רק עוברי-סף-גבוה. רוב הימים: 0-2 מטבעות, או "כלום לא עובר".
6. **מנוע חישובי משותף.** הכלי האישי וה-SaaS חולקים קובץ JS אחד (`scoring-engine.js`) — לוגיקת חישוב טהורה. כל תיקון בכלי האישי משוכפל ל-SaaS דרך הקובץ הזה. ראו §6.

### זרימת המשתמש
כפתור עגול אחד → אנימציית סריקה במילים (מוריד טיקרים / מנתח נרות / מחשב volume) → טבעת עיגולים (רק עוברי-סף) → לחיצה על עיגול → **כרטיס החלטה** (Entry / SL / Trailing / TP + לוח תלת-דרגתי: מאומת/נאסף/מודיעין) → דיוק תזמון בבדיקות חוזרות.

---

## 2. ארכיטקטורה

### 2.1 הסטאק (יורש כמו שהוא)
| שכבה | טכנולוגיה |
|---|---|
| Backend | Python 3.13, FastAPI, aiosqlite, APScheduler, Pydantic, python-jose, passlib, slowapi |
| Frontend | Next.js 15.5, React 19, @tanstack/react-query, zustand, zod, recharts, shadcn/radix, Tailwind |
| Auth | JWT ב-httpOnly cookie (`access_token`), FastAPI dependency `get_current_user` |
| תשלומים | Stripe (Stripe Checkout + Stripe Billing); מסמכי מס ישראליים דרך שכבת invoice provider (`INVOICE_PROVIDER`) |
| אחסון | Cloudflare R2 (aioboto3) + signed URLs |
| מייל | Resend (טרנזקציוני). שיווקי/ברודקאסט — דרך admin broadcast |
| Deploy | Railway + nixpacks + Litestream (SQLite→R2). CI: pytest + tsc |
| DB | SQLite עד ~500 משתמשים → PostgreSQL אחרי |

### 2.2 מודל ה-repo
`finaroda-saas` (Private) נוצר כ-template מ-`hamakpetza` (לא מ-`hamakpetza-agent` הישן). העבודה דרך Claude Code מחובר ל-repo. הכלי האישי נשאר מעבדה לוקלית נפרדת; פיצ'ר מאומת שם מיושם מחדש (לא מועתק) בליבת ה-SaaS, בקצב מבוקר.

### 2.3 חלוקת frontend (route groups, יורש מבנה)
- `(scan)` — מסך הסריקה (כפתור→עיגולים→כרטיס). **חדש, ליבת FINARODA.**
- `(dashboard)` — דאשבורד לקוח "מה היה קורה". **חדש.**
- `(admin)` — פאנל מנהל (יורש + מתאים).
- `(academy)` — ספריית וידאו למידה (יורש).
- `(auth)`, `checkout`, `paywall`, `legal`, `coming-soon` (יורש).

---

## 3. ירושה: keep / adapt / discard

### 3.1 KEEP — יורש as-is (עם תיקון מוקשים)
| רכיב | קבצים | מקור |
|---|---|---|
| Auth + magic-link + Google + beta gate/waitlist | `core/auth.py`, `core/google_oauth.py`, `api/auth.py`, `api/waitlist.py` | audit §4 |
| Stripe billing (Checkout/webhook/Billing recurring/trial) | `api/billing.py`, `core/stripe_service.py`, `core/invoice_provider.py` | §5 |
| Trial 14 יום בלי כרטיס + crons | `start_trial`, `expire_trials`, `trial_ending_soon_task` | §5 |
| Coupons | migration 020, `api/admin/coupons.py` | §3,§8 |
| Broadcast (in-app + email) | `api/broadcasts.py`, `api/admin/broadcasts.py` | §7 |
| Notifications + Consent (append-only) | `notifications`, `consent_log` (001) | §10 |
| Onboarding survey עריך | migration 019, `api/admin/onboarding.py` | §3,§8 |
| Academy — Academy 2.0 (v0.13.0) DB-backed lessons מחליף את ה-shell; טבלאות VOD ‏mig 009 רדומות | `academy_lessons` mig 033, `api/academy.py`, `api/admin_academy.py` | §5.12 |
| R2 storage + signed URL | `core/storage.py` | §11 |
| Cost tracking | `ai_logs`, `api_usage`, `track_api_call` | §11 |
| Feature flags + system_settings | migrations 011/017 | §3 |
| Admin: users/analytics/beta/settings | `api/admin/*` | §8 |
| Deploy: Railway/nixpacks/Litestream/CI | `railway.toml`, `litestream.yml` | §11 |

### 3.2 ADAPT — יורש עם שינוי דומיין
| רכיב | מה משתנה |
|---|---|
| `users` table | זורקים עמודות קריירה (saved_pitch, cv pointers, journey). מוסיפים: `default_threshold`, `last_scan_at`. |
| Referral | היום משלם ב"טוקנים" ולוגיקה תלויה ב-Telegram (stub). **לבנות מחדש כ-REST** + תגמול כספי/הנחה (לא טוקנים). |
| Admin MRR/churn | היום הערכה גסה. **לתקן:** MRR שמכבד קופונים/trial; churn כשיעור עם חלון. |
| Tier vocabulary | לאחד אוצר מילים אחד (לא premium/b2b מול pro/unlimited). פלאנים של FINARODA. |
| Tickets | היה רק ב-legacy `support_tickets` (bot). **להעביר ל-migration מודרני** + UI לקוח/אדמין. |

### 3.3 DISCARD — לא נכנס בכלל
כל שכבת הקריירה/Agent (audit §12): `agent.py`, `agent_tools.py`, `rag.py` (chromadb/voyage), `cv_*`, `scraper.py`, `matcher.py`, `interview_sim.py`, `linkedin_*`, `panel_*`, `confidence/imposter/brand`, `ask_nadav`, `simulation_*`, `self_presentation`. + הטבלאות שלהן (002-008, 015-016, 021-023, 029-034). + `core/db.py` הישן כולו (סכמת bot). + תלויות: chromadb, voyageai, openai, rank_bm25, pdfplumber, python-docx, reportlab.

---

## 4. מוקשים לתיקון בירושה (לא לדלג)

1. **סכמה נקייה.** להתחיל מ-`migrations/` בלבד, לזרוק `core/db.py`. למפות מחדש את הטבלאות הנדרשות (users, billing, coupons, referral, notifications, consent, tickets) לסכמה אחת עקבית על `internal_id`. אין `CREATE TABLE IF NOT EXISTS` כפולים.
2. **מייל — Resend כבר עובד אצל נדב** (האודיט ראה env ריק בעותק בלבד). יורש as-is, לא חוסם. ✓
3. **תשלום אחד (Stripe).** ה-PSP הוא **Stripe** (Stripe Checkout + Stripe Billing). היסטוריה: תחילה Morning, אז Cardcom v11 (Stage 3), וב-Stage 3R (2026-07-14, v0.16.0) מעבר ל-Stripe. חיבור live דורש credentials + webhook signature verification + בדיקה. אין הזרמת legacy נוספת.
4. **חיזוק auth:** revocation (session store / jti blacklist) במקום JWT 30 יום ללא ביטול; hash ל-magic-link token (לא plaintext); להסיר dev-secret fallback בפרודקשן; אכיפת `aud`+`iss` ב-Google גם כש-CLIENT_ID ריק; admin כתפקיד ב-DB ולא רשימת env.
5. **MRR/churn אמיתיים** (ראו §3.2).

---

## 5. מודל הדאטה של FINARODA (חדש)

הליבה החדשה. כל הטבלאות על `internal_id`, מצטרפות ל-migrations הנקיות.

### 5.1 `scan_events` — כל סריקה (לא רק עוברי-סף)
```sql
CREATE TABLE scan_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    scanned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    coins_scanned INTEGER,        -- כמה מטבעות נסרקו
    coins_passed INTEGER,         -- כמה עברו סף
    threshold REAL,               -- הסף שהיה פעיל
    client_ip_region TEXT,        -- לא ה-IP המלא; אזור בלבד (פרטיות)
    FOREIGN KEY (user_id) REFERENCES users(internal_id)
);
CREATE INDEX idx_scan_user ON scan_events(user_id, scanned_at DESC);
```

### 5.2 `score_log` — לוג ציר-זמן ללמידה (הלב של המחקר)
**עיקרון:** רושמים את **כל** המטבעות שנסרקו (גם שלא עברו), כדי לחשב base-rate אמיתי. רושמים את הרמות בזמן הסריקה — סקריפט backtest מריץ מחיר קדימה ובודק הצלחה/כשל. **בלי** רישום Bybit של הלקוח.
```sql
CREATE TABLE score_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    logged_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    coin TEXT NOT NULL,
    direction TEXT NOT NULL,        -- long | short
    score REAL NOT NULL,
    passed_threshold INTEGER NOT NULL,  -- 0/1
    -- מדדים מאומתים בלבד (ציר-זמן):
    ema7_slope_pct REAL,            -- signed
    volume_ratio REAL,
    price REAL,
    -- רמות בזמן הסריקה (ל-backtest):
    entry REAL, sl REAL, tp REAL, trailing_pct REAL,
    -- מולא בדיעבד ע"י סקריפט ה-backtest:
    outcome TEXT,                   -- NULL | win | loss | open
    r_multiple REAL,
    resolved_at DATETIME,
    FOREIGN KEY (scan_event_id) REFERENCES scan_events(id),
    FOREIGN KEY (user_id) REFERENCES users(internal_id)
);
CREATE INDEX idx_scorelog_coin ON score_log(coin, logged_at DESC);
CREATE INDEX idx_scorelog_unresolved ON score_log(outcome) WHERE outcome IS NULL;
```

> **תוספת עתידית מתוכננת (migration, לפני צבירת דאטה משמעותית):** עמודת `regime_state TEXT` בכל שורת `score_log` — מצב המשטר (`bear` / `bull` / `transition`, מוגדר לפי BTC, hysteresis N=5 — לפי מודל המשטר, PRD הכלי האישי §15.5). בלעדיה ה-base-rate סובל time-confound (ערבוב בין דגימות ממשטרים שונים). יש להוסיף **לפני** שנצברת דאטה משמעותית כדי שכל שורה תיוחס למשטר מלכתחילה.

### 5.3 `decision_snapshots` — מצב הכרטיס שהוצג ללקוח (אסמכתא)
מה שהלקוח ראה בפועל, מתויג "ניתוח לא ייעוץ". משמש לדאשבורד "מה היה קורה".
```sql
CREATE TABLE decision_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    score_log_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    shown_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    card_json TEXT NOT NULL,        -- הכרטיס המלא כפי שהוצג (Entry/SL/Trailing/TP + תלת-דרגתי + desc/breakdown)
    FOREIGN KEY (score_log_id) REFERENCES score_log(id),
    FOREIGN KEY (user_id) REFERENCES users(internal_id)
);
```

### 5.4 `support_tickets` — מודרני (מהעברה מ-legacy)
```sql
CREATE TABLE support_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT,                  -- bug | question | billing | other
    status TEXT DEFAULT 'open',     -- open | in_progress | resolved | closed
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(internal_id)
);
CREATE INDEX idx_ticket_status ON support_tickets(status, created_at DESC);
```
> **mig 030 (v0.10.0):** `support_tickets` קיבל עמודת `app_version` (גרסת האפליקציה בזמן פתיחת הטיקט). בנוסף, תצוגת הטיקט באדמין מחזירה את **20 האירועים האחרונים שנרשמו למדווח** (xp/scan/funnel) לצורך הקשר דיבאג.

### 5.5 `episodes` — ספריית אפיזודות לאונבורדינג (Episode Library)
משמש את סימולציית האונבורדינג (F13, ראו `FINARODA_ONBOARDING_SPEC.md`). כל אפיזודה = **טווח kline אמיתי ומתוארך** מקובץ הטריידים/בקטסטים + התוצאה בפועל. הגרפים **מרונדרים אצלנו** מ-kline — **לעולם לא צילומי מסך מ-TradingView/Bybit** (רישוי במוצר מסחרי + עקביות ויזואלית). **מומש (§5.8): in-app SVG candlestick, לא recharts** — כדי להימנע מ-peer-dep של React 19 (החלטה פתוחה, revert אם נדב מעדיף); recharts נשאר dependency רשום.
```sql
CREATE TABLE episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin TEXT NOT NULL,
    date_range TEXT NOT NULL,        -- טווח מתוארך (מקור אמת: trades CSV / AnchorLog)
    kline_data TEXT NOT NULL,        -- נרות גולמיים לרינדור מקומי (in-app SVG, §5.8)
    scenario_type TEXT NOT NULL,     -- trap | valid_setup | discipline_save | patience
    lesson_flag TEXT,                -- הדגל החינוכי שהאפיזודה מדגימה
    outcome TEXT NOT NULL,           -- תוצאת האמת של האפיזודה (למשל דעיכה ב-X%)
    real_stats_ref TEXT,             -- הפניה למספר האמת (אימות מול ה-CSV לפני שילוב)
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```
> אמת אמפירית בלבד: כל מספר שמוצג באונבורדינג מגיע מ-`real_stats_ref` מאומת. אין סטטיסטיקות מומצאות ואין הוכחה חברתית מפוברקת.

### 5.6 `xp_events` — לוג צבירת XP (מקור-אמת: `XP_ECONOMY.md` v1.0)
כל צבירת XP נרשמת כאירוע בדיד. **מקורות מותרים = רשימה סגורה** (`XP_ECONOMY.md` §1): `daily_first_scan` (+50, פעם ביום), `academy_lesson` (+100, פעם לשיעור), `journal_reveal_viewed` (+25, פעם לתרחיש), `onboarding` (חד-פעמי, תסריטאי). **אסור לצמיתות:** XP על רווח/תוצאת what-if, מספר סריקות, רצפים, הזמנת חברים (RED LINE תרבותית).
```sql
CREATE TABLE xp_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    source TEXT NOT NULL,             -- daily_first_scan | academy_lesson | journal_reveal_viewed | onboarding (רשימה סגורה)
    ref TEXT NOT NULL,                -- מפתח ה-idempotency: YYYY-MM-DD (סריקה יומית) | lesson_id | scenario_id
    amount INTEGER NOT NULL,          -- +50 / +100 / +25 / תסריט אונבורדינג
    ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(internal_id),
    UNIQUE (user_id, source, ref)     -- idempotent: אירוע כפול לא מזכה XP פעמיים
);
CREATE INDEX idx_xp_user ON xp_events(user_id, ts DESC);
```
> **חוקתי:** כתיבת XP **צד-שרת בלבד** — לעולם לא מהלקוח (client-side scan מחשב ציון, אך לא מזכה XP). ה-`UNIQUE (user_id, source, ref)` הוא הגנת ה-farming (סריקה שנייה באותו יום → 0, ללא cooldown). דרגות ה-XP נגזרות מ-`SUM(amount)` — אין עמודת "rank" נפרדת לסנכרן. סף הדרגות והמקורות המלאים: `XP_ECONOMY.md`.

### 5.7 `onboarding_funnel_events` — משפך האונבורדינג (Onboarding Spec §5)
מדדי משפך מיום 1: השלמת 60 השניות, השלמת ענף הכישלון (`branch_1a_to_s2`), הרשמה, בחירת פיצול trial/Free (`fork_choice`), חזרת D1. אירועים לפני הרשמה (S0–S4) נושאים `anon_id` בלבד; אחרי הרשמה — `user_id`. **Append-only analytics — לא gamification** (אין רצפים/תדירות; trust-not-engagement).
```sql
CREATE TABLE onboarding_funnel_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(internal_id),  -- NULL לפני הרשמה
    anon_id TEXT,                                    -- session id טרום-הרשמה
    stage   TEXT NOT NULL,   -- screen_view|branch_1a_to_s2|signup|completion|fork_choice|d1_return
    detail  TEXT,            -- JSON
    ts      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 5.8 מימוש F13 — Episode Library + withholding + onboarding API (migrations 023–025)
- **`episodes` (§5.5) הורחב למימוש** בעמודות: `ext_id` (מפתח seed טבעי, E1/E3/E4), `direction`, `entry_index` (נקודת פיצול ל-withholding), `entry_price`, ו-`outcome` (JSON). כל נר נושא `ema7`/`ema200` אמיתיים. **Seed:** `backend/data/onboarding_episodes.json`, נבנה מ-Bybit עם **assertions של אמת אמפירית** (הבנייה נכשלת אם הנרות האמיתיים לא תומכים בכניסה/תוצאה המתועדת). E1 נבחר-מחדש ל-BTCUSDT 25/06 (ראה `EPISODES_AND_VERIFIED_NUMBERS.md`).
- **Server-side outcome withholding (AC):** `GET /api/onboarding/episodes/{id}` מחזיר רק נרות ה-setup (`0..entry_index`) — **ללא** `outcome` וללא נרות ה-reveal. `POST …/{id}/reveal` מחזיר את הנרות שהוסתרו + ה-outcome (S1 trap, S10 time-machine). ה-outcome כולל (valid_setup): `risk_price` (Calculated Risk Level, ל-E3 = 0.1511) ו-`checks` (top passed checks: regime/weekly_bias/ema7_slope/volume — ל-"Why PASS").
- **XP (12/07):** מענק **חד-פעמי לכל החיים (300), מזוכה ב-`POST /api/onboarding/complete`**. אנטי-farming: אינדקס unique חלקי `ux_xp_onboarding_once` על `xp_events(user_id) WHERE source='onboarding'` (migration **026**) → הרצה חוזרת מזכה 0. המונה 50/100/50/100 = תצוגת-לקוח בלבד. **Funnel:** `POST /api/onboarding/funnel` (optional-auth). **Routing:** משתמש שהשלים אונבורדינג ננותב ל-`/scan` (once-per-lifetime; back לא חוזר).
- **Charts:** מרונדרים in-app (SVG candlestick, הרפרנס של מנוע ה-SVG v25.67) מנרות אמיתיים — **לעולם לא צילומים חיצוניים**. `navigator.vibrate` על SCAN עם fallback שקט (iOS).

### 5.9 מימוש Package B — journal (F3), entitlements, admin (migrations 027–028)

**`journal_scenarios` (mig 028) — לב ה-retention (B4/F3).** רשומת תרחיש דרגה-ראשונה מכל סריקה, מחליפה גזירה ישירה מ-`score_log`. מקור-אמת של הלוגיקה: `backend/core/journal.py`.
```sql
CREATE TABLE journal_scenarios (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(internal_id),
    scan_event_id  INTEGER REFERENCES scan_events(id),
    score_log_id   INTEGER REFERENCES score_log(id),
    scenario_type  TEXT NOT NULL CHECK (scenario_type IN ('pass','no_setups_day')),
    scan_date      TEXT NOT NULL,                 -- YYYY-MM-DD (UTC scan day)
    coin TEXT, direction TEXT CHECK (direction IS NULL OR direction IN ('long','short')),
    score REAL, entry REAL, sl REAL, tp REAL, trailing_pct REAL,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- server-side resolution (NEVER serialized to the client until revealed):
    status         TEXT NOT NULL DEFAULT 'open'
                   CHECK (status IN ('open','win','loss','save','expired','skip')),
    r_result       REAL,                          -- hypothetical R, never money (F3 AC4)
    resolved_at    DATETIME,
    -- reveal-gating: outcome withheld until the user's NEXT scan reveals it:
    revealed_at    DATETIME,
    viewed_at      DATETIME                        -- set on open of revealed row (+25 XP)
);
-- one PASS scenario per momentum score_log row; one no_setups_day per user/day:
CREATE UNIQUE INDEX ux_journal_pass  ON journal_scenarios(score_log_id) WHERE scenario_type='pass';
CREATE UNIQUE INDEX ux_journal_noset ON journal_scenarios(user_id, scan_date) WHERE scenario_type='no_setups_day';
```
- **יצירה (בסריקה):** כל PASS (‏`momentum` + `passed_threshold=1`) → תרחיש `pass`; יום ללא PASS → `no_setups_day` (‏`status='skip'`, נחשף מיד). **WATCH לעולם לא תרחיש** (PRD F3 AC2). idempotent דרך שני ה-partial unique indexes (backfill = no-op).
- **Resolution (cron צד-שרת, `app/tasks/journal_tasks.py` דרך `scripts/run_resolve_scenarios.py`):** מריץ תרחישי `pass` פתוחים מול נרות Bybit יומיים (trigger→target/risk/7-day). `evaluate_outcome` = פונקציה טהורה. **`status`:** `win` (target ראשון, r=+reward/risk) · `loss` (risk ראשון, r=−1) · **`save`** (CAPITAL SAVES — trigger לא נורה בחלון, r=0, הון נשמר) · `expired` (נורה ללא target/risk, r=signed-at-close) · `open` (טרם ניתן להכריע).
- **Reveal-gating (PRD F3 AC5):** התוצאה מחושבת בשרת אך **מוחזקת מכל payload עד הסריקה הבאה** — `core/journal.on_scan` חושף קודם resolutions קודמות ואז יוצר תרחישים חדשים; שורות לא-חשופות נטולות דאטת תוצאה ב-payload וב-DOM (regression). Nav badge = ספירת לא-חשופים (‏`GET /api/journal/badge`). +25 XP צפייה (‏`journal_reveal_viewed`, §5.6, idempotent per scenario).

**`ticket_replies` (mig 028) — thread אדמין↔משתמש (B7c/F10):** `ticket_id`→`support_tickets` (ON DELETE CASCADE), `author_id`, `is_admin`, `body`, `email_sent` (fan-out מייל = stub לוגי).

**`notifications_log` (mig 028) — שני ה-system sends המוחלטים בלבד (B7f/F11):** `notif_type IN ('trial_reminder_day11','journal_reveal_teaser','broadcast')`, `channel IN ('in_app','email','email_in_app')`, `UNIQUE (notif_type, ref)` (idempotency). ברודקאסטים נשמרים ב-`admin_broadcasts` (הורחב ב-mig 028: `audience IN ('all','plan','trial_ending')` + `channel_in_app`/`channel_email`). **הערה:** `notifications_log` הוא **ledger** של idempotency + audit-אדמין בלבד — **נפרד** מפיד הפעמון של המשתמש (‏`notifications`, mig 031 למטה).

**§5.10 — Stage 5: notification feed + prefs + emails (mig 031, v0.11.0):**
- **`notifications` (mig 031) — פיד הפעמון (F11):** `id`, `user_id`, `type` (`trial_reminder`/`reveal_teaser`/`broadcast`), `title`, `body`, `link_path` (deep-link in-app), `created_at`, `read_at` (nullable). Index `(user_id, read_at)`. server-authoritative: הספירה וה-read-state מה-DB (שורדים refresh). פתיחת הפאנל מסמנת את הפריטים הגלויים כנקראים. **יצירת שורה חסומה ע"י `inapp_enabled=0`** (AC3). _(mig 031 גם משנה טבלת `notifications` מתה מ-mig 005 → `notifications_legacy_outbox`, לא-הרסני.)_
- **`notification_prefs` (mig 031) — העדפות per-user חוצות-מכשירים (DB, לא localStorage):** `user_id` PK, `inapp_enabled`, `sound_enabled`, `vibration_enabled`, `email_product` (day-11 + reveal-teaser), `email_broadcast` (one-click unsubscribe חובה) — כולם default `1`.
- **`journal_scenarios.teaser_sent_at` (mig 031) — sent-flag ל-dedup של reveal-teaser** (D-N5): sweep שולח teaser רק על שורות `resolved`/`revealed_at IS NULL`/`teaser_sent_at IS NULL`, ומסמן — ריצה שנייה שולחת אפס.
- **אימייל (`core/email.py`):** Resend אמיתי עם **DEV console-fallback** כשאין `RESEND_API_KEY` (כמו `DEV_RETURN_MAGIC_LINK`, אפס קריאות רשת בבדיקות). renderers טהורים (`render_trial_reminder`/`render_reveal_teaser`/`render_broadcast`) — ה-reveal-teaser **ללא שום ערך תוצאה** (pull-only red line: ערכים לא עוזבים את השרת לפני reveal, כולל למייל). כל broadcast נושא לינק unsubscribe חתום.
- **טוקן unsubscribe (D-N7):** HMAC על `JWT_SECRET` (‏`jose`), per-category, `purpose=email_unsubscribe`, TTL שנה. אימות → `(user_id, category)`; טוקן מזויף/פג → נדחה.
- **Endpoints:** `GET /api/notifications` (feed + `unread_count`), `POST /api/notifications/read` (`ids` או הכל), `GET/PUT /api/notifications/prefs`; `GET /api/email/unsubscribe?token=` (ללא login, idempotent, דף HTML); `POST /api/cron/notifications` (header `X-Cron-Secret`=`CRON_SECRET`, מריץ day-11 + reveal-teaser, idempotent; ריק=503 fail-closed); admin `GET /api/admin/broadcasts/preview?audience=&target_tier=` (`recipients` + `email_optin`) ו-`POST /api/admin/broadcasts` (שולח מיילים לאופט-אין בלבד + unsubscribe + שורות פעמון, מחזיר `delivered_inapp`/`delivered_email`).
- **cron wiring:** `run_resolve_scenarios` מריץ רק resolution שוק; ה-sends עברו ל-`POST /api/cron/notifications` (חיווט Railway ידני — SESSION_HANDOFF). env חדש: `CRON_SECRET`.

**§5.11 — Stage 7: Admin v1.1 + Sentry + ticket breadcrumbs (mig 032, v0.12.0):**
- **Admin users v1.1 (`GET /api/admin/users`):** עמודות — email, call_sign, tier, subscription_status, signup(created_at), last_active(`COALESCE(last_scan_at,last_login_at)`), xp, rank(`core/ranks.py`, level/name מ-XP), scans_total, scans_week, **active_days_7d/30d**, referrals(ספירה אמיתית, Stage 4 v0.17.0), churn_survey(EXISTS churn_reasons). פילטרים צד-שרת **AND** (`_user_filters`, URL-encoded): `search`, `plan`, `status`(trial|active|expired|churned), `signup_from/to`, `active_from/to`, `min_scans`. `status=churned` = יש שורת churn_reasons (שונה מ-expired שקט).
- **active-days = ADMIN ANALYTICS בלבד (D-A1, RED LINE):** distinct calendar days עם scan בחלון מתגלגל (7d=`date('now','-6 days')`, 30d=`-29 days`) — read-only מ-scan_events, **לא user-facing, לא מעניק XP, לא gate**. שם העמודה "Active days", לא "streak".
- **CSV (`GET /api/admin/users/export.csv`):** StreamingResponse text/csv, **אותם** query-params של list (view מסונן זהה), row-cap 5000, admin-only(403). מוכרז לפני `/users/{user_id}` כדי לא להתנגש.
- **Churn survey (`churn_reasons` mig 006):** `POST /api/churn/survey` (auth, שאלה חובה + free-text אופציונלי, skippable; מחשב days_as_customer + subscription_plan; total_spent NULL עד Stage 3). Admin: `GET /api/admin/churn` (רשימה) + aggregate ב-`/overview` + flag בטבלה + סינון.
- **Sentry (D-A6):** backend `core/monitoring.py` — env-gated (`SENTRY_DSN_BACKEND` או `SENTRY_DSN`), `init_sentry()`, `before_send=scrub_event` (מסיר user.email/ip/username + cookies + Authorization/Cookie/X-Cron-Secret headers, שומר `user.id` בלבד), `set_request_user(id)` ב-`get_current_user`. frontend `lib/sentry.ts` — `shouldInitSentry(dsn,env)` טהור + dynamic import של `@sentry/nextjs` (env-gated), `src/instrumentation.ts`(server) + `src/instrumentation-client.ts`(client). ללא DSN — אפס init, אפס רשת (בדיקות). traces 0.1.
- **Breadcrumbs (D-A7):** `support_tickets.breadcrumbs` (mig 032, JSON). לקוח: `lib/breadcrumbs.ts` ring-buffer 20 (route_change/scan_submit/api_error/notif_open, hooks ב-layout/apiFetch/NotificationBell), מצורף ל-`POST /api/support/tickets`. שרת: `core/breadcrumbs.py sanitize_breadcrumbs` — **allowlist** (`type,event_type,path,route,label,ts,timestamp,code,status_code,method`) מסיר כל שדה אחר → **אף ערך תוצאה (status/r_result) לא נשמר** (reveal-gating red line). admin ticket_detail מחזיר breadcrumbs(client trail) + recent_events(server, last-20).

**§5.12 — Stage 6: Academy 2.0 (mig 033, v0.13.0):** מחליף את רשימת `_MODULES` הקשיחה של B6 בטבלת-DB. הטבלאות הישנות `academy_bundles`/`academy_episodes` (mig 009, VOD/bundle→episode, ירושת template) נותרו **רדומות** ולא-בשימוש — הן מבנה דו-שכבתי שלא שווק; Academy 2.0 שטוח (card grid) ומחליף אותן ברמת המוצר.
```sql
CREATE TABLE academy_lessons (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    slug             TEXT NOT NULL UNIQUE,          -- מפתח ההשלמה == xp_events.ref (== module_id הישן)
    title            TEXT NOT NULL,
    description      TEXT NOT NULL DEFAULT '',       -- טקסט כרטיס (metadata, לא תוכן שיעור)
    content_type     TEXT NOT NULL DEFAULT 'text' CHECK (content_type IN ('text','video')),
    body             TEXT NOT NULL DEFAULT '',       -- תוכן טקסט (נשלט-שרת, gated)
    video_url        TEXT,                            -- URL embed מנורמל (YouTube/Vimeo), gated
    duration_minutes INTEGER NOT NULL DEFAULT 0,
    tags             TEXT NOT NULL DEFAULT '[]',      -- JSON array (חיפוש)
    min_plan         TEXT NOT NULL DEFAULT 'free' CHECK (min_plan IN ('free','basic','pro')),
    min_rank         INTEGER NOT NULL DEFAULT 0,      -- 0 | 1000 | 3000 | 8000 (סף XP, STATUS)
    sort_index       INTEGER NOT NULL DEFAULT 0,      -- סדר נשלט-אדמין (up/down)
    awards_xp        INTEGER NOT NULL DEFAULT 1,      -- 0 ל-seed stubs (התנהגות B6 נשמרת)
    archived_at      DATETIME,                         -- NULL=פעיל; archive-not-delete (D-AC6)
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```
- **שער-כפול (D-AC1, `core/academy_gate.py`):** `is_unlocked = plan_ok(user,min_plan) AND rank_ok(xp_total,min_rank)`. plan: free<basic<pro (legacy `advanced`==basic, mig 029; `trial`=גישת Pro). rank: `xp_total >= min_rank` — **סטטוס, לא הוצאה** (XP_ECONOMY: אין XP-כמטבע). `lock_reason` בשפה פשוטה (שער-דרגה נקרא ראשון: "Unlocks at <rank>", אחרת "Available on <plan> plan").
- **תוכן נשלט-שרת (D-AC7):** רשימת `GET /api/academy` מחזירה מטא-דאטה + מצב-נעילה + `lock_reason` בלבד (ללא body/video). `GET /api/academy/{slug}` מחזיר תוכן מלא **רק אם פתוח**, אחרת **403** — שיעור נעול לא זולג body/video ל-payload (נבדק).
- **השלמה/XP ללא שינוי:** `POST /api/academy/{slug}/complete` — +100 חד-פעמי (`INSERT OR IGNORE INTO xp_events(source='academy_lesson', ref=slug)`, unique). `awards_xp=0` → 0/`completed=false` (parity ל-stub של B6). **המיגרציה purely additive — אפס נגיעה ב-`xp_events`**, כל השלמה קיימת נשמרת לפי אותו slug (S3).
- **וידאו (D-AC2):** URL בלבד (YouTube unlisted / Vimeo), ללא העלאות. `validate_video_url` מנרמל ל-embed URL בזמן-כתיבה; URL לא-תקין → 400 `INVALID_VIDEO_URL`. נגן lazy (iframe נטען רק בלחיצה).
- **seed (mig 033):** 12 השיעורים הקיימים עם `slug`==module_id הישן, `body` נזרע מ-`concept_tooltips_content.json` (אותו מקור שה-B6 רינדר בצד-לקוח, כעת נשלט-שרת). 3 stubs → `awards_xp=0`.
- **Endpoints אדמין (admin-only, audited ל-`admin_events`, `api/admin_academy.py`):** `GET/POST /api/admin/academy/lessons`, `PUT /api/admin/academy/lessons/{id}`, `POST .../{id}/archive|restore`, `POST .../reorder` (`ordered_ids`, up/down — D-AC5).

**`user_settings` (mig 028) — הגדרות סריקה נשמרות (B5/F5):** `user_id` PK, `call_sign` (זהות מ-onboarding S9), `analysis_lens IN ('ema200','rsi','volume','full')`, `risk_style IN ('conservative','balanced','aggressive')`, `coin_prefs` (JSON), `palette`. **display & geometry בלבד — לעולם לא מה שנחשב הזדמנות** (RED LINE §3.5.5).

**`admin_events` (mig 006, קיים מראש) — audit trail של B7:** כל mutation של האדמין (plan override / extend-trial / grant-XP / suspend) נכתבת ל-`admin_events(admin_id, event_type, target_user_id, details_json, created_at)`. XP source `admin_grant` audited דרך זה (‏`XP_ECONOMY.md` §1, לא user-earnable).

**Endpoints שנוספו (Package B):**
| endpoint | תיאור |
|---|---|
| `GET /api/scan/entitlements` | binding gating config לפי tier → `{tier, coins_per_scan, chart_layers, scans_per_day}` (‏`core/entitlements.py`). |
| `POST /api/scan/events` | דוחה סריקה מעל מכסת המטבעות (403 `PLAN_COIN_LIMIT`); **אוכף מגבלת סריקות/יום (BUG 3, v0.10.0): 429 `DAILY_SCAN_LIMIT`** (Free=1/יום, בתשלום=unlimited, admin-editable דרך `scans_per_day_*`); מזכה first-scan-of-day XP (+50, idempotent per day, `daily_first_scan`). |
| `GET /api/scan/history` · `GET /api/scan/history/{id}` | **read-only (Decision B, v0.10.0):** רשימת סריקות אחרונות (זמן/מטבעות/passes) + תצוגת תוצאה שמורה, נגזר מ-`score_log`/`scan_events`. **אין** דאטת reveal/outcome. |
| `GET /api/plans` | public: שלושת המסלולים (Free/Basic/Pro, אחרי Decision A) עם price/coins/scans/chart_layers מ-`system_settings`. |
| `GET /api/journal/badge` | ספירת תוצאות לא-חשופות בלבד (reveal badge). |
| `GET /api/profile` · `PUT /api/profile/settings` | פרופיל + call-sign + סולם דרגות; שמירת Lens/Risk Style. |
| `POST /api/support/tickets` | פתיחת טיקט (Report a problem). |
| `POST /api/billing/trial` | D1 no-card trial (our own trial, NOT a Stripe trial). |
| `GET /api/broadcasts/active` | banner in-app פעיל (לעולם לא מכסה SCAN/disclaimer). |

**מפתחות `system_settings` חדשים (migrations 027–028, admin-editable בלי קוד):**
- **coins/scan:** `scan_coins_free` (=2; basic/advanced/pro נזרעו ב-mig 008). **Decision A (mig 029, v0.10.0):** `scan_coins_basic=5` (Basic ירש את רוחב ה-Advanced); מפתחות `*_advanced` הוסרו.
- **prices (mig 029, אגורות):** `plan_price_basic=5900` (₪59), `plan_price_pro=14900` (₪149), **PENDING-ACCOUNTANT**. מפתחות `plan_price_advanced` הוסרו.
- **chart layers (E7/F15):** `chart_layers_{free,basic,pro}`: `'ema200_only'` (Free = chart+EMA200) / `'full'` (בתשלום = כל השכבות). `chart_layers_advanced` הוסר (mig 029).
- **scans/day (BUG 3, v0.10.0, נאכף בשרת):** `scans_per_day_{free,basic,pro}`: Free=1, בתשלום=0 (unlimited). **`POST /api/scan/events` דוחה מעל המכסה עם 429 `DAILY_SCAN_LIMIT`** (הלקוח מציג מצב מגבלה ידידותי). `scans_per_day_advanced` הוסר (mig 029).
- **admin (B7e):** `trial_reminder_day` (=11), `journal_history_days_free` (=7).

> **tier enum (Decision A, mig 029, v0.10.0):** הקטלוג הוא `free`/`basic`/`pro`. `'advanced'` הוא **ערך legacy retired-but-tolerated**: ה-CHECK constraint לא נבנה מחדש, ומשתמשי `advanced` קיימים מוגרו ל-`basic` ע"י mig 029. אין להנפיק `advanced` חדש.

> **RED LINE נשמר:** ה-entitlements קונים **רוחב** (מטבעות) ו-**עומק** (שכבות גרף) — לעולם לא verdict שונה. הציון והסף זהים בכל פלאן.

---

## 6. מנוע הסריקה (client-side) + המנוע המשותף

### 6.1 המנוע המשותף — `scoring-engine.js`
לוגיקת החישוב הטהורה (אפס UI): EMA7 slope signed, volume ratio, price-vs-EMA7, מרחק SL, ציון, גאומטריית SL/עוגן. **קובץ JS אחד** שהכלי האישי וה-SaaS מייבאים שניהם.

> **Swing S/R canon (v0.8.0):** `findRecentSwingLevels(highs, lows, lookback, scanRange)` → `{swingHigh, swingLow}` הועבר מהכלי האישי (`engine.mjs`) אל `@finaroda/scoring-engine` **byte-faithfully** — זהו **מקור ה-S/R היחיד** שהמנוע מודד מולו (liquidity-proximity check + כל הטריידים המתועדים), כך שהגרף מצייר בדיוק מה שהמנוע מנקד. הגרפים ניגשים אליו דרך adapter דק `frontend/src/lib/chart/swings.ts` (`swingLevels`). **`computeRangeLevels` (קירוב ה-pivot בן-השבוע של ה-SaaS) הוסר** יחד עם `lib/onboarding/levels.ts` (נמחק 2026-07-13). **Equivalence test** (`shared/scoring-engine.test.js`) מאמת swings זהים מול העתק verbatim של המימוש האישי על עשרות וקטורים דטרמיניסטיים.

```
              scoring-engine.js  (JS טהור, מנוע משותף)
             /                    \
   כלי אישי (לוקלי, HTML)      SaaS (ענן, Next.js client-side)
```

זרימת השכפול: תיקון בכלי האישי → נכנס ל-`scoring-engine.js` → מועתק ל-repo של ה-SaaS (בהמשך: npm package משותף) → ה-SaaS מקבל אותו מוח חישובי.

> **עבודה חד-פעמית (P0/P2):** היום הלוגיקה שזורה בתוך ה-React של הכלי האישי (730KB מקומפל). צריך **לחלץ** פעם אחת את פונקציות החישוב (`scoreDirection`, `computeReversalAnchor`, EMA7 slope וכו') לקובץ עצמאי, ואז שני הצדדים מייבאים. המלצה: לחלץ מוקדם. הכלי האישי = מעבדה לוקלית שממשיכה כרגיל; ה-SaaS בענן כמו ג'ובי.

### 6.2 הסריקה ב-SaaS
**עיקרון מאושר:** כל לחיצת לקוח = משיכה טרייה ועצמאית מ-Bybit (endpoint ציבורי, חינמי, ללא API key) + חישוב מחדש. **אין** קאש משותף. כל לקוח מ-IP שלו → rate-limit נפרד, אפס צוואר בקבוק.

- **ברירת מחדל:** fetch ישיר מהדפדפן מול `api.bybit.com/v5/market/*` (kline/tickers/OI) — רובם מחזירים CORS תקין. IP של הלקוח.
- **Fallback:** proxy דק ב-backend רק ל-endpoints בעייתיים — לא מאחד דאטה, רק מעקף CORS.
- **חישוב:** דרך `scoring-engine.js` המשותף. דטרמיניסטי.
- **מספר מטבעות בסריקה:** לפי פלאן (Free 2 / בסיס 5 / פרו 10, אחרי Decision A), נשלט מהאדמין דרך `system_settings` בלי קוד.
- **רטט בלחיצת SCAN (E6, נדב 2026-07-11):** לחיצת כפתור ה-SCAN מפעילה `navigator.vibrate(...)` עם **fallback שקט** — היכן שה-API לא נתמך (iOS Safari לא תומך ב-Vibration API) פשוט לא יורטט, בלי שגיאה ובלי חסימת הסריקה. haptic feedback עדין בלבד; אינו נוגע בלוגיקת הסריקה/הציון.
- **כתיבה:** כל סריקה → `scan_events` + שורת `score_log` לכל מטבע (גם שלא עבר). הכרטיס שמוצג → `decision_snapshots`.

---

## 7. לולאת הלמידה + backtest "מה היה קורה"

רכיב אחד, שני שימושים:
- **למידה (מנהל):** cron יומי מריץ מחיר קדימה על שורות `score_log` עם `outcome IS NULL`, ממלא win/loss/r_multiple. בונה base-rate: ציון-X → WR/avgR אמיתי. זה מאמת אם הסף עובד.
- **"מה היה קורה" (לקוח):** דאשבורד מציג, על כל הפוזיציות **המאושרות שקיבל**, תשואה מצטברת + WR + avgR — כאילו נכנס לכולן. מתויג **"תוצאה היפותטית, ניתוח לא ייעוץ"** בכל מסך.

> measure-first: זה מודד את איכות **המערכת** (ההמלצות), לא ביצוע הלקוח. אין לנו רישום Bybit, ולא צריך.

---

## 8. דאשבורדים

### 8.1 דאשבורד לקוח
- "מה היה קורה אם נכנסת לכל המאושרות" — תשואה/WR/avgR (היפותטי, מתויג).
- היסטוריית סריקות + כרטיסים שהוצגו.
- מדדי משמעת: היצמדות/דילוג (לא entries/day).

### 8.2 דאשבורד מנהל (יורש + מתאים)
- לקוחות: ת.כניסה, ת.נטישה, **סיבת עזיבה** (שאלון יציאה דרך webhook ביטול), סטטוס, MRR נוכחי.
- מערכת טיקטים (פתיחה/מענה).
- ברודקאסט (in-app + email).
- ניהול קופונים, beta allowlist/waitlist, פלאנים, סף-סריקה גלובלי.
- ניהול וידאו (academy).

---

## 9. תשלומים, מנוי, חבר-מביא-חבר

> **Stage 3R (2026-07-14, v0.16.0): PSP switched from Cardcom to Stripe (Stripe Checkout + Billing). The prior Cardcom design is superseded. Israeli tax documents are issued by a provider-agnostic invoice layer (`INVOICE_PROVIDER`), not by Stripe.** Stripe's own invoices are NOT Israeli tax documents. The operating entity is an Israeli LTD (in formation), VAT registered.

- **Stripe (Stripe Checkout + Stripe Billing):**
  - **Checkout:** a hosted **Stripe Checkout Session** per plan (the card never touches our servers) with success/cancel redirect paths (`STRIPE_SUCCESS_PATH`/`STRIPE_CANCEL_PATH`). **Activation happens ONLY via the signature-verified webhook**, never the browser redirect.
  - **Recurring + retries:** **Stripe Billing / Smart Retries** own recurring charges and failure retries. The old homegrown recurring-charge + +24h/+72h dunning scheduler was DELETED. Our own failure / recovery / cancel emails still fire (from the webhook), so the copy stays ours.
  - **Cancel:** Stripe `cancel_at_period_end`, keeping our end-of-period access semantics + the churn-survey hook.
  - **Webhook:** verifies the Stripe signature and is idempotent by event id (`processed_webhook_events`). Handled events: `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `customer.subscription.updated`, `customer.subscription.deleted`.
  - **Trial 14 יום ללא כרטיס (OURS):** card-free, **NOT a Stripe trial** (Stripe knows nothing about trialing users); trial expiry is a cron. תזכורת יום 11; בסוף התקופה בחירה אקטיבית: פלאן בתשלום או Free. לכידת הכרטיס עוברת לרגע ההמרה לתשלום בלבד (Checkout Session). _(change order מאושר, נדב 2026-07-09; מחליף את "trial עם כרטיס" שהיה נעול.)_
  - **Israeli tax-invoice layer:** `core/invoice_provider.py` abstraction issues one Israeli tax document per successful charge. Provider is config (`INVOICE_PROVIDER`): `mock` default (offline), with a documented interface ready for Green Invoice / iCount / EZcount (provider NOT chosen yet). Document type default is now `tax_invoice_receipt`. Stripe's own invoices must never be presented as Israeli tax documents.
  - **Endpoints:** `/api/billing/*` (checkout, trial, webhook, status, cancel).
  - **Env vars:** `FEATURE_STRIPE_LIVE`, `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `INVOICE_PROVIDER`, `STRIPE_SUCCESS_PATH`, `STRIPE_CANCEL_PATH`. (Removed: all `CARDCOM_*`, `FEATURE_CARDCOM_LIVE`, `DUNNING_RETRY_OFFSETS_HOURS`.)
  - **Prices:** remain config (agorot ints, ILS, VAT-inclusive display + footnote); Stripe Prices are seeded from config by an idempotent seed script (`backend/scripts/seed_stripe_prices.py`, test mode).
- **⤷ Historical record (Stage 3, v0.14.0), sandbox/mock only (superseded by Stage 3R above), Cardcom sandbox/mock (`FEATURE_CARDCOM_LIVE=false`, אין טרמינל אמיתי):**
  - **מכונת-מצבים אחת (`core/billing_state.py`, D-B4, server-authoritative):** `subscription_status` ∈ none/trial/active/past_due/cancelled/expired. מטריצת מעברים חוקיים (`assert_transition` זורק `IllegalTransition` על לא-חוקי); כל שינוי סטטוס עובר `apply_transition` (guard + audit ל-`subscription_events`). **ההרשאות נגזרות מה-state בלבד** (`effective_tier`): active/trial/past_due/cancelled שומרים את ה-tier בתשלום (past_due=grace בזמן dunning, cancelled=עד תום התקופה), expired/none→free. breadth (מטבעות/שכבות/סריקות-ליום) עדיין נגזר מ-`tier` דרך `system_settings` — ה-state קובע רק אם ה-tier בתשלום. אוצר-המילים = ה-CHECK הקיים (mig 001), מכסה את D-B4 אחד-לאחד (S2, "trialing"→trial, "canceled"→cancelled; בלי rename).
  - **מסמכי חיוב (`core/cardcom_invoice.py`, D-B3, mig 034 `billing_documents`):** מסמך receipt/invoice_receipt לכל חיוב מוצלח (ראשון+חוזר), idempotent per-transaction; **סוג-מסמך = CONFIG** (`system_settings.billing_document_type`, ברירת-מחדל receipt, נבחר ע"י רו"ח — S3); offline=MOCK אפס-רשת, live=`Documents/Create` מגודר. מייל receipt עם קישור למסמך (Stage-5 email, כיבוד `email_product`).
  - **webhook (D-B8):** אימות HMAC constant-time, הפעלה **צד-שרת בלבד** (redirect לבד לא מפעיל), idempotent by deal-id. **חיוב חוזר + dunning (D-B5):** כשל→past_due, retry ב-+24h ואז +72h (config `DUNNING_RETRY_OFFSETS_HOURS`), מייל+פעמון לכל כשל, מיצוי→expired→Free, recovery→active; idempotent (ריצה כפולה=0). **ביטול end-of-period (D-B6):** status→cancelled, גישה עד paid-through, cron מוריד ל-Free; churn survey מחווט; ביטול-כפול בטוח. **cron:** `POST /api/cron/billing` (X-Cron-Secret, D-B9). **כסף=agorot ints** end-to-end (D-B10).
  - **סכמה (mig 034, additive):** `billing_documents`; `payment_transactions += coupon_code/referral_source (D-B7 inert)/kind`; `users += dunning_next_retry_at`; `subscription_events` CHECK מורחב (+5 event-types).
- **Stage 3R, the surviving state machine (v0.16.0):** the internal billing state machine (`core/billing_state.py`, states none/trial/active/past_due/cancelled/expired) SURVIVES as the single source of truth for entitlements, now fed **exclusively by Stripe webhooks**. Entitlements logic is unchanged. One transition edge was added: **active→expired** (for an involuntary `customer.subscription.deleted`). DB migration **035** renames columns to Stripe: `users.cardcom_token → stripe_customer_id` (plus new `stripe_subscription_id`, `card_last4`, `card_expiry`); `payment_transactions.cardcom_tx_id → stripe_reference` and `cardcom_response_json → provider_response_json`; `billing_documents.cardcom_document_id → provider_document_id`; new table `processed_webhook_events`; `billing_document_type` default → `tax_invoice_receipt`. **go-live** (Stripe live keys + webhook secret + a chosen `INVOICE_PROVIDER` + `FEATURE_STRIPE_LIVE=true` + Railway cron for trial-expiry) = משימה ידנית של נדב, מפורטת ב-SESSION_HANDOFF.
- **Stage 4 (Coupons + Referral, Stripe-native, v0.17.0):** קופונים + referral נבנו על גבי Stripe.
  - **Coupons:** `core/coupon_service.py` יוצר **Stripe Coupon** (`percent_off` או `amount_off` באגורות + `currency=ils`, `duration=once`) + **Promotion Code**; DEV = ids מזויפים דטרמיניסטיים, אפס-רשת. שורת-מראה ב-`coupons`. Admin: `api/admin_promotions.py` (`/api/admin/coupons` create/list/deactivate, 403 + audited). **הגבלת פלאן (D-S1) — המנגנון שנבחר: אכיפה אצלנו** (`validate_coupon_for_plan`) לפני יצירת ה-Checkout Session (לא Stripe `applies_to`, כי אנו שומרים Price ids לכל פלאן ולא Product ids, ובונים session לכל פלאן בנפרד). קודים לא-מוגבלים משתמשים בשדה ה-Stripe המתארח (`allow_promotion_codes=true`). Redemptions מסונכרנים מ-`checkout.session.completed` (`coupon_redemptions`, idempotent per coupon,user + סנכרון `redeemed_count`).
  - **Referral:** `core/referral_service.py`. קוד קבוע 8-תווים ל-משתמש (‏`users.referral_code`), קישור `/r/<code>`; קשירה חד-פעמית ב-signup (‏`bind_referral`, immutable, הפניה-עצמית חסומה id+email). התגמול נדלק על החיוב-בתשלום הראשון של המגויס (‏`invoice.paid` amount>0, כל `billing_reason`; חודש 100%-קופון = amount 0 לא מדליק). idempotent דרך מעבר יחיד bound→rewarded. תגמול = זיכוי-יתרת-לקוח של חודש בפלאן הנוכחי של המגייס (‏`Customer.create_balance_transaction` שלילי), או **banked** (‏`referral_credits`) ל-trial/Free ומיושם בחיוב-בתשלום הראשון של המגייס (לפי הפלאן שירכוש; זיכויים נערמים). void מסיר banked או מפרסם תנועה מפצה (חיובית), מבוקר.
  - **D-S8 (מסמכי מס):** חשבונית בסך 0 (‏checkout amount_total=0 או recurring amount_paid=0) מפעילה/מחדשת אך **אינה** מנפיקה מסמך מס — שורת `zero_amount_invoice_no_document` ב-`subscription_events` במקום.
  - **C2 (אימות webhook):** `verify_and_parse` משתמש כעת ב-`stripe.Webhook.construct_event` (ה-SDK הרשמי; אותה סכמת `t=,v1=` HMAC + סובלנות 300s, קריפטו טהור אפס-רשת), ואז מנתח מחדש את הגוף ל-dict רגיל כדי לשמור על חוזה ה-handlers. ה-HMAC ה-hand-rolled הוסר.
  - **DB (mig 036, reshape לא-הרסני של המודל הרדום):** `coupons` נבנה מחדש לשורת-מראה של Stripe; `coupon_applications` → `coupon_redemptions`; `referrals` נבנה מחדש למודל קשירה+תגמול (UNIQUE referred_id); חדש `referral_credits`; CHECK של `subscription_events` הורחב ב-6 event-types (referral reward/credit/void, coupon_redeemed, zero_amount_invoice_no_document). STOP S3 נוקה (3 הטבלאות 0 שורות בדב). **אין env חדש.**
- **Free + 2 פלאנים בתשלום (Decision A, 2026-07-13, Advanced הוסר, Basic ירש את רוחבו):**

| פלאן | מחיר ₪/חודש | מטבעות בסריקה |
|---|---|---|
| Free | 0 | 2 (סריקה 1/יום) |
| בסיס | 59 (PENDING-ACCOUNTANT) | 5 |
| פרו | 149 (PENDING-ACCOUNTANT) | 10 |

> כל המגבלות (מטבעות, סף) נשלטות מהאדמין דרך `system_settings` בלי קוד. אוצר מילים אחד לפלאנים (לא premium/b2b מול pro/unlimited).
> **Free tier (D2, נדב 2026-07-09):** סריקה 1/יום · 2 מטבעות · **Trading Blueprint מלא** · דאשבורד F3 מוגבל ל-7 הימים האחרונים · ללא ייצוא · academy בסיסי. כל המגבלות נשלטות דרך `system_settings`. במסכי paywall/פיצול — אפשרות משנית "Continue on Free".

- **קופונים:** migration 020 + admin UI (to be redesigned Stripe-native, e.g. Stripe promotion codes, in the deferred Stage 4).
- **חבר מביא חבר:** המגייס מקבל **50% הנחה לחודש** — **רק אחרי שהחבר המגויס התמיד 3 חודשים** (סינון "מטיילים"). דורש: (א) מעקב referrer→referred + תאריך, (ב) בדיקת 3 חודשי מנוי פעיל רצוף, (ג) **מנגנון בקרה/אישור לאדמין** לפני מתן ההנחה. תגמול = הנחה, לא טוקנים.
- **שאלון onboarding עריך** (migration 019) — נשמר, ניתן לעריכה ע"י הלקוח והמנהל.

---

## 10. LLM — לא בליבה, פיצ'ר עתידי

ה-LLM **אסור** בליבה (דטרמיניסטית). פיצ'ר V2 מתועד: **כפתור "העתק לפרומפט"** — הכרטיס מייצר בלוק טקסט מובנה (ציון, כיוון, רמות, מדדים מאומתים, הקשר משטר, דיסקליימר) שהלקוח מעתיק ל-LLM חיצוני שלו לחיזוק שיקול דעת. אפס עלות/latency/תחזוקה עלינו; אחריות ההחלטה על הלקוח (חשוב משפטית). דאטה מספרית מובנית, לא תמונת גרף.

---

## 11. סדר בנייה (פאזות)

| פאזה | תוכן | תלות |
|---|---|---|
| **P0 — ניקוי** | מ-`finaroda-saas`: למחוק שכבת קריירה/Agent (§3.3), לזרוק `core/db.py`, להוריד תלויות. סכמה נקייה. | — |
| **P1 (תשתית חיה)** | חיבור Stripe (Checkout + Billing, keys+webhook signature), מחיקת Morning/legacy, auth מחוזק, deploy ב-Railway. (Resend כבר עובד.) | P0 |
| **P2 — ליבת סריקה** | client-side Bybit fetch + ציון + עיגולים + כרטיס החלטה. `scan_events`/`score_log`/`decision_snapshots`. | P1 |
| **P3 — לולאת למידה** | cron backtest "מה היה קורה" + דאשבורד לקוח. | P2 |
| **P4 — מסחרי** | פלאנים, trial, קופונים, referral חדש, paywall. | P1 |
| **P5 — מנהל+קהילה** | אדמין (MRR/churn מתוקן), טיקטים, ברודקאסט, academy, onboarding survey. | P4 |
| **V2** | כפתור "העתק לפרומפט LLM", PWA push. (Stripe global billing already shipped in Stage 3R, v0.16.0.) | — |

---

## 12. החלטות שנסגרו (v1.0)

| # | החלטה |
|---|---|
| 1 | **פלאנים (Decision A, 2026-07-13, Advanced הוסר): Free ₪0 / בסיס ₪59 / פרו ₪149 (PENDING-ACCOUNTANT). Basic ירש את רוחב ה-Advanced.** |
| 2 | מטבעות בסריקה: Free 2 / בסיס 5 / פרו 10 — **נשלט מהאדמין בלי קוד** |
| 3 | trial **ללא כרטיס** (change order, נדב 2026-07-09): 14 יום, ללא tokenization בהרשמה, ללא חיוב אוטומטי, תזכורת יום 11; בסוף התקופה בחירה אקטיבית — פלאן בתשלום או Free. לכידת הכרטיס עוברת לרגע ההמרה לתשלום. _(מחליף את "trial עם כרטיס" שהיה נעול ב-v1.0.)_ |
| 4 | **חבר מביא חבר:** 50% הנחה לחודש למגייס, רק אחרי 3 חודשי התמדה של המגויס + בקרת אדמין |
| 5 | קהל V1 ישראלי (PSP = **Stripe** מ-Stage 3R; ישות ישראלית בע"מ בהקמה, עוסק מורשה במע"מ; מסמכי מס דרך `INVOICE_PROVIDER`), **UI באנגלית מלאה** |
| 6 | וידאו: YouTube unlisted מספיק ל-V1 |
| 7 | מנוע משותף ב-**JS** (`scoring-engine.js`); כלי אישי לוקלי, SaaS בענן |
| 8 | **Free tier** (נדב 2026-07-09): סריקה 1/יום · 2 מטבעות · Blueprint מלא · F3 מוגבל 7 ימים · ללא ייצוא · academy בסיסי — נשלט `system_settings` |

### עדיין פתוח (לא חוסם מימוש)
- **מסגור משפטי** — Claude יכתוב טיוטת ToS/דיסקליימר "ניתוח לא ייעוץ" + הסכמת פרטיות; נדב מעביר לעו"ד לאישור.
- **מחירי trial/הנחות מדויקים** — נדב מאמת מול רו"ח.

---

_v1.0 — §12 נסגר, מנוע משותף ב-JS, PSP = Stripe (Stage 3R, v0.16.0), Resend עובד. הצעד הבא: Claude Design למסע לקוח/UX (ראו FINARODA_SAAS_UX.md) → מימוש לפי הפאזות._
