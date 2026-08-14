# Talaqi MVP Through Closed Beta Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a secure, localized, mobile-first Talaqi PWA for a closed beta in Istanbul and Algiers, supporting verified-member club/event creation and free or organizer-confirmed cash registration.

**Architecture:** Build a modular monolith in one monorepo: Next.js PWA, FastAPI API, PostgreSQL-backed worker/outbox, generated TypeScript client, shared UI, and translation packages. PostgreSQL is the source of truth; all sensitive behavior is server-authorized and concurrency-safe.

**Tech Stack:** Node.js 24 LTS, pnpm workspaces, Next.js App Router, React, TypeScript, Tailwind CSS, TanStack Query, React Hook Form + Zod, Python 3.13, uv, FastAPI, Pydantic v2, SQLAlchemy async, Alembic, PostgreSQL 18, pytest, Vitest, Testing Library, Playwright, Ruff, Pyright, Docker Compose, OpenTelemetry, and S3-compatible storage.

## Global constraints

- MVP excludes online payments, refunds, native apps, chat/social feeds, QR check-in, recurring instances, and ML recommendations.
- Store instants in UTC and retain event IANA time-zone identifiers.
- Use UUIDv7 opaque identifiers; never expose sequential IDs.
- All member-facing copy uses translation keys for `en`, `tr`, `fr`, and `ar`; Arabic must be RTL-safe.
- Every mutation is server-authenticated, CSRF-protected, object-authorized, audited where sensitive, and idempotent where retryable.
- Backend routers call their own service only; services may call another module's public service interface but never its repository.
- One migration-chain owner at a time. Never edit an already-merged Alembic migration.
- Pin exact application dependencies in `pnpm-lock.yaml` and `uv.lock`; use only supported security-patched runtime/minor releases.
- Each task follows red-green-refactor, includes negative/security cases where relevant, runs its listed gate, and lands as one focused commit.

## Public contracts locked before feature work

### API conventions

- Base URL: `/api/v1`; JSON uses `snake_case`; timestamps are RFC 3339 UTC strings.
- Error envelope: `{"error":{"code":"stable_code","message_key":"errors.key","field_errors":[],"request_id":"uuid"}}`.
- Cursor page: `{"items":[],"next_cursor":"opaque-or-null"}` with a default limit of 20 and maximum of 100.
- Retryable mutations require an `Idempotency-Key` header; replay returns the stored status/body, while key reuse with a different request hash returns `409 idempotency_conflict`.
- Editable organizer resources carry integer `revision`; stale updates return `409 stale_revision`.

### Domain enums

- Club membership policy: `open | approval_required`; membership role: `owner | admin | member`.
- Event ownership: `club | independent`; visibility: `public | private_link`; lifecycle: `draft | published | cancelled | completed | suspended`.
- Registration method: `free | cash_organizer_confirmed`; state: `confirmed | cash_pending | waitlisted | cancelled | expired`.
- Moderation target: `user | club | event`; case state: `open | investigating | actioned | dismissed`; action: `suspend | unpublish | restore | restrict`.

### Repository map

- `apps/web`: routes, feature components, auth-aware layouts, PWA manifest/service worker, and browser tests.
- `apps/api`: FastAPI entry point and independently bounded modules for identity, profiles, regions, clubs, events, registrations, communications, moderation, audit, settings, media, and outbox.
- `apps/worker`: PostgreSQL job claiming, outbox delivery, schedules, and adapter orchestration.
- `packages/api-client`: generated TypeScript client; `packages/ui`: accessible primitives and Talaqi tokens; `packages/translations`: four complete dictionaries.
- `infrastructure`: local containers, deployment manifests, monitoring, and CI support; `tests/e2e` and `tests/security`: cross-app journeys.

---

## Phase 0 — Product and engineering foundation

### Task 0.1: Repository contract and architecture decisions

**Files:** Create root `AGENTS.md`, `README.md`, `docs/decisions/0001-modular-monolith.md`, `0002-cookie-auth.md`, `0003-postgres-outbox.md`, `0004-no-online-payments-in-mvp.md`, and `docs/product/mvp-acceptance.md`.

