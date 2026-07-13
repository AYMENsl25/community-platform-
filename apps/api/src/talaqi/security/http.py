from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Final
from urllib.parse import urlsplit

from fastapi import FastAPI
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from talaqi.config import Environment, Settings
from talaqi.db.identifiers import generate_uuid7

_SECURITY_HEADERS: Final[tuple[tuple[bytes, bytes], ...]] = (
    (
        b"content-security-policy",
        b"default-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
    ),
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (
        b"permissions-policy",
        b"camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    ),
)
_HSTS: Final = (b"strict-transport-security", b"max-age=63072000; includeSubDomains")
_METHODS: Final = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
_METHODS_VALUE: Final = ", ".join(_METHODS)
_HEADERS: Final = ("Accept", "Content-Type", "Idempotency-Key", "X-CSRF-Token")
_HEADERS_VALUE: Final = ", ".join(_HEADERS)
_HEADER_NAMES: Final = frozenset(name.lower() for name in _HEADERS)
_CONTROLLED_RESPONSE_HEADERS: Final = frozenset(
    {
        *(name for name, _ in _SECURITY_HEADERS),
        _HSTS[0],
        b"access-control-allow-origin",
        b"access-control-allow-credentials",
        b"access-control-allow-methods",
        b"access-control-allow-headers",
        b"access-control-expose-headers",
    }
)


def _configured_hostname(value: str) -> str:
    parsed = urlsplit(f"//{value}")
    return (parsed.hostname or "").rstrip(".").lower()


def _request_hostname(value: str) -> str | None:
    if not value or value != value.strip() or any(character in value for character in "/@?#\\"):
        return None
    try:
        parsed = urlsplit(f"//{value}")
        port = parsed.port
    except ValueError:
        return None
    if parsed.username is not None or parsed.password is not None or parsed.hostname is None:
        return None

    authority = parsed.netloc
    if authority.startswith("["):
        closing_bracket = authority.find("]")
        if closing_bracket < 0:
            return None
        suffix = authority[closing_bracket + 1 :]
        if suffix and (not suffix.startswith(":") or not suffix[1:].isdecimal()):
            return None
    else:
        if authority.count(":") > 1:
            return None
        if ":" in authority and not authority.rsplit(":", maxsplit=1)[1].isdecimal():
            return None
    if port is not None and not 1 <= port <= 65535:
        return None
    return parsed.hostname.rstrip(".").lower()


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", ()):
        if key.lower() == name:
            return value.decode("latin-1")
    return None


def _replace_headers(
    existing: Iterable[tuple[bytes, bytes]], replacements: Iterable[tuple[bytes, bytes]]
) -> list[tuple[bytes, bytes]]:
    replacement_list = list(replacements)
    names = _CONTROLLED_RESPONSE_HEADERS | {name.lower() for name, _ in replacement_list}
    return [
        (name, value) for name, value in existing if name.lower() not in names
    ] + replacement_list


class HttpSecurityMiddleware:
    def __init__(self, app: ASGIApp, *, settings_factory: Callable[[], Settings]) -> None:
        self.app = app
        self._settings_factory = settings_factory
        self._settings: Settings | None = None

    def _resolve_settings(self) -> Settings:
        if self._settings is None:
            self._settings = self._settings_factory()
        return self._settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            settings = self._resolve_settings()
        except Exception:
            request_id = str(generate_uuid7())
            scope.setdefault("state", {})["request_id"] = request_id
            response = JSONResponse(
                {
                    "error": {
                        "code": "internal_error",
                        "message_key": "errors.internal",
                        "field_errors": [],
                        "request_id": request_id,
                    }
                },
                status_code=500,
                headers={"X-Request-ID": request_id},
            )
            await response(scope, receive, self._secured_send(send, list(_SECURITY_HEADERS)))
            return
        origin = _header(scope, b"origin")
        host = _header(scope, b"host") or ""
        request_method = _header(scope, b"access-control-request-method")
        is_preflight = scope["method"] == "OPTIONS" and request_method is not None
        allowed_hosts = {_configured_hostname(value) for value in settings.allowed_hosts}

        response_headers: list[tuple[bytes, bytes]] = list(_SECURITY_HEADERS)
        if settings.environment is Environment.PRODUCTION:
            response_headers.append(_HSTS)

        state = scope.setdefault("state", {})
        if _request_hostname(host) not in allowed_hosts:
            request_id = str(generate_uuid7())
            state["request_id"] = request_id
            response = JSONResponse(
                {
                    "error": {
                        "code": "bad_request",
                        "message_key": "errors.bad_request",
                        "field_errors": [],
                        "request_id": request_id,
                    }
                },
                status_code=400,
                headers={"X-Request-ID": request_id},
            )
            await response(scope, receive, self._secured_send(send, response_headers))
            return

        if is_preflight:
            request_id = str(generate_uuid7())
            state["request_id"] = request_id
            response_headers.append((b"x-request-id", request_id.encode("ascii")))
            requested_headers = _header(scope, b"access-control-request-headers") or ""
            header_names = {
                item.strip().lower() for item in requested_headers.split(",") if item.strip()
            }
            allowed = (
                origin in settings.allowed_origins
                and request_method in _METHODS
                and header_names.issubset(_HEADER_NAMES)
            )
            if allowed:
                response_headers.extend(self._cors_headers(origin, preflight=True))
                response = PlainTextResponse("OK", status_code=200)
            else:
                response = PlainTextResponse("Disallowed CORS request", status_code=400)
            await response(scope, receive, self._secured_send(send, response_headers))
            return

        if origin in settings.allowed_origins:
            response_headers.extend(self._cors_headers(origin, preflight=False))
        await self.app(scope, receive, self._secured_send(send, response_headers))

    @staticmethod
    def _cors_headers(origin: str | None, *, preflight: bool) -> list[tuple[bytes, bytes]]:
        if origin is None:
            return []
        headers = [
            (b"access-control-allow-origin", origin.encode("latin-1")),
            (b"access-control-allow-credentials", b"true"),
            (b"vary", b"Origin"),
        ]
        if preflight:
            headers.extend(
                (
                    (b"access-control-allow-methods", _METHODS_VALUE.encode("ascii")),
                    (b"access-control-allow-headers", _HEADERS_VALUE.encode("ascii")),
                )
            )
        else:
            headers.append((b"access-control-expose-headers", b"X-Request-ID"))
        return headers

    @staticmethod
    def _secured_send(send: Send, replacements: list[tuple[bytes, bytes]]) -> Send:
        async def secured(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = _replace_headers(message.get("headers", ()), replacements)
            await send(message)

        return secured


def install_http_security(application: FastAPI, settings_factory: Callable[[], Settings]) -> None:
    if getattr(application.state, "http_security_installed", False):
        return
    application.state.http_security_installed = True
    application.add_middleware(HttpSecurityMiddleware, settings_factory=settings_factory)


__all__ = ["install_http_security"]
