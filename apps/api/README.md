# COMMUNITI API

FastAPI backend for COMMUNITI.

## Local Setup

```bash
cd apps/api
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
```

Edit `.env` and set your real PostgreSQL password:

```text
DB_HOST=localhost
DB_PORT=5432
DB_NAME=communiti_dev
DB_USER=postgres
DB_PASSWORD=YOUR_PASSWORD
```

Use the separate `DB_*` fields locally. They are safer than a full `DATABASE_URL` because passwords with `@`, `#`, `/`, or `:` do not need URL encoding.

Run:

```bash
uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000/docs
```

## First Endpoints

```text
GET /health
GET /api/v1/health/db
GET /api/v1/meta/categories
GET /api/v1/meta/tags
```

## Authentication

Google login is handled through Clerk.

The frontend will use Clerk's Google OAuth flow, then send a Clerk JWT to this API:

```text
Authorization: Bearer <clerk_jwt>
```

FastAPI verifies the token, maps it to a local `users` row, and applies authorization policies.

Required API environment fields:

```text
CLERK_ISSUER=https://your-clerk-frontend-api.clerk.accounts.dev
CLERK_JWKS_URL=
CLERK_AUDIENCE=
CLERK_AUTHORIZED_PARTIES=http://localhost:3000,http://127.0.0.1:3000
```

Leave `CLERK_JWKS_URL` empty unless you need to override Clerk's default JWKS URL. Google OAuth Client ID and Client Secret belong in the Clerk dashboard, not in the FastAPI `.env`.

## Seed local data

After the schema exists and `.env` has the correct DB password, run:

```bash
python -m app.scripts.seed_dev
```

This inserts idempotent demo users, clubs, events, registrations, and saved events.
