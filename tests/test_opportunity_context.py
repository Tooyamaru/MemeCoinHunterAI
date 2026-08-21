from dataclasses import FrozenInstanceError
from datetime import timedelta

import pytest

from core.opportunity import (
    OpportunityContext,
    OpportunityRecordHistory,
    P05_T08_CONTRACT_VERSION,
    P05_T08_EVALUATOR_VERSION,
    evaluate_opportunity_score,
    materialize_opportunity_context,
    materialize_opportunity_record,
)
from tests.test_opportunity_score import _evaluation


def _inputs():
    record = materialize_opportunity_record(evaluate_opportunity_score(_evaluation()))
    history = OpportunityRecordHistory((record,))
    return record, history


def test_context_preserves_complete_upstream_provenance_and_linkage():
    record, history = _inputs()

    context = materialize_opportunity_context(record, history)

    assert isinstance(context, OpportunityContext)
    assert context.opportunity_record is record
    assert context.record_history is history
    assert context.opportunity_score is record.opportunity_score
    assert context.feature_evaluation is record.feature_evaluation
    assert context.risk_evaluation is record.risk_evaluation
    assert context.signal_snapshot is record.signal_snapshot
    assert context.record_digest == record.digest
    assert context.history_digest == history.digest
    assert context.contract_version == P05_T08_CONTRACT_VERSION
    assert context.evaluator_version == P05_T08_EVALUATOR_VERSION


def test_context_is_canonical_and_deterministic():
    record, history = _inputs()
    first = materialize_opportunity_context(record, history)
    second = materialize_opportunity_context(record, history)

    assert first == second
    assert first.canonical_representation == second.canonical_representation
    assert first.digest == second.digest
    assert first.deterministic_representation == first.canonical_representation


def test_context_rejects_record_not_linked_by_identity():
    record, history = _inputs()
    equivalent = materialize_opportunity_record(record.opportunity_score)

    with pytest.raises(ValueError, match="identity"):
        materialize_opportunity_context(equivalent, history)


def test_context_rejects_history_digest_or_identity_mismatch():
    record, history = _inputs()
    tampered_history = OpportunityRecordHistory()
    assert tampered_history.append(record).stored
    object.__setattr__(tampered_history, "_records_by_digest", {})

    with pytest.raises(ValueError):
        materialize_opportunity_context(record, tampered_history)


def test_context_rejects_inconsistent_reference_time():
    record, history = _inputs()
    with pytest.raises(ValueError, match="identity"):
        OpportunityContext(
            candidate_id=record.candidate_id,
            chain_id=record.chain_id,
            token_identity=record.token_identity,
            reference_time=record.reference_time + timedelta(seconds=1),
            record_digest=record.digest,
            history_digest=history.digest,
            opportunity_record=record,
            record_history=history,
            risk_evaluation=record.risk_evaluation,
            feature_evaluation=record.feature_evaluation,
            signal_snapshot=record.signal_snapshot,
            opportunity_score=record.opportunity_score,
        )


def test_context_is_immutable_and_not_a_decision_or_order():
    record, history = _inputs()
    context = materialize_opportunity_context(record, history)

    with pytest.raises(FrozenInstanceError):
        context.candidate_id = "changed"
    assert context.is_decision is False
    assert context.is_authorization is False
    assert context.is_order is False
    assert not hasattr(context, "ranking")
    assert not hasattr(context, "decision")
    assert not hasattr(context, "execution_instruction")


@pytest.mark.parametrize("invalid", [None, object(), "record"])
def test_invalid_record_input_fails_closed(invalid):
    _, history = _inputs()

    with pytest.raises(ValueError):
        materialize_opportunity_context(invalid, history)


@pytest.mark.parametrize("invalid", [None, object(), "history"])
def test_invalid_history_input_fails_closed(invalid):
    record, _ = _inputs()

    with pytest.raises(ValueError):
        materialize_opportunity_context(record, invalid)