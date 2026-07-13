from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr
from talaqi.config import Settings
from talaqi.main import create_app


@pytest.mark.asyncio
async def test_default_database_readiness_executes_select_one(
    test_database_url: SecretStr, migrated_database: None
) -> None:
    del migrated_database
    settings = Settings.model_validate(
        {
            "environment": "test",
            "api_public_url": "http://localhost:8000",
            "web_public_url": "http://localhost:3000",
            "allowed_origins": ["http://localhost:3000"],
            "allowed_hosts": ["localhost"],
            "session_secret": "test-secret",
            "cookie_secure": False,
            "admin_mfa_required": False,
            "database_url": test_database_url,
            "s3_endpoint": "http://localhost:9000",
            "s3_bucket": "test",
            "s3_access_key": "access",
            "s3_secret_key": "secret",
            "smtp_host": "localhost",
            "smtp_port": 1025,
            "log_level": "DEBUG",
        }
    )
    transport = httpx.ASGITransport(app=create_app(settings))

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"configuration": "ok", "database": "ok"},
    }
