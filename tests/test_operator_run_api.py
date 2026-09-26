from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
import pytest

from backend.api.main import create_app
from backend.application.operator_paper_case_run import OperatorPaperCaseRunService
from backend.core.config import Settings
from tests.test_operator_paper_case_registry import _prepared
from tests.test_operator_paper_case_run import _oci_result


TOKEN = "controller-secret-token-1234567890"


@asynccontextmanager
async def _api(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'oaf-run.db'}",
        operator_bearer_token=TOKEN,
        operator_case_registry_capacity=4,
        operator_case_ttl_seconds=600,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield app, client


@pytest.mark.asyncio
async def test_authenticated_run_claims_exact_case_once_and_returns_safe_projection(tmp_path):
    calls = []

    class Oci:
        def run(self, request):
            calls.append(request)
            return _oci_result(request)

    async with _api(tmp_path) as (app, client):
        record = app.state.operator_case_registry.put(_prepared())
        app.state.operator_run_service = OperatorPaperCaseRunService(
            registry=app.state.operator_case_registry,
            oci=Oci(),
        )
        path = f"/api/v1/operator/paper-cases/{record.handle}/run"
        headers = {"Authorization": f"Bearer {TOKEN}"}
        payload = {"case_digest": record.case_digest, "confirm_run": True}

        first = await client.post(path, json=payload, headers=headers)
        second = await client.post(path, json=payload, headers=headers)

        assert first.status_code == 200
        assert first.headers["cache-control"] == "no-store"
        body = first.json()
        assert body["state"] == "RUN_TERMINAL"
        assert body["outcome"] == "RUN_TERMINAL"
        assert body["oci_outcome"] == "OSC_RESULT_RETURNED"
        assert body["osc_outcome"] == "OWNER_UNAVAILABLE"
        assert body["lifecycle_result_digest"] is None
        assert body["persist_eligible"] is False
        assert body["simulation_only"] is True
        assert len(calls) == 1
        assert calls[0].cip_result is record.prepared.cip_result

        assert second.status_code == 409
        assert second.json()["error"]["code"] == "operator_case_not_runnable"
        assert len(calls) == 1

        review = await client.get(
            f"/api/v1/operator/paper-cases/{record.handle}",
            headers=headers,
        )
        assert review.status_code == 200
        assert review.json()["state"] == "RUN_TERMINAL"


@pytest.mark.asyncio
async def test_run_requires_auth_before_case_lookup_or_oci(tmp_path):
    calls = []

    class Oci:
        def run(self, request):
            calls.append(request)
            raise AssertionError("must not run")

    async with _api(tmp_path) as (app, client):
        record = app.state.operator_case_registry.put(_prepared())
        app.state.operator_run_service = OperatorPaperCaseRunService(
            registry=app.state.operator_case_registry,
            oci=Oci(),
        )
        response = await client.post(
            f"/api/v1/operator/paper-cases/{record.handle}/run",
            json={"case_digest": record.case_digest, "confirm_run": True},
        )

        assert response.status_code == 401
        assert calls == []


@pytest.mark.asyncio
async def test_run_confirmation_is_required_before_service_call(tmp_path):
    calls = []

    class Service:
        def run_once(self, **kwargs):
            calls.append(kwargs)
            raise AssertionError("must not run")

    async with _api(tmp_path) as (app, client):
        record = app.state.operator_case_registry.put(_prepared())
        app.state.operator_run_service = Service()
        response = await client.post(
            f"/api/v1/operator/paper-cases/{record.handle}/run",
            json={"case_digest": record.case_digest, "confirm_run": False},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "operator_run_confirmation_required"
        assert calls == []


@pytest.mark.asyncio
async def test_run_digest_mismatch_stops_before_oci(tmp_path):
    calls = []

    class Oci:
        def run(self, request):
            calls.append(request)
            raise AssertionError("must not run")

    async with _api(tmp_path) as (app, client):
        record = app.state.operator_case_registry.put(_prepared())
        app.state.operator_run_service = OperatorPaperCaseRunService(
            registry=app.state.operator_case_registry,
            oci=Oci(),
        )
        response = await client.post(
            f"/api/v1/operator/paper-cases/{record.handle}/run",
            json={"case_digest": "0" * 64, "confirm_run": True},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "operator_case_digest_mismatch"
        assert calls == []


@pytest.mark.asyncio
async def test_uncertain_run_is_terminal_and_not_retried(tmp_path):
    calls = []

    class Oci:
        def run(self, request):
            calls.append(request)
            raise RuntimeError("private uncertain failure")

    async with _api(tmp_path) as (app, client):
        record = app.state.operator_case_registry.put(_prepared())
        app.state.operator_run_service = OperatorPaperCaseRunService(
            registry=app.state.operator_case_registry,
            oci=Oci(),
        )
        path = f"/api/v1/operator/paper-cases/{record.handle}/run"
        headers = {"Authorization": f"Bearer {TOKEN}"}
        payload = {"case_digest": record.case_digest, "confirm_run": True}

        first = await client.post(path, json=payload, headers=headers)
        second = await client.post(path, json=payload, headers=headers)

        assert first.status_code == 200
        assert first.json()["state"] == "RUN_OUTCOME_UNKNOWN"
        assert first.json()["outcome"] == "RUN_OUTCOME_UNKNOWN"
        assert first.json()["oci_outcome"] is None
        assert second.status_code == 409
        assert len(calls) == 1
