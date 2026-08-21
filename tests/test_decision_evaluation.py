from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from core.decision import (
    DEFAULT_DECISION_EVALUATION_RULESET,
    DecisionAction,
    DecisionEvaluationRuleset,
    EntryPosture,
    P06_T02_RULESET_VERSION,
    evaluate_decision_intent,
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


def test_valid_evaluation_is_buy_wait_and_preserves_provenance():
    result = evaluate_decision_intent(_context())

    assert result.action is DecisionAction.BUY
    assert result.entry_posture is EntryPosture.WAIT
    assert result.context_digest == result.context.digest
    assert result.opportunity_score is result.context.opportunity_score
    assert result.ruleset_version == P06_T02_RULESET_VERSION
    assert result.evaluator_version == "p06-t02-evaluator-v1"
    assert result.analytical_confidence == (
        result.opportunity_score.score / Decimal("100")
    )


def test_identical_context_and_ruleset_produce_identical_intent():
    context = _context()

    first = evaluate_decision_intent(context)
    second = evaluate_decision_intent(context)

    assert first == second
    assert first.canonical_representation == second.canonical_representation
    assert first.digest == second.digest


def test_ruleset_is_immutable_canonical_and_versioned():
    ruleset = DEFAULT_DECISION_EVALUATION_RULESET

    with pytest.raises(FrozenInstanceError):
        ruleset.buy_score_threshold = Decimal("1")
    assert ruleset.canonical_representation == ruleset.deterministic_representation
    assert ruleset.digest == ruleset.representation_digest
    assert ruleset.version == P06_T02_RULESET_VERSION


def test_thresholds_are_explicit_and_deterministic():
    result = evaluate_decision_intent(
        _context(),
        ruleset=DecisionEvaluationRuleset(
            buy_score_threshold=Decimal("90"),
            watch_score_threshold=Decimal("80"),
        ),
    )

    assert result.action is DecisionAction.WATCH
    assert result.entry_posture is EntryPosture.WAIT


def test_stale_evidence_fails_closed_to_no_trade():
    result = evaluate_decision_intent(
        _context(),
        ruleset=DecisionEvaluationRuleset(max_evidence_age_seconds=0),
    )

    assert result.action is DecisionAction.NO_TRADE
    assert "STALE_EVIDENCE" in result.uncertainty
    assert result.entry_posture is EntryPosture.WAIT


def test_tampered_context_is_rejected_fail_closed():
    context = _context()
    object.__setattr__(context, "token_identity", "tampered")

    with pytest.raises(ValueError, match="invalid|tampered|canonical"):
        evaluate_decision_intent(context)


def test_unsupported_ruleset_version_is_rejected():
    with pytest.raises(ValueError, match="unsupported"):
        DecisionEvaluationRuleset(version="unsupported")


@pytest.mark.parametrize("action", tuple(DecisionAction))
def test_all_authorized_actions_are_validated(action):
    from core.decision import create_decision_intent

    result = create_decision_intent(_context(), action=action)

    assert result.action is action


def test_invalid_action_is_rejected():
    with pytest.raises(ValueError, match="unsupported decision action"):
        from core.decision import create_decision_intent

        create_decision_intent(_context(), action="RANK")


def test_evaluation_has_no_ranking_or_execution_semantics():
    result = evaluate_decision_intent(_context())

    assert not hasattr(result, "ranking")
    assert not hasattr(result, "comparison")
    assert not hasattr(result, "authorization")
    assert not hasattr(result, "capital_allocation")
    assert not hasattr(result, "execution_request")
    assert not hasattr(result, "wallet")
    assert not hasattr(result, "rpc")
    assert not hasattr(result, "dex")


def test_evaluation_does_not_depend_on_uncontrolled_system_clock():
    context = _context()
    first = evaluate_decision_intent(context)
    second = evaluate_decision_intent(context)

    assert first.decision_time == context.reference_time
    assert first.decision_time == second.decision_time
    assert first.digest == second.digest