"""Focused OSC-01 invocation and no duplicate domain delegation checks."""

from dataclasses import replace
from decimal import Decimal

import pytest

from backend.application.one_shot_controlled_paper_caller import (
    OneShotControlledPaperCaller, OneShotPaperOutcome, P01Osc01Request,
)
from backend.application.p05_opportunity_context_continuation import P05OpportunityContextContinuationService
from backend.application.opportunity_context_to_decision_continuation import OpportunityContextToDecisionContinuationService
from backend.application.decision_to_risk_capital_continuation import DecisionToRiskCapitalContinuationService
from backend.application.risk_capital_to_paper_admission_continuation import (
    RiskCapitalToPaperAdmissionContinuationService,
)
from backend.application.rti15_to_controlled_paper_lifecycle import Rti15ToControlledPaperLifecycleContinuationService
from core.decision import DecisionEvaluationRuleset
from core.runtime.controlled_paper_run_admission import (
    ControlledPaperRunAdmissionOutcome, ControlledPaperRunAdmissionResult,
)
from tests.test_controlled_paper_lifecycle import _evidence, _instruction
from tests.test_opportunity_context_to_decision_continuation import _materialized
from tests.test_paper_risk_capital_authorization import _policy
from tests.test_paper_simulation_input import _configuration, _execution, _replay, _state
from tests.test_risk_capital_to_paper_admission_continuation import _facts
from tests.test_p05_opportunity_context_continuation import _composition_unavailable


def _request():
    facts = _facts()
    admitted = RiskCapitalToPaperAdmissionContinuationService().materialize(*facts)
    admission = ControlledPaperRunAdmissionResult(
        outcome=ControlledPaperRunAdmissionOutcome.READY_FOR_PAPER_SIMULATION,
        reason_codes=(),
        decision_intent=admitted.upstream_result.upstream_result.decision_intent,
        risk_capital_authorization=admitted.upstream_result.authorization_result,
        paper_simulation_input=admitted.paper_simulation_input,
    )
    fill = _instruction(admission)
    upstream = facts[0].upstream_result.upstream_result.upstream_result
    return P01Osc01Request(
        invocation_id="invocation:1", rti11_result=upstream,
        decision_ruleset=DecisionEvaluationRuleset(
            buy_score_threshold=Decimal("1"), watch_score_threshold=Decimal("0")),
        decision_time=facts[0].upstream_result.decision_time,
        policy_snapshot=facts[0].policy_snapshot,
        execution_observation=facts[1], simulation_configuration=facts[2],
        initial_paper_state=facts[3], replay_identity=facts[4],
        fill_instruction=fill, lifecycle_evidence=_evidence(admission, fill),
    )


def test_happy_path_exact_chain_and_determinism():
    request = _request()
    called = []

    class Counted:
        def __init__(self, owner, method):
            self.owner = owner
            self.method = method

        def __getattr__(self, name):
            if name != self.method:
                raise AttributeError(name)
            def invoke(*args, **kwargs):
                called.append(name)
                return getattr(self.owner, name)(*args, **kwargs)
            return invoke

    owners = [(P05OpportunityContextContinuationService(), "continue_to_context"),
              (OpportunityContextToDecisionContinuationService(), "continue_to_decision"),
              (DecisionToRiskCapitalContinuationService(), "continue_to_risk_capital"),
              (RiskCapitalToPaperAdmissionContinuationService(), "continue_to_paper_admission"),
              (Rti15ToControlledPaperLifecycleContinuationService(), "continue_to_controlled_paper_lifecycle")]
    result = OneShotControlledPaperCaller(**{f"rti{i}": Counted(owner, method)
                                           for i, (owner, method) in enumerate(owners, 12)}).run(request)
    assert called == [method for _, method in owners]
    assert result.outcome is OneShotPaperOutcome.LIFECYCLE_RETURNED
    assert result.terminal_stage == "RTI-16"
    assert result.rti12_result.upstream_result is request.rti11_result
    assert result.rti13_result.upstream_result is result.rti12_result
    assert result.rti14_result.upstream_result is result.rti13_result
    assert result.rti15_result.upstream_result is result.rti14_result
    assert result.rti16_result.upstream_result is result.rti15_result
    assert result.lifecycle_result is result.rti16_result.lifecycle_result
    assert result.digest == OneShotControlledPaperCaller().run(request).digest
    assert result.digest != OneShotControlledPaperCaller().run(replace(request, invocation_id="invocation:2")).digest


