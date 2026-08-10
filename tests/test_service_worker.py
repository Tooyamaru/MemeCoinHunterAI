import asyncio

import pytest

from backend.application.service import ApplicationService, ServiceRequestContext
from backend.core.config import Settings
from backend.core.database import DatabaseRuntime
from backend.core.runtime import RuntimeMetadata, RuntimeState
from backend.core.safety import SafetyBoundary
from backend.workers.runtime import BaseWorker, WorkerCoordinator, WorkerState


def make_runtime() -> RuntimeState:
    settings = Settings(_env_file=None, app_env="test", database_url=None)
    return RuntimeState(metadata=RuntimeMetadata.from_settings(settings), ready=True)


def make_service() -> ApplicationService:
    settings = Settings(_env_file=None, app_env="test", database_url=None)
    return ApplicationService(runtime=make_runtime(), database=DatabaseRuntime(settings))


@pytest.mark.asyncio
async def test_application_service_is_instantiable_and_testable_without_http() -> None:
    service = make_service()

    assert service.initialized is False
    await service.initialize()
    status = service.status(ServiceRequestContext(request_id="service-test"))

    assert service.initialized is True
    assert status.request_id == "service-test"
    assert status.ready is True
    assert status.safety.action_allowed is False
    assert status.workers.workers == ()

    await service.shutdown()
    assert service.initialized is False


@pytest.mark.asyncio
async def test_worker_identity_and_explicit_lifecycle() -> None:
    safety = SafetyBoundary(watchdog_healthy=True, kill_switch_active=False)
    worker = BaseWorker("foundation-test-worker", safety=safety, action=wait_for_stop)

    assert worker.name == "foundation-test-worker"
    assert worker.state is WorkerState.CREATED
    await worker.start()
    assert worker.state is WorkerState.RUNNING
    await worker.stop()
    assert worker.state is WorkerState.STOPPED


@pytest.mark.asyncio
async def test_worker_cancellation_is_safe() -> None:
    safety = SafetyBoundary(watchdog_healthy=True, kill_switch_active=False)
    worker = BaseWorker("cancellation-test-worker", safety=safety, action=wait_forever)

    await worker.start()
    task = worker._task
    assert task is not None
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await worker.stop()

    assert worker.state is WorkerState.STOPPED


@pytest.mark.asyncio
async def test_worker_does_not_start_when_kill_switch_is_active() -> None:
    activity_started = False

    async def record_activity(stop_event: asyncio.Event) -> None:
        nonlocal activity_started
        activity_started = True
        await stop_event.wait()

    worker = BaseWorker(
        "blocked-worker",
        safety=SafetyBoundary(watchdog_healthy=True, kill_switch_active=True),
        action=record_activity,
    )

    await worker.start()
    await asyncio.sleep(0)

    assert worker.state is WorkerState.BLOCKED
    assert activity_started is False
    await worker.stop()


def test_worker_coordinator_registers_inspects_and_rejects_duplicates() -> None:
    coordinator = WorkerCoordinator()
    first = BaseWorker("zulu-worker")
    second = BaseWorker("alpha-worker")

    coordinator.register(first)
    coordinator.register(second)

    assert coordinator.enumerate() == ("alpha-worker", "zulu-worker")
    assert tuple(status.name for status in coordinator.inspect()) == (
        "alpha-worker",
        "zulu-worker",
    )
    assert first.state is WorkerState.CREATED
    with pytest.raises(ValueError, match="already registered"):
        coordinator.register(BaseWorker("alpha-worker"))


@pytest.mark.asyncio
async def test_worker_coordinator_starts_and_stops_deterministically() -> None:
    events: list[str] = []
    safety = SafetyBoundary(watchdog_healthy=True, kill_switch_active=False)

    async def record_start(stop_event: asyncio.Event) -> None:
        events.append("started")
        await stop_event.wait()

    coordinator = WorkerCoordinator(safety=safety)
    first = BaseWorker("first-worker", safety=safety, action=record_start)
    second = BaseWorker("second-worker", safety=safety, action=record_start)
    coordinator.register(second)
    coordinator.register(first)

    status = await coordinator.start_all()
    assert tuple(worker.state for worker in status.workers) == (
        WorkerState.RUNNING,
        WorkerState.RUNNING,
    )
    await asyncio.sleep(0)
    await coordinator.stop_all()
    assert coordinator.status().all_stopped is True
    assert events == ["started", "started"]


@pytest.mark.asyncio
async def test_worker_coordinator_shutdown_handles_cancelled_worker() -> None:
    safety = SafetyBoundary(watchdog_healthy=True, kill_switch_active=False)
    coordinator = WorkerCoordinator(safety=safety)
    worker = BaseWorker("cancelled-worker", safety=safety, action=wait_forever)
    coordinator.register(worker)

    await coordinator.start_all()
    assert worker._task is not None
    worker._task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await worker._task

    status = await coordinator.shutdown()
    assert status.all_stopped is True
    assert status.shutting_down is True


@pytest.mark.asyncio
async def test_worker_failure_is_visible_and_shutdown_continues() -> None:
    safety = SafetyBoundary(watchdog_healthy=True, kill_switch_active=False)

    async def fail_worker(stop_event: asyncio.Event) -> None:
        raise RuntimeError("expected worker failure")

    coordinator = WorkerCoordinator(safety=safety)
    failed = BaseWorker("failed-worker", safety=safety, action=fail_worker)
    healthy = BaseWorker("healthy-worker", safety=safety, action=wait_for_stop)
    coordinator.register(failed)
    coordinator.register(healthy)

    await coordinator.start_all()
    await asyncio.sleep(0)
    failed_status = coordinator.status().failed_workers
    assert len(failed_status) == 1
    assert failed_status[0].name == "failed-worker"
    assert failed_status[0].failure == "RuntimeError: expected worker failure"

    status = await coordinator.shutdown()
    assert status.all_stopped is True


@pytest.mark.asyncio
async def test_worker_coordinator_propagates_unsafe_safety() -> None:
    coordinator = WorkerCoordinator()
    worker = BaseWorker("blocked-by-coordinator")
    coordinator.register(worker)

    status = await coordinator.start_all()

    assert status.safety.action_allowed is False
    assert status.workers[0].state is WorkerState.BLOCKED
    assert status.workers[0].blocked_reason == "safe_default"
    assert worker._task is None


def test_worker_coordinator_unregisters_only_stopped_workers() -> None:
    coordinator = WorkerCoordinator()
    worker = BaseWorker("removable-worker")
    coordinator.register(worker)

    removed = coordinator.unregister("removable-worker")

    assert removed is worker
    assert coordinator.enumerate() == ()


def test_safety_defaults_to_no_action() -> None:
    safety = SafetyBoundary()

    assert safety.check_activity() is False
    assert safety.status().kill_switch_active is True
    assert safety.status().watchdog_healthy is False


def test_worker_import_has_no_automatic_task() -> None:
    worker = BaseWorker("import-safe-worker")

    assert worker.state is WorkerState.CREATED
    assert worker._task is None


async def wait_for_stop(stop_event: asyncio.Event) -> None:
    await stop_event.wait()


async def wait_forever(stop_event: asyncio.Event) -> None:
    await asyncio.Future()