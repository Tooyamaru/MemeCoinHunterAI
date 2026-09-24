"""Focused P01-OSC-02 staged-suffix contract tests."""

from dataclasses import replace
from pathlib import Path
import ast

import pytest

from backend.application.decision_to_risk_capital_continuation import (
    DecisionToRiskCapitalContinuationService,
)
from backend.application.prevalidated_risk_capital_suffix_caller import (
    P01_OSC_02_CONTRACT_VERSION,
    P01Osc02Request,
    PrevalidatedRiskCapitalSuffixCaller,
    PrevalidatedSuffixOutcome,
)
from backend.application.risk_capital_to_paper_admission_continuation import (
    RiskCapitalToPaperAdmissionContinuationService,
)
from backend.application.rti15_to_controlled_paper_lifecycle import (
    Rti15ToControlledPaperLifecycleContinuationService,
)
from core.risk.paper_risk_capital_authorization import (
    AuthorizationStatus,
    RiskStateStatus,
)
from core.runtime.controlled_paper_run_admission import (
    ControlledPaperRunAdmissionOutcome,
    ControlledPaperRunAdmissionResult,
)
from tests.test_controlled_paper_lifecycle import _evidence, _instruction
from tests.test_paper_risk_capital_authorization import _policy
from tests.test_risk_capital_to_paper_admission_continuation import _facts


def _request(rti14=None):
    facts = _facts(rti14) if rti14 is not None else _facts()
    rti14 = facts[0]
    admitted = RiskCapitalToPaperAdmissionContinuationService().materialize(*facts)
    if admitted.paper_simulation_input is None:
        approved_facts = _facts()
        admitted = RiskCapitalToPaperAdmissionContinuationService().materialize(
            *approved_facts
        )
    admission = ControlledPaperRunAdmissionResult(
        outcome=ControlledPaperRunAdmissionOutcome.READY_FOR_PAPER_SIMULATION,
        reason_codes=(),
        decision_intent=admitted.upstream_result.upstream_result.decision_intent,
        risk_capital_authorization=admitted.upstream_result.authorization_result,
        paper_simulation_input=admitted.paper_simulation_input,
    )
    fill = _instruction(admission)
    evidence = _evidence(admission, fill)
    return P01Osc02Request(
        invocation_id="osc02:1",
        rti14_result=rti14,
        execution_observation=facts[1],
        simulation_configuration=facts[2],
        initial_paper_state=facts[3],
        replay_identity=facts[4],
        fill_instruction=fill,
        lifecycle_evidence=evidence,
    )


def _rejected_rti14():
    approved = _facts()[0]
    rejected_policy = _policy(
        approved.upstream_result.decision_intent,
        risk_state=replace(
            approved.policy_snapshot.risk_state,
            status=RiskStateStatus.BLOCK,
            risk_flags=("blocked",),
            state_digest=None,
        ),
    )
    result = DecisionToRiskCapitalContinuationService().continue_to_risk_capital(
        approved.upstream_result,
        rejected_policy,
    )
    assert result.authorization_result.status is AuthorizationStatus.REJECTED
    return result


def test_happy_path_calls_only_rti15_and_rti16_once_with_exact_objects():
    request = _request()
    called = []

    class Rti15:
        def __init__(self):
            self.owner = RiskCapitalToPaperAdmissionContinuationService()

        def continue_to_paper_admission(self, upstream, **kwargs):
            called.append(("RTI-15", upstream, kwargs))
            return self.owner.continue_to_paper_admission(upstream, **kwargs)

    class Rti16:
        def __init__(self):
            self.owner = Rti15ToControlledPaperLifecycleContinuationService()

        def continue_to_controlled_paper_lifecycle(self, upstream, **kwargs):
            called.append(("RTI-16", upstream, kwargs))
            return self.owner.continue_to_controlled_paper_lifecycle(
                upstream, **kwargs
            )

    result = PrevalidatedRiskCapitalSuffixCaller(
        rti15=Rti15(), rti16=Rti16()
    ).run(request)

    assert result.contract_version == P01_OSC_02_CONTRACT_VERSION
    assert result.outcome is PrevalidatedSuffixOutcome.LIFECYCLE_RETURNED
    assert result.terminal_stage == "RTI-16"
    assert [entry[0] for entry in called] == ["RTI-15", "RTI-16"]
    assert called[0][1] is request.rti14_result
    assert called[0][2]["execution_observation"] is request.execution_observation
    assert called[0][2]["simulation_configuration"] is request.simulation_configuration
    assert called[0][2]["initial_paper_state"] is request.initial_paper_state
    assert called[0][2]["replay_identity"] is request.replay_identity
    assert called[1][1] is result.rti15_result
    assert called[1][2]["fill_instruction"] is request.fill_instruction
    assert called[1][2]["lifecycle_evidence"] is request.lifecycle_evidence
    assert result.rti15_result.upstream_result is request.rti14_result
    assert result.rti16_result.upstream_result is result.rti15_result
    assert result.lifecycle_result is result.rti16_result.lifecycle_result


