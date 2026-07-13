# ADR 0002: First-party cookie authentication

- Status: Accepted
- Date: 2026-07-11

## Decision

Use email/password accounts with Argon2id, verification, single-use expiring reset tokens, HttpOnly Secure SameSite=Lax access/refresh cookies, rotating refresh sessions with replay-family revocation, and CSRF protection on cookie-authenticated mutations. Every mutation also requires server authentication and object authorization. Platform-admin production actions require MFA.

## Consequences

Production fails closed for weak secrets, insecure cookies, wildcard origins/hosts, non-HTTPS public URLs, unavailable migrations, or missing admin MFA enforcement. Tokens and credentials are never logged. Google OAuth remains deferred unless credentials and exact redirect URLs are approved.