- [ ] Record commands, module boundaries, naming, security stop conditions, migration ownership, review rules, and Definition of Done.
- [ ] Copy all approved rules and deferred scope from the design; include a requirement-to-phase traceability table.
- [ ] Scan `AGENTS.md`, `README.md`, and `docs` for unfinished requirements and in-scope payment work; expect none.
- [ ] Commit `docs: establish Talaqi MVP engineering contract`.

### Task 0.2: Monorepo and deterministic toolchains

**Files:** Create `package.json`, `pnpm-workspace.yaml`, `turbo.json`, `.nvmrc`, `.python-version`, `pyproject.toml`, lockfiles, shared TypeScript/Ruff/Pyright/EditorConfig settings, and empty workspace packages.

- [ ] Add root scripts `format:check`, `lint`, `typecheck`, `test`, `build`, `openapi:check`, and `e2e`; scripts must delegate to workspaces without rewriting files.
- [ ] Scaffold Next.js with App Router/TypeScript/Tailwind and Python packages with `uv`; do not add a second server-state or form library.
- [ ] Run `corepack pnpm install --frozen-lockfile`, `uv sync --frozen`, `pnpm lint`, and `uv run ruff check .`; expect exit 0.
- [ ] Commit `build: scaffold deterministic Talaqi monorepo`.

### Task 0.3: Local services and configuration contract

**Files:** Create `compose.yaml`, `.env.example`, `apps/api/src/talaqi/config.py`, `apps/api/src/talaqi/main.py`, health routers, and configuration tests.

- [ ] Start PostgreSQL 18 and local S3/email test adapters; expose no production secret defaults.
- [ ] Implement validated environment profiles and `/health/live` plus dependency-aware `/health/ready` outside `/api/v1`.
- [ ] Add production fail-closed tests for weak secrets, insecure cookies, wildcard origins/hosts, non-HTTPS public URLs, and missing admin MFA enforcement.
- [ ] Run `docker compose config`, `uv run pytest apps/api/tests/config apps/api/tests/health -q`; expect exit 0.
- [ ] Commit `feat: add local services and fail-closed configuration`.

### Task 0.4: Database, migrations, shared persistence, and fixtures

**Files:** Create async database/session modules, Alembic configuration and initial migration, UUIDv7/time helpers, transaction test fixtures, and migration tests.

- [ ] Establish naming conventions, UTC timestamps, soft/suspension fields where specified, and revision columns for editable organizer resources.
- [ ] Test clean upgrade, downgrade, and upgrade again against PostgreSQL—not SQLite.
- [ ] Run `uv run alembic upgrade head`, `uv run pytest apps/api/tests/db -q`, `uv run alembic downgrade base`, then `uv run alembic upgrade head`; expect all exit 0.
- [ ] Commit `feat: establish PostgreSQL persistence and migrations`.

### Task 0.5: API envelope, pagination, idempotency, and generated client

**Files:** Create API error/pagination/idempotency primitives, request-ID middleware, OpenAPI generation script, `packages/api-client`, and contract tests.

- [ ] Implement the locked error and cursor contracts; persist idempotency key, actor, route, request hash, status, body, and expiry.
- [ ] Generate the TypeScript client from a deterministic checked-in OpenAPI document and fail CI on drift.
- [ ] Run `uv run pytest apps/api/tests/platform -q`, `pnpm openapi:check`, and `pnpm --filter @talaqi/api-client typecheck`; expect exit 0.
- [ ] Commit `feat: define stable API and client contracts`.

### Task 0.6: Talaqi design foundation and accessible shell

**Files:** Create Talaqi color/type/spacing tokens, logo assets derived from `LOGO.png`, accessible UI primitives, public/member/organizer/admin layouts, and component tests.

- [ ] Use the logo's deep green, warm off-white, and coral accent; provide optimized wordmark, icon, favicon, and monochrome variants without altering the mark.
- [ ] Implement skip link, semantic landmarks, visible focus, keyboard navigation, reduced motion, responsive navigation, and logical CSS properties for RTL.
- [ ] Run `pnpm --filter @talaqi/ui test`, `pnpm --filter @talaqi/web typecheck`, and `pnpm --filter @talaqi/web build`; expect exit 0.
- [ ] Commit `feat: add Talaqi accessible design foundation`.

### Task 0.7: CI skeleton and security baseline

