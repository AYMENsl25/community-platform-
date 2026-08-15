# CI and security operations

Talaqi's foundation gates are deterministic, fail closed, and use the repository lockfiles as the source of truth. Use Node 24, pnpm 10.34.5, Python 3.13, and uv 0.11.28. Install with:

```text
corepack pnpm install --frozen-lockfile
python -m uv sync --frozen
```

## Local gates

Run the same fast checks used by CI with `python -m uv run pre-commit run --all-files`. The local hooks use only `language: system` commands from the locked workspace: text/YAML safety, Ruff format and lint, Prettier, and detect-secrets. Before opening a pull request, also run the root format, lint, typecheck, test, build, OpenAPI drift, brand, audit, and Playwright commands documented in the README.

The detect-secrets baseline contains reviewed false positives from test-only placeholder credentials and immutable checksum fixtures. It contains hashes, never source values. New source, tests, workflows, and documentation are scanned; lockfiles, binary/generated brand assets, and ignored local environment files are the only excluded categories.

## Required checks and path mapping

- `changes` calculates a merge-base-to-head diff. A missing or invalid base, a zero SHA, or any classifier error enables every class.
- `web` covers the web app, shared UI/translations/config, JavaScript root configuration, and brand tooling.
- `api` covers API and worker Python; `contract` conservatively includes API routes/OpenAPI and the generated client.
- `migration` covers Alembic, database assets/tests, and API persistence code, using PostgreSQL 18 on an explicit loopback-only runner port.
- `security` covers executable source plus workflows, manifests, lockfiles, pre-commit, classifier, and security tests/documentation.
- `playwright` always runs on pull requests targeting `main` and pushes to `main`. It builds and starts the production web app, installs Chromium only, and tests the foundation heading, first-focus skip link, main target, and 320-pixel overflow.

Branch protection should require `changes`, `web`, `api`, `contract`, `migration`, `security`, `playwright`, and the CodeQL analysis checks appropriate to the repository policy. Skipped changed-file-aware jobs may need GitHub rules configured to accept their skipped conclusion. Branch protection itself must be enabled in GitHub repository settings; repository code cannot claim or silently configure it.

## Cache and scan policy

CI caches only the pnpm content-addressed store and uv download/build cache, keyed by runtime and the relevant lockfile. It never caches build output, Next.js output, browser binaries/reports, test results, databases, virtual environments, credentials, or generated API clients.

High or critical dependency findings block. There are no high/critical exceptions or suppressions. Moderate findings do not silently disappear: open a tracked remediation item with owner, affected component, compensating control, and due date. Dependency remediation updates the direct or transitive pin through pnpm/uv, regenerates only the relevant lockfile, and reruns all affected gates. Dependency Review applies to pull requests, pnpm audits production packages at `high`, and pip-audit scans exported locked production requirements.

Resolved finding: `GHSA-qx2v-qp2m-jg93` / `CVE-2026-41305` (PostCSS style-output XSS). The workspace override now resolves `next@16.2.10` to `postcss@8.5.23`, above the patched `8.5.10` floor. On 2026-08-15, `corepack pnpm audit --prod --audit-level high` and the exported-lock `pip-audit` gate both reported no known vulnerabilities. Keep the override until a locked stable Next.js release supplies an equal or newer transitive version, and reject any lockfile change that regresses below the patched floor.

If a secret is detected, stop the change, do not add it to the baseline, revoke/rotate the credential through its owning system, remove it from the working tree and history as appropriate, notify the security owner, and audit access. Add a baseline entry only for a reviewed non-secret false positive and document why it cannot use an inline allowlist marker.

Ruff's security rules scan production Python and repository scripts; CodeQL scans JavaScript/TypeScript and Python with minimal permissions. CI action references are immutable reviewed SHAs. Dependabot proposes weekly npm, pip, and GitHub Actions updates.

## Runtime boundary

Security settings are resolved and frozen on the first request, never during import, app construction, middleware-stack creation, or OpenAPI generation. Production alone emits HSTS. Safe request logs contain only timestamp, event, method, matched route template, status, bounded duration, server request ID, and level.

The in-memory rate limiter is for development and test only. Staging and production must inject a durable provider adapter; startup/runtime configuration fails closed when one is absent. This foundation intentionally does not attach a global or endpoint-specific policy.
