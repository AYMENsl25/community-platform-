# COMMUNITI Security Notes

## Authentication

Clerk owns identity and Google OAuth. FastAPI verifies Clerk JWTs on protected requests and maps the identity into the local `users` table.

Protected API requests use:

```text
Authorization: Bearer <clerk_jwt>
```

The backend validates:

- JWT signature through Clerk JWKS.
- Token issuer.
- Token audience when configured.
- Authorized party (`azp`) against allowed frontend origins.
- Subject and email claims before local user upsert.

## Development Auth Shortcut

When `ENVIRONMENT=development`, the API can read `X-Communiti-User-Email` for local testing without a real Clerk token. Do not enable this in production.

## Authorization

Object-level authorization belongs in services and policies, not only in routers.

Current rules include:

- Users can access only their own `/me/*` data.
- Club owners, club admins, and platform admins can manage clubs.
- Event management follows club management permissions.
- Organizer approval is required before creating clubs unless the user is a platform admin.
- Admin organizer-review routes require `platform_role=admin`.

## Secrets

- Never commit `.env`, `.env.*`, JWTs, database passwords, or provider tokens.
- Store production secrets in the deployment platform.
- Prefer `DB_*` fields locally to avoid URL-encoding database passwords.
- Do not log raw JWTs, secrets, or sensitive user data.

## Remaining Security Work

- Add rate limiting.
- Add trusted host middleware for production.
- Standardize error responses without leaking internals.
- Add dependency vulnerability scanning.
- Add audit logging for organizer/admin writes.
- Add backup/restore and secret rotation runbooks.