**Files:** Create GitHub Actions workflows, pre-commit configuration, dependency/secret/static scans, security-header middleware, rate-limit abstraction, and CI documentation.

- [ ] Add changed-file-aware web/API/contract/migration/security jobs, cache-only optimizations, and protected-branch Playwright job.
- [ ] Implement CSP, HSTS in production, `nosniff`, frame denial, referrer/permissions policies, strict hosts/CORS, structured redacted logs, and development in-memory rate limiting behind an adapter.
- [ ] Run the complete root quality suite plus header/redaction tests; expect no high/critical findings.
- [ ] Commit `ci: enforce Talaqi quality and security gates`.

**Phase 0 exit:** A clean clone can install, start dependencies, migrate, build both applications, generate the client, and pass CI using documented commands.

## Phase 1 — Identity, regions, localization, and discovery

### Task 1.1: Regional catalog and policy service

**Produces:** `RegionPolicyService.get(country_code)` and public country/city/category endpoints.

- [ ] Add countries, cities, categories, currencies, locale defaults, time zones, registration methods, ownership limits, venue rules, and deadline bounds; seed Turkey/Istanbul and Algeria/Algiers with approved defaults.
- [ ] Add admin-safe validation so policy changes cannot invalidate active reservations or extend deadlines beyond event start.
- [ ] Test locale/currency/time-zone mapping, bounds, unknown/disabled regions, and deterministic seed replay.
- [ ] Gate: API unit/integration tests, Alembic round trip, OpenAPI/client drift check.
- [ ] Commit `feat: add configurable regional policies`.

### Task 1.2: Accounts and password authentication

**Produces:** `POST /auth/register`, `/auth/login`, `/auth/logout`; `AuthService.require_user()`.

- [ ] Model users, Argon2id credentials, terms/age attestation versions, login throttling, and non-enumerating authentication errors.
- [ ] Register with email, password, 18+ attestation, privacy/terms acceptance; keep unverified accounts unable to create or register.
- [ ] Test duplicate/case-normalized email, weak passwords, timing-safe failure behavior, lockout/rate-limit boundaries, and log redaction.
- [ ] Gate: identity tests plus security tests; commit `feat: add secure account authentication`.

### Task 1.3: Verification, reset, and rotating sessions

**Produces:** verification/reset endpoints, `POST /auth/refresh`, session-list/revoke endpoints, and email outbox events.

- [ ] Store only hashed single-use verification/reset tokens with expiry; rotate refresh sessions and detect replay by revoking the session family.
- [ ] Use HttpOnly Secure SameSite=Lax access/refresh cookies and synchronizer/double-submit CSRF protection for mutations.
- [ ] Test expired/used tokens, refresh replay, session revocation, CSRF missing/mismatch, cookie flags, and non-enumerating reset responses.
- [ ] Gate: auth integration/security suite; commit `feat: add verification reset and rotating sessions`.

### Task 1.4: Profiles, preferences, and creation eligibility

**Produces:** `GET/PATCH /me`, `GET /me/capabilities`, and `CreationEligibilityService`.

- [ ] Add unique username, display name, country/city, locale, IANA time zone, currency, notification preferences, and organizer/community-rules acceptance. Avatar upload is enabled after Task 3.1 provides verified media assets.
- [ ] Return capabilities and explicit blockers for create-club, create-independent-event, register-event, and admin access.
- [ ] Test normalization, locale/region compatibility, incomplete profiles, unverified email, ownership limits, and cross-user access denial.
- [ ] Gate: profile/policy tests and generated client check; commit `feat: add profiles and creation eligibility`.

### Task 1.5: Complete localization and RTL framework

**Produces:** locale middleware, shared formatters, and parity-checked `en/tr/fr/ar` dictionaries.

- [ ] Localize API error codes on the client; format dates, plural text, numbers, and currencies by selected locale; update `html lang` and `dir` immediately.
- [ ] Add dictionary key parity/literal-copy linting and pseudo-long-text tests; no visible string may live directly in a feature component.
- [ ] Gate: translation parity, component RTL tests, and screenshots for all four locales; commit `feat: establish complete localization framework`.

### Task 1.6: Public discovery read models and search API

**Produces:** `GET /events`, `/events/{id}`, `/clubs`, `/clubs/{slug}`, `/search`, and metadata endpoints.

