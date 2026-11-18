# Tender Hands – Backend API

Flask-based REST API for the Tender Hands Kenyan charity donation platform.

## Tech Stack

| Concern | Library |
|---|---|
| Framework | Flask 3 (app factory + blueprints) |
| ORM | Flask-SQLAlchemy + Flask-Migrate (Alembic) |
| Validation / Serialization | Marshmallow |
| Authentication | Flask-JWT-Extended (access + refresh tokens) |
| CORS | Flask-CORS |
| Payments | Safaricom Daraja M-Pesa STK Push |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Deployment | Vercel (serverless, entry point `api.py`) |

---

## Local Setup

### 1. Prerequisites

- Python 3.11+
- pip or any Python package manager

### 2. Clone and install

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements-dev.txt
```

### 3. Environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Key variables:

| Variable | Default | Description |
|---|---|---|
| `FLASK_ENV` | `development` | `development` / `production` / `testing` |
| `SECRET_KEY` | *(required)* | Flask session secret |
| `DATABASE_URL` | `sqlite:///tender_hands_dev.db` | DB connection string |
| `JWT_SECRET_KEY` | *(required)* | JWT signing secret |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated allowed origins |
| `MPESA_ENV` | `sandbox` | `sandbox` or `production` |
| `MPESA_CONSUMER_KEY` | – | Daraja app consumer key |
| `MPESA_CONSUMER_SECRET` | – | Daraja app consumer secret |
| `MPESA_SHORTCODE` | `174379` | Business shortcode |
| `MPESA_PASSKEY` | – | Lipa Na M-Pesa passkey |
| `MPESA_CALLBACK_URL` | – | Public HTTPS URL for Daraja callbacks |
| `CRON_SECRET` | – | Shared secret the scheduler sends to `POST /api/recurring/run-due` |

### 4. Database migrations

```bash
# First time – initialise migration history (already done if repo cloned)
flask --app api:app db init

# After model changes
flask --app api:app db migrate -m "describe change"
flask --app api:app db upgrade
```

### 5. Seed the database

```bash
python seed.py
```

Creates:
- **Admin** – `admin@tenderhands.co.ke` / `Admin@1234!`
- **Charity owner** – `owner@tenderhands.co.ke` / `Owner@1234!`
- **Demo donor** – `donor@tenderhands.co.ke` / `Donor@1234!`
- 4 approved charities (Amani, Maji Kwa Wote, Tumaini, Tupande)
- 5 completed sample donations + 1 recurring donation

### 6. Run the dev server

```bash
flask --app api:app run --debug
```

API is available at `http://localhost:5000`.

---

## Running Tests

```bash
pytest
```

85 tests (auth, charities, donations, recurring scheduling, admin, M-Pesa).

For verbose output:

```bash
pytest -v
```

---

## Endpoint Reference

All endpoints are prefixed `/api`.

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | – | Register a new user |
| `POST` | `/auth/login` | – | Login (email or phone) |
| `POST` | `/auth/refresh` | Refresh token | Get new access token |
| `GET` | `/auth/me` | Bearer | Get current user profile |
| `PATCH` | `/auth/me` | Bearer | Update profile / password |

### Charities

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/charities` | – | List approved charities (filter: `category`, `featured`, `search`, `page`, `per_page`) |
| `GET` | `/charities/mine` | `charity` role | The signed-in owner's charity (`null` before they apply) |
| `GET` | `/charities/<slug>` | – | Get charity detail |
| `POST` | `/charities` | `charity` role | Submit charity application (creates as pending) |
| `PATCH` | `/charities/<slug>` | Owner or admin | Update charity fields |

### Charity Owner Sub-resources

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/charities/<slug>/stories` | – | List published impact stories (owner/admin: `?all=1` includes drafts) |
| `POST` | `/charities/<slug>/stories` | Owner | Create impact story |
| `PATCH` | `/charities/<slug>/stories/<id>` | Owner | Update story |
| `DELETE` | `/charities/<slug>/stories/<id>` | Owner | Delete story |
| `GET` | `/charities/<slug>/beneficiaries` | Owner | List beneficiaries |
| `POST` | `/charities/<slug>/beneficiaries` | Owner | Add beneficiary |
| `PATCH` | `/charities/<slug>/beneficiaries/<id>` | Owner | Update beneficiary |
| `DELETE` | `/charities/<slug>/beneficiaries/<id>` | Owner | Delete beneficiary |
| `GET` | `/charities/<slug>/inventory` | Owner | List inventory items |
| `POST` | `/charities/<slug>/inventory` | Owner | Add inventory item |
| `PATCH` | `/charities/<slug>/inventory/<id>` | Owner | Update item |
| `DELETE` | `/charities/<slug>/inventory/<id>` | Owner | Delete item |

