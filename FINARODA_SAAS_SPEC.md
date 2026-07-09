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
משמש את סימולציית האונבורדינג (F13, ראו `FINARODA_ONBOARDING_SPEC.md`). כל אפיזודה = **טווח kline אמיתי ומתוארך** מקובץ הטריידים/בקטסטים + התוצאה בפועל. הגרפים **מרונדרים אצלנו** מ-kline דרך `recharts` הקיים ב-frontend — **לעולם לא צילומי מסך מ-TradingView/Bybit** (רישוי במוצר מסחרי + עקביות ויזואלית).
```sql
CREATE TABLE episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin TEXT NOT NULL,
    date_range TEXT NOT NULL,        -- טווח מתוארך (מקור אמת: trades CSV / AnchorLog)
    kline_data TEXT NOT NULL,        -- נרות גולמיים לרינדור מקומי (recharts)
    scenario_type TEXT NOT NULL,     -- trap | valid_setup | discipline_save | patience
    lesson_flag TEXT,                -- הדגל החינוכי שהאפיזודה מדגימה
    outcome TEXT NOT NULL,           -- תוצאת האמת של האפיזודה (למשל דעיכה ב-X%)
    real_stats_ref TEXT,             -- הפניה למספר האמת (אימות מול ה-CSV לפני שילוב)
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```
> אמת אמפירית בלבד: כל מספר שמוצג באונבורדינג מגיע מ-`real_stats_ref` מאומת. אין סטטיסטיקות מומצאות ואין הוכחה חברתית מפוברקת.

---

## 6. מנוע הסריקה (client-side) + המנוע המשותף

### 6.1 המנוע המשותף — `scoring-engine.js`
לוגיקת החישוב הטהורה (אפס UI): EMA7 slope signed, volume ratio, price-vs-EMA7, מרחק SL, ציון, גאומטריית SL/עוגן. **קובץ JS אחד** שהכלי האישי וה-SaaS מייבאים שניהם.

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
