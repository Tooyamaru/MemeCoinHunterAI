"""Minimal application-service boundary for orchestration and context reuse."""

from dataclasses import dataclass

from backend.core.database import DatabaseRuntime
from backend.core.logging import get_logger
from backend.core.request_id import get_request_id
from backend.core.runtime import RuntimeState
from backend.core.safety import SafetyBoundary, SafetyStatus
from backend.workers.runtime import (
    BaseWorker,
    WorkerCoordinator,
    WorkerCoordinatorStatus,
)

logger = get_logger()


@dataclass(frozen=True)
class ServiceRequestContext:
    """Request context passed into service methods without requiring HTTP."""

    request_id: str = "-"

    @classmethod
    def current(cls) -> "ServiceRequestContext":
        """Reuse the existing request correlation context."""

        return cls(request_id=get_request_id())


@dataclass(frozen=True)
class ServiceStatus:
    """Typed service status returned to callers and tests."""

    service: str
    request_id: str
    initialized: bool
    application_ready: bool
    database_ready: bool
    safety: SafetyStatus
    workers: WorkerCoordinatorStatus

    @property
    def ready(self) -> bool:
        return self.application_ready and self.database_ready


class ApplicationService:
    """Coordinates application boundaries without owning HTTP or persistence."""

    def __init__(
        self,
        *,
        runtime: RuntimeState,
        database: DatabaseRuntime,
        safety: SafetyBoundary | None = None,
    ) -> None:
        self.runtime = runtime
        self.database = database
        self.safety = safety or SafetyBoundary()
        self.workers = WorkerCoordinator(safety=self.safety)
        self.initialized = False

    async def initialize(self) -> None:
        """Initialize the service boundary without starting future work."""

        self.initialized = True
        logger.info(
            "service.initialized",
            extra={
                "service": self.runtime.metadata.service,
                "safety_action_allowed": self.safety.check_activity(),
            },
        )

    async def shutdown(self) -> None:
        """Close the service boundary deterministically."""

        await self.workers.shutdown()
        self.initialized = False
        logger.info("service.shutdown", extra={"service": self.runtime.metadata.service})

    def register_worker(self, worker: BaseWorker) -> None:
        """Register a worker without starting it."""

        self.workers.register(worker)

    def unregister_worker(self, name: str) -> BaseWorker:
        """Unregister a worker after it has been stopped."""

        return self.workers.unregister(name)

    async def start_workers(self) -> WorkerCoordinatorStatus:
        """Start registered workers through the coordination boundary."""

        return await self.workers.start_all()

    async def stop_workers(self) -> WorkerCoordinatorStatus:
        """Stop registered workers through the coordination boundary."""

        return await self.workers.stop_all()

    def status(self, context: ServiceRequestContext | None = None) -> ServiceStatus:
        """Return application state without requiring an HTTP request."""

        request_context = context or ServiceRequestContext.current()
        return ServiceStatus(
            service=self.runtime.metadata.service,
            request_id=request_context.request_id,
            initialized=self.initialized,
            application_ready=self.runtime.ready,
            database_ready=self.database.is_ready,
            safety=self.safety.status(),
            workers=self.workers.status(),
        )