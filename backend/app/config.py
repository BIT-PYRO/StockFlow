from functools import lru_cache

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "Inventory & Order Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ───────────────────────────────────────────────────────────────
    # Required — must be set in .env or via environment variable.
    # Expected format: postgresql://user:password@host:port/dbname
    DATABASE_URL: PostgresDsn

    # ── Connection pool ────────────────────────────────────────────────────────
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins, e.g. "http://localhost:3000,https://example.com"
    # Defaults to "*" for development; restrict in production.
    CORS_ORIGINS: str = "*"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def database_url_must_be_set(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must be set in .env or environment")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance. Use this in dependency injection."""
    return Settings()


# Module-level singleton — import this directly where DI is not available.
settings = get_settings()
