"""Database boundary for the P01 foundation.

No connection is opened yet. A later P01 task can add PostgreSQL access and
migrations behind this boundary without coupling the API to a local database.
"""

from dataclasses import dataclass
from enum import StrEnum

from backend.core.config import Settings, get_settings


class DatabaseState(StrEnum):
    """Truthful states available before a live database connection exists."""

    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONFIGURED = "CONFIGURED"
    CONNECTED = "CONNECTED"
    UNAVAILABLE = "UNAVAILABLE"


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
        return self.state is DatabaseState.CONNECTED


def get_database_config(settings: Settings | None = None) -> DatabaseConfig:
    """Return database configuration without probing or connecting to it."""

    active_settings = settings or get_settings()
    return DatabaseConfig(url=active_settings.database_url or None)
