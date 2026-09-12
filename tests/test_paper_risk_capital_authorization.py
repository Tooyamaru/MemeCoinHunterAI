from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal

import pytest

from core.decision import DecisionAction, EntryPosture, evaluate_decision_intent
from core.risk.paper_risk_capital_authorization import (
    AuthorizationStatus,
    PaperCapitalState,
    PaperExposureState,
    PaperRiskCapitalPolicySnapshot,
    RiskState,
    RiskStateStatus,
    evaluate_paper_risk_capital_authorization,
)
from tests.test_opportunity_score import _evaluation
from core.opportunity import (
    OpportunityRecordHistory,
    evaluate_opportunity_score,
    materialize_opportunity_context,
    materialize_opportunity_record,
)


UTC = timezone.utc


def _intent(**overrides):
    record = materialize_opportunity_record(evaluate_opportunity_score(_evaluation()))
    context = materialize_opportunity_context(
        record,
        OpportunityRecordHistory((record,)),
    )
    values = {
        "context": context,
        "action": DecisionAction.BUY,
        "entry_posture": EntryPosture.WAIT,
        "expected_edge_assumptions": ("paper admission only",),
        "decision_time": context.reference_time,
    }
    values.update(overrides)
    from core.decision import create_decision_intent

    return create_decision_intent(**values)


def _policy(intent=None, **overrides):
    intent = intent or _intent()
    reference = intent.context.reference_time
    values = {
        "policy_snapshot_id": "policy-1",
        "risk_governor_version": "risk-governor-v1",
        "capital_authorization_version": "capital-authority-v1",
        "evaluator_version": "p08-risk-capital-authority-evaluator-v1",
        "scope_identity": {
            "paper_lifecycle_id": "lifecycle-1",
            "paper_portfolio_id": "portfolio-1",
            "candidate_id": intent.candidate_id,
            "chain_id": intent.chain_id,
            "token_identity": intent.token_identity,
        },
        "decision_intent_digest": intent.digest,
        "context_digest": intent.context_digest,
        "simulation_reference_time": reference,
        "policy_cutoff_time": reference,
        "risk_state_max_age_seconds": Decimal("60"),
        "paper_capital_state_max_age_seconds": Decimal("60"),
        "paper_exposure_state_max_age_seconds": Decimal("60"),
        "valid_from": reference - timedelta(minutes=1),
        "valid_until": reference + timedelta(minutes=5),
        "risk_state": RiskState(
            status=RiskStateStatus.PASS,
            emergency_stop=False,
            risk_flags=(),
            as_of_time=reference - timedelta(seconds=20),
            available_at=reference - timedelta(seconds=10),
        ),
        "paper_capital_state": PaperCapitalState(
            unit="paper-unit",
            budget_total=Decimal("100"),
            committed_before=Decimal("10"),
            requested_entry=Decimal("20"),
            max_single_entry=Decimal("50"),
            as_of_time=reference - timedelta(seconds=20),
            available_at=reference - timedelta(seconds=10),
        ),
        "paper_exposure_state": PaperExposureState(
            unit="paper-unit",
            exposure_before=Decimal("10"),
            max_total_exposure=Decimal("50"),
            as_of_time=reference - timedelta(seconds=20),
            available_at=reference - timedelta(seconds=10),
        ),
        "provenance": {"source": "immutable-fixture"},
    }
    values.update(overrides)
    return PaperRiskCapitalPolicySnapshot(**values)


def test_valid_approval_is_deterministic_and_paper_only():
    intent = _intent()
    policy = _policy(intent)

    first = evaluate_paper_risk_capital_authorization(intent, policy)
    second = evaluate_paper_risk_capital_authorization(intent, policy)

    assert first.status is AuthorizationStatus.APPROVED
    assert first.primary_reason_code is None
    assert first.reason_codes == ()
    assert first.authorization_effect == "PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY"
    assert first.authorization_id == second.authorization_id
    assert first.digest == second.digest
    assert first.canonical_representation == second.canonical_representation
    assert first.is_authorization is True
    assert first.is_order is False

    observation = first.to_authorization_observation()
    assert observation.status.value == "PASS"
    assert observation.observation_id == first.authorization_id
    assert observation.scope_identity == first.scope_identity


