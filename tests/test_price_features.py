from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from core.data.contracts import DataQuality, FreshnessPolicy
from core.data.market_intelligence import (
    MarketIntelligenceCategory,
    MarketIntelligenceOutcome,
)
from core.features import (
    FeatureCalculationContext,
    FeatureCalculationStatus,
    FeatureReason,
    FeatureDefinition,
    PRICE_ACCELERATION,
    calculate_feature,
    calculate_price_acceleration,
    calculate_price_velocity,
)
from tests.test_market_intelligence import _observation, _processor


UTC = timezone.utc
BASE = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
REFERENCE = BASE + timedelta(seconds=10)
POLICY = FreshnessPolicy(stale_after=timedelta(minutes=1))


def _price(
    seconds: int,
    value: int | str,
    *,
    source_event_id: str | None = None,
    observation_id: str | None = None,
    **overrides,
):
    observed = BASE + timedelta(seconds=seconds)
    received = observed + timedelta(seconds=1)
    defaults = {
        "source_event_id": source_event_id or f"price-{seconds}",
        "sequence": seconds + 1,
        "value": value,
        "observation_time": observed,
        "received_time": received,
        "reference_time": REFERENCE,
        "data_age": REFERENCE - observed,
        "observation_metadata": {
            "measurement": "price",
            "unit": "USD",
            "quote_asset": "USDC",
        },
    }
    values = dict(defaults)
    values.update(overrides)
    safe_values = dict(values)
    for field in ("observation_time", "received_time", "reference_time", "data_age"):
        safe_values[field] = defaults[field]
    accepted = _processor().process(
        _observation(**safe_values)
    ).observation
    assert accepted is not None
    accepted = replace(
        accepted,
        **{
            field: values[field]
            for field in ("observation_time", "received_time", "reference_time", "data_age")
            if field in overrides
        },
    )
    if observation_id is not None:
        accepted = replace(
            accepted,
            observation_id=observation_id,
            provenance=replace(accepted.provenance, observation_id=observation_id),
        )
    return accepted


def _context(
    *,
    reference_time: datetime | None = REFERENCE,
    policy: FreshnessPolicy | None = POLICY,
):
    return FeatureCalculationContext(reference_time, policy, evaluation_id="eval-1")


def test_velocity_uses_latest_two_observations_and_is_deterministic():
    observations = [_price(0, 10), _price(2, 14), _price(5, 20)]

    left = calculate_price_velocity(observations, context=_context())
    right = calculate_price_velocity(list(reversed(observations)), context=_context())

    assert left.status is FeatureCalculationStatus.CALCULATED
    assert left.value == Decimal("2")
    assert left.value_unit == "USD/second"
    assert left.representation_digest == right.representation_digest
    assert left.canonical_representation == right.canonical_representation


def test_acceleration_uses_irregular_interval_formula():
    result = calculate_price_acceleration(
        [_price(0, 10), _price(2, 16), _price(5, 19)],
        context=_context(),
    )

    assert result.status is FeatureCalculationStatus.CALCULATED
    assert result.value == Decimal("-0.8")
    assert result.value_unit == "USD/second^2"


@pytest.mark.parametrize(
    ("observations", "context", "reason"),
    [
        ([_price(0, 10)], _context(), FeatureReason.INSUFFICIENT_PRICE_OBSERVATIONS),
        ([_price(0, 10), _price(2, 14)], _context(policy=None), FeatureReason.MISSING_CALCULATION_CONTEXT),
        ([_price(0, 10), _price(2, 14)], None, FeatureReason.MISSING_CALCULATION_CONTEXT),
    ],
)
def test_missing_required_inputs_are_unknown_without_a_value(observations, context, reason):
    result = calculate_price_velocity(observations, context=context)

    assert result.status is FeatureCalculationStatus.UNKNOWN
    assert reason.value in result.reason_codes
    assert result.value is None


def test_stale_input_is_rejected_at_explicit_reference_time():
    result = calculate_price_velocity(
        [_price(0, 10), _price(2, 14)],
        context=_context(policy=FreshnessPolicy(stale_after=timedelta(seconds=5))),
    )

    assert result.status is FeatureCalculationStatus.UNKNOWN
    assert result.reason_codes == (FeatureReason.STALE_INPUT.value,)
    assert result.value is None


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("observation_time", FeatureReason.FUTURE_OBSERVATION),
        ("received_time", FeatureReason.NOT_AVAILABLE_AT_REFERENCE_TIME),
    ],
)
def test_future_and_not_available_inputs_fail_closed(field, reason):
    future = BASE + timedelta(seconds=11)
    overrides = {field: future}
    if field == "observation_time":
        overrides["data_age"] = REFERENCE - future
    result = calculate_price_velocity(
        [_price(0, 10), _price(2, 14, **overrides)],
        context=_context(),
    )

    assert result.status is FeatureCalculationStatus.INVALID
    assert reason.value in result.reason_codes
    assert result.value is None


