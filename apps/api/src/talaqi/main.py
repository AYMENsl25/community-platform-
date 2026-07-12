from __future__ import annotations

from fastapi import FastAPI

from talaqi.config import Settings, get_settings
from talaqi.health import ReadinessRegistry, create_health_router


def create_app(
    settings: Settings | None = None, readiness_registry: ReadinessRegistry | None = None
) -> FastAPI:
    registry = readiness_registry or ReadinessRegistry()
    if readiness_registry is None:

        async def configuration_probe() -> bool:
            configured = settings if settings is not None else get_settings()
            _ = configured.environment
            return True

        registry.register("configuration", configuration_probe)

    application = FastAPI(title="Talaqi API")
    application.include_router(create_health_router(registry))
    return application


app = create_app()
