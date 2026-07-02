import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from threading import Lock
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


@dataclass
class RequestMetrics:
    total_requests: int = 0
    in_flight_requests: int = 0
    slow_requests: int = 0
    total_duration_ms: float = 0
    by_status: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_path: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _lock: Lock = field(default_factory=Lock)

    def start(self) -> None:
        with self._lock:
            self.in_flight_requests += 1

    def finish(self, *, path: str, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self.in_flight_requests = max(self.in_flight_requests - 1, 0)
            self.total_requests += 1
            self.total_duration_ms += duration_ms
            self.by_status[str(status_code)] += 1
            self.by_path[path] += 1
            if duration_ms >= settings.slow_request_threshold_ms:
                self.slow_requests += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            average_duration_ms = (
                round(self.total_duration_ms / self.total_requests, 2)
                if self.total_requests
                else 0
            )
            return {
                "enabled": settings.metrics_enabled,
                "total_requests": self.total_requests,
                "in_flight_requests": self.in_flight_requests,
                "slow_requests": self.slow_requests,
                "average_duration_ms": average_duration_ms,
                "by_status": dict(self.by_status),
                "top_paths": dict(
                    sorted(
                        self.by_path.items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )[:10]
                ),
            }


rate_limiter = InMemoryRateLimiter(
    limit=max(settings.rate_limit_requests_per_minute, 1),
)
request_metrics = RequestMetrics()


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
        trace_id = request.headers.get("X-Trace-ID") or request_id
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        request_metrics.start()

        if settings.rate_limit_enabled and not _is_rate_limit_exempt(request.url.path):
            if not rate_limiter.allow(_client_key(request), time.monotonic()):
                rate_limit_response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Try again shortly.",
                            "request_id": request_id,
                        }
                    },
                    headers={
                        "X-Request-ID": request_id,
                        "X-Trace-ID": trace_id,
                        "Retry-After": "60",
                    },
                )
                request_metrics.finish(
                    path=request.url.path,
                    status_code=rate_limit_response.status_code,
                    duration_ms=round((time.perf_counter() - start) * 1000, 2),
                )
                return rate_limit_response

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        request_metrics.finish(
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        log_extra = {
            "request_id": request_id,
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
        if duration_ms >= settings.slow_request_threshold_ms:
            logger.warning("slow request completed", extra=log_extra)
        else:
            logger.info("request completed", extra=log_extra)
        return response
