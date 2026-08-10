from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from core.data.contracts import DataQuality, FreshnessPolicy, RawEvent, SourceHealthStatus
from core.data.orchestration import (
    AdapterObservation,
    CursorContinuity,
    IngestionContext,
    IngestionOrchestrator,
    IngestionOutcome,
    ObservationKind,
)


UTC = timezone.utc
EVENT_TIME = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
RECEIVED_TIME = EVENT_TIME + timedelta(seconds=1)
OBSERVED_TIME = RECEIVED_TIME
PROCESSING_TIME = RECEIVED_TIME + timedelta(seconds=1)
REFERENCE_TIME = EVENT_TIME + timedelta(seconds=10)
POLICY = FreshnessPolicy(stale_after=timedelta(minutes=1))


class Recorder:
    def __init__(self) -> None:
        self.results = []

    def publish(self, result) -> None:
        self.results.append(result)


def raw(
    *,
    source_id: str = "fixture-source",
    source_event_id: str | None = "evt-1",
    payload: Any = {"price": 1},
    sequence: int | str | None = 1,
    event_time: Any = EVENT_TIME,
) -> RawEvent:
    return RawEvent(
        source_id=source_id,
        source_event_id=source_event_id,
        payload=payload,
        sequence=sequence,
        event_time=event_time,
        received_time=RECEIVED_TIME,
        source_metadata={"fixture": "local"},
    )


def observation(
    *,
    kind: ObservationKind = ObservationKind.EVENT,
    event: RawEvent | None = None,
    source_id: str = "fixture-source",
    cursor: int | str | None = None,
    continuity: CursorContinuity = CursorContinuity.NOT_PROVIDED,
    reason: str | None = None,
) -> AdapterObservation:
    if event is None and kind in {ObservationKind.FAILURE, ObservationKind.RESYNC_REQUIRED}:
        raw_event = None
    else:
        raw_event = event if event is not None else raw(source_id=source_id)
    return AdapterObservation(
        source_id=source_id,
        kind=kind,
        observed_time=OBSERVED_TIME,
        raw_event=raw_event,
        cursor=cursor,
        cursor_continuity=continuity,
        failure_reason=reason,
        source_metadata={"fixture": "local"},
    )


def orchestrator(*, publisher=None) -> IngestionOrchestrator:
    return IngestionOrchestrator(
        context=IngestionContext(freshness_policy=POLICY, contract_version="p02-t02-test"),
        publisher=publisher,
    )


def process(
    runner: IngestionOrchestrator,
    item: AdapterObservation,
    *,
    processing_time: datetime = PROCESSING_TIME,
    reference_time: datetime = REFERENCE_TIME,
):
    return runner.process(item, processing_time=processing_time, reference_time=reference_time)


def test_valid_observation_is_accepted_and_published_with_provenance() -> None:
    recorder = Recorder()
    result = process(orchestrator(publisher=recorder), observation())

    assert result.outcome is IngestionOutcome.ACCEPTED
    assert result.quality_status is DataQuality.VALID
    assert result.accepted is True
    assert result.published_as_current is True
    assert result.state is not None
    assert result.state.source_id == "fixture-source"
    assert result.contract_version == "p02-t02-test"
    assert recorder.results == [result]


def test_malformed_observation_is_rejected_without_side_effect() -> None:
    runner = orchestrator()
    malformed = AdapterObservation(
        source_id="fixture-source",
        kind=ObservationKind.EVENT,
        observed_time=OBSERVED_TIME,
        raw_event=None,
    )

    result = process(runner, malformed)

    assert result.outcome is IngestionOutcome.OBSERVATION_REJECTED
    assert result.accepted is False
    assert runner.context.source_health.get("fixture-source").status is SourceHealthStatus.UNKNOWN


def test_p02_t01_quality_is_propagated() -> None:
    result = process(orchestrator(), observation(event=raw(event_time=EVENT_TIME - timedelta(minutes=2))))

    assert result.outcome is IngestionOutcome.QUALITY_REJECTED
    assert result.quality_status is DataQuality.STALE
    assert result.state is not None
    assert result.state.data_age == timedelta(minutes=2, seconds=10)


def test_duplicate_is_observable_and_not_current() -> None:
    runner = orchestrator()
    assert process(runner, observation()).accepted is True

    result = process(runner, observation())

    assert result.quality_status is DataQuality.DUPLICATE
    assert result.outcome is IngestionOutcome.QUALITY_REJECTED
    assert result.published_as_current is False


def test_out_of_order_is_observable_and_does_not_advance_ordering() -> None:
    runner = orchestrator()
    process(runner, observation(event=raw(source_event_id="evt-3", sequence=3)))

    result = process(runner, observation(event=raw(source_event_id="evt-2", sequence=2)))

    assert result.quality_status is DataQuality.OUT_OF_ORDER
    assert runner.context.normalization.last_sequence_by_source["fixture-source"] == 3


def test_contradiction_is_not_silently_accepted() -> None:
    runner = orchestrator()
    process(runner, observation())

    result = process(runner, observation(event=raw(payload={"price": 2})))

    assert result.quality_status is DataQuality.CONTRADICTORY
    assert result.accepted is False