def test_missing_price_semantics_is_unknown_and_not_inferred():
    result = calculate_price_velocity(
        [
            _price(
                0,
                10,
                observation_metadata={"measurement": "price"},
            ),
            _price(2, 14),
        ],
        context=_context(),
    )

    assert result.status is FeatureCalculationStatus.UNKNOWN
    assert result.reason_codes == (FeatureReason.MISSING_PRICE_SEMANTICS.value,)
    assert result.value is None


def test_units_quotes_duplicates_and_contradictions_fail_closed():
    incompatible = calculate_price_velocity(
        [_price(0, 10), _price(2, 14, observation_metadata={"measurement": "price", "unit": "EUR", "quote_asset": "USDC"})],
        context=_context(),
    )
    duplicate = calculate_price_velocity(
        [_price(0, 10), _price(0, 10)],
        context=_context(),
    )
    contradiction = calculate_price_velocity(
        [_price(0, 10, observation_id="same"), _price(2, 14, observation_id="same")],
        context=_context(),
    )

    assert incompatible.status is FeatureCalculationStatus.UNKNOWN
    assert FeatureReason.INCOMPATIBLE_PRICE_UNIT.value in incompatible.reason_codes
    assert duplicate.status is FeatureCalculationStatus.UNKNOWN
    assert FeatureReason.DUPLICATE_INPUT.value in duplicate.reason_codes
    assert contradiction.status is FeatureCalculationStatus.UNKNOWN
    assert FeatureReason.CONTRADICTORY_INPUT.value in contradiction.reason_codes


def test_zero_elapsed_time_and_nonfinite_values_are_invalid():
    equal_time = calculate_price_velocity([_price(1, 10), _price(1, 14)], context=_context())
    nonfinite = calculate_price_velocity(
        [replace(_price(0, 10), value=float("inf")), _price(2, 14)],
        context=_context(),
    )

    assert equal_time.status is FeatureCalculationStatus.INVALID
    assert equal_time.reason_codes == (FeatureReason.ZERO_ELAPSED_TIME.value,)
    assert nonfinite.status is FeatureCalculationStatus.INVALID
    assert nonfinite.reason_codes == (FeatureReason.INVALID_NUMERIC_VALUE.value,)


def test_rejected_upstream_and_out_of_scope_categories_are_not_numeric():
    rejected = replace(_price(0, 10), quality=DataQuality.STALE)
    quality_result = calculate_price_velocity([rejected, _price(2, 14)], context=_context())
    unsupported = calculate_feature(
        FeatureDefinition("transaction_frequency", "transaction-frequency-v1"),
        [_price(0, 10), _price(2, 14)],
        context=_context(),
    )
    category = replace(_price(0, 10), intelligence_category=MarketIntelligenceCategory.VOLUME)
    category_result = calculate_price_velocity([category, _price(2, 14)], context=_context())

    assert quality_result.status is FeatureCalculationStatus.UNKNOWN
    assert quality_result.value is None
    assert unsupported.status is FeatureCalculationStatus.UNSUPPORTED
    assert unsupported.reason_codes == (FeatureReason.UNSUPPORTED_FEATURE.value,)
    assert category_result.status is FeatureCalculationStatus.UNSUPPORTED
    assert category_result.reason_codes == (FeatureReason.UNSUPPORTED_CATEGORY.value,)


def test_provenance_snapshot_linkage_and_input_immutability_are_preserved():
    observations = [_price(0, 10), _price(2, 14)]
    before = tuple(observations)
    result = calculate_price_velocity(observations, context=_context())

    assert result.status is FeatureCalculationStatus.CALCULATED
    assert result.snapshot_linkage.input_set_digest == result.input_set_digest
    assert result.snapshot_linkage.feature_representation_digest == result.representation_digest
    assert tuple(item.observation_id for item in result.inputs) == tuple(
        sorted(item.observation_id for item in observations)
    )
    assert all(item.state_digest == "p02-t08-state-digest" for item in result.upstream_references)
    assert observations == list(before)
    assert result.canonical_representation["value"] == "2"