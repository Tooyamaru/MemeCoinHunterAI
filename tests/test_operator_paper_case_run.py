from datetime import timedelta

from backend.application.operator_paper_case_registry import (
    OperatorPaperCaseRegistry,
    OperatorPaperCaseState,
)
from backend.application.operator_paper_case_run import (
    OperatorPaperCaseRunService,
    OperatorPaperRunOutcome,
)
from backend.application.prepared_paper_case_invocation import (
    P01Oci01Result,
    PreparedPaperInvocationOutcome,
)
from backend.application.prevalidated_risk_capital_suffix_caller import (
    P01Osc02Result,
    PrevalidatedSuffixOutcome,
)
from tests.test_operator_paper_case_registry import NOW, _prepared


HANDLE = "opaque-handle-run-12345678901234567890"


def _registry():
    return OperatorPaperCaseRegistry(
        capacity=4,
        ttl=timedelta(minutes=10),
        clock=lambda: NOW,
        handle_factory=lambda: HANDLE,
    )


def _oci_result(request):
    osc = P01Osc02Result(
        request=request.cip_result.osc02_request,
        outcome=PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE,
        reason_codes=("RTI-15_UNAVAILABLE",),
        terminal_stage="RTI-14",
    )
    return P01Oci01Result(
        request=request,
        outcome=PreparedPaperInvocationOutcome.OSC_RESULT_RETURNED,
        reason_codes=(),
        terminal_stage="OSC-02",
        osc02_result=osc,
    )


def test_run_once_claims_and_retains_exact_oci_result():
    registry = _registry()
    record = registry.put(_prepared())
    calls = []

    class Oci:
        def run(self, request):
            calls.append(request)
            return _oci_result(request)

    result = OperatorPaperCaseRunService(registry=registry, oci=Oci()).run_once(
        handle=record.handle,
        case_digest=record.case_digest,
    )

    assert result.outcome is OperatorPaperRunOutcome.RUN_TERMINAL
    assert len(calls) == 1
    assert calls[0].cip_result is record.prepared.cip_result
    assert result.record is registry.get(record.handle)
    assert result.record.state is OperatorPaperCaseState.RUN_TERMINAL
    assert result.record.oci_result.request is calls[0]
    assert result.record.oci_result.request.cip_result is record.prepared.cip_result


def test_second_run_is_rejected_without_second_oci_call():
    registry = _registry()
    record = registry.put(_prepared())
    calls = []

    class Oci:
        def run(self, request):
            calls.append(request)
            return _oci_result(request)

    service = OperatorPaperCaseRunService(registry=registry, oci=Oci())
    first = service.run_once(handle=record.handle, case_digest=record.case_digest)
    second = service.run_once(handle=record.handle, case_digest=record.case_digest)

    assert first.outcome is OperatorPaperRunOutcome.RUN_TERMINAL
    assert second.outcome is OperatorPaperRunOutcome.CASE_NOT_RUNNABLE
    assert calls == [first.record.oci_result.request]


def test_digest_mismatch_stops_before_oci_and_leaves_review_ready():
    registry = _registry()
    record = registry.put(_prepared())
    calls = []

    class Oci:
        def run(self, request):
            calls.append(request)
            raise AssertionError("must not run")

    result = OperatorPaperCaseRunService(registry=registry, oci=Oci()).run_once(
        handle=record.handle,
        case_digest="0" * 64,
    )

    assert result.outcome is OperatorPaperRunOutcome.CASE_DIGEST_MISMATCH
    assert calls == []
    assert registry.get(record.handle).state is OperatorPaperCaseState.REVIEW_READY


def test_uncertain_oci_failure_becomes_nonretryable_unknown():
    registry = _registry()
    record = registry.put(_prepared())
    calls = []

    class Oci:
        def run(self, request):
            calls.append(request)
            raise RuntimeError("private uncertain failure")

    service = OperatorPaperCaseRunService(registry=registry, oci=Oci())
    first = service.run_once(handle=record.handle, case_digest=record.case_digest)
    second = service.run_once(handle=record.handle, case_digest=record.case_digest)

    assert first.outcome is OperatorPaperRunOutcome.RUN_OUTCOME_UNKNOWN
    assert first.record.state is OperatorPaperCaseState.RUN_OUTCOME_UNKNOWN
    assert second.outcome is OperatorPaperRunOutcome.CASE_NOT_RUNNABLE
    assert len(calls) == 1


def test_invalid_oci_return_becomes_unknown_without_retry():
    registry = _registry()
    record = registry.put(_prepared())

    class Oci:
        def run(self, request):
            return object()

    result = OperatorPaperCaseRunService(registry=registry, oci=Oci()).run_once(
        handle=record.handle,
        case_digest=record.case_digest,
    )

    assert result.outcome is OperatorPaperRunOutcome.RUN_OUTCOME_UNKNOWN
    assert registry.get(record.handle).state is OperatorPaperCaseState.RUN_OUTCOME_UNKNOWN
