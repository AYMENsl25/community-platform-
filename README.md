# COMMUNITI

COMMUNITI is a community clubs SaaS for discovering clubs, joining events, managing organizer workflows, and building toward AI-assisted search and recommendations.

## Tech Stack

- Web: Next.js, React, TypeScript, Tailwind CSS.
- API: FastAPI, Pydantic, SQLAlchemy async, asyncpg.
- Database: PostgreSQL.
- Auth: Clerk JWTs, with Google OAuth handled by Clerk.
- Future AI/search: PostgreSQL search first, pgvector embeddings later.

## Repository Structure

- `apps/api` - FastAPI backend.
- `apps/web` - Next.js frontend.
- `database` - PostgreSQL schema and migrations.
- `docs` - architecture, API, security, CORS, and ADR documentation.
- `BACKEND_FASTAPI_PLAN.md` - backend execution plan.
- `COMMUNITI_BACKEND_PLAN_IMPROVEMENT.md` - backend architecture review.
- `COMMUNITI_PROMPT.md` - original product prompt/reference.

## Prerequisites

- Python 3.12.
- PostgreSQL 15 or newer.
- Node.js and pnpm for the web app.
- A Clerk application when testing real authenticated requests.

## Database Setup

Create a local PostgreSQL database named `communiti_dev`, then apply the schema and migrations from `database`.

```powershell
psql -d communiti_dev -f database/communiti_schema.sql
psql -d communiti_dev -f database/migrations/0001_organizer_requests.sql
```

## API Setup

```powershell
cd apps/api
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Edit `apps/api/.env` with your local database settings. Prefer the separate `DB_*` fields for local development because passwords do not need URL encoding.

Run the API:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs`.

## Web Setup

```powershell
cd apps/web
pnpm install
Copy-Item .env.example .env.local
pnpm dev
```

The frontend expects the API at `http://127.0.0.1:8000/api/v1` by default.

## Clerk And Google Auth Setup

Create a Clerk application, then copy the keys into `apps/web/.env.local`:

```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL=/explore
NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL=/account/onboarding
```

In the Clerk dashboard, enable Google as a social connection. For development, Clerk can use its shared OAuth credentials. For production, create a Google OAuth web client in Google Cloud, then paste its Client ID and Client Secret into the Clerk Google connection.

FastAPI does not receive Google passwords or Google OAuth secrets. The browser signs in with Clerk, the frontend sends a Clerk JWT as `Authorization: Bearer <token>`, and the API verifies that JWT using `apps/api/.env`:

```env
CLERK_ISSUER=https://your-clerk-frontend-api.clerk.accounts.dev
CLERK_AUTHORIZED_PARTIES=http://localhost:3000,http://127.0.0.1:3000
```

Protected frontend routes currently include organizer tools such as `/organizer/events/new` and `/organizer/clubs/new`. Public browsing stays open, and clicking Register while signed out sends the user to Clerk sign-in before returning to complete the registration.

## Seed Data

After the schema exists and `apps/api/.env` is configured:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m app.scripts.seed_dev
```

The seed command is idempotent and intended for local development only.

## Testing

Backend quality checks:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe -m pytest
```

Frontend checks:

```powershell
cd apps/web
pnpm lint
pnpm type-check
pnpm build
```

## Main API Surfaces

- `GET /health`
- `GET /api/v1/health/db`
- `GET /api/v1/meta/categories`
- `GET /api/v1/meta/tags`
- `GET /api/v1/clubs`
- `GET /api/v1/clubs/{slug}`
- `POST /api/v1/clubs`
- `POST /api/v1/clubs/{club_id}/join`
- `GET /api/v1/events`
- `GET /api/v1/events/{event_id}`
- `POST /api/v1/events/{event_id}/register`
- `GET /api/v1/me/profile`
- `GET /api/v1/me/notifications`
- `GET /api/v1/search`
- `POST /api/v1/recommendations/events`

See [docs/api.md](docs/api.md) for endpoint notes.

## Security Notes

- Do not commit `.env` files or secrets.
- Clerk verifies Google OAuth; FastAPI verifies Clerk JWTs.
- Protected routes use `Authorization: Bearer <clerk_jwt>`.
- Development can use `X-Communiti-User-Email` only when `ENVIRONMENT=development`.
- CORS origins must be explicit in production.

See [docs/security.md](docs/security.md) and [docs/cors-debugging.md](docs/cors-debugging.md).

## Deployment Notes

The current MVP target is Vercel for the web app, a hosted FastAPI service for `apps/api`, and managed PostgreSQL.

Build the API image from `apps/api`:

```powershell
cd apps/api
docker build -t communiti-api .
```

Run database migrations with Alembic:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

See [docs/deployment.md](docs/deployment.md) for the production checklist.
