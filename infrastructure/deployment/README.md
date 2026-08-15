# Deployment infrastructure

## Selected portable beta stack

Verified on 2026-08-15 from official provider documentation:

- Paid Render web services/background worker for Next.js, FastAPI, and workers. Render free instances are preview-only: they spin down, have ephemeral files, and are explicitly not for production. Render preview environments require Pro and are billed per resource.
- Neon Launch PostgreSQL for production; a Free project may be used only for disposable development. The Free plan currently provides 0.5 GB storage, 100 CU-hours, and a six-hour restore window; Launch provides a seven-day restore window.
- Cloudflare R2 Standard behind the existing S3 adapter. The current monthly free allowance is 10 GB-month, one million Class A operations, ten million Class B operations, and free direct egress; production billing alerts remain mandatory.
- Resend transactional API behind `ProductionEmailProvider`. The current free plan allows 3,000 messages/month and 100/day; exceeding beta needs a paid plan because free has no overage.
- Provider-neutral JSON logs/metrics and alert contracts remain portable. Select the final monitoring sink only after staging verifies ingestion, alert delivery, retention, region, and deletion controls.

Sources: <https://render.com/docs/free>, <https://render.com/docs/preview-environments>, <https://render.com/docs/deploys>, <https://neon.com/pricing>, <https://developers.cloudflare.com/r2/pricing/>, and <https://resend.com/docs/knowledge-base/what-is-resend-pricing>.

Free/student offers are cost aids, not release controls. Production must use paid, non-expiring services with backups and a spend cap. GitHub Education eligibility is personal and must not be assumed by repository automation.

## Pipeline contract

`preview.yml` builds against a disposable PostgreSQL 18 database without repository or deployment secrets. `deploy.yml` is manual and binds to a protected `staging` or `production` GitHub environment. Configure required reviewers for production in GitHub before launch.

The release job checks out one immutable SHA, validates public HTTPS endpoints, runs `alembic upgrade head` exactly once, triggers API/worker/web deploy hooks for the same SHA, then requires liveness/readiness smoke success. Secrets exist only in protected environment secrets and are never copied to preview jobs.

Migrations use expand/migrate/contract changes. A failed application release redeploys the previous application SHA; it never runs `alembic downgrade` in production. Contract/removal migrations require a later release after old application versions are retired and restore evidence exists.
