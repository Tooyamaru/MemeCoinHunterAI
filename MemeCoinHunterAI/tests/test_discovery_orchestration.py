from datetime import datetime, timedelta, timezone
from copy import deepcopy

import pytest

from core.data.contracts import DataQuality, FreshnessPolicy
from core.data.discovery import (
    DiscoveryContext,
    DiscoveryKind,
    DiscoveryObservation,
    DiscoveryOrdering,
    DiscoveryOutcome,
    TokenDiscoveryBoundary,
)
from core.data.discovery_orchestration import (
    DiscoveryOrchestrationOutcome,
    DiscoveryToOrchestrationBoundary,
)
from core.data.orchestration import (
    IngestionContext,
    IngestionOrchestrator,
    IngestionOutcome,
    ObservationKind,
)


UTC = timezone.utc
EVENT_TIME = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
RECEIVED_TIME = EVENT_TIME + timedelta(seconds=1)
OBSERVED_TIME = RECEIVED_TIME
DISCOVERY_PROCESSING_TIME = RECEIVED_TIME + timedelta(seconds=1)
DISCOVERY_REFERENCE_TIME = EVENT_TIME + timedelta(seconds=10)
DOWNSTREAM_PROCESSING_TIME = DISCOVERY_PROCESSING_TIME + timedelta(seconds=1)
DOWNSTREAM_REFERENCE_TIME = DISCOVERY_REFERENCE_TIME


def discovery_observation(
    *,
    source_id: str = "fixture-source",
    source_event_id: str | None = "discovery-event-1",
    token_identity: str = "mint-A",
    sequence: int | str | None = 1,
    kind: DiscoveryKind = DiscoveryKind.DISCOVERED,
    discovery_time: datetime = EVENT_TIME,
    received_time: datetime = RECEIVED_TIME,
    metadata: dict = {"symbol": "MINT"},
) -> DiscoveryObservation:
    return DiscoveryObservation(
        source_id=source_id,
        kind=kind,
        token_identity=token_identity,
        chain_id="solana",
        observation_time=OBSERVED_TIME,
        discovery_time=discovery_time,
        received_time=received_time,
        source_event_id=source_event_id,
        sequence=sequence,
        discovery_reason="P02_T05_FIXTURE",
        metadata=metadata,
        source_metadata={
            "raw_event": {"raw_layer": "raw"},
            "adapter": {"adapter_layer": "adapter"},
        },
    )


def discovery_boundary() -> TokenDiscoveryBoundary:
    return TokenDiscoveryBoundary(
        context=DiscoveryContext(
            freshness_policy=FreshnessPolicy(stale_after=timedelta(minutes=1)),
            contract_version="p02-t04-test",
        )
    )


def discovery_result(
    runner: TokenDiscoveryBoundary | None = None,
    item: DiscoveryObservation | object | None = None,
):
    runner = runner or discovery_boundary()
    item = item or discovery_observation()
    return runner.process(
        item,
        processing_time=DISCOVERY_PROCESSING_TIME,
        reference_time=DISCOVERY_REFERENCE_TIME,
    )


def boundary(*, recorder=None) -> DiscoveryToOrchestrationBoundary:
    return DiscoveryToOrchestrationBoundary(
        orchestrator=IngestionOrchestrator(
            context=IngestionContext(
                freshness_policy=FreshnessPolicy(stale_after=timedelta(minutes=1)),
                contract_version="p02-t02-test",
            ),
            publisher=recorder,
        )
    )


class Recorder:
    def __init__(self) -> None:
        self.results = []

    def publish(self, result) -> None:
        self.results.append(result)


def process(runner, result):
    return runner.process(
        result,
        processing_time=DOWNSTREAM_PROCESSING_TIME,
        reference_time=DOWNSTREAM_REFERENCE_TIME,
    )


