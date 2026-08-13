from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy import text

from talaqi.clubs.membership_routes import router as club_memberships_router
from talaqi.clubs.routes import router as clubs_router
from talaqi.communications.content_routes import router as communications_content_router
from talaqi.communications.routes import router as communications_router
from talaqi.config import Settings, get_settings
from talaqi.dashboard import router as dashboard_router
from talaqi.db.engine import build_async_engine, build_session_factory
from talaqi.discovery.routes import router as discovery_router
from talaqi.events.access_rate_limits import install_event_access_rate_limits
from talaqi.events.access_routes import router as event_access_router
from talaqi.events.routes import router as events_router
from talaqi.health import ReadinessProbe, ReadinessRegistry, create_health_router
from talaqi.identity.rate_limits import install_auth_rate_limits
from talaqi.identity.routes import router as identity_router
from talaqi.media.routes import router as media_router
from talaqi.media.runtime import install_media_storage
from talaqi.media.storage import MediaStorage
from talaqi.moderation.routes import router as moderation_router
from talaqi.platform import register_platform_contracts
from talaqi.platform.openapi import install_openapi
from talaqi.profiles.routes import router as profiles_router
from talaqi.regions.routes import router as regions_router
from talaqi.registrations.routes import router as registrations_router
from talaqi.runtime import SessionFactory, install_runtime
from talaqi.security import RateLimiter, install_http_security, install_request_logging


def create_app(
    settings: Settings | None = None,
    readiness_registry: ReadinessRegistry | None = None,
    *,
    database_probe: ReadinessProbe | None = None,
    session_factory: SessionFactory | None = None,
    storage_probe: ReadinessProbe | None = None,
    auth_rate_limiter: RateLimiter | None = None,
    event_access_rate_limiter: RateLimiter | None = None,
    media_storage: MediaStorage | None = None,
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
    settings_factory = (lambda: settings) if settings is not None else get_settings
    install_runtime(application, settings_factory, session_factory)
    media_runtime = install_media_storage(application, settings_factory, media_storage)
    if readiness_registry is None:
        registry.register("object_storage", storage_probe or media_runtime.ready)

    install_auth_rate_limits(application, settings_factory, provider=auth_rate_limiter)
    install_event_access_rate_limits(
        application,
        settings_factory,
        provider=event_access_rate_limiter,
    )
    install_http_security(application, settings_factory)
    install_request_logging(application)
    application.include_router(create_health_router(registry))
    application.include_router(regions_router)
    application.include_router(identity_router)
    application.include_router(profiles_router)
    application.include_router(communications_router)
    application.include_router(communications_content_router)
    application.include_router(dashboard_router)
    application.include_router(clubs_router)
    application.include_router(club_memberships_router)
    application.include_router(events_router)
    application.include_router(event_access_router)
    application.include_router(registrations_router)
    application.include_router(discovery_router)
    application.include_router(media_router)
    application.include_router(moderation_router)
    install_openapi(application)
    return application


app = create_app()
