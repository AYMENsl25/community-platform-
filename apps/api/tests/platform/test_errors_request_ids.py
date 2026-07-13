from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, ValidationError
from talaqi.db.identifiers import validate_uuid7
from talaqi.main import create_app
from talaqi.platform import ApiError, CursorParams, FieldError, register_platform_contracts


class MaliciousValidationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: dict[str, int]
    items: list[int]


@pytest.fixture
def contract_app() -> FastAPI:
    application = FastAPI()
    register_platform_contracts(application)

    @application.get("/ok")
    async def ok() -> dict[str, bool]:  # pyright: ignore[reportUnusedFunction]
        return {"ok": True}

    @application.get("/api-error")
    async def api_error() -> None:  # pyright: ignore[reportUnusedFunction]
        raise ApiError(
            code="stable_problem",
            message_key="errors.stable_problem",
            status_code=409,
        )

    @application.get("/validation")
    async def validation(  # pyright: ignore[reportUnusedFunction]
        limit: int = Query(ge=1, le=100),
    ) -> dict[str, int]:
        return {"limit": limit}

    @application.get("/http-error")
    async def http_error() -> None:  # pyright: ignore[reportUnusedFunction]
        raise HTTPException(status_code=404, detail="postgresql://user:password@internal/db")

    @application.get("/unhandled")
    async def unhandled() -> None:  # pyright: ignore[reportUnusedFunction]
        raise RuntimeError("password=secret https://internal.example/trace")

    @application.get("/page")
    async def page(  # pyright: ignore[reportUnusedFunction]
        params: Annotated[CursorParams, Query()],
    ) -> dict[str, int]:
        return {"limit": params.limit}

    @application.post("/body-validation")
    async def body_validation(  # pyright: ignore[reportUnusedFunction]
        body: MaliciousValidationBody,
    ) -> dict[str, bool]:
        del body
        return {"ok": True}

    @application.post("/root-mapping-validation")
    async def root_mapping_validation(  # pyright: ignore[reportUnusedFunction]
        body: dict[str, int],
    ) -> dict[str, bool]:
        del body
        return {"ok": True}

    return application


@pytest_asyncio.fixture
async def client(contract_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=contract_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as value:
        yield value


@pytest.mark.asyncio
async def test_success_and_health_responses_have_server_owned_uuid7_request_ids(
    client: httpx.AsyncClient,
) -> None:
    supplied = "11111111-1111-7111-8111-111111111111"

    first = await client.get("/ok", headers={"X-Request-ID": supplied})
    second = await client.get("/ok")

    first_id = first.headers["X-Request-ID"]
    second_id = second.headers["X-Request-ID"]
    assert validate_uuid7(first_id) == validate_uuid7(first_id)
    assert validate_uuid7(second_id) == validate_uuid7(second_id)
    assert first_id != supplied
    assert first_id != second_id

    health_transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=health_transport, base_url="http://test") as health:
        response = await health.get("/health/live")
    assert response.json() == {"status": "ok"}
    validate_uuid7(response.headers["X-Request-ID"])


@pytest.mark.asyncio
async def test_api_error_has_exact_locked_envelope_and_matching_request_id(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/api-error")
    request_id = response.headers["X-Request-ID"]

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "stable_problem",
            "message_key": "errors.stable_problem",
            "field_errors": [],
            "request_id": request_id,
        }
    }


@pytest.mark.asyncio
async def test_validation_error_uses_stable_safe_field_errors_without_input(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/validation", params={"limit": "password=secret"})
    request_id = response.headers["X-Request-ID"]

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message_key": "errors.validation",
            "field_errors": [
                {
                    "field": "query.limit",
                    "code": "int_parsing",
                    "message_key": "errors.validation.int_parsing",
                }
            ],
            "request_id": request_id,
        }
    }
    assert "password" not in response.text
    assert "secret" not in response.text
    assert "input" not in response.text


