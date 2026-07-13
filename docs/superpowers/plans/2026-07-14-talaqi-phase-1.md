# Talaqi Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver regional configuration, secure identity and sessions, complete profiles and eligibility, four-locale localization, public discovery APIs, saved events, and the localized public web experience.

**Architecture:** Add bounded vertical modules to the existing stateless FastAPI modular monolith and consume them through the versioned OpenAPI boundary from Next.js. PostgreSQL remains authoritative, email intents use the transactional outbox, web authentication uses secure cookies while identity/session services remain transport-neutral for future mobile clients.

**Tech Stack:** Python 3.13, FastAPI 0.139.0, Pydantic 2.13.4, SQLAlchemy asyncio 2.0.51, PostgreSQL 18, Alembic 1.18.5, Argon2, Next.js 16.2.10, React 19, TypeScript 5.9.3, Vitest 4.1.10, Playwright 1.61.1, pnpm 10.34.5.

## Global Constraints

- Binding design: `docs/superpowers/specs/2026-07-14-talaqi-phase-1-design.md`.
- Baseline: `511d97b15a251974a8631d9f1df493a492c310cf` after the approved design commit.
- Preserve Phase 0 API envelopes, request IDs, strict hosts/CORS, security headers, redacted logging, idempotency, deterministic OpenAPI generation, and changed-file CI.
- Preserve connection-free import, application construction, middleware-stack construction, and OpenAPI generation; database settings and engines resolve only during runtime requests/lifespan.
- Existing migration `0001_closed_beta_baseline` and its SQL asset remain byte-identical.
- PostgreSQL integration and migration tests never use SQLite and never target a non-loopback/non-`_test` database.
- Every state-changing cookie-authenticated endpoint added after Task 1.3 requires CSRF validation.
- Never persist or log raw passwords, access/refresh tokens, verification/reset tokens, CSRF secrets, cookies, private links, or submitted credentials.
- Unverified users may log in but cannot create clubs/events, save events, or register for events.
- Registration uses email/password; login accepts email and, after profile creation, username.
- Authentication constants: access 900 seconds, refresh 2,592,000 seconds, verification 86,400 seconds, reset 3,600 seconds, lockout 900 seconds after 5 failures, password length 12-128.
- Exact new Python dependencies are `argon2-cffi==25.1.0` and `email-validator==2.3.0`; do not add JWT, Redis, OAuth, payment, analytics, recommendation-ML, or production email-provider dependencies.
- Development/test discovery fixtures are explicit seed-command data; production migrations never insert fake users, clubs, or events.
- Each master task ends as exactly one reviewed commit using its specified subject. Push it fast-forward to `origin/main`, verify the remote SHA, then continue.

---

### Task 1.1: Regional catalog and policy service

**Files:**
- Create: `apps/api/src/talaqi/runtime.py`
- Create: `apps/api/src/talaqi/regions/__init__.py`
- Create: `apps/api/src/talaqi/regions/models.py`
- Create: `apps/api/src/talaqi/regions/repository.py`
- Create: `apps/api/src/talaqi/regions/service.py`
- Create: `apps/api/src/talaqi/regions/schemas.py`
- Create: `apps/api/src/talaqi/regions/routes.py`
- Create: `database/migrations/versions/0002_regional_catalog.py`
- Create: `apps/api/tests/regions/conftest.py`
- Create: `apps/api/tests/regions/test_service.py`
- Create: `apps/api/tests/regions/test_routes.py`
- Create: `apps/api/tests/regions/test_seed_replay.py`
- Modify: `apps/api/src/talaqi/main.py`
- Modify: `apps/api/tests/db/test_migrations.py`
- Modify: `apps/api/tests/db/test_schema_contract.py`
- Regenerate: `openapi/talaqi-v1.json`
- Regenerate: `packages/api-client/src/schema.generated.ts`

**Interfaces:**
- Produces: `RegionPolicyService.get(country_code: str) -> RegionPolicy`.
- Produces: `RegionPolicyService.validate_deadlines(policy, *, event_start, obligations=()) -> None`.
- Produces: public `GET /api/v1/countries`, `/api/v1/cities`, `/api/v1/categories`, and `/api/v1/regions/{country_code}/policy`.
- Produces: request-scoped `AsyncSession` dependency from a lazy runtime; later tasks reuse it.

- [ ] **Step 1: Add failing regional domain and seed tests**

