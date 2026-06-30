# COMMUNITI API

Base path: `/api/v1`

Interactive docs are available at `/docs` when the API is running locally.

## Public Endpoints

- `GET /health` - process health check outside the versioned API prefix.
- `GET /api/v1/health/db` - database readiness check.
- `GET /api/v1/meta/categories` - list event/category metadata.
- `GET /api/v1/meta/tags` - list tag metadata.
- `GET /api/v1/clubs` - list public clubs with pagination and filters.
- `GET /api/v1/clubs/{slug}` - fetch a public club detail.
- `GET /api/v1/events` - list public events with pagination and filters.
- `GET /api/v1/events/{event_id}` - fetch public event detail.
- `GET /api/v1/events/{event_id}/capacity` - fetch event capacity state.
- `GET /api/v1/search` - search public content.

## Authenticated Endpoints

Authenticated requests should include:

```text
Authorization: Bearer <clerk_jwt>
```

Local development can use `X-Communiti-User-Email` only when `ENVIRONMENT=development`.

- `GET /api/v1/auth/me`
- `GET /api/v1/me/profile`
- `PATCH /api/v1/me/profile`
- `GET /api/v1/me/preferences`
- `PATCH /api/v1/me/preferences`
- `GET /api/v1/me/clubs`
- `GET /api/v1/me/events`
- `GET /api/v1/me/registrations`
- `GET /api/v1/me/saved-events`
- `GET /api/v1/me/notifications`
- `PATCH /api/v1/me/notifications/read-all`
- `PATCH /api/v1/me/notifications/{notification_id}/read`
- `GET /api/v1/me/organizer-request`
- `POST /api/v1/me/organizer-request`
- `POST /api/v1/clubs`
- `PATCH /api/v1/clubs/{club_id}`
- `DELETE /api/v1/clubs/{club_id}`
- `POST /api/v1/clubs/{club_id}/join`
- `POST /api/v1/clubs/{club_id}/leave`
- `POST /api/v1/events`
- `PATCH /api/v1/events/{event_id}`
- `DELETE /api/v1/events/{event_id}`
- `POST /api/v1/events/{event_id}/register`
- `POST /api/v1/events/{event_id}/cancel-registration`
- `POST /api/v1/events/{event_id}/save`
- `DELETE /api/v1/events/{event_id}/save`
- `POST /api/v1/recommendations/events`

## Admin Endpoints

- `GET /api/v1/admin/organizer-requests`
- `POST /api/v1/admin/organizer-requests/{request_id}/approve`
- `POST /api/v1/admin/organizer-requests/{request_id}/reject`

## Error Shape

API errors use a standard object shape:

```json
{
  "error": {
    "code": "EVENT_FULL",
    "message": "The event is full.",
    "request_id": "req_123"
  }
}
```

Validation errors include an additional `details` field with FastAPI validation details. Clients should display `error.message` and may log `error.code` plus `error.request_id`.
