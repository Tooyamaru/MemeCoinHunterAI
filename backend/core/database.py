"""Lazy async SQLAlchemy runtime and centralized session boundary."""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import StrEnum
from typing import AsyncIterator
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import Settings, get_settings
from backend.core.logging import get_logger

logger = get_logger()


class DatabaseState(StrEnum):
    """Truthful states available to the application."""

    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONFIGURED = "CONFIGURED"
    CONNECTED = "CONNECTED"
    UNAVAILABLE = "UNAVAILABLE"


def redact_database_url(database_url: str | None) -> str | None:
    """Return a database URL with credentials removed."""

    if not database_url:
        return None
    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except ValueError:
        parsed = urlsplit(database_url)
        if parsed.netloc and "@" in parsed.netloc:
            host = parsed.netloc.rsplit("@", 1)[-1]
            return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))
        return "<invalid-database-url>"


def async_database_url(database_url: str) -> str:
    """Normalize common PostgreSQL URLs for the async SQLAlchemy driver."""

    url = make_url(database_url)
    if url.drivername in {"postgresql", "postgres"}:
        query = dict(url.query)
        sslmode = query.pop("sslmode", None)
        if sslmode and sslmode != "disable":
            query["ssl"] = sslmode
        url = url.set(drivername="postgresql+asyncpg", query=query)
    return url.render_as_string(hide_password=False)


@dataclass(frozen=True)
class DatabaseConfig:
    """Database connection intent, not an active connection."""

    url: str | None

    @property
    def is_configured(self) -> bool:
        return bool(self.url)

    @property
    def state(self) -> DatabaseState:
        return DatabaseState.CONFIGURED if self.is_configured else DatabaseState.NOT_CONFIGURED

    @property
    def is_connected(self) -> bool:
        return False


def get_database_config(settings: Settings | None = None) -> DatabaseConfig:
    """Return database configuration without opening a connection."""

    active_settings = settings or get_settings()
    return DatabaseConfig(url=active_settings.database_url or None)


class DatabaseRuntime:
    """Owns the async engine, health check, and request/worker sessions."""

    def __init__(self, settings: Settings) -> None:
        self.config = get_database_config(settings)
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self.state = self.config.state
        self.error: str | None = None

    @property
    def is_ready(self) -> bool:
        return self.state in (DatabaseState.NOT_CONFIGURED, DatabaseState.CONNECTED)

    async def start(self) -> None:
        """Create the engine lazily and perform a real connectivity check."""

        if not self.config.url:
            self.state = DatabaseState.NOT_CONFIGURED
            return

        try:
            self.engine = create_async_engine(async_database_url(self.config.url), pool_pre_ping=True)
            self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            self.state = DatabaseState.CONNECTED
            self.error = None
            logger.info("database.connected", extra={"database_url": redact_database_url(self.config.url)})
        except (SQLAlchemyError, OSError, TypeError, ValueError) as exc:
            self.state = DatabaseState.UNAVAILABLE
            self.error = type(exc).__name__
            logger.warning(
                "database.unavailable",
                extra={
                    "database_url": redact_database_url(self.config.url),
                    "error_type": type(exc).__name__,
                },
            )
            await self.dispose()

    @asynccontextmanager
    async def session_scope(self) -> AsyncIterator[AsyncSession]:
        """Yield one short-lived transactional unit of work."""

        if self.session_factory is None:
            raise RuntimeError("Database session requested before a connection was established")

        async with self.session_factory() as session:
            try:
                async with session.begin():
                    yield session
            except Exception:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        """Release the engine safely during shutdown or failed startup."""

        if self.engine is not None:
            await self.engine.dispose()
        self.engine = None
        self.session_factory = None
