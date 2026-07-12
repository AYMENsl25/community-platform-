# Talaqi PostgreSQL bootstrap

This directory contains the one-time PostgreSQL 18 baseline for Talaqi's closed-beta MVP.

## Requirements

- PostgreSQL 18.4 or a newer security-patched PostgreSQL 18 minor release.
- An empty database whose connected owner may create a schema, types, functions, tables, triggers, and indexes.
- `psql` configured with TLS for any remote database.

## Local PostgreSQL 18

The root `compose.yaml` is the development service contract. Copy `.env.example` to `.env`, replace the conspicuous local-only password placeholder, validate the resolved configuration, and start the named-volume service:

```powershell
Copy-Item .env.example .env
docker compose config
docker compose up -d --wait postgres
docker compose ps
```

The database and user are both `talaqi`, and port 5432 is published only on `127.0.0.1`. Stop the service with `docker compose down`; add `--volumes` only when you intentionally want to destroy local data. Never reuse local compose credentials in staging or production.

## Apply and verify with pgAdmin

1. In pgAdmin, expand **Servers**, connect to a PostgreSQL 18 server, and enter the server password when requested.
2. Right-click **Databases**, choose **Create > Database**, set **Database** to `talaqi`, keep your administrative login as **Owner**, and select **Save**.
3. Select the new `talaqi` database. Open **Tools > Query Tool**.
4. Select **Open File** (`Ctrl+O`) and open `database/bootstrap.sql` from this project folder.
5. Do not highlight only part of the file. Select **Execute Script** or press `F5` so the complete transaction runs.
6. Confirm the **Messages** panel contains `COMMIT` and no error. Refresh **Databases > talaqi > Schemas**; the `talaqi` schema should appear.
7. Open a new Query Tool tab on the same database, open `database/tests/schema_contract.sql`, and press `F5`.
8. Confirm **Data Output** returns `passed = true` and `Talaqi schema contract passed.`.

If execution reports an error, do not run the remaining statements individually. Select **Rollback** in Query Tool (or run `ROLLBACK;`), save the complete error text, and fix the cause before retrying the full bootstrap on an empty database.

## Apply and verify with psql

Set the connection URL in your shell without placing credentials in command history or files. For PowerShell:

```powershell
$env:DATABASE_URL = Read-Host 'PostgreSQL URL'
psql "$env:DATABASE_URL" -v ON_ERROR_STOP=1 -f database/bootstrap.sql
psql "$env:DATABASE_URL" -v ON_ERROR_STOP=1 -f database/tests/schema_contract.sql
Remove-Item Env:DATABASE_URL
```

Expected final test output:

```text
 passed | message
--------+---------------------------------------
 t      | Talaqi schema contract passed.
```

The script runs in one transaction and is intentionally one-time-only. Do not rerun it on an initialized database. After the application repository is created, stamp this baseline into Alembic and make every later change through a new reviewed migration.

## Application-role grants

The bootstrap creates no login role and grants nothing to `PUBLIC`. Create the application and migration roles using your database provider's secret-management interface, then grant only the privileges each runtime needs. Do not paste provider passwords into GitHub, `.env.example`, issues, or chat.

The FastAPI service remains responsible for object-level authorization. Do not expose these tables directly through a public database REST API. If a provider automatically exposes schemas, expose only `public` and keep `talaqi` private.
