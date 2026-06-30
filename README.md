# COMMUNITI

COMMUNITI is a community clubs SaaS with a FastAPI backend, PostgreSQL database, and Next.js frontend.

## Project Structure

- `apps/api` - FastAPI backend.
- `apps/web` - Next.js frontend.
- `database` - PostgreSQL schema and migrations.
- `BACKEND_FASTAPI_PLAN.md` - backend execution plan.
- `COMMUNITI_PROMPT.md` - original product prompt/reference.

## Local Development

Backend:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd apps/web
pnpm dev
```

The frontend expects the API at `http://127.0.0.1:8000/api/v1` by default.
