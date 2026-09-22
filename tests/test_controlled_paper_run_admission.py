from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal

import pytest

from core.decision import DecisionEvaluationRuleset, evaluate_decision_intent
from core.runtime import (
    ControlledPaperRunAdmissionOutcome,
    prepare_controlled_paper_run,
)
from core.risk.paper_risk_capital_authorization import RiskStateStatus
from tests.test_paper_risk_capital_authorization import (
    _intent,
    _policy,
)
from tests.test_paper_simulation_input import (
    _configuration,
    _execution,
    _replay,
    _state,
)


def _facts(*, ruleset=None, policy_factory=_policy, **overrides):
    context = _intent().context
    ruleset = ruleset or DecisionEvaluationRuleset()
    decision = evaluate_decision_intent(context, ruleset=ruleset)
    reference = context.reference_time
    values = {
        "opportunity_context": context,
        "decision_ruleset": ruleset,
        "policy_snapshot": policy_factory(decision),
        "execution_observation": _execution(
            observation_time=reference - timedelta(seconds=10),
            availability_time=reference - timedelta(seconds=5),
        ),
        "simulation_configuration": _configuration(),
        "initial_paper_state": _state(
            as_of_time=reference - timedelta(seconds=20),
        ),
        "replay_identity": _replay(),
        "decision_time": reference,
    }
    values.update(overrides)
    return values, decision


def test_qualifying_context_reaches_one_canonical_p07_admission():
    facts, expected_decision = _facts()

    result = prepare_controlled_paper_run(**facts)

    assert result.outcome is (
        ControlledPaperRunAdmissionOutcome.READY_FOR_PAPER_SIMULATION
    )
    assert result.reason_codes == ()
    assert result.decision_intent == expected_decision
    assert result.risk_capital_authorization is not None
    assert result.risk_capital_authorization.status.value == "APPROVED"
    assert result.paper_simulation_input is not None
    assert result.paper_simulation_input.contract_version == "p07-t01-v2"
    assert (
        result.paper_simulation_input.decision_intent.decision_intent_digest
        == expected_decision.digest
    )
    assert result.paper_simulation_input.authorization_observation.status.value == "PASS"


def test_identical_explicit_facts_are_deterministic():
    facts, _ = _facts()

    first = prepare_controlled_paper_run(**facts)
    second = prepare_controlled_paper_run(**facts)

    assert first == second
    assert first.digest == second.digest
    assert first.canonical_representation == second.canonical_representation


def test_non_buy_decision_preserves_authority_rejection_and_creates_no_p07_input():
    ruleset = DecisionEvaluationRuleset(
        buy_score_threshold=Decimal("90"),
        watch_score_threshold=Decimal("50"),
    )
    facts, decision = _facts(ruleset=ruleset)

    result = prepare_controlled_paper_run(**facts)

    assert decision.action.value == "WATCH"
    assert result.outcome is ControlledPaperRunAdmissionOutcome.AUTHORIZATION_REJECTED
    assert result.decision_intent == decision
    assert result.reason_codes == ("P06_ACTION_NOT_ALLOWED",)
    assert result.risk_capital_authorization is not None
    assert result.risk_capital_authorization.reason_codes == result.reason_codes
    assert result.paper_simulation_input is None


def test_risk_governor_block_is_preserved_and_cannot_create_p07_input():
    def blocked_policy(decision):
        baseline = _policy(decision)
        return _policy(
            decision,
            risk_state=replace(
                baseline.risk_state,
                status=RiskStateStatus.BLOCK,
                risk_flags=("manual-block",),
                state_digest=None,
            ),
        )

    facts, _ = _facts(policy_factory=blocked_policy)

    result = prepare_controlled_paper_run(**facts)

    assert result.outcome is ControlledPaperRunAdmissionOutcome.AUTHORIZATION_REJECTED
    assert result.reason_codes == ("RISK_STATE_BLOCKED",)
    assert result.paper_simulation_input is None


def test_tampered_policy_fails_closed_before_p07_admission():
    facts, _ = _facts()
    policy = facts["policy_snapshot"]
    object.__setattr__(policy, "policy_snapshot_id", "tampered")

    result = prepare_controlled_paper_run(**facts)

    assert result.outcome is ControlledPaperRunAdmissionOutcome.INVALID_INPUT
    assert result.reason_codes == ("RISK_CAPITAL_INVALID_INPUT",)
    assert result.decision_intent is not None
    assert result.risk_capital_authorization is None
    assert result.paper_simulation_input is None


def test_future_execution_observation_fails_closed_at_p07_boundary():
    facts, _ = _facts()
    reference = facts["opportunity_context"].reference_time
    facts["execution_observation"] = _execution(
        observation_time=reference + timedelta(seconds=1),
        availability_time=reference + timedelta(seconds=1),
    )

    result = prepare_controlled_paper_run(**facts)

    assert result.outcome is ControlledPaperRunAdmissionOutcome.INVALID_INPUT
    assert result.reason_codes == ("P07_ADMISSION_INVALID_INPUT",)
    assert result.risk_capital_authorization is not None
    assert result.risk_capital_authorization.status.value == "APPROVED"
    assert result.paper_simulation_input is None


def test_unsupported_input_type_fails_before_any_domain_output():
    facts, _ = _facts()
    facts["execution_observation"] = object()

    result = prepare_controlled_paper_run(**facts)

    assert result.outcome is ControlledPaperRunAdmissionOutcome.INVALID_INPUT
    assert result.reason_codes == ("UNSUPPORTED_INPUT_TYPE",)
    assert result.decision_intent is None
    assert result.risk_capital_authorization is None
    assert result.paper_simulation_input is None


def test_result_is_immutable_and_digest_tampering_is_rejected():
    facts, _ = _facts()
    result = prepare_controlled_paper_run(**facts)

    with pytest.raises(FrozenInstanceError):
        result.reason_codes = ("changed",)
    with pytest.raises(ValueError, match="result_digest"):
        replace(result, result_digest="0" * 64)
