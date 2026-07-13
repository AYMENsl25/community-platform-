# Talaqi Phase 1 Design

**Status:** Approved for implementation planning  
**Date:** 2026-07-14  
**Phase:** Identity, regions, localization, and discovery  
**Baseline:** Phase 0 commit `e3c278354918695e62f549e3c6b1541ea907ef9a`

## Purpose

Phase 1 turns the Phase 0 foundation into the first usable Talaqi product slice. It adds regional configuration for Istanbul and Algiers, secure email/password identity, verification and rotating sessions, complete member profiles and eligibility decisions, four-locale localization, public discovery APIs, saved events, and the localized public web experience.

The phase does not add club or event creation, membership management, registrations, media uploads, online payments, moderation operations, or production email-provider selection. Public club and event records used to prove discovery are deterministic development/test fixtures; they are not fake production data.

## Approved product decisions

- Registration accepts email and password. Username is selected during profile completion.
- Login accepts email immediately and accepts username after a completed profile supplies one.
- Email-unverified users may log in with a restricted session. They may access verification and session-management functions but may not create clubs, create independent events, save events, or register for events.
- Email verification alone does not unlock creation. Creation also requires a complete profile, the approved 18+ attestation, current terms/privacy acceptance, and current organizer/community-rules acceptance.
- Any eligible verified member may automatically create clubs and independent events in later phases; Phase 1 only returns the eligibility decision and blockers.
- Online payments remain deferred. Phase 1 discovery may describe free or organizer-confirmed cash fixtures only.
- Access-cookie lifetime is 15 minutes.
- Rotating refresh-session lifetime is 30 days.
- Email-verification token lifetime is 24 hours.
- Password-reset token lifetime is 1 hour.
- Login locks for 15 minutes after five failed attempts.
- Passwords are 12 to 128 characters and reject known common or breached values without logging or persisting the supplied password.

## Architecture

Talaqi remains a modular monolith for the closed beta: one stateless FastAPI deployment initially, divided into bounded modules with explicit interfaces. This deployment choice does not couple the backend to the Next.js web application. Web, future native mobile applications, and explicitly authorized integrations consume the same versioned `/api/v1` HTTP boundary and deterministic OpenAPI contract.

Each bounded module owns its routes, request/response schemas, application services, repositories, policy rules, and focused tests. Modules may depend on published typed interfaces but may not import another module's repository internals or mutate another module's tables directly. Discovery is a deliberate read-model boundary and may join public data through its own read-only repository queries.

The application remains horizontally scalable. API processes hold no authoritative session, rate-limit, or product state in memory in deployed environments. PostgreSQL is the transactional source of truth. Durable email intents use the outbox. Workers scale independently. S3-compatible media remains behind the existing adapter boundary for later phases. A bounded module may be extracted into a separate service later if measured load or organizational ownership justifies it; clients remain stable because the API contract does not change.

Authentication domain services are transport-neutral. Phase 1 implements the approved secure cookie transport for the web and PWA. A future native-mobile token transport may wrap the same identity, session, and capability services without rewriting password, verification, rotation, revocation, or authorization rules.

## Module boundaries and task sequence

### Task 1.1: Regions and policy

The regions module owns countries, cities, categories, locale defaults, currencies, IANA time zones, registration-method availability, ownership limits, exact-venue defaults, cash-deadline bounds, and cancellation-deadline bounds.

`RegionPolicyService.get(country_code)` is the authoritative application interface. Public metadata endpoints expose only enabled countries, beta-enabled cities, enabled categories, and safe policy values. A deterministic data migration seeds Turkey/Istanbul and Algeria/Algiers with the approved defaults. Replaying the seed produces the same logical records and does not duplicate them.

Policy updates validate the complete proposed policy before persistence. They may not make an active reservation invalid, reduce a configured deadline below already-issued obligations, or permit a deadline after event start. Admin mutation endpoints remain out of scope until the administration phase; the validation service is implemented and tested now so future administration uses one rule source.

### Task 1.2: Identity and password authentication

The identity module owns users, normalized identifiers, Argon2id password hashes, current legal-attestation versions, failed-login state, lockout, authentication throttling, registration, login, logout, and `AuthService.require_user()`.

Registration always returns a non-enumerating public result for duplicate or newly created email addresses while creating only one normalized account. Login accepts normalized email or an existing normalized username. Authentication performs timing-safe password verification even when the account is absent or unavailable. Suspended, deleted, and locked users receive generic authentication failures.