```python
async def test_launch_policies_are_seeded_with_approved_defaults(region_service):
    turkey = await region_service.get("TR")
    algeria = await region_service.get("DZ")
    assert (turkey.default_locale, turkey.default_currency) == ("tr", "TRY")
    assert (turkey.cash_default_minutes, turkey.cash_bounds) == (1440, (120, 4320))
    assert (algeria.default_locale, algeria.default_currency) == ("fr", "DZD")
    assert (algeria.cash_default_minutes, algeria.cash_bounds) == (2880, (120, 10080))
    assert turkey.cancellation_bounds == algeria.cancellation_bounds == (0, 10080)
    assert turkey.club_limit == algeria.club_limit == 1
    assert turkey.independent_event_limit == algeria.independent_event_limit == 3
```

Run: `.venv\Scripts\python.exe -m pytest -q apps/api/tests/regions`
Expected: FAIL because `talaqi.regions` and revision `0002_regional_catalog` do not exist.

- [ ] **Step 2: Add the lazy runtime and regional domain contracts**

```python
@dataclass(frozen=True, slots=True)
class RegionPolicy:
    country_code: str
    default_locale: Literal["en", "tr", "fr", "ar"]
    default_currency: str
    allowed_registration_methods: tuple[str, ...]
    cash_default_minutes: int
    cash_bounds: tuple[int, int]
    cancellation_default_minutes: int
    cancellation_bounds: tuple[int, int]
    club_limit: int
    independent_event_limit: int
    exact_venue_public_by_default: bool
    revision: int
```

`runtime.py` must expose an application-installed lazy session-factory holder and `async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]`. It resolves settings at request/lifespan time, uses `build_async_engine`/`build_session_factory`, rolls back on exception, closes every session, and supports test injection without opening a connection during OpenAPI generation.

- [ ] **Step 3: Add migration `0002_regional_catalog`**

Use parameter-free deterministic SQL in the migration to upsert:

- `TR`, `regions.country.tr`, locale `tr`, currency `TRY`.
- Istanbul slug `istanbul`, `Europe/Istanbul`, beta enabled.
- `DZ`, `regions.country.dz`, locale `fr`, currency `DZD`.
- Algiers slug `algiers`, `Africa/Algiers`, beta enabled.
- Categories, ordered: `sports`, `arts-culture`, `technology`, `language-exchange`, `outdoors`, `games`.
- Turkey policy: methods `free` and `cash_organizer_confirmed`; cash 120/1440/4320; cancellation 0/1440/10080; limits 1/3; exact venue false.
- Algeria policy: methods `free` and `cash_organizer_confirmed`; cash 120/2880/10080; cancellation 0/1440/10080; limits 1/3; exact venue false.

Downgrade deletes only rows owned by this revision and refuses destructive execution unless `validate_test_database_url(TEST_DATABASE_URL)` passes.

- [ ] **Step 4: Implement repository, policy validation, and public schemas/routes**

Repository queries use bound SQLAlchemy parameters, select only enabled public rows, normalize country codes to uppercase and city/category slugs to lowercase, and map missing/disabled regions to `ApiError(code="region_not_found", message_key="errors.region_not_found", status_code=404)`.

`validate_deadlines` rejects negative/inverted bounds, values outside the country ceiling, deadlines after event start, and changes that invalidate supplied active obligation timestamps. It never mutates persisted state.

- [ ] **Step 5: Register routes and prove construction remains lazy**

Add the router in `create_app()` without resolving settings or constructing an engine. Extend OpenAPI tests to call `create_app().openapi()` with all configuration variables absent.

