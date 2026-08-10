"""Cancellation-safe worker lifecycle foundation."""

import asyncio
from dataclasses import dataclass
from enum import StrEnum
from typing import Awaitable, Callable

from backend.core.logging import get_logger
from backend.core.safety import SafetyBoundary, SafetyStatus

logger = get_logger()

WorkerAction = Callable[[asyncio.Event], Awaitable[None]]


class WorkerState(StrEnum):
    """Observable states for a future worker process."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class BaseWorker:
    """A worker lifecycle shell with no automatic work or external I/O."""

    def __init__(
        self,
        name: str,
        *,
        safety: SafetyBoundary | None = None,
        action: WorkerAction | None = None,
    ) -> None:
        if not name or name.strip() != name:
            raise ValueError("Worker name must be a non-empty stable identifier")
        self.name = name
        self.safety = safety or SafetyBoundary()
        self.action = action
        self.state = WorkerState.CREATED
        self.failure: str | None = None
        self.blocked_reason: str | None = None
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        return self.state is WorkerState.RUNNING

    async def start(self) -> None:
        """Start explicitly, or remain blocked when safety is not satisfied."""

        if self.state is WorkerState.RUNNING:
            return
        self._stop_event.clear()
        self.failure = None
        self.blocked_reason = None
        if not self.safety.check_activity():
            self.state = WorkerState.BLOCKED
            self.blocked_reason = self.safety.status().reason
            logger.warning(
                "worker.safety_blocked",
                extra={"worker_name": self.name, "reason": self.blocked_reason},
            )
            return

        self.state = WorkerState.RUNNING
        logger.info("worker.started", extra={"worker_name": self.name})
        if self.action is not None:
            self._task = asyncio.create_task(self._run_action(), name=self.name)

    async def stop(self) -> None:
        """Stop explicitly and safely absorb task cancellation."""

        if self.state in {
            WorkerState.CREATED,
            WorkerState.BLOCKED,
            WorkerState.STOPPED,
            WorkerState.FAILED,
        }:
            self.state = WorkerState.STOPPED
            return

        self.state = WorkerState.STOPPING
        self._stop_event.set()
        task = self._task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info("worker.cancelled", extra={"worker_name": self.name})
        self._task = None
        self.state = WorkerState.STOPPED
        logger.info("worker.stopped", extra={"worker_name": self.name})

    async def _run_action(self) -> None:
        """Run only an explicitly supplied, testable future action."""

        try:
            await self.action(self._stop_event)  # type: ignore[misc]
        except asyncio.CancelledError:
            logger.info("worker.cancelled", extra={"worker_name": self.name})
            raise
        except Exception as exc:
            self.failure = f"{type(exc).__name__}: {exc}" or type(exc).__name__
            self.state = WorkerState.FAILED
            logger.exception(
                "worker.failed",
                extra={"worker_name": self.name, "failure": self.failure},
            )

    def block(self, reason: str) -> None:
        """Record that coordination prevented this worker from starting."""

        if self.state is WorkerState.CREATED:
            self.state = WorkerState.BLOCKED
            self.blocked_reason = reason

    def status(self) -> "WorkerStatus":
        """Return a stable, inspectable snapshot of this worker."""

        return WorkerStatus(
            name=self.name,
            state=self.state,
            running=self.is_running,
            failure=self.failure,
            blocked_reason=self.blocked_reason,
        )


@dataclass(frozen=True)
class WorkerStatus:
    """Immutable observable state for a registered worker."""

    name: str
    state: WorkerState
    running: bool
    failure: str | None
    blocked_reason: str | None


@dataclass(frozen=True)
class WorkerCoordinatorStatus:
    """Immutable aggregate state for a worker collection."""

    workers: tuple[WorkerStatus, ...]
    safety: SafetyStatus
    shutting_down: bool

    @property
    def all_stopped(self) -> bool:
        return all(worker.state is WorkerState.STOPPED for worker in self.workers)

    @property
    def failed_workers(self) -> tuple[WorkerStatus, ...]:
        return tuple(worker for worker in self.workers if worker.failure is not None)


class WorkerCoordinator:
    """Explicit, deterministic coordination for registered workers."""

    def __init__(self, *, safety: SafetyBoundary | None = None) -> None:
        self.safety = safety or SafetyBoundary()
        self._workers: dict[str, BaseWorker] = {}
        self._shutting_down = False

    def register(self, worker: BaseWorker) -> None:
        """Register a worker by its stable identity."""

        if worker.name in self._workers:
            raise ValueError(f"Worker already registered: {worker.name}")
        self._workers[worker.name] = worker

    def unregister(self, name: str) -> BaseWorker:
        """Remove a stopped worker and return it."""

        worker = self._workers[name]
        if worker.is_running or worker.state is WorkerState.STOPPING:
            raise RuntimeError(f"Worker must be stopped before unregistering: {name}")
        return self._workers.pop(name)

    def enumerate(self) -> tuple[str, ...]:
        """Return registered identities in deterministic order."""

        return tuple(sorted(self._workers))

    def inspect(self) -> tuple[WorkerStatus, ...]:
        """Return registered worker snapshots in deterministic order."""

        return tuple(self._workers[name].status() for name in self.enumerate())

    def status(self) -> WorkerCoordinatorStatus:
        """Return aggregate worker and safety state."""

        return WorkerCoordinatorStatus(
            workers=self.inspect(),
            safety=self.safety.status(),
            shutting_down=self._shutting_down,
        )

    async def start_all(self) -> WorkerCoordinatorStatus:
        """Start workers sequentially in deterministic identity order."""

        self._shutting_down = False
        if not self.safety.check_activity():
            reason = self.safety.status().reason
            for worker in self._workers.values():
                worker.block(reason)
            return self.status()

        for name in self.enumerate():
            await self._workers[name].start()
        return self.status()

    async def stop_all(self) -> WorkerCoordinatorStatus:
        """Stop every worker sequentially, continuing after worker failures."""

        for name in self.enumerate():
            try:
                await self._workers[name].stop()
            except Exception as exc:
                worker = self._workers[name]
                worker.failure = f"{type(exc).__name__}: {exc}" or type(exc).__name__
                worker.state = WorkerState.FAILED
                logger.exception(
                    "worker.stop_failed",
                    extra={"worker_name": name, "failure": worker.failure},
                )
        return self.status()

    async def shutdown(self) -> WorkerCoordinatorStatus:
        """Perform deterministic, idempotent coordinated shutdown."""

        self._shutting_down = True
        return await self.stop_all()