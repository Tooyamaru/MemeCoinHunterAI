from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from types import MappingProxyType

import pytest

from core.data.read_only_market_data import (
    CONTRACT_VERSION,
    EvaluationContext,
    FieldStatus,
    FreshnessBoundary,
    MetricEnvelope,
    ObservationKind,
    OrderingStatus,
    ProcessingContext,
    ProvenanceEnvelope,
    ReasonCode,
    ReadOnlyMarketDataObservation,
    SourceEnvelope,
    TimeWindow,
    derive_observation_id,
    process_observation,
    validate_observation,
)


UTC = timezone.utc
OBSERVED_AT = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
AVAILABLE_AT = OBSERVED_AT + timedelta(seconds=1)
CUTOFF = OBSERVED_AT + timedelta(seconds=10)


def context(
    *,
    cutoff_time: datetime = CUTOFF,
    profile: str = "paper-evaluation-v1",
    max_age_seconds: str | None = "60",
    boundary: FreshnessBoundary = FreshnessBoundary.INCLUSIVE,
    required_fields: tuple[str, ...] = ("asset_age", "liquidity", "price", "volume"),
    optional_fields: tuple[str, ...] = (),
    predecessor_digest: str | None = None,
    processing_identity: str = "processing-fixture-v1",
) -> EvaluationContext:
    return EvaluationContext(
        cutoff_time=cutoff_time,
        freshness_policy_version="freshness-v1",
        max_age_seconds=max_age_seconds,
        freshness_boundary=boundary,
        consumer_profile_version=profile,
        required_fields=required_fields,
        permitted_optional_fields=optional_fields,
        predecessor_context_digest=predecessor_digest,
        processing_context_identity=processing_identity,
    )


def metrics(*, include_optional: bool = False) -> dict[str, MetricEnvelope]:
    window = TimeWindow(
        start=OBSERVED_AT - timedelta(minutes=5),
        end=OBSERVED_AT,
        boundary=FreshnessBoundary.INCLUSIVE,
    )
    values = {
        "price": MetricEnvelope(
            status=FieldStatus.PRESENT,
            value={"amount": "1.25", "quote_asset": "USD"},
            unit="USD",
            semantic_version="price-v1",
            measurement_window=None,
            reference_semantics=None,
            source_field="price",
        ),
        "liquidity": MetricEnvelope(
            status=FieldStatus.PRESENT,
            value={
                "amount": "100000",
                "valuation_unit": "USD",
                "valuation_context": "source-v1",
            },
            unit="USD",
            semantic_version="liquidity-v1",
            measurement_window=None,
            reference_semantics=None,
            source_field="liquidity",
        ),
        "volume": MetricEnvelope(
            status=FieldStatus.PRESENT,
            value={"amount": "500.5"},
            unit="USD",
            semantic_version="volume-v1",
            measurement_window=window,
            reference_semantics=None,
            source_field="volume",
        ),
        "asset_age": MetricEnvelope(
            status=FieldStatus.PRESENT,
            value={"amount": "3600"},
            unit="SECONDS",
            semantic_version="asset-age-v1",
            measurement_window=None,
            reference_semantics="source-genesis",
            source_field="asset_age",
        ),
    }
    if include_optional:
        values["holders"] = MetricEnvelope(
            status=FieldStatus.PRESENT,
            value={"count": "42"},
            unit="COUNT",
            semantic_version="holders-v1",
            measurement_window=None,
            reference_semantics=None,
            source_field="holders",
        )
        values["transactions"] = MetricEnvelope(
            status=FieldStatus.PRESENT,
            value={"count": "7"},
            unit="COUNT",
            semantic_version="transactions-v1",
            measurement_window=window,
            reference_semantics=None,
            source_field="transactions",
        )
    return values


