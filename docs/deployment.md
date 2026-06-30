# Deployment

## API Image

Build from the API directory:

```powershell
cd apps/api
docker build -t communiti-api .
```

Runtime command:

```text
python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
```

## Environment

Production should set:

- `ENVIRONMENT=production`
- `DATABASE_URL`
- `ALLOWED_ORIGINS`
- `TRUSTED_HOSTS`
- `CLERK_ISSUER`
- `CLERK_AUDIENCE`
- `CLERK_AUTHORIZED_PARTIES`
- `RATE_LIMIT_ENABLED=true`
- `RATE_LIMIT_REQUESTS_PER_MINUTE`

## Migrations

Alembic is configured in `apps/api/alembic.ini`.

For a new database:

```powershell
cd apps/api
python -m alembic -c alembic.ini upgrade head
```

For an existing database created from `database/communiti_schema.sql`, stamp the baseline revision once:

```powershell
cd apps/api
python -m alembic -c alembic.ini stamp 0001_baseline
```

Future schema changes should be added as new Alembic revisions.

## Health Checks

- `GET /health` confirms the API process is running.
- `GET /api/v1/health/db` confirms database connectivity.

## Production Checklist

- Apply migrations before serving traffic.
- Use managed PostgreSQL with automated backups.
- Configure exact CORS origins and trusted hosts.
- Store secrets in the deployment platform.
- Enable HTTPS only.
- Confirm `/health` and `/api/v1/health/db` pass after deploy.
- Run dependency vulnerability scanning in CI.
- Rehearse restore from backup before onboarding real users.