### Donations

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/donations` | `donor` role | Initiate M-Pesa STK push and create pending donation |
| `GET` | `/donations/me` | `donor` role | Donor's donation history |
| `GET` | `/donations/<id>/receipt` | Bearer | Get receipt for completed donation |
| `POST` | `/mpesa/callback` | – (Daraja webhook) | Receive M-Pesa payment result |

### Recurring Donations

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/recurring` | `donor` role | List user's recurring donations |
| `POST` | `/recurring` | `donor` role | Create recurring donation |
| `PATCH` | `/recurring/<id>` | `donor` role | Update amount / status / next run date |
| `DELETE` | `/recurring/<id>` | `donor` role | Cancel (sets status to `cancelled`) |
| `POST` | `/recurring/run-due` | `X-Cron-Secret` header | Charge every due recurring donation (scheduler only) |

### Dashboard

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/dashboard/summary` | `donor` role | `total_donated`, `charities_supported`, `monthly_giving`, `recent_donations` |

### Admin

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/admin/charities` | `admin` role | List all charities (filter: `status`) |
| `POST` | `/admin/charities/<slug>/approve` | `admin` role | Approve a pending charity |
| `POST` | `/admin/charities/<slug>/reject` | `admin` role | Reject a charity |
| `POST` | `/admin/charities/<slug>/feature` | `admin` role | Toggle featured status |
| `GET` | `/admin/stats` | `admin` role | Platform-wide statistics |

---

## Response Format

All responses follow a consistent envelope:

```json
{
  "success": true,
  "data": { ... },
  "meta": { "total": 42, "page": 1, "per_page": 12, "pages": 4 }
}
```

Errors:

```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": { "email": ["Not a valid email address."] }
}
```

---

## M-Pesa Integration

Payments use Safaricom Daraja STK Push (sandbox by default).

1. `POST /api/donations` triggers an STK push to the donor's phone.
2. The donation record is created with `status: "pending"` and stores the `CheckoutRequestID`.
3. Safaricom POSTs to `MPESA_CALLBACK_URL` (`/api/mpesa/callback`).
4. The callback handler matches by `CheckoutRequestID`, then sets status to `completed` (with receipt number) or `failed`.

> **Never trust the client** to mark a donation as completed – only the Daraja callback does this.

Requests are built to match Daraja's requirements: the `Timestamp` is
`YYYYMMDDHHmmss` in **East Africa Time** (UTC+3) and the same string is used for
the password, `Amount` is a whole number, and `PartyA` / `PhoneNumber` are
normalised to `2547XXXXXXXX`.

### Checking the sandbox

```bash
cd backend
.venv\Scripts\activate           # macOS/Linux: source .venv/bin/activate
python scripts/mpesa_sandbox_check.py 254708374149 1
```

Sends one STK Push with your `.env` credentials and prints Daraja's response.
Full walkthrough (Daraja app, passkey, ngrok, expected database rows) is in
[`docs/mpesa-testing.md`](docs/mpesa-testing.md).

The live sandbox flow has **not** been verified from this repository yet – see
the checklist in that document.

---

## Scheduled recurring donations

Vercel has no background worker, so a scheduler calls the endpoint instead:

```bash
curl -X POST https://your-backend.vercel.app/api/recurring/run-due \
  -H "X-Cron-Secret: $CRON_SECRET"
```

- The header is compared in constant time against `CRON_SECRET`; a missing or
  wrong secret returns `403`, and an unset `CRON_SECRET` rejects every call.
- Every `active` recurring donation with `next_run_date <= today` gets a pending
  donation (linked via `donations.recurring_donation_id`), an STK Push attempt,
  and a `next_run_date` advanced by one month.
- A failed STK Push is logged and counted in `failed`; the rest of the batch
  still runs.
- Calling it twice on the same day does not charge twice: the schedule has
  already moved on, and a donation created earlier the same day is skipped.

Locally:

```bash
curl -X POST http://localhost:5000/api/recurring/run-due -H "X-Cron-Secret: <your CRON_SECRET>"
```

A daily external scheduler (cron-job.org, GitHub Actions) is set up in
[`../DEPLOYMENT.md`](../DEPLOYMENT.md) step 5.

---

## Deployment to Vercel

Full dashboard settings, environment variables and the smoke-test checklist live
in [`../DEPLOYMENT.md`](../DEPLOYMENT.md). In short:

1. Root directory `backend`, Framework Preset `Flask`.
2. Vercel's Flask preset looks for `app.py`, `index.py`, `server.py`, `main.py`,
   `wsgi.py` or `asgi.py` – `api.py` is not one of those names, so
   `backend/index.py` re-exports the app from `api.py`. Local commands keep
   using `flask --app api:app`.
3. `DATABASE_URL` must be PostgreSQL (`psycopg2-binary` is in
   `requirements.txt`); SQLite does not persist on serverless functions.
4. Run `flask --app api:app db upgrade` against that database from your machine.
5. No `vercel.json` is used.