def observation(
    *,
    observation_id: str = "source-observation-1",
    source_event_id: str | None = "source-event-1",
    chain_id: str | None = "chain-A",
    market_subject_id: str | None = "market-A",
    kind: ObservationKind = ObservationKind.DISCOVERY,
    observed_at: datetime = OBSERVED_AT,
    availability_at: datetime = AVAILABLE_AT,
    observation_metrics: dict[str, MetricEnvelope] | None = None,
    evaluation_context: EvaluationContext | None = None,
    source_metadata: dict[str, str] | None = None,
    predecessor_digest: str | None = None,
    sequence: int | str | None = 1,
) -> ReadOnlyMarketDataObservation:
    selected_context = evaluation_context or context(predecessor_digest=predecessor_digest)
    selected_metrics = observation_metrics or metrics()
    source = SourceEnvelope(
        source_id="source-A",
        source_event_id=source_event_id,
        source_contract_version="source-v1",
        adapter_contract_version=CONTRACT_VERSION,
        source_observed_at=observed_at,
        source_metadata=source_metadata or {"fixture": "local"},
    )
    provenance = ProvenanceEnvelope(
        source_id=source.source_id,
        source_event_id=source.source_event_id,
        candidate_id="candidate-A",
        chain_id=chain_id,
        token_identity="token-A",
        market_subject_id=market_subject_id,
        observation_id=observation_id,
        observed_at=observed_at,
        availability_at=availability_at,
        cutoff_time=selected_context.cutoff_time,
        freshness_policy_version=selected_context.freshness_policy_version,
        consumer_profile_version=selected_context.consumer_profile_version,
        predecessor_digest=selected_context.predecessor_context_digest,
        field_provenance={
            name: {"source_field": name} for name in selected_metrics
        },
    )
    return ReadOnlyMarketDataObservation(
        contract_version=CONTRACT_VERSION,
        observation_id=observation_id,
        candidate_id="candidate-A",
        chain_id=chain_id,
        token_identity="token-A",
        market_subject_id=market_subject_id,
        observation_kind=kind,
        observed_at=observed_at,
        availability_at=availability_at,
        sequence=sequence,
        ordering_status=OrderingStatus.ORDERED,
        source=source,
        provenance=provenance,
        metrics=selected_metrics,
        evaluation_context=selected_context,
        raw_payload_digest="0" * 64,
    )


def test_valid_discovery_and_paper_evaluation_are_accepted() -> None:
    for kind in (ObservationKind.DISCOVERY, ObservationKind.PAPER_EVALUATION):
        item = observation(kind=kind)
        result = validate_observation(item, item.evaluation_context)
        assert result.reason_code is ReasonCode.VALID
        assert result.accepted is True
        assert result.state_changed is True
        assert result.observation_digest == item.observation_digest


def test_observation_and_nested_values_are_immutable() -> None:
    item = observation()
    assert isinstance(item.metrics, MappingProxyType)
    assert isinstance(item.source.source_metadata, MappingProxyType)
    with pytest.raises(FrozenInstanceError):
        item.candidate_id = "changed"
    with pytest.raises(TypeError):
        item.metrics["price"] = item.metrics["price"]
    with pytest.raises(TypeError):
        item.source.source_metadata["new"] = "value"


def test_equivalent_canonical_inputs_have_equal_digests() -> None:
    left = observation(source_metadata={"b": "two", "a": "one"})
    right = observation(source_metadata={"a": "one", "b": "two"})
    assert left.observation_digest == right.observation_digest
    assert validate_observation(left, left.evaluation_context) == validate_observation(
        right, right.evaluation_context
    )


def test_digest_tampering_is_rejected() -> None:
    item = observation()
    tampered = replace(item, raw_payload_digest="f" * 64, observation_digest=None)
    assert tampered.observation_digest != item.observation_digest
    result = validate_observation(tampered, tampered.evaluation_context)
    assert result.reason_code is ReasonCode.DIGEST_MISMATCH


