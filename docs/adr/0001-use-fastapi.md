# ADR 0001: Use FastAPI For The Backend

## Status

Accepted

## Context

COMMUNITI needs a typed HTTP API, OpenAPI documentation, async database access, and room for Python-based AI/search workflows.

## Decision

Use FastAPI for the backend in `apps/api`.

## Consequences

- The API can expose OpenAPI docs and a future generated TypeScript client.
- Python remains available for embeddings, recommendations, and LLM evaluation work.
- The project must add production pieces deliberately: migrations, background workers, observability, rate limits, and deployment packaging.
