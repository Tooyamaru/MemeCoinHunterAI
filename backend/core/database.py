"""Database boundary for the P01 foundation.

No connection is opened yet. A later P01 task can add PostgreSQL access and
migrations behind this boundary without coupling the API to a local database.
"""

from dataclasses import dataclass

from backend.core.config import Settings, get_settings


@dataclass(frozen=True)
class DatabaseConfig:
    """Database connection intent, not an active connection."""

    url: str | None

    @property
    def is_configured(self) -> bool:
        return bool(self.url)


def get_database_config(settings: Settings | None = None) -> DatabaseConfig:
    """Return database configuration without probing or connecting to it."""

    active_settings = settings or get_settings()
    return DatabaseConfig(url=active_settings.database_url or None)
