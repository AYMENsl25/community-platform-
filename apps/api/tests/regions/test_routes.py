from __future__ import annotations

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from talaqi.config import Settings
from talaqi.main import create_app


def _settings() -> Settings:
    database_url = (
        "postgresql+asyncpg://unused:unused@localhost:5432/unused_test"  # pragma: allowlist secret
    )
    return Settings.model_validate(
        {
            "environment": "test",
            "api_public_url": "http://localhost:8000",
            "web_public_url": "http://localhost:3000",
            "allowed_origins": ["http://localhost:3000"],
            "allowed_hosts": ["localhost"],
            "session_secret": "test-secret",  # pragma: allowlist secret
            "cookie_secure": False,
            "admin_mfa_required": False,
            "database_url": database_url,
            "s3_endpoint": "http://localhost:9000",
            "s3_bucket": "test",
            "s3_access_key": "access",
            "s3_secret_key": "secret",  # pragma: allowlist secret
            "smtp_host": "localhost",
            "smtp_port": 1025,
            "log_level": "DEBUG",
        }
    )


@pytest.mark.asyncio
async def test_public_catalog_and_policy_routes_return_normalized_seed_data(
    region_engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(region_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(_settings(), session_factory=factory)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        countries = await client.get("/api/v1/countries")
        cities = await client.get("/api/v1/cities", params={"country_code": "tr"})
        categories = await client.get("/api/v1/categories")
        policy = await client.get("/api/v1/regions/tr/policy")

    assert countries.status_code == cities.status_code == categories.status_code == 200
    assert [item["code"] for item in countries.json()] == ["DZ", "TR"]
    assert cities.json() == [
        {
            "country_code": "TR",
            "slug": "istanbul",
            "name_key": "regions.city.istanbul",
            "time_zone": "Europe/Istanbul",
            "beta_enabled": True,
        }
    ]
    assert categories.json() == [
        {
            "slug": "sports",
            "name_key": "categories.sports",
            "icon_key": "sports",
            "sort_order": 10,
        },
        {
            "slug": "arts-culture",
            "name_key": "categories.arts_culture",
            "icon_key": "arts-culture",
            "sort_order": 20,
        },
        {
            "slug": "technology",
            "name_key": "categories.technology",
            "icon_key": "technology",
            "sort_order": 30,
        },
        {
            "slug": "language-exchange",
            "name_key": "categories.language_exchange",
            "icon_key": "language-exchange",
            "sort_order": 40,
        },
        {
            "slug": "outdoors",
            "name_key": "categories.outdoors",
            "icon_key": "outdoors",
            "sort_order": 50,
        },
        {
            "slug": "games",
            "name_key": "categories.games",
            "icon_key": "games",
            "sort_order": 60,
        },
    ]
    assert policy.status_code == 200
    assert policy.json()["country_code"] == "TR"
    assert policy.json()["cash_bounds"] == [120, 4320]


@pytest.mark.asyncio
async def test_public_cities_exclude_enabled_cities_outside_the_beta(
    region_engine: AsyncEngine,
) -> None:
    async with region_engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO talaqi.cities (
                    country_id, slug, name_key, time_zone, beta_enabled, enabled
                )
                SELECT id, 'ankara', 'regions.city.ankara', 'Europe/Istanbul', false, true
                FROM talaqi.countries WHERE code = 'TR'
                """
            )
        )
    try:
        factory = async_sessionmaker(region_engine, class_=AsyncSession, expire_on_commit=False)
        app = create_app(_settings(), session_factory=factory)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            response = await client.get("/api/v1/cities", params={"country_code": "TR"})

        assert response.status_code == 200
        assert [item["slug"] for item in response.json()] == ["istanbul"]
    finally:
        async with region_engine.begin() as connection:
            await connection.execute(text("DELETE FROM talaqi.cities WHERE slug = 'ankara'"))


@pytest.mark.asyncio
async def test_invalid_city_country_filter_matches_platform_error_schema(
    region_engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(region_engine, class_=AsyncSession, expire_on_commit=False)
    app = create_app(_settings(), session_factory=factory)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.get("/api/v1/cities", params={"country_code": "x"})

    assert response.status_code == 422
    assert set(response.json()) == {"error"}
    assert set(response.json()["error"]) == {
        "code",
        "message_key",
        "field_errors",
        "request_id",
    }
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["field_errors"] == [
        {
            "field": "query.country_code",
            "code": "string_too_short",
            "message_key": "errors.validation.string_too_short",
        }
    ]


def test_app_openapi_construction_is_configuration_and_connection_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration_prefixes = (
        "ENVIRONMENT",
        "API_",
        "WEB_",
        "ALLOWED_",
        "SESSION_",
        "COOKIE_",
        "ADMIN_",
        "DATABASE_",
        "S3_",
        "SMTP_",
        "LOG_",
    )
    for name in tuple(__import__("os").environ):
        if name.startswith(configuration_prefixes):
            monkeypatch.delenv(name, raising=False)

    document = create_app().openapi()

    assert "/api/v1/countries" in document["paths"]
    assert "/api/v1/regions/{country_code}/policy" in document["paths"]
