# Deploying Tender Hands to Vercel

Two Vercel projects deploy from this one repository:

| Project | Root directory | Runtime |
|---|---|---|
| `tender-hands-api` | `backend/` | Python / Flask |
| `tender-hands-web` | `frontend/` | TanStack Start (Vite + Nitro) |

Everything below is configured in the **Vercel dashboard**. There is no
`vercel.json` in this repository and none is needed.

Deploy in this order: database → backend → frontend → point the backend's CORS
at the frontend URL.

---

## 0. Prerequisites (you do these)

- The repository pushed to GitHub / GitLab / Bitbucket.
- A PostgreSQL database with a connection string. Vercel Postgres, Neon and
  Supabase all work; the string looks like
  `postgresql://user:password@host:5432/dbname?sslmode=require`.
- Daraja credentials for the backend (`MPESA_*`, see
  `backend/docs/mpesa-testing.md`).

## 1. Backend project – `tender-hands-api`

**Dashboard → Add New → Project → import the repository**, then:

| Setting | Value |
|---|---|
| Project name | `tender-hands-api` |
| **Root Directory** | `backend` |
| **Framework Preset** | `Flask` (auto-detected from `requirements.txt`) |
| **Build Command** | *(leave empty – the Flask preset has no build step)* |
| **Output Directory** | *(leave empty)* |
| **Install Command** | `pip install -r requirements.txt` |

### Entry point

Vercel's zero-configuration Flask preset loads the WSGI `app` from
`app.py`, `index.py`, `server.py`, `main.py`, `wsgi.py` or `asgi.py` (at the
project root, or inside `src/` or `app/`). **`api.py` is not one of those
names**, so the project also ships a two-line `backend/index.py` that re-exports
the app from `api.py`. Vercel loads `index.py` → `api.py`; every local command
still uses `flask --app api:app`.

### Environment variables

**Project → Settings → Environment Variables.** Set each one for *Production*
(and *Preview* if you want previews to work). Values marked 🔒 are secrets –
use "Sensitive" and never commit them.

| Variable | Where the value comes from |
|---|---|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` 🔒 | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_SECRET_KEY` 🔒 | Generate again, separately from `SECRET_KEY` |
| `DATABASE_URL` 🔒 | PostgreSQL connection string from step 0. Leave `?sslmode=require` on Neon/Supabase |
| `CORS_ORIGINS` | The deployed frontend origin, e.g. `https://tender-hands-web.vercel.app` (comma-separated, no trailing slash). Can be set after the frontend is deployed – see step 4 |
| `MPESA_ENV` | `sandbox` for testing, `production` for live money |
| `MPESA_CONSUMER_KEY` 🔒 | Daraja app → Keys |
| `MPESA_CONSUMER_SECRET` 🔒 | Daraja app → Keys |
| `MPESA_SHORTCODE` | `174379` for sandbox; your paybill number in production |
| `MPESA_PASSKEY` 🔒 | Daraja → Simulate → Test Credentials (sandbox) |
| `MPESA_CALLBACK_URL` | `https://tender-hands-api.vercel.app/api/mpesa/callback` |
| `MPESA_DEMO_MODE` | `true` to record donations as paid without calling Daraja (class demo; labelled `M-PESA (demo)`). Leave unset for real payments |
| `CRON_SECRET` 🔒 | Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` – the scheduler sends it as the `X-Cron-Secret` header |

Also set `PYTHON_VERSION` = `3.12` if the detected version cannot install
`psycopg2-binary` (the PostgreSQL driver pinned in `requirements.txt`).

Click **Deploy**, then check:

```bash
curl https://tender-hands-api.vercel.app/api/charities
# {"success": true, "data": [], "meta": {...}}
```

> Serverless functions have no persistent disk. The SQLite default in
> `app/config.py` (`sqlite:///tender_hands_dev.db`) does **not** work on Vercel –
> `DATABASE_URL` must point at PostgreSQL.

## 2. Prepare the production database

Migrations must run against the **same** database as `DATABASE_URL`. Do this
from your machine, before (or right after) the first deploy:

**PowerShell**

```powershell
cd backend
.venv\Scripts\activate
$env:DATABASE_URL = "postgresql://user:password@host:5432/dbname?sslmode=require"
$env:FLASK_ENV = "production"
flask --app api:app db upgrade
```

**bash / macOS / Linux**

```bash
cd backend
source .venv/bin/activate
export DATABASE_URL="postgresql://user:password@host:5432/dbname?sslmode=require"
export FLASK_ENV="production"
flask --app api:app db upgrade
```

This applies both revisions in `backend/migrations/versions/` – the initial
schema and the `donations.recurring_donation_id` column.

Never run `db.create_all()` or `python seed.py` against the production
database.

### Creating the first admin