- [ ] **Step 6: Verify focused, migration, contract, and full gates**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q apps/api/tests/regions apps/api/tests/db
python -m uv run alembic upgrade head
.venv\Scripts\python.exe -m pytest -q
corepack pnpm openapi:generate
corepack pnpm openapi:check
corepack pnpm --filter @talaqi/api-client test
corepack pnpm --filter @talaqi/api-client typecheck
```

Expected: all commands exit 0; migration upgrade/downgrade/upgrade is covered by the database suite; OpenAPI has no drift.

- [ ] **Step 7: Commit and delivery gate**

```powershell
git add apps/api database/migrations/versions/0002_regional_catalog.py openapi packages/api-client
git commit -m "feat: add configurable regional policies"
```

Independent task review must approve specification compliance and code quality before fast-forward push to `origin/main`.

---

### Task 1.2: Accounts and password authentication

**Files:**
- Create: `apps/api/src/talaqi/identity/__init__.py`
- Create: `apps/api/src/talaqi/identity/models.py`
- Create: `apps/api/src/talaqi/identity/passwords.py`
- Create: `apps/api/src/talaqi/identity/repository.py`
- Create: `apps/api/src/talaqi/identity/sessions.py`
- Create: `apps/api/src/talaqi/identity/service.py`
- Create: `apps/api/src/talaqi/identity/dependencies.py`
- Create: `apps/api/src/talaqi/identity/schemas.py`
- Create: `apps/api/src/talaqi/identity/routes.py`
- Create: `apps/api/src/talaqi/identity/password_denylist.sha256`
- Create: `database/migrations/versions/0003_identity_authentication.py`
- Create: `apps/api/tests/identity/conftest.py`
- Create: `apps/api/tests/identity/test_passwords.py`
- Create: `apps/api/tests/identity/test_service.py`
- Create: `apps/api/tests/identity/test_routes.py`
- Create: `apps/api/tests/identity/test_security.py`
- Modify: `apps/api/pyproject.toml`
- Modify: `apps/api/src/talaqi/main.py`
- Modify: `apps/api/src/talaqi/config.py`
- Modify: `.env.example`
- Modify: `uv.lock`
- Regenerate: `openapi/talaqi-v1.json`
- Regenerate: `packages/api-client/src/schema.generated.ts`

**Interfaces:**
- Consumes: Task 1.1 lazy database session dependency.
- Produces: `AuthService.require_user(request) -> AuthPrincipal`.
- Produces: `AuthPrincipal(user_id, session_id, email_verified, status, is_platform_admin)`.
- Produces: `POST /api/v1/auth/register`, `/login`, `/logout`.
- Produces: stable session codec/service extended by Task 1.3 rather than replaced.

- [ ] **Step 1: Add exact dependencies and failing password/identity tests**

Pin `argon2-cffi==25.1.0` and `email-validator==2.3.0`, refresh `uv.lock`, then write RED tests for 12/128 boundaries, 129 rejection, Unicode preservation, whitespace-only rejection, denylisted hashes, Argon2id output, verify mismatch, normalized email, duplicate registration, username lookup, generic missing/suspended/locked failures, and five-failure lockout.

```python
def test_password_policy_rejects_breached_digest(policy):
    with pytest.raises(ApiError) as error:
        policy.validate("password123456")
    assert error.value.code == "invalid_credentials_input"
```

Run: `.venv\Scripts\python.exe -m pytest -q apps/api/tests/identity`
Expected: FAIL because the identity module does not exist.

- [ ] **Step 2: Implement password and identifier primitives**

Use `argon2.PasswordHasher` with Argon2id, memory cost 65,536 KiB, time cost 3, parallelism 4, 32-byte hash, and 16-byte salt. Run hashing/verification through `asyncio.to_thread`; propagate cancellation. The denylist stores uppercase SHA-256 digests only, loads once, and compares the submitted password digest with `hmac.compare_digest`. Email normalization uses `email_validator.validate_email(..., check_deliverability=False)` and stores its normalized result lowercased. Username normalization is lowercase ASCII matching `^[a-z0-9_]{3,30}$`.

- [ ] **Step 3: Add identity migration and repository**

Revision `0003_identity_authentication` may add safe indexes/constraints needed for normalized identifier lookup and lockout, but must not rewrite password hashes or seed users. Repository methods are atomic and bound-parameter only:

```python
class IdentityRepository(Protocol):
    async def create_user(self, registration: NewUser) -> UserRecord: ...
    async def find_for_login(self, identifier: str) -> UserRecord | None: ...
    async def record_failed_login(self, user_id: UUID, now: datetime) -> LoginState: ...
    async def clear_failed_login(self, user_id: UUID) -> None: ...
    async def create_session(self, session: NewSession) -> SessionRecord: ...
    async def revoke_session(self, session_id: UUID, reason: str, now: datetime) -> None: ...
