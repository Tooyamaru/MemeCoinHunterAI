from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import ast

import pytest

from backend.application.decision_to_risk_capital_continuation import (
    DecisionToRiskCapitalContinuationService,
)
from backend.application.opportunity_context_to_decision_continuation import (
    OpportunityContextToDecisionContinuationService,
)
from backend.application.risk_capital_to_paper_admission_continuation import (
    P01_RTI_15_CONTRACT_VERSION,
    RiskCapitalToPaperAdmissionContinuationService,
    RiskCapitalToPaperAdmissionOutcome,
)
from core.decision import DecisionEvaluationRuleset
from core.execution import AuthorizationObservation, PaperSimulationInput
from core.risk.paper_risk_capital_authorization import AuthorizationStatus, RiskStateStatus
from tests.test_decision_to_risk_capital_continuation import _not_decided
from tests.test_opportunity_context_to_decision_continuation import _materialized
from tests.test_paper_risk_capital_authorization import _policy
from tests.test_paper_simulation_input import _configuration, _execution, _replay, _state


def _approved_upstream():
    context_result = _materialized()
    ruleset = DecisionEvaluationRuleset(
        buy_score_threshold=Decimal("1"),
        watch_score_threshold=Decimal("0"),
    )
    decision_result = OpportunityContextToDecisionContinuationService().continue_to_decision(
        context_result, ruleset, context_result.context.reference_time
    )
    policy = _policy(decision_result.decision_intent)
    result = DecisionToRiskCapitalContinuationService().continue_to_risk_capital(
        decision_result, policy
    )
    assert result.authorization_result.status is AuthorizationStatus.APPROVED
    return result


def _facts(upstream=None):
    upstream = upstream or _approved_upstream()
    reference = (
        upstream.authorization_result.simulation_reference_time
        if upstream.authorization_result is not None
        else _approved_upstream().authorization_result.simulation_reference_time
    )
    return (
        upstream,
        _execution(
            observation_time=reference - timedelta(seconds=10),
            availability_time=reference - timedelta(seconds=5),
        ),
        _configuration(),
        _state(as_of_time=reference - timedelta(seconds=20)),
        _replay(),
    )


def test_exact_approved_flow_delegates_once_and_stops_at_p07_input():
    facts = _facts()
    observation_calls = []
    input_calls = []

    def observation_factory(authorization):
        observation_calls.append(authorization)
        return AuthorizationObservation.from_risk_capital_result(authorization)

    def input_factory(**kwargs):
        input_calls.append(kwargs)
        return PaperSimulationInput(**kwargs)

    result = RiskCapitalToPaperAdmissionContinuationService(
        observation_factory=observation_factory,
        input_factory=input_factory,
    ).continue_to_paper_admission(*facts)

    assert result.contract_version == P01_RTI_15_CONTRACT_VERSION
    assert result.outcome is RiskCapitalToPaperAdmissionOutcome.ADMISSION_MATERIALIZED
    assert result.reason_codes == ()
    assert observation_calls == [facts[0].authorization_result]
    assert len(input_calls) == 1
    assert input_calls[0]["decision_intent"] is facts[0].upstream_result.decision_intent
    assert input_calls[0]["authorization_observation"] is result.authorization_observation
    assert input_calls[0]["execution_observation"] is facts[1]
    assert input_calls[0]["simulation_configuration"] is facts[2]
    assert input_calls[0]["initial_paper_state"] is facts[3]
    assert input_calls[0]["replay_identity"] is facts[4]
    assert result.paper_simulation_input.contract_version == "p07-t01-v2"
    assert len(result.digest) == 64


def test_rejected_authorization_stops_before_observation_and_p07():
    approved = _approved_upstream()
    rejected_policy = _policy(
        approved.upstream_result.decision_intent,
        risk_state=replace(
            approved.policy_snapshot.risk_state,
            status=RiskStateStatus.BLOCK,
            risk_flags=("blocked",),
            state_digest=None,
        ),
    )
    rejected = DecisionToRiskCapitalContinuationService().continue_to_risk_capital(
        approved.upstream_result, rejected_policy
    )
    assert rejected.authorization_result.status is AuthorizationStatus.REJECTED
    calls = []
    service = RiskCapitalToPaperAdmissionContinuationService(
        observation_factory=lambda value: calls.append(value),
        input_factory=lambda **kwargs: calls.append(kwargs),
    )
    result = service.continue_to_paper_admission(*_facts(rejected))
    assert result.outcome is RiskCapitalToPaperAdmissionOutcome.UPSTREAM_NOT_AUTHORIZED
    assert result.reason_codes == ("UPSTREAM_NOT_AUTHORIZED",)
    assert result.authorization_observation is None
    assert result.paper_simulation_input is None
    assert calls == []


