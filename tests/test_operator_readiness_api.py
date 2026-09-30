from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
import pytest

from backend.api.main import create_app
from backend.core.config import Settings


TOKEN = "controller-secret-token-1234567890"


@asynccontextmanager
async def _api(
    tmp_path,
    *,
    app_env="test",
    solana_rpc_url="https://solana.example",
    ack=False,
    database_configured=True,
):
    settings = Settings(
        _env_file=None,
        app_env=app_env,
        database_url=(
            f"sqlite+aiosqlite:///{tmp_path / 'operator-readiness.db'}"
            if database_configured
            else None
        ),
        operator_bearer_token=TOKEN,
        operator_process_local_registry_ack=ack,
        solana_rpc_url=solana_rpc_url,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield app, client


@pytest.mark.asyncio
async def test_authenticated_operator_readiness_is_no_store_and_no_provider_probe(tmp_path):
    async with _api(tmp_path) as (_app, client):
        response = await client.get(
            "/api/v1/operator/paper-cases/readiness",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        body = response.json()
        assert body["contract_version"] == "p01-oaf-01-operator-readiness-v1"
        assert body["status"] == "READY"
        assert body["checks"]["database"] == "connected"
        assert body["checks"]["case_registry"] == "enabled"
        assert body["checks"]["prepare_service"] == "configured"
        assert body["checks"]["run_service"] == "configured"
        assert body["checks"]["persist_service"] == "configured"
        assert body["process_local_registry"] is True
        assert body["provider_connectivity_checked"] is False
        assert body["simulation_only"] is True


@pytest.mark.asyncio
async def test_operator_readiness_requires_connected_durable_database(tmp_path):
    async with _api(tmp_path, database_configured=False) as (_app, client):
        response = await client.get(
            "/api/v1/operator/paper-cases/readiness",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "NOT_READY"
        assert body["checks"]["database"] == "not_configured"
        assert body["checks"]["case_registry"] == "enabled"
        assert body["checks"]["prepare_service"] == "configured"
        assert body["checks"]["run_service"] == "configured"
        assert body["checks"]["persist_service"] == "configured"
        assert body["provider_connectivity_checked"] is False
        assert body["simulation_only"] is True


@pytest.mark.asyncio
async def test_operator_readiness_requires_auth_before_configuration_projection(tmp_path):
    async with _api(tmp_path) as (_app, client):
        response = await client.get("/api/v1/operator/paper-cases/readiness")

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "operator_auth_required"


@pytest.mark.asyncio
async def test_operator_readiness_is_not_ready_without_prepare_source_configuration(tmp_path):
    async with _api(tmp_path, solana_rpc_url=None) as (_app, client):
        response = await client.get(
            "/api/v1/operator/paper-cases/readiness",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "NOT_READY"
        assert body["checks"]["prepare_service"] == "unavailable"
        assert body["checks"]["run_service"] == "configured"
        assert body["checks"]["persist_service"] == "configured"
        assert body["provider_connectivity_checked"] is False


@pytest.mark.asyncio
async def test_operator_readiness_reflects_fail_closed_production_registry(tmp_path):
    async with _api(
        tmp_path,
        app_env="production",
        solana_rpc_url="https://solana.example",
        ack=False,
    ) as (_app, client):
        response = await client.get(
            "/api/v1/operator/paper-cases/readiness",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "NOT_READY"
        assert body["checks"]["case_registry"] == "unavailable"
        assert body["checks"]["prepare_service"] == "unavailable"
        assert body["checks"]["run_service"] == "unavailable"
        assert body["checks"]["persist_service"] == "unavailable"
