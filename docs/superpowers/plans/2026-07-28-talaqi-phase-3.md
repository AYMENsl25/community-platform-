# Talaqi Phase 3 Implementation Plan

> Implement one master-plan task at a time with red-green-refactor. Do not begin the next task until the current task's focused commit is pushed to and verified on `origin/main`.

**Goal:** Deliver secure media, club and independent event publishing, private-link and exact-venue privacy, the organizer event workspace, and complete public event/club experiences.

**Architecture:** Add bounded `media` and `events` vertical modules to the existing stateless FastAPI modular monolith. PostgreSQL remains authoritative. Storage is accessed only through local-development and S3-compatible adapters. Next.js consumes regenerated OpenAPI types and server-returned capabilities. Public and audience-specific projections remain separate so private links and exact venues cannot enter public caches.

**Baseline:** `7c13a1aa088a4761b59eaf372edf4f1c978968a0`

**Design:** [Phase 3 design](../specs/2026-07-28-talaqi-phase-3-design.md)

## Global invariants

- Preserve all merged migrations; add new revisions from `0007_moderation_priority`.
- Use PostgreSQL, never SQLite, for migration and repository verification.
- Each API mutation is authenticated, CSRF-protected, object-authorized, and idempotent where retryable.
- Storage keys and actor identity are server-owned. Never place filenames, raw private links, secrets, or caller-provided actor IDs into trusted paths or authorization decisions.
- Exact venue data is visible only to managers, confirmed attendees, unexpired cash-pending attendees, or everyone when a manager explicitly makes it public.
- Render organizer controls only from API-returned capabilities.
- Keep English, Turkish, French, and Arabic translation parity and Arabic RTL safety.
- Do not add registration transitions, waitlists, communications, payments, recurring events, chat, QR check-in, or ML recommendations.
- Run specification/security review before code-quality review for every task.
- Stage only the current task's paths and create exactly one feature commit with the master-plan subject.

## Task 3.1: Media asset pipeline

**Produces:** signed-upload create/complete endpoints, verified canonical image assets, local and S3-compatible storage adapters, cleanup, and the `MediaService` public interface.

### Step 1: Add failing media domain and verifier tests

Create:

- `apps/api/tests/media/test_models.py`
- `apps/api/tests/media/test_verifier.py`
- `apps/api/tests/media/fixtures.py`

Cover safe filename normalization, allowed declared types, byte bounds, owner-scoped storage-key construction, signature/MIME agreement, one-frame enforcement, dimensions/pixel ceiling, EXIF orientation, metadata stripping, canonical WebP, SHA-256, malformed input, truncation, polyglot rejection, and stable safe error codes.

Run:

```text
python -m uv run pytest -q apps/api/tests/media/test_models.py apps/api/tests/media/test_verifier.py
```

Expected RED: media module imports are absent.

### Step 2: Pin the image dependency and implement pure media domain behavior

Modify:

- `apps/api/pyproject.toml`
- `uv.lock`

Create:

- `apps/api/src/talaqi/media/__init__.py`
- `apps/api/src/talaqi/media/models.py`
- `apps/api/src/talaqi/media/verifier.py`

Pin `pillow==12.3.0`. Implement immutable domain values, safe filename and storage-key validation, bounded decoder configuration, format/signature agreement, single-frame decoding, EXIF orientation, metadata-free deterministic WebP encoding, and canonical digest/dimension output. Convert library exceptions to stable internal media-validation failures without retaining exception text.

Run the Step 1 tests. Expected GREEN.

### Step 3: Add failing storage-adapter contract tests

Create:

- `apps/api/tests/media/test_local_storage.py`
- `apps/api/tests/media/test_s3_storage.py`
- `apps/api/tests/media/test_storage_contract.py`

Cover method/key/expiry/content-length/content-type binding, local-root confinement, symlink/path traversal rejection, atomic writes, bounded reads, replacement, deletion, readiness, S3 path-style endpoint construction, SigV4 canonicalization, redacted failures, and no credential/capability logging.

Run:

```text
python -m uv run pytest -q apps/api/tests/media/test_local_storage.py apps/api/tests/media/test_s3_storage.py apps/api/tests/media/test_storage_contract.py
```

Expected RED: adapter types are absent.

### Step 4: Implement local and S3-compatible adapters

Create:

- `apps/api/src/talaqi/media/storage.py`
- `apps/api/src/talaqi/media/local_storage.py`
- `apps/api/src/talaqi/media/s3_storage.py`
- `apps/api/src/talaqi/media/runtime.py`