```

- [ ] **Step 4: Implement stable access sessions and authentication service**

Create a 32-byte random server session identifier persisted in `sessions`; populate required refresh/CSRF hashes with domain-separated random values but do not expose refresh/CSRF cookies until Task 1.3. The access cookie is a canonical base64url payload plus HMAC-SHA256 signature using `SESSION_SECRET`; payload fields are version `1`, session UUID, user UUID, issued-at integer, and 900-second expiry. Cookie name is `talaqi_access`; path `/`; `HttpOnly`; `SameSite=Lax`; `Secure` follows validated settings.

Always run one Argon2 verification for missing identifiers using a fixed valid dummy hash. On successful login clear failures and issue a session. On the fifth failed attempt set `locked_until=now+900s`. Public failure is always `ApiError(code="invalid_credentials", message_key="errors.invalid_credentials", status_code=401)`.

- [ ] **Step 5: Implement schemas/routes and non-enumerating behavior**

Registration body contains only `email`, `password`, `age_attested: Literal[True]`, `terms_version`, and `privacy_version`. Versions must match configured current versions. Duplicate registration returns the same `202` response shape as creation and emits no second account. Login body contains `identifier` and `password`; success returns only safe user/session status and sets the access cookie. Logout revokes the current session and clears the cookie; before Task 1.3 it accepts the authenticated access cookie without a CSRF requirement because Task 1.3 owns and immediately adds CSRF to all mutations.

- [ ] **Step 6: Verify security, timing-shape, lockout, log, migration, and contract gates**

Tests must prove missing-user and wrong-password paths perform one Argon2 verify call, raw credentials never enter response/log/database session hashes, cancellation propagates from password work, normalized duplicates race to one row, and unverified principals authenticate with `email_verified=False`.

Run focused identity tests, full Python suite, migration round trip, Ruff/S/Pyright, OpenAPI generation/check, API-client tests/typecheck, pre-commit, pip-audit, and secret scanning. All exit 0.

- [ ] **Step 7: Commit and delivery gate**

```powershell
git commit -m "feat: add secure account authentication"
```

Review and push only after the task reviewer approves both verdicts.

---

### Task 1.3: Verification, reset, and rotating sessions

**Files:**
- Create: `apps/api/src/talaqi/identity/tokens.py`
- Create: `apps/api/src/talaqi/identity/csrf.py`
- Create: `apps/api/src/talaqi/identity/outbox.py`
- Create: `database/migrations/versions/0004_verification_rotating_sessions.py`
- Create: `apps/api/tests/identity/test_tokens.py`
- Create: `apps/api/tests/identity/test_rotation.py`
- Create: `apps/api/tests/identity/test_csrf.py`
- Create: `apps/api/tests/identity/test_session_routes.py`
- Create: `apps/api/tests/identity/test_recovery_routes.py`
- Modify: `apps/api/src/talaqi/identity/models.py`
- Modify: `apps/api/src/talaqi/identity/repository.py`
- Modify: `apps/api/src/talaqi/identity/sessions.py`
- Modify: `apps/api/src/talaqi/identity/service.py`
- Modify: `apps/api/src/talaqi/identity/dependencies.py`
- Modify: `apps/api/src/talaqi/identity/schemas.py`
- Modify: `apps/api/src/talaqi/identity/routes.py`
- Regenerate: OpenAPI and generated client.

**Interfaces:**
- Consumes: Task 1.2 session codec, identity repository, principal, and auth routes.
- Produces: verification request/confirm, reset request/confirm, refresh, session list/revoke endpoints, and durable email outbox events.
- Produces: `require_csrf(request, principal) -> None` dependency reused by later mutations.

- [ ] **Step 1: Add RED token, rotation, replay, CSRF, and recovery tests**

Cover 86,400-second verification expiry, 3,600-second reset expiry, used/expired/wrong-kind tokens, non-enumerating requests, atomic verification, password reset revoking every session, refresh rotation, concurrent double refresh, replay-family revocation, current/other/all session revocation, cross-user denial, cookie flags, CSRF missing/mismatch, and cancellation.

```python
async def test_refresh_replay_revokes_entire_family(session_service):
    first = await session_service.issue(user_id)
    replacement = await session_service.rotate(first.raw_refresh)
    with pytest.raises(ApiError) as replay:
        await session_service.rotate(first.raw_refresh)
    assert replay.value.code == "invalid_session"
    assert await session_service.is_active(replacement.session_id) is False
