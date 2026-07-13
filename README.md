# Talaqi

Talaqi is a mobile-first community and events PWA for an adult-only closed beta in Istanbul and Algiers. Verified members with a complete profile and accepted organizer/community rules may create a club or an independent event. MVP registration is free or organizer-confirmed cash only.

The repository will contain a Next.js App Router PWA, FastAPI modular monolith, PostgreSQL-backed worker/outbox, generated TypeScript client, shared UI, and four-locale translation dictionaries. PostgreSQL 18 is authoritative for transactions, capacity, idempotency, audit history, and the transactional outbox.

## Authoritative context

- [Approved closed-beta design](docs/product/closed-beta-design.md)
- [Master implementation plan](docs/product/master-implementation-plan.md)
- [MVP acceptance and traceability](docs/product/mvp-acceptance.md)
- [Architecture decisions](docs/decisions/0001-modular-monolith.md)
- [PostgreSQL baseline](database/README.md)

If documents conflict, the approved design and master implementation plan govern. Changes to locked behavior require product-owner approval and an ADR.

## Command contract

Later foundation tasks must provide these root commands. Until their scripts exist, these names and expected outcomes are fixed:

```powershell
corepack pnpm install --frozen-lockfile
uv sync --frozen
docker compose up -d --wait
uv run alembic upgrade head
corepack pnpm format:check
corepack pnpm lint
corepack pnpm typecheck
uv run ruff format --check .
uv run ruff check .
uv run pyright
corepack pnpm test
uv run pytest -q
corepack pnpm openapi:check
corepack pnpm build
corepack pnpm e2e
docker compose down
```

Every verification command must exit 0; migrations must report one head, OpenAPI must have no diff, and critical Playwright journeys must pass. PostgreSQL baseline setup and its separate schema contract are documented in [database/README.md](database/README.md).

## Local services and API health

Copy `.env.example` to the ignored `.env`, replace every `REPLACE_WITH_...` local placeholder, then start the loopback-only PostgreSQL, MinIO, and Mailpit services. Mailpit has no authentication and is strictly for local email inspection.

```powershell
Copy-Item .env.example .env
docker compose config
docker compose up -d --wait
uv run uvicorn talaqi.main:app --app-dir apps/api/src --reload
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
docker compose down
```

Liveness is process-only. Readiness validates configuration and performs a bounded PostgreSQL
`SELECT 1`; object-storage and SMTP network probes are introduced with their later adapters. App
construction remains connection-free. Production and staging configuration must use HTTPS, secure
cookies, explicit non-local origins/hosts, a non-placeholder session secret of at least 64
characters, and enforced admin MFA.

## PostgreSQL migrations and tests

PostgreSQL 18 is the only supported persistence test backend; there is no SQLite fallback. The
compose service stays on loopback port 5432. A separately installed native PostgreSQL may use another
explicit port, such as 5433, through the ignored `.env.test.local` file. `TEST_DATABASE_URL` must use
the `postgresql+asyncpg` driver, a loopback host, an explicit port, and a database whose name ends
exactly in `_test`; destructive tooling fails closed for every other target.

Load the ignored setting into the process environment without printing it, then run migrations and
database tests:

```powershell
uv run alembic upgrade head
uv run pytest apps/api/tests/db -q
uv run alembic downgrade base
uv run alembic upgrade head
uv run alembic heads
```

The closed-beta baseline migration is immutable. Every later schema change requires a new Alembic
revision. See [database/README.md](database/README.md) for the schema-contract verification and safe
stamp workflow for a database that was initialized manually.

## Locked public contracts

- REST base path: `/api/v1`; JSON names use `snake_case`; timestamps are RFC 3339 UTC strings.
- Error: `{"error":{"code":"stable_code","message_key":"errors.key","field_errors":[],"request_id":"uuid"}}`.
- Cursor page: `{"items":[],"next_cursor":"opaque-or-null"}`; default limit 20, maximum 100.
- Retryable mutations require `Idempotency-Key`. A replay returns the stored status/body; reuse with another request hash returns `409 idempotency_conflict`.
- Editable organizer resources use integer `revision`; stale updates return `409 stale_revision`.
- Identifiers are opaque UUIDv7 values. Sequential identifiers are never exposed.
- Instants are stored in UTC and events retain their IANA time-zone identifier.

## MVP boundary

The MVP excludes online payments and refunds, native apps, feeds/chat/comments/reactions, QR check-in, recurring instances, revenue analytics, and ML recommendations. No checkout routes, provider code, webhooks, payment tables, refund flows, disputes, or provider selection belong in the MVP.
