# Talaqi engineering contract

Read the approved product documents and relevant ADRs before changing the repository. Work on one bounded task and do not silently change product behavior, architecture, authentication, public contracts, migration history, or deferred scope.

## Architecture and ownership

- The monorepo boundaries are `apps/web`, `apps/api`, `apps/worker`, `packages/api-client`, `packages/ui`, `packages/translations`, `infrastructure`, `tests/e2e`, and `tests/security`.
- API modules are identity, profiles, regions, clubs, events, registrations, communications, moderation, audit, settings, media, and outbox. Each module owns its router, schemas, service, repository, models, policies, events, and tests.
- Routers call only their own module service. Services may call another module's public service interface but never another module's repository.
- PostgreSQL is the source of truth. External email, storage, monitoring, and later integrations remain behind adapters.
- Do not introduce microservices, Kubernetes, Kafka, Elasticsearch, or Redis without an approved ADR. PostgreSQL outbox/leases are the beta reliability boundary.

## API and naming

- Use REST/OpenAPI under `/api/v1`, `snake_case` JSON, RFC 3339 UTC timestamps, opaque UUIDv7 identifiers, and retained event IANA zones.
- Preserve the exact error, cursor, idempotency, and revision contracts in [README.md](README.md).
- Use domain terms and enums from the master plan. Avoid generic cross-module `utils` and `services` directories.
- All member-facing copy uses translation keys with parity for `en`, `tr`, `fr`, and `ar`; layouts and tests must be Arabic RTL-safe.

## Security stop conditions

Stop and ask before changing an approved business rule, module boundary, public API contract outside task scope, authentication strategy, payment boundary, or destructive migration. Also stop when unrelated user changes conflict with the task.

Every mutation must be authenticated, CSRF-protected, object-authorized, audited where sensitive, and idempotent where retryable. Add negative object-authorization tests for every organizer/admin mutation. Never expose credentials, tokens, exact private-link values, unnecessary attendee data, or private venue data. Production must fail closed for unsafe secrets, insecure cookie/origin/host/public-URL settings, unavailable migrations, or admin accounts without MFA.

Exact venue address, coordinates, and directions are restricted to event managers and members whose registration is `confirmed` or unexpired `cash_pending`, unless a manager explicitly makes the venue public. Service workers may cache only static/public data, never sessions, profiles, invitation tokens, attendee data, or notifications.

## Database and migrations

- One migration-chain owner at a time. Never edit an already-merged Alembic migration; add a reviewed migration.
- Use PostgreSQL, not SQLite, for migration, constraint, repository, and concurrency verification.
- Put invariants in database constraints and use transactions/row locks for capacity-sensitive state.
- Confirmed plus seat-holding cash-pending registrations never exceed capacity. One active registration exists per member/event; waitlists are deterministic FIFO.
- Every registration transition stores actor, reason, previous/new state, and UTC timestamp. Sensitive audit and registration history is immutable.

## Review and testing

- One issue and short-lived branch per task; one focused commit. A different reviewer checks architecture/spec compliance before code quality where possible.
- Shared contracts, migrations, authentication, and CI change only within explicit task scope. Security-sensitive work requires negative-test review.
- Follow red-green-refactor for implementation tasks. Test relevant unit, repository, API, contract, concurrency, component, E2E, accessibility, localization/RTL, and security behavior.
- Pin exact application dependencies in lockfiles and use supported, security-patched runtime/minor releases.
- Run the exact task gate plus relevant root commands listed in [README.md](README.md). Never claim completion without fresh output.

## Definition of Done

A task is done only when its approved acceptance criteria are met; scope and architecture are preserved; tests cover happy, negative/security, and concurrency paths as applicable; formatting, lint, types, tests, builds, migrations, OpenAPI, and E2E gates relevant to the change pass; user-facing text is localized and RTL-safe; no secrets or private data are exposed; documentation is current; the diff is self-reviewed; and the task lands as one focused commit.

The MVP is done only when all critical visitor, member, club owner/admin, independent organizer, and platform-admin journeys work in four locales; accessibility, installability, security and concurrency suites pass; migration/restore and worker recovery rehearsals succeed; policies/runbooks/monitoring are operational; and the controlled Istanbul/Algiers beta is supportable without direct database intervention.