```

- [ ] **Step 2: Implement token hashing and outbox creation**

Generate a random UUID4 token identifier. The public token is `<uuid>.<base64url(HMAC-SHA256(session_secret, domain || NUL || uuid.bytes))>`. Persist only `HMAC-SHA256(session_secret, b"stored\0" + public_token)` in `auth_tokens.token_hash`. Confirmation parses the UUID, recomputes the authenticator and stored hash with `compare_digest`, locks the row, verifies kind/expiry/unused state, and sets `used_at` in the same transaction as user verification or password/session changes.

Outbox payload contains only user UUID, auth-token UUID, locale hint, and an internal template/event identifier. The delivery adapter reconstructs the link from the token UUID and the session secret; no raw token is persisted in `outbox_events`. Tests prove reconstruction yields the same public token and that database/log/output inspection cannot recover the session secret. Document the production-provider handoff boundary.

- [ ] **Step 3: Implement rotating refresh families**

Cookie names are `talaqi_access`, `talaqi_refresh`, and `talaqi_csrf`. Refresh values are opaque 32-byte random tokens; database stores domain-separated HMAC hashes. Rotation uses `SELECT ... FOR UPDATE`, rejects expired/revoked sessions, marks the current row rotated/revoked, creates the replacement in the same family, links `replaced_by_session_id`, and returns new access/refresh/CSRF values. Replay of a rotated token revokes every active row in that family before returning a generic 401.

- [ ] **Step 4: Implement session-bound CSRF**

The readable CSRF cookie contains a random value; the request must send the same value in `X-CSRF-Token`. Verify the cookie/header with `compare_digest`, then verify its domain-separated HMAC against the current session's `csrf_secret_hash`. Apply to logout, refresh where browser cookie transport is used, session revocation, reset-confirm when authenticated, and every later profile/saved-event mutation. Safe methods do not require CSRF.

- [ ] **Step 5: Add endpoints and restricted-session policy**

Add:

- `POST /api/v1/auth/verification/request`
- `POST /api/v1/auth/verification/confirm`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/sessions`
- `DELETE /api/v1/auth/sessions/{session_id}`
- `DELETE /api/v1/auth/sessions`

Verification/reset request responses are identical for absent/present accounts. Restricted unverified principals can request/confirm verification and manage sessions. Password reset replaces the Argon2 hash and revokes all existing session families.

- [ ] **Step 6: Verify focused concurrency/security plus full gates**

Run identity suites against PostgreSQL, migration round trip, full pytest, static gates, OpenAPI/client gates, pre-commit, audits, and secret scan. Use real concurrent sessions for rotation/replay tests. Expected: all exit 0 and no raw token substring appears in logs, database token/hash columns, exception text, or OpenAPI examples.

- [ ] **Step 7: Commit and delivery gate**

```powershell
git commit -m "feat: add verification reset and rotating sessions"
```

Review, amend findings, verify, fast-forward push, and confirm remote SHA.

---

### Task 1.4: Profiles, preferences, and creation eligibility

**Files:**
- Create: `apps/api/src/talaqi/profiles/__init__.py`
- Create: `apps/api/src/talaqi/profiles/models.py`
- Create: `apps/api/src/talaqi/profiles/repository.py`
- Create: `apps/api/src/talaqi/profiles/service.py`
- Create: `apps/api/src/talaqi/profiles/eligibility.py`
- Create: `apps/api/src/talaqi/profiles/schemas.py`
- Create: `apps/api/src/talaqi/profiles/routes.py`
- Create: `database/migrations/versions/0005_profiles_eligibility.py`
- Create: `apps/api/tests/profiles/conftest.py`
- Create: `apps/api/tests/profiles/test_service.py`
- Create: `apps/api/tests/profiles/test_eligibility.py`
- Create: `apps/api/tests/profiles/test_routes.py`
- Modify: `apps/api/src/talaqi/main.py`
- Regenerate: OpenAPI and generated client.

**Interfaces:**
- Consumes: `RegionPolicyService`, `AuthPrincipal`, `require_csrf`.
- Produces: `GET/PATCH /api/v1/me`, `GET /api/v1/me/capabilities`.
- Produces: `CreationEligibilityService.evaluate(principal, profile) -> Capabilities`.

- [ ] **Step 1: Add RED normalization, compatibility, access, and capability tests**

Test username lowercasing and uniqueness races, display-name trim, enabled country/city pairing, locale/time-zone/currency compatibility, required preferences, security-email immutability, incomplete profiles, unverified email, stale rules, suspended/deleted user, limits, cross-user denial, and admin capability.

```python
assert capabilities.create_club is False
assert capabilities.create_independent_event is False
assert capabilities.save_event is False
assert capabilities.blockers == ("email_verification_required", "profile_incomplete")
```

- [ ] **Step 2: Add migration and profile repository**

Revision `0005_profiles_eligibility` adds only missing constraints/indexes or explicit rule-version fields needed by the approved profile contract. It does not create avatars or media behavior. Upsert the caller's own profile atomically; no route accepts a user ID for profile mutation.