- [ ] Add cursor filtering by region/city/category/date/price type/search and stable rule-based sorting; exclude drafts, suspended records, and private-link events.
- [ ] Return card-ready cover, localized date/price state, coarse venue, availability, organizer/club summary, and authenticated member registration/save state.
- [ ] Add authenticated idempotent `PUT /events/{event_id}/saved`, `DELETE /events/{event_id}/saved`, and cursor-paginated `GET /me/saved-events`; saved-event records never hold capacity.
- [ ] Test cursor stability, search normalization, privacy exclusions, suspended content, and query plans/indexes on representative fixtures.
- [ ] Gate: repository/API/contract tests; commit `feat: add public discovery APIs`.

### Task 1.7: Public web experience

- [ ] Build landing, explore list, filter drawer, club detail, event detail skeleton, locale/region chooser, empty/error/loading states, and transparent featured ranking.
- [ ] Use URL-backed filters, server-render public metadata, responsive images, keyboard-operable controls, and no private-response caching.
- [ ] Gate: component tests, axe checks, mobile/desktop/RTL Playwright discovery journey, typecheck, and production build.
- [ ] Commit `feat: deliver localized public discovery experience`.

**Phase 1 exit:** A verified adult can create a complete profile; visitors can discover safe public club/event fixtures in four locales; all auth and CSRF negative tests pass.

## Phase 2 — Clubs, scoped authorization, audit, and moderation foundation

### Task 2.1: Immutable audit and policy functions

**Produces:** append-only `AuditService.record`, `can_edit_club`, `can_manage_members`, `can_manage_event`, `can_confirm_cash`, and admin-policy functions.

- [x] Define actor, action, target, reason, safe before/after metadata, request ID, and timestamp; prevent application update/delete of audit rows.
- [x] Unit-test the complete role/action matrix and integration-test cross-club, cross-event, and suspended-actor denial.
- [x] Gate: audit/policy/authorization-negative suite; commit `feat: add immutable audit and scoped policies`.

### Task 2.2: Club draft, completion, and automatic publication

**Produces:** `POST /clubs`, `GET/PATCH /clubs/{id}`, and completion/publish behavior.

- [x] Enforce verified/profile/rules eligibility and club limit; create private draft, calculate missing required fields, and publish atomically when complete.
- [x] Store slug, name, description, category, country/city, membership policy, social links, logo/cover references, revision, and lifecycle state.
- [x] Test duplicate slug, incomplete draft privacy, automatic publication, stale revision, limit enforcement, suspension, and audit emission.
- [x] Gate: club repository/API/security tests and migration round trip; commit `feat: add automatic club publication`.

### Task 2.3: Club memberships and owner/admin roles

**Produces:** join/leave, join-request approve/reject, member listing, role change, ownership transfer, and close endpoints.

- [x] Implement immediate open membership and idempotent approval requests; only owner may change admin roles; protect sole-owner exit.
- [x] Restrict member personal data to managers; public club views expose aggregate counts only.
- [x] Test concurrent joins, duplicate approval, admin escalation attempts, cross-club access, ownership transfer, and closed/suspended clubs.
- [x] Gate: membership integration/concurrency/security suite; commit `feat: add protected club membership operations`.

### Task 2.4: Organizer club workspace

- [x] Build owned/managed-club navigation, draft-completion form, profile preview, member/request tables, role/ownership confirmations, and server-error mapping.
- [x] Render only API-returned capabilities while preserving backend denial tests; all destructive actions require explicit confirmation and reason where audited.
- [x] Gate: component tests, owner/admin/member Playwright journeys, RTL, keyboard, and build.
- [x] Commit `feat: add club organizer workspace`.

### Task 2.5: Moderation cases and platform-admin shell foundation

**Produces:** case list/detail, user/club/event search, suspend/unpublish/restore actions, and admin audit views.

- [x] Require admin role plus MFA for production actions; require action reason; record immutable audit; remove suspended content from discovery immediately.
- [x] Define launch report categories: safety, harassment, fraud, illegal content, privacy, spam, and other. Emergency/safety reports display an immediate local-emergency-services notice and enter highest priority.
- [x] Test non-admin and non-MFA denial, cross-target actions, required reasons, restoration, discovery removal, and audit integrity.
- [x] Gate: moderation/security/API/client tests and admin E2E; commit `feat: establish moderation and admin operations`.

