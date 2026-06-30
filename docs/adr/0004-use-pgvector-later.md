# ADR 0004: Add pgvector After The Relational MVP

## Status

Accepted

## Context

COMMUNITI will need semantic event search, personalized recommendations, and AI-assisted discovery. The dataset is small during MVP development, and local/deployment environments may not have pgvector ready immediately.

## Decision

Start with relational/public search and add pgvector after the core API and deployment path are stable.

## Consequences

- The current search implementation can ship without blocking on vector infrastructure.
- Future migrations should introduce search documents, embedding metadata, permission-aware retrieval, and vector indexes.
- AI features must filter retrieved content by permissions before model calls.
- Prompt, cost, privacy, and evaluation controls are required before LLM features perform user-facing actions.