def test_chain_id_null_is_only_valid_for_chain_neutral_profile() -> None:
    neutral_context = context(profile="chain-neutral-v1")
    valid = observation(
        chain_id=None,
        evaluation_context=neutral_context,
    )
    assert validate_observation(valid, neutral_context).reason_code is ReasonCode.VALID

    non_neutral_context = context()
    invalid = observation(chain_id=None, evaluation_context=non_neutral_context)
    assert validate_observation(invalid, non_neutral_context).reason_code is ReasonCode.INVALID_IDENTITY


@pytest.mark.parametrize(
    "item",
    [
        observation(
            source_metadata={"x" * 1025: "value"},
        ),
        observation(
            source_metadata={f"key-{index}": "value" for index in range(65)},
        ),
        observation(
            observation_metrics={
                **metrics(),
                "holders": MetricEnvelope(
                    status=FieldStatus.PRESENT,
                    value={"count": "100000000000000000000"},
                    unit="COUNT",
                    semantic_version="holders-v1",
                    measurement_window=None,
                    reference_semantics=None,
                    source_field="holders",
                ),
            },
            evaluation_context=context(optional_fields=("holders",)),
        ),
    ],
)
def test_scalar_and_mapping_bounds_fail_closed(item: ReadOnlyMarketDataObservation) -> None:
    result = validate_observation(item, item.evaluation_context)
    assert result.reason_code is ReasonCode.INVALID_CANONICAL_REPRESENTATION


def test_nested_mapping_depth_and_sequence_bounds_fail_closed() -> None:
    nested: dict[str, object] = {"leaf": "value"}
    for _ in range(8):
        nested = {"nested": nested}
    deep = observation(source_metadata=nested)
    assert (
        validate_observation(deep, deep.evaluation_context).reason_code
        is ReasonCode.INVALID_CANONICAL_REPRESENTATION
    )

    long_required = context(required_fields=tuple(f"price-{index}" for index in range(129)))
    item = observation(evaluation_context=long_required)
    assert (
        validate_observation(item, long_required).reason_code
        is ReasonCode.INVALID_CANONICAL_REPRESENTATION
    )


def test_optional_holders_and_transactions_require_profile_permission() -> None:
    permitted = context(optional_fields=("holders", "transactions"))
    item = observation(
        observation_metrics=metrics(include_optional=True),
        evaluation_context=permitted,
    )
    assert validate_observation(item, permitted).reason_code is ReasonCode.VALID

    forbidden_context = context()
    forbidden = observation(
        observation_metrics=metrics(include_optional=True),
        evaluation_context=forbidden_context,
    )
    assert (
        validate_observation(forbidden, forbidden_context).reason_code
        is ReasonCode.UNSUPPORTED_FIELD
    )


def test_missing_invalid_and_unsupported_inputs_have_stable_reasons() -> None:
    missing = observation(
        observation_metrics={name: value for name, value in metrics().items() if name != "price"}
    )
    assert (
        validate_observation(missing, missing.evaluation_context).reason_code
        is ReasonCode.MISSING_REQUIRED_INPUT
    )

    invalid_type = replace(observation(), chain_id=123, observation_digest=None)
    assert (
        validate_observation(invalid_type, invalid_type.evaluation_context).reason_code
        is ReasonCode.INVALID_TYPE
    )

    unsupported = replace(
        observation(),
        contract_version="p08-read-only-market-data-observation-v2",
        observation_digest=None,
    )
    assert (
        validate_observation(unsupported, unsupported.evaluation_context).reason_code
        is ReasonCode.UNSUPPORTED_VERSION
    )


def test_freshness_boundaries_future_and_stale_are_deterministic() -> None:
    inclusive_context = context(max_age_seconds="10", boundary=FreshnessBoundary.INCLUSIVE)
    inclusive = observation(evaluation_context=inclusive_context)
    assert validate_observation(inclusive, inclusive_context).reason_code is ReasonCode.VALID

    exclusive_context = context(max_age_seconds="10", boundary=FreshnessBoundary.EXCLUSIVE)
    exclusive = observation(evaluation_context=exclusive_context)
    assert (
        validate_observation(exclusive, exclusive_context).reason_code
        is ReasonCode.STALE_OBSERVATION
    )

    future_context = context(cutoff_time=CUTOFF)
    future = observation(
        observed_at=CUTOFF + timedelta(seconds=1),
        availability_at=CUTOFF + timedelta(seconds=2),
        evaluation_context=future_context,
    )
    assert (
        validate_observation(future, future_context).reason_code
        is ReasonCode.FUTURE_OBSERVATION
    )