def test_rejected_rti14_stops_before_both_suffix_owners():
    request = _request(_rejected_rti14())
    calls = []

    class Forbidden15:
        def continue_to_paper_admission(self, *args, **kwargs):
            calls.append("RTI-15")
            raise AssertionError("must not run")

    class Forbidden16:
        def continue_to_controlled_paper_lifecycle(self, *args, **kwargs):
            calls.append("RTI-16")
            raise AssertionError("must not run")

    result = PrevalidatedRiskCapitalSuffixCaller(
        rti15=Forbidden15(), rti16=Forbidden16()
    ).run(request)
    assert result.outcome is PrevalidatedSuffixOutcome.UPSTREAM_STOPPED
    assert result.terminal_stage == "RTI-14"
    assert result.rti15_result is result.rti16_result is None
    assert result.reason_codes == request.rti14_result.authorization_result.reason_codes
    assert calls == []


def test_nonmaterialized_rti15_stops_before_rti16():
    request = _request()
    canonical = RiskCapitalToPaperAdmissionContinuationService().continue_to_paper_admission(
        request.rti14_result,
        execution_observation=request.execution_observation,
        simulation_configuration=request.simulation_configuration,
        initial_paper_state=request.initial_paper_state,
        replay_identity=request.replay_identity,
    )
    stopped = replace(
        canonical,
        outcome="ADMISSION_UNAVAILABLE",
        reason_codes=("P07_ADMISSION_UNAVAILABLE",),
        authorization_observation=canonical.authorization_observation,
        paper_simulation_input=None,
        result_digest=None,
    )
    calls = []

    class Owner15:
        def continue_to_paper_admission(self, *args, **kwargs):
            return stopped

    class Forbidden16:
        def continue_to_controlled_paper_lifecycle(self, *args, **kwargs):
            calls.append(True)
            raise AssertionError("must not run")

    result = PrevalidatedRiskCapitalSuffixCaller(
        rti15=Owner15(), rti16=Forbidden16()
    ).run(request)
    assert result.outcome is PrevalidatedSuffixOutcome.UPSTREAM_STOPPED
    assert result.terminal_stage == "RTI-15"
    assert result.rti15_result is stopped
    assert result.rti16_result is None
    assert calls == []


def test_nonmaterialized_rti16_is_preserved_as_upstream_stop():
    request = _request()

    class UnavailableLifecycle:
        def continue_to_controlled_paper_lifecycle(self, upstream, **kwargs):
            owner = Rti15ToControlledPaperLifecycleContinuationService(
                lifecycle_owner=lambda *args, **kw: (_ for _ in ()).throw(
                    RuntimeError("private")
                )
            )
            return owner.continue_to_controlled_paper_lifecycle(upstream, **kwargs)

    result = PrevalidatedRiskCapitalSuffixCaller(
        rti16=UnavailableLifecycle()
    ).run(request)
    assert result.outcome is PrevalidatedSuffixOutcome.UPSTREAM_STOPPED
    assert result.terminal_stage == "RTI-16"
    assert result.rti16_result is not None
    assert result.reason_codes == result.rti16_result.reason_codes


