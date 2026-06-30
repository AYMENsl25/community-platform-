# ADR 0003: Use Clerk For Authentication

## Status

Accepted

## Context

The product needs social login and session management without owning password storage. Google login is required, but storing passwords or implementing OAuth directly in FastAPI would add avoidable risk.

## Decision

Use Clerk for authentication and Google OAuth. FastAPI verifies Clerk JWTs and maps authenticated identities into local users.

## Consequences

- FastAPI never stores passwords.
- The frontend obtains Clerk sessions and sends bearer tokens to the API.
- The API must validate issuer, JWKS signature, expiration, audience when configured, and authorized party.
- Local development can use a development-only email header shortcut.
