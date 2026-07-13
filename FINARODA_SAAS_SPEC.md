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
| תשלומים | Cardcom v11 REST (V1) → Stripe גלובלי (V2) |
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
| Cardcom v11 (checkout/webhook/recurring/trial) | `api/cardcom.py`, `core/cardcom_service.py` | §5 |
| Trial 14 יום בלי כרטיס + crons | `start_trial`, `expire_trials`, `trial_ending_soon_task` | §5 |
| Coupons | migration 020, `api/admin/coupons.py` | §3,§8 |
| Broadcast (in-app + email) | `api/broadcasts.py`, `api/admin/broadcasts.py` | §7 |
| Notifications + Consent (append-only) | `notifications`, `consent_log` (001) | §10 |
| Onboarding survey עריך | migration 019, `api/admin/onboarding.py` | §3,§8 |
| Academy/VOD (YouTube embed) | migration 013, `api/academy.py` | §9 |
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
3. **תשלום אחד.** Cardcom v11 **טרם חובר** (היה Morning, עברו ל-Cardcom, לא הושלם). ב-P1: להשלים חיבור (credentials + webhook + בדיקה), ולמחוק Morning + legacy aiohttp + Stripe stub.
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

**`notifications_log` (mig 028) — שני ה-system sends המוחלטים בלבד (B7f/F11):** `notif_type IN ('trial_reminder_day11','journal_reveal_teaser','broadcast')`, `channel IN ('in_app','email','email_in_app')`, `UNIQUE (notif_type, ref)` (idempotency). ברודקאסטים נשמרים ב-`admin_broadcasts` (הורחב ב-mig 028: `audience IN ('all','plan','trial_ending')` + `channel_in_app`/`channel_email`).

**`user_settings` (mig 028) — הגדרות סריקה נשמרות (B5/F5):** `user_id` PK, `call_sign` (זהות מ-onboarding S9), `analysis_lens IN ('ema200','rsi','volume','full')`, `risk_style IN ('conservative','balanced','aggressive')`, `coin_prefs` (JSON), `palette`. **display & geometry בלבד — לעולם לא מה שנחשב הזדמנות** (RED LINE §3.5.5).

**`admin_events` (mig 006, קיים מראש) — audit trail של B7:** כל mutation של האדמין (plan override / extend-trial / grant-XP / suspend) נכתבת ל-`admin_events(admin_id, event_type, target_user_id, details_json, created_at)`. XP source `admin_grant` audited דרך זה (‏`XP_ECONOMY.md` §1, לא user-earnable).

**Endpoints שנוספו (Package B):**
| endpoint | תיאור |
|---|---|
| `GET /api/scan/entitlements` | binding gating config לפי tier → `{tier, coins_per_scan, chart_layers, scans_per_day}` (‏`core/entitlements.py`). |
| `POST /api/scan/events` | דוחה סריקה מעל מכסת המטבעות (403 `PLAN_COIN_LIMIT`); מזכה first-scan-of-day XP (+50, idempotent per day, `daily_first_scan`). |
| `GET /api/plans` | public — 4 המסלולים (Free+Basic/Advanced/Pro) עם price/coins/scans/chart_layers מ-`system_settings`. |
| `GET /api/journal/badge` | ספירת תוצאות לא-חשופות בלבד (reveal badge). |
| `GET /api/profile` · `PUT /api/profile/settings` | פרופיל + call-sign + סולם דרגות; שמירת Lens/Risk Style. |
| `POST /api/support/tickets` | פתיחת טיקט (Report a problem). |
| `POST /api/cardcom/trial` | D1 no-card trial. |
| `GET /api/broadcasts/active` | banner in-app פעיל (לעולם לא מכסה SCAN/disclaimer). |

**מפתחות `system_settings` חדשים (migrations 027–028, admin-editable בלי קוד):**
- **coins/scan:** `scan_coins_free` (=2; basic/advanced/pro נזרעו ב-mig 008).
- **chart layers (E7/F15):** `chart_layers_{free,basic,advanced,pro}` — `'ema200_only'` (Free = chart+EMA200) / `'full'` (בתשלום = כל השכבות).
- **scans/day:** `scans_per_day_{free,basic,advanced,pro}` — Free=1, בתשלום=0 (unlimited). מוצג ב-UI; רק coins/scan + chart_layers hard-gated בשרת בשלב זה.
- **admin (B7e):** `trial_reminder_day` (=11), `journal_history_days_free` (=7).

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
- **מספר מטבעות בסריקה:** לפי פלאן (בסיס 2 / מתקדם 5 / פרו 10), נשלט מהאדמין דרך `system_settings` בלי קוד.
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

