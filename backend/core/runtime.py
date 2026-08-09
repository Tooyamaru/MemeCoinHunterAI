"""Runtime metadata and lifecycle state."""

from dataclasses import dataclass
from datetime import datetime, timezone

from backend.core.config import Settings

SERVICE_NAME = "meme-coin-hunter-ai"


def utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp suitable for runtime metadata."""

    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RuntimeMetadata:
    """Stable identity and startup information for this process."""

    service: str
    version: str
    environment: str
    started_at: str

    @classmethod
    def from_settings(cls, settings: Settings) -> "RuntimeMetadata":
        return cls(
            service=SERVICE_NAME,
            version=settings.app_version,
            environment=settings.app_env,
            started_at=utc_now_iso(),
        )


@dataclass
class RuntimeState:
    """Mutable lifecycle state owned by the FastAPI application."""

    metadata: RuntimeMetadata
    ready: bool = False
