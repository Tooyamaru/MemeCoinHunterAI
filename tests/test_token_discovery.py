from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from core.data.adapters import (
    AdapterCapabilities,
    AdapterCapability,
    AdapterIdentity,
    DeterministicFakeAdapter,
)
from core.data.contracts import DataQuality, FreshnessPolicy, RawEvent
from core.data.discovery import (
    DiscoveryContext,
    DiscoveryKind,
    DiscoveryObservation,
    DiscoveryOrdering,
    DiscoveryOutcome,
    InMemoryDiscoveryPublisher,
    TokenDiscoveryBoundary,
)
from core.data.orchestration import AdapterObservation, CursorContinuity, ObservationKind


UTC = timezone.utc
SOURCE_TIME = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
DISCOVERY_TIME = SOURCE_TIME + timedelta(seconds=1)
PROCESSING_TIME = DISCOVERY_TIME + timedelta(seconds=1)
REFERENCE_TIME = SOURCE_TIME + timedelta(seconds=10)
POLICY = FreshnessPolicy(stale_after=timedelta(minutes=1))


def discovery(
    *,
    source_id: str = "fixture-source",
    token: str = "mint-A",
    source_event_id: str | None = "event-1",
    sequence: int | str | None = 1,
    kind: DiscoveryKind = DiscoveryKind.DISCOVERED,
    chain_id: str = "solana",
    discovery_time: datetime = DISCOVERY_TIME,
    continuity: CursorContinuity = CursorContinuity.NOT_PROVIDED,
    metadata: Any = {"symbol": "MINT"},
) -> DiscoveryObservation:
    return DiscoveryObservation(
        source_id=source_id,
        kind=kind,
        token_identity=token,
        chain_id=chain_id,
        observation_time=DISCOVERY_TIME,
        discovery_time=discovery_time,
        source_event_id=source_event_id,
        sequence=sequence,
        cursor_continuity=continuity,
        discovery_reason="NEW_SOURCE_OBSERVATION",
        metadata=metadata,
        source_metadata={"fixture": "local"},
    )


def boundary(*, publisher=None, stale_after: timedelta | None = timedelta(minutes=1)):
    return TokenDiscoveryBoundary(
        context=DiscoveryContext(
            freshness_policy=FreshnessPolicy(stale_after=stale_after),
            contract_version="p02-t04-test",
        ),
        publisher=publisher,
    )


def process(runner: TokenDiscoveryBoundary, item, **kwargs):
    return runner.process(
        item,
        processing_time=kwargs.get("processing_time", PROCESSING_TIME),
        reference_time=kwargs.get("reference_time", REFERENCE_TIME),
    )


def test_valid_token_discovery_is_accepted_with_provenance() -> None:
    result = process(boundary(), discovery())

    assert result.outcome is DiscoveryOutcome.ACCEPTED
    assert result.quality_status is DataQuality.VALID
    assert result.accepted is True
    assert result.published_as_current is True
    assert result.record is not None
    assert result.record.token_identity == "mint-A"
    assert result.record.provenance.source_id == "fixture-source"
    assert result.record.provenance.source_event_id == "event-1"
    assert result.record.provenance.sequence == 1
    assert result.record.contract_version == "p02-t04-test"


@pytest.mark.parametrize(
    "item, expected_reason",
    [
        (discovery(token=""), "token_identity is required"),
        (object(), "observation must be"),
    ],
)
def test_malformed_discovery_is_invalid(item, expected_reason: str) -> None:
    result = process(boundary(), item)

    assert result.outcome is DiscoveryOutcome.INVALID
    assert result.quality_status is DataQuality.INVALID
    assert expected_reason in " ".join(result.reasons)
    assert result.published_as_current is False


def test_duplicate_discovery_is_observable_and_not_current() -> None:
    runner = boundary()
    assert process(runner, discovery()).outcome is DiscoveryOutcome.ACCEPTED

    result = process(runner, discovery())

    assert result.outcome is DiscoveryOutcome.DUPLICATE
    assert result.quality_status is DataQuality.DUPLICATE
    assert result.accepted is False
    assert result.published_as_current is False
    assert result.record is not None
    assert result.record.provenance.source_event_id == "event-1"


def test_contradictory_identity_is_not_silently_overwritten() -> None:
    runner = boundary()
    process(runner, discovery(token="mint-A"))

    result = process(runner, discovery(token="mint-B"))

    assert result.outcome is DiscoveryOutcome.CONTRADICTORY
    assert result.quality_status is DataQuality.CONTRADICTORY
    assert result.record is not None
    assert result.record.token_identity == "mint-B"


def test_stale_discovery_is_explicitly_rejected() -> None:
    result = process(
        boundary(stale_after=timedelta(seconds=2)),
        discovery(discovery_time=SOURCE_TIME - timedelta(minutes=2)),
    )

    assert result.outcome is DiscoveryOutcome.STALE
    assert result.quality_status is DataQuality.STALE
    assert result.record is not None
    assert result.record.data_age == timedelta(minutes=2, seconds=10)


def test_out_of_order_discovery_does_not_advance_sequence() -> None:
    runner = boundary()
    process(runner, discovery(sequence=3, source_event_id="event-3"))

    result = process(runner, discovery(sequence=2, source_event_id="event-2"))

    assert result.outcome is DiscoveryOutcome.OUT_OF_ORDER
    assert result.quality_status is DataQuality.OUT_OF_ORDER
    assert runner.context.last_sequence_by_source["fixture-source"] == 3