def test_tampered_request_fails_before_any_owner_call():
    request = _request()
    object.__setattr__(request.rti14_result, "result_digest", "0" * 64)
    calls = []

    class Rti15:
        def continue_to_paper_admission(self, *args, **kwargs):
            calls.append(True)

    with pytest.raises(ValueError, match="noncanonical rti14_result"):
        PrevalidatedRiskCapitalSuffixCaller(rti15=Rti15()).run(request)
    assert calls == []


@pytest.mark.parametrize("stage", ["RTI-15", "RTI-16"])
def test_owner_value_error_is_standardized_validation_failure(stage):
    request = _request()

    class Bad15:
        def continue_to_paper_admission(self, *args, **kwargs):
            raise ValueError("private")

    class Bad16:
        def continue_to_controlled_paper_lifecycle(self, *args, **kwargs):
            raise ValueError("private")

    caller = PrevalidatedRiskCapitalSuffixCaller(
        rti15=Bad15() if stage == "RTI-15" else None,
        rti16=Bad16() if stage == "RTI-16" else None,
    )
    with pytest.raises(ValueError) as error:
        caller.run(request)
    assert str(error.value) == f"{stage} validation failed"
    assert "private" not in str(error.value)


@pytest.mark.parametrize("stage", ["RTI-15", "RTI-16"])
def test_unexpected_owner_exception_is_bounded_once(stage):
    request = _request()
    calls = []

    class Fail15:
        def continue_to_paper_admission(self, *args, **kwargs):
            calls.append("RTI-15")
            raise RuntimeError("private")

    class Fail16:
        def continue_to_controlled_paper_lifecycle(self, *args, **kwargs):
            calls.append("RTI-16")
            raise RuntimeError("private")

    caller = PrevalidatedRiskCapitalSuffixCaller(
        rti15=Fail15() if stage == "RTI-15" else None,
        rti16=Fail16() if stage == "RTI-16" else None,
    )
    result = caller.run(request)
    assert calls == [stage]
    assert result.outcome is PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE
    assert result.reason_codes == (f"{stage}_UNAVAILABLE",)
    assert "private" not in str(result.canonical_representation)


@pytest.mark.parametrize("stage", ["RTI-15", "RTI-16"])
def test_invalid_owner_return_is_bounded(stage):
    request = _request()

    class Invalid15:
        def continue_to_paper_admission(self, *args, **kwargs):
            return object()

    class Invalid16:
        def continue_to_controlled_paper_lifecycle(self, *args, **kwargs):
            return object()

    caller = PrevalidatedRiskCapitalSuffixCaller(
        rti15=Invalid15() if stage == "RTI-15" else None,
        rti16=Invalid16() if stage == "RTI-16" else None,
    )
    result = caller.run(request)
    assert result.outcome is PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE
    assert result.reason_codes == (f"{stage}_UNAVAILABLE",)


def test_deterministic_digest_and_invocation_identity_binding():
    request = _request()
    first = PrevalidatedRiskCapitalSuffixCaller().run(request)
    second = PrevalidatedRiskCapitalSuffixCaller().run(request)
    changed = PrevalidatedRiskCapitalSuffixCaller().run(
        replace(request, invocation_id="osc02:2")
    )
    assert first.digest == second.digest
    assert first.canonical_representation == second.canonical_representation
    assert first.digest != changed.digest
    with pytest.raises(ValueError, match="digest"):
        replace(first, result_digest="0" * 64)


def test_module_has_no_prefix_pfs_persistence_provider_or_runtime_imports():
    path = Path("backend/application/prevalidated_risk_capital_suffix_caller.py")
    tree = ast.parse(path.read_text())
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden = {
        "market_to_opportunity",
        "p05_opportunity_context",
        "opportunity_context_to_decision",
        "paper_fact_sourcing",
        "one_shot_controlled_paper_caller",
        "one_shot_paper_persistence",
        "paper_lifecycle_persistence",
        "httpx",
        "requests",
        "fastapi",
        "sqlalchemy",
        "worker",
        "scheduler",
    }
    assert not any(any(part in name for part in forbidden) for name in imports)
