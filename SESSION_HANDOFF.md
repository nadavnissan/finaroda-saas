# SESSION HANDOFF — FINARODA SaaS

> מוחלף בסוף כל סשן. מסמך "איך להיכנס", לא ארכיון.

---

> NOTE: from 2026-07-01 this handoff is written in **English** (terminal mangles Hebrew).

## Where we are now
- **Active branch:** dev
- **Remote:** `origin` = https://github.com/nadavnissan/finaroda-saas.git ✅
- **Last commit (dev):** deploy/build chore commits (v0.4.2–v0.4.7) + Vercel trigger — on top of P2 scorer.
- **Validation:** ✅ all green — pytest 25/25, shared node --test 12/12, tsc clean, eslint clean, next build 16 routes.
- **main:** = `1338a26` (P2 scorer, from the authorized dev→main merge). The staging deploy/build chores (v0.4.2–v0.4.7) are **dev only** — Nadav merges to main manually.

## 🟢 STAGING — LIVE (deployed from `dev`)
- **Frontend (Vercel):** https://finaroda-saas.vercel.app  — Root Directory `frontend`, pnpm workspace, Production Branch = `dev`.
- **Backend (Railway):** https://finaroda-saas-production.up.railway.app  — nixpacks Python, volume `/app/data`, plain uvicorn (no Litestream). `ENVIRONMENT=staging`.
- **Cardcom:** TEST mode (`FEATURE_CARDCOM_LIVE=false`) — no real charges.
- **Login on staging (no email):** `DEV_RETURN_MAGIC_LINK=true` + `FEATURE_PUBLIC_SIGNUPS_OPEN=true`. To log in: `POST {backend}/api/auth/magic-link {"email":"..."}` → the response's `dev_magic_link` contains the token → open it (or `GET {backend}/api/auth/verify?token=...`) to set the `access_token` cookie. `rodanis@gmail.com` is a bootstrap admin (is_admin=true).
- **Smoke test (2026-07-01, all PASS):** health 200 (env=staging) · magic-link→verify→/me authenticated as rodanis (is_admin) · authenticated `POST /api/scan/events` → 200, persisted `scan_event_id=1` + `score_log` BTCUSDT · unauthenticated `/api/scan/events` → 401 (expected, auth-required — not CORS).
- **Not deployed:** Litestream/R2 backups (skipped for staging), Resend email (dev-return link instead), production domain (finaroda.com), lawyer/accountant sign-off.

## מה נעשה בסשן האחרון (P1 — תשתית חיה)
- **Auth (מוקשח, SPEC §4):** magic-link (Resend, console fallback בdev) + Google OAuth (iss תמיד, aud כשיש CLIENT_ID) + Apple stub(501). JWT ב-httpOnly cookie + get_current_user. magic-link token נשמר כ-**SHA-256 hash**. admin כ-role ב-DB (users.is_admin) עם bootstrap לפי ADMIN_BOOTSTRAP_EMAILS. beta gate + allowlist + waitlist. endpoints: /api/auth/{magic-link,verify,google,apple,logout,me} + /api/waitlist.
- **Cardcom v11 (TEST mode בלבד):** initiate(LowProfile)/webhook(HMAC)/status/cancel + charge_recurring(ChargeToken) + start_trial(14 יום, כרטיס) + run_renewal_batch + expire_trials. מיפוי basic/advanced/pro, מחירים מ-system_settings. **הכל dry-run/503 עד FEATURE_CARDCOM_LIVE=true.** migration 019 (billing_failure_count + מחירי פלאנים).
- **Deploy (מוכן, לא פרוס):** railway.toml (+3 crons), nixpacks.toml, litestream.yml (finaroda.db→R2), Dockerfile.
- **Frontend:** src/lib/api.ts + login/verify/coming-soon/paywall/checkout(success,cancelled) מחוברים ל-endpoints. UI אנגלית.

## מה עודכן ע"י נדב (לא Claude): scoring-engine
- **🟢 levels engine חולץ** מהכלי האישי (v25.80) ל-`shared/scoring-engine.js`: calcEMA/RSI/ATR/ADX/closedCandles/ema7Slope/computeSlTp/computeReversalAnchor — byte-faithful, node --test 8/8.
- **🟡 scoreDirection עדיין stub שזורק** — pass 2, דורש golden vectors מהכלי האישי (ראו `shared/scoring-engine.api.md`).

