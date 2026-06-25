# COMMUNITI FastAPI Backend Plan

This is the working backend plan for COMMUNITI after the PostgreSQL database foundation. It incorporates the improvement review from `COMMUNITI_BACKEND_PLAN_IMPROVEMENT.md` and upgrades the original checklist into a production-oriented execution plan.

## 1. Goal

Build a FastAPI backend that connects the Next.js web app to PostgreSQL and exposes typed, secure API endpoints for users, clubs, events, registrations, saved events, notifications, search, recommendations, and later AI/LLM features.

The backend should be simple enough to build now, but structured enough to grow into a real SaaS.

## 2. Architecture Decision

Keep the main stack:

- Web: Next.js
- Backend: FastAPI
- Database: PostgreSQL
- AI search later: pgvector
- Auth: Clerk
- Social login: Google OAuth through Clerk
- Background jobs later: Redis + worker
- Mobile later: Expo React Native

FastAPI remains the best backend choice for this project because COMMUNITI will use Python-heavy AI, embeddings, async APIs, OpenAPI docs, and PostgreSQL/pgvector.

Do not switch to Django, NestJS, or Spring Boot unless the product direction changes significantly.

## 3. Target Request Flow

```text
Next.js / Expo client
  -> Clerk Bearer token
  -> FastAPI router
  -> dependency injection
  -> authentication
  -> authorization policy
  -> service layer
  -> repository layer
  -> PostgreSQL transaction
  -> background job / domain event
  -> typed response schema
```

Rules:

- Routers handle HTTP only.
- Schemas validate request/response data.
- Services contain business logic.
- Repositories contain database queries.
- Policies contain authorization decisions.
- Tests live near the module they verify.

## 4. Backend Folder Structure

```text
apps/
  api/
    app/
      main.py
      core/
        config.py
        security.py
        cors.py
        errors.py
        logging.py
        rate_limit.py
        observability.py
      db/
        session.py
        base.py
      api/
        v1/
          router.py
          health.py
          meta.py
      modules/
        users/
          router.py
          schemas.py
          service.py
          repository.py
          models.py
          policies.py
          tests/
        clubs/
          router.py
          schemas.py
          service.py
          repository.py
          models.py
          policies.py
          tests/
        events/
          router.py
          schemas.py
          service.py
          repository.py
          models.py
          policies.py
          tasks.py
          tests/
        registrations/
          router.py
          schemas.py
          service.py
          repository.py
          models.py
          policies.py
          tests/
        saved_events/
          router.py
          schemas.py
          service.py
          repository.py
          tests/
        notifications/
          router.py
          schemas.py
          service.py
          repository.py
          tasks.py
          tests/
        search/
          router.py
          schemas.py
          service.py
          repository.py
          tests/
        recommendations/
          router.py
          schemas.py
          service.py
          repository.py
          tests/
        ai/
          router.py
          schemas.py
          provider.py
          service.py
          safety.py
          cost.py
          prompts/
          evals/
          tests/
      scripts/
        seed_dev.py
      workers/
        celery_app.py
        jobs.py
      tests/
        conftest.py
        integration/
        security/
    requirements.txt
    requirements-dev.txt
    Dockerfile
    alembic.ini
    .env.example
```

## 5. Phase 0: Project Documentation Foundation

Before building much more backend code, add the docs that make the project manageable.

Deliverables:

- Expand `README.md`.
- Add `docs/architecture.md`.
- Add `docs/api.md`.
- Add `docs/security.md`.
- Add `docs/cors-debugging.md`.
- Add `docs/adr/0001-use-fastapi.md`.
- Add `docs/adr/0002-use-postgresql.md`.
- Add `docs/adr/0003-use-clerk-auth.md`.
- Add `docs/adr/0004-use-pgvector-later.md`.

README sections:

- Overview
- Tech stack
- Repository structure
- Prerequisites
- Database setup
- API setup
- Web setup
- Environment variables
- Migrations
- Seed data
- Testing
- Deployment
- CORS troubleshooting
- Security notes