def test_valid_discovery_is_converted_and_forwarded_to_existing_orchestration() -> None:
    result = process(boundary(), discovery_result())

    assert result.conversion.outcome is DiscoveryOrchestrationOutcome.FORWARDED
    assert result.conversion.observation is not None
    assert result.conversion.observation.kind is ObservationKind.EVENT
    assert result.ingestion_result is not None
    assert result.ingestion_result.outcome is IngestionOutcome.ACCEPTED
    assert result.ingestion_result.published_as_current is True


def test_provenance_source_and_all_point_in_time_timestamps_are_preserved() -> None:
    source = discovery_result()
    converted = boundary().convert(source)

    assert converted.observation is not None
    observation = converted.observation
    assert observation.source_id == source.source_id
    assert observation.observed_time == OBSERVED_TIME
    assert observation.correlation_id == source.discovery_id
    assert observation.raw_event is not None
    assert observation.raw_event.source_id == source.record.provenance.source_id
    assert observation.raw_event.source_event_id == "discovery-event-1"
    assert observation.raw_event.event_time == EVENT_TIME
    assert observation.raw_event.received_time == RECEIVED_TIME
    assert observation.raw_event.sequence == 1
    assert observation.raw_event.source_metadata == source.record.provenance.source_metadata


def test_discovery_classification_outcome_and_ordering_are_preserved() -> None:
    source = discovery_result(
        item=discovery_observation(
            kind=DiscoveryKind.METADATA_UPDATED,
            source_event_id="metadata-event",
        )
    )
    converted = boundary().convert(source)

    assert converted.observation is not None
    payload = converted.observation.raw_event.payload
    assert payload["discovery_kind"] == DiscoveryKind.METADATA_UPDATED.value
    assert payload["discovery_outcome"] == DiscoveryOutcome.ACCEPTED.value
    assert payload["ordering"] == DiscoveryOrdering.FIRST.value
    assert payload["token_identity"] == "mint-A"
    assert converted.observation.source_metadata["discovery_id"] == source.discovery_id


@pytest.mark.parametrize(
    "source",
    [
        object(),
        discovery_result(item=discovery_observation(token_identity="")),
    ],
)
def test_invalid_discovery_is_rejected_without_forwarding(source) -> None:
    runner = boundary()
    before = deepcopy(runner.orchestrator.context)

    result = process(runner, source)

    assert result.conversion.outcome is DiscoveryOrchestrationOutcome.REJECTED
    assert result.conversion.forwarded is False
    assert result.ingestion_result is None
    assert result.published_as_current is False
    assert runner.orchestrator.context == before


def test_malformed_provenance_is_rejected_without_mutation() -> None:
    source = discovery_result()
    assert source.record is not None
    malformed = source.record.provenance
    object.__setattr__(malformed, "received_time", EVENT_TIME - timedelta(seconds=1))

    runner = boundary()
    result = process(runner, source)

    assert result.conversion.outcome is DiscoveryOrchestrationOutcome.REJECTED
    assert "received_time" in " ".join(result.reasons)
    assert result.ingestion_result is None


def test_invalid_ordering_is_rejected_without_forwarding() -> None:
    source = discovery_result()
    assert source.record is not None
    object.__setattr__(source.record, "ordering", DiscoveryOrdering.OUT_OF_ORDER)

    converted = boundary().convert(source)

    assert converted.outcome is DiscoveryOrchestrationOutcome.REJECTED
    assert "OUT_OF_ORDER" in " ".join(converted.reasons)