**Phase 2 exit:** Verified members can publish clubs and manage scoped memberships; admins can safely suspend/restore content; every protected action has negative authorization coverage and audit evidence.

## Phase 3 — Events, media, visibility, and venue privacy

### Task 3.1: Media asset pipeline

**Produces:** signed-upload create/complete endpoints and `MediaService` adapter interface.

- [x] Enforce owner-scoped keys, MIME/signature agreement, image dimensions, 10 MB input limit, safe filenames, re-encoding, metadata stripping, and post-upload verification before attachment.
- [x] Provide local development and S3-compatible adapters; delete/quarantine failed assets and expire abandoned uploads.
- [x] Gate: malicious/polyglot/path traversal/oversize tests plus adapter contract tests; commit `feat: add secure media pipeline`.

### Task 3.2: Event domain and publishing

**Produces:** create/get/update/cancel/complete/delete-draft/duplicate event endpoints.

- [x] Support club/independent ownership, draft/published lifecycle, public/private-link visibility, future start/end, IANA zone, country/city, capacity, category, free/cash method, deadlines, media, and revision.
- [x] Enforce manager policy, event-country regional rules, paired coordinates, exact-venue policy, ownership limits, canonical cover media, and audit records.
- [x] Test invalid dates/zones/coordinates, unauthorized club use, limit/rule violations, stale revisions, cancellation, duplicate-as-draft, and suspended owners.
- [x] Gate: event domain/repository/API/security tests, migration round trip, client check; commit `feat: add club and independent events`.

### Task 3.3: Private-link access and venue disclosure

**Produces:** tokenized private-event resolver and audience-aware event detail projection.

- [x] Generate high-entropy tokens, store only token hashes, support rotation/revocation, exclude tokens from logs/referrers/analytics, and rate-limit access attempts.
- [x] Return city/district publicly and exact address/coordinates only to managers, confirmed attendees, or unexpired cash-pending attendees unless explicitly public.
- [x] Gate: token leakage/brute-force/privacy matrix tests; commit `feat: protect private events and venue details`.

### Task 3.4: Shared event form and organizer operations UI

- [x] Build one schema-driven form for create/edit/duplicate with ownership selector, regional policy hints, date/time-zone controls, visibility, media, capacity, method, deadlines, and venue disclosure preview.
- [x] Add organizer event list/detail, attendee placeholder, lifecycle actions, optimistic-revision conflict recovery, and canonical preview cards.
- [x] Gate: component tests, club/independent organizer Playwright journeys, mobile/RTL/accessibility, and build.
- [x] Commit `feat: add event organizer workspace`.

### Task 3.5: Complete public club/event details

- [x] Add canonical media, organizer trust/ownership, localized schedule, coarse venue/map, availability, rules/cancellation summary, save affordance, club events, and related rule-based events.
- [x] Ensure private/suspended/draft content cannot appear in metadata, sitemaps, caches, or public fetches.
- [x] Gate: SEO/privacy/component/Playwright tests in four locales; commit `feat: complete public event and club experiences`.

**Phase 3 exit:** Eligible members publish safe club or independent events, private links remain unindexed and secret, and exact venues obey the approved audience policy.

## Phase 4 — Registration, cash reservations, capacity, and waitlists

### Task 4.1: Registration model and transition service

**Produces:** typed transition commands and immutable registration-transition history.

- [x] Add unique active member/event constraint, state/method, seat-held flag, waitlist sequence, deadlines, idempotency record, and actor/reason history.
- [x] Centralize allowed transitions; reject arbitrary repository state updates and transitions after event cancellation/start.
- [x] Gate: exhaustive state-table/property tests and migration round trip; commit `feat: define registration state machine`.

### Task 4.2: Concurrency-safe registration

**Produces:** `POST /events/{event_id}/registrations`.

- [x] Lock the event capacity row, re-check eligibility/availability inside the transaction, create `confirmed` for free or `cash_pending` for cash when a seat exists, otherwise allocate deterministic FIFO waitlist sequence.
- [x] Return existing active registration for a safe identical retry; reject conflicting idempotency reuse; enqueue committed notifications via outbox.
- [x] Gate: 50-client last-seat contention, duplicate/retry, suspended/private eligibility, deadline, and capacity invariant tests; commit `feat: add atomic event registration`.