def test_noncomposed_stops_without_calling_any_owner():
    request = replace(_request(), rti11_result=_composition_unavailable())

    class Forbidden:
        def continue_to_context(self, *args):
            raise AssertionError("RTI-12 must not run")

    result = OneShotControlledPaperCaller(rti12=Forbidden()).run(request)
    assert result.outcome is OneShotPaperOutcome.UPSTREAM_STOPPED
    assert result.terminal_stage == "RTI-11"
    assert result.rti12_result is None


def test_bad_explicit_input_fails_before_owner_call():
    request = _request()
    called = []

    class Owner:
        def continue_to_context(self, *args):
            called.append(True)

    with pytest.raises(ValueError):
        OneShotControlledPaperCaller(rti12=Owner()).run(
            replace(request, decision_time=request.decision_time.replace(tzinfo=None)))
    assert not called


def test_owner_exception_is_bounded_once_and_valueerror_is_validation():
    request = _request()
    called = []

    class Owner:
        def continue_to_context(self, *args):
            called.append(args)
            raise RuntimeError("secret")

    result = OneShotControlledPaperCaller(rti12=Owner()).run(request)
    assert result.outcome is OneShotPaperOutcome.OWNER_UNAVAILABLE
    assert result.reason_codes == ("RTI-12_UNAVAILABLE",)
    assert len(called) == 1 and called[0] == (request.rti11_result,)
    assert "secret" not in str(result.canonical_representation)

    class Invalid:
        def continue_to_context(self, *args):
            raise ValueError("secret")

    with pytest.raises(ValueError, match="RTI-12 validation failed"):
        OneShotControlledPaperCaller(rti12=Invalid()).run(request)


def test_rejected_risk_authority_stops_before_rti15():
    request = _request()
    # Preserve canonical Risk/Capital owner output; its own policy determines rejection.
    rejected_rules = DecisionEvaluationRuleset()
    context = _materialized()
    from backend.application.opportunity_context_to_decision_continuation import OpportunityContextToDecisionContinuationService
    decision = OpportunityContextToDecisionContinuationService().materialize(context, rejected_rules, context.context.reference_time)
    policy = _policy(decision.decision_intent)
    request = replace(request, rti11_result=context.upstream_result,
                      decision_ruleset=rejected_rules, decision_time=decision.decision_time,
                      policy_snapshot=policy)
    result = OneShotControlledPaperCaller().run(request)
    assert result.outcome is OneShotPaperOutcome.UPSTREAM_STOPPED
    assert result.terminal_stage == "RTI-14"
    assert result.rti15_result is None
    assert result.reason_codes == result.rti14_result.authorization_result.reason_codes


def test_invalid_owner_output_does_not_continue_or_fabricate_result():
    request = _request()

    class Broken:
        def continue_to_context(self, *args):
            return object()

    result = OneShotControlledPaperCaller(rti12=Broken()).run(request)
    assert result.outcome is OneShotPaperOutcome.OWNER_UNAVAILABLE
    assert result.terminal_stage == "RTI-11" and result.rti12_result is None
    assert result.reason_codes == ("RTI-12_UNAVAILABLE",)


def test_tampered_upstream_digest_rejected_before_delegate():
    request = _request()
    object.__setattr__(request.rti11_result, "result_digest", "0" * 64)
    with pytest.raises(ValueError, match="noncanonical rti11_result"):
        OneShotControlledPaperCaller().run(request)