Task 1.2 establishes short-lived authenticated access and the session-service interface using the existing session persistence contract. Task 1.3 completes refresh rotation, replay response, session listing/revocation, verification/reset flows, and CSRF enforcement. Task 1.2 must not create a temporary authentication architecture that Task 1.3 discards.

### Task 1.3: Verification, reset, rotating sessions, and CSRF

The session module owns verification/reset tokens, refresh-session families, rotation, replay detection, session listing, revocation, cookie encoding, and CSRF validation. Raw verification, reset, access, refresh, and CSRF secrets are never persisted or logged. Database records store only domain-separated cryptographic hashes.

Verification and reset requests always use non-enumerating responses. Tokens are random, single-use, expiring, and invalid after use. Refreshing atomically revokes the presented session, creates its replacement, and links the two records. Reuse of a rotated refresh token revokes the complete session family. Logout revokes the current session. Users may list their own sessions and revoke one or all other sessions; cross-user access is denied.

The web transport uses `HttpOnly`, `Secure` in deployed environments, `SameSite=Lax` access and refresh cookies. Cookie-authenticated mutations require a CSRF cookie/header match plus a server-verified session-bound secret. Access expiry is 15 minutes and refresh expiry is 30 days. Cancellation continues to propagate, public errors use the existing envelope, and completed request logs contain no credential material.

Verification and reset creation writes durable email intents to `outbox_events`. Local/test delivery uses the existing email test adapter. Production email-provider selection remains deferred to the communications phase.

### Task 1.4: Profiles, preferences, and creation eligibility

The profiles module owns unique normalized username, display name, country, city, locale, IANA time zone, preferred currency, notification preferences, profile completion, and current organizer/community-rules acceptance. Avatar behavior remains disabled until verified media assets exist in Phase 3.

Country, city, locale, time zone, and currency combinations are validated through the regions module. Security email cannot be disabled. A profile is complete only when every required field is valid and persisted.

`CreationEligibilityService` returns explicit boolean capabilities and stable blocker codes for club creation, independent-event creation, event saving, event registration, and administration. It evaluates account state, email verification, profile completeness, current legal/rules acceptance, regional availability, and the configured ownership limits. It reveals no cross-user information. Phase 1 does not implement the mutations governed by the future creation capabilities.

### Task 1.5: Localization and RTL

The localization boundary owns locale resolution, `en`, `tr`, `fr`, and `ar` dictionaries, shared date/number/currency/plural formatters, localized client rendering of stable API error keys, and document `lang`/`dir` state. Locale preference order is authenticated profile, explicit public locale selection, supported request preference, regional default, then English.

All visible feature copy uses translation keys. Dictionary key parity and literal-copy linting are mandatory. Arabic uses RTL-safe logical layout properties. Changing locale updates document language and direction immediately without leaking private response data into public caches. Pseudo-long-text and all-locale rendering tests protect layout resilience.

### Task 1.6: Discovery APIs and saved events

The discovery module owns read-only public club/event/search models, metadata composition, stable filters, cursor ordering, public privacy rules, and saved-event mutations. It exposes public lists/details for events and clubs plus cross-entity search and metadata endpoints.

Discovery includes only published, non-suspended public records. It excludes drafts, closed/suspended content where required, private-link events, exact private venue details, and user-private data. Filters cover country, city, category, date, price type, and normalized search text. Ordering is deterministic, transparent, rule-based, and cursor-stable; no machine-learning recommendation system is introduced.

Authenticated verified members may idempotently save and unsave eligible public events and list their saved events with cursor pagination. Unverified sessions receive the explicit verification blocker. Saved-event records never reserve event capacity.

Development and test discovery records are loaded by a deterministic fixture command. Production migrations contain regional reference data only and never insert fake clubs, users, or events.

### Task 1.7: Localized public web

The web application owns the landing page, Explore results, URL-backed filters, filter drawer, club detail, event detail skeleton, locale/region chooser, loading/empty/error states, transparent featured explanation, and server-rendered public metadata.

The web consumes generated API-client types and does not duplicate domain policy. Public content may use explicitly bounded caching. Sessions, profiles, saved state, private links, and user-specific responses are never cached publicly or by a service worker. Controls are keyboard-operable, targets remain accessible, images are responsive, and layouts support mobile, desktop, reduced motion, long text, and Arabic RTL.

## Request and data flow

