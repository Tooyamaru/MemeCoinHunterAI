"""Bounded end-to-end verification of the controlled-paper operator chain.

This suite intentionally starts from an already prepared canonical case so it can
verify the HTTP/operator boundaries without provider/network access.  Preparation
itself remains covered by the dedicated prepare transport tests.
"""

from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
import pytest

from backend.api.main import create_app
from backend.application.operator_paper_case_persist import OperatorPaperCasePersistService
from backend.application.operator_paper_case_run import OperatorPaperCaseRunService
from backend.application.paper_lifecycle_persistence import (
    PaperLifecyclePersistenceOutcome,
    PaperLifecyclePersistenceResult,
)
from backend.core.config import Settings
from tests.test_operator_paper_case_persist import _lifecycle_terminal
from tests.test_operator_paper_case_registry import _prepared
from tests.test_operator_paper_case_run import _oci_result


TOKEN = "controller-secret-token-1234567890"


@asynccontextmanager
async def _api(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'operator-e2e.db'}",
        operator_bearer_token=TOKEN,
        operator_case_registry_capacity=8,
        operator_case_ttl_seconds=600,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield app, client


@pytest.mark.asyncio
async def test_review_run_once_and_fail_closed_boundaries_share_one_case(tmp_path):
    """Review and run remain explicit, authenticated, digest-bound and once-only."""
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
        headers = {"Authorization": f"Bearer {TOKEN}"}
        review_path = f"/api/v1/operator/paper-cases/{record.handle}"
        run_path = f"{review_path}/run"

        review = await client.get(review_path, headers=headers)
        assert review.status_code == 200
        assert review.json()["handle"] == record.handle
        assert review.json()["case_digest"] == record.case_digest

        unauthenticated = await client.post(
            run_path,
            json={"case_digest": record.case_digest, "confirm_run": True},
        )
        assert unauthenticated.status_code == 401
        assert calls == []

        mismatch = await client.post(
            run_path,
            json={"case_digest": "0" * 64, "confirm_run": True},
            headers=headers,
        )
        assert mismatch.status_code == 409
        assert mismatch.json()["error"]["code"] == "operator_case_digest_mismatch"
        assert calls == []

        first = await client.post(
            run_path,
            json={"case_digest": record.case_digest, "confirm_run": True},
            headers=headers,
        )
        assert first.status_code == 200
        assert first.json()["state"] == "RUN_TERMINAL"
        assert first.json()["simulation_only"] is True
        assert len(calls) == 1
        assert calls[0].cip_result is record.prepared.cip_result

        second = await client.post(
            run_path,
            json={"case_digest": record.case_digest, "confirm_run": True},
            headers=headers,
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "operator_case_not_runnable"
        assert len(calls) == 1

        final_review = await client.get(review_path, headers=headers)
        assert final_review.status_code == 200
        assert final_review.json()["state"] == "RUN_TERMINAL"


@pytest.mark.asyncio
async def test_persist_once_readback_projection_and_fail_closed_boundaries_share_one_case(tmp_path):
    """Persist/readback handoff preserves the exact lifecycle digest and is once-only."""
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
        headers = {"Authorization": f"Bearer {TOKEN}"}
        review_path = f"/api/v1/operator/paper-cases/{terminal.handle}"
        persist_path = f"{review_path}/persist"
        oci = terminal.oci_result
        osc = oci.osc02_result
        lifecycle = osc.lifecycle_result
        payload = {
            "case_digest": terminal.case_digest,
            "oci_digest": oci.result_digest,
            "osc_digest": osc.result_digest,
            "lifecycle_result_digest": lifecycle.digest,
            "confirm_persist": True,
        }

        unauthenticated = await client.post(persist_path, json=payload)
        assert unauthenticated.status_code == 401
        assert calls == []

        mismatch_payload = dict(payload)
        mismatch_payload["lifecycle_result_digest"] = "0" * 64
        mismatch = await client.post(persist_path, json=mismatch_payload, headers=headers)
        assert mismatch.status_code == 409
        assert mismatch.json()["error"]["code"] == "operator_lifecycle_digest_mismatch"
        assert calls == []

        first = await client.post(persist_path, json=payload, headers=headers)
        assert first.status_code == 200
        body = first.json()
        assert body["state"] == "PERSIST_TERMINAL"
        assert body["persistence_outcome"] == "STORED"
        assert body["lifecycle_result_digest"] == lifecycle.digest
        assert body["readback_path"] == f"/api/v1/paper-lifecycle-results/{lifecycle.digest}"
        assert body["simulation_only"] is True
        assert calls == [lifecycle]

        second = await client.post(persist_path, json=payload, headers=headers)
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "operator_case_not_persistable"
        assert calls == [lifecycle]

        final_review = await client.get(review_path, headers=headers)
        assert final_review.status_code == 200
        review_body = final_review.json()
        assert review_body["state"] == "PERSIST_TERMINAL"
        assert review_body["lifecycle_result_digest"] == lifecycle.digest
        assert review_body["readback_path"] == body["readback_path"]
        assert review_body["simulation_only"] is True
