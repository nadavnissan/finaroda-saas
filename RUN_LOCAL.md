# RUN_LOCAL.md — Run FINARODA locally on Windows (PowerShell)

Exact steps to bring a **fresh clone** up on Windows, from zero to a working sign-in.
Written because these specific steps (env file location, DEV sign-in flag, the beta gate,
and stale browser storage) have each cost hours. Follow them in order.

> Prereqs: **Python 3.13**, **Node 20+**, **pnpm 10+** (`npm i -g pnpm`), and Git.
> Run every command from **PowerShell**. Paths below assume the repo root
> `C:\...\finaroda-saas` (adjust to wherever you cloned).

---

## 1. Backend (FastAPI) — port 8000

```powershell
# from the repo root
cd C:\path\to\finaroda-saas

# 1a. create + activate a virtualenv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
#   If activation is blocked by execution policy, run once (current user):
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   then re-run Activate.ps1

# 1b. install backend deps
pip install -r backend/requirements.txt

# 1c. create the backend .env from the template
Copy-Item backend\.env.example backend\.env
```

### 1d. Fill `backend\.env` — the four values that actually matter locally

Open `backend\.env` and set these (the rest can stay as the template defaults for local dev):

| Var | Local value | Why |
|-----|-------------|-----|
| `JWT_SECRET` | any long random hex | Signs your session cookie. Generate one below. |
| `ENCRYPTION_KEY` | a Fernet key | Present so nothing complains. Generate one below. |
| `DEV_RETURN_MAGIC_LINK` | `true` | Makes `/login` show a **DEV SIGN-IN** button and return the magic link in the API response — you sign in with **no email server**. (The app refuses to boot with this `true` when `ENVIRONMENT=production`.) |
| `FEATURE_PUBLIC_SIGNUPS_OPEN` | `true` | Bypasses the closed-beta allowlist so any email can sign up locally. Keep it `false` only if you want to test the real gate (see §4). |

Generate the two secrets (with the venv active):

```powershell
# JWT_SECRET
python -c "import secrets; print(secrets.token_hex(32))"

# ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste each into `backend\.env`. Leave `ENVIRONMENT=development` and
`RESEND_API_KEY=` empty (empty → emails are logged to the console, never sent).

### 1e. Run the API

```powershell
# from the repo root, venv active. Migrations run automatically on startup
# (creates data\finaroda.db and applies all migrations).
uvicorn backend.main:app --reload --port 8000
```

Check it: open <http://localhost:8000/api/health> → `{"status":"ok",...}`.
API docs at <http://localhost:8000/docs>.

---

## 2. Frontend (Next.js) — port 3000

Open a **second** PowerShell window (leave the API running in the first).

```powershell
cd C:\path\to\finaroda-saas

# 2a. install the whole pnpm workspace (frontend + shared scoring-engine).
#     Run this at the REPO ROOT, not inside frontend/ — it is a workspace.
pnpm install

# 2b. point the frontend at the local API (optional: this is already the default).
Set-Content -Path frontend\.env.local -Value "NEXT_PUBLIC_API_URL=http://localhost:8000" -Encoding utf8

# 2c. start the dev server
cd frontend
pnpm dev
```

Open <http://localhost:3000>. Sign in via **DEV SIGN-IN** on `/login` (works because
`DEV_RETURN_MAGIC_LINK=true`). New users land in onboarding; finishing it grants the
one-time 300 XP and drops you on `/scan`.

---

## 3. Run the test suites (optional but recommended)

```powershell
# backend (repo root, venv active)
python -m pytest -q

# frontend unit tests
cd frontend
pnpm test:unit

# shared scoring-engine tests
cd ..\shared
pnpm test
```

---

## 4. Add a test user to the beta allowlist (only if `FEATURE_PUBLIC_SIGNUPS_OPEN=false`)

The closed-beta gate lets only allowlisted emails sign up. The founder email
(`rodanis@gmail.com`) is seeded by migration 011. To test the gated flow with another
email, either set `FEATURE_PUBLIC_SIGNUPS_OPEN=true` (opens signup to everyone — simplest),
**or** keep it `false` and insert the email:

```powershell
# repo root, venv active. The DB is created on first API startup (§1e).
python -c "import sqlite3; c=sqlite3.connect('data/finaroda.db'); c.execute(\"INSERT OR IGNORE INTO beta_allowlist (email, added_by, note) VALUES ('you@example.com','local','manual test user')\"); c.commit(); print('added')"
```

Use the same email in the DEV SIGN-IN box.

---

## 5. When things look broken after an auth/session change — CLEAR SITE DATA

The app stores a session cookie plus local/session storage (onboarding progress, scan
state, notification read-state). After switching users, changing `JWT_SECRET`, or pulling
new code, **stale browser storage** is the usual cause of weird states (stuck on a screen,
"logged in as nobody", a scan result that will not clear).

Fix in Chrome/Edge:

1. Open DevTools (**F12**) → **Application** tab.
2. Left sidebar → **Storage** → **Clear site data** (clears cookies + local + session storage for the origin).
3. Hard-reload (**Ctrl+Shift+R**).

If the backend schema itself looks wrong, stop the API, delete the local DB
(`Remove-Item data\finaroda.db*`), and restart the API — migrations rebuild it from
scratch (you lose local test data only).

---

## Ports & summary

| Service | Command (from) | URL |
|---------|----------------|-----|
| Backend API | `uvicorn backend.main:app --reload --port 8000` (repo root) | http://localhost:8000 |
| Frontend | `pnpm dev` (frontend/) | http://localhost:3000 |

Two terminals, API first. Sign in with DEV SIGN-IN. Clear site data when in doubt.
