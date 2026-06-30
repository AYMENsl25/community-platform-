# COMMUNITI Architecture

COMMUNITI uses a small modular monolith shape: a Next.js web app talks to a FastAPI API, and FastAPI owns database access to PostgreSQL.

## Request Flow

```text
Next.js client
  -> Clerk session token
  -> FastAPI router
  -> dependency injection
  -> authentication
  -> authorization policy
  -> service layer
  -> repository layer
  -> PostgreSQL
  -> typed response schema
```

## Backend Boundaries

- Routers handle HTTP concerns: paths, status codes, dependencies, and response models.
- Schemas define request and response contracts.
- Services contain use-case logic, authorization decisions, and transaction boundaries.
- Repositories contain SQL queries and database function calls.
- Policies keep object-level authorization rules explicit and testable.

## Current Backend Modules

- `auth` maps Clerk identity to local users.
- `me` exposes profile, preferences, clubs, events, registrations, saved events, and notifications for the current user.
- `organizer_requests` manages organizer approval workflows.
- `clubs` supports public reads, organizer management, join, and leave.
- `events` supports public reads, organizer management, registration, cancellation, save, and unsave.
- `search` searches public indexed content.
- `recommendations` tracks recommendation interactions.

## Data Strategy

PostgreSQL is the source of truth. The API uses raw SQL through SQLAlchemy async sessions today, which keeps the schema explicit and avoids leaking ORM objects into response contracts.

The search path starts with relational text search. AI-ready search should add `search_documents`, embedding metadata, permission-aware retrieval, background indexing, and pgvector once the local extension/deployment target is ready.

## Remaining Architecture Work

- Add Alembic migration management.
- Add a Dockerfile for API deployment.
- Add generated TypeScript API client package from OpenAPI.
- Add background worker structure before async jobs become necessary.
- Add production observability: metrics, traces, error reporting, and slow query logging.
