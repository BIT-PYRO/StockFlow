import logging
import os
from functools import lru_cache
from pathlib import Path

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_diag_log = logging.getLogger("diagnostics.config")


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
    _run_config_diagnostics()
    return Settings()


def _run_config_diagnostics() -> None:
    """Diagnostic-only: inspect .env loading and settings resolution."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s [%(name)s] %(message)s",
    )

    # 1. Locate .env — pydantic-settings resolves it relative to cwd.
    cwd = Path.cwd()
    env_path = cwd / ".env"
    _diag_log.debug("CWD                   : %s", cwd)
    _diag_log.debug(".env search path      : %s", env_path)
    if env_path.exists():
        _diag_log.debug(".env file found       : YES (%d bytes)", env_path.stat().st_size)
        _diag_log.debug(".env contents ---------")
        for i, line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), 1):
            # Redact password from DATABASE_URL line before printing.
            if "DATABASE_URL" in line:
                try:
                    from urllib.parse import urlparse, urlunparse
                    parsed = urlparse(line.split("=", 1)[1].strip())
                    redacted = parsed._replace(
                        netloc=f"{parsed.username}:***@{parsed.hostname}:{parsed.port}"
                    )
                    _diag_log.debug("  line %02d: DATABASE_URL=%s", i, urlunparse(redacted))
                except Exception:
                    _diag_log.debug("  line %02d: DATABASE_URL=<parse error>", i)
            else:
                _diag_log.debug("  line %02d: %s", i, line)
        _diag_log.debug(".env contents ---------")
    else:
        _diag_log.warning(".env file NOT found at %s", env_path)

    # 2. Check raw DATABASE_URL in the OS environment (set by Docker / shell).
    raw_env = os.environ.get("DATABASE_URL", "<not set in OS environment>")
    if raw_env != "<not set in OS environment>":
        try:
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(raw_env)
            redacted = parsed._replace(
                netloc=f"{parsed.username}:***@{parsed.hostname}:{parsed.port}"
            )
            _diag_log.debug("OS env DATABASE_URL   : %s", urlunparse(redacted))
        except Exception:
            _diag_log.debug("OS env DATABASE_URL   : <parse error>")
    else:
        _diag_log.debug("OS env DATABASE_URL   : %s", raw_env)

    # 3. Verify pydantic-settings model_config.
    _diag_log.debug("pydantic-settings cfg : env_file=%r  encoding=%r  case_sensitive=%r",
                    Settings.model_config.get("env_file"),
                    Settings.model_config.get("env_file_encoding"),
                    Settings.model_config.get("case_sensitive"))

    # 4. Check for hardcoded credentials in this file.
    this_file = Path(__file__).read_text(encoding="utf-8")
    hardcoded_suspects = ["postgresql://", "postgres:", "password", "secret"]
    found = [w for w in hardcoded_suspects if w.lower() in this_file.lower()
             and "hardcoded" not in this_file[max(0, this_file.lower().find(w)-30):this_file.lower().find(w)+30]]
    if found:
        _diag_log.warning("Possible hardcoded credential keywords in config.py: %s", found)
    else:
        _diag_log.debug("Hardcoded credential check: no suspects in config.py")


# Module-level singleton — import this directly where DI is not available.
settings = get_settings()

