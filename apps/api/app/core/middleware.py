import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette import status
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings

logger = logging.getLogger("communiti.requests")

RequestHandler = Callable[[Request], Awaitable[Response]]


class InMemoryRateLimiter:
    def __init__(self, *, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float) -> bool:
        hits = self._hits[key]
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


rate_limiter = InMemoryRateLimiter(
    limit=max(settings.rate_limit_requests_per_minute, 1),
)


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    return request.client.host if request.client else "unknown"


def _is_rate_limit_exempt(path: str) -> bool:
    return any(
        path == exempt_path or path.startswith(f"{exempt_path}/")
        for exempt_path in settings.rate_limit_exempt_path_list
    )


def configure_security_middleware(app: FastAPI) -> None:
    trusted_hosts = settings.trusted_host_list
    if trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

    @app.middleware("http")
    async def request_context_middleware(
        request: Request, call_next: RequestHandler
    ) -> Response:
        start = time.perf_counter()
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
        request.state.request_id = request_id

        if settings.rate_limit_enabled and not _is_rate_limit_exempt(request.url.path):
            if not rate_limiter.allow(_client_key(request), time.monotonic()):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Try again shortly.",
                            "request_id": request_id,
                        }
                    },
                    headers={"X-Request-ID": request_id, "Retry-After": "60"},
                )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
