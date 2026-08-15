# Phase 6 closed-beta release-candidate record

Date: 2026-08-15  
Branch: `phase-6/operational-hardening`  
Verified content SHA: `75edd2537fdfe86d4c98734cef30d829575f89b6`

## Decision

The repository and local disposable-environment release matrix are ready for a staging candidate. The release is **not approved, tagged, or launched**. Staging provider configuration, a representative encrypted-backup restore, legal/product-owner approval, MFA account enrollment, and the monitored 48-hour closed-beta review remain required human/external gates.

## Verified local evidence

| Gate | Result |
| --- | --- |
| Ruff format/lint, Pyright | 328 files formatted; no lint, type, warning, or information findings |
| ESLint and TypeScript | All six-workspace checks passed |
| Global Python gate | Exact documented `pytest -q` command passed: 717 tests |
| API/worker tests | 710 passed in the CI application partition |
| PostgreSQL migration/idempotency tests | 53 passed in the isolated CI partition; clean upgrade, downgrade/re-upgrade, one head, seed counts, readiness, and transaction behavior covered |
| Repository security/deployment/operations tests | 41 passed |
| JavaScript unit/component tests | 192 passed across 45 files |
| OpenAPI and generated client | No drift |
| Brand assets | Four deterministic assets verified |
| Production build | Next.js 16.2.11 build passed, including localized policy routes and PWA assets |
| Browser journeys | 53 Playwright tests passed with one Chromium worker: four locales, RTL, 320 px layouts, accessibility, visitor/member/organizer/admin authorization, registration/waitlist/cash, policies, PWA, and logout cache clearing |
| Security/dependencies | See `phase-6-security-review.md`; the reviewed branch has no known package audit or local high/critical finding |

The first release-matrix attempt incorrectly overlapped the global Python suite with other verification processes and caused shared disposable-schema collisions. Rerunning the exact documented `pytest -q` gate by itself passed all 717 tests. The sequential partitions declared by `.github/workflows/ci.yml` also passed (710 + 53), followed by all 41 repository contract tests. No fixture, assertion, expected identifier, or database safety guard was weakened.

## Release data and controls

- Migration `0002_regional_catalog` deterministically seeds Istanbul and Algiers plus the six approved enabled categories; migration coverage verifies `(2 countries, 2 cities, 6 categories, 2 policies, 1 revision)` after replay.
- Migration `0013_feature_flags` seeds member reports, organizer announcements, and independent event creation. Operational changes require platform-admin role, MFA, CSRF, a reason, preview, and immutable audit evidence.
- No production personal data or fixture identities were imported. The discovery fixture seeder refuses staging/production databases.
- Production configuration fails closed on missing admin MFA enforcement, weak secrets, insecure cookies, non-HTTPS public URLs, unsafe hosts/origins, or migration/readiness failure.

## Required approval evidence before tagging

1. Create GitHub `staging`, `production`, `production-backup`, and `staging-restore` environments with least-privilege provider credentials and reviewer protection. The repository currently reports zero environments.
2. Deploy this immutable branch SHA to staging, verify headers/hosts/CORS/readiness, exercise migration failure and application rollback, and attach redacted provider/workflow evidence.
3. Run the encrypted provider-backup and isolated restore workflows, sample protected media, compare database/media checksums, and record measured recovery time.
4. Have authorized people create the support and platform-admin accounts, enroll MFA without sharing seeds/recovery codes, and verify the public support inbox end to end.
5. Obtain legal approval for the four-locale policy drafts and product-owner acceptance for visitor, member, club owner/admin, independent organizer, and platform-admin journeys.
6. Launch only through controlled invitations, monitor the defined bounded metrics and alerts, then record the 48-hour go/no-go decision and rollback triggers.

Only after all six items pass may the Task 6.8 checklist be completed and an approved release-candidate tag be created.
