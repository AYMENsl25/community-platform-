from __future__ import annotations

import json
from pathlib import Path

import pytest
from talaqi.main import create_app
from talaqi.platform.openapi import (
    OpenApiDriftError,
    build_openapi_document,
    render_openapi_document,
    write_openapi,
)


def test_openapi_document_is_byte_deterministic_and_contains_locked_components() -> None:
    first = render_openapi_document(build_openapi_document(create_app()))
    second = render_openapi_document(build_openapi_document(create_app()))

    assert first == second
    assert first.endswith(b"\n")
    document = json.loads(first)
    assert document["paths"]["/health/live"]["get"]["operationId"] == "healthLive"
    assert document["paths"]["/health/ready"]["get"]["operationId"] == "healthReady"
    schemas = document["components"]["schemas"]
    assert {"FieldError", "ErrorEnvelope", "CursorPage"}.issubset(schemas)
    assert schemas["ErrorEnvelope"]["properties"]["error"]["$ref"] == (
        "#/components/schemas/ErrorDetail"
    )
    assert schemas["CursorPage"]["required"] == ["items", "next_cursor"]
    headers = document["components"]["headers"]
    assert headers["RequestId"]["schema"] == {"type": "string", "format": "uuid"}
    assert headers["IdempotencyKey"]["schema"] == {
        "type": "string",
        "minLength": 16,
        "maxLength": 200,
    }
    for path in ("/health/live", "/health/ready"):
        success = document["paths"][path]["get"]["responses"]["200"]
        assert success["headers"]["X-Request-ID"] == {"$ref": "#/components/headers/RequestId"}

    readiness_responses = document["paths"]["/health/ready"]["get"]["responses"]
    assert set(readiness_responses) == {"200", "503"}
    unavailable = readiness_responses["503"]
    assert unavailable["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ReadyResponse"
    }
    assert unavailable["headers"]["X-Request-ID"] == {"$ref": "#/components/headers/RequestId"}


def test_openapi_contains_no_environment_secret_path_or_generation_metadata() -> None:
    rendered = render_openapi_document(build_openapi_document(create_app())).decode("utf-8")

    for forbidden in (
        "postgresql://",
        "password",
        "smtp_",
        "s3_secret",
        "C:\\\\Users",
        "/home/",
        "generated_at",
        "generation_timestamp",
    ):
        assert forbidden not in rendered


def test_openapi_check_detects_drift_without_rewriting(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"
    document = build_openapi_document(create_app())
    write_openapi(document, output=output, check=False)
    expected = output.read_bytes()

    write_openapi(document, output=output, check=True)
    output.write_bytes(b"{}\n")
    with pytest.raises(OpenApiDriftError, match="out of date"):
        write_openapi(document, output=output, check=True)

    assert output.read_bytes() == b"{}\n"
    assert expected != output.read_bytes()
