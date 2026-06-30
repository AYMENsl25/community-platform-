# Frontend Integration

The web app currently uses a small fetch wrapper in `apps/web/lib/api.ts` and backend adapters in `apps/web/lib/backend-events.ts` and `apps/web/lib/backend-clubs.ts`.

## API Base URL

Set:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## Error Handling

The API returns:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Event not found",
    "request_id": "req_123"
  }
}
```

The web fetch wrapper reads `error.message` when present and falls back to HTTP status text.

## Generated Client Path

Once the backend contract stabilizes, generate types from OpenAPI:

```powershell
cd apps/web
pnpm dlx openapi-typescript http://127.0.0.1:8000/openapi.json -o ../../packages/api-client/src/schema.ts
```

Recommended next package:

```text
packages/api-client/
  package.json
  src/
    schema.ts
    client.ts
```

The generated client should replace manual duplicate API types in `apps/web/lib/backend-events.ts`.

## E2E Coverage

Add Playwright when authenticated flows are wired to Clerk:

- Explore page loads API events.
- Event detail renders from the API.
- Register/save actions handle loading, success, and errors.
- Organizer event creation handles validation errors.
- CORS/auth failures display actionable UI.