def test_failure_is_not_valid_market_data() -> None:
    runner = orchestrator()
    result = process(
        runner,
        observation(
            kind=ObservationKind.FAILURE,
            event=None,
            reason="fixture timeout",
        ),
    )

    assert result.outcome is IngestionOutcome.SOURCE_FAILURE
    assert result.quality_status is DataQuality.SOURCE_UNAVAILABLE
    assert result.published_as_current is False
    assert result.source_health is not None
    assert result.source_health.status is SourceHealthStatus.FAILED


def test_failed_source_does_not_recover_on_restart_or_rejected_observation() -> None:
    runner = orchestrator()
    process(runner, observation(kind=ObservationKind.FAILURE, event=None, reason="timeout"))

    rejected = process(runner, observation(event=raw(payload={"bad": object()})))

    assert rejected.quality_status is DataQuality.SOURCE_UNAVAILABLE
    assert rejected.recovered is False
    assert runner.context.source_health.get("fixture-source").status is SourceHealthStatus.FAILED


def test_failed_source_recovers_only_after_accepted_observation() -> None:
    runner = orchestrator()
    process(runner, observation(kind=ObservationKind.FAILURE, event=None, reason="timeout"))

    result = process(runner, observation(event=raw(source_event_id="evt-recovered", sequence=2)))

    assert result.outcome is IngestionOutcome.SOURCE_RECOVERY
    assert result.recovered is True
    assert result.accepted is True
    assert result.source_health is not None
    assert result.source_health.status is SourceHealthStatus.AVAILABLE


def test_source_failure_is_isolated() -> None:
    runner = orchestrator()
    process(runner, observation(kind=ObservationKind.FAILURE, event=None, reason="timeout"))

    other = process(runner, observation(source_id="other-source", event=raw(source_id="other-source")))

    assert other.outcome is IngestionOutcome.ACCEPTED
    assert runner.context.source_health.get("fixture-source").status is SourceHealthStatus.FAILED
    assert runner.context.source_health.get("other-source").status is SourceHealthStatus.AVAILABLE


def test_missing_cursor_does_not_claim_ordering() -> None:
    runner = orchestrator()
    result = process(runner, observation(event=raw(sequence=None)))

    assert result.accepted is True
    assert result.state is not None
    assert result.state.ordering_status.value == "NOT_PROVIDED"
    assert result.cursor is None


def test_cursor_discontinuity_requires_explicit_resynchronization() -> None:
    runner = orchestrator()
    discontinuous = process(
        runner,
        observation(
            event=raw(),
            cursor=1,
            continuity=CursorContinuity.DISCONTINUOUS,
        ),
    )

    assert discontinuous.outcome is IngestionOutcome.OBSERVATION_REJECTED
    assert "resynchronization" in " ".join(discontinuous.reasons)

    requested = process(
        runner,
        AdapterObservation(
            source_id="fixture-source",
            kind=ObservationKind.RESYNC_REQUIRED,
            observed_time=OBSERVED_TIME,
            cursor=1,
            cursor_continuity=CursorContinuity.DISCONTINUOUS,
        ),
    )
    assert requested.outcome is IngestionOutcome.RESYNCHRONIZATION_REQUIRED

    resynced = process(
        runner,
        observation(
            kind=ObservationKind.RESYNC,
            event=raw(source_event_id="evt-resync", sequence=1),
            cursor=1,
            continuity=CursorContinuity.CONTINUOUS,
        ),
    )
    assert resynced.outcome is IngestionOutcome.ACCEPTED
    assert resynced.resynchronization_required is False


def test_replay_with_equivalent_context_is_deterministic() -> None:
    sequence = [
        observation(event=raw(source_event_id="evt-1", sequence=1)),
        observation(event=raw(source_event_id="evt-2", sequence=2)),
        observation(event=raw(source_event_id="evt-2", sequence=2)),
    ]
    left = orchestrator()
    right = orchestrator()

    left_results = [process(left, item) for item in sequence]
    right_results = [process(right, item) for item in sequence]

    assert left_results == right_results


def test_processing_and_reference_times_are_explicit() -> None:
    runner = orchestrator()
    with pytest.raises(TypeError):
        runner.process(observation())  # type: ignore[call-arg]

    result = process(runner, observation(), processing_time=PROCESSING_TIME.replace(tzinfo=None))
    assert result.outcome is IngestionOutcome.OBSERVATION_REJECTED


def test_provider_specific_object_is_rejected_at_boundary() -> None:
    runner = orchestrator()
    result = process(
        runner,
        observation(event=raw(payload={"provider_object": object()})),
    )

    assert result.outcome is IngestionOutcome.QUALITY_REJECTED
    assert result.quality_status is DataQuality.INVALID


def test_recovery_observation_without_accepted_event_cannot_recover() -> None:
    runner = orchestrator()
    process(runner, observation(kind=ObservationKind.FAILURE, event=None, reason="timeout"))
    recovery_only = AdapterObservation(
        source_id="fixture-source",
        kind=ObservationKind.RECOVERY,
        observed_time=OBSERVED_TIME,
        raw_event=None,
    )

    result = process(runner, recovery_only)

    assert result.outcome is IngestionOutcome.OBSERVATION_REJECTED
    assert runner.context.source_health.get("fixture-source").status is SourceHealthStatus.FAILED