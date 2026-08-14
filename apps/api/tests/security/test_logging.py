from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from io import StringIO

import httpx
import pytest
from fastapi import FastAPI, Request
from talaqi.db.identifiers import validate_uuid7
from talaqi.platform import register_platform_contracts
from talaqi.security.http import install_http_security
from talaqi.security.logging import install_request_logging, redact_sensitive

from .helpers import security_settings

ALLOWED_KEYS = {
    "timestamp",
    "event",
    "method",
    "route",
    "status_code",
    "duration_ms",
    "request_id",
    "trace_id",
    "level",
}


def logger_and_stream() -> tuple[logging.Logger, StringIO]:
    stream = StringIO()
    logger = logging.Logger("test.safe.request", level=logging.INFO)
    logger.addHandler(logging.StreamHandler(stream))
    return logger, stream


@pytest.mark.asyncio
async def test_lazy_settings_failure_returns_one_safe_completed_event() -> None:
    logger, stream = logger_and_stream()
    resolutions: list[int] = []

    def fail_settings():  # type: ignore[no-untyped-def]
        resolutions.append(1)
        raise RuntimeError(  # pragma: allowlist secret
            "Bearer settings-secret password=hunter2"  # pragma: allowlist secret
        )

    app = FastAPI()
    register_platform_contracts(app)
    install_http_security(app, fail_settings)
    install_request_logging(app, logger=logger)
    app.openapi()
    app.build_middleware_stack()
    assert resolutions == []

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.get("/unresolved")

    assert resolutions == [1]
    assert response.status_code == 500
    request_id = response.headers["x-request-id"]
    validate_uuid7(request_id)
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message_key": "errors.internal",
            "field_errors": [],
            "request_id": request_id,
        }
    }
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"].startswith("default-src 'none'")
    assert "strict-transport-security" not in response.headers

    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert len(events) == 1
    assert events[0]["status_code"] == 500
    assert events[0]["request_id"] == request_id
    assert response.headers["x-trace-id"] == events[0]["trace_id"]
    assert len(events[0]["trace_id"]) == 32
    assert events[0]["level"] == "ERROR"
    assert not any(
        value in stream.getvalue() or value in response.text
        for value in ("settings-secret", "hunter2", "Bearer")
    )


@pytest.mark.asyncio
async def test_completed_events_have_exact_safe_schema_and_templates() -> None:
    logger, stream = logger_and_stream()
    app = FastAPI()
    register_platform_contracts(app)
    install_request_logging(
        app,
        logger=logger,
        clock=lambda: 1.25,
        timestamp=lambda: datetime(2026, 7, 13, 12, 30, tzinfo=UTC),
    )

    @app.get("/items/{item_id}")
    async def item(  # pyright: ignore[reportUnusedFunction]
        item_id: str, request: Request
    ) -> dict[str, str]:
        del request
        return {"id": item_id}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (
            await client.get("/items/password=secret?token=hunter2")  # pragma: allowlist secret
        ).status_code == 200
        assert (
            await client.get("/postgresql://user:pass@private")  # pragma: allowlist secret
        ).status_code == 404

    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert len(events) == 2
    assert all(set(event) == ALLOWED_KEYS for event in events)
    assert events[0] == {
        "timestamp": "2026-07-13T12:30:00Z",
        "event": "request.completed",
        "method": "GET",
        "route": "/items/{item_id}",
        "status_code": 200,
        "duration_ms": 0,
        "request_id": events[0]["request_id"],
        "trace_id": events[0]["trace_id"],
        "level": "INFO",
    }
    assert events[1]["route"] == "unmatched"
    assert not any(
        value in stream.getvalue()
        for value in ("password", "secret", "hunter2", "postgresql", "private")
    )


@pytest.mark.asyncio
async def test_unhandled_exception_logs_one_generic_error_and_cancellation_logs_nothing() -> None:
    logger, stream = logger_and_stream()
    app = FastAPI()
    register_platform_contracts(app)
    install_http_security(app, security_settings)
    install_request_logging(app, logger=logger)

    @app.get("/explode")
    async def explode() -> None:  # pyright: ignore[reportUnusedFunction]
        raise RuntimeError(  # pragma: allowlist secret
            "Bearer top-secret "  # pragma: allowlist secret
            "password=hunter2 "  # pragma: allowlist secret
            "https://user:pass@internal/path"  # pragma: allowlist secret
        )

    @app.get("/cancel")
    async def cancel() -> None:  # pyright: ignore[reportUnusedFunction]
        raise asyncio.CancelledError

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        response = await client.get("/explode")
        assert response.status_code == 500
        with pytest.raises(asyncio.CancelledError):
            await client.get("/cancel")

    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert len(events) == 1
    assert events[0]["level"] == "ERROR"
    assert events[0]["route"] == "/explode"
    assert not any(
        value in stream.getvalue() for value in ("top-secret", "hunter2", "internal", "pass@")
    )


def test_recursive_redaction_never_echoes_sensitive_sources() -> None:
    hostile = {
        "password": "hunter2",  # pragma: allowlist secret
        "nested": [
            "Bearer abc.def.ghi",
            "token=very-secret",  # pragma: allowlist secret
            "https://user:pass@internal.example/path",
            {"api_key": "key-value"},  # pragma: allowlist secret
        ],
        "safe": "public",
    }
    redacted = redact_sensitive(hostile)
    assert isinstance(redacted, dict)
    rendered = json.dumps(redacted)
    assert redacted["safe"] == "public"
    assert rendered.count("[REDACTED]") >= 4
    assert not any(
        value in rendered
        for value in ("hunter2", "abc.def", "very-secret", "user:pass", "key-value")
    )


@pytest.mark.asyncio
async def test_valid_traceparent_is_correlated_and_hostile_value_is_replaced() -> None:
    logger, stream = logger_and_stream()
    app = FastAPI()
    register_platform_contracts(app)
    install_request_logging(app, logger=logger)

    @app.get("/trace")
    async def trace() -> dict[str, bool]:  # pyright: ignore[reportUnusedFunction]
        return {"ok": True}

    valid = "0123456789abcdef0123456789abcdef"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as client:
        correlated = await client.get(
            "/trace", headers={"traceparent": f"00-{valid}-0123456789abcdef-01"}
        )
        replaced = await client.get("/trace", headers={"traceparent": "Bearer private-token"})
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert correlated.headers["x-trace-id"] == events[0]["trace_id"] == valid
    assert replaced.headers["x-trace-id"] == events[1]["trace_id"]
    assert events[1]["trace_id"] != "Bearer private-token"
    assert "private-token" not in stream.getvalue()
