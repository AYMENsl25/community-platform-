from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

API_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=API_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    app_name: str = "COMMUNITI API"
    api_v1_prefix: str = "/api/v1"

    # Prefer DB_* fields locally because they avoid URL-encoding issues in passwords.
    database_url: str | None = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "communiti_dev"
    db_user: str = "postgres"
    db_password: str = Field(default="postgres", repr=False)

    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 120
    rate_limit_exempt_paths: str = "/health,/docs,/redoc,/openapi.json"

    clerk_issuer: str | None = None
    clerk_jwks_url: str | None = None
    clerk_audience: str | None = None
    clerk_authorized_parties: str | None = None

    web_base_url: str = "http://127.0.0.1:3000"
    payment_provider: str = "moyasar"
    moyasar_secret_key: str | None = Field(default=None, repr=False)
    moyasar_webhook_secret: str | None = Field(default=None, repr=False)
    moyasar_api_base_url: str = "https://api.moyasar.com/v1"

    @field_validator(
        "database_url",
        "clerk_issuer",
        "clerk_jwks_url",
        "clerk_audience",
        "clerk_authorized_parties",
        "moyasar_secret_key",
        "moyasar_webhook_secret",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def sqlalchemy_database_url(self) -> str | URL:
        if self.database_url and "YOUR_PASSWORD" not in self.database_url:
            return self.database_url

        return URL.create(
            "postgresql+asyncpg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @property
    def allowed_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def trusted_host_list(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]

    @property
    def rate_limit_exempt_path_list(self) -> list[str]:
        return [
            path.strip()
            for path in self.rate_limit_exempt_paths.split(",")
            if path.strip()
        ]

    @property
    def effective_clerk_jwks_url(self) -> str | None:
        if self.clerk_jwks_url:
            return self.clerk_jwks_url
        if self.clerk_issuer:
            return f"{self.clerk_issuer.rstrip('/')}/.well-known/jwks.json"
        return None

    @property
    def clerk_authorized_party_list(self) -> list[str]:
        if self.clerk_authorized_parties:
            return [
                origin.strip()
                for origin in self.clerk_authorized_parties.split(",")
                if origin.strip()
            ]
        return self.allowed_origin_list

    @property
    def normalized_web_base_url(self) -> str:
        return self.web_base_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
