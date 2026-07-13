# Contributing

Use the locked Node 24/pnpm 10.34.5 and Python 3.13/uv 0.11.28 toolchains. Start from a short-lived branch, keep one bounded task per commit, and preserve the module and security contracts in `AGENTS.md`.

Install dependencies and enable the local hook:

```text
corepack pnpm install --frozen-lockfile
python -m uv sync --frozen
python -m uv run pre-commit install
```

Before review, run `python -m uv run pre-commit run --all-files` plus the affected root gates in the README. Never bypass a high/critical dependency finding or add a real credential to `.secrets.baseline`. See `docs/engineering/ci-security.md` for job mapping, branch-protection setup, caches, scan response, and remediation policy.
