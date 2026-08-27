from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from core.learning import (
    OutcomeLearningDatasetSnapshot,
    P08_T02_CONTRACT_VERSION,
    create_outcome_learning_dataset_snapshot,
)
from tests.test_outcome_learning import _observation


def _second_observation():
    observation = _observation()
    result = replace(
        observation.paper_result,
        fill_digest="fill-2",
    )
    from core.execution import PaperSimulationResultHistory
    from core.learning import create_outcome_learning_observation

    return create_outcome_learning_observation(
        observation.decision_intent,
        observation.simulation_input,
        result,
        PaperSimulationResultHistory((result,)),
    )


def test_snapshot_preserves_valid_observations_and_provenance():
    first = _observation()
    second = _second_observation()
    snapshot = create_outcome_learning_dataset_snapshot(
        (second, first),
        as_of_time=first.simulation_reference_time + timedelta(hours=1),
    )

    assert isinstance(snapshot, OutcomeLearningDatasetSnapshot)
    assert all(
        any(candidate is source for source in (first, second))
        for candidate in snapshot.observations
    )
    assert snapshot.observation_count == 2
    assert snapshot.observation_digests == tuple(
        observation.digest for observation in snapshot.observations
    )
    assert snapshot.source_observation_digests == snapshot.observation_digests
    assert snapshot.contract_version == P08_T02_CONTRACT_VERSION
    assert snapshot.observations[0] is first or snapshot.observations[0] is second


def test_snapshot_order_digest_and_cutoff_are_reproducible():
    first = _observation()
    second = _second_observation()
    cutoff = first.simulation_reference_time + timedelta(hours=1)

    left = create_outcome_learning_dataset_snapshot((first, second), cutoff)
    right = create_outcome_learning_dataset_snapshot((second, first), cutoff)

    assert left.observations == right.observations
    assert left.canonical_representation == right.canonical_representation
    assert left.digest == right.digest
    assert left.as_of_time.tzinfo is timezone.utc


def test_snapshot_rejects_empty_duplicate_and_future_observations():
    first = _observation()
    cutoff = first.simulation_reference_time

    with pytest.raises(ValueError, match="at least one"):
        create_outcome_learning_dataset_snapshot((), cutoff)
    with pytest.raises(ValueError, match="duplicate"):
        create_outcome_learning_dataset_snapshot((first, first), cutoff)
    with pytest.raises(ValueError, match="after"):
        create_outcome_learning_dataset_snapshot(
            (first,),
            first.simulation_reference_time - timedelta(seconds=1),
        )


def test_snapshot_rejects_invalid_tampered_and_unsupported_inputs():
    first = _observation()

    with pytest.raises(ValueError, match="OutcomeLearningObservation"):
        create_outcome_learning_dataset_snapshot((object(),), first.simulation_reference_time)

    object.__setattr__(first.decision_intent.context, "candidate_id", "tampered")
    with pytest.raises(ValueError, match="invalid|tampered|DecisionIntent"):
        create_outcome_learning_dataset_snapshot((first,), first.simulation_reference_time)

    clean = _observation()
    with pytest.raises(ValueError, match="contract version"):
        OutcomeLearningDatasetSnapshot(
            observations=(clean,),
            as_of_time=clean.simulation_reference_time,
            observation_digests=(clean.digest,),
            contract_version="p08-t99-v1",
        )


def test_snapshot_preserves_unknown_information_without_interpretation():
    observation = _observation()
    unknown_result = replace(
        observation.paper_result,
        status="UNAVAILABLE",
        reconciliation_status="UNKNOWN",
    )
    from core.execution import PaperSimulationResultHistory
    from core.learning import create_outcome_learning_observation

    unknown_observation = create_outcome_learning_observation(
        observation.decision_intent,
        observation.simulation_input,
        unknown_result,
        PaperSimulationResultHistory((unknown_result,)),
    )
    snapshot = create_outcome_learning_dataset_snapshot(
        (unknown_observation,),
        unknown_observation.simulation_reference_time,
    )

    assert snapshot.observations[0].outcome_status == "UNAVAILABLE"
    assert snapshot.observations[0].reconciliation_status == "UNKNOWN"


def test_snapshot_is_immutable_and_does_not_add_learning_or_execution_authority():
    observation = _observation()
    snapshot = create_outcome_learning_dataset_snapshot(
        [observation],
        observation.simulation_reference_time,
    )

    with pytest.raises(FrozenInstanceError):
        snapshot.as_of_time = datetime.now(timezone.utc)
    assert isinstance(snapshot.observations, tuple)
    assert not hasattr(snapshot, "win_loss")
    assert not hasattr(snapshot, "ranking")
    assert not hasattr(snapshot, "model_update")
    assert not hasattr(snapshot, "execution")