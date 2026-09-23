"""Contract checks for the bounded RTI-15 → RTI-02 continuation."""

from dataclasses import replace

import pytest

from backend.application.risk_capital_to_paper_admission_continuation import (
    RiskCapitalToPaperAdmissionContinuationService,
)
from backend.application.rti15_to_controlled_paper_lifecycle import (
    P01_RTI_16_CONTRACT_VERSION,
    P01Rti16ControlledPaperLifecycleContinuationResult,
    Rti15ToControlledLifecycleOutcome as Outcome,
    Rti15ToControlledPaperLifecycleContinuationService as Service,
)
from core.runtime.controlled_paper_lifecycle import (
    ControlledPaperLifecycleOutcome,
    run_controlled_paper_lifecycle,
)
from core.runtime.controlled_paper_run_admission import (
    ControlledPaperRunAdmissionOutcome,
    ControlledPaperRunAdmissionResult,
)
from tests.test_controlled_paper_lifecycle import _evidence, _instruction
from tests.test_risk_capital_to_paper_admission_continuation import _facts
from tests.test_paper_reconciliation import _expectation


def _inputs():
    upstream = RiskCapitalToPaperAdmissionContinuationService().materialize(*_facts())
    admission = ControlledPaperRunAdmissionResult(
        outcome=ControlledPaperRunAdmissionOutcome.READY_FOR_PAPER_SIMULATION,
        reason_codes=(),
        decision_intent=upstream.upstream_result.upstream_result.decision_intent,
        risk_capital_authorization=upstream.upstream_result.authorization_result,
        paper_simulation_input=upstream.paper_simulation_input,
    )
    fill = _instruction(admission)
    return upstream, fill, _evidence(admission, fill)


def test_exact_owner_called_once_with_exact_objects_and_result_preserved():
    upstream, fill, evidence = _inputs()
    calls = []

    def owner(admission, *, fill_instruction, lifecycle_evidence):
        calls.append((admission, fill_instruction, lifecycle_evidence))
        return run_controlled_paper_lifecycle(
            admission, fill_instruction=fill_instruction, lifecycle_evidence=lifecycle_evidence
        )

    result = Service(lifecycle_owner=owner).materialize(upstream, fill, evidence)
    assert result.contract_version == P01_RTI_16_CONTRACT_VERSION
    assert result.outcome is Outcome.LIFECYCLE_MATERIALIZED
    assert result.reason_codes == ()
    assert len(calls) == 1
    admission, passed_fill, passed_evidence = calls[0]
    assert passed_fill is fill and passed_evidence is evidence
    assert admission is result.compatibility_admission
    assert admission.decision_intent is upstream.upstream_result.upstream_result.decision_intent
    assert admission.risk_capital_authorization is upstream.upstream_result.authorization_result
    assert admission.paper_simulation_input is upstream.paper_simulation_input
    assert result.lifecycle_result.admission is admission
    assert result.lifecycle_result.outcome is ControlledPaperLifecycleOutcome.RECONCILIATION_NOT_MATCHED
    # An independently supplied expectation can match the actual owner ledger.
    matching = replace(evidence, reconciliation_expectation=_expectation(
        result.lifecycle_result.ledger_entry, reference=evidence.lifecycle_reference_time))
    observed = Service().materialize(upstream, fill, matching)
    assert observed.lifecycle_result.outcome is ControlledPaperLifecycleOutcome.OBSERVATION_PRODUCED
    assert observed.lifecycle_result.observation is not None
    assert Service().materialize(upstream, fill, evidence).digest == result.digest
    assert replace(result) == result


def test_nonmatch_owner_outcome_is_preserved():
    upstream, fill, evidence = _inputs()
    expectation = replace(evidence.reconciliation_expectation,
                          expected_fields={**evidence.reconciliation_expectation.expected_fields,
                                           "expected_entry_digest": "e" * 64},
                          expectation_digest=None)
    evidence = replace(evidence, reconciliation_expectation=expectation)
    result = Service().materialize(upstream, fill, evidence)
    assert result.outcome is Outcome.LIFECYCLE_MATERIALIZED
    assert result.lifecycle_result.outcome is ControlledPaperLifecycleOutcome.RECONCILIATION_NOT_MATCHED
    assert result.lifecycle_result.observation is None


def test_nonadmitted_stops_after_validating_all_explicit_inputs():
    upstream, fill, evidence = _inputs()
    stopped = replace(upstream, outcome="ADMISSION_UNAVAILABLE", reason_codes=("P07_ADMISSION_UNAVAILABLE",),
                      paper_simulation_input=None, result_digest=None)
    calls = []
    service = Service(admission_factory=lambda **kwargs: calls.append(kwargs),
                      lifecycle_owner=lambda *args, **kwargs: calls.append(args))
    result = service.materialize(stopped, fill, evidence)
    assert result.outcome is Outcome.UPSTREAM_NOT_ADMITTED
    assert result.compatibility_admission is result.lifecycle_result is None
    assert calls == []
    object.__setattr__(fill, "quantity_unit", "")
    with pytest.raises(ValueError, match="canonical"):
        service.materialize(stopped, fill, evidence)
    assert calls == []


@pytest.mark.parametrize("position", range(3))
def test_invalid_input_types_are_validation_failures(position):
    inputs = list(_inputs())
    inputs[position] = object()
    with pytest.raises(ValueError, match="canonical"):
        Service().materialize(*inputs)


@pytest.mark.parametrize("position,field,value", [
    (0, "result_digest", "0" * 64),
    (1, "requested_quantity", "wrong"),
    (2, "sequence_number", -1),
])
def test_tampered_input_fails_before_owner(position, field, value):
    inputs = list(_inputs())
    object.__setattr__(inputs[position], field, value)
    calls = []
    with pytest.raises(ValueError, match="canonical"):
        Service(lifecycle_owner=lambda *args, **kwargs: calls.append(args)).materialize(*inputs)
    assert calls == []


@pytest.mark.parametrize("failure,reason", [
    (RuntimeError("private detail"), "ADMISSION_ENVELOPE_UNAVAILABLE"),
    (object(), "ADMISSION_ENVELOPE_INVALID_RESULT"),
])
def test_admission_failure_is_bounded(failure, reason):
    def factory(**kwargs):
        if isinstance(failure, Exception):
            raise failure
        return failure
    result = Service(admission_factory=factory).materialize(*_inputs())
    assert result.outcome is Outcome.LIFECYCLE_UNAVAILABLE
    assert result.reason_codes == (reason,)
    assert result.compatibility_admission is result.lifecycle_result is None
    assert "private" not in str(result.canonical_representation)


@pytest.mark.parametrize("failure,reason", [
    (RuntimeError("private detail"), "LIFECYCLE_UNAVAILABLE"),
    (object(), "LIFECYCLE_INVALID_RESULT"),
])
def test_lifecycle_failure_is_bounded(failure, reason):
    def owner(*args, **kwargs):
        if isinstance(failure, Exception):
            raise failure
        return failure
    result = Service(lifecycle_owner=owner).materialize(*_inputs())
    assert result.outcome is Outcome.LIFECYCLE_UNAVAILABLE
    assert result.reason_codes == (reason,)
    assert result.compatibility_admission is not None and result.lifecycle_result is None


@pytest.mark.parametrize("stage", ["admission", "lifecycle"])
def test_owner_value_error_is_safe_validation_failure(stage):
    def fail(*args, **kwargs):
        raise ValueError("private detail")
    service = Service(**{"admission_factory" if stage == "admission" else "lifecycle_owner": fail})
    with pytest.raises(ValueError) as error:
        service.materialize(*_inputs())
    assert "private" not in str(error.value)


def test_result_digest_covers_explicit_evidence_and_rejects_tampering():
    result = Service().materialize(*_inputs())
    assert len(result.digest) == 64
    with pytest.raises(ValueError):
        replace(result, result_digest="0" * 64)
    with pytest.raises(ValueError):
        P01Rti16ControlledPaperLifecycleContinuationResult(
            upstream_result=result.upstream_result, fill_instruction=result.fill_instruction,
            lifecycle_evidence=result.lifecycle_evidence, outcome="UPSTREAM_NOT_ADMITTED",
            reason_codes=("UPSTREAM_NOT_ADMITTED",))