## 6. Phase 1: Backend Foundation

Build the first FastAPI service shell.

Deliverables:

- `apps/api` scaffold.
- FastAPI app factory.
- Pydantic settings with `.env`.
- Async SQLAlchemy engine/session using `asyncpg`.
- CORS middleware.
- Error middleware.
- Request ID middleware.
- Structured logging.
- API prefix: `/api/v1`.
- OpenAPI tags.
- Health endpoint.
- DB readiness endpoint.
- Basic rate-limit foundation.

Initial endpoints:

```text
GET /health
GET /api/v1/health/db
GET /api/v1/meta/categories
GET /api/v1/meta/tags
```

Quality gate:

- `pytest`
- `ruff check`
- `ruff format --check`
- `mypy` or `pyright`
- GitHub Actions CI

## 7. Phase 2: Read APIs

Create safe read-only endpoints using existing PostgreSQL tables/views.

Endpoints:

```text
GET /api/v1/clubs
GET /api/v1/clubs/{slug}
GET /api/v1/events
GET /api/v1/events/{id}
GET /api/v1/events/{id}/capacity
```

Requirements:

- Pagination.
- Filtering.
- Sorting.
- Text search using `pg_trgm`.
- Response schemas.
- Do not return raw ORM models.
- Integration tests for list/detail/filter behavior.

Purpose:

- Replace static frontend data from `communiti-platform-design 2/lib/events.ts`.
- Prove the backend can return real PostgreSQL rows.

## 8. Phase 3: Seed Data and Local QA

Add a repeatable local seed command:

```bash
python -m app.scripts.seed_dev
```

Seed data:

- Test users.
- Clubs.
- Club memberships.
- Published events.
- Registrations.
- Saved events.
- Notifications.

Rules:

- Seed script must be idempotent.
- Seed script is local/dev only.
- Seed script must never run automatically in production.

## 9. Phase 4: Authentication and Authorization

Move auth before full write APIs.

Authentication endpoint:

```text
GET /api/v1/auth/me
```

Authentication requirements:

- Verify Clerk JWT on protected requests.
- Validate signature, expiration, issuer, audience/authorized party.
- Never trust `clerk_user_id` from request body.
- Map Clerk user to local `users` row.
- Create local user on first login if needed.
- Use `Authorization: Bearer <token>` for frontend/API calls.
Google login requirements:

- Configure Google login in Clerk, not directly in FastAPI.
- Frontend receives a Clerk session after Google OAuth.
- Frontend sends the Clerk JWT to FastAPI as `Authorization: Bearer <token>`.
- Store only identity metadata in PostgreSQL: `clerk_user_id`, email, display name, avatar URL, and roles.
- Do not store Google access tokens unless a future feature truly needs Google APIs.
- If Google API access is needed later, store provider tokens only through Clerk/provider-managed flows or an encrypted secrets strategy.

Google login flow:

```text
User clicks "Continue with Google" in Next.js
  -> Clerk handles Google OAuth
  -> Clerk creates/updates the user session
  -> Next.js reads Clerk JWT
  -> Next.js calls FastAPI with Bearer token
  -> FastAPI verifies token and upserts local users row
```

Authorization policy requirements:

- Users can update only their own profile.
- Organizers can manage only their own clubs/events.
- Club admins can manage only clubs they belong to with an admin role.
- Admin endpoints require platform admin role.
- Every route using `{id}` must check object-level permission.

Example policy:

```python
def can_manage_club(user, club) -> bool:
    return user.platform_role == "admin" or club.owner_id == user.id
```

Security tests:

- Missing token rejected.
- Invalid token rejected.
- Expired token rejected.
- User cannot update another user.
- Organizer cannot manage another organizer's event.

## 10. Phase 5: Write APIs

Build write endpoints after auth is stable.

Endpoints:

