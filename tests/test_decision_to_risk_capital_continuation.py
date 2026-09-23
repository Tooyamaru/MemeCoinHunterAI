from dataclasses import replace

import pytest

from backend.application.decision_to_risk_capital_continuation import (
    P01_RTI_14_CONTRACT_VERSION,
    DecisionToRiskCapitalContinuationService,
    DecisionToRiskCapitalOutcome,
)
from backend.application.opportunity_context_to_decision_continuation import (
    OpportunityContextToDecisionContinuationService,
)
from core.risk.paper_risk_capital_authorization import (
    AuthorizationStatus,
    RiskStateStatus,
    evaluate_paper_risk_capital_authorization,
)
from tests.test_opportunity_context_to_decision_continuation import (
    _materialized,
    _not_materialized,
    _ruleset,
)
from tests.test_paper_risk_capital_authorization import _policy


def _decided():
    upstream = _materialized()
    return OpportunityContextToDecisionContinuationService().continue_to_decision(
        upstream,
        _ruleset(),
        upstream.context.reference_time,
    )


def _not_decided():
    upstream = _not_materialized()
    return OpportunityContextToDecisionContinuationService().continue_to_decision(
        upstream,
        _ruleset(),
        upstream.upstream_result.request.reference_time,
    )


def test_approved_authorization_materializes_once_with_exact_identity():
    upstream = _decided()
    policy = _policy(upstream.decision_intent)
    calls = []

    def evaluator(decision, supplied_policy):
        calls.append((decision, supplied_policy))
        return evaluate_paper_risk_capital_authorization(decision, supplied_policy)

    result = DecisionToRiskCapitalContinuationService(
        risk_capital_evaluator=evaluator
    ).continue_to_risk_capital(upstream, policy)

    assert result.contract_version == P01_RTI_14_CONTRACT_VERSION
    assert result.outcome is DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED
    assert result.reason_codes == ()
    assert len(calls) == 1
    assert calls[0][0] is upstream.decision_intent
    assert calls[0][1] is policy
    assert result.upstream_result is upstream
    assert result.policy_snapshot is policy
    # RTI-14 must preserve the exact owner result. This canonical RTI-13 fixture
    # currently yields a P06 action that Risk/Capital rejects; RTI-14 must not
    # reinterpret that owner decision as an approval.
    expected = evaluate_paper_risk_capital_authorization(
        upstream.decision_intent, policy
    )
    assert result.authorization_result == expected
    assert result.authorization_result.status is AuthorizationStatus.REJECTED
    assert result.authorization_result.authorization_effect == (
        "PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY"
    )
    assert len(result.digest) == 64


def test_rejected_authorization_is_still_materialized_and_preserves_reasons():
    upstream = _decided()
    base = _policy(upstream.decision_intent)
    blocked = replace(
        base.risk_state,
        status=RiskStateStatus.BLOCK,
        risk_flags=("blocked",),
        state_digest=None,
    )
    policy = _policy(upstream.decision_intent, risk_state=blocked)

    result = DecisionToRiskCapitalContinuationService().continue_to_risk_capital(
        upstream, policy
    )

    assert result.outcome is DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED
    assert result.authorization_result.status is AuthorizationStatus.REJECTED
    assert "RISK_STATE_BLOCKED" in result.authorization_result.reason_codes
    assert result.authorization_result.reason_codes == (
        "P06_ACTION_NOT_ALLOWED",
        "RISK_STATE_BLOCKED",
    )
    assert result.reason_codes == ()


def test_non_decision_stops_before_authority():
    upstream = _not_decided()
    # A non-decision has no intent to bind; use a canonical policy from a separate
    # canonical intent solely as the explicit caller-owned RTI-14 input.
    decided = _decided()
    policy = _policy(decided.decision_intent)
    calls = 0

    def evaluator(*args):
        nonlocal calls
        calls += 1
        raise AssertionError("Risk/Capital authority must not run")

    result = DecisionToRiskCapitalContinuationService(
        risk_capital_evaluator=evaluator
    ).continue_to_risk_capital(upstream, policy)

    assert result.outcome is DecisionToRiskCapitalOutcome.UPSTREAM_NOT_DECIDED
    assert result.reason_codes == ("UPSTREAM_NOT_DECIDED",)
    assert result.authorization_result is None
    assert calls == 0