- [ ] **Step 3: Implement profile validation/service**

`PATCH /me` is a complete replacement of editable profile values for deterministic completion: username, display name, country code, city slug, locale, time zone, preferred currency, event/community email preferences, organizer rules version, and community rules version. Validate region compatibility through Task 1.1. Mark `profile_completed_at` only when all fields and current rule versions are valid.

- [ ] **Step 4: Implement stable capability model**

```python
class Capabilities(BaseModel):
    create_club: bool
    create_independent_event: bool
    save_event: bool
    register_event: bool
    access_admin: bool
    blockers: tuple[str, ...]
```

Blockers are stable sorted codes from: `account_unavailable`, `email_verification_required`, `profile_incomplete`, `rules_acceptance_required`, `region_unavailable`, `club_limit_reached`, `independent_event_limit_reached`, `admin_mfa_required`. Ownership counts query existing clubs/events but do not create them. Limits never delete existing resources.

- [ ] **Step 5: Add routes with authentication/CSRF and safe responses**

`GET` routes require an active principal. `PATCH /me` requires CSRF. Responses never expose email, password/session state, admin internals, or another user's profile. Avatar is always absent/null until Phase 3.

- [ ] **Step 6: Verify profile/policy/PostgreSQL/contracts/full gates**

Run focused profile and region tests, migration round trip, full pytest, OpenAPI/client generation and tests, static/security gates, pre-commit, audits. Expected: all exit 0.

- [ ] **Step 7: Commit and delivery gate**

```powershell
git commit -m "feat: add profiles and creation eligibility"
```

Review and verified push to `main`.

---

### Task 1.5: Complete localization and RTL framework

**Files:**
- Create: `apps/api/src/talaqi/localization/__init__.py`
- Create: `apps/api/src/talaqi/localization/service.py`
- Create: `apps/api/tests/localization/test_service.py`
- Create: `packages/translations/src/dictionaries/en.ts`
- Create: `packages/translations/src/dictionaries/tr.ts`
- Create: `packages/translations/src/dictionaries/fr.ts`
- Create: `packages/translations/src/dictionaries/ar.ts`
- Create: `packages/translations/src/formatters.ts`
- Create: `packages/translations/src/locale.ts`
- Create: `packages/translations/src/parity.test.ts`
- Create: `packages/translations/src/formatters.test.ts`
- Create: `packages/translations/scripts/check-literals.mjs`
- Modify: `packages/translations/src/index.ts`
- Modify: `packages/translations/package.json`
- Modify: `apps/web/src/app/layout.tsx`
- Modify: relevant shell/home components to remove direct visible literals.
- Create: locale/RTL component and Playwright tests.

**Interfaces:**
- Consumes: supported locale and regional default values from prior tasks.
- Produces: `resolve_locale(profile, explicit, accept_language, regional_default) -> LocaleCode`.
- Produces: shared `translate`, `formatDate`, `formatNumber`, `formatCurrency`, `formatPlural`, `getLocaleDirection`, and document-locale utilities.

- [ ] **Step 1: Add RED parity, literal, formatter, and RTL tests**

Tests assert exact key parity, no value copied unchanged from English unless allowlisted brand/proper noun, no visible string literals in feature components, Turkish/French/Arabic number/date/currency output, Arabic `dir=rtl`, immediate `lang`/`dir` update, and pseudo-long values without overflow.

- [ ] **Step 2: Split dictionaries and implement locale resolution**

Locale precedence is authenticated profile, explicit public choice, supported `Accept-Language`, regional default, English. Normalize subtags (`tr-TR -> tr`, `ar-DZ -> ar`) and ignore unsupported or malformed values. API errors keep stable `message_key`; the client translates it and falls back to `errors.unknown` without rendering the raw key.

- [ ] **Step 3: Implement `Intl` formatters**

Use platform `Intl.DateTimeFormat`, `Intl.NumberFormat`, and plural rules; do not add a formatting dependency. Dates require explicit IANA time zone. Currency requires a supported ISO code from regional/profile data. Expose deterministic options so tests do not depend on host defaults.

- [ ] **Step 4: Complete dictionaries and remove direct visible literals**

Add all Phase 1 navigation, auth, profile, region, discovery, state, filter, accessibility, and error keys in all four languages. Preserve native UTF-8 source. Brand name `Talaqi` is the only broad literal-copy allowance; proper city/currency codes are explicit narrow allowances.

