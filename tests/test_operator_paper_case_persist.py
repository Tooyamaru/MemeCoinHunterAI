from datetime import timedelta

import pytest

from backend.application.operator_paper_case_persist import (
    OperatorPaperCasePersistService,
    OperatorPaperPersistOutcome,
)
from backend.application.operator_paper_case_registry import (
    OperatorPaperCaseRegistry,
    OperatorPaperCaseState,
)
from backend.application.paper_lifecycle_persistence import (
    PaperLifecyclePersistenceOutcome,
    PaperLifecyclePersistenceResult,
)
from backend.application.prepared_paper_case_invocation import (
    P01Oci01Request,
    P01Oci01Result,
    PreparedPaperInvocationOutcome,
)
from backend.application.prevalidated_risk_capital_suffix_caller import (
    PrevalidatedRiskCapitalSuffixCaller,
    PrevalidatedSuffixOutcome,
)
from tests.test_operator_paper_case_registry import NOW, _prepared
from tests.test_operator_paper_case_run import _oci_result


HANDLE = "opaque-persist-handle-1234567890123456"


def _registry():
    return OperatorPaperCaseRegistry(
        capacity=4,
        ttl=timedelta(minutes=10),
        clock=lambda: NOW,
        handle_factory=lambda: HANDLE,
    )


def _lifecycle_terminal(registry):
    record = registry.put(_prepared())
    claimed = registry.claim_run(record.handle, case_digest=record.case_digest)
    request = P01Oci01Request(claimed.prepared.cip_result)
    osc = PrevalidatedRiskCapitalSuffixCaller().run(
        request.cip_result.osc02_request
    )
    assert osc.outcome is PrevalidatedSuffixOutcome.LIFECYCLE_RETURNED
    assert osc.lifecycle_result is not None
    oci = P01Oci01Result(
        request=request,
        outcome=PreparedPaperInvocationOutcome.OSC_RESULT_RETURNED,
        reason_codes=(),
        terminal_stage="OSC-02",
        osc02_result=osc,
    )
    terminal = registry.complete_run(record.handle, oci_result=oci)
    return terminal


@pytest.mark.asyncio
async def test_persist_once_passes_exact_lifecycle_to_rti03_and_retains_result():
    registry = _registry()
    terminal = _lifecycle_terminal(registry)
    lifecycle = terminal.oci_result.osc02_result.lifecycle_result
    calls = []

    class Persistence:
        async def persist(self, value):
            calls.append(value)
            return PaperLifecyclePersistenceResult(
                outcome=PaperLifecyclePersistenceOutcome.STORED,
                reason_codes=(),
                lifecycle_result_digest=value.digest,
                artifact_count=1,
            )

    service = OperatorPaperCasePersistService(
        registry=registry,
        persistence=Persistence(),
    )
    kwargs = {
        "handle": terminal.handle,
        "case_digest": terminal.case_digest,
        "oci_digest": terminal.oci_result.result_digest,
        "osc_digest": terminal.oci_result.osc02_result.result_digest,
        "lifecycle_result_digest": lifecycle.digest,
    }

    first = await service.persist_once(**kwargs)
    second = await service.persist_once(**kwargs)

    assert first.outcome is OperatorPaperPersistOutcome.PERSIST_TERMINAL
    assert first.record.state is OperatorPaperCaseState.PERSIST_TERMINAL
    assert first.record.persistence_result.outcome is PaperLifecyclePersistenceOutcome.STORED
    assert calls == [lifecycle]
    assert calls[0] is lifecycle
    assert second.outcome is OperatorPaperPersistOutcome.CASE_NOT_PERSISTABLE
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_persist_digest_mismatch_stops_before_rti03():
    registry = _registry()
    terminal = _lifecycle_terminal(registry)
    calls = []

    class Persistence:
        async def persist(self, value):
            calls.append(value)
            raise AssertionError("must not run")

    result = await OperatorPaperCasePersistService(
        registry=registry,
        persistence=Persistence(),
    ).persist_once(
        handle=terminal.handle,
        case_digest=terminal.case_digest,
        oci_digest="0" * 64,
        osc_digest=terminal.oci_result.osc02_result.result_digest,
        lifecycle_result_digest=terminal.oci_result.osc02_result.lifecycle_result.digest,
    )

    assert result.outcome is OperatorPaperPersistOutcome.OCI_DIGEST_MISMATCH
    assert calls == []
    assert registry.get(terminal.handle).state is OperatorPaperCaseState.RUN_TERMINAL


@pytest.mark.asyncio
async def test_uncertain_persist_is_nonretryable_unknown():
    registry = _registry()
    terminal = _lifecycle_terminal(registry)
    lifecycle = terminal.oci_result.osc02_result.lifecycle_result
    calls = []

    class Persistence:
        async def persist(self, value):
            calls.append(value)
            raise RuntimeError("private uncertain persistence failure")

    service = OperatorPaperCasePersistService(
        registry=registry,
        persistence=Persistence(),
    )
    kwargs = {
        "handle": terminal.handle,
        "case_digest": terminal.case_digest,
        "oci_digest": terminal.oci_result.result_digest,
        "osc_digest": terminal.oci_result.osc02_result.result_digest,
        "lifecycle_result_digest": lifecycle.digest,
    }

    first = await service.persist_once(**kwargs)
    second = await service.persist_once(**kwargs)

    assert first.outcome is OperatorPaperPersistOutcome.PERSIST_OUTCOME_UNKNOWN
    assert first.record.state is OperatorPaperCaseState.PERSIST_OUTCOME_UNKNOWN
    assert second.outcome is OperatorPaperPersistOutcome.CASE_NOT_PERSISTABLE
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_non_lifecycle_terminal_cannot_claim_persistence():
    registry = _registry()
    record = registry.put(_prepared())
    claimed = registry.claim_run(record.handle, case_digest=record.case_digest)
    request = P01Oci01Request(claimed.prepared.cip_result)
    terminal = registry.complete_run(
        record.handle,
        oci_result=_oci_result(request),
    )
    calls = []

    class Persistence:
        async def persist(self, value):
            calls.append(value)
            raise AssertionError("must not run")

    result = await OperatorPaperCasePersistService(
        registry=registry,
        persistence=Persistence(),
    ).persist_once(
        handle=terminal.handle,
        case_digest=terminal.case_digest,
        oci_digest=terminal.oci_result.result_digest,
        osc_digest=terminal.oci_result.osc02_result.result_digest,
        lifecycle_result_digest="1" * 64,
    )

    assert result.outcome is OperatorPaperPersistOutcome.CASE_NOT_PERSISTABLE
    assert calls == []
