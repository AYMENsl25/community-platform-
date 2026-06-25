# COMMUNITI FastAPI Backend Plan

This document is the working plan for building the COMMUNITI backend after the PostgreSQL database foundation.

## Goal

Build a FastAPI backend that connects the Next.js web app to PostgreSQL and exposes typed, secure API endpoints for users, clubs, events, registrations, saved events, notifications, and later AI-powered search/recommendations.

## Target Architecture

```text
Next.js Web App
  -> FastAPI Backend
  -> PostgreSQL Database
  -> Redis / background workers later
```

## Backend Folder Structure

```text
apps/api/
  app/
    main.py
    config.py
    database.py
    dependencies.py
    middleware/
      cors.py
      errors.py
      logging.py
    modules/
      health/
      users/
      clubs/
      events/
      registrations/
      saved_events/
      notifications/
      search/
      recommendations/
    tests/
  requirements.txt
  requirements-dev.txt
  alembic.ini
  alembic/
```

## Phase 1: Backend Foundation

- Create `apps/api`.
- Add FastAPI app factory.
- Add Pydantic settings.
- Add async SQLAlchemy database connection.
- Add CORS for the Next.js frontend.
- Add health endpoint.
- Add error handling middleware.
- Add local `.env.example`.

First endpoints:

```text
GET /health
GET /api/v1/meta/categories
GET /api/v1/meta/tags
```

## Phase 2: Read APIs

Create read-only endpoints that use existing PostgreSQL tables/views.

```text
GET /api/v1/clubs
GET /api/v1/clubs/{slug}
GET /api/v1/events
GET /api/v1/events/{id}
GET /api/v1/events/{id}/capacity
```

Purpose:

- Replace static frontend data from `lib/events.ts`.
- Prove the backend can return real database data.
- Keep the first integration simple and testable.

## Phase 3: Seed Data

Add a seed SQL or Python seed script for:

- One test user.
- Several clubs.
- Several published events.
- Club memberships.
- Event registrations.

Purpose:

- Give the frontend real content.
- Enable manual QA and API testing.

## Phase 4: Write APIs

Use database functions where appropriate.

```text
POST /api/v1/clubs
PATCH /api/v1/clubs/{id}
POST /api/v1/clubs/{id}/join
POST /api/v1/clubs/{id}/leave
POST /api/v1/events
PATCH /api/v1/events/{id}
POST /api/v1/events/{id}/register
POST /api/v1/events/{id}/cancel-registration
POST /api/v1/events/{id}/save
DELETE /api/v1/events/{id}/save
```

Purpose:

- Turn the prototype into a working SaaS.
- Keep capacity and waitlist logic consistent with database functions.

## Phase 5: Authentication

Add Clerk authentication.

- Store `clerk_user_id` in `users`.
- Verify JWT in FastAPI middleware/dependency.
- Add `GET /api/v1/auth/me`.
- Protect write endpoints.

Purpose:

- Users can safely register for events.
- Organizers can manage only their own clubs/events.

## Phase 6: Frontend Integration

Update Next.js:

- Replace static `EVENTS` with API calls.
- Add API client.
- Add loading/error states.
- Connect event cards to real event detail pages.
- Connect join/register buttons to backend.

Purpose:

- The web app becomes data-driven instead of static.

## Phase 7: Testing

Backend tests:

- Health endpoint.
- Categories/tags endpoint.
- Event listing endpoint.
- Event registration function behavior.
- Waitlist promotion behavior.
- Permission checks after auth is added.

Frontend tests:

- Explore page loads real API data.
- Filters work.
- Event detail route works.
- Join/register flow works.

## Phase 8: AI Search Later

After pgvector is installed:

- Change `search_embeddings.embedding` from `double precision[]` to `vector(1536)`.
- Add IVFFlat vector index.
- Add embedding generation background job.
- Add semantic search endpoint.
- Add recommendations endpoint.

Endpoints:

```text
GET /api/v1/search?q=
GET /api/v1/recommendations/me
```

## Deployment Path

MVP:

- Web: Vercel.
- API: Railway.
- Database: Railway PostgreSQL or local-to-cloud migration.
- Secrets: Railway environment variables.

Later production:

- API: AWS ECS/Fargate.
- Database: AWS RDS PostgreSQL.
- Cache: Redis/ElastiCache.

## Immediate Next Milestone

Backend running locally:

```text
FastAPI on http://localhost:8000
Connected to communiti_dev
GET /api/v1/events returns real PostgreSQL rows
```

