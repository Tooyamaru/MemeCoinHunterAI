from dataclasses import FrozenInstanceError

import pytest

from core.opportunity import (
    OpportunityRecordHistory,
    OpportunityRecordHistoryOutcome,
    OpportunityRecordHistoryResult,
    P05_T07_CONTRACT_VERSION,
    materialize_opportunity_record,
)
from tests.test_opportunity_score import _evaluation
from core.opportunity import evaluate_opportunity_score


def _record():
    return materialize_opportunity_record(evaluate_opportunity_score(_evaluation()))


def test_history_stores_valid_record_and_preserves_provenance():
    record = _record()
    history = OpportunityRecordHistory()

    result = history.append(record)

    assert isinstance(result, OpportunityRecordHistoryResult)
    assert result.outcome is OpportunityRecordHistoryOutcome.STORED
    assert result.accepted is True
    assert result.record is record
    assert result.records == (record,)
    assert record.feature_evaluation is result.record.feature_evaluation
    assert record.risk_evaluation is result.record.risk_evaluation
    assert record.signal_snapshot is result.record.signal_snapshot
    assert result.contract_version == P05_T07_CONTRACT_VERSION


def test_history_is_deterministic_and_duplicate_safe():
    record = _record()
    first = OpportunityRecordHistory((record,))
    second = OpportunityRecordHistory()

    duplicate = second.append(record)
    second.append(record)

    assert duplicate.outcome is OpportunityRecordHistoryOutcome.STORED
    assert first.digest == second.digest
    assert second.record_count == 1
    assert second.retrieve() == (record,)


@pytest.mark.parametrize("invalid", [None, object(), "record"])
def test_invalid_input_fails_closed(invalid):
    result = OpportunityRecordHistory().append(invalid)

    assert result.outcome is OpportunityRecordHistoryOutcome.INVALID_INPUT
    assert result.accepted is False
    assert result.record is None
    assert result.reason_codes == ("INVALID_RECORD",)


def test_tampered_record_fails_closed_without_mutating_history():
    record = _record()
    history = OpportunityRecordHistory((record,))
    original_digest = history.digest
    tampered = _record()
    object.__setattr__(tampered, "candidate_id", "tampered")

    result = history.append(tampered)

    assert result.outcome is OpportunityRecordHistoryOutcome.INVALID_INPUT
    assert result.records == (record,)
    assert history.digest == original_digest


def test_history_views_are_immutable_and_records_have_no_forbidden_semantics():
    record = _record()
    history = OpportunityRecordHistory((record,))
    result = history.append(record)

    with pytest.raises(FrozenInstanceError):
        result.outcome = OpportunityRecordHistoryOutcome.DUPLICATE
    assert not hasattr(result.record, "ranking")
    assert not hasattr(result.record, "decision")
    assert not hasattr(result.record, "authorization")
    assert not hasattr(result.record, "execution_instruction")