@pytest.mark.asyncio
async def test_validation_locations_never_reflect_keys_urls_passwords_or_list_indices(
    client: httpx.AsyncClient,
) -> None:
    unsafe_values = (
        "password",
        "secret-value",
        "https://private.example/path",
        "postgresql://user:credential@internal/db",
    )
    response = await client.post(
        "/body-validation",
        json={
            "payload": {
                unsafe_values[0]: unsafe_values[1],
                unsafe_values[2]: "not-an-integer",
            },
            "items": ["not-an-integer", unsafe_values[1]],
            unsafe_values[3]: unsafe_values[1],
        },
    )

    assert response.status_code == 422
    request_id = response.headers["X-Request-ID"]
    assert response.json()["error"] == {
        "code": "validation_error",
        "message_key": "errors.validation",
        "field_errors": [
            {
                "field": "body.*",
                "code": "extra_forbidden",
                "message_key": "errors.validation.extra_forbidden",
            },
            {
                "field": "body.items.*",
                "code": "int_parsing",
                "message_key": "errors.validation.int_parsing",
            },
            {
                "field": "body.payload.*",
                "code": "int_parsing",
                "message_key": "errors.validation.int_parsing",
            },
        ],
        "request_id": request_id,
    }
    for unsafe in (*unsafe_values, ".0", ".1"):
        assert unsafe not in response.text


def test_field_error_rejects_non_public_identifiers() -> None:
    with pytest.raises(ValidationError):
        FieldError(
            field="body.password=secret",
            code="int parsing from https://private.example",
            message_key="private message",
        )
    with pytest.raises(ValidationError):
        FieldError(
            field="body.*.*",
            code="invalid",
            message_key="errors.validation.invalid",
        )


def test_field_error_accepts_safe_domain_translation_identifiers() -> None:
    field_error = FieldError(
        field="body.username",
        code="username_taken",
        message_key="errors.profile.username_taken",
    )

    assert field_error.message_key == "errors.profile.username_taken"


@pytest.mark.asyncio
async def test_root_mapping_key_is_not_mistaken_for_a_schema_field(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/root-mapping-validation", json={"password": "secret-value"})

    assert response.status_code == 422
    assert response.json()["error"]["field_errors"] == [
        {
            "field": "body.*",
            "code": "int_parsing",
            "message_key": "errors.validation.int_parsing",
        }
    ]
    assert "password" not in response.text
    assert "secret-value" not in response.text


@pytest.mark.asyncio
async def test_http_and_unhandled_errors_fail_closed_without_internal_details(
    client: httpx.AsyncClient,
) -> None:
    not_found = await client.get("/http-error")
    failed = await client.get("/unhandled")

    assert not_found.status_code == 404
    assert not_found.json()["error"] == {
        "code": "not_found",
        "message_key": "errors.not_found",
        "field_errors": [],
        "request_id": not_found.headers["X-Request-ID"],
    }
    assert failed.status_code == 500
    assert failed.json()["error"] == {
        "code": "internal_error",
        "message_key": "errors.internal",
        "field_errors": [],
        "request_id": failed.headers["X-Request-ID"],
    }
    for unsafe in ("password", "secret", "postgresql", "internal.example", "trace"):
        assert unsafe not in not_found.text
        assert unsafe not in failed.text


@pytest.mark.asyncio
async def test_framework_http_errors_also_use_the_standard_envelope(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/missing-route")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "not_found",
        "message_key": "errors.not_found",
        "field_errors": [],
        "request_id": response.headers["X-Request-ID"],
    }


@pytest.mark.asyncio
async def test_query_page_limit_defaults_accepts_bounds_and_rejects_invalid_values_in_envelope(
    client: httpx.AsyncClient,
) -> None:
    assert (await client.get("/page")).json() == {"limit": 20}
    assert (await client.get("/page", params={"limit": "1"})).json() == {"limit": 1}
    assert (await client.get("/page", params={"limit": "100"})).json() == {"limit": 100}

    for invalid in ("0", "-1", "101", "1.5", "not-an-integer"):
        response = await client.get("/page", params={"limit": invalid})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
        assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
