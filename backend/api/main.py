"""FastAPI application entrypoint for the P01 foundation."""

from fastapi import FastAPI

from backend.core.config import get_settings
from backend.core.logging import configure_logging

settings = get_settings()
logger = configure_logging(settings)

app = FastAPI(
    title="Meme Coin Hunter AI",
    version=settings.app_version,
    description="Application foundation only; market and trading features are not enabled.",
)


@app.get("/health", tags=["runtime"])
def health() -> dict[str, str]:
    """Return lightweight process health without probing unimplemented services."""

    return {
        "status": "ok",
        "service": "meme-coin-hunter-ai",
        "version": settings.app_version,
        "environment": settings.app_env,
    }
