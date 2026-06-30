# COMMUNITI API Client

This package is reserved for the generated TypeScript client from FastAPI OpenAPI.

Generate the schema from a running local API:

```powershell
cd apps/web
pnpm dlx openapi-typescript http://127.0.0.1:8000/openapi.json -o ../../packages/api-client/src/schema.ts
```

The package should stay generated-contract-first. Handwritten helpers can live beside generated types, but route and schema types should come from OpenAPI.
