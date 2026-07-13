from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from talaqi.db.identifiers import generate_uuid7
from talaqi.platform.errors import error_response


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = str(generate_uuid7())
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        response = error_response(
            request,
            status_code=500,
            code="internal_error",
            message_key="errors.internal",
        )
    response.headers["X-Request-ID"] = request_id
    return response