### Task 4.3: Cancellation and FIFO promotion

**Produces:** `DELETE /events/{event_id}/registrations/me` and `PromotionService.promote_next()`.

- [x] Enforce event cutoff, release the seat, and promote exactly one oldest eligible waitlisted member in the same transaction; skip cancelled/ineligible entries deterministically.
- [x] For free events promote to confirmed; for cash events promote to cash-pending with a newly bounded expiry; emit transition/audit/outbox records.
- [x] Gate: simultaneous cancellations/promotions, cutoff boundary, worker retry, and no-overcapacity tests; commit `feat: add cancellation and FIFO promotion`.

### Task 4.4: Organizer cash confirmation and attendee API

**Produces:** confirm-cash endpoint plus manager-only attendee cursor list/filter/export request.

- [x] Confirm only unexpired cash-pending records for a managed event; make identical retries safe and reject cross-event/cross-club access.
- [x] Limit attendee fields to operational necessities; filter by state/search and audit CSV export requests.
- [x] Gate: cash expiry race, duplicate confirmation, authorization/privacy, pagination, and export tests; commit `feat: add cash confirmation and attendee operations`.

### Task 4.5: Expiry worker and recovery

**Produces:** lease-based cash-expiry job with bounded retries and dead-letter visibility.

- [x] Claim due reservations using PostgreSQL `FOR UPDATE SKIP LOCKED`, transition to expired, release capacity, promote waitlist, and emit notifications in one recoverable transaction.
- [x] Test multiple workers, crash after claim, restart recovery, clock boundaries, and idempotent replay.
- [x] Gate: worker integration/concurrency tests; commit `feat: expire cash reservations reliably`.

### Task 4.6: Member registration and ticket experience

- [x] Add register/cancel/waitlist controls, free confirmation, cash instructions/countdown, ticket/reservation views, capacity states, venue disclosure, and actionable localized errors.
- [x] Revalidate server state after mutations; never infer confirmation from optimistic UI.
- [x] Gate: component tests and Playwright free, cash, full/waitlist, cancel/promote, and unauthorized journeys in mobile/RTL modes.
- [x] Commit `feat: deliver member registration experience`.

### Task 4.7: Organizer attendee experience

- [x] Build filterable/paginated attendee table, cash-confirm confirmation, waitlist/capacity summary, privacy-safe CSV generation status, and narrow responsive layout.
- [x] Gate: owner/admin/independent-owner positive paths, unrelated organizer negative path, keyboard/RTL, and build.
- [x] Commit `feat: deliver attendee and cash operations UI`.

**Phase 4 exit:** Last-seat and waitlist invariants hold under concurrency; workers recover after interruption; members and managers can complete all free/cash journeys without direct database intervention.

## Phase 5 — Communications, dashboards, PWA, and experience completion

### Task 5.1: Transactional outbox runtime

- [x] Implement atomic event writes, lease/claim, deduplication, bounded exponential retry with jitter, delivery status, dead-letter review, and retention cleanup.
- [x] Gate: competing workers, crash/restart, poison event, ordering-by-aggregate, and duplicate delivery contract tests.
- [x] Commit `feat: add reliable transactional outbox worker`.

### Task 5.2: In-app notifications and preferences

**Produces:** notification list/unread count/read endpoints and preference-aware delivery decisions.

- [x] Create notifications for security, membership, event, registration, cash, waitlist, cancellation, and moderation events; security-critical email cannot be disabled.
- [x] Test recipient isolation, preference handling, cursor pagination, unread consistency, and outbox replay.
- [x] Commit `feat: add in-app notifications and preferences` after API/client tests pass.

### Task 5.3: Transactional email adapters and templates

- [x] Provide console/test and production-provider interfaces; implement four-locale verification, reset, security, membership, registration, cash-expiry, promotion, cancellation, and event-change templates.
- [x] Keep exact private venue out of pre-confirmation emails; add daily quotas, provider IDs, retry classifications, and delivery logging without tokens/private bodies.
- [x] Gate: template parity/render snapshots, adapter contracts, privacy, retry, and quota tests; commit `feat: add localized transactional email`.

