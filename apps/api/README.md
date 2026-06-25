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
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/communiti_dev
```

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

## Authentication Plan

Google login will be handled through Clerk.

The frontend will use Clerk's Google OAuth flow, then send a Clerk JWT to this API:

```text
Authorization: Bearer <clerk_jwt>
```

FastAPI will verify the token, map it to a local `users` row, and apply authorization policies.
