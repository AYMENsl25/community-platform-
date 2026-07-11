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
