from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


class OpenApiDriftError(RuntimeError):
    pass


def build_openapi_document(application: FastAPI) -> dict[str, Any]:
    document = get_openapi(
        title=application.title,
        version="1.0.0",
        openapi_version=application.openapi_version,
        description=application.description,
        routes=application.routes,
    )
    components = cast(dict[str, Any], document.setdefault("components", {}))
    schemas = cast(dict[str, Any], components.setdefault("schemas", {}))
    schemas.update(_platform_schemas())
    components["headers"] = _platform_headers()
    components["responses"] = {
        "PlatformError": {
            "description": "A stable Talaqi platform error envelope.",
            "headers": {"X-Request-ID": {"$ref": "#/components/headers/RequestId"}},
            "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}
            },
        }
    }
    _add_request_id_response_headers(document)
    return document


def render_openapi_document(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, separators=(",", ": "))
        + "\n"
    ).encode("utf-8")


def write_openapi(document: dict[str, Any], *, output: Path, check: bool) -> None:
    rendered = render_openapi_document(document)
    if check:
        if not output.is_file() or output.read_bytes() != rendered:
            raise OpenApiDriftError("checked-in OpenAPI document is out of date")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rendered)


def install_openapi(application: FastAPI) -> None:
    def custom_openapi() -> dict[str, Any]:
        if application.openapi_schema is None:
            application.openapi_schema = build_openapi_document(application)
        return application.openapi_schema

    application.openapi = custom_openapi  # pyright: ignore[reportAttributeAccessIssue,reportAssignmentType]


def _platform_schemas() -> dict[str, Any]:
    return {
        "CursorPage": {
            "additionalProperties": False,
            "properties": {
                "items": {"items": {}, "type": "array"},
                "next_cursor": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                },
            },
            "required": ["items", "next_cursor"],
            "title": "CursorPage",
            "type": "object",
        },
        "ErrorDetail": {
            "additionalProperties": False,
            "properties": {
                "code": {"type": "string"},
                "message_key": {"type": "string"},
                "field_errors": {
                    "items": {"$ref": "#/components/schemas/FieldError"},
                    "type": "array",
                },
                "request_id": {"format": "uuid", "type": "string"},
            },
            "required": ["code", "message_key", "field_errors", "request_id"],
            "title": "ErrorDetail",
            "type": "object",
        },
        "ErrorEnvelope": {
            "additionalProperties": False,
            "properties": {
                "error": {"$ref": "#/components/schemas/ErrorDetail"},
            },
            "required": ["error"],
            "title": "ErrorEnvelope",
            "type": "object",
        },
        "FieldError": {
            "additionalProperties": False,
            "properties": {
                "field": {"type": "string"},
                "code": {"type": "string"},
                "message_key": {"type": "string"},
            },
            "required": ["field", "code", "message_key"],
            "title": "FieldError",
            "type": "object",
        },
    }


def _platform_headers() -> dict[str, Any]:
    return {
        "IdempotencyKey": {
            "description": "Required on retryable mutation operations.",
            "required": True,
            "schema": {"type": "string", "minLength": 16, "maxLength": 200},
        },
        "RequestId": {
            "description": "A server-owned UUIDv7 request identifier.",
            "schema": {"type": "string", "format": "uuid"},
        },
    }


def _add_request_id_response_headers(document: dict[str, Any]) -> None:
    paths = cast(dict[str, object], document.get("paths", {}))
    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        typed_path_item = cast(dict[str, object], path_item)
        for method, operation in typed_path_item.items():
            if method not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            if not isinstance(operation, dict):
                continue
            typed_operation = cast(dict[str, object], operation)
            responses = typed_operation.get("responses", {})
            if not isinstance(responses, dict):
                continue
            typed_responses = cast(dict[str, object], responses)
            for response in typed_responses.values():
                if isinstance(response, dict):
                    typed_response = cast(dict[str, object], response)
                    headers = typed_response.setdefault("headers", {})
                    if isinstance(headers, dict):
                        typed_headers = cast(dict[str, object], headers)
                        typed_headers["X-Request-ID"] = {"$ref": "#/components/headers/RequestId"}