Public registration only allows the `donor` and `charity` roles, so the admin
account is created deliberately:

```bash
export DATABASE_URL="postgresql://..." FLASK_ENV=production
cd backend
flask --app api:app shell
```

```python
from app.extensions import db
from app.models.user import User

admin = User(full_name="Platform Admin", email="you@example.com", role="admin")
admin.set_password("a-long-unique-password!")
db.session.add(admin)
db.session.commit()
```

## 3. Demo data – staging only ⚠️

`python seed.py` creates charities, sample donations and **three accounts with
publicly known passwords** (`Admin@1234!`, `Owner@1234!`, `Donor@1234!`) plus a
demo admin. It is for local development and a throwaway staging database only.

- Never run it against the production database.
- If you seeded a staging deploy, delete those accounts (or change their
  passwords) before sharing the URL with anyone.
- The admin account that approves real charities in production must be created
  with the shell snippet above, never by seeding.

## 4. Frontend project – `tender-hands-web`

**Dashboard → Add New → Project → import the same repository**, then:

| Setting | Value |
|---|---|
| Project name | `tender-hands-web` |
| **Root Directory** | `frontend` |
| **Framework Preset** | `TanStack Start` if listed; otherwise `Other` |
| **Install Command** | `npm install` |
| **Build Command** | `NITRO_PRESET=vercel npm run build` |
| **Output Directory** | *(leave empty)* |

Nitro writes a Vercel Build Output (`.vercel/output`) during
`NITRO_PRESET=vercel npm run build`; Vercel picks it up automatically, so the
Output Directory must stay empty. This has been verified locally: the build
produces `.vercel/output/config.json` and `.vercel/output/functions/__server.func`.

### Environment variables

| Variable | Value |
|---|---|
| `VITE_API_URL` | `https://tender-hands-api.vercel.app` (the backend project URL, no trailing slash) |

`VITE_API_URL` is baked into the bundle **at build time**. Set it for
Production *and* Preview, and redeploy after changing it.

### Then close the CORS loop

1. Copy the frontend URL Vercel gives you (e.g.
   `https://tender-hands-web.vercel.app`).
2. Go back to `tender-hands-api` → Settings → Environment Variables →
   `CORS_ORIGINS` → set it to that origin (add previews comma-separated if
   needed).
3. Redeploy the backend so the new value takes effect.

## 5. Scheduling recurring donations

Vercel Cron Jobs are configured in `vercel.json`, which this project does not
have, so use an external scheduler. It only needs to call one endpoint once a
day:

```
POST https://tender-hands-api.vercel.app/api/recurring/run-due
X-Cron-Secret: <CRON_SECRET>
```

- **cron-job.org / similar**: URL above, method POST, custom header
  `X-Cron-Secret`, schedule daily at 08:00 Africa/Nairobi.
- **GitHub Actions** (in the repository, optional):

```yaml
name: recurring-donations
on:
  schedule:
    - cron: "0 5 * * *"   # 05:00 UTC = 08:00 EAT
  workflow_dispatch:
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - run: |
          curl --fail --show-error -X POST \
            -H "X-Cron-Secret: ${{ secrets.CRON_SECRET }}" \
            https://tender-hands-api.vercel.app/api/recurring/run-due
```

The response reports `{"due": n, "created": n, "skipped": n, "failed": n}`.
Calling it twice on the same day is safe – already-charged records are skipped.

## 6. Post-deploy smoke test

Run these in order against the deployed URLs.

- [ ] `GET https://<backend>/api/charities` returns `{"success": true, "data": [...]}` (empty list is fine before seeding).
- [ ] **Register** a donor at `https://<frontend>/account` – lands on `/dashboard`.
- [ ] **Log in** with that donor – stays logged in after a page refresh.
- [ ] **Browse charities** at `/charities` – approved charities render, no CORS error in the browser console.
- [ ] **Register a charity** (role "I'm registering a charity") – lands on `/owner`, submit a charity, badge shows *Pending review*.
- [ ] **Admin approve** – log in as the admin, open `/admin` → *Pending* → *Approve*; the owner's badge becomes *Approved* and the charity appears on `/charities`.
- [ ] **Donate** – as the donor, donate KES 10; the M-Pesa prompt arrives on the phone.
- [ ] **Callback received** – after entering the PIN, the donation row goes from `pending` to `completed` with an `mpesa_receipt`, and `/dashboard` shows it.
- [ ] **Recurring run** – `POST /api/recurring/run-due` without the header returns 403, with the header returns 200.
- [ ] **Owner CRUD** – create, edit and delete an impact story, a beneficiary and an inventory item from `/owner`.

Anything failing in the last three steps is an M-Pesa/scheduler issue, not a
deployment issue; see `backend/docs/mpesa-testing.md`.