Modify:

- `apps/api/src/talaqi/config.py`
- `.env.example`
- `apps/api/src/talaqi/main.py`
- focused configuration/readiness tests

Add frozen configuration for storage backend, local root, upload-grant lifetime, and image pixel ceiling. Reject local storage in staging/production. Keep app construction connection-free. Install a lazy storage runtime and bounded readiness probe. Use existing `httpx` plus a private SigV4 signer; do not expose storage credentials.

Run the Step 3 tests and focused settings/readiness tests. Expected GREEN.

### Step 5: Add failing repository and service tests

Create:

- `apps/api/tests/media/conftest.py`
- `apps/api/tests/media/test_repository.py`
- `apps/api/tests/media/test_service.py`

Cover pending creation, UUIDv7 owner-scoped keys, foreign-owner indistinguishability, idempotent completion, verified shape, canonical replacement-before-verification, transient storage retry, quarantine, attachability, bounded cleanup, concurrent completion, and cleanup/completion races.

Run:

```text
python -m uv run pytest -q apps/api/tests/media/test_repository.py apps/api/tests/media/test_service.py
```

Expected RED: repository and service are absent.

### Step 6: Implement repository, service, and cleanup boundary

Create:

- `apps/api/src/talaqi/media/repository.py`
- `apps/api/src/talaqi/media/service.py`

Add a migration only if a required lifecycle invariant cannot be represented by the baseline `media_assets` schema. Do not modify `0001` or the bootstrap SQL. Implement row-locking completion, safe status transitions, public `require_verified_owned`, and bounded abandoned-upload cleanup. Record only safe media audit facts.

Run Step 5 tests. Expected GREEN.

### Step 7: Add failing API and security tests

Create:

- `apps/api/tests/media/test_routes.py`
- `apps/api/tests/media/test_security.py`
- `tests/security/media_uploads/` fixtures where static malicious samples are required

Cover create, local signed PUT, complete, authentication, verification blockers, CSRF, idempotency replay/conflict, content-length mismatch, oversize streaming, foreign asset denial, capabilities absent from logs/errors/audits, cache headers, malformed requests, and all malicious/polyglot/path-traversal cases.

Expected routes:

- `POST /api/v1/media/uploads`
- adapter-returned signed `PUT` target
- `POST /api/v1/media/uploads/{asset_id}/complete`

Run:

```text
python -m uv run pytest -q apps/api/tests/media tests/security/media_uploads
```

Expected RED: routes are absent.

### Step 8: Implement routes and application wiring

Create:

- `apps/api/src/talaqi/media/schemas.py`
- `apps/api/src/talaqi/media/routes.py`

Modify:

- `apps/api/src/talaqi/main.py`
- `apps/api/src/talaqi/platform/openapi.py` only if required by the established operation-ID contract

Use existing authentication, CSRF, request-ID, idempotency, error, and transaction boundaries. Return `private, no-store` and `Vary: Cookie` for authenticated create/complete responses. Never echo storage internals outside the explicit short-lived upload grant.

Run Step 7 tests. Expected GREEN.

### Step 9: Generate contracts and prove integration

Modify generated artifacts only through existing generation commands:

- `openapi/talaqi-v1.json`
- `packages/api-client/src/schema.generated.ts`

Run:

```text
corepack pnpm openapi:generate
corepack pnpm openapi:check
corepack pnpm --filter @talaqi/api-client test
python -m uv run pytest -q apps/api/tests/media
```

If a migration was added, also run upgrade, downgrade, upgrade, `alembic heads`, database schema contract, and focused repository tests against PostgreSQL 18.

### Step 10: Task 3.1 complete gate

Run:

```text
python -m uv run pytest -q
python -m uv run ruff format --check .
python -m uv run ruff check .
python -m uv run pyright
corepack pnpm format:check
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
corepack pnpm openapi:check
python -m uv run pre-commit run --all-files
corepack pnpm audit --prod --audit-level high
```

Review the complete Task 3.1 diff for specification/security compliance, then code quality. Fix critical and important findings and rerun affected gates.

Commit exactly:

```text
feat: add secure media pipeline
```

Push fast-forward to `origin/main`, fetch, and verify local and remote SHA equality before Task 3.2.

## Task 3.2: Event domain and publishing

**Produces:** create/get-managed/update/cancel/complete/delete-draft/duplicate event endpoints.

