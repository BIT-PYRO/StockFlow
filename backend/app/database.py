import logging
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

_diag_log = logging.getLogger("diagnostics.database")


def _redact_url(url: str) -> str:
    """Return the connection URL with the password replaced by ***."""
    try:
        p = urlparse(url)
        return urlunparse(p._replace(netloc=f"{p.username}:***@{p.hostname}:{p.port}"))
    except Exception:
        return "<url-parse-error>"


# 5. Log the exact connection string passed to create_engine (password redacted).
_raw_url = str(settings.DATABASE_URL)
_diag_log.debug("create_engine URL     : %s", _redact_url(_raw_url))
_diag_log.debug("  driver              : %s", urlparse(_raw_url).scheme)
_diag_log.debug("  host                : %s", urlparse(_raw_url).hostname)
_diag_log.debug("  port                : %s", urlparse(_raw_url).port)
_diag_log.debug("  database            : %s", urlparse(_raw_url).path.lstrip("/"))
_diag_log.debug("  user                : %s", urlparse(_raw_url).username)
_diag_log.debug("  pool_size           : %s", settings.DB_POOL_SIZE)
_diag_log.debug("  max_overflow        : %s", settings.DB_MAX_OVERFLOW)
_diag_log.debug("  pool_timeout        : %s", settings.DB_POOL_TIMEOUT)

engine = create_engine(
    _raw_url,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
)


@event.listens_for(engine, "connect")
def _on_connect(dbapi_connection, connection_record):  # noqa: ARG001
    """Diagnostic: fires on every new raw DBAPI connection from the pool."""
    _diag_log.debug("DB pool: new connection opened — dsn=%s",
                    _redact_url(_raw_url))


@event.listens_for(engine, "checkout")
def _on_checkout(dbapi_connection, connection_record, connection_proxy):  # noqa: ARG001
    """Diagnostic: fires each time a connection is checked out from the pool."""
    _diag_log.debug("DB pool: connection checked out")


# Verify the connection once at startup and log the resolved server version.
try:
    with engine.connect() as _conn:
        _version = _conn.execute(text("SELECT version()")).scalar()
        _diag_log.debug("DB connection OK      : %s", _version)
except Exception as _exc:
    _diag_log.error("DB connection FAILED  : %s", _exc)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