@pytest.mark.parametrize("invalid", [None, object(), "upstream"])
def test_invalid_upstream_fails_before_authority(invalid):
    decided = _decided()
    policy = _policy(decided.decision_intent)
    with pytest.raises(ValueError, match="P01Rti13DecisionContinuationResult"):
        DecisionToRiskCapitalContinuationService().continue_to_risk_capital(
            invalid, policy
        )


@pytest.mark.parametrize("invalid", [None, object(), "policy"])
def test_invalid_policy_fails_before_authority(invalid):
    with pytest.raises(ValueError, match="PaperRiskCapitalPolicySnapshot"):
        DecisionToRiskCapitalContinuationService().continue_to_risk_capital(
            _decided(), invalid
        )


def test_policy_decision_linkage_mismatch_fails_before_authority():
    upstream = _decided()
    other = _decided()
    policy = _policy(other.decision_intent)
    object.__setattr__(policy, "decision_intent_digest", "0" * 64)
    calls = 0

    def evaluator(*args):
        nonlocal calls
        calls += 1
        raise AssertionError("authority must not run")

    with pytest.raises(ValueError, match="canonical|DecisionIntent"):
        DecisionToRiskCapitalContinuationService(
            risk_capital_evaluator=evaluator
        ).continue_to_risk_capital(upstream, policy)
    assert calls == 0


def test_owner_value_error_is_standardized_without_raw_detail():
    upstream = _decided()
    policy = _policy(upstream.decision_intent)

    def evaluator(*args):
        raise ValueError("secret raw owner detail")

    with pytest.raises(ValueError) as error:
        DecisionToRiskCapitalContinuationService(
            risk_capital_evaluator=evaluator
        ).continue_to_risk_capital(upstream, policy)

    assert str(error.value) == "Risk/Capital authority validation failed"
    assert "secret" not in str(error.value)


def test_unexpected_owner_exception_is_bounded_unavailable():
    upstream = _decided()
    policy = _policy(upstream.decision_intent)

    def evaluator(*args):
        raise RuntimeError("must not leak")

    result = DecisionToRiskCapitalContinuationService(
        risk_capital_evaluator=evaluator
    ).continue_to_risk_capital(upstream, policy)

    assert result.outcome is DecisionToRiskCapitalOutcome.AUTHORIZATION_UNAVAILABLE
    assert result.reason_codes == ("RISK_CAPITAL_UNAVAILABLE",)
    assert result.authorization_result is None
    assert "must not leak" not in str(result.canonical_representation)


def test_invalid_owner_type_is_bounded_invalid_result():
    upstream = _decided()
    policy = _policy(upstream.decision_intent)

    result = DecisionToRiskCapitalContinuationService(
        risk_capital_evaluator=lambda *args: object()
    ).continue_to_risk_capital(upstream, policy)

    assert result.outcome is DecisionToRiskCapitalOutcome.AUTHORIZATION_UNAVAILABLE
    assert result.reason_codes == ("RISK_CAPITAL_INVALID_RESULT",)


def test_tampered_owner_result_is_bounded_invalid_result():
    upstream = _decided()
    policy = _policy(upstream.decision_intent)
    authorization = evaluate_paper_risk_capital_authorization(
        upstream.decision_intent, policy
    )
    object.__setattr__(authorization, "result_digest", "0" * 64)

    result = DecisionToRiskCapitalContinuationService(
        risk_capital_evaluator=lambda *args: authorization
    ).continue_to_risk_capital(upstream, policy)

    assert result.outcome is DecisionToRiskCapitalOutcome.AUTHORIZATION_UNAVAILABLE
    assert result.reason_codes == ("RISK_CAPITAL_INVALID_RESULT",)


def test_wrapper_digest_is_deterministic():
    upstream = _decided()
    policy = _policy(upstream.decision_intent)
    service = DecisionToRiskCapitalContinuationService()

    first = service.continue_to_risk_capital(upstream, policy)
    second = service.continue_to_risk_capital(upstream, policy)

    assert first.digest == second.digest
    assert first.canonical_representation == second.canonical_representation
    assert first.deterministic_representation == second.deterministic_representation


def test_no_alias_fallback_or_retry_on_owner_failure():
    upstream = _decided()
    policy = _policy(upstream.decision_intent)
    calls = 0

    def evaluator(*args):
        nonlocal calls
        calls += 1
        raise RuntimeError("unavailable")

    result = DecisionToRiskCapitalContinuationService(
        risk_capital_evaluator=evaluator
    ).continue_to_risk_capital(upstream, policy)

    assert calls == 1
    assert result.outcome is DecisionToRiskCapitalOutcome.AUTHORIZATION_UNAVAILABLE
