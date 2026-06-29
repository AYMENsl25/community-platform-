from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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

    clerk_issuer: str | None = None
    clerk_jwks_url: str | None = None
    clerk_audience: str | None = None
    clerk_authorized_parties: str | None = None

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