- [ ] **Step 5: Wire document language/direction and RTL-safe layout**

Server render initial `lang`/`dir`; client locale changes update both attributes synchronously. Use logical CSS only for new/modified layout and maintain keyboard order independent of visual RTL direction.

- [ ] **Step 6: Verify translation, component, screenshot/browser, and full gates**

Run translation tests/literal checker, web tests, lint/typecheck/build, Playwright for `en/tr/fr/ar` including Arabic RTL and 320px overflow, then full root suites and pre-commit. Expected: all exit 0.

- [ ] **Step 7: Commit and delivery gate**

```powershell
git commit -m "feat: establish complete localization framework"
```

Review and verified push to `main`.

---

### Task 1.6: Public discovery read models and search API

**Files:**
- Create: `apps/api/src/talaqi/discovery/__init__.py`
- Create: `apps/api/src/talaqi/discovery/models.py`
- Create: `apps/api/src/talaqi/discovery/repository.py`
- Create: `apps/api/src/talaqi/discovery/service.py`
- Create: `apps/api/src/talaqi/discovery/schemas.py`
- Create: `apps/api/src/talaqi/discovery/routes.py`
- Create: `apps/api/src/talaqi/discovery/fixtures.py`
- Create: `apps/api/scripts/seed_discovery_fixtures.py`
- Create: `database/migrations/versions/0006_discovery_indexes.py`
- Create: `apps/api/tests/discovery/conftest.py`
- Create: `apps/api/tests/discovery/test_repository.py`
- Create: `apps/api/tests/discovery/test_routes.py`
- Create: `apps/api/tests/discovery/test_privacy.py`
- Create: `apps/api/tests/discovery/test_saved_events.py`
- Create: `apps/api/tests/discovery/test_query_plans.py`
- Modify: `apps/api/src/talaqi/main.py`
- Regenerate: OpenAPI and generated client.

**Interfaces:**
- Consumes: regions, authenticated principal, capabilities, CSRF, cursor codec.
- Produces: `GET /api/v1/events`, `/events/{id}`, `/clubs`, `/clubs/{slug}`, `/search`, `/metadata`.
- Produces: `PUT/DELETE /api/v1/events/{event_id}/saved`, `GET /api/v1/me/saved-events`.

- [ ] **Step 1: Add RED filters, cursor, privacy, saved-state, and query-plan tests**

Cover country/city/category/date/price/search combinations, stable `(featured_score, start_at, id)` ordering, cursor mismatch/tamper, normalized search, draft/suspended/private-link exclusion, coarse venue only, unauthenticated card state, restricted unverified save, idempotent save/delete, cursor-paginated saved list, zero capacity effects, and representative `EXPLAIN` index usage.

- [ ] **Step 2: Add discovery indexes migration**

Revision `0006_discovery_indexes` adds only indexes required by measured test queries, using partial predicates for published/public/non-suspended rows. No production fixture rows are inserted. Downgrade removes only its indexes.

- [ ] **Step 3: Implement deterministic fixture command**

The explicit script refuses production/staging, requires an explicit local `_test` or development database, and upserts deterministic UUIDv7-compatible fixture IDs for at least two clubs and four events across Istanbul/Algiers, free/cash, categories, future dates, plus draft/suspended/private-link negative fixtures. It also creates one fixture owner with an unusable Argon2id hash. Replays produce identical logical data.

- [ ] **Step 4: Implement read repository and stable cursors**

Queries select card-ready cover reference, localized date/price state inputs, coarse district/meeting area, availability, organizer/club summary, and optional caller save/registration state. Never return exact address/coordinates, owner email/profile-private fields, invite tokens, or attendee data. Cursor filter fingerprint binds country/city/category/date/price/search/sort so it cannot be reused across filters.

- [ ] **Step 5: Implement routes and saved-event mutations**

Public GET routes accept bounded query strings and page sizes. `PUT`/`DELETE saved` require active verified principal, `save_event` capability, and CSRF. They are naturally idempotent with the `(user_id,event_id)` key. Missing/non-public events return the same public 404.

- [ ] **Step 6: Verify repository/API/privacy/query-plan/contracts/full gates**

Run focused discovery tests against PostgreSQL, migration round trip, OpenAPI/client generation/tests, full Python/static/security/pre-commit/audit gates. Expected: all exit 0; query plans use approved indexes; production migration contains no fixture clubs/events/users.

