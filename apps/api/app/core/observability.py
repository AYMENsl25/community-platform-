import logging
from importlib import import_module
from typing import Any

from fastapi import FastAPI

from app.core.config import settings

logger = logging.getLogger("communiti.observability")


def configure_observability(app: FastAPI) -> None:
    app.state.sentry_enabled = False
    app.state.otel_enabled = False
    configure_sentry(app)
    configure_opentelemetry(app)


def configure_sentry(app: FastAPI) -> None:
    if not settings.sentry_dsn:
        return

    try:
        sentry_sdk = import_module("sentry_sdk")
    except ImportError:
        logger.warning("sentry dsn configured but sentry_sdk is not installed")
        return

    getattr(sentry_sdk, "init")(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        environment=settings.environment,
        release=f"communiti-api@{app.version}",
    )
    app.state.sentry_enabled = True
    logger.info("sentry initialized")


def configure_opentelemetry(app: FastAPI) -> None:
    if not settings.otel_exporter_otlp_endpoint:
        return
    try:
        instrumentation = import_module("opentelemetry.instrumentation.fastapi")
    except ImportError:
        logger.warning(
            "otel endpoint configured but OpenTelemetry packages are not installed"
        )
        return
    instrumentor = getattr(instrumentation, "FastAPIInstrumentor")
    instrumentor.instrument_app(app)
    app.state.otel_enabled = True
    logger.info("opentelemetry fastapi instrumentation enabled")


def observability_context() -> dict[str, Any]:
    return {
        "environment": settings.environment,
        "sentry": {
            "enabled": bool(settings.sentry_dsn),
            "traces_sample_rate": settings.sentry_traces_sample_rate,
        },
        "opentelemetry": {
            "enabled": bool(settings.otel_exporter_otlp_endpoint),
            "otlp_endpoint_configured": bool(settings.otel_exporter_otlp_endpoint),
        },
        "metrics": {
            "enabled": settings.metrics_enabled,
            "export_url_configured": bool(settings.metrics_export_url),
        },
        "slow_logs": {
            "request_threshold_ms": settings.slow_request_threshold_ms,
            "db_query_threshold_ms": settings.db_slow_query_threshold_ms,
        },
    }


def sentry_context() -> dict[str, Any]:
    return observability_context()["sentry"]
