from datetime import datetime, timedelta, timezone
from typing import Mapping

import pytest

from core.data.contracts import (
    DataQuality,
    FreshnessPolicy,
    NormalizationContext,
    OrderingStatus,
    ProviderNeutralAdapter,
    RawEvent,
    SourceHealthStatus,
    SourceHealthTracker,
    canonical_identity,
    normalize_raw_event,
    validate_raw_event,
)


UTC = timezone.utc
EVENT_TIME = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
RECEIVED_TIME = EVENT_TIME + timedelta(seconds=1)
PROCESSING_TIME = RECEIVED_TIME + timedelta(seconds=1)
REFERENCE_TIME = EVENT_TIME + timedelta(seconds=10)
POLICY = FreshnessPolicy(stale_after=timedelta(minutes=1))


def event(
    *,
    payload: Mapping[str, object] | object = {"price": 1},
    source_event_id: str | None = "evt-1",
    sequence: int | str | None = 1,
    event_time: object = EVENT_TIME,
    received_time: object = RECEIVED_TIME,
) -> RawEvent:
    return RawEvent(
        source_id="fixture-source",
        source_event_id=source_event_id,
        payload=payload,  # type: ignore[arg-type]
        event_time=event_time,  # type: ignore[arg-type]
        received_time=received_time,  # type: ignore[arg-type]
        sequence=sequence,
        source_metadata={"fixture": "local"},
    )


def normalize(
    raw: RawEvent,
    *,
    context: NormalizationContext | None = None,
    source_health=None,
):
    return normalize_raw_event(
        raw,
        processing_time=PROCESSING_TIME,
        reference_time=REFERENCE_TIME,
        freshness_policy=POLICY,
        context=context,
        source_health=source_health,
    )


def test_valid_event() -> None:
    result = normalize(event())
    assert result.quality_status is DataQuality.VALID
    assert result.state is not None
    assert result.state.ordering_status is OrderingStatus.FIRST


def test_malformed_event_is_invalid() -> None:
    raw = event(payload={"bad": object()})
    quality, errors = validate_raw_event(raw)
    assert quality is DataQuality.INVALID
    assert "unsupported value type" in errors[0]


def test_malformed_event_normalization_returns_invalid_state() -> None:
    result = normalize(event(payload={"bad": object()}))
    assert result.quality_status is DataQuality.INVALID
    assert result.state is not None
    assert result.state.payload == {}


def test_incomplete_event_is_not_valid() -> None:
    quality, errors = validate_raw_event(event(event_time=None))
    assert quality is DataQuality.INCOMPLETE
    assert "event_time is required" in errors


def test_stale_event_uses_configured_policy() -> None:
    raw = event(event_time=EVENT_TIME - timedelta(minutes=2))
    result = normalize(raw)
    assert result.quality_status is DataQuality.STALE
    assert result.state is not None
    assert result.state.data_age == timedelta(minutes=2, seconds=10)


def test_duplicate_event_is_detected_deterministically() -> None:
    context = NormalizationContext()
    assert normalize(event(), context=context).quality_status is DataQuality.VALID
    duplicate = normalize(event(), context=context)
    assert duplicate.quality_status is DataQuality.DUPLICATE


def test_out_of_order_sequence_is_rejected() -> None:
    context = NormalizationContext()
    normalize(event(sequence=3), context=context)
    result = normalize(event(source_event_id="evt-2", sequence=2), context=context)
    assert result.quality_status is DataQuality.OUT_OF_ORDER
    assert result.state is not None
    assert result.state.ordering_status is OrderingStatus.OUT_OF_ORDER


def test_contradictory_payload_with_same_identity_is_visible() -> None:
    context = NormalizationContext()
    normalize(event(), context=context)
    result = normalize(event(payload={"price": 2}), context=context)
    assert result.quality_status is DataQuality.CONTRADICTORY


def test_unavailable_source_is_not_fresh_valid_data() -> None:
    health = SourceHealthTracker()
    failed = health.observe_failure("fixture-source", RECEIVED_TIME, "fixture timeout")
    result = normalize(event(), source_health=failed)
    assert result.quality_status is DataQuality.SOURCE_UNAVAILABLE


def test_unrelated_source_failure_does_not_poison_event() -> None:
    health = SourceHealthTracker()
    failed = health.observe_failure("other-source", RECEIVED_TIME, "fixture timeout")
    result = normalize(event(), source_health=failed)
    assert result.quality_status is DataQuality.VALID


def test_recovery_requires_an_accepted_event() -> None:
    health = SourceHealthTracker()
    health.observe_failure("fixture-source", RECEIVED_TIME, "fixture timeout")
    still_failed = health.observe_success("fixture-source", PROCESSING_TIME, accepted_event=False)
    assert still_failed.status is SourceHealthStatus.FAILED
    recovered = health.observe_success("fixture-source", PROCESSING_TIME, accepted_event=True)
    assert recovered.status is SourceHealthStatus.AVAILABLE
    assert recovered.recovery_observed_time == PROCESSING_TIME


def test_normalization_is_deterministic() -> None:
    first = normalize(event(payload={"b": 2, "a": 1}))
    second = normalize(event(payload={"a": 1, "b": 2}))
    assert first.state == second.state


def test_freshness_calculation_uses_fixed_reference_time() -> None:
    result = normalize(event())
    assert result.state is not None
    assert result.state.data_age == timedelta(seconds=10)


def test_missing_sequence_does_not_claim_ordering() -> None:
    result = normalize(event(sequence=None))
    assert result.quality_status is DataQuality.VALID
    assert result.state is not None
    assert result.state.ordering_status is OrderingStatus.NOT_PROVIDED


def test_identity_collision_is_contradiction_not_duplicate() -> None:
    context = NormalizationContext()
    normalize(event(payload={"price": 1}), context=context)
    result = normalize(event(payload={"price": 2}), context=context)
    assert result.quality_status is DataQuality.CONTRADICTORY
    assert result.quality_status is not DataQuality.DUPLICATE


def test_provider_adapter_boundary_is_protocol_only() -> None:
    assert isinstance(ProviderNeutralAdapter, type)
    assert "adapt" in ProviderNeutralAdapter.__annotations__ or hasattr(ProviderNeutralAdapter, "adapt")


def test_source_and_timestamp_metadata_are_preserved() -> None:
    result = normalize(event(source_event_id="source-event", sequence="cursor-7"))
    assert result.state is not None
    assert result.state.source_id == "fixture-source"
    assert result.state.source_event_id == "source-event"
    assert result.state.event_time == EVENT_TIME
    assert result.state.received_time == RECEIVED_TIME
    assert result.state.processing_time == PROCESSING_TIME
    assert result.state.sequence == "cursor-7"


def test_identity_is_stable_for_equivalent_event_content() -> None:
    left = event(source_event_id=None, payload={"b": [2, 1], "a": 1})
    right = event(source_event_id=None, payload={"a": 1, "b": [2, 1]})
    assert canonical_identity(left) == canonical_identity(right)