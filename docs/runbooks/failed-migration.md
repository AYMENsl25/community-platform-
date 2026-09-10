# Recover a failed migration

1. Stop the release before new application instances start and retain the failed job logs with secrets redacted.
2. Determine whether the transaction rolled back. Check Alembic revision and schema facts read-only; never guess or edit `alembic_version` manually.
3. For an expand/migrate failure, fix forward and rerun the single release job. Redeploy the previous application SHA if it remains compatible; do not downgrade production automatically.
4. If data correctness is uncertain, freeze writes and follow the restore runbook into an isolated target before any cutover decision.
5. Record cause, affected revisions, application SHAs, commands, timing, verification, and prevention action.
