import asyncio
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from backend.application import (
    ControlledPaperPersistenceService,
    PaperLifecycleArtifactKind,
    PaperLifecyclePersistenceOutcome,
    PaperLifecycleReadOutcome,
)
from backend.core.config import Settings
from backend.core.database import DatabaseRuntime, DatabaseState
from backend.core.models import Base, PaperLifecycleArtifact, PaperLifecycleRun
from backend.core.repositories import PaperLifecycleRepository
from core.decision import DecisionEvaluationRuleset
from core.runtime import prepare_controlled_paper_run, run_controlled_paper_lifecycle
from tests.test_controlled_paper_lifecycle import (
    _evidence,
    _instruction,
    _ready_admission,
)
from tests.test_controlled_paper_run_admission import _facts


@pytest_asyncio.fixture
async def sqlite_runtime(tmp_path):
    database_file = tmp_path / "paper-lifecycle.db"
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


def _complete_lifecycle():
    admission = _ready_admission()
    instruction = _instruction(admission)
    return run_controlled_paper_lifecycle(
        admission,
        fill_instruction=instruction,
        lifecycle_evidence=_evidence(admission, instruction),
    )


def _reconciliation_mismatch_lifecycle():
    admission = _ready_admission()
    instruction = _instruction(admission)
    return run_controlled_paper_lifecycle(
        admission,
        fill_instruction=instruction,
        lifecycle_evidence=_evidence(
            admission,
            instruction,
            expectation_fields={"entry_digest": "e" * 64},
        ),
    )


def _unready_lifecycle():
    ruleset = DecisionEvaluationRuleset(
        buy_score_threshold=Decimal("90"),
        watch_score_threshold=Decimal("50"),
    )
    facts, _ = _facts(ruleset=ruleset)
    rejected = prepare_controlled_paper_run(**facts)
    ready = _ready_admission()
    instruction = _instruction(ready)
    return run_controlled_paper_lifecycle(
        rejected,
        fill_instruction=instruction,
        lifecycle_evidence=_evidence(ready, instruction),
    )


async def _counts(runtime):
    async with runtime.session_scope() as session:
        runs = await session.scalar(select(func.count()).select_from(PaperLifecycleRun))
        artifacts = await session.scalar(
            select(func.count()).select_from(PaperLifecycleArtifact)
        )
    return runs, artifacts


@pytest.mark.asyncio
async def test_complete_lifecycle_is_stored_and_read_back_exactly(sqlite_runtime):
    lifecycle = _complete_lifecycle()
    service = ControlledPaperPersistenceService(sqlite_runtime)

    stored = await service.persist(lifecycle)
    read = await service.read(lifecycle.digest)

    assert stored.outcome is PaperLifecyclePersistenceOutcome.STORED
    assert stored.lifecycle_result_digest == lifecycle.digest
    assert stored.artifact_count == 13
    assert read.outcome is PaperLifecycleReadOutcome.FOUND
    assert read.run is not None
    assert read.run.lifecycle_result_digest == lifecycle.digest
    assert read.run.artifact_count == 13
    assert tuple(value.ordinal for value in read.artifacts) == tuple(range(1, 14))
    assert tuple(value.artifact_kind for value in read.artifacts) == tuple(
        PaperLifecycleArtifactKind
    )
    assert await _counts(sqlite_runtime) == (1, 13)


@pytest.mark.asyncio
async def test_identical_retry_is_idempotent_without_new_rows(sqlite_runtime):
    lifecycle = _complete_lifecycle()
    service = ControlledPaperPersistenceService(sqlite_runtime)

    first = await service.persist(lifecycle)
    second = await service.persist(lifecycle)

    assert first.outcome is PaperLifecyclePersistenceOutcome.STORED
    assert second.outcome is PaperLifecyclePersistenceOutcome.ALREADY_STORED
    assert second.artifact_count == 13
    assert await _counts(sqlite_runtime) == (1, 13)


@pytest.mark.asyncio
async def test_non_complete_outcomes_store_only_existing_artifacts(sqlite_runtime):
    service = ControlledPaperPersistenceService(sqlite_runtime)
    mismatch = _reconciliation_mismatch_lifecycle()
    unready = _unready_lifecycle()

    mismatch_result = await service.persist(mismatch)
    unready_result = await service.persist(unready)
    mismatch_read = await service.read(mismatch.digest)
    unready_read = await service.read(unready.digest)

    assert mismatch_result.artifact_count == 10
    assert tuple(value.artifact_kind for value in mismatch_read.artifacts)[-1] is (
        PaperLifecycleArtifactKind.RECONCILIATION_RESULT
    )
    assert unready_result.artifact_count == 3
    assert tuple(value.artifact_kind for value in unready_read.artifacts) == (
        PaperLifecycleArtifactKind.ADMISSION_RESULT,
        PaperLifecycleArtifactKind.DECISION_INTENT,
        PaperLifecycleArtifactKind.RISK_CAPITAL_AUTHORIZATION,
    )
    assert await _counts(sqlite_runtime) == (2, 13)


