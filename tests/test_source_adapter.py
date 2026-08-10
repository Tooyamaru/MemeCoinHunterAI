from datetime import datetime, timedelta, timezone

import pytest

from core.data.adapters import (
    AdapterCapabilities,
    AdapterCapability,
    AdapterHealthStatus,
    AdapterIdentity,
    AdapterLifecycleState,
    DeterministicFakeAdapter,
    ProviderNeutralSourceAdapter,
    UnsupportedCapabilityError,
)
from core.data.contracts import DataQuality, FreshnessPolicy, RawEvent, SourceHealthStatus
from core.data.orchestration import (
    AdapterObservation,
    IngestionContext,
    IngestionOrchestrator,
    IngestionOutcome,
    ObservationKind,
)


UTC = timezone.utc
EVENT_TIME = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
RECEIVED_TIME = EVENT_TIME + timedelta(seconds=1)
PROCESSING_TIME = RECEIVED_TIME + timedelta(seconds=1)
REFERENCE_TIME = EVENT_TIME + timedelta(seconds=10)


def raw(*, source_id: str = "fixture-source", sequence: int = 1) -> RawEvent:
    return RawEvent(
        source_id=source_id,
        source_event_id=f"evt-{sequence}",
        payload={"price": sequence},
        event_time=EVENT_TIME,
        received_time=RECEIVED_TIME,
        sequence=sequence,
        source_metadata={"fixture": "adapter"},
    )


def adapter(
    observations: tuple[AdapterObservation, ...] = (),
) -> DeterministicFakeAdapter:
    return DeterministicFakeAdapter(
        identity=AdapterIdentity(
            adapter_id="fake-adapter-v1",
            source_id="fixture-source",
            contract_version="p02-t03-test",
        ),
        capabilities=AdapterCapabilities(
            frozenset(
                {
                    AdapterCapability.BATCH,
                    AdapterCapability.CURSOR,
                    AdapterCapability.ORDERING,
                }
            )
        ),
        observations=observations,
    )


def valid_observation(sequence: int = 1) -> AdapterObservation:
    return AdapterObservation(
        source_id="fixture-source",
        kind=ObservationKind.EVENT,
        observed_time=RECEIVED_TIME,
        raw_event=raw(sequence=sequence),
        cursor=sequence,
    )


def test_valid_adapter_satisfies_provider_neutral_contract() -> None:
    source = adapter((valid_observation(),))

    assert isinstance(source, ProviderNeutralSourceAdapter)
    assert source.identity.adapter_id == "fake-adapter-v1"
    assert source.identity.source_id == "fixture-source"
    assert source.lifecycle_state is AdapterLifecycleState.CREATED
    assert source.health.status is AdapterHealthStatus.UNKNOWN


def test_capabilities_are_explicit_and_unsupported_capability_is_observable() -> None:
    source = adapter()

    assert source.capabilities.supports(AdapterCapability.CURSOR)
    assert not source.capabilities.supports(AdapterCapability.STREAM)
    with pytest.raises(UnsupportedCapabilityError):
        source.capabilities.require(AdapterCapability.STREAM)


def test_lifecycle_transitions_do_not_claim_source_availability() -> None:
    source = adapter()

    started = source.start(observed_time=RECEIVED_TIME)
    assert started.state is AdapterLifecycleState.STARTED
    assert started.health.status is AdapterHealthStatus.UNKNOWN
    assert source.health.status is AdapterHealthStatus.UNKNOWN

    stopped = source.stop(observed_time=PROCESSING_TIME)
    assert stopped.state is AdapterLifecycleState.STOPPED


def test_adapter_emits_valid_p02_t02_observation_with_cursor() -> None:
    source = adapter((valid_observation(),))
    source.start(observed_time=RECEIVED_TIME)

    observations = source.observe()

    assert observations[0].kind is ObservationKind.EVENT
    assert observations[0].cursor == 1
    assert observations[0].raw_event is not None


def test_adapter_failure_is_explicit_and_does_not_become_valid_data() -> None:
    source = adapter()
    failure = source.failure_observation(
        observed_time=PROCESSING_TIME,
        reason="fixture unavailable",
        cursor=7,
    )

    assert failure.kind is ObservationKind.FAILURE
    assert failure.failure_reason == "fixture unavailable"
    assert failure.cursor == 7
    assert failure.raw_event is None


def test_provider_specific_object_cannot_cross_boundary() -> None:
    with pytest.raises(TypeError, match="provider-specific"):
        adapter((object(),))  # type: ignore[arg-type]


def test_observation_source_must_match_adapter_identity() -> None:
    with pytest.raises(ValueError, match="source_id"):
        adapter(
            (
                AdapterObservation(
                    source_id="other-source",
                    kind=ObservationKind.EVENT,
                    observed_time=RECEIVED_TIME,
                    raw_event=raw(source_id="other-source"),
                ),
            )
        )


def test_failed_adapter_health_is_explicit_and_separately_tracked() -> None:
    source = adapter()

    health = source.mark_health(
        status=AdapterHealthStatus.FAILED,
        observed_time=PROCESSING_TIME,
        reason="fixture failure",
    )

    assert health.status is AdapterHealthStatus.FAILED
    assert source.lifecycle_state is AdapterLifecycleState.FAILED
    assert source.health.status is AdapterHealthStatus.FAILED


def test_fake_adapter_is_deterministic() -> None:
    left = adapter((valid_observation(),))
    right = adapter((valid_observation(),))
    left.start(observed_time=RECEIVED_TIME)
    right.start(observed_time=RECEIVED_TIME)

    assert left.observe() == right.observe()


def test_adapter_output_is_consumed_by_p02_t02_orchestration() -> None:
    source = adapter((valid_observation(),))
    source.start(observed_time=RECEIVED_TIME)
    runner = IngestionOrchestrator(
        context=IngestionContext(
            freshness_policy=FreshnessPolicy(stale_after=timedelta(minutes=1)),
            contract_version="p02-t03-test",
        )
    )

    result = runner.process(
        source.observe()[0],
        processing_time=PROCESSING_TIME,
        reference_time=REFERENCE_TIME,
    )

    assert result.outcome is IngestionOutcome.ACCEPTED
    assert result.quality_status is DataQuality.VALID
    assert result.source_health is not None
    assert result.source_health.status is SourceHealthStatus.AVAILABLE


def test_adapter_failure_observation_reaches_p02_t02_source_health() -> None:
    source = adapter()
    runner = IngestionOrchestrator(
        context=IngestionContext(
            freshness_policy=FreshnessPolicy(stale_after=timedelta(minutes=1)),
            contract_version="p02-t03-test",
        )
    )

    result = runner.process(
        source.failure_observation(
            observed_time=PROCESSING_TIME,
            reason="fixture timeout",
        ),
        processing_time=PROCESSING_TIME,
        reference_time=REFERENCE_TIME,
    )

    assert result.outcome is IngestionOutcome.SOURCE_FAILURE
    assert result.source_health is not None
    assert result.source_health.status is SourceHealthStatus.FAILED