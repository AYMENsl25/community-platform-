# ADR 0003: PostgreSQL transactional outbox

- Status: Accepted
- Date: 2026-07-11

## Decision

Commit business state and outbox records in the same PostgreSQL transaction. A worker claims records with safe leases, performs delivery or scheduled work, records results, and retries with bounded backoff. PostgreSQL also protects capacity, idempotency, immutable history, expiry, and FIFO promotion.

## Consequences

Redis is not required for the first beta. It may be added by ADR when distributed rate limits, queue lag, throughput, or lock contention cross agreed thresholds. Worker restart and recovery must be rehearsed, and operational tooling must support safe retry without direct registration-state overrides.
