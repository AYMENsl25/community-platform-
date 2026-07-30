from __future__ import annotations

from typing import cast

from talaqi.main import create_app


def test_discovery_openapi_is_connection_free_and_complete() -> None:
    document = create_app().openapi()

    expected = {
        "/api/v1/events": {"get"},
        "/api/v1/events/{event_id}": {"get"},
        "/api/v1/events/{event_id}/saved": {"put", "delete"},
        "/api/v1/clubs": {"get", "post"},
        "/api/v1/clubs/{club_id}": {"get", "patch"},
        "/api/v1/clubs/{club_id}/join": {"post"},
        "/api/v1/clubs/{club_id}/membership": {"delete"},
        "/api/v1/clubs/{club_id}/members": {"get"},
        "/api/v1/clubs/{club_id}/join-requests": {"get"},
        "/api/v1/clubs/{club_id}/join-requests/{join_request_id}/approve": {"post"},
        "/api/v1/clubs/{club_id}/join-requests/{join_request_id}/reject": {"post"},
        "/api/v1/clubs/{club_id}/members/{user_id}/role": {"patch"},
        "/api/v1/clubs/{club_id}/ownership-transfer": {"post"},
        "/api/v1/clubs/{club_id}/close": {"post"},
        "/api/v1/clubs/{slug}": {"get"},
        "/api/v1/search": {"get"},
        "/api/v1/metadata": {"get"},
        "/api/v1/me/saved-events": {"get"},
    }
    for path, methods in expected.items():
        assert methods.issubset(document["paths"][path])


def _schema_names(value: object) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        mapping = cast(dict[str, object], value)
        reference = mapping.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/components/schemas/"):
            names.add(reference.rsplit("/", maxsplit=1)[-1])
        for nested in mapping.values():
            names.update(_schema_names(nested))
    elif isinstance(value, list):
        for nested in cast(list[object], value):
            names.update(_schema_names(nested))
    return names


def test_public_discovery_schemas_have_no_private_venue_or_identity_fields() -> None:
    document = create_app().openapi()
    schemas = cast(dict[str, object], document["components"]["schemas"])
    public_operations = (
        ("/api/v1/events", "get"),
        ("/api/v1/events/{event_id}", "get"),
        ("/api/v1/clubs", "get"),
        ("/api/v1/clubs/{slug}", "get"),
        ("/api/v1/search", "get"),
        ("/api/v1/metadata", "get"),
    )
    pending: set[str] = set()
    for path, method in public_operations:
        pending.update(_schema_names(document["paths"][path][method]["responses"]))
    reachable: dict[str, object] = {}
    while pending:
        name = pending.pop()
        if name in reachable:
            continue
        schema = schemas[name]
        reachable[name] = schema
        pending.update(_schema_names(schema))
    rendered = repr(reachable).casefold()

    for forbidden in (
        "exact_address",
        "latitude",
        "longitude",
        "owner_user_id",
        "email",
        "invite_token",
        "attendee",
        "featured_score",
    ):
        assert forbidden not in rendered


def test_saved_mutations_document_auth_csrf_and_not_found_failures() -> None:
    paths = create_app().openapi()["paths"]

    for method in ("put", "delete"):
        responses = paths["/api/v1/events/{event_id}/saved"][method]["responses"]
        assert {"204", "401", "403", "404"}.issubset(responses)
