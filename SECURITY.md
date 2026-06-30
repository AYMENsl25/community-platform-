# Security Policy

## Supported Branch

Security fixes should target `main`.

## Reporting

Do not open public issues for suspected vulnerabilities involving secrets, authentication, authorization, user data, or infrastructure access. Share the report privately with the repository owner.

Include:

- Affected endpoint, package, or workflow.
- Reproduction steps.
- Expected impact.
- Any relevant request IDs or logs with secrets removed.

## Local Safety Rules

- Never commit `.env` files, tokens, passwords, JWTs, or provider credentials.
- Use Clerk for identity and Google OAuth.
- Keep production CORS origins and trusted hosts explicit.
- Rotate secrets after accidental exposure.
