from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
import pytest

from backend.api.main import create_app
from backend.core.config import Settings
from tests.test_operator_paper_case_registry import _prepared


TOKEN = "controller-secret-token-1234567890"


@asynccontextmanager
async def _api(tmp_path, *, token=TOKEN):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'oaf-review.db'}",
        operator_bearer_token=token,
        operator_case_registry_capacity=4,
        operator_case_ttl_seconds=600,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield app, client


@pytest.mark.asyncio
async def test_authenticated_review_returns_safe_projection_without_owner_rerun(tmp_path):
    async with _api(tmp_path) as (app, client):
        prepared = _prepared()
        record = app.state.operator_case_registry.put(prepared)

        response = await client.get(
            f"/api/v1/operator/paper-cases/{record.handle}",
            headers={"Authorization": f"Bearer {TOKEN}", "X-Request-ID": "oaf-review-1"},
        )

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        body = response.json()
        assert body["handle"] == record.handle
        assert body["case_digest"] == record.case_digest
        assert body["state"] == "REVIEW_READY"
        assert body["candidate_id"] == prepared.request.rti11_result.request.candidate_id
        assert body["token_mint"] == prepared.request.rti11_result.request.target.token_mint
        assert body["pool_address"] == prepared.request.rti11_result.request.target.pool_address
        assert body["cip_outcome"] == "REQUEST_PREPARED"
        assert body["simulation_only"] is True
        assert "historical_price_proxy" in body["source_label"]
        assert "osc02_request" not in body
        assert "authorization_result" not in body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers,expected_status,expected_code",
    (
        ({}, 401, "operator_auth_required"),
        ({"Authorization": "Bearer wrong"}, 401, "operator_auth_invalid"),
    ),
)
async def test_review_requires_fail_closed_operator_auth(
    tmp_path, headers, expected_status, expected_code
):
    async with _api(tmp_path) as (app, client):
        record = app.state.operator_case_registry.put(_prepared())
        response = await client.get(
            f"/api/v1/operator/paper-cases/{record.handle}",
            headers=headers,
        )
        assert response.status_code == expected_status
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["error"]["code"] == expected_code


@pytest.mark.asyncio
async def test_unconfigured_operator_access_returns_503(tmp_path):
    async with _api(tmp_path, token=None) as (app, client):
        record = app.state.operator_case_registry.put(_prepared())
        response = await client.get(
            f"/api/v1/operator/paper-cases/{record.handle}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "operator_access_unavailable"


@pytest.mark.asyncio
async def test_missing_or_expired_handle_is_safe_404(tmp_path):
    async with _api(tmp_path) as (_app, client):
        response = await client.get(
            "/api/v1/operator/paper-cases/not-present-handle",
            headers={"Authorization": f"Bearer {TOKEN}", "X-Request-ID": "missing-case"},
        )
        assert response.status_code == 404
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-request-id"] == "missing-case"
        assert response.json()["error"]["code"] == "operator_case_not_found"


@pytest.mark.asyncio
async def test_review_route_is_get_only(tmp_path):
    async with _api(tmp_path) as (app, client):
        record = app.state.operator_case_registry.put(_prepared())
        path = f"/api/v1/operator/paper-cases/{record.handle}"
        headers = {"Authorization": f"Bearer {TOKEN}"}
        responses = [
            await client.post(path, headers=headers),
            await client.put(path, headers=headers),
            await client.patch(path, headers=headers),
            await client.delete(path, headers=headers),
        ]
        assert [response.status_code for response in responses] == [405, 405, 405, 405]
