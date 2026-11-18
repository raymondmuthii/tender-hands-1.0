# Tender Hands

A Kenyan charity donation platform. The repo contains two independent apps:

```
tender-hands-pixel-perfect/
├── frontend/        TanStack Start (React + TypeScript + Vite)
├── backend/         Flask REST API (Python)
└── DEPLOYMENT.md    Vercel dashboard settings for both projects
```

---

## Running locally

Open **two terminals**.

### Terminal 1 — Backend

```powershell
cd backend

# First time only
uv venv .venv
.venv\Scripts\activate
uv pip install -r requirements-dev.txt
Copy-Item .env.example .env   # then edit .env with your secrets
flask --app api:app db upgrade
python seed.py

# Every time
.venv\Scripts\activate
flask --app api:app run --debug
```

API available at → **http://localhost:5000**

### Terminal 2 — Frontend

```powershell
cd frontend

# First time only
npm install

# Every time
npm run dev
```

Frontend available at → **http://localhost:3000** (check terminal for exact port)

---

## Running the tests

**Backend** (85 tests, in-memory SQLite, no backend server needed):

```powershell
cd backend
.venv\Scripts\activate
pytest
```

**Frontend** (28 tests, Vitest + Testing Library, API client mocked):

```powershell
cd frontend
npm test
```

---

## Who lands where

| Role | Page after login |
|---|---|
| `donor` | `/dashboard` |
| `charity` | `/owner` – submit a charity, manage stories, beneficiaries and inventory |
| `admin` | `/admin` – approve / reject / feature charities |

New accounts are created as `donor` (default) or `charity`; admin accounts are
made with the seed script locally or `flask shell` in production.

---

## How they connect

`frontend/.env` controls where the frontend points:

```env
VITE_API_URL=http://localhost:5000
```

In development, Vite proxies all `/api/*` requests to Flask so there are no CORS issues.
In production, set `VITE_API_URL` to your deployed backend URL in the Vercel dashboard.

---

## Seed accounts (after running `python seed.py`)

| Role | Email | Password |
|---|---|---|
| Admin | admin@tenderhands.co.ke | Admin@1234! |
| Donor | donor@tenderhands.co.ke | Donor@1234! |
| Charity owner | owner@tenderhands.co.ke | Owner@1234! |

---

---

## Deploying

Both apps deploy to Vercel as two projects (backend `backend/`, frontend
`frontend/`) configured entirely in the dashboard – there is no `vercel.json`.
See **`DEPLOYMENT.md`** for the exact settings, every environment variable, and
the post-deploy smoke-test checklist.

---

See `backend/README.md` for full API docs, migration commands, and M-Pesa setup
(`backend/docs/mpesa-testing.md` covers sandbox verification).