### Task 5.4: Club announcements and event updates

- [x] Add manager-authorized create/list endpoints, audience selection, revision-safe event updates, and delivery through outbox; notify only eligible recipients.
- [x] Build organizer composer/history and member notification views; do not add chat, comments, or replies.
- [x] Gate: authorization, audience privacy, dedupe, localized UI, and E2E tests; commit `feat: add announcements and event updates`.

### Task 5.5: Member and organizer dashboards

- [x] Member: upcoming events, confirmed/cash-pending/waitlisted actions, saved events, joined clubs, notifications, and profile blockers.
- [x] Organizer: owned/managed clubs, independent events, status/capacity/cash queues, membership requests, alerts, and quick actions using the approved three-column desktop/stacked-mobile pattern.
- [x] Gate: permission-specific component/E2E tests, empty/error/loading, RTL, accessibility, and build; commit `feat: complete member and organizer dashboards`.

### Task 5.6: Safe PWA installation and offline behavior

- [x] Add manifest, Talaqi icons, theme colors, installability, update prompt, offline shell, and cache rules limited to versioned static assets and safe public GET responses.
- [x] Explicitly bypass auth, `/me`, invitations, registrations, notifications, attendee, admin, and mutation requests; clear user-scoped browser state on logout.
- [x] Gate: Lighthouse installability, cache allow/deny tests, offline public-shell journey, and logout privacy test; commit `feat: make Talaqi a privacy-safe PWA`.

### Task 5.7: Four-locale accessibility and responsive completion

- [x] Reach dictionary parity for every screen/email/error; perform Arabic RTL, long French/Turkish copy, keyboard, focus, screen-reader, contrast, reduced-motion, and 320 px layout QA.
- [x] Gate: automated axe has zero serious/critical issues, visual baselines approved for critical routes, and all four-locale Playwright journeys pass.
- [x] Commit `fix: complete localization accessibility and responsive QA`.

**Phase 5 exit:** All critical journeys are installable, usable at mobile widths, accessible, and fully localized; communications are reliable and privacy-safe.

## Phase 6 — Operational hardening and closed beta

### Task 6.1: Complete reports and moderation operations

- [ ] Add authenticated report submission with evidence-safe metadata, priority, assignment, decisions, reasons, restoration, search, and response-time metrics.
- [ ] Set targets: immediate queueing for safety/emergency, human acknowledgement within 4 hours for high priority and 2 business days for standard reports; expose breach indicators to admins.
- [ ] Gate: abuse/rate-limit, privacy, state transition, authorization, audit, and admin E2E tests; commit `feat: complete beta moderation workflow`.

### Task 6.2: Regional settings and operational admin tools

- [x] Build MFA-protected policy editing, feature flags, ownership limits, search, audit review, outbox/dead-letter visibility, and safe retry actions.
- [x] Validate changes server-side and preview impact; prohibit destructive bulk edits or direct registration-state overrides.
- [x] Gate: non-MFA/role negative tests, policy-boundary tests, admin E2E, and client drift check; commit `feat: add safe platform operations console`.

### Task 6.3: Observability and alerting

- [ ] Add correlated JSON logs, traces, error reporting, request/error/latency, DB saturation, job age/failure, email failure, transition, expiry, promotion, moderation SLA, and business-funnel metrics.
- [ ] Alert on user-impacting API outage, migration failure, stalled queue, DB/storage capacity, critical email failure, and invariant violation; exclude high-cardinality personal data.
- [ ] Gate: telemetry contract/redaction tests and synthetic alert exercises; commit `ops: add beta observability and alerts`.

### Task 6.4: Security and privacy hardening review

- [ ] Run threat-model review across auth, sessions, CSRF, CORS/hosts, authorization, private links, venue/attendee privacy, uploads, rate limits, worker retries, logs, and admin MFA.
- [ ] Add dependency, secret, SAST, DAST, cookie/header, IDOR, unsafe-upload, and retention/anonymization verification; resolve all high/critical findings.
- [ ] Gate: full `tests/security`, scans, and documented exception process; commit `security: harden Talaqi for closed beta`.

### Task 6.5: Deployment pipeline and migration safety

