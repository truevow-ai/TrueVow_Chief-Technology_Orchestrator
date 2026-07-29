"""Application configuration.

Uses pydantic-settings, matching the TrueVow platform convention.
Values load from environment and .env / .env.local.
"""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TrueVow RETAINER Service"
    app_version: str = "0.1.0"
    environment: str = "development"

    auth_mode: str = "local"
    local_jwt_secret: str = "insecure-dev-secret-change-me"
    local_jwt_algorithm: str = "HS256"
    clerk_jwks_url: str = ""
    clerk_issuer: str = ""
    clerk_audience: str = ""
    clerk_jwks_cache_ttl: int = 3600

    retainer_database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("RETAINER_DATABASE_URL", "DATABASE_URL"),
    )

    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""

    cors_allow_origins: str = "*"

    host: str = "0.0.0.0"
    port: int = 3038

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def effective_database_url(self) -> str:
        url = self.retainer_database_url
        if not url:
            return "sqlite+aiosqlite:///:memory:"
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