## Latest change — DOCS regulatory reframing (docs only, no code)
- Reframed the FRONT-END as a utility calculator. **Engine/score/edge/threshold unchanged.**
- New calculator terminology (Mathematical Trigger Point / Calculated Risk Level / Calculated Target Level / Dynamic Risk Level / Trading Blueprint), formula-transparency notes, an **Analysis Lens** (display only) and a **Risk Style** (Conservative/Balanced/Aggressive → `computeSlTp` opt only).
- **RED LINE:** client never changes score/weights/edge/85-82 threshold — only what's displayed + risk geometry. Authoritative spec: **PRD §3.5**; legal spine: **LEGAL §6**.
- **One product-scope change:** the per-user "personal threshold" was removed (violated the RED LINE). `users.default_threshold` stays for admin-only per-user overrides.
- Docs: PRD v2.1, UX v1.2, LEGAL v2.

## Latest — P2 scorer wired (real score live, dev only)
- **Real scorer wired:** `scoreDirection` (momentum profile = `MOMENTUM_CAL`) imported from `@finaroda/scoring-engine/scorer.js` (verbatim v25.80, untouched). `SCORE_GATE_ENABLED=true` — the live **85 PASS / 82-84 WATCH** gate on the numeric score; a `blocked` macro-gate result is hidden.
- **Direction:** score both long+short (momentum); prefer non-blocked, then higher score.
- **3 profiles logged (measure-first):** momentum (displayed) + pullback (`DEFAULT_CALIBRATION`) + continuation (`{...DEFAULT_CALIBRATION, entryMode:'continuation'}`) → `score_log` (migration 021 added `profile`). Only momentum is displayed.
- **RED LINE kept:** score uses fixed inputs (`DEFAULT_RISK`+`MOMENTUM_CAL`); Risk Style feeds only `computeSlTp` opt (levels). Analysis Lens is now display-only (no longer gates).
- **marketData extended client-side:** weekly (derived), open interest + oiChangePct (best-effort), change24h; marketContext (coinChanges/mean/std) built per scan.

## P2 scan core (base, done, dev only)
- **Scan flow:** central SCAN button + Lens/Risk-Style toggles → streaming log (4 steps) → client-side Bybit fetch (user IP, no shared cache; thin `/api/market/proxy` CORS fallback) → passers as circles (ring ≤5 / list >5) → **Trading Blueprint** → empty state (F1b).
- **Engine imported** as `@finaroda/scoring-engine` (symlink to `shared/`, `transpilePackages`, ambient d.ts). Levels only: computeSlTp / computeReversalAnchor / ema7Slope / indicators. **scoreDirection never called.**
- **Score-pending:** every coin recorded with `score=NULL` (migration 020); card shows "Score pending — engine pass 2 (levels are real)". Real 85/82 gate wired behind `SCORE_GATE_ENABLED=false` in `engine.ts`.
- **Interim rules (documented):** direction = sign of verified EMA7 slope; visibility = levels valid + Analysis-Lens condition (`lens.ts`).
- **Persistence (SPEC §5):** `POST /api/scan/events` (scan_events + score_log) and `POST /api/scan/snapshot` (decision_snapshots), auth-required, best-effort from the client.
- **RED LINE honored:** Lens = display only; Risk Style = `computeSlTp` opt only; score/weights/edge/threshold never client-touchable.

## Next step — P3 (learning loop)
- **Score is live** — no longer blocked (scorer extracted + wired).
- **P3 (SPEC §11):** backtest cron over `score_log` (outcome NULL) → "what would have happened" dashboard (F3). The 3 profiles now in `score_log` enable base-rate per profile.
- **Still open:** per-plan coin limit (2/5/10 from system_settings) not yet wired into the scan universe (currently a fixed 10-coin default). Open-interest/marketContext are best-effort — revisit accuracy in P3.

## מוכן לפריסה (ממתין להפעלה ידנית של נדב)
- **Cardcom live:** להזין credentials אמיתיים (sandbox→prod) + FEATURE_CARDCOM_LIVE=true. עד אז אין חיוב.
- **Railway deploy:** לחבר repo, למפות volume ל-/app/data, להזין env vars (backend/.env.example), להפעיל. CI (pytest+tsc) — עוד לא נכתב (אפשר ב-P2+).
- **Resend/Google/R2:** להזין מפתחות אמיתיים ב-env הפרודקשן.

## פתוחים / חוסמים
- אישור PRD מנדב; אישור עו"ד ל-LEGAL; אימות מחירים מול רו"ח; פלט Claude Design ל-UX.
- scoreDirection pass 2 (golden vectors) — חוסם ציון אמיתי ב-P2.

---

## תזכורת Branch Gate
Claude עובד על dev בלבד. נדב ממזג dev→main ידנית. אסור ל-Claude לגעת ב-main/production.

## איך מריצים מקומית
- Backend: `.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --port 8000`
- Frontend: `cd frontend && pnpm dev`  (צריך `NEXT_PUBLIC_API_URL`, ברירת מחדל localhost:8000)
- Validation: `.venv/Scripts/python.exe -m pytest` · `cd frontend && pnpm exec tsc --noEmit && pnpm run lint` · `cd shared && node --test`