def test_temporal_and_provenance_links_are_preserved() -> None:
    item = observation(predecessor_digest="a" * 64)
    result = validate_observation(item, item.evaluation_context)
    assert result.reason_code is ReasonCode.VALID
    assert result.provenance is item.provenance

    broken = replace(
        item,
        provenance=replace(item.provenance, token_identity="other-token"),
        observation_digest=None,
    )
    assert (
        validate_observation(broken, broken.evaluation_context).reason_code
        is ReasonCode.DIGEST_MISMATCH
    )


def test_duplicate_replay_contradiction_and_ordering_do_not_change_state() -> None:
    item = observation()
    first = validate_observation(item, item.evaluation_context)
    assert first.next_context is not None

    replay = validate_observation(item, item.evaluation_context, first.next_context)
    assert replay.reason_code is ReasonCode.REPLAY
    assert replay.state_changed is False

    duplicate_context = ProcessingContext(
        processing_context_identity=item.evaluation_context.processing_context_identity,
        accepted_fingerprints={item.observation_id: item.observation_digest},
    )
    duplicate = validate_observation(item, item.evaluation_context, duplicate_context)
    assert duplicate.reason_code is ReasonCode.DUPLICATE
    assert duplicate.state_changed is False

    changed_metrics = dict(item.metrics)
    changed_metrics["price"] = replace(
        changed_metrics["price"],
        value={"amount": "1.26", "quote_asset": "USD"},
        field_digest=None,
    )
    changed = replace(
        item,
        metrics=changed_metrics,
        observation_digest=None,
    )
    contradictory = validate_observation(changed, item.evaluation_context, duplicate_context)
    assert contradictory.reason_code is ReasonCode.CONTRADICTORY_INPUT
    assert contradictory.state_changed is False

    ordered_context = ProcessingContext(
        processing_context_identity=item.evaluation_context.processing_context_identity,
        latest_sequences={"source-A|chain-A|token-A|market-A": 3},
    )
    out_of_order = replace(item, sequence=2, observation_digest=None)
    out_result = validate_observation(out_of_order, out_of_order.evaluation_context, ordered_context)
    assert out_result.reason_code is ReasonCode.OUT_OF_ORDER
    assert out_result.state_changed is False


def test_reason_precedence_prefers_invalid_type_over_missing_input() -> None:
    item = observation(
        observation_metrics={
            name: value for name, value in metrics().items() if name != "price"
        }
    )
    invalid = replace(item, chain_id=123, observation_digest=None)
    result = validate_observation(invalid, invalid.evaluation_context)
    assert result.reason_code is ReasonCode.INVALID_TYPE


def test_derived_identity_is_stable_when_source_event_is_absent() -> None:
    initial = observation(observation_id="placeholder", source_event_id=None)
    derived = derive_observation_id(initial)
    item = replace(initial, observation_id=derived, observation_digest=None)
    assert derive_observation_id(item) == derived
    assert validate_observation(item, item.evaluation_context).reason_code is ReasonCode.VALID


def test_explicit_processing_context_is_not_mutated() -> None:
    item = observation()
    processing = ProcessingContext(
        processing_context_identity=item.evaluation_context.processing_context_identity
    )
    before = processing.context_digest
    result = process_observation(item, evaluation_context=item.evaluation_context, processing_context=processing)
    assert result.reason_code is ReasonCode.VALID
    assert processing.context_digest == before
    assert processing.accepted_fingerprints == {}