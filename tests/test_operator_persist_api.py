from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
import pytest

from backend.api.main import create_app
from backend.application.operator_paper_case_persist import (
    OperatorPaperCasePersistService,
)
from backend.application.paper_lifecycle_persistence import (
    PaperLifecyclePersistenceOutcome,
    PaperLifecyclePersistenceResult,
)
from backend.core.config import Settings
from tests.test_operator_paper_case_persist import _lifecycle_terminal


TOKEN = "controller-secret-token-1234567890"


@asynccontextmanager
async def _api(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'oaf-persist.db'}",
        operator_bearer_token=TOKEN,
        operator_case_registry_capacity=4,
        operator_case_ttl_seconds=600,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield app, client


def _payload(record):
    oci = record.oci_result
    osc = oci.osc02_result
    lifecycle = osc.lifecycle_result
    return {
        "case_digest": record.case_digest,
        "oci_digest": oci.result_digest,
        "osc_digest": osc.result_digest,
        "lifecycle_result_digest": lifecycle.digest,
        "confirm_persist": True,
    }


@pytest.mark.asyncio
async def test_authenticated_persist_calls_rti03_once_and_exposes_readback(tmp_path):
    calls = []

    class Persistence:
        async def persist(self, lifecycle):
            calls.append(lifecycle)
            return PaperLifecyclePersistenceResult(
                outcome=PaperLifecyclePersistenceOutcome.STORED,
                reason_codes=(),
                lifecycle_result_digest=lifecycle.digest,
                artifact_count=12,
            )

    async with _api(tmp_path) as (app, client):
        terminal = _lifecycle_terminal(app.state.operator_case_registry)
        app.state.operator_persist_service = OperatorPaperCasePersistService(
            registry=app.state.operator_case_registry,
            persistence=Persistence(),
        )
        path = f"/api/v1/operator/paper-cases/{terminal.handle}/persist"
        headers = {"Authorization": f"Bearer {TOKEN}"}
        payload = _payload(terminal)

        first = await client.post(path, json=payload, headers=headers)
        second = await client.post(path, json=payload, headers=headers)

        assert first.status_code == 200
        assert first.headers["cache-control"] == "no-store"
        body = first.json()
        assert body["state"] == "PERSIST_TERMINAL"
        assert body["outcome"] == "PERSIST_TERMINAL"
        assert body["persistence_outcome"] == "STORED"
        assert body["lifecycle_result_digest"] == payload["lifecycle_result_digest"]
        assert body["readback_path"].endswith(payload["lifecycle_result_digest"])
        assert body["artifact_count"] == 12
        assert body["simulation_only"] is True
        assert calls == [terminal.oci_result.osc02_result.lifecycle_result]

        assert second.status_code == 409
        assert second.json()["error"]["code"] == "operator_case_not_persistable"
        assert len(calls) == 1

        review = await client.get(
            f"/api/v1/operator/paper-cases/{terminal.handle}",
            headers=headers,
        )
        assert review.status_code == 200
        review_body = review.json()
        assert review_body["state"] == "PERSIST_TERMINAL"
        assert review_body["persistence_outcome"] == "STORED"
        assert review_body["lifecycle_result_digest"] == payload["lifecycle_result_digest"]
        assert review_body["readback_path"].endswith(payload["lifecycle_result_digest"])


@pytest.mark.asyncio
async def test_persist_requires_auth_before_service_call(tmp_path):
    calls = []

    class Service:
        async def persist_once(self, **kwargs):
            calls.append(kwargs)
            raise AssertionError("must not run")

    async with _api(tmp_path) as (app, client):
        terminal = _lifecycle_terminal(app.state.operator_case_registry)
        app.state.operator_persist_service = Service()
        response = await client.post(
            f"/api/v1/operator/paper-cases/{terminal.handle}/persist",
            json=_payload(terminal),
        )

        assert response.status_code == 401
        assert calls == []


@pytest.mark.asyncio
async def test_persist_confirmation_is_required_before_service_call(tmp_path):
    calls = []

    class Service:
        async def persist_once(self, **kwargs):
            calls.append(kwargs)
            raise AssertionError("must not run")

    async with _api(tmp_path) as (app, client):
        terminal = _lifecycle_terminal(app.state.operator_case_registry)
        app.state.operator_persist_service = Service()
        payload = _payload(terminal)
        payload["confirm_persist"] = False

        response = await client.post(
            f"/api/v1/operator/paper-cases/{terminal.handle}/persist",
            json=payload,
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "operator_persist_confirmation_required"
        assert calls == []


@pytest.mark.asyncio
async def test_persist_digest_mismatch_is_conflict_without_rti03_call(tmp_path):
    calls = []

    class Persistence:
        async def persist(self, lifecycle):
            calls.append(lifecycle)
            raise AssertionError("must not run")

    async with _api(tmp_path) as (app, client):
        terminal = _lifecycle_terminal(app.state.operator_case_registry)
        app.state.operator_persist_service = OperatorPaperCasePersistService(
            registry=app.state.operator_case_registry,
            persistence=Persistence(),
        )
        payload = _payload(terminal)
        payload["lifecycle_result_digest"] = "0" * 64

        response = await client.post(
            f"/api/v1/operator/paper-cases/{terminal.handle}/persist",
            json=payload,
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "operator_lifecycle_digest_mismatch"
        assert calls == []


@pytest.mark.asyncio
async def test_uncertain_persist_is_terminal_without_automatic_retry(tmp_path):
    calls = []

    class Persistence:
        async def persist(self, lifecycle):
            calls.append(lifecycle)
            raise RuntimeError("private uncertain persistence failure")

    async with _api(tmp_path) as (app, client):
        terminal = _lifecycle_terminal(app.state.operator_case_registry)
        app.state.operator_persist_service = OperatorPaperCasePersistService(
            registry=app.state.operator_case_registry,
            persistence=Persistence(),
        )
        path = f"/api/v1/operator/paper-cases/{terminal.handle}/persist"
        payload = _payload(terminal)
        headers = {"Authorization": f"Bearer {TOKEN}"}

        first = await client.post(path, json=payload, headers=headers)
        second = await client.post(path, json=payload, headers=headers)

        assert first.status_code == 200
        assert first.json()["state"] == "PERSIST_OUTCOME_UNKNOWN"
        assert first.json()["outcome"] == "PERSIST_OUTCOME_UNKNOWN"
        assert first.json()["persistence_outcome"] is None
        assert second.status_code == 409
        assert len(calls) == 1