@pytest.mark.asyncio
async def test_tampered_outer_result_is_rejected_before_database_write(sqlite_runtime):
    lifecycle = _complete_lifecycle()
    object.__setattr__(lifecycle, "result_digest", "0" * 64)
    service = ControlledPaperPersistenceService(sqlite_runtime)

    result = await service.persist(lifecycle)

    assert result.outcome is PaperLifecyclePersistenceOutcome.INVALID_INPUT
    assert result.reason_codes == ("INVALID_LIFECYCLE_RESULT",)
    assert await _counts(sqlite_runtime) == (0, 0)


@pytest.mark.asyncio
async def test_corrupt_existing_payload_is_conflict_and_read_fails_closed(
    sqlite_runtime,
):
    lifecycle = _complete_lifecycle()
    service = ControlledPaperPersistenceService(sqlite_runtime)
    await service.persist(lifecycle)

    async with sqlite_runtime.session_scope() as session:
        artifact = await session.scalar(
            select(PaperLifecycleArtifact).where(
                PaperLifecycleArtifact.artifact_kind
                == PaperLifecycleArtifactKind.OUTCOME_OBSERVATION.value
            )
        )
        assert artifact is not None
        artifact.canonical_payload = "{}"

    conflict = await service.persist(lifecycle)
    read = await service.read(lifecycle.digest)

    assert conflict.outcome is PaperLifecyclePersistenceOutcome.CONFLICT
    assert conflict.reason_codes == ("PERSISTED_BUNDLE_CORRUPT",)
    assert read.outcome is PaperLifecycleReadOutcome.CORRUPT
    assert read.run is None
    assert read.artifacts == ()
    assert await _counts(sqlite_runtime) == (1, 13)


class _FailAfterRootRepository(PaperLifecycleRepository):
    async def insert_bundle(
        self,
        session,
        *,
        run_values,
        artifact_values,
    ):
        session.add(PaperLifecycleRun(**dict(run_values)))
        await session.flush()
        raise SQLAlchemyError("forced failure after root")


@pytest.mark.asyncio
async def test_failure_after_root_insert_rolls_back_everything(sqlite_runtime):
    service = ControlledPaperPersistenceService(
        sqlite_runtime,
        repository=_FailAfterRootRepository(),
    )

    result = await service.persist(_complete_lifecycle())

    assert result.outcome is PaperLifecyclePersistenceOutcome.STORAGE_UNAVAILABLE
    assert result.reason_codes == ("DATABASE_WRITE_FAILED",)
    assert await _counts(sqlite_runtime) == (0, 0)


@pytest.mark.asyncio
async def test_unavailable_database_and_missing_digest_are_explicit(tmp_path):
    runtime = DatabaseRuntime(
        Settings(_env_file=None, app_env="test", database_url=None)
    )
    service = ControlledPaperPersistenceService(runtime)
    lifecycle = _complete_lifecycle()

    write = await service.persist(lifecycle)
    read = await service.read(lifecycle.digest)

    assert write.outcome is PaperLifecyclePersistenceOutcome.STORAGE_UNAVAILABLE
    assert read.outcome is PaperLifecycleReadOutcome.STORAGE_UNAVAILABLE
    with pytest.raises(ValueError, match="must be a digest"):
        await service.read("not-a-digest")


@pytest.mark.asyncio
async def test_missing_record_is_distinct_from_corruption(sqlite_runtime):
    result = await ControlledPaperPersistenceService(sqlite_runtime).read("f" * 64)

    assert result.outcome is PaperLifecycleReadOutcome.NOT_FOUND
    assert result.reason_codes == ("LIFECYCLE_NOT_FOUND",)


@pytest.mark.asyncio
async def test_two_concurrent_identical_attempts_create_one_bundle(sqlite_runtime):
    lifecycle = _complete_lifecycle()
    first_service = ControlledPaperPersistenceService(sqlite_runtime)
    second_service = ControlledPaperPersistenceService(sqlite_runtime)

    results = await asyncio.gather(
        first_service.persist(lifecycle),
        second_service.persist(lifecycle),
    )

    assert {result.outcome for result in results} == {
        PaperLifecyclePersistenceOutcome.STORED,
        PaperLifecyclePersistenceOutcome.ALREADY_STORED,
    }
    assert await _counts(sqlite_runtime) == (1, 13)


def test_models_define_append_only_identity_and_order_constraints():
    run_table = Base.metadata.tables["paper_lifecycle_runs"]
    artifact_table = Base.metadata.tables["paper_lifecycle_artifacts"]

    assert "payload_digest" in artifact_table.c
    assert artifact_table.c.run_id.foreign_keys
    assert any(
        constraint.name == "uq_paper_artifact_run_kind"
        for constraint in artifact_table.constraints
    )
    assert any(
        constraint.name == "uq_paper_artifact_run_ordinal"
        for constraint in artifact_table.constraints
    )
    assert run_table.c.lifecycle_result_digest.unique is True


def test_persistence_results_are_immutable_and_digest_protected():
    result = asyncio.run(_result_for_immutability())

    with pytest.raises(FrozenInstanceError):
        result.artifact_count = 99
    with pytest.raises(ValueError, match="result_digest"):
        replace(result, result_digest="0" * 64)


async def _result_for_immutability():
    runtime = DatabaseRuntime(
        Settings(_env_file=None, app_env="test", database_url=None)
    )
    return await ControlledPaperPersistenceService(runtime).persist(
        _complete_lifecycle()
    )
