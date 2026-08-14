from dataclasses import FrozenInstanceError, replace

import pytest

from core.features import (
    FeatureCalculationSnapshotHistory,
    FeatureSnapshotHistoryOutcome,
    create_feature_calculation_snapshot,
    calculate_price_velocity,
)
from tests.test_price_features import _context, _price


def _snapshot(seconds: int, value: int, event: str):
    result = calculate_price_velocity(
        [
            _price(0, 10, source_event_id=f"{event}-first"),
            _price(seconds, value, source_event_id=f"{event}-last"),
        ],
        context=_context(),
    )
    return create_feature_calculation_snapshot(result)


def test_history_stores_valid_snapshot_and_returns_immutable_history():
    snapshot = _snapshot(2, 14, "one")
    history = FeatureCalculationSnapshotHistory()

    result = history.append(snapshot)

    assert result.outcome is FeatureSnapshotHistoryOutcome.STORED
    assert result.accepted is True
    assert result.snapshot is snapshot
    assert history.retrieve() == (snapshot,)
    assert history.retrieve()[0] is snapshot
    assert history.snapshot_count == 1
    assert history.representation_digest == result.history_digest
    assert isinstance(history.retrieve(), tuple)


def test_history_is_deterministic_independent_of_insertion_order():
    first = _snapshot(2, 14, "first")
    second = _snapshot(5, 20, "second")

    left = FeatureCalculationSnapshotHistory()
    left.append(second)
    left.append(first)
    right = FeatureCalculationSnapshotHistory([first, second])

    assert left.retrieve() == right.retrieve()
    assert left.digest == right.digest
    assert tuple(item.digest for item in left.retrieve()) == tuple(
        sorted((first.digest, second.digest), key=lambda value: value)
    ) or left.retrieve() == tuple(
        sorted((first, second), key=lambda value: value.digest)
    )


def test_history_deduplicates_by_snapshot_digest():
    snapshot = _snapshot(2, 14, "duplicate")
    history = FeatureCalculationSnapshotHistory()

    first = history.append(snapshot)
    duplicate = history.append(snapshot)

    assert first.outcome is FeatureSnapshotHistoryOutcome.STORED
    assert duplicate.outcome is FeatureSnapshotHistoryOutcome.DUPLICATE
    assert duplicate.snapshot is snapshot
    assert history.snapshot_count == 1


def test_history_deduplicates_separate_equivalent_snapshot_objects_by_digest():
    first_snapshot = _snapshot(2, 14, "equivalent")
    second_snapshot = _snapshot(2, 14, "equivalent")
    history = FeatureCalculationSnapshotHistory()

    first = history.append(first_snapshot)
    duplicate = history.append(second_snapshot)

    assert first_snapshot is not second_snapshot
    assert first_snapshot == second_snapshot
    assert first_snapshot.digest == second_snapshot.digest
    assert first.outcome is FeatureSnapshotHistoryOutcome.STORED
    assert duplicate.outcome is FeatureSnapshotHistoryOutcome.DUPLICATE
    assert duplicate.snapshot is first_snapshot
    assert history.retrieve() == (first_snapshot,)


def test_empty_history_is_safe_and_deterministic():
    left = FeatureCalculationSnapshotHistory()
    right = FeatureCalculationSnapshotHistory.from_snapshots([])

    assert left.retrieve() == ()
    assert left.history == ()
    assert left.snapshot_count == 0
    assert left.digest == right.digest


def test_history_result_and_read_view_are_immutable():
    result = FeatureCalculationSnapshotHistory().append(_snapshot(2, 14, "immutable"))

    with pytest.raises(FrozenInstanceError):
        result.outcome = FeatureSnapshotHistoryOutcome.INVALID_INPUT
    with pytest.raises(FrozenInstanceError):
        result.snapshots = ()
    with pytest.raises(TypeError):
        result.snapshots[0].canonical_representation["tampered"] = True


def test_same_snapshot_set_has_the_same_history_digest_across_instances():
    left = FeatureCalculationSnapshotHistory(
        [_snapshot(2, 14, "digest-a"), _snapshot(5, 20, "digest-b")]
    )
    right = FeatureCalculationSnapshotHistory(
        [_snapshot(5, 20, "digest-b"), _snapshot(2, 14, "digest-a")]
    )

    assert left.retrieve() == right.retrieve()
    assert left.history_digest == right.history_digest
    assert left.history_digest == left.representation_digest
    assert right.history_digest == right.digest


def test_invalid_insertion_does_not_mutate_history():
    snapshot = _snapshot(2, 14, "valid")
    history = FeatureCalculationSnapshotHistory([snapshot])
    before = history.retrieve()
    before_digest = history.digest

    result = history.append(object())

    assert result.outcome is FeatureSnapshotHistoryOutcome.INVALID_INPUT
    assert result.accepted is False
    assert result.snapshot is None
    assert result.reason_codes == ("INVALID_SNAPSHOT",)
    assert history.retrieve() == before
    assert history.digest == before_digest


def test_tampered_snapshot_is_rejected_without_history_mutation():
    snapshot = _snapshot(2, 14, "tampered")
    original = snapshot.digest
    tampered = replace(snapshot)
    object.__setattr__(tampered, "contract_version", "")
    history = FeatureCalculationSnapshotHistory()

    result = history.append(tampered)

    assert result.outcome is FeatureSnapshotHistoryOutcome.INVALID_INPUT
    assert history.retrieve() == ()
    assert tampered.digest != original