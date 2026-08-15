# Phase 6 deployment rehearsal

**Review date:** 2026-08-15

**Branch:** `phase-6/operational-hardening`

## Verified locally

- Preview workflow uses a disposable PostgreSQL 18 database, receives no deployment secrets, applies migrations, runs readiness/deployment tests, builds the web application, and checks OpenAPI drift.
- Guarded release workflow accepts only an exact commit SHA and a protected `staging` or `production` GitHub environment.
- One release job runs `alembic upgrade head` once before API, worker, and web deploy hooks for the same SHA.
- Rollback redeploys the previous application SHA and never downgrades the production schema.
- Clean upgrade, previous-schema forward migration, downgrade/re-upgrade compatibility, one-head validation, readiness failure, workflow isolation, and release-contract tests passed: 17 tests.

## External staging gate

The repository currently has no GitHub `staging` or `production` environments. No Render/Neon/R2/Resend credentials or deploy hooks were supplied, so an actual staging deployment, provider secret-isolation inspection, remote smoke/E2E run, and application rollback were not executed. Create protected environments, add required reviewers and environment-scoped secrets/variables, provision paid non-expiring services, and run `Guarded deployment` against staging before release-candidate approval.

Required environment variables: `API_PUBLIC_URL` and `WEB_PUBLIC_URL`. Required secrets: `DATABASE_URL`, `API_DEPLOY_HOOK`, `WORKER_DEPLOY_HOOK`, and `WEB_DEPLOY_HOOK`. Record the workflow URL, immutable release/previous SHAs, migration revision, smoke result, rollback timing, and provider screenshots without copying secret values.
