# Restore a Talaqi backup

1. Declare the incident, freeze deploys, record the suspected failure time, and select the newest encrypted backup before that time.
2. Never restore over production. Run `Restore rehearsal` into `talaqi_restore_test`; verify the manifest before decryption and keep plaintext only on the isolated runner.
3. Require `pg_restore --exit-on-error`, one Alembic revision at the expected head, row-count checks for users/events/registrations/audit/outbox, and sampled media checksum/read tests.
4. Record start/end time, recovery point, recovery duration, backup/workflow IDs, checksums, and discrepancies without copying personal data.
5. Promote a restored database only through an approved provider cutover. Rotate backup credentials after suspected compromise and securely remove plaintext artifacts.

Stop if the manifest differs, decryption fails, the target is not isolated, schema head differs, sampled media fails, or authorization to cut over is absent.