```text
POST   /api/v1/clubs
PATCH  /api/v1/clubs/{id}
POST   /api/v1/clubs/{id}/join
POST   /api/v1/clubs/{id}/leave
POST   /api/v1/events
PATCH  /api/v1/events/{id}
POST   /api/v1/events/{id}/register
POST   /api/v1/events/{id}/cancel-registration
POST   /api/v1/events/{id}/save
DELETE /api/v1/events/{id}/save
```

Requirements:

- Use transactions for write flows.
- Use database functions for registration/waitlist flows where useful.
- Add idempotency where duplicate clicks are likely.
- Add audit logs for organizer/admin changes.
- Return consistent error objects.
- Test capacity and waitlist race conditions.

Standard error shape:

```json
{
  "error": {
    "code": "EVENT_FULL",
    "message": "The event is full. You have been added to the waitlist.",
    "request_id": "req_..."
  }
}
```

## 11. Phase 6: Frontend Integration

Update the Next.js app to consume the backend.

Frontend requirements:

- Generate TypeScript API client from FastAPI OpenAPI.
- Add TanStack Query or SWR.
- Add loading states.
- Add empty states.
- Add error states.
- Add authenticated API calls.
- Replace static `EVENTS`.
- Connect event cards to detail pages.
- Connect join/register/save buttons.
- Add E2E tests.

Recommended package:

```text
packages/api-client/
```

## 12. Phase 7: AI-Ready Search Foundation

Do not scatter AI logic in route handlers.

Prepare search data before full AI features:

- `search_documents`
- `search_embeddings`
- `embedding_model`
- `embedding_version`
- source type: event, club, tag, category
- source ID
- visibility/permission fields
- background indexing job
- reindex command
- deletion handling

Current local database temporarily uses:

```sql
embedding double precision[]
```

After pgvector is installed, migrate to:

```sql
embedding vector(1536)
```

Vector index strategy:

- Start with exact search while data is tiny.
- Benchmark HNSW vs IVFFlat later.
- HNSW usually has better query recall/performance but uses more memory.
- IVFFlat is cheaper to build but needs tuning.

## 13. Phase 8: AI/LLM MVP

Initial AI features:

1. Semantic event search.
2. Personalized recommendations.
3. Organizer event-description assistant.
4. Community assistant for finding public/permitted events.
5. Admin moderation helper.

AI module:

```text
modules/ai/
  provider.py
  schemas.py
  service.py
  safety.py
  cost.py
  prompts/
  evals/
```

AI safety rules:

- Do not send unnecessary personal data to model providers.
- Redact logs.
- Add user/team rate limits.
- Add cost limits.
- Use structured outputs.
- Add evals before prompt/model changes.
- Treat retrieved content as untrusted.
- Defend against prompt injection.
- Do not expose hidden prompts.
- Filter RAG retrieval by permissions before giving context to an LLM.
- AI must not perform destructive writes without human confirmation.

## 14. Phase 9: Mobile Expansion

After web and API work:

- Add `apps/mobile` with Expo.
- Reuse Clerk auth.
- Reuse generated API client.
- Add push notification device registration.

Mobile-oriented endpoints:

```text
GET    /api/v1/me/feed
GET    /api/v1/me/notifications
POST   /api/v1/devices
DELETE /api/v1/devices/{id}
```

## 15. Phase 10: Production Hardening

Before real users:

- HTTPS everywhere.
- Strict CORS allowlist.
- Trusted host middleware.
- Rate limiting.
- Request IDs.
- Structured logs.
- Sentry or equivalent error tracking.
- OpenTelemetry traces/metrics.
- Slow query logging.
- Dependency scanning.
- Secret rotation process.
- Backup and restore test.
- Migration rollback plan.
- Load test registration spikes.
- Incident checklist.

## 16. CORS Strategy

Allowed origins must be exact.

Local allowlist:

```text
http://localhost:3000
http://127.0.0.1:3000
```

Production allowlist:

```text
https://your-production-web-domain.com
```

Rules:

