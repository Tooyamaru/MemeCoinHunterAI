from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import func, select

import backend.application.controlled_paper_run_service as service_module
from backend.application import (
    ControlledPaperPersistenceService,
    ControlledPaperRunOutcome,
    ControlledPaperRunRequest,
    ControlledPaperRunService,
    PaperLifecyclePersistenceOutcome,
)
from backend.application.service import ServiceRequestContext
from backend.core.config import Settings
from backend.core.database import DatabaseRuntime, DatabaseState
from backend.core.models import Base, PaperLifecycleArtifact, PaperLifecycleRun
from core.decision import DecisionEvaluationRuleset
from core.runtime import (
    ControlledPaperLifecycleOutcome,
    ControlledPaperRunAdmissionOutcome,
    prepare_controlled_paper_run,
)
from tests.test_controlled_paper_lifecycle import (
    _evidence,
    _instruction,
    _ready_admission,
)
from tests.test_controlled_paper_run_admission import _facts


@pytest_asyncio.fixture
async def sqlite_runtime(tmp_path):
    database_file = tmp_path / "controlled-paper-run.db"
    runtime = DatabaseRuntime(
        Settings(
            _env_file=None,
            app_env="test",
            database_url=f"sqlite+aiosqlite:///{database_file}",
        )
    )
    await runtime.start()
    assert runtime.state is DatabaseState.CONNECTED
    assert runtime.engine is not None
    async with runtime.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield runtime
    finally:
        await runtime.dispose()


def _request(
    *,
    invocation_id="paper-run-001",
    ruleset=None,
    expectation_fields=None,
    request_context=None,
):
    facts, _ = _facts(ruleset=ruleset)
    admission = prepare_controlled_paper_run(**facts)
    evidence_admission = (
        admission
        if admission.paper_simulation_input is not None
        else _ready_admission()
    )
    instruction = _instruction(evidence_admission)
    evidence = _evidence(
        evidence_admission,
        instruction,
        expectation_fields=expectation_fields,
    )
    return ControlledPaperRunRequest(
        invocation_id=invocation_id,
        **facts,
        fill_instruction=instruction,
        lifecycle_evidence=evidence,
        request_context=request_context,
    )


async def _counts(runtime):
    async with runtime.session_scope() as session:
        runs = await session.scalar(select(func.count()).select_from(PaperLifecycleRun))
        artifacts = await session.scalar(
            select(func.count()).select_from(PaperLifecycleArtifact)
        )
    return runs, artifacts


@pytest.mark.asyncio
async def test_complete_request_runs_all_owners_once_and_persists(
    sqlite_runtime,
    monkeypatch,
):
    persistence = ControlledPaperPersistenceService(sqlite_runtime)
    service = ControlledPaperRunService(persistence)
    request = _request()
    calls = {"admission": 0, "lifecycle": 0, "persistence": 0}
    original_admission = service_module.prepare_controlled_paper_run
    original_lifecycle = service_module.run_controlled_paper_lifecycle
    original_persist = persistence.persist

    def counted_admission(**kwargs):
        calls["admission"] += 1
        return original_admission(**kwargs)

    def counted_lifecycle(admission, **kwargs):
        calls["lifecycle"] += 1
        return original_lifecycle(admission, **kwargs)

    async def counted_persist(lifecycle):
        calls["persistence"] += 1
        return await original_persist(lifecycle)

    monkeypatch.setattr(
        service_module,
        "prepare_controlled_paper_run",
        counted_admission,
    )
    monkeypatch.setattr(
        service_module,
        "run_controlled_paper_lifecycle",
        counted_lifecycle,
    )
    monkeypatch.setattr(persistence, "persist", counted_persist)

    result = await service.run(request)

    assert result.outcome is ControlledPaperRunOutcome.PERSISTED
    assert result.reason_codes == ()
    assert result.admission.outcome is (
        ControlledPaperRunAdmissionOutcome.READY_FOR_PAPER_SIMULATION
    )
    assert result.lifecycle.outcome is (
        ControlledPaperLifecycleOutcome.OBSERVATION_PRODUCED
    )
    assert result.persistence.outcome is PaperLifecyclePersistenceOutcome.STORED
    assert calls == {"admission": 1, "lifecycle": 1, "persistence": 1}
    assert await _counts(sqlite_runtime) == (1, 13)


@pytest.mark.asyncio
async def test_identical_retry_is_already_persisted_without_duplicate_rows(
    sqlite_runtime,
):
    service = ControlledPaperRunService(
        ControlledPaperPersistenceService(sqlite_runtime)
    )
    request = _request()

    first = await service.run(request)
    second = await service.run(request)

    assert first.outcome is ControlledPaperRunOutcome.PERSISTED
    assert second.outcome is ControlledPaperRunOutcome.ALREADY_PERSISTED
    assert first.lifecycle == second.lifecycle
    assert await _counts(sqlite_runtime) == (1, 13)


@pytest.mark.asyncio
async def test_risk_rejection_is_preserved_and_persisted_without_fill(
    sqlite_runtime,
):
    ruleset = DecisionEvaluationRuleset(
        buy_score_threshold=Decimal("90"),
        watch_score_threshold=Decimal("50"),
    )
    service = ControlledPaperRunService(
        ControlledPaperPersistenceService(sqlite_runtime)
    )

    result = await service.run(_request(ruleset=ruleset))

    assert result.outcome is ControlledPaperRunOutcome.PERSISTED
    assert result.admission.outcome is (
        ControlledPaperRunAdmissionOutcome.AUTHORIZATION_REJECTED
    )
    assert result.lifecycle.outcome is (
        ControlledPaperLifecycleOutcome.ADMISSION_NOT_READY
    )
    assert result.lifecycle.fill_outcome is None
    assert result.persistence.artifact_count == 3
    assert await _counts(sqlite_runtime) == (1, 3)


