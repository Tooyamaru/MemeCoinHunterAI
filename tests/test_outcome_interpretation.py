from dataclasses import FrozenInstanceError, replace
from datetime import timedelta

import pytest

from core.execution import PaperSimulationResultHistory
from core.learning import (
    OutcomeInterpretationResult,
    OutcomeInterpretationSnapshot,
    OutcomeInterpretationStatus,
    P08_T03_CONTRACT_VERSION,
    P08_T03_EVALUATOR_VERSION,
    create_outcome_interpretation_snapshot,
    create_outcome_learning_observation,
    create_outcome_learning_dataset_snapshot,
)
from tests.test_outcome_learning import _observation


def _snapshot():
    observation = _observation()
    return create_outcome_learning_dataset_snapshot(
        (observation,),
        observation.simulation_reference_time,
    )


def _snapshot_with_status(
    *,
    outcome_status="FILLED",
    reconciliation_status="RECONCILED",
):
    observation = _observation()
    result = replace(
        observation.paper_result,
        status=outcome_status,
        reconciliation_status=reconciliation_status,
    )
    updated = create_outcome_learning_observation(
        observation.decision_intent,
        observation.simulation_input,
        result,
        PaperSimulationResultHistory((result,)),
    )
    return create_outcome_learning_dataset_snapshot(
        (updated,),
        updated.simulation_reference_time,
    )


def test_interpretation_produces_one_result_per_source_observation():
    dataset = _snapshot()

    result = create_outcome_interpretation_snapshot(dataset)

    assert isinstance(result, OutcomeInterpretationSnapshot)
    assert result.result_count == dataset.observation_count
    assert result.source_dataset_digest == dataset.digest
    assert len(result.result_digests) == dataset.observation_count

    interpretation = result.results[0]

    assert isinstance(interpretation, OutcomeInterpretationResult)
    assert (
        interpretation.source_observation_digest
        == dataset.observations[0].digest
    )
    assert interpretation.candidate_id == dataset.observations[0].candidate_id
    assert interpretation.chain_id == dataset.observations[0].chain_id
    assert (
        interpretation.token_identity
        == dataset.observations[0].token_identity
    )
    assert (
        interpretation.reference_time
        == dataset.observations[0].simulation_reference_time
    )
    assert interpretation.interpretation_status == (
        OutcomeInterpretationStatus.UNCLASSIFIED
    )


def test_interpretation_preserves_source_paper_and_reconciliation_states():
    dataset = _snapshot_with_status(
        outcome_status="UNAVAILABLE",
        reconciliation_status="UNKNOWN",
    )

    result = create_outcome_interpretation_snapshot(dataset)
    interpretation = result.results[0]

    assert interpretation.source_outcome_status == "UNAVAILABLE"
    assert interpretation.source_reconciliation_status == "UNKNOWN"
    assert interpretation.interpretation_status == (
        OutcomeInterpretationStatus.UNAVAILABLE
    )


def test_unknown_reconciliation_is_explicitly_unknown():
    dataset = _snapshot_with_status(
        outcome_status="FILLED",
        reconciliation_status="UNKNOWN",
    )

    result = create_outcome_interpretation_snapshot(dataset)

    assert result.results[0].interpretation_status == (
        OutcomeInterpretationStatus.UNKNOWN
    )


@pytest.mark.parametrize(
    "outcome_status",
    ["FILLED", "PARTIAL", "FAILED", "REJECTED"],
)
def test_non_unknown_valid_paper_states_remain_unclassified(outcome_status):
    dataset = _snapshot_with_status(
        outcome_status=outcome_status,
        reconciliation_status="RECONCILED",
    )

    result = create_outcome_interpretation_snapshot(dataset)

    interpretation = result.results[0]

    assert interpretation.source_outcome_status == outcome_status
    assert interpretation.interpretation_status == (
        OutcomeInterpretationStatus.UNCLASSIFIED
    )


def test_interpretation_is_deterministic():
    first = _snapshot()
    second = _snapshot()

    left = create_outcome_interpretation_snapshot(first)
    right = create_outcome_interpretation_snapshot(second)

    assert left.canonical_representation == right.canonical_representation
    assert left.digest == right.digest
    assert left.results[0].digest == right.results[0].digest


def test_interpretation_snapshot_is_immutable():
    result = create_outcome_interpretation_snapshot(_snapshot())

    with pytest.raises(FrozenInstanceError):
        result.source_dataset_digest = "0" * 64

    with pytest.raises(FrozenInstanceError):
        result.results[0].candidate_id = "tampered"


