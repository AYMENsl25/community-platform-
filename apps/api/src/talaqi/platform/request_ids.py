from __future__ import annotations

from fastapi import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from talaqi.db.identifiers import generate_uuid7
from talaqi.platform.errors import error_response


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(generate_uuid7())
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (name, value)
                    for name, value in message.get("headers", ())
                    if name.lower() != b"x-request-id"
                ]
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            request = Request(scope, receive=receive)
            response = error_response(
                request,
                status_code=500,
                code="internal_error",
                message_key="errors.internal",
            )
            await response(scope, receive, send_with_request_id)


__all__ = ["RequestIdMiddleware"]
