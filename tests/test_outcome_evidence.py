from dataclasses import FrozenInstanceError, replace
from datetime import timedelta

import pytest

from core.learning import (
    OutcomeEvidenceEvaluationResult,
    OutcomeEvidenceReasonCode,
    OutcomeEvidenceState,
    OutcomeInterpretationStatus,
    P08_T03_CONTRACT_VERSION,
    P08_T03_EVALUATOR_VERSION,
    P08_T04_CONTRACT_VERSION,
    P08_T04_EVALUATOR_VERSION,
    create_outcome_evidence_evaluation,
    create_outcome_interpretation_snapshot,
    create_outcome_learning_dataset_snapshot,
)
from core.execution import PaperSimulationResultHistory
from tests.test_outcome_learning import _observation


def _dataset():
    observation = _observation()
    return create_outcome_learning_dataset_snapshot(
        (observation,),
        observation.simulation_reference_time,
    )


def _interpretation(status=OutcomeInterpretationStatus.UNCLASSIFIED):
    result = create_outcome_interpretation_snapshot(_dataset()).results[0]
    return replace(result, interpretation_status=status)


def test_evaluation_preserves_valid_linkage_and_paper_provenance():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]

    result = create_outcome_evidence_evaluation(interpretation, dataset)

    observation = dataset.observations[0]
    assert isinstance(result, OutcomeEvidenceEvaluationResult)
    assert result.source_interpretation_digest == interpretation.digest
    assert result.source_dataset_digest == dataset.digest
    assert result.source_observation_digest == observation.digest
    assert result.source_paper_outcome_status == observation.outcome_status
    assert result.source_reconciliation_status == observation.reconciliation_status
    assert result.source_interpretation_contract_version == P08_T03_CONTRACT_VERSION
    assert result.source_interpretation_evaluator_version == P08_T03_EVALUATOR_VERSION
    assert result.contract_version == P08_T04_CONTRACT_VERSION
    assert result.evaluator_version == P08_T04_EVALUATOR_VERSION


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (
            OutcomeInterpretationStatus.UNCLASSIFIED,
            OutcomeEvidenceReasonCode.STATE_UNCLASSIFIED_PRESERVED,
        ),
        (
            OutcomeInterpretationStatus.UNKNOWN,
            OutcomeEvidenceReasonCode.STATE_UNKNOWN_PRESERVED,
        ),
        (
            OutcomeInterpretationStatus.UNAVAILABLE,
            OutcomeEvidenceReasonCode.STATE_UNAVAILABLE_PRESERVED,
        ),
        (
            OutcomeInterpretationStatus.INCOMPLETE,
            OutcomeEvidenceReasonCode.STATE_INCOMPLETE_PRESERVED,
        ),
    ],
)
def test_all_evidence_states_and_reason_order_are_preserved(status, reason):
    dataset = _dataset()
    result = create_outcome_evidence_evaluation(
        _interpretation(status),
        dataset,
    )

    assert result.evidence_state is OutcomeEvidenceState(status.value)
    assert result.reason_codes == (
        OutcomeEvidenceReasonCode.LINKAGE_VALID,
        reason,
    )


def test_evaluation_is_deterministic_and_digest_covers_canonical_result():
    left_dataset = _dataset()
    right_dataset = _dataset()
    left = create_outcome_evidence_evaluation(
        create_outcome_interpretation_snapshot(left_dataset).results[0],
        left_dataset,
    )
    right = create_outcome_evidence_evaluation(
        create_outcome_interpretation_snapshot(right_dataset).results[0],
        right_dataset,
    )

    assert left.canonical_representation == right.canonical_representation
    assert left.deterministic_representation == left.canonical_representation
    assert left.result_digest == right.result_digest
    assert len(left.result_digest) == 64


def test_result_is_immutable_and_nested_representation_is_frozen():
    dataset = _dataset()
    result = create_outcome_evidence_evaluation(
        create_outcome_interpretation_snapshot(dataset).results[0],
        dataset,
    )

    with pytest.raises(FrozenInstanceError):
        result.evidence_state = OutcomeEvidenceState.UNKNOWN
    with pytest.raises(TypeError):
        result.canonical_representation["evidence_state"] = "UNKNOWN"
    assert isinstance(result.reason_codes, tuple)


def test_rejects_dataset_linkage_mismatch():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    tampered = replace(
        interpretation,
        source_dataset_digest="0" * 64,
    )

    with pytest.raises(ValueError, match="source dataset digest"):
        create_outcome_evidence_evaluation(tampered, dataset)


def test_rejects_observation_mismatch_and_non_member():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    tampered = replace(
        interpretation,
        source_observation_digest="0" * 64,
    )

    with pytest.raises(ValueError, match="exactly one observation"):
        create_outcome_evidence_evaluation(tampered, dataset)


def test_rejects_provenance_mismatch():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    tampered = replace(interpretation, candidate_id="different-candidate")

    with pytest.raises(ValueError, match="candidate identity"):
        create_outcome_evidence_evaluation(tampered, dataset)


def test_rejects_cutoff_violation():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    tampered = replace(
        interpretation,
        reference_time=dataset.as_of_time + timedelta(seconds=1),
    )

    with pytest.raises(ValueError, match="reference time"):
        create_outcome_evidence_evaluation(tampered, dataset)


def test_rejects_invalid_and_unsupported_predecessors():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]

    with pytest.raises(ValueError, match="OutcomeInterpretationResult"):
        create_outcome_evidence_evaluation(object(), dataset)
    with pytest.raises(ValueError, match="OutcomeLearningDatasetSnapshot"):
        create_outcome_evidence_evaluation(interpretation, object())
    with pytest.raises(ValueError, match="contract version"):
        create_outcome_evidence_evaluation(
            replace(interpretation, contract_version="p08-t99-v1"),
            dataset,
        )


def test_rejects_tampered_dataset_and_duplicate_resolution():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]

    object.__setattr__(dataset, "observations", (dataset.observations[0],) * 2)
    object.__setattr__(
        dataset,
        "observation_digests",
        (dataset.observations[0].digest,) * 2,
    )

    with pytest.raises(ValueError, match="invalid|duplicate"):
        create_outcome_evidence_evaluation(interpretation, dataset)


def test_rejects_tampered_output_digest_and_forbidden_authority():
    dataset = _dataset()
    result = create_outcome_evidence_evaluation(
        create_outcome_interpretation_snapshot(dataset).results[0],
        dataset,
    )
    with pytest.raises(ValueError, match="result digest"):
        replace(result, result_digest="0" * 64)

    forbidden = (
        "win",
        "loss",
        "profit",
        "profitability",
        "return",
        "expectancy",
        "drawdown",
        "ranking",
        "aggregation",
        "strategy",
        "model_update",
        "decision_override",
        "risk_override",
        "execution",
        "wallet",
        "rpc",
        "provider",
        "reconciliation",
    )
    for name in forbidden:
        assert not hasattr(result, name)


def test_evaluation_does_not_mutate_predecessors():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    dataset_before = dataset.canonical_representation
    interpretation_before = interpretation.canonical_representation

    create_outcome_evidence_evaluation(interpretation, dataset)

    assert dataset.canonical_representation == dataset_before
    assert interpretation.canonical_representation == interpretation_before