- Add failing domain tests for ownership shape, schedules, IANA zones, regional methods/deadlines, capacity, coordinate pairing, venue policy, media, lifecycle, and revisions.
- Implement the bounded events module and published interfaces for club access, eligibility, regions, media, and audit.
- Add PostgreSQL repository tests for independent ownership limits, club manager authorization, row locks, revision conflicts, lifecycle constraints, duplicate-as-draft, and suspended principals/content.
- Add one forward migration only for invariants absent from the baseline; prove PostgreSQL upgrade/downgrade/re-upgrade and one head.
- Add authenticated, CSRF-protected, idempotent and revision-aware routes with complete negative object-authorization tests.
- Regenerate OpenAPI/client and run event domain/repository/API/security, migration, client, and full regression gates.
- Review, commit `feat: add club and independent events`, push to `origin/main`, and verify the remote SHA.

## Task 3.3: Private-link access and venue disclosure

**Produces:** tokenized private-event resolver and audience-aware event detail projection.

- Add failing token tests for 256-bit entropy, domain-separated hash-only persistence, one-time return, rotation, revocation, expiry, generic failure, and log/cache/referrer exclusion.
- Implement header/body token transport and a dedicated durable-deployment rate-limit boundary; do not put raw tokens in paths or query strings.
- Add the audience projection and PostgreSQL privacy-matrix tests for anonymous, ordinary member, club manager, independent owner, confirmed attendee, valid/expired cash-pending attendee, cancelled registration, and explicitly public venue.
- Prove private, draft, and suspended events remain absent from public discovery and metadata.
- Regenerate contracts and run token leakage, brute-force, privacy matrix, security, and full regression gates.
- Review, commit `feat: protect private events and venue details`, push to `origin/main`, and verify the remote SHA.

## Task 3.4: Shared event form and organizer operations UI

**Produces:** one event form and complete organizer event list/detail workflows.

- Add generated-client-backed server proxies that allowlist only required event/media routes and forward only approved auth/CSRF cookies and headers.
- Add failing component tests for server-returned ownership/capabilities, create/edit/duplicate form state, regional hints, date/time-zone controls, media states, visibility, capacity, methods, deadlines, venue preview, lifecycle actions, and revision conflict recovery.
- Implement organizer list/detail, canonical preview cards, loading/empty/error states, and the explicit Phase 4 attendee placeholder.
- Add translation keys with parity across `en`, `tr`, `fr`, and `ar`; use logical properties and stable focus behavior.
- Add Playwright club-owner/admin/member and independent-organizer journeys plus denial, mobile, keyboard, accessibility, long-text, reduced-motion, and Arabic RTL checks.
- Run component, E2E, accessibility, localization, lint, typecheck, and build gates.
- Review, commit `feat: add event organizer workspace`, push to `origin/main`, and verify the remote SHA.

## Task 3.5: Complete public club/event details

**Produces:** complete safe public club and event pages with discovery integration.

- Add canonical media, organizer trust/ownership, localized schedule, coarse venue/map, availability, regional registration/cancellation summary, save affordance, club events, and deterministic related events.
- Keep exact private venues and user-specific saved state out of public caches.
- Ensure private-link, draft, suspended, and otherwise ineligible content cannot appear through public fetches, metadata, sitemaps, canonical/alternate links, server caches, or service workers.
- Add SEO/privacy/component/Playwright tests in English, Turkish, French, and Arabic, including RTL, keyboard, accessibility, mobile, long text, and cache behavior.
- Run all API, client, web, build, security, accessibility, and E2E gates.
- Review, commit `feat: complete public event and club experiences`, push to `origin/main`, and verify the remote SHA.

## Phase 3 exit matrix

- An eligible club owner/admin can create and publish a valid club event.
- An eligible member can create and publish an independent event within the configured limit.
- Ineligible, suspended, cross-club, stale-revision, and invalid-policy mutations are denied and audited where sensitive.
- Uploaded images are verified canonical assets; malicious, oversized, foreign, pending, quarantined, and abandoned assets cannot be attached.
- Private-link values are hash-only at rest, absent from logs/caches/metadata, rotatable/revocable, and brute-force protected.
- Exact venue fields pass the complete approved audience matrix.
- Organizer and public journeys pass in four locales with Arabic RTL, keyboard, accessibility, mobile, and production-build coverage.
- PostgreSQL migrations have one head and pass round-trip validation.
- OpenAPI and generated TypeScript client are synchronized.
- All applicable root quality and security gates pass with a clean pushed worktree.
