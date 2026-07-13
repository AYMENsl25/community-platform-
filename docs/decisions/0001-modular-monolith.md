# ADR 0001: Modular monolith

- Status: Accepted
- Date: 2026-07-11

## Decision

Use one monorepo with a Next.js PWA, FastAPI modular monolith, PostgreSQL-backed worker, generated TypeScript API client, shared UI, and translations. Modules deploy together but communicate through explicit public service interfaces. Routers call only their own service; services may call another module's public service interface but never its repository.

PostgreSQL is authoritative for transactions and invariants. External providers use replaceable adapters. Microservices, Kubernetes, Kafka, Elasticsearch, and a required Redis dependency are outside the MVP.

## Consequences

The design supports one developer coordinating bounded agents without distributed-system overhead. Module ownership and tests must remain explicit. Redis or service extraction requires measured need and a new ADR.