def test_non_accepted_resync_cannot_mutate_downstream_ordering_state() -> None:
    discovery_runner = discovery_boundary()
    accepted = discovery_result(
        discovery_runner,
        discovery_observation(sequence=7, source_event_id="event-7"),
    )
    discovery_runner.process(
        discovery_observation(
            kind=DiscoveryKind.RESYNC,
            source_event_id="resync-stale",
            sequence=2,
            discovery_time=EVENT_TIME - timedelta(minutes=2),
            received_time=EVENT_TIME - timedelta(minutes=1, seconds=59),
        ),
        processing_time=DISCOVERY_PROCESSING_TIME,
        reference_time=DISCOVERY_REFERENCE_TIME,
    )
    rejected = discovery_runner.process(
        discovery_observation(
            kind=DiscoveryKind.RESYNC,
            source_event_id="resync-rejected",
            sequence=2,
            discovery_time=EVENT_TIME - timedelta(minutes=2),
            received_time=EVENT_TIME - timedelta(minutes=1, seconds=59),
        ),
        processing_time=DISCOVERY_PROCESSING_TIME,
        reference_time=DISCOVERY_REFERENCE_TIME,
    )

    assert accepted.outcome is DiscoveryOutcome.ACCEPTED
    assert rejected.outcome is DiscoveryOutcome.STALE
    downstream = boundary()
    accepted_downstream = process(downstream, accepted)
    assert accepted_downstream.ingestion_result is not None
    assert accepted_downstream.ingestion_result.accepted is True
    before = deepcopy(downstream.orchestrator.context)
    converted = downstream.convert(rejected)

    assert converted.forwarded is False
    assert downstream.orchestrator.context == before


def test_accepted_resync_uses_existing_resync_semantics() -> None:
    discovery_runner = discovery_boundary()
    first = discovery_result(
        discovery_runner,
        discovery_observation(sequence=7, source_event_id="event-7"),
    )
    resync = discovery_result(
        discovery_runner,
        discovery_observation(
            kind=DiscoveryKind.RESYNC,
            source_event_id="event-resync",
            sequence=2,
        ),
    )
    downstream = boundary()

    assert process(downstream, first).ingestion_result.accepted is True
    result = process(downstream, resync)

    assert result.conversion.observation.kind is ObservationKind.RESYNC
    assert result.ingestion_result is not None
    assert result.ingestion_result.outcome is IngestionOutcome.ACCEPTED
    assert downstream.orchestrator.context.normalization.last_sequence_by_source[
        "fixture-source"
    ] == 2


@pytest.mark.parametrize("outcome", list(DiscoveryOutcome)[1:])
def test_unknown_or_invalid_discovery_outcomes_are_never_promoted(outcome) -> None:
    source = discovery_result()
    object.__setattr__(source, "outcome", outcome)
    object.__setattr__(source, "accepted", False)
    object.__setattr__(source, "published_as_current", False)

    result = process(boundary(), source)

    assert result.conversion.forwarded is False
    assert result.ingestion_result is None
    assert result.published_as_current is False


def test_conversion_is_deterministic_for_equivalent_input() -> None:
    left = boundary().convert(discovery_result())
    right = boundary().convert(discovery_result())

    assert left == right


def test_duplicate_and_contradictory_discovery_remain_rejected() -> None:
    runner = discovery_boundary()
    accepted = discovery_result(runner)
    duplicate = discovery_result(runner)
    contradictory = discovery_result(
        runner,
        discovery_observation(token_identity="mint-B"),
    )
    downstream = boundary()

    assert process(downstream, accepted).ingestion_result.accepted is True
    assert process(downstream, duplicate).conversion.forwarded is False
    assert process(downstream, contradictory).conversion.forwarded is False
    assert duplicate.outcome is DiscoveryOutcome.DUPLICATE
    assert contradictory.outcome is DiscoveryOutcome.CONTRADICTORY


def test_existing_publisher_protocol_receives_only_downstream_result() -> None:
    recorder = Recorder()
    runner = boundary(recorder=recorder)
    accepted = discovery_result()
    rejected = discovery_result(
        item=discovery_observation(token_identity=""),
    )

    forwarded = process(runner, accepted)
    not_forwarded = process(runner, rejected)

    assert forwarded.ingestion_result is not None
    assert recorder.results == [forwarded.ingestion_result]
    assert not_forwarded.published_as_current is False