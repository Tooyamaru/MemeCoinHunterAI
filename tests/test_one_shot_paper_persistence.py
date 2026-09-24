"""Focused optional OSC-01 to RTI-03 composition and STOP checks."""

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, patch

import pytest

from backend.application.one_shot_controlled_paper_caller import (
    OneShotControlledPaperCaller, OneShotPaperOutcome,
)
from backend.application.one_shot_paper_persistence import (
    OneShotPaperPersistenceService, OneShotPersistenceOutcome, P01Osp01Result,
)
from backend.application.paper_lifecycle_persistence import (
    ControlledPaperPersistenceService, PaperLifecyclePersistenceOutcome,
    PaperLifecyclePersistenceResult, PaperLifecycleReadOutcome,
)
from backend.application.rti15_to_controlled_paper_lifecycle import (
    Rti15ToControlledPaperLifecycleContinuationService,
)
from tests.test_controlled_paper_lifecycle import _evidence
from tests.test_controlled_paper_persistence import _counts, sqlite_runtime
from tests.test_one_shot_controlled_paper_caller import _request
from tests.test_p05_opportunity_context_continuation import _composition_unavailable


@pytest.fixture(scope="module")
def ready_osc():
    return OneShotControlledPaperCaller().run(_request())


@pytest.mark.asyncio
async def test_exact_lifecycle_single_write_and_readback(ready_osc, sqlite_runtime):
    owner = ControlledPaperPersistenceService(sqlite_runtime)
    actual = owner.persist
    owner.persist = AsyncMock(wraps=actual)
    with patch.object(OneShotControlledPaperCaller, "run", side_effect=AssertionError("OSC rerun")):
        result = await OneShotPaperPersistenceService(owner).persist(ready_osc)
    owner.persist.assert_awaited_once_with(ready_osc.rti16_result.lifecycle_result)
    assert result.outcome is OneShotPersistenceOutcome.STORED
    assert result.osc_result is ready_osc
    assert result.persistence_result is not None
    assert result.persistence_result.lifecycle_result_digest == ready_osc.lifecycle_result.digest
    assert result.invocation_id == ready_osc.invocation_id
    assert result.canonical_representation["osc_result_digest"] == ready_osc.digest
    assert result.canonical_representation["rti16_result_digest"] == ready_osc.rti16_result.digest
    assert result.canonical_representation["rti03_result_digest"] == result.persistence_result.digest
    read = await owner.read(ready_osc.lifecycle_result.digest)
    assert read.outcome is PaperLifecycleReadOutcome.FOUND
    assert await _counts(sqlite_runtime) == (1, result.persistence_result.artifact_count)


@pytest.mark.asyncio
async def test_explicit_repeat_is_owner_idempotent(ready_osc, sqlite_runtime):
    service = OneShotPaperPersistenceService(ControlledPaperPersistenceService(sqlite_runtime))
    first = await service.persist(ready_osc)
    second = await service.persist(ready_osc)
    assert first.outcome is OneShotPersistenceOutcome.STORED
    assert second.outcome is OneShotPersistenceOutcome.ALREADY_STORED
    assert first.digest != second.digest
    assert await _counts(sqlite_runtime) == (1, first.persistence_result.artifact_count)


@pytest.mark.asyncio
@pytest.mark.parametrize("unavailable", [False, True])
async def test_nonpersistable_osc_stops_before_owner(unavailable, sqlite_runtime):
    request = replace(_request(), rti11_result=_composition_unavailable())
    if unavailable:
        class Failed:
            def continue_to_context(self, *args):
                raise RuntimeError("unavailable")
        request = _request()
        osc = OneShotControlledPaperCaller(rti12=Failed()).run(request)
    else:
        osc = OneShotControlledPaperCaller().run(request)
    assert osc.outcome in (OneShotPaperOutcome.UPSTREAM_STOPPED, OneShotPaperOutcome.OWNER_UNAVAILABLE)
    owner = ControlledPaperPersistenceService(sqlite_runtime)
    owner.persist = AsyncMock(side_effect=AssertionError("unexpected persistence"))
    result = await OneShotPaperPersistenceService(owner).persist(osc)
    owner.persist.assert_not_awaited()
    assert result.outcome is OneShotPersistenceOutcome.UPSTREAM_NOT_PERSISTABLE
    assert result.reason_codes == osc.reason_codes and result.persistence_result is None
    assert await _counts(sqlite_runtime) == (0, 0)


