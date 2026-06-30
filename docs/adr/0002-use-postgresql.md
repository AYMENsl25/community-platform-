# ADR 0002: Use PostgreSQL As The Source Of Truth

## Status

Accepted

## Context

COMMUNITI needs relational integrity for users, clubs, memberships, events, registrations, saved events, notifications, organizer requests, and later search documents.

## Decision

Use PostgreSQL as the primary application database.

## Consequences

- The data model can enforce relational constraints and transactional write flows.
- Registration and waitlist operations can use database functions where concurrency matters.
- Local development needs repeatable schema setup and migration tooling.
- The next database hardening step is Alembic-based migrations.
