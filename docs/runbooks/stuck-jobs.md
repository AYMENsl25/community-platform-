# Recover stuck jobs

1. Check oldest pending age, lease owner/expiry, failure class, aggregate ordering, and worker health using bounded IDs; do not inspect private payload bodies in shared channels.
2. Restart a worker and confirm expired leases are reacquired. A stale worker must not complete or fail a job after another worker owns the exact lease token.
3. Use the MFA-protected single-event retry action only for permanent/dead-letter items after correcting the cause. Never bulk retry or directly alter registration state.
4. Verify deduplication, downstream provider ID, transition invariants, queue-age recovery, and alert clearance; record event type, safe error class, operator, reason, and times.

Escalate invariant violations, repeated security-email failure, or registration-order anomalies immediately.
