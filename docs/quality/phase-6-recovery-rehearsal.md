# Phase 6 recovery and lifecycle rehearsal

**Review date:** 2026-08-15

## Verified repository scope

- Scheduled/manual backup workflow creates a custom PostgreSQL dump, encrypts it with AES-256 before upload, removes plaintext, creates a SHA-256 manifest, and uploads encrypted artifacts with server-side encryption.
- Manual restore workflow downloads into an isolated PostgreSQL 18 `talaqi_restore_test` service, verifies checksums before decrypting, uses `pg_restore --exit-on-error`, checks the Alembic revision, and removes plaintext artifacts.
- Account deletion is CSRF-protected, revokes active sessions, permits recovery for 30 days, then anonymizes email/profile identity and removes authentication/MFA credentials while retaining immutable records.
- Expired authentication tokens and revoked/expired sessions have bounded cleanup behavior.
- Restore, stuck-job, failed-migration, account-recovery, data-rights, and compromised-admin runbooks define safe stop/escalation conditions.
- Lifecycle/identity/operations gate: 154 tests passed; Ruff, Pyright, and OpenAPI/client drift passed.

## External restore gate

GitHub `production-backup` and `staging-restore` environments were created on 2026-08-15, but they contain no provider-scoped backup variables or secrets. A representative provider backup download, sampled media restore, database/media checksum comparison, and measured recovery time were not executed. Configure least-privilege write-only backup and read-only restore credentials, run both workflows, and attach redacted workflow/provider evidence before Task 6.8 approval.