def test_non_materialized_rti14_stops_before_p07():
    non_decision = _not_decided()
    approved = _approved_upstream()
    upstream = DecisionToRiskCapitalContinuationService().continue_to_risk_capital(
        non_decision, approved.policy_snapshot
    )
    result = RiskCapitalToPaperAdmissionContinuationService().continue_to_paper_admission(
        *_facts(upstream)
    )
    assert result.outcome is RiskCapitalToPaperAdmissionOutcome.UPSTREAM_NOT_AUTHORIZED
    assert result.paper_simulation_input is None


@pytest.mark.parametrize("index", range(5))
def test_invalid_explicit_input_types_are_validation_failures(index):
    facts = list(_facts())
    facts[index] = object()
    with pytest.raises(ValueError):
        RiskCapitalToPaperAdmissionContinuationService().continue_to_paper_admission(*facts)


def test_tampered_upstream_fails_before_delegation():
    facts = list(_facts())
    object.__setattr__(facts[0], "result_digest", "0" * 64)
    calls = []
    with pytest.raises(ValueError, match="canonical"):
        RiskCapitalToPaperAdmissionContinuationService(
            observation_factory=lambda value: calls.append(value),
        ).continue_to_paper_admission(*facts)
    assert calls == []


def test_tampered_explicit_fact_fails_before_delegation():
    facts = list(_facts())
    object.__setattr__(facts[1], "observation_digest", "0" * 64)
    calls = []
    with pytest.raises(ValueError, match="not canonical"):
        RiskCapitalToPaperAdmissionContinuationService(
            observation_factory=lambda value: calls.append(value),
        ).continue_to_paper_admission(*facts)
    assert calls == []


def test_observation_value_error_is_safe_validation_failure():
    def invalid(_):
        raise ValueError("raw secret detail")

    with pytest.raises(ValueError) as error:
        RiskCapitalToPaperAdmissionContinuationService(
            observation_factory=invalid
        ).continue_to_paper_admission(*_facts())
    assert str(error.value) == "Risk/Capital observation validation failed"
    assert "secret" not in str(error.value)


def test_unexpected_observation_failure_is_bounded_without_retry():
    calls = 0
    def unavailable(_):
        nonlocal calls
        calls += 1
        raise RuntimeError("raw detail")
    result = RiskCapitalToPaperAdmissionContinuationService(
        observation_factory=unavailable
    ).continue_to_paper_admission(*_facts())
    assert calls == 1
    assert result.outcome is RiskCapitalToPaperAdmissionOutcome.ADMISSION_UNAVAILABLE
    assert result.reason_codes == ("AUTHORIZATION_OBSERVATION_UNAVAILABLE",)
    assert "raw detail" not in str(result.canonical_representation)


def test_invalid_observation_output_is_bounded():
    result = RiskCapitalToPaperAdmissionContinuationService(
        observation_factory=lambda _: object()
    ).continue_to_paper_admission(*_facts())
    assert result.reason_codes == ("AUTHORIZATION_OBSERVATION_INVALID_RESULT",)


def test_p07_value_error_is_safe_validation_failure():
    def invalid(**kwargs):
        raise ValueError("raw P07 detail")
    with pytest.raises(ValueError) as error:
        RiskCapitalToPaperAdmissionContinuationService(
            input_factory=invalid
        ).continue_to_paper_admission(*_facts())
    assert str(error.value) == "P07-T01 admission validation failed"
    assert "raw" not in str(error.value)


def test_unexpected_and_invalid_p07_results_are_bounded():
    calls = 0
    def unavailable(**kwargs):
        nonlocal calls
        calls += 1
        raise RuntimeError("hidden")
    first = RiskCapitalToPaperAdmissionContinuationService(
        input_factory=unavailable
    ).continue_to_paper_admission(*_facts())
    second = RiskCapitalToPaperAdmissionContinuationService(
        input_factory=lambda **kwargs: object()
    ).continue_to_paper_admission(*_facts())
    assert calls == 1
    assert first.reason_codes == ("P07_ADMISSION_UNAVAILABLE",)
    assert second.reason_codes == ("P07_ADMISSION_INVALID_RESULT",)


def test_deterministic_digest_and_exact_provenance_identity():
    facts = _facts()
    service = RiskCapitalToPaperAdmissionContinuationService()
    first = service.continue_to_paper_admission(*facts)
    second = service.continue_to_paper_admission(*facts)
    assert first.digest == second.digest
    assert first.canonical_representation == second.canonical_representation
    assert first.paper_simulation_input.decision_intent.intent is facts[0].upstream_result.decision_intent
    reference = first.authorization_observation.authorization_reference
    assert reference.authorization_digest == facts[0].authorization_result.digest
    assert reference.decision_intent_digest == facts[0].authorization_result.decision_intent_digest


def test_module_has_no_forbidden_runtime_imports():
    path = Path("backend/application/risk_capital_to_paper_admission_continuation.py")
    tree = ast.parse(path.read_text())
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden = {
        "httpx", "requests", "sqlalchemy", "fastapi", "websockets",
        "controlled_paper_lifecycle", "paper_lifecycle_persistence",
        "paper_fill_outcome", "paper_ledger", "worker", "scheduler",
    }
    assert not any(any(part in name for part in forbidden) for name in imports)