@pytest.mark.asyncio
async def test_tampering_and_owner_validation_fail(ready_osc, sqlite_runtime):
    owner = ControlledPaperPersistenceService(sqlite_runtime)
    owner.persist = AsyncMock()
    invalid = replace(ready_osc)
    object.__setattr__(invalid, "result_digest", "0" * 64)
    with pytest.raises(ValueError, match="canonical OSC"):
        await OneShotPaperPersistenceService(owner).persist(invalid)
    owner.persist.assert_not_awaited()
    owner.persist.side_effect = ValueError("secret")
    with pytest.raises(ValueError, match="RTI-03 validation failed") as failure:
        await OneShotPaperPersistenceService(owner).persist(ready_osc)
    assert "secret" not in str(failure.value)
    assert owner.persist.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome,reason,digest", [
    (PaperLifecyclePersistenceOutcome.CONFLICT, "EXISTING_BUNDLE_CONFLICT", True),
    (PaperLifecyclePersistenceOutcome.INVALID_INPUT, "INVALID_LIFECYCLE_RESULT", False),
    (PaperLifecyclePersistenceOutcome.STORAGE_UNAVAILABLE, "DATABASE_UNAVAILABLE", True),
])
async def test_canonical_owner_outcome_is_preserved(ready_osc, sqlite_runtime, outcome, reason, digest):
    owner_result = PaperLifecyclePersistenceResult(outcome, (reason,),
        ready_osc.lifecycle_result.digest if digest else None, 0)
    owner = ControlledPaperPersistenceService(sqlite_runtime)
    owner.persist = AsyncMock(return_value=owner_result)
    result = await OneShotPaperPersistenceService(owner).persist(ready_osc)
    owner.persist.assert_awaited_once_with(ready_osc.lifecycle_result)
    assert result.persistence_result is owner_result
    assert result.outcome.value == outcome.value and result.reason_codes == owner_result.reason_codes
    assert P01Osp01Result(ready_osc, result.outcome, result.reason_codes, owner_result).digest == result.digest
    assert await _counts(sqlite_runtime) == (0, 0)


@pytest.mark.asyncio
async def test_invalid_owner_output_and_unexpected_failure_are_bounded(ready_osc, sqlite_runtime):
    owner = ControlledPaperPersistenceService(sqlite_runtime)
    other_digest = "0" * 64 if ready_osc.lifecycle_result.digest != "0" * 64 else "1" * 64
    owner.persist = AsyncMock(return_value=PaperLifecyclePersistenceResult(
        PaperLifecyclePersistenceOutcome.STORED, (), other_digest, 1))
    invalid = await OneShotPaperPersistenceService(owner).persist(ready_osc)
    assert invalid.outcome is OneShotPersistenceOutcome.PERSISTENCE_UNAVAILABLE
    assert invalid.reason_codes == ("RTI_03_INVALID_RESULT",) and invalid.persistence_result is None
    owner.persist = AsyncMock(side_effect=RuntimeError("secret"))
    failed = await OneShotPaperPersistenceService(owner).persist(ready_osc)
    assert failed.outcome is OneShotPersistenceOutcome.PERSISTENCE_UNAVAILABLE
    assert failed.reason_codes == ("RTI_03_UNAVAILABLE",)
    assert "secret" not in str(failed.canonical_representation)


@pytest.mark.asyncio
async def test_cancellation_propagates(ready_osc, sqlite_runtime):
    owner = ControlledPaperPersistenceService(sqlite_runtime)
    owner.persist = AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await OneShotPaperPersistenceService(owner).persist(ready_osc)
    assert owner.persist.await_count == 1


@pytest.mark.asyncio
async def test_reconciliation_mismatch_still_delegates(ready_osc, sqlite_runtime):
    old = ready_osc.rti16_result
    changed_evidence = _evidence(old.compatibility_admission, old.fill_instruction,
                                 expectation_fields={"entry_digest": "e" * 64})
    changed_rti16 = Rti15ToControlledPaperLifecycleContinuationService().continue_to_controlled_paper_lifecycle(
        old.upstream_result, old.fill_instruction, changed_evidence)
    changed = replace(ready_osc,
                      request=replace(ready_osc.request, lifecycle_evidence=changed_evidence),
                      rti16_result=changed_rti16, result_digest=None)
    owner = ControlledPaperPersistenceService(sqlite_runtime)
    owner.persist = AsyncMock(wraps=owner.persist)
    result = await OneShotPaperPersistenceService(owner).persist(changed)
    assert result.outcome is OneShotPersistenceOutcome.STORED
    owner.persist.assert_awaited_once_with(changed.lifecycle_result)
    assert await _counts(sqlite_runtime) == (1, 10)
