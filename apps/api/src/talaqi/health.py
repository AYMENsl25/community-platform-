from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable
from typing import Literal, Protocol

from fastapi import APIRouter, Response, status
from pydantic import BaseModel


class ReadinessProbe(Protocol):
    def __call__(self) -> Awaitable[bool]: ...


class LiveResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, Literal["ok", "failed"]]


class ReadinessRegistry:
    def __init__(self, *, timeout_seconds: float = 0.5) -> None:
        self._timeout_seconds = timeout_seconds
        self._probes: dict[str, ReadinessProbe] = {}

    def register(self, name: str, probe: ReadinessProbe) -> None:
        if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name) is None:
            raise ValueError("readiness check names must be stable safe identifiers")
        if name in self._probes:
            raise ValueError("readiness check names must be unique")
        self._probes[name] = probe

    async def check(self) -> dict[str, Literal["ok", "failed"]]:
        async def isolated(probe: ReadinessProbe) -> Literal["ok", "failed"]:
            try:
                passed = await asyncio.wait_for(probe(), timeout=self._timeout_seconds)
            except Exception:
                return "failed"
            return "ok" if passed else "failed"

        results = await asyncio.gather(*(isolated(probe) for probe in self._probes.values()))
        return dict(zip(self._probes, results, strict=True))


def create_health_router(registry: ReadinessRegistry) -> APIRouter:
    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("/live", response_model=LiveResponse, operation_id="healthLive")
    async def _live() -> LiveResponse:  # pyright: ignore[reportUnusedFunction]
        return LiveResponse()

    @router.get(
        "/ready",
        response_model=ReadyResponse,
        operation_id="healthReady",
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {
                "model": ReadyResponse,
                "description": "One or more readiness dependencies are unavailable.",
            }
        },
    )
    async def _ready(  # pyright: ignore[reportUnusedFunction]
        response: Response,
    ) -> ReadyResponse:
        checks = await registry.check()
        is_ready = all(value == "ok" for value in checks.values())
        if not is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(status="ready" if is_ready else "not_ready", checks=checks)

    return router