- Do not use `*` with credentials.
- Allow `Authorization`, `Content-Type`, and `X-Request-ID`.
- Confirm `OPTIONS` preflight works.
- Add CORS middleware before route handlers.
- Do not mix `localhost` and `127.0.0.1` randomly.

## 17. Testing Strategy

Backend test groups:

```text
tests/
  unit/
  integration/
  security/
  ai/
  e2e/
```

Minimum backend tests:

- Health endpoint.
- DB readiness endpoint.
- Categories/tags endpoint.
- Event listing.
- Event detail.
- Pagination/filtering.
- Registration success.
- Duplicate registration.
- Full event -> waitlist.
- Cancellation -> waitlist promotion.
- Missing/invalid/expired token.
- Organizer permission checks.
- CORS preflight.
- AI output schema validation later.

Quality tools:

- pytest
- pytest-asyncio or AnyIO
- httpx.AsyncClient
- Ruff
- mypy or pyright
- coverage threshold
- pre-commit hooks
- dependency vulnerability scan

## 18. Observability

Add from the beginning:

- Request ID.
- Structured JSON logs.
- Error tracking.
- Traces.
- Metrics.
- Database connection pool metrics.
- AI token/cost metrics later.

Log example:

```json
{
  "timestamp": "...",
  "level": "INFO",
  "request_id": "req_123",
  "method": "POST",
  "path": "/api/v1/events/123/register",
  "status_code": 200,
  "duration_ms": 42,
  "user_id": "user_123"
}
```

Never log:

- Raw JWTs.
- Passwords.
- Secrets.
- Full private prompts.
- Sensitive personal data unless redacted.

## 19. CI/CD Plan

GitHub Actions should run on pull requests and pushes to `main`.

Required checks:

- Install dependencies.
- Ruff lint.
- Ruff format check.
- Type check.
- Pytest.
- API Docker build.
- Frontend lint/type/build later.

Example API checks:

```text
ruff check apps/api
ruff format --check apps/api
mypy apps/api
pytest apps/api/tests
```

Branch rules:

- `main` must stay deployable.
- Feature branches for new work.
- Pull requests before merge.
- CI must pass before deployment.

## 20. Deployment Strategy

MVP:

- Web: Vercel.
- API: Railway.
- Database: managed PostgreSQL.
- Redis: managed Redis later.
- Secrets: platform environment variables.

Later:

- API: AWS ECS/Fargate.
- Database: AWS RDS PostgreSQL.
- Cache: ElastiCache Redis.
- Logs/metrics/traces centralized.

Deployment checklist:

- Dockerfile exists.
- `/health` works.
- DB readiness works.
- Migrations run safely.
- Secrets come from environment.
- CORS production domain configured.
- Clerk production keys configured.
- HTTPS only.
- Backups enabled.
- Rollback documented.

## 21. Definition of Done

A backend feature is done only when:

- Endpoint implemented.
- Request/response schemas added.
- Auth/authorization added where needed.
- Service and repository boundaries respected.
- Tests added.
- OpenAPI docs are correct.
- Errors follow standard shape.
- Logs include request ID.
- Database migration added if needed.
- README/docs updated.
- CI passes.

## 22. Immediate Next Actions

Do these next, in order:

1. Expand `README.md`.
2. Add ADR docs for FastAPI, PostgreSQL, Clerk, and pgvector.
3. Scaffold `apps/api`.
4. Add FastAPI app factory and `/health`.
5. Add database connection to `communiti_dev`.
6. Add meta endpoints for categories/tags.
7. Add read endpoints for events/clubs.
8. Add seed data script.
9. Add auth before write APIs.
10. Add write APIs for registration and club joins.
11. Connect Next.js to the API.

## 23. Immediate Next Milestone

The next concrete milestone is:

```text
FastAPI running locally on http://localhost:8000
Connected to PostgreSQL communiti_dev
GET /api/v1/meta/categories returns database rows
GET /api/v1/events returns real PostgreSQL rows
```