- [ ] **Step 7: Commit and delivery gate**

```powershell
git commit -m "feat: add public discovery APIs"
```

Review and verified push to `main`.

---

### Task 1.7: Public web experience

**Files:**
- Create: `apps/web/src/lib/api/public-client.ts`
- Create: `apps/web/src/lib/locale/locale-context.tsx`
- Create: `apps/web/src/components/discovery/event-card.tsx`
- Create: `apps/web/src/components/discovery/club-card.tsx`
- Create: `apps/web/src/components/discovery/filter-drawer.tsx`
- Create: `apps/web/src/components/discovery/result-states.tsx`
- Create: `apps/web/src/app/explore/page.tsx`
- Create: `apps/web/src/app/clubs/[slug]/page.tsx`
- Create: `apps/web/src/app/events/[id]/page.tsx`
- Create: `apps/web/src/app/error.tsx`
- Create: `apps/web/src/app/loading.tsx`
- Create: focused component/page tests beside each component/page.
- Create: `tests/e2e/discovery.spec.ts`
- Modify: `apps/web/src/app/page.tsx`
- Modify: `apps/web/src/app/layout.tsx`
- Modify: `apps/web/src/app/globals.css`
- Modify: shell navigation and translation dictionaries only for Phase 1 keys.

**Interfaces:**
- Consumes: generated API-client schemas from Task 1.6 and localization APIs from Task 1.5.
- Produces: landing, Explore, filter drawer, public club/event detail skeletons, locale/region chooser, and accessible localized states.

- [ ] **Step 1: Add RED component and routing tests**

Test card content/privacy, URL-backed filters, drawer keyboard behavior/focus return, locale/region selection, loading/empty/error states, featured-ranking explanation, no exact venue, server metadata, safe public-cache directives, no caching of authenticated/save state, and all navigation links.

- [ ] **Step 2: Implement the typed public API adapter**

Use generated schemas and a small fetch wrapper. Public list/detail requests use explicit bounded revalidation/cache tags only when no cookies or user-specific state are present. Authenticated/save-state requests use `cache: "no-store"`. Map failures to stable UI state keys; never render raw server bodies or exception text.

- [ ] **Step 3: Build landing and Explore**

Landing includes region chooser, categories, featured events, popular clubs, transparent rule-based explanation, and organizer CTA that leads to profile/capability guidance rather than creation. Explore parses and serializes country, city, category, date, price, search, and cursor in the URL. Filters work without JavaScript through navigation/form semantics and enhance to a keyboard-accessible drawer.

- [ ] **Step 4: Build club/event details and states**

Club detail renders public description/category/region and its public events. Event detail skeleton renders cover placeholder, localized schedule/price state, coarse venue, availability, organizer/club summary, rules/cancellation summary placeholder, and save affordance for eligible sessions. It never displays exact address, coordinates, attendees, private links, or internal ranking scores.

- [ ] **Step 5: Complete accessibility, responsive, locale, RTL, and metadata behavior**

Use semantic landmarks/headings, visible focus, 44px targets, reduced motion, logical CSS, responsive images/placeholders, translated accessible names, and document locale/direction. Generate server metadata from public safe fields only. Ensure no page-level overflow at 320px in every locale.

- [ ] **Step 6: Add Playwright discovery journeys**

Run mobile 320px and desktop Chromium journeys for all four locales. Cover landing to Explore, filters reflected in URL, club detail, event detail, keyboard drawer/skip link, Arabic RTL, empty/error behavior via deterministic fixture/test server, and absence of exact venue/private text. Add axe checks with zero serious/critical findings using the repository-approved accessibility test dependency if already present; if adding one, pin it exactly and audit it.

- [ ] **Step 7: Verify web/API contract and full Phase 1 gates**

Run focused web/translation/API-client tests, lint, typecheck, production build, OpenAPI check, brand check, Playwright all-locale discovery journeys, full Python suite, migration head/round trip, pre-commit, secret/dependency/security scans. Expected: all exit 0, no high/critical findings, no OpenAPI drift, and one Alembic head.

- [ ] **Step 8: Commit, final review, and delivery gate**

```powershell
git commit -m "feat: deliver localized public discovery experience"
```

After task review and verified push, run a final independent review over the complete Phase 1 range and verify the Phase 1 exit: a verified adult completes a valid profile; restricted sessions remain restricted; visitors discover safe fixtures in four locales; all auth, CSRF, privacy, accessibility, migration, contract, and browser gates pass.
