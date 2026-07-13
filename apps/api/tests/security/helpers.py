from __future__ import annotations

from talaqi.config import Environment, Settings


def security_settings(environment: Environment = Environment.TEST) -> Settings:
    deployed = environment in {Environment.STAGING, Environment.PRODUCTION}
    return Settings.model_validate(
        {
            "environment": environment,
            "api_public_url": "https://api.example.test" if deployed else "http://localhost:8000",
            "web_public_url": "https://web.example.test" if deployed else "http://localhost:3000",
            "allowed_origins": [
                "https://web.example.test" if deployed else "http://localhost:3000"
            ],
            "allowed_hosts": ["api.example.test:8443" if deployed else "localhost"],
            "session_secret": "s" * 64 if deployed else "test-secret",  # pragma: allowlist secret
            "cookie_secure": deployed,
            "admin_mfa_required": deployed,
            "database_url": "postgresql://u:p@localhost/talaqi_test",  # pragma: allowlist secret
            "s3_endpoint": "https://s3.example.test" if deployed else "http://localhost:9000",
            "s3_bucket": "test",
            "s3_access_key": "access",
            "s3_secret_key": "secret",  # pragma: allowlist secret
            "smtp_host": "smtp.example.test" if deployed else "localhost",
            "smtp_port": 1025,
            "log_level": "INFO",
        }
    )
