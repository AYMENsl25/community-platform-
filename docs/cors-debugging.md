# CORS Debugging

COMMUNITI runs the web app and API on different local origins:

- Web: `http://localhost:3000` or `http://127.0.0.1:3000`
- API: `http://127.0.0.1:8000`

## Configuration

Set allowed origins in `apps/api/.env`:

```text
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

In development, the API also allows localhost or 127.0.0.1 with any port through a regex so alternate Next.js ports work during local testing.

## Checklist

- Use the same host consistently. `localhost` and `127.0.0.1` are different origins.
- Include the exact scheme: `http` and `https` are different origins.
- Include the exact port.
- Do not use `*` when credentials or authorization headers are involved.
- Confirm preflight `OPTIONS` requests include the expected headers.
- Confirm frontend requests send `Authorization` only when the token exists.

## Allowed Headers

The API currently allows:

- `Authorization`
- `Content-Type`
- `X-Request-ID`
- `X-Communiti-User-Email`

`X-Communiti-User-Email` is for development only.
