from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal
from types import MappingProxyType

import pytest

from core.features import (
    FeatureCalculationSnapshot,
    FeatureSnapshotStatus,
    calculate_price_velocity,
    create_feature_calculation_snapshot,
    snapshot_feature_calculation_result,
)
from tests.test_price_features import _context, _price


def _result():
    return calculate_price_velocity(
        [_price(0, 10), _price(2, 14)],
        context=_context(),
    )


def test_valid_snapshot_preserves_t09_result_and_provenance():
    result = _result()

    snapshot = create_feature_calculation_snapshot(result)

    assert snapshot.calculation_result_id == result.result_id
    assert snapshot.status is result.status
    assert snapshot.feature_id == result.feature_id
    assert snapshot.feature_version == result.feature_version
    assert snapshot.value == Decimal("2")
    assert snapshot.reference_time == result.reference_time
    assert snapshot.inputs == result.inputs
    assert snapshot.upstream_references == result.upstream_references
    assert snapshot.input_set_digest == result.input_set_digest
    assert snapshot.snapshot_linkage == result.snapshot_linkage
    assert snapshot.result_representation_digest == result.representation_digest


def test_snapshot_and_nested_representation_are_immutable():
    snapshot = create_feature_calculation_snapshot(_result())

    with pytest.raises(FrozenInstanceError):
        snapshot.value = Decimal("99")
    with pytest.raises(TypeError):
        snapshot.canonical_representation["new"] = "value"
    assert isinstance(snapshot.canonical_representation, MappingProxyType)
    with pytest.raises(TypeError):
        snapshot.canonical_representation["inputs"][0]["value"] = "99"


def test_repeated_creation_and_equivalent_input_order_are_deterministic():
    first_result = calculate_price_velocity(
        [_price(0, 10), _price(2, 14)],
        context=_context(),
    )
    second_result = calculate_price_velocity(
        list(reversed([_price(0, 10), _price(2, 14)])),
        context=_context(),
    )

    first = create_feature_calculation_snapshot(first_result)
    second = create_feature_calculation_snapshot(second_result)

    assert first == second
    assert first.canonical_representation == second.canonical_representation
    assert first.digest == second.digest
    assert first.digest == create_feature_calculation_snapshot(first_result).digest


def test_snapshot_result_is_explicit_and_deterministic():
    first = snapshot_feature_calculation_result(_result())
    second = snapshot_feature_calculation_result(_result())

    assert first.status is FeatureSnapshotStatus.SNAPSHOTTED
    assert first.valid is True
    assert first.snapshot is not None
    assert first == second
    assert first.digest == second.digest


def test_tampered_result_is_rejected_without_mutation():
    result = _result()
    before = result.canonical_representation
    tampered = replace(result, value=Decimal("999"))

    outcome = snapshot_feature_calculation_result(tampered)

    assert outcome.status is FeatureSnapshotStatus.INVALID_INPUT
    assert outcome.snapshot is None
    assert result.canonical_representation == before


def test_input_after_reference_time_is_rejected_at_snapshot_boundary():
    result = _result()
    future_input = replace(
        result.inputs[0],
        observation_time=result.reference_time + timedelta(seconds=1),
    )
    tampered = replace(result, inputs=(future_input, result.inputs[1]))

    outcome = snapshot_feature_calculation_result(tampered)

    assert outcome.status is FeatureSnapshotStatus.INVALID_INPUT
    assert outcome.reason_codes == ("INVALID_CALCULATION_RESULT",)


def test_invalid_snapshot_input_fails_closed():
    result = snapshot_feature_calculation_result(object())

    assert result.status is FeatureSnapshotStatus.INVALID_INPUT
    assert result.snapshotted is False
    assert result.snapshot is None
    assert result.reason_codes == ("INVALID_CALCULATION_RESULT",)


def test_direct_snapshot_creation_rejects_invalid_result():
    with pytest.raises(ValueError, match="INVALID_CALCULATION_RESULT"):
        FeatureCalculationSnapshot.from_result(object())