from __future__ import annotations

from talaqi.main import create_app


def test_discovery_openapi_is_connection_free_and_complete() -> None:
    document = create_app().openapi()

    expected = {
        "/api/v1/events": {"get"},
        "/api/v1/events/{event_id}": {"get"},
        "/api/v1/events/{event_id}/saved": {"put", "delete"},
        "/api/v1/clubs": {"get", "post"},
        "/api/v1/clubs/{club_id}": {"get", "patch"},
        "/api/v1/clubs/{slug}": {"get"},
        "/api/v1/search": {"get"},
        "/api/v1/metadata": {"get"},
        "/api/v1/me/saved-events": {"get"},
    }
    for path, methods in expected.items():
        assert set(document["paths"][path]) == methods


def test_public_discovery_schemas_have_no_private_venue_or_identity_fields() -> None:
    schemas = create_app().openapi()["components"]["schemas"]
    rendered = repr(
        {
            name: value
            for name, value in schemas.items()
            if name.startswith(("Event", "Club", "Search"))
        }
    ).casefold()

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