1. A client calls a versioned API endpoint with the existing request-ID and security boundary.
2. The transport adapter validates cookies and CSRF where applicable, then resolves an immutable authentication context.
3. The route validates its public schema and calls one application service.
4. The service applies regional, identity, profile, capability, and privacy policies through typed interfaces.
5. Repositories execute within the existing transaction boundary and return domain/read-model values rather than SQL rows.
6. State changes and required communications persist atomically with an outbox event.
7. The route maps the result to the stable response schema. Errors retain the existing generic envelope and message keys.
8. OpenAPI generation updates the checked-in contract and generated TypeScript client; drift fails CI.

## Security and privacy rules

- Preserve the Phase 0 CSP, production HSTS, host/CORS validation, request IDs, redacted structured logs, error envelopes, secret scanning, and dependency gates.
- Never expose account existence through registration, login, verification, or reset responses.
- Never store or log raw passwords, access tokens, refresh tokens, verification/reset values, CSRF secrets, cookie contents, private links, or exception text containing personal data.
- Use Argon2id for password hashes and cryptographically secure random token material.
- Apply the dedicated authentication rate-limit namespace; deployed environments require the production rate-limit provider rather than the in-memory development adapter.
- Authorize by server-owned identity and object relationships, never by user-supplied actor identifiers.
- Require CSRF protection for every cookie-authenticated mutation, including logout, profile changes, saving, unsaving, and session revocation.
- Preserve restricted login: unverified sessions may use verification and session-management functions only.
- Do not collect date of birth, government identification, verification documents, or unnecessary location data.
- Public discovery exposes coarse venue information only. Exact venue visibility remains governed by later event policies.

## Error handling

All endpoints use the Phase 0 error contract with stable codes, translation message keys, field errors, and a server request ID. Authentication and recovery failures are generic. Validation locations are allowlisted and never echo submitted values. Database conflicts map to stable domain errors without exposing constraint names. Configuration failures fail closed. Cancellation is never converted into an application error.

## Migration and compatibility strategy

Each task that changes persistence adds one forward migration and validates upgrade, downgrade, and upgrade against PostgreSQL 18. Existing migration `0001` remains byte-identical. Migrations may add constraints, indexes, or reference data required by the task but may not add later-phase product behavior. Public API evolution remains additive inside `/api/v1` during Phase 1, and every task regenerates/checks OpenAPI and the TypeScript client when its contract changes.

## Test strategy

Every behavior follows RED, GREEN, and refactor. Each task runs focused unit tests, PostgreSQL integration tests where persistence changes, authorization-negative tests, security/log-redaction tests, migration round trips, OpenAPI/client drift, and the full regression suite before commit.

Authentication tests cover normalized duplicate identifiers, common/weak passwords, timing-safe missing-user behavior, lockout boundaries, restricted sessions, token expiry/use, rotation races, replay-family revocation, cookie flags, CSRF missing/mismatch, logout, cross-user session access, and cancellation.

Region/profile tests cover deterministic seeds, disabled/unknown regions, bounds, locale/currency/time-zone compatibility, incomplete profiles, stale legal/rules versions, ownership limits, and cross-user denial.

Discovery tests cover filter combinations, cursor stability, search normalization, privacy exclusions, saved-event idempotency, query plans/index use on representative fixtures, and no capacity effects.

Web tests cover component behavior, accessibility, all four locales, Arabic RTL, long text, mobile and desktop layouts, URL-backed filters, public caching boundaries, production build, and Playwright discovery journeys.

## Commit, review, and GitHub delivery

The seven product tasks use the exact master-plan commit subjects:

1. `feat: add configurable regional policies`
2. `feat: add secure account authentication`
3. `feat: add verification reset and rotating sessions`
4. `feat: add profiles and creation eligibility`
5. `feat: establish complete localization framework`
6. `feat: add public discovery APIs`
7. `feat: deliver localized public discovery experience`

Each task is implemented sequentially in an isolated Phase 1 worktree. A fresh implementer follows its decision-complete task brief and TDD report contract. A separate reviewer checks both specification compliance and code quality. Critical and important findings are fixed and re-reviewed. The controller reruns the applicable complete gates, creates or amends exactly one task commit, pushes that approved fast-forward commit directly to GitHub `main`, verifies the remote SHA, and only then begins the next task.

After Task 1.7, a fresh reviewer evaluates the complete Phase 1 range and the controller runs the Phase 1 acceptance matrix. Phase 1 exits only when a verified adult can complete a valid profile, restricted/unverified behavior is proven, visitors can discover safe public club/event fixtures in all four locales, and all authentication, CSRF, privacy, accessibility, migration, contract, and browser gates pass.

