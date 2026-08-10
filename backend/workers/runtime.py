"""Cancellation-safe worker lifecycle foundation."""

import asyncio
from enum import StrEnum
from typing import Awaitable, Callable

from backend.core.logging import get_logger
from backend.core.safety import SafetyBoundary

logger = get_logger()

WorkerAction = Callable[[asyncio.Event], Awaitable[None]]


class WorkerState(StrEnum):
    """Observable states for a future worker process."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"


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
        if not self.safety.check_activity():
            self.state = WorkerState.BLOCKED
            logger.warning(
                "worker.safety_blocked",
                extra={"worker_name": self.name, "reason": self.safety.status().reason},
            )
            return

        self.state = WorkerState.RUNNING
        logger.info("worker.started", extra={"worker_name": self.name})
        if self.action is not None:
            self._task = asyncio.create_task(self._run_action(), name=self.name)

    async def stop(self) -> None:
        """Stop explicitly and safely absorb task cancellation."""

        if self.state in {WorkerState.CREATED, WorkerState.BLOCKED, WorkerState.STOPPED}:
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