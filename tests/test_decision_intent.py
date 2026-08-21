from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from core.decision import (
    DecisionAction,
    DecisionIntent,
    EntryPosture,
    P06_T01_CONTRACT_VERSION,
    create_decision_intent,
)
from core.opportunity import (
    OpportunityRecordHistory,
    materialize_opportunity_context,
    materialize_opportunity_record,
    evaluate_opportunity_score,
)
from tests.test_opportunity_score import _evaluation


def _context():
    record = materialize_opportunity_record(evaluate_opportunity_score(_evaluation()))
    return materialize_opportunity_context(record, OpportunityRecordHistory((record,)))


def _intent(**overrides):
    context = _context()
    values = {
        "context": context,
        "action": DecisionAction.WATCH,
        "entry_posture": EntryPosture.WAIT,
        "expected_edge_assumptions": ("liquidity remains observable",),
        "confidence": Decimal("0.75"),
        "decision_time": context.reference_time,
    }
    values.update(overrides)
    return create_decision_intent(**values)


def test_valid_intent_preserves_complete_p05_provenance():
    intent = _intent()

    assert isinstance(intent, DecisionIntent)
    assert intent.contract_version == P06_T01_CONTRACT_VERSION
    assert intent.context is intent.context
    assert intent.context_digest == intent.context.digest
    assert intent.risk_evaluation is intent.context.risk_evaluation
    assert intent.feature_evaluation is intent.context.feature_evaluation
    assert intent.signal_snapshot is intent.context.signal_snapshot
    assert intent.opportunity_score is intent.context.opportunity_score
    assert intent.opportunity_record is intent.context.opportunity_record
    assert intent.record_history is intent.context.record_history
    assert intent.action is DecisionAction.WATCH
    assert intent.entry_posture is EntryPosture.WAIT
    assert intent.analytical_confidence == Decimal("0.75")
    assert intent.probability_of_profit is None


def test_intent_is_immutable_and_not_authorization_or_order():
    intent = _intent()

    with pytest.raises(FrozenInstanceError):
        intent.action = DecisionAction.BUY
    assert intent.is_decision is True
    assert intent.is_authorization is False
    assert intent.is_order is False
    assert not hasattr(intent, "ranking")
    assert not hasattr(intent, "authorization")
    assert not hasattr(intent, "execution_request")


def test_canonical_representation_and_digest_are_deterministic():
    first = _intent()
    second = _intent()

    assert first.canonical_representation == second.canonical_representation
    assert first.deterministic_representation == first.canonical_representation
    assert first.digest == second.digest
    assert len(first.digest) == 64


@pytest.mark.parametrize(
    "field,value",
    [
        ("ruleset_version", "unsupported"),
        ("evaluator_version", "unsupported"),
        ("contract_version", "unsupported"),
    ],
)
def test_unsupported_versions_are_rejected(field, value):
    with pytest.raises(ValueError, match="unsupported"):
        _intent(**{field: value})


def test_tampered_context_is_rejected():
    context = _context()
    object.__setattr__(context, "candidate_id", "tampered")

    with pytest.raises(ValueError, match="canonical|tampered|invalid"):
        create_decision_intent(context, action=DecisionAction.NO_TRADE)


def test_incomplete_provenance_is_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        _intent(expected_edge_assumptions=("",))


def test_unknown_or_invalidated_evidence_requires_no_trade():
    with pytest.raises(ValueError, match="NO_TRADE"):
        _intent(uncertainty=("evidence is uncertain",))
    with pytest.raises(ValueError, match="NO_TRADE"):
        _intent(invalidation_conditions=("context is invalidated",))

    intent = _intent(
        action=DecisionAction.NO_TRADE,
        uncertainty=("evidence is uncertain",),
        invalidation_conditions=("context is invalidated",),
    )
    assert intent.action is DecisionAction.NO_TRADE


def test_action_and_entry_posture_remain_separate():
    intent = _intent(action=DecisionAction.BUY, entry_posture=EntryPosture.DEFERRED)

    assert intent.action is DecisionAction.BUY
    assert intent.entry_posture is EntryPosture.DEFERRED
    assert intent.canonical_representation["action"] == "BUY"
    assert intent.canonical_representation["entry_posture"] == "DEFERRED"


def test_invalid_semantics_and_time_fail_closed():
    with pytest.raises(ValueError, match="unsupported decision action"):
        _intent(action="RANK")
    with pytest.raises(ValueError, match="unsupported entry posture"):
        _intent(entry_posture="EXECUTE")
    with pytest.raises(ValueError, match="precede"):
        _intent(decision_time=datetime(2026, 8, 11, 11, 0, tzinfo=timezone.utc))


def test_ranking_authorization_and_execution_semantics_are_not_contract_inputs():
    with pytest.raises(TypeError):
        create_decision_intent(_context(), ranking=("candidate-a",))
    with pytest.raises(TypeError):
        create_decision_intent(_context(), authorization="ALLOW")
    with pytest.raises(TypeError):
        create_decision_intent(_context(), execution_request="submit")


def test_confidence_is_analytical_and_bounded():
    with pytest.raises(ValueError, match="between"):
        _intent(confidence=Decimal("1.1"))
    with pytest.raises(ValueError, match="finite"):
        _intent(confidence=Decimal("NaN"))