def test_result_is_immutable_and_versioned():
    dataset = _snapshot()
    result = create_outcome_interpretation_snapshot(dataset)
    interpretation = result.results[0]

    with pytest.raises(FrozenInstanceError):
        interpretation.interpretation_status = (
            OutcomeInterpretationStatus.UNKNOWN
        )

    assert interpretation.contract_version == P08_T03_CONTRACT_VERSION
    assert interpretation.evaluator_version == P08_T03_EVALUATOR_VERSION
    assert len(interpretation.digest) == 64


def test_interpretation_has_no_economic_or_authority_semantics():
    result = create_outcome_interpretation_snapshot(_snapshot())
    interpretation = result.results[0]

    forbidden = (
        "win",
        "loss",
        "profit",
        "profitability",
        "expectancy",
        "edge",
        "drawdown",
        "slippage",
        "latency",
        "ranking",
        "score",
        "decision",
        "authorization",
        "execution",
        "model_update",
        "training",
        "strategy_update",
    )

    for name in forbidden:
        assert not hasattr(interpretation, name)


def test_interpretation_rejects_non_dataset_input():
    with pytest.raises(ValueError, match="OutcomeLearningDatasetSnapshot"):
        create_outcome_interpretation_snapshot(object())


def test_interpretation_rejects_tampered_dataset():
    dataset = _snapshot()

    object.__setattr__(
        dataset.observations[0].decision_intent.context,
        "candidate_id",
        "tampered",
    )

    with pytest.raises(
        ValueError,
        match="invalid|tampered|DecisionIntent",
    ):
        create_outcome_interpretation_snapshot(dataset)


def test_snapshot_rejects_result_from_different_dataset():
    dataset = _snapshot()
    result = create_outcome_interpretation_snapshot(dataset)
    interpretation = result.results[0]

    other_observation = _observation()
    other_result = replace(
        other_observation.paper_result,
        fill_digest="different-fill-digest",
    )
    other_observation = create_outcome_learning_observation(
        other_observation.decision_intent,
        other_observation.simulation_input,
        other_result,
        PaperSimulationResultHistory((other_result,)),
    )
    other_dataset = create_outcome_learning_dataset_snapshot(
        (other_observation,),
        other_observation.simulation_reference_time,
    )

    assert other_dataset.digest != dataset.digest

    tampered = replace(
        interpretation,
        source_dataset_digest=other_dataset.digest,
    )

    with pytest.raises(ValueError, match="source dataset digest"):
        OutcomeInterpretationSnapshot(
            source_dataset_digest=dataset.digest,
            source_dataset_as_of_time=dataset.as_of_time,
            results=(tampered,),
            result_digests=(tampered.digest,),
        )


def test_snapshot_rejects_future_result_reference_time():
    dataset = _snapshot()
    result = create_outcome_interpretation_snapshot(dataset)
    interpretation = result.results[0]

    future = replace(
        interpretation,
        reference_time=dataset.as_of_time + timedelta(seconds=1),
    )

    with pytest.raises(ValueError, match="after source dataset cutoff"):
        OutcomeInterpretationSnapshot(
            source_dataset_digest=dataset.digest,
            source_dataset_as_of_time=dataset.as_of_time,
            results=(future,),
            result_digests=(future.digest,),
        )


def test_snapshot_rejects_wrong_result_digests():
    dataset = _snapshot()
    result = create_outcome_interpretation_snapshot(dataset)

    with pytest.raises(ValueError, match="result digests"):
        OutcomeInterpretationSnapshot(
            source_dataset_digest=result.source_dataset_digest,
            source_dataset_as_of_time=result.source_dataset_as_of_time,
            results=result.results,
            result_digests=("0" * 64,),
        )


def test_snapshot_rejects_duplicate_result_digests():
    dataset = _snapshot()
    result = create_outcome_interpretation_snapshot(dataset)

    with pytest.raises(ValueError, match="duplicate"):
        OutcomeInterpretationSnapshot(
            source_dataset_digest=result.source_dataset_digest,
            source_dataset_as_of_time=result.source_dataset_as_of_time,
            results=(result.results[0], result.results[0]),
            result_digests=(
                result.results[0].digest,
                result.results[0].digest,
            ),
        )


def test_t03_does_not_fetch_or_require_external_evidence():
    dataset = _snapshot()

    result = create_outcome_interpretation_snapshot(dataset)

    assert result.result_count == dataset.observation_count
    assert result.source_dataset_digest == dataset.digest
    assert all(
        interpretation.source_observation_digest
        in dataset.observation_digests
        for interpretation in result.results
    )
