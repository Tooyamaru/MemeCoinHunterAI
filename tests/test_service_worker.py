import asyncio

import pytest

from backend.application.service import ApplicationService, ServiceRequestContext
from backend.core.config import Settings
from backend.core.database import DatabaseRuntime
from backend.core.runtime import RuntimeMetadata, RuntimeState
from backend.core.safety import SafetyBoundary
from backend.workers.runtime import BaseWorker, WorkerState


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