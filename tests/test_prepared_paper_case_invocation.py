"""P01-OCI-01 handoff tests: OSC-02 is always a deterministic test double."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast

import pytest

from backend.application.controlled_paper_experiment_input_preparation import (
    ControlledInputPreparationOutcome,
    ControlledPaperExperimentInputPreparer,
)
from backend.application.prepared_paper_case_invocation import (
    P01_OCI_01_CONTRACT_VERSION,
    P01Oci01Request,
    P01Oci01Result,
    PreparedPaperCaseInvocationService,
    PreparedPaperInvocationOutcome,
)
from backend.application.prevalidated_risk_capital_suffix_caller import (
    P01Osc02Result,
    PrevalidatedSuffixOutcome,
)
from tests.test_controlled_paper_experiment_input_preparation import _case


@pytest.fixture(scope="module")
def ready():
    # Upstream canonical fixtures are in-memory; OSC-02.run is never called.
    return ControlledPaperExperimentInputPreparer().prepare(_case())


def _owner_result(prepared):
    # A canonical OSC result can describe owner unavailability without running
    # RTI-15, RTI-16, lifecycle or any operational paper experiment.
    return P01Osc02Result(
        request=prepared.osc02_request,
        outcome=PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE,
        reason_codes=("RTI-15_UNAVAILABLE",),
        terminal_stage="RTI-14",
    )


def test_exact_request_passed_once_and_exact_osc_result_preserved(ready):
    owner_result = _owner_result(ready)
    calls = []

    class Owner:
        def run(self, request):
            calls.append(request)
            return owner_result

    entry = P01Oci01Request(ready)
    result = PreparedPaperCaseInvocationService(osc02=Owner()).run(entry)
    assert calls == [ready.osc02_request]
    assert calls[0] is ready.osc02_request
    assert result.request is entry
    assert result.request.cip_result is ready
    assert result.osc02_result is owner_result
    assert result.outcome is PreparedPaperInvocationOutcome.OSC_RESULT_RETURNED
    assert result.osc02_result.outcome is PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE
    assert result.terminal_stage == "OSC-02"
    assert result.contract_version == P01_OCI_01_CONTRACT_VERSION
    material = result.canonical_representation
    assert material["cip_result_digest"] == ready.result_digest
    assert material["osc_result_digest"] == owner_result.result_digest
    assert material["prepared_input_digests"] == ready.osc02_request.input_digests
    assert material["invocation_id"] == ready.request.invocation_id
    assert owner_result.request is ready.osc02_request
    assert ready.osc02_request.rti14_result is ready.request.pfx_result.rti14_result
    assert ready.osc02_request.fill_instruction is ready.request.pfs_result.fill_instruction


def test_canonical_nonready_cases_stop_with_zero_owner_calls(ready):
    terminal = [
        ControlledPaperExperimentInputPreparer().prepare(_case(blocked=True)),
        ControlledPaperExperimentInputPreparer().prepare(_case(capacity=Decimal("1"))),
        replace(
            ready,
            outcome=ControlledInputPreparationOutcome.PREPARATION_UNAVAILABLE,
            reason_codes=("OSC_REQUEST_UNAVAILABLE",),
            terminal_stage="OSC-02",
            osc02_request=None,
            result_digest=None,
        ),
    ]
    assert [case.outcome for case in terminal] == [
        ControlledInputPreparationOutcome.PREFIX_NOT_ELIGIBLE,
        ControlledInputPreparationOutcome.FACTS_NOT_MATERIALIZED,
        ControlledInputPreparationOutcome.PREPARATION_UNAVAILABLE,
    ]

    class ForbiddenOwner:
        def run(self, request):
            pytest.fail("OSC-02 must not be called for a non-ready CIP case")

    service = PreparedPaperCaseInvocationService(osc02=ForbiddenOwner())
    for case in terminal:
        result = service.run(P01Oci01Request(case))
        assert result.outcome is PreparedPaperInvocationOutcome.CASE_NOT_PREPARED
        assert result.terminal_stage == "CIP-01"
        assert result.reason_codes == ("CASE_NOT_PREPARED",)
        assert result.osc02_result is None
        assert result.request.cip_result is case
        assert result.canonical_representation["cip_result_digest"] == case.result_digest


def test_deterministic_digest_and_no_global_idempotency_claim(ready):
    owner_result = _owner_result(ready)
    calls = []

    class Owner:
        def run(self, request):
            calls.append(request)
            return owner_result

    service = PreparedPaperCaseInvocationService(osc02=Owner())
    entry = P01Oci01Request(ready)
    first = service.run(entry)
    second = service.run(entry)  # Separate explicit invocation, no durable lock.
    assert calls == [ready.osc02_request, ready.osc02_request]
    assert first.result_digest == second.result_digest
    assert first.osc02_result is second.osc02_result is owner_result
    changed_id = replace(ready.request, invocation_id="osc:other")
    changed_osc = replace(ready.osc02_request, invocation_id="osc:other")
    changed_cip = replace(
        ready, request=changed_id, osc02_request=changed_osc, result_digest=None,
    )
    third = PreparedPaperCaseInvocationService(
        osc02=type("Owner", (), {"run": lambda self, _: _owner_result(changed_cip)})()
    ).run(P01Oci01Request(changed_cip))
    assert first.result_digest != third.result_digest


def test_validation_fails_before_owner_and_owner_valueerror_is_safe(ready):
    calls = []

    class Owner:
        def run(self, request):
            calls.append(request)
            raise ValueError("private owner diagnostic")

    service = PreparedPaperCaseInvocationService(osc02=Owner())
    with pytest.raises(ValueError, match="invalid OCI-01 request"):
        service.run(ready)
    with pytest.raises(ValueError, match="unsupported OCI-01 contract"):
        P01Oci01Request(ready, contract_version="wrong-version")
    corrupted = replace(ready)
    object.__setattr__(corrupted, "result_digest", "0" * 64)
    with pytest.raises(ValueError, match="noncanonical CIP-01 result"):
        service.run(P01Oci01Request(corrupted))
    assert calls == []
    with pytest.raises(ValueError, match="OSC-02 validation failed") as error:
        service.run(P01Oci01Request(ready))
    assert "private" not in str(error.value)
    assert calls == [ready.osc02_request]
    with pytest.raises(ValueError, match="invalid OSC-02 owner seam"):
        PreparedPaperCaseInvocationService(osc02=object())


@pytest.mark.parametrize("kind", ["exception", "invalid", "foreign", "tampered"])
def test_unexpected_or_invalid_owner_result_stops_after_one_call(ready, kind):
    calls = []

    class Owner:
        def run(self, request):
            calls.append(request)
            if kind == "exception":
                raise RuntimeError("private failure")
            if kind == "invalid":
                return object()
            if kind == "foreign":
                foreign = replace(request, invocation_id="osc:foreign")
                return P01Osc02Result(
                    foreign, PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE,
                    ("RTI-15_UNAVAILABLE",), "RTI-14",
                )
            result = _owner_result(ready)
            object.__setattr__(result, "result_digest", "0" * 64)
            return result

    result = PreparedPaperCaseInvocationService(osc02=Owner()).run(
        P01Oci01Request(ready)
    )
    assert calls == [ready.osc02_request]
    assert result.outcome is PreparedPaperInvocationOutcome.OSC_UNAVAILABLE
    assert result.reason_codes == ("OSC-02_UNAVAILABLE",)
    assert result.osc02_result is None
    assert result.terminal_stage == "OSC-02"


def test_oci_result_shape_digest_and_exact_owner_link_are_guarded(ready):
    entry = P01Oci01Request(ready)
    owner_result = _owner_result(ready)
    result = PreparedPaperCaseInvocationService(
        osc02=type("Owner", (), {"run": lambda self, _: owner_result})()
    ).run(entry)
    with pytest.raises(ValueError, match="digest mismatch"):
        replace(result, result_digest="0" * 64)
    with pytest.raises(ValueError, match="result shape"):
        replace(result, osc02_result=None)
    with pytest.raises(ValueError, match="invalid exact OSC-02 result"):
        replace(
            result,
            osc02_result=P01Osc02Result(
                replace(ready.osc02_request, invocation_id="osc:foreign"),
                PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE,
                ("RTI-15_UNAVAILABLE",), "RTI-14",
            ),
            result_digest=None,
        )


def test_module_does_not_import_or_invoke_upstream_or_live_owners():
    source = Path("backend/application/prepared_paper_case_invocation.py").read_text()
    imported = {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    for forbidden in (
        "ControlledPaperExperimentInputPreparer", "PaperFactSourcingService",
        "PrevalidatedDecisionRiskCapitalPrefixService", "RiskCapitalToPaperAdmissionContinuationService",
        "Rti15ToControlledPaperLifecycleContinuationService", "run_controlled_paper_lifecycle",
        "ControlledPaperPersistenceService", "OneShotPaperPersistenceService",
    ):
        assert forbidden not in imported
