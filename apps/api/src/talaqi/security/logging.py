from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Final, cast

from fastapi import FastAPI
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_LOGGER_NAME: Final = "talaqi.request"
_SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|secret|token|api[_-]?key|authorization|cookie)", re.I
)
_CREDENTIAL = re.compile(
    r"(?:\b(?:bearer|basic)\s+\S+|\b(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*\S+|[a-z][a-z0-9+.-]*://[^\s/@:]+:[^\s/@]+@)",
    re.I,
)


def redact_sensitive(value: object, *, key: str | None = None) -> object:
    if key is not None and _SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {
            str(item_key): redact_sensitive(item, key=str(item_key))
            for item_key, item in mapping.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence = cast(Sequence[object], value)
        return [redact_sensitive(item) for item in sequence]
    if isinstance(value, str) and _CREDENTIAL.search(value):
        return "[REDACTED]"
    return value


def configure_request_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(getattr(handler, "_talaqi_request_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler._talaqi_request_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    return logger


class SafeRequestLoggingMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        logger: logging.Logger,
        clock: Callable[[], float],
        timestamp: Callable[[], datetime],
    ) -> None:
        self.app = app
        self._logger = logger
        self._clock = clock
        self._timestamp = timestamp

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = self._clock()
        status_code = 500
        request_id = "unavailable"

        async def capture(message: Message) -> None:
            nonlocal request_id, status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                for name, value in message.get("headers", ()):
                    if name.lower() == b"x-request-id":
                        request_id = value.decode("ascii", errors="ignore")
                        break
            await send(message)

        await self.app(scope, receive, capture)
        duration = round(max(0.0, min((self._clock() - started) * 1000, 86_400_000)))
        route_object = scope.get("route")
        route = getattr(route_object, "path", "unmatched")
        if not isinstance(route, str) or not route.startswith("/"):
            route = "unmatched"
        level = "ERROR" if status_code >= 500 else "INFO"
        observed = (
            self._timestamp().astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        )
        event = {
            "timestamp": observed,
            "event": "request.completed",
            "method": str(scope.get("method", "")).upper(),
            "route": route,
            "status_code": status_code,
            "duration_ms": duration,
            "request_id": request_id,
            "level": level,
        }
        message = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        self._logger.log(logging.ERROR if status_code >= 500 else logging.INFO, message)


def install_request_logging(
    application: FastAPI,
    *,
    logger: logging.Logger | None = None,
    clock: Callable[[], float] = time.monotonic,
    timestamp: Callable[[], datetime] | None = None,
) -> None:
    if getattr(application.state, "request_logging_installed", False):
        return
    application.state.request_logging_installed = True
    application.add_middleware(
        SafeRequestLoggingMiddleware,
        logger=logger or configure_request_logger(),
        clock=clock,
        timestamp=timestamp or (lambda: datetime.now(UTC)),
    )


__all__ = ["configure_request_logger", "install_request_logging", "redact_sensitive"]