def test_missing_cursor_has_unknown_ordering() -> None:
    result = process(boundary(), discovery(sequence=None))

    assert result.outcome is DiscoveryOutcome.ACCEPTED
    assert result.record is not None
    assert result.record.ordering is DiscoveryOrdering.UNKNOWN
    assert result.sequence is None


def test_cursor_discontinuity_requires_explicit_resynchronization() -> None:
    runner = boundary()
    result = process(
        runner,
        discovery(
            continuity=CursorContinuity.DISCONTINUOUS,
            source_event_id="event-gap",
        ),
    )

    assert result.outcome is DiscoveryOutcome.RESYNC_REQUIRED
    assert result.resynchronization_required is True

    blocked = process(runner, discovery(source_event_id="event-blocked", sequence=2))
    assert blocked.outcome is DiscoveryOutcome.RESYNC_REQUIRED

    resynced = process(
        runner,
        discovery(
            kind=DiscoveryKind.RESYNC,
            source_event_id="event-resync",
            sequence=1,
            continuity=CursorContinuity.CONTINUOUS,
        ),
    )
    assert resynced.outcome is DiscoveryOutcome.ACCEPTED
    assert resynced.resynchronization_required is False


def test_unavailable_adapter_observation_is_not_valid_discovery() -> None:
    result = process(
        boundary(),
        AdapterObservation(
            source_id="fixture-source",
            kind=ObservationKind.FAILURE,
            observed_time=DISCOVERY_TIME,
            failure_reason="fixture unavailable",
        ),
    )

    assert result.outcome is DiscoveryOutcome.UNAVAILABLE
    assert result.quality_status is DataQuality.SOURCE_UNAVAILABLE
    assert result.published_as_current is False


def test_p02_t03_adapter_output_feeds_discovery_boundary() -> None:
    raw_event = RawEvent(
        source_id="fixture-source",
        source_event_id="event-adapter",
        payload={
            "token_identity": "mint-adapter",
            "chain_id": "solana",
            "discovery_reason": "ADAPTER_FIXTURE",
            "metadata": {"symbol": "ADP"},
        },
        event_time=SOURCE_TIME,
        received_time=DISCOVERY_TIME,
        sequence=4,
        source_metadata={"fixture": "adapter"},
    )
    adapter = DeterministicFakeAdapter(
        identity=AdapterIdentity(
            adapter_id="adapter-v1",
            source_id="fixture-source",
            contract_version="p02-t03-test",
        ),
        capabilities=AdapterCapabilities(frozenset({AdapterCapability.BATCH})),
        observations=(
            AdapterObservation(
                source_id="fixture-source",
                kind=ObservationKind.EVENT,
                observed_time=DISCOVERY_TIME,
                raw_event=raw_event,
                cursor=4,
            ),
        ),
    )
    adapter.start(observed_time=DISCOVERY_TIME)

    result = process(boundary(), adapter.observe()[0])

    assert result.outcome is DiscoveryOutcome.ACCEPTED
    assert result.record is not None
    assert result.record.token_identity == "mint-adapter"


def test_provider_specific_object_cannot_cross_discovery_boundary() -> None:
    result = process(
        boundary(),
        discovery(metadata={"provider_object": object()}),
    )

    assert result.outcome is DiscoveryOutcome.INVALID
    assert result.published_as_current is False


def test_invalid_result_remains_observable_without_valid_publication() -> None:
    publisher = InMemoryDiscoveryPublisher()
    result = process(
        boundary(publisher=publisher),
        discovery(token=""),
    )

    assert result.outcome is DiscoveryOutcome.INVALID
    assert publisher.results == [result]
    assert all(not item.published_as_current for item in publisher.results)


def test_source_isolation_is_preserved() -> None:
    runner = boundary()
    process(runner, discovery(source_id="source-A", source_event_id="a-1", sequence=3))
    other = process(
        runner,
        discovery(source_id="source-B", source_event_id="b-1", sequence=1),
    )

    assert other.outcome is DiscoveryOutcome.ACCEPTED
    assert runner.context.last_sequence_by_source == {"source-A": 3, "source-B": 1}


def test_equivalent_sequences_replay_identically() -> None:
    sequence = (
        discovery(source_event_id="event-1", sequence=1),
        discovery(source_event_id="event-2", sequence=2, token="mint-B"),
        discovery(source_event_id="event-2", sequence=2, token="mint-B"),
    )
    left = boundary()
    right = boundary()

    assert [process(left, item) for item in sequence] == [
        process(right, item) for item in sequence
    ]


def test_explicit_reference_time_controls_freshness_deterministically() -> None:
    runner = boundary(stale_after=timedelta(seconds=5))
    fresh = process(
        runner,
        discovery(source_event_id="fresh", sequence=1),
        reference_time=DISCOVERY_TIME + timedelta(seconds=4),
    )
    stale = process(
        boundary(stale_after=timedelta(seconds=5)),
        discovery(source_event_id="stale", sequence=1),
        reference_time=DISCOVERY_TIME + timedelta(seconds=6),
    )

    assert fresh.outcome is DiscoveryOutcome.ACCEPTED
    assert stale.outcome is DiscoveryOutcome.STALE