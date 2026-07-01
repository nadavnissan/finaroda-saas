# SESSION HANDOFF — FINARODA SaaS

> מוחלף בסוף כל סשן. מסמך "איך להיכנס", לא ארכיון.

---

> NOTE: from 2026-07-01 this handoff is written in **English** (terminal mangles Hebrew).

## Where we are now
- **Active branch:** dev
- **Remote:** `origin` = https://github.com/nadavnissan/finaroda-saas.git ✅
- **Last commit:** DOCS — regulatory reframing (calculator framing) on top of P1 / engine extraction / P1.5 / P0
- **Validation:** ✅ all green — pytest 16/16, shared node --test 8/8, tsc clean, eslint clean, next build (16 routes), uvicorn boot (health 200, auth/me 401, cardcom 401, waitlist 200). Reframing was docs-only (no code), so the last green state stands.
- **Production (main):** NOT updated since P0+P1.5 (= b011b83). Everything after that (engine extraction, P1, reframing) is on **dev only** — Nadav merges to main manually.

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

## Next step — P2 (scan core)
Per SPEC §11: client-side Bybit fetch + rings + Trading Blueprint. Real **levels** can be wired now (the levels engine exists). The **score** (PASS≥85 / WATCH 82-84) is blocked until `scoreDirection` pass 2. When P2 builds the Blueprint, use the v2.1 calculator terminology and honor Analysis Lens (display) + Risk Style (`computeSlTp` opt), never touching the score (RED LINE).

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