def test_policy_denial_is_rejected_with_stable_reason():
    intent = _intent()
    policy = _policy(
        intent,
        risk_state=replace(
            _policy(intent).risk_state,
            status=RiskStateStatus.BLOCK,
            risk_flags=("emergency-stop",),
            state_digest=None,
        ),
    )

    result = evaluate_paper_risk_capital_authorization(intent, policy)

    assert result.status is AuthorizationStatus.REJECTED
    assert result.primary_reason_code == "RISK_STATE_BLOCKED"
    assert result.reason_codes == ("RISK_STATE_BLOCKED",)
    assert result.to_authorization_observation().status.value == "FAIL"


def test_future_and_stale_policy_states_fail_closed_with_exact_reasons():
    intent = _intent()
    reference = intent.context.reference_time
    future = _policy(
        intent,
        risk_state=replace(
            _policy(intent).risk_state,
            as_of_time=reference + timedelta(seconds=1),
            available_at=reference + timedelta(seconds=1),
            state_digest=None,
        ),
    )
    stale = _policy(
        intent,
        risk_state=replace(
            _policy(intent).risk_state,
            as_of_time=reference - timedelta(seconds=61),
            state_digest=None,
        ),
    )

    future_result = evaluate_paper_risk_capital_authorization(intent, future)
    stale_result = evaluate_paper_risk_capital_authorization(intent, stale)

    assert future_result.primary_reason_code == "POLICY_STATE_FUTURE_DATED"
    assert stale_result.primary_reason_code == "POLICY_STATE_STALE"


def test_invalid_missing_and_tampered_policy_input_fails_closed():
    intent = _intent()
    with pytest.raises(ValueError, match="missing PaperRiskCapitalPolicySnapshot"):
        PaperRiskCapitalPolicySnapshot.from_mapping({})

    with pytest.raises(ValueError, match="timezone-aware"):
        _policy(intent, policy_cutoff_time=intent.context.reference_time.replace(tzinfo=None))

    tampered = _policy(intent)
    object.__setattr__(tampered, "policy_snapshot_id", "tampered")
    with pytest.raises(ValueError, match="policy_snapshot_digest"):
        evaluate_paper_risk_capital_authorization(intent, tampered)


def test_reason_precedence_is_fail_closed_and_deterministic():
    intent = _intent()
    reference = intent.context.reference_time
    policy = _policy(
        intent,
        risk_state=replace(
            _policy(intent).risk_state,
            status=RiskStateStatus.BLOCK,
            as_of_time=reference + timedelta(seconds=1),
            available_at=reference + timedelta(seconds=1),
            state_digest=None,
        ),
    )

    result = evaluate_paper_risk_capital_authorization(intent, policy)

    assert result.reason_codes == (
        "POLICY_STATE_FUTURE_DATED",
        "RISK_STATE_BLOCKED",
        "PAPER_OBSERVATION_UNAVAILABLE",
    )
    assert result.primary_reason_code == "POLICY_STATE_FUTURE_DATED"


def test_replay_and_digest_identity_are_stable_but_scope_changes_identity():
    intent = _intent()
    first = evaluate_paper_risk_capital_authorization(intent, _policy(intent))
    changed_scope = _policy(
        intent,
        scope_identity={
            **_policy(intent).scope_identity,
            "paper_lifecycle_id": "lifecycle-2",
        },
    )
    second = evaluate_paper_risk_capital_authorization(intent, changed_scope)

    assert first.digest == evaluate_paper_risk_capital_authorization(
        intent, _policy(intent)
    ).digest
    assert first.authorization_id != second.authorization_id
    assert first.policy_snapshot_digest != second.policy_snapshot_digest


def test_policy_and_inputs_are_immutable():
    intent = _intent()
    policy = _policy(intent)
    before = policy.canonical_representation

    with pytest.raises(FrozenInstanceError):
        policy.policy_snapshot_id = "changed"
    with pytest.raises(TypeError):
        policy.scope_identity["candidate_id"] = "changed"
    with pytest.raises(TypeError):
        policy.provenance["changed"] = True

    result = evaluate_paper_risk_capital_authorization(intent, policy)
    assert policy.canonical_representation == before
    assert result.status is AuthorizationStatus.APPROVED