"""FastAPI application entrypoint for the P01 foundation."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.core.config import get_settings
from backend.core.logging import configure_logging, get_logger
from backend.core.request_id import RequestIdMiddleware, get_request_id
from backend.core.runtime import RuntimeMetadata, RuntimeState

settings = get_settings()
configure_logging(settings)
logger = get_logger()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Start and stop only internal application runtime state."""

    runtime = RuntimeState(metadata=RuntimeMetadata.from_settings(settings), ready=True)
    application.state.runtime = runtime
    logger.info(
        "application.startup",
        extra={"service": runtime.metadata.service, "environment": runtime.metadata.environment},
    )
    try:
        yield
    finally:
        runtime.ready = False
        logger.info(
            "application.shutdown",
            extra={"service": runtime.metadata.service, "environment": runtime.metadata.environment},
        )


def create_app() -> FastAPI:
    """Build the API application with its runtime-only foundation."""

    application = FastAPI(
        title="Meme Coin Hunter AI",
        version=settings.app_version,
        description="Application foundation only; market and trading features are not enabled.",
        lifespan=lifespan,
    )
    application.add_middleware(RequestIdMiddleware)

    @application.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            extra={"method": request.method, "path": request.url.path},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": "Internal server error",
                    "request_id": get_request_id(),
                }
            },
        )

    @application.get("/health", tags=["runtime"])
    def health() -> dict[str, str]:
        """Return lightweight process health without external connectivity checks."""

        runtime: RuntimeState = application.state.runtime
        return {
            "status": "ok",
            "service": runtime.metadata.service,
            "version": runtime.metadata.version,
            "environment": runtime.metadata.environment,
        }

    @application.get("/ready", tags=["runtime"])
    def ready() -> dict[str, object]:
        """Report only the internal application readiness that actually exists."""

        runtime: RuntimeState = application.state.runtime
        return {
            "status": "ready" if runtime.ready else "not_ready",
            "service": runtime.metadata.service,
            "checks": {"application": "ok" if runtime.ready else "not_ready"},
        }

    return application


app = create_app()
