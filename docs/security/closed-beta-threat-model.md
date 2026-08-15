# Closed-beta threat model

## Scope and invariants

This review covers the public web boundary, FastAPI application, PostgreSQL authority, object storage, transactional outbox worker, email adapter, administrator operations, and CI/release path. Personal data, session material, private-event links, exact venues, attendee lists, moderation evidence, uploaded media, audit history, and backup material are protected assets.

The browser, public network, provider webhooks, uploaded bytes, email provider, object store, CI runner, and operator workstation are separate trust boundaries. PostgreSQL remains authoritative for identity, authorization, registration capacity, moderation state, policy revisions, and outbox leases. No client assertion or provider callback may directly change those invariants.

## Threat and control matrix

| Threat | Required control | Verification |
| --- | --- | --- |
| Session theft, fixation, CSRF, or cross-account revocation | Rotated opaque sessions, server-owned IDs, secure cookie policy, double-submit CSRF, ownership checks, bounded recovery | `apps/api/tests/identity` |
| Host-header, CORS, browser injection, or unsafe error disclosure | Explicit host/origin allowlists, locked methods/headers, CSP and security headers, route-template logs, stable safe errors | `apps/api/tests/security`, `apps/api/tests/platform/test_errors_request_ids.py` |
| Capability escalation or IDOR | Object-level authorization on clubs, events, media, registrations, reports, audit, settings, and outbox actions; MFA for platform operations | `apps/api/tests/audit/test_authorization.py`, feature route suites, `tests/e2e/admin.spec.ts` |
| Private-link or venue disclosure | Hashed private tokens, bounded attempts, revocation, public/private response separation, authenticated attendee access | `apps/api/tests/events/test_private_access.py`, `apps/api/tests/discovery` |
| Malicious or polyglot upload | Bounded size and dimensions, decoded-image verification, canonical re-encoding, MIME allowlist, ownership transitions, private storage keys | `apps/api/tests/media` |
| Registration race or direct state override | PostgreSQL row locks, idempotency, transition records, FIFO promotion, safe operational actions only | `apps/api/tests/registrations`, `apps/api/tests/settings` |
| Worker replay, stale lease, poison message, or sensitive telemetry | Exact lease-token completion, bounded retry/dead letter, deduplication, safe error classes, low-cardinality redacted metrics | `apps/worker/tests`, `apps/api/tests/security/test_telemetry.py` |
| Report abuse or evidence leakage | Authentication, CSRF, rate limit, evidence-safe metadata, MFA moderation, auditable state transitions | `apps/api/tests/moderation` |
| Secret or vulnerable dependency reaches release | Frozen locks, production audits, Ruff security rules, detect-secrets, CodeQL, immutable CI actions | `tests/security`, `.github/workflows/ci.yml` |
| Retained or deleted identity leaks through lifecycle work | Schema-level deletion/anonymization markers now; Task 6.6 owns timed cleanup, recovery, anonymization, backup, and restore verification | `apps/api/tests/db/test_schema_contract.py`; Task 6.6 lifecycle suite |

## Abuse cases and residual risks

- In-memory rate limiting is allowed only in development and tests. Staging and production fail closed without a durable adapter; distributed-limit behavior must be exercised after provider selection.
- Provider-side DAST, alert delivery, object-storage policy inspection, backup encryption, and restore isolation require deployed staging credentials. Local ASGI tests validate the application boundary but cannot certify provider configuration.
- Legal retention periods and the final account-deletion policy require product-owner/legal approval. Code must preserve the documented recovery window and mandatory audit records without treating legal approval as automated.
- A provider or platform exception cannot weaken authentication, authorization, CSRF, private-data boundaries, migration safety, or registration invariants.

## Security exception process

No high or critical finding may be accepted for closed beta. A lower-severity exception requires a tracked record containing the advisory or finding ID, affected asset and component, exploit preconditions, owner, compensating control, expiry date, remediation trigger, and verification evidence. The product owner and security reviewer must approve it. CI suppressions and secret-baseline additions are not exception records. Expired exceptions block release until remediated or explicitly re-reviewed.

## Review gate

Run the focused security matrix, production dependency audits, Ruff security rules, detect-secrets, repository security tests, OpenAPI drift, and the admin/private-event E2E journeys. Record deployed DAST, provider policy, and legal approvals in release evidence; local tests must not claim those external checks passed.