- [ ] Add preview, staging, and manually approved production pipelines; run migrations once as a release job; use backward-compatible expand/migrate/contract changes and independent app rollback.
- [ ] Select providers only after current free/student commercial terms are checked; keep PostgreSQL, S3, email, and monitoring adapters portable.
- [ ] Gate: clean and previous-schema migration, staging smoke/E2E, rollback rehearsal, readiness failure, and secret isolation; commit `deploy: add guarded staging and production releases`.

### Task 6.6: Backup, recovery, retention, and account deletion

- [ ] Automate encrypted PostgreSQL/object-storage backups, restore validation, retention cleanup, 30-day account-deletion recovery, identity anonymization, and legally required audit preservation.
- [ ] Write and rehearse runbooks for restore, stuck jobs, failed migration, account recovery, data export/deletion, and compromised admin/session response.
- [ ] Gate: representative staging restore with checksums and sampled media, deletion/retention tests, and recorded recovery times; commit `ops: establish recovery and data lifecycle`.

### Task 6.7: Legal, policy, and support readiness

- [ ] Publish localized terms, privacy notice, 18+ age policy, community/organizer rules, cancellation/cash rules, moderation/reporting policy, and support contact.
- [ ] Version acceptances and require re-consent only for materially changed policies; legal review is a human launch gate.
- [ ] Gate: link/locale/version tests and product-owner/legal approval record; commit `docs: publish beta policies and support paths`.

### Task 6.8: Closed-beta release candidate

- [ ] Seed approved categories and Istanbul/Algiers data; create support/admin accounts with MFA; configure quotas and feature flags; import no production personal data.
- [ ] Run the release matrix: lint, format check, types, unit/integration/concurrency/security tests, migrations, OpenAPI drift, web build, all four-locale Playwright journeys, accessibility, PWA, backup/restore, and worker restart.
- [ ] Conduct product-owner acceptance for visitor, member, club owner/admin, independent organizer, and platform-admin journeys; record known low-risk issues and rollback triggers.
- [ ] Launch closed beta behind controlled invitations, monitor activation/event creation/registration/repeat participation/cancellation/cash expiry/promotion/report metrics, and hold a 48-hour go/no-go review.
- [ ] Commit `release: prepare Talaqi closed beta` and tag the approved release candidate.

**Phase 6 exit / MVP done:** No high/critical security issues; migrations and restore succeed; last-seat/waitlist and authorization-negative suites pass; four-locale critical E2E passes; monitoring/runbooks/legal pages are operational; the controlled Istanbul/Algiers beta is supportable.

## Global verification commands

Run from repository root before every phase exit:

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
```

Expected: every command exits 0; migration reports one head; OpenAPI has no diff; Playwright reports all critical journeys passed. Stop the stack with `docker compose down` after verification.

## Task ordering and agent safety

- Execute phases sequentially. Within a phase, parallelize only UI work against a frozen API contract or independent adapter/test work.
- Tasks 0.4, 0.5, 2.1, 4.1, and all migration-bearing tasks have a single owner and must merge before dependents start.
- Each task receives a dedicated task card containing exact acceptance tests, owned paths, excluded scope, and the master coding prompt from `TALAQI_TECHNICAL_PRODUCT_PLAN.md`.
- A different reviewer checks architecture/spec compliance first and code quality second. Security-sensitive tasks require explicit negative-test review.
- At each phase exit, regenerate the next phase's task cards from the merged repository so file paths and signatures reflect reality; the product behavior and public contracts in this plan may not be changed without product-owner approval and an ADR.

## Assumptions and future boundaries

- Adult-only beta, two launch cities, minimal profile identity, venue-disclosure policy, timing bounds, ownership limits, moderation categories/targets, and retention periods use the defaults in the approved design.
- Google OAuth is deferred unless credentials and exact redirect URLs are available; email/password is the required identity path.
- Redis is deferred; PostgreSQL outbox/leases and a provider/edge production rate limiter cover beta load. Add Redis by ADR if queue lag, distributed throttling, or lock contention breaches agreed service thresholds.
- Online payment code, tables, routes, UI, webhooks, refunds, disputes, and provider selection are excluded. Preserve only the registration-method enum boundary and external-adapter architecture.
- Hosting vendors are deliberately not locked because current free/student terms change; Task 6.5 selects them using portability, commercial-use, data-region, backup, and cost criteria without changing application architecture.
