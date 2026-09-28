from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
import pytest

from backend.api.main import create_app
from backend.application.operator_paper_case_registry import OperatorPaperCaseRegistry
from backend.core.config import Settings
from tests.test_operator_paper_case_registry import _prepared


TOKEN = "controller-secret-token-1234567890"


@asynccontextmanager
async def _api(tmp_path, *, ack: bool):
    settings = Settings(
        _env_file=None,
        app_env="production",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'deployment-guard.db'}",
        operator_bearer_token=TOKEN,
        operator_process_local_registry_ack=ack,
        operator_case_registry_capacity=4,
        operator_case_ttl_seconds=600,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield app, client


@pytest.mark.asyncio
async def test_production_operator_registry_is_fail_closed_without_explicit_ack(tmp_path):
    async with _api(tmp_path, ack=False) as (app, client):
        assert app.state.operator_registry_enabled is False
        assert app.state.operator_case_registry is None
        assert app.state.operator_run_service is None
        assert app.state.operator_persist_service is None
        assert app.state.operator_prepare_service is None

        ready = await client.get("/ready")
        assert ready.status_code == 503
        assert ready.json()["checks"]["operator_case_registry"] == "process_local_ack_required"

        review = await client.get(
            "/api/v1/operator/paper-cases/not-present-handle",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert review.status_code == 503
        assert review.json()["error"]["code"] == "OPERATOR_CASE_REGISTRY_UNAVAILABLE"


@pytest.mark.asyncio
async def test_production_operator_registry_requires_ack_but_remains_process_local(tmp_path):
    async with _api(tmp_path, ack=True) as (app, client):
        assert app.state.operator_registry_enabled is True
        assert isinstance(app.state.operator_case_registry, OperatorPaperCaseRegistry)

        record = app.state.operator_case_registry.put(_prepared())

        ready = await client.get("/ready")
        assert ready.status_code == 200
        assert ready.json()["checks"]["operator_case_registry"] == "process_local_acknowledged"

        review = await client.get(
            f"/api/v1/operator/paper-cases/{record.handle}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert review.status_code == 200
        assert review.json()["case_digest"] == record.case_digest


@pytest.mark.asyncio
async def test_test_environment_does_not_require_deployment_ack(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test-guard.db'}",
        operator_bearer_token=TOKEN,
        operator_process_local_registry_ack=False,
    )
    app = create_app(settings)

    async with app.router.lifespan_context(app):
        assert app.state.operator_registry_enabled is True
        assert isinstance(app.state.operator_case_registry, OperatorPaperCaseRegistry)