- **Cardcom v11** (V1): checkout (LowProfile/Create), webhook HMAC, recurring (ChargeToken), **trial 14 יום ללא כרטיס** (ללא tokenization בהרשמה, ללא חיוב אוטומטי; תזכורת יום 11; בסוף התקופה בחירה אקטיבית: פלאן בתשלום או Free). לכידת הכרטיס (tokenization) עוברת לרגע ההמרה לתשלום בלבד. Stripe גלובלי = V2. _(change order מאושר — נדב 2026-07-09; מחליף את "trial עם כרטיס" שהיה נעול.)_
- **Free + 3 פלאנים בתשלום:**

| פלאן | מחיר ₪/חודש | מטבעות בסריקה |
|---|---|---|
| Free | 0 | 2 (סריקה 1/יום) |
| בסיס | 50 | 2 |
| מתקדם | 100 | 5 |
| פרו | 150 | 10 |

> כל המגבלות (מטבעות, סף) נשלטות מהאדמין דרך `system_settings` בלי קוד. אוצר מילים אחד לפלאנים (לא premium/b2b מול pro/unlimited).
> **Free tier (D2, נדב 2026-07-09):** סריקה 1/יום · 2 מטבעות · **Trading Blueprint מלא** · דאשבורד F3 מוגבל ל-7 הימים האחרונים · ללא ייצוא · academy בסיסי. כל המגבלות נשלטות דרך `system_settings`. במסכי paywall/פיצול — אפשרות משנית "Continue on Free".

- **קופונים:** Cardcom/migration 020 + admin UI.
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
| **P1 — תשתית חיה** | חיבור Cardcom v11 (credentials+webhook), מחיקת Morning/legacy, auth מחוזק, deploy ב-Railway. (Resend כבר עובד.) | P0 |
| **P2 — ליבת סריקה** | client-side Bybit fetch + ציון + עיגולים + כרטיס החלטה. `scan_events`/`score_log`/`decision_snapshots`. | P1 |
| **P3 — לולאת למידה** | cron backtest "מה היה קורה" + דאשבורד לקוח. | P2 |
| **P4 — מסחרי** | פלאנים, trial, קופונים, referral חדש, paywall. | P1 |
| **P5 — מנהל+קהילה** | אדמין (MRR/churn מתוקן), טיקטים, ברודקאסט, academy, onboarding survey. | P4 |
| **V2** | Stripe גלובלי, כפתור "העתק לפרומפט LLM", PWA push. | — |

---

## 12. החלטות שנסגרו (v1.0)

| # | החלטה |
|---|---|
| 1 | **3 פלאנים: בסיס 50 / מתקדם 100 / פרו 150 ₪** |
| 2 | מטבעות בסריקה: בסיס 2 / מתקדם 5 / פרו 10 — **נשלט מהאדמין בלי קוד** |
| 3 | trial **ללא כרטיס** (change order, נדב 2026-07-09): 14 יום, ללא tokenization בהרשמה, ללא חיוב אוטומטי, תזכורת יום 11; בסוף התקופה בחירה אקטיבית — פלאן בתשלום או Free. לכידת הכרטיס עוברת לרגע ההמרה לתשלום. _(מחליף את "trial עם כרטיס" שהיה נעול ב-v1.0.)_ |
| 4 | **חבר מביא חבר:** 50% הנחה לחודש למגייס, רק אחרי 3 חודשי התמדה של המגויס + בקרת אדמין |
| 5 | קהל V1 ישראלי (Cardcom), **UI באנגלית מלאה**, Stripe בעתיד |
| 6 | וידאו: YouTube unlisted מספיק ל-V1 |
| 7 | מנוע משותף ב-**JS** (`scoring-engine.js`); כלי אישי לוקלי, SaaS בענן |
| 8 | **Free tier** (נדב 2026-07-09): סריקה 1/יום · 2 מטבעות · Blueprint מלא · F3 מוגבל 7 ימים · ללא ייצוא · academy בסיסי — נשלט `system_settings` |

### עדיין פתוח (לא חוסם מימוש)
- **מסגור משפטי** — Claude יכתוב טיוטת ToS/דיסקליימר "ניתוח לא ייעוץ" + הסכמת פרטיות; נדב מעביר לעו"ד לאישור.
- **מחירי trial/הנחות מדויקים** — נדב מאמת מול רו"ח.

---

_v1.0 — §12 נסגר, מנוע משותף ב-JS, Cardcom יחיד, Resend עובד. הצעד הבא: Claude Design למסע לקוח/UX (ראו FINARODA_SAAS_UX.md) → מימוש לפי הפאזות._