@pytest.mark.asyncio
async def test_reconciliation_mismatch_is_preserved_and_persisted(
    sqlite_runtime,
):
    service = ControlledPaperRunService(
        ControlledPaperPersistenceService(sqlite_runtime)
    )

    result = await service.run(
        _request(expectation_fields={"entry_digest": "e" * 64})
    )

    assert result.outcome is ControlledPaperRunOutcome.PERSISTED
    assert result.lifecycle.outcome is (
        ControlledPaperLifecycleOutcome.RECONCILIATION_NOT_MATCHED
    )
    assert result.lifecycle.paper_result is None
    assert result.lifecycle.history_result is None
    assert result.lifecycle.observation is None
    assert result.persistence.artifact_count == 10
    assert await _counts(sqlite_runtime) == (1, 10)


@pytest.mark.asyncio
async def test_invalid_outer_request_and_tampered_owner_result_fail_closed(
    sqlite_runtime,
    monkeypatch,
):
    service = ControlledPaperRunService(
        ControlledPaperPersistenceService(sqlite_runtime)
    )

    unsupported = await service.run(object())
    tampered_admission = prepare_controlled_paper_run(**_facts()[0])
    object.__setattr__(tampered_admission, "result_digest", "0" * 64)
    monkeypatch.setattr(
        service_module,
        "prepare_controlled_paper_run",
        lambda **_kwargs: tampered_admission,
    )
    tampered = await service.run(_request(invocation_id="paper-run-tampered"))

    assert unsupported.outcome is ControlledPaperRunOutcome.INVALID_INPUT
    assert unsupported.reason_codes == ("INVALID_REQUEST_TYPE",)
    assert unsupported.invocation_id is None
    assert tampered.outcome is ControlledPaperRunOutcome.INVALID_INPUT
    assert tampered.reason_codes == ("ADMISSION_RESULT_INVALID",)
    assert tampered.admission is None
    assert tampered.lifecycle is None
    assert tampered.persistence is None
    assert await _counts(sqlite_runtime) == (0, 0)


@pytest.mark.asyncio
async def test_canonical_owner_invalid_admission_is_preserved_and_persisted(
    sqlite_runtime,
):
    request = _request(invocation_id="paper-run-owner-invalid")
    object.__setattr__(request.policy_snapshot, "policy_snapshot_id", "tampered")
    service = ControlledPaperRunService(
        ControlledPaperPersistenceService(sqlite_runtime)
    )

    result = await service.run(request)

    assert result.outcome is ControlledPaperRunOutcome.PERSISTED
    assert result.admission.outcome is ControlledPaperRunAdmissionOutcome.INVALID_INPUT
    assert result.admission.reason_codes == ("RISK_CAPITAL_INVALID_INPUT",)
    assert result.lifecycle.outcome is (
        ControlledPaperLifecycleOutcome.ADMISSION_NOT_READY
    )
    assert result.lifecycle.fill_outcome is None
    assert result.persistence.artifact_count == 2
    assert await _counts(sqlite_runtime) == (1, 2)


@pytest.mark.asyncio
async def test_storage_unavailable_and_conflict_remain_distinct(
    sqlite_runtime,
):
    unavailable_runtime = DatabaseRuntime(
        Settings(_env_file=None, app_env="test", database_url=None)
    )
    unavailable_service = ControlledPaperRunService(
        ControlledPaperPersistenceService(unavailable_runtime)
    )
    request = _request()

    unavailable = await unavailable_service.run(request)

    persisted_service = ControlledPaperRunService(
        ControlledPaperPersistenceService(sqlite_runtime)
    )
    stored = await persisted_service.run(request)
    async with sqlite_runtime.session_scope() as session:
        artifact = await session.scalar(select(PaperLifecycleArtifact).limit(1))
        assert artifact is not None
        artifact.canonical_payload = "{}"
    conflict = await persisted_service.run(request)

    assert unavailable.outcome is ControlledPaperRunOutcome.STORAGE_UNAVAILABLE
    assert unavailable.reason_codes == ("DATABASE_UNAVAILABLE",)
    assert stored.outcome is ControlledPaperRunOutcome.PERSISTED
    assert conflict.outcome is ControlledPaperRunOutcome.PERSISTENCE_CONFLICT
    assert conflict.reason_codes == ("PERSISTED_BUNDLE_CORRUPT",)


@pytest.mark.asyncio
async def test_correlation_context_does_not_change_deterministic_result():
    runtime = DatabaseRuntime(
        Settings(_env_file=None, app_env="test", database_url=None)
    )
    service = ControlledPaperRunService(ControlledPaperPersistenceService(runtime))
    baseline = _request(
        request_context=ServiceRequestContext(request_id="request-one")
    )
    changed_context = replace(
        baseline,
        request_context=ServiceRequestContext(request_id="request-two"),
    )

    first = await service.run(baseline)
    second = await service.run(changed_context)

    assert baseline == changed_context
    assert first == second
    assert first.digest == second.digest
    assert first.canonical_representation == second.canonical_representation


@pytest.mark.asyncio
async def test_result_is_immutable_and_digest_protected(sqlite_runtime):
    result = await ControlledPaperRunService(
        ControlledPaperPersistenceService(sqlite_runtime)
    ).run(_request())

    with pytest.raises(FrozenInstanceError):
        result.reason_codes = ("changed",)
    with pytest.raises(ValueError, match="result_digest"):
        replace(result, result_digest="0" * 64)


def test_request_rejects_non_canonical_invocation_identity():
    with pytest.raises(ValueError, match="invocation_id"):
        _request(invocation_id="contains space")
