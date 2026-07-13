from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy import text

from talaqi.config import Settings, get_settings
from talaqi.db.engine import build_async_engine, build_session_factory
from talaqi.health import ReadinessProbe, ReadinessRegistry, create_health_router
from talaqi.platform import register_platform_contracts
from talaqi.platform.openapi import install_openapi


def create_app(
    settings: Settings | None = None,
    readiness_registry: ReadinessRegistry | None = None,
    *,
    database_probe: ReadinessProbe | None = None,
) -> FastAPI:
    registry = readiness_registry or ReadinessRegistry()
    if readiness_registry is None:

        async def configuration_probe() -> bool:
            configured = settings if settings is not None else get_settings()
            _ = configured.environment
            return True

        registry.register("configuration", configuration_probe)

        if database_probe is None:

            async def default_database_probe() -> bool:
                configured = settings if settings is not None else get_settings()
                engine = build_async_engine(configured.database_url)
                try:
                    session_factory = build_session_factory(engine)
                    async with session_factory() as session:
                        result = await session.execute(text("SELECT 1"))
                        return result.scalar_one() == 1
                finally:
                    await engine.dispose()

            database_probe = default_database_probe

        registry.register("database", database_probe)

    application = FastAPI(title="Talaqi API")
    register_platform_contracts(application)
    application.include_router(create_health_router(registry))
    install_openapi(application)
    return application


app = create_app()
