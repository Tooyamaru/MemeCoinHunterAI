from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
import pytest

from backend.api.main import create_app
from backend.core.config import Settings
from tests.test_operator_post_prepare_api import _payload
from tests.test_paper_fact_sourcing import _rti11


TOKEN = "controller-secret-token-1234567890"


@asynccontextmanager
async def _api(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'prepare-validation.db'}",
        operator_bearer_token=TOKEN,
        solana_rpc_url=None,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield app, client


@pytest.mark.asyncio
async def test_prepare_validation_decodes_without_prepare_service_or_case_mutation(tmp_path):
    payload = _payload(_rti11())

    async with _api(tmp_path) as (app, client):
        assert app.state.operator_prepare_service is None
        assert app.state.operator_case_registry.get("not-present") is None

        response = await client.post(
            "/api/v1/operator/paper-cases/validate",
            json=payload,
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        body = response.json()
        assert body["contract_version"] == "p01-oaf-01-prepare-validation-v1"
        assert body["status"] == "VALID"
        assert body["candidate_id"] == payload["candidate_id"]
        assert body["token_mint"] == payload["token_mint"]
        assert body["chain_id"] == payload["target"]["chain_id"]
        assert body["pool_address"] == payload["target"]["pool_address"]
        assert body["pfx_invocation_id"] == payload["paper_intent"]["pfx_invocation_id"]
        assert body["cip_invocation_id"] == payload["paper_intent"]["cip_invocation_id"]
        assert body["provider_connectivity_checked"] is False
        assert body["mutates_case"] is False
        assert body["simulation_only"] is True


@pytest.mark.asyncio
async def test_prepare_validation_rejects_invalid_canonical_payload_without_provider(tmp_path):
    payload = _payload(_rti11())
    del payload["paper_intent"]["replay_identity"]

    async with _api(tmp_path) as (_app, client):
        response = await client.post(
            "/api/v1/operator/paper-cases/validate",
            json=payload,
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

        assert response.status_code == 422
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["error"]["code"] == "operator_prepare_invalid"


@pytest.mark.asyncio
async def test_prepare_validation_requires_operator_auth(tmp_path):
    payload = _payload(_rti11())

    async with _api(tmp_path) as (_app, client):
        response = await client.post(
            "/api/v1/operator/paper-cases/validate",
            json=payload,
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "operator_auth_required"
