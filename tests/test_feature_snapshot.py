from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal
import builtins
import os
from pathlib import Path
import random
import socket
import time
from types import MappingProxyType
import urllib.request

import pytest

from core.features import (
    FeatureCalculationStatus,
    FeatureCalculationSnapshot,
    FeatureInputReference,
    FeatureUpstreamReference,
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


def test_snapshot_canonical_representation_is_complete():
    snapshot = create_feature_calculation_snapshot(_result())

    assert set(snapshot.canonical_representation) == {
        "calculation_result_id",
        "status",
        "reason_codes",
        "feature_id",
        "feature_version",
        "calculation_contract_version",
        "value",
        "value_unit",
        "price_unit",
        "quote_asset",
        "source_id",
        "chain_id",
        "token_identity",
        "market_subject_id",
        "reference_time",
        "freshness_policy",
        "evaluation_id",
        "inputs",
        "upstream_references",
        "input_set_digest",
        "snapshot_linkage",
        "result_representation_digest",
        "contract_version",
    }
    assert set(snapshot.canonical_representation["snapshot_linkage"]) == {
        "reference_time",
        "input_set_digest",
        "observation_ids",
        "upstream_references",
        "p02_contract_version",
        "feature_representation_digest",
    }


def test_snapshot_and_nested_representation_are_immutable():
    snapshot = create_feature_calculation_snapshot(_result())

    with pytest.raises(FrozenInstanceError):
        snapshot.value = Decimal("99")
    with pytest.raises(TypeError):
        snapshot.canonical_representation["new"] = "value"
    assert isinstance(snapshot.canonical_representation, MappingProxyType)
    with pytest.raises(TypeError):
        snapshot.canonical_representation["inputs"][0]["value"] = "99"


def test_snapshot_normalizes_non_utc_result_reference_time():
    reference_time = _result().reference_time.astimezone(
        timezone(timedelta(hours=7))
    )
    result = calculate_price_velocity(
        [_price(0, 10), _price(2, 14)],
        context=_context(reference_time=reference_time),
    )

    snapshot = create_feature_calculation_snapshot(result)

    assert snapshot.reference_time == reference_time.astimezone(timezone.utc)
    assert snapshot.canonical_representation["reference_time"] == (
        reference_time.astimezone(timezone.utc).isoformat()
    )


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


@pytest.mark.parametrize(
    "tampered",
    [
        pytest.param(lambda result: replace(result, value=float("nan")), id="nan"),
        pytest.param(lambda result: replace(result, value=float("inf")), id="infinity"),
        pytest.param(lambda result: replace(result, value="2"), id="non-decimal"),
        pytest.param(
            lambda result: replace(
                result,
                status=FeatureCalculationStatus.UNKNOWN,
                value=Decimal("2"),
                value_unit="USD/second",
            ),
            id="non-calculated-value",
        ),
    ],
)
def test_invalid_calculated_value_shapes_fail_closed(tampered):
    outcome = snapshot_feature_calculation_result(tampered(_result()))

    assert outcome.status is FeatureSnapshotStatus.INVALID_INPUT
    assert outcome.snapshot is None
    assert outcome.reason_codes == ("INVALID_CALCULATION_RESULT",)


def test_non_normalized_reason_codes_are_rejected():
    outcome = snapshot_feature_calculation_result(
        replace(_result(), reason_codes=("Z_REASON", "A_REASON"))
    )

    assert outcome.status is FeatureSnapshotStatus.INVALID_INPUT
    assert outcome.reason_codes == ("INVALID_CALCULATION_RESULT",)


@pytest.mark.parametrize(
    "tampered",
    [
        pytest.param(
            lambda result: replace(result, reference_time=result.reference_time.replace(tzinfo=None)),
            id="naive-reference-time",
        ),
        pytest.param(
            lambda result: replace(
                result,
                inputs=(
                    replace(result.inputs[0], observation_time=result.inputs[0].observation_time.replace(tzinfo=None)),
                    result.inputs[1],
                ),
            ),
            id="naive-observation-time",
        ),
    ],
)
def test_naive_timestamps_are_rejected(tampered):
    outcome = snapshot_feature_calculation_result(tampered(_result()))

    assert outcome.status is FeatureSnapshotStatus.INVALID_INPUT
    assert outcome.snapshot is None


@pytest.mark.parametrize("field", ["inputs", "upstream_references"])
def test_malformed_input_and_upstream_references_are_rejected(field):
    result = _result()
    tampered = replace(result, **{field: (object(),)})

    outcome = snapshot_feature_calculation_result(tampered)

    assert outcome.status is FeatureSnapshotStatus.INVALID_INPUT
    assert outcome.snapshot is None
    assert outcome.reason_codes == ("INVALID_CALCULATION_RESULT",)


def test_input_set_digest_mismatch_is_rejected():
    outcome = snapshot_feature_calculation_result(
        replace(_result(), input_set_digest="tampered-input-digest")
    )

    assert outcome.status is FeatureSnapshotStatus.INVALID_INPUT
    assert outcome.snapshot is None


def test_snapshot_linkage_mismatch_is_rejected():
    result = _result()
    tampered = replace(
        result,
        snapshot_linkage=replace(
            result.snapshot_linkage,
            observation_ids=(),
        ),
    )

    outcome = snapshot_feature_calculation_result(tampered)

    assert outcome.status is FeatureSnapshotStatus.INVALID_INPUT
    assert outcome.snapshot is None


@pytest.mark.parametrize(
    "tampered",
    [
        pytest.param(lambda result: replace(result, result_id="tampered"), id="result-id"),
        pytest.param(
            lambda result: replace(result, representation_digest="tampered"),
            id="representation-digest",
        ),
    ],
)
def test_result_identity_and_representation_digest_mismatches_are_rejected(tampered):
    outcome = snapshot_feature_calculation_result(tampered(_result()))

    assert outcome.status is FeatureSnapshotStatus.INVALID_INPUT
    assert outcome.snapshot is None


def test_future_received_time_is_rejected_without_fallback():
    result = _result()
    future_input = replace(
        result.inputs[0],
        received_time=result.reference_time + timedelta(seconds=1),
    )
    outcome = snapshot_feature_calculation_result(
        replace(result, inputs=(future_input, result.inputs[1]))
    )

    assert outcome.status is FeatureSnapshotStatus.INVALID_INPUT
    assert outcome.snapshot is None


def test_snapshot_creation_does_not_mutate_source_result_or_references():
    result = _result()
    before_representation = result.canonical_representation
    before_inputs = result.inputs
    before_upstream = result.upstream_references

    snapshot = create_feature_calculation_snapshot(result)

    assert snapshot.inputs == before_inputs
    assert snapshot.upstream_references == before_upstream
    assert result.canonical_representation == before_representation
    assert result.inputs == before_inputs
    assert result.upstream_references == before_upstream


def test_snapshot_result_is_explicit_and_deterministic():
    first = snapshot_feature_calculation_result(_result())
    second = snapshot_feature_calculation_result(_result())

    assert first.status is FeatureSnapshotStatus.SNAPSHOTTED
    assert first.valid is True
    assert first.snapshot is not None
    assert first == second
    assert first.digest == second.digest


def test_snapshot_result_wrapper_is_immutable():
    outcome = snapshot_feature_calculation_result(_result())

    with pytest.raises(FrozenInstanceError):
        outcome.snapshot = None
    with pytest.raises(FrozenInstanceError):
        outcome.reason_codes = ("tampered",)


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


def test_snapshot_is_independent_of_clock_environment_and_external_io(monkeypatch):
    def unexpected_call(*args, **kwargs):
        raise AssertionError("T10 must not use wall-clock, environment, or I/O")

    monkeypatch.setattr(time, "time", unexpected_call)
    monkeypatch.setattr(random, "random", unexpected_call)
    monkeypatch.setattr(os, "getenv", unexpected_call)
    monkeypatch.setattr(socket, "socket", unexpected_call)
    monkeypatch.setattr(urllib.request, "urlopen", unexpected_call)
    monkeypatch.setattr(Path, "read_text", unexpected_call)
    monkeypatch.setattr(builtins, "open", unexpected_call)

    first = create_feature_calculation_snapshot(_result())
    second = create_feature_calculation_snapshot(_result())

    assert first.canonical_representation == second.canonical_representation
    assert first.digest == second.digest