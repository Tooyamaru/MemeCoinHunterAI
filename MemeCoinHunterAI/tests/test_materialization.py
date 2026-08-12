from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from core.data.contracts import DataQuality, FreshnessPolicy
from core.data.discovery import (
    DiscoveryContext,
    DiscoveryKind,
    DiscoveryObservation,
    DiscoveryOutcome,
    TokenDiscoveryBoundary,
)
from core.data.materialization import (
    MaterializationContext,
    MaterializationOutcome,
    TokenUniverseMaterializer,
)


UTC = timezone.utc
EVENT_TIME = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
RECEIVED_TIME = EVENT_TIME + timedelta(seconds=1)
OBSERVED_TIME = RECEIVED_TIME
PROCESSING_TIME = RECEIVED_TIME + timedelta(seconds=1)
REFERENCE_TIME = EVENT_TIME + timedelta(seconds=10)


def discovery_boundary() -> TokenDiscoveryBoundary:
    return TokenDiscoveryBoundary(
        context=DiscoveryContext(
            freshness_policy=FreshnessPolicy(stale_after=timedelta(minutes=1)),
            contract_version="p02-t04-test",
        )
    )


def discovery(
    runner: TokenDiscoveryBoundary,
    *,
    source_event_id: str = "event-1",
    token_identity: str = "mint-A",
    sequence: int | None = 1,
    kind: DiscoveryKind = DiscoveryKind.DISCOVERED,
    metadata: dict[str, str] | None = None,
    discovery_time: datetime = EVENT_TIME,
    observation_time: datetime = OBSERVED_TIME,
    received_time: datetime = RECEIVED_TIME,
):
    item = DiscoveryObservation(
        source_id="fixture-source",
        kind=kind,
        token_identity=token_identity,
        chain_id="solana",
        observation_time=observation_time,
        discovery_time=discovery_time,
        received_time=received_time,
        source_event_id=source_event_id,
        sequence=sequence,
        discovery_reason="P02_T06_FIXTURE",
        metadata=metadata or {"symbol": "MINT"},
        source_metadata={"fixture": "local"},
    )
    return runner.process(
        item,
        processing_time=PROCESSING_TIME,
        reference_time=REFERENCE_TIME,
    )


def materializer() -> TokenUniverseMaterializer:
    return TokenUniverseMaterializer(
        context=MaterializationContext(
            materializer_contract_version="p02-t06-test",
        )
    )


def process(runner, result, *, processing_time=PROCESSING_TIME, reference_time=REFERENCE_TIME):
    return runner.process(
        result,
        processing_time=processing_time,
        reference_time=reference_time,
    )


def test_discovered_result_creates_current_entry_with_provenance() -> None:
    source = discovery(discovery_boundary())

    result = process(materializer(), source)

    assert result.outcome is MaterializationOutcome.MATERIALIZED
    assert result.current_view_changed is True
    assert result.current_view_present is True
    assert len(result.current_view) == 1
    assert result.entry is not None
    assert result.entry.token_identity == "mint-A"
    assert result.entry.provenance.source_event_id == "event-1"
    assert result.entry.discovery_contract_version == "p02-t04-test"
    assert result.materializer_contract_version == "p02-t06-test"


def test_observation_before_receipt_is_materialized_as_current() -> None:
    source = discovery(
        discovery_boundary(),
        source_event_id="observed-before-received",
        observation_time=EVENT_TIME,
        received_time=RECEIVED_TIME,
    )

    result = process(materializer(), source)

    assert result.outcome is MaterializationOutcome.MATERIALIZED
    assert result.current_view_present is True
    assert result.current_view_changed is True
    assert result.entry is not None
    assert result.entry.provenance.observation_time == EVENT_TIME
    assert result.entry.provenance.received_time == RECEIVED_TIME


def test_discovery_after_receipt_remains_rejected() -> None:
    source = discovery(
        discovery_boundary(),
        source_event_id="discovery-after-received",
        discovery_time=RECEIVED_TIME + timedelta(seconds=1),
        received_time=RECEIVED_TIME,
    )

    result = process(materializer(), source)

    assert result.outcome is MaterializationOutcome.INVALID
    assert result.current_view_changed is False
    assert result.current_view == ()


def test_metadata_update_replaces_only_discovery_derived_entry() -> None:
    discovery_runner = discovery_boundary()
    runner = materializer()
    process(runner, discovery(discovery_runner))

    updated = process(
        runner,
        discovery(
            discovery_runner,
            source_event_id="event-2",
            sequence=2,
            kind=DiscoveryKind.METADATA_UPDATED,
            metadata={"symbol": "UPDATED"},
        ),
    )

    assert updated.outcome is MaterializationOutcome.UPDATED
    assert updated.entry is not None
    assert updated.entry.metadata == {"symbol": "UPDATED"}
    assert updated.entry.discovery_kind is DiscoveryKind.METADATA_UPDATED
    assert updated.entry.provenance.source_event_id == "event-2"
    assert len(updated.current_view) == 1


def test_removed_result_removes_entry_and_remains_observable() -> None:
    discovery_runner = discovery_boundary()
    runner = materializer()
    process(runner, discovery(discovery_runner))

    removed = process(
        runner,
        discovery(
            discovery_runner,
            source_event_id="event-remove",
            sequence=2,
            kind=DiscoveryKind.REMOVED,
        ),
    )

    assert removed.outcome is MaterializationOutcome.REMOVED
    assert removed.entry is None
    assert removed.current_view_changed is True
    assert removed.current_view_present is False
    assert removed.discovery_record is not None
    assert removed.discovery_record.discovery_kind is DiscoveryKind.REMOVED
    assert removed.current_view == ()


def test_duplicate_is_observable_and_does_not_mutate_state() -> None:
    source = discovery(discovery_boundary())
    runner = materializer()
    accepted = process(runner, source)
    before = runner.state.state_version

    duplicate = process(runner, source)

    assert accepted.outcome is MaterializationOutcome.MATERIALIZED
    assert duplicate.outcome is MaterializationOutcome.DUPLICATE
    assert duplicate.current_view_changed is False
    assert duplicate.state_version == before


def test_duplicate_is_detected_against_prepopulated_state() -> None:
    discovery_runner = discovery_boundary()
    source = discovery(discovery_runner)
    seeded = materializer()
    process(seeded, source)

    runner = TokenUniverseMaterializer(
        context=MaterializationContext(
            initial_state=deepcopy(seeded.state),
            materializer_contract_version="p02-t06-test",
        )
    )
    duplicate = process(runner, source)

    assert duplicate.outcome is MaterializationOutcome.DUPLICATE
    assert duplicate.current_view_changed is False


def test_contradictory_discovery_does_not_overwrite_existing_entry() -> None:
    discovery_runner = discovery_boundary()
    runner = materializer()
    process(runner, discovery(discovery_runner))
    before = runner.snapshot()

    contradictory = process(
        runner,
        discovery(
            discovery_runner,
            source_event_id="event-2",
            sequence=2,
            token_identity="mint-B",
        ),
    )

    assert contradictory.outcome is MaterializationOutcome.MATERIALIZED
    assert runner.snapshot() == before + (
        contradictory.entry,
    )


def test_same_token_discovered_again_is_contradictory_and_not_replaced() -> None:
    discovery_runner = discovery_boundary()
    runner = materializer()
    first = discovery(discovery_runner)
    process(runner, first)
    before = runner.snapshot()

    second = discovery(
        discovery_runner,
        source_event_id="event-2",
        sequence=2,
    )
    result = process(runner, second)

    assert result.outcome is MaterializationOutcome.CONTRADICTORY
    assert result.current_view_changed is False
    assert runner.snapshot() == before


def test_out_of_order_does_not_advance_state() -> None:
    discovery_runner = discovery_boundary()
    runner = materializer()
    process(runner, discovery(discovery_runner, sequence=3))
    before = runner.state.state_version

    result = process(
        runner,
        discovery(discovery_runner, source_event_id="event-2", sequence=2),
    )

    assert result.outcome is MaterializationOutcome.OUT_OF_ORDER
    assert result.state_version == before
    assert runner.state.latest_sequence_by_source["fixture-source"] == 3


def test_stale_invalid_unavailable_and_resync_inputs_fail_closed() -> None:
    stale_source = discovery(
        discovery_boundary(),
        source_event_id="stale",
        discovery_time=EVENT_TIME - timedelta(minutes=2),
    )
    runner = materializer()
    stale = process(runner, stale_source)
    assert stale.outcome is MaterializationOutcome.STALE
    assert runner.snapshot() == ()

    invalid = process(runner, object())
    assert invalid.outcome is MaterializationOutcome.INVALID
    assert invalid.current_view_changed is False

    unavailable = discovery_boundary().process(
        object(),
        processing_time=PROCESSING_TIME,
        reference_time=REFERENCE_TIME,
    )
    assert unavailable.outcome is DiscoveryOutcome.INVALID

    resync = discovery(
        discovery_boundary(),
        source_event_id="resync",
        sequence=1,
        kind=DiscoveryKind.RESYNC,
    )
    result = process(runner, resync)
    assert result.outcome is MaterializationOutcome.RESYNCHRONIZATION_REQUIRED
    assert result.current_view_changed is False


def test_cross_chain_same_token_has_separate_entries() -> None:
    left_runner = discovery_boundary()
    right_runner = discovery_boundary()
    left = discovery(left_runner, source_event_id="left", sequence=1)
    right_item = DiscoveryObservation(
        source_id="other-source",
        kind=DiscoveryKind.DISCOVERED,
        token_identity="mint-A",
        chain_id="other-chain",
        observation_time=OBSERVED_TIME,
        discovery_time=EVENT_TIME,
        received_time=RECEIVED_TIME,
        source_event_id="right",
        sequence=1,
        discovery_reason="P02_T06_FIXTURE",
        metadata={"symbol": "MINT"},
        source_metadata={"fixture": "local"},
    )
    right = right_runner.process(
        right_item,
        processing_time=PROCESSING_TIME,
        reference_time=REFERENCE_TIME,
    )
    runner = materializer()

    process(runner, left)
    result = process(runner, right)

    assert result.outcome is MaterializationOutcome.MATERIALIZED
    assert {(entry.chain_id, entry.token_identity) for entry in result.current_view} == {
        ("solana", "mint-A"),
        ("other-chain", "mint-A"),
    }


def test_rejected_inputs_leave_all_owned_state_unchanged() -> None:
    runner = materializer()
    before = deepcopy(runner.state)

    result = process(runner, object())

    assert result.outcome is MaterializationOutcome.INVALID
    assert runner.state == before


def test_batch_replay_and_digest_are_deterministic() -> None:
    left_discovery = discovery_boundary()
    right_discovery = discovery_boundary()
    items_left = (
        discovery(left_discovery, source_event_id="one", sequence=1),
        discovery(left_discovery, source_event_id="two", sequence=2, token_identity="mint-B"),
    )
    items_right = (
        discovery(right_discovery, source_event_id="one", sequence=1),
        discovery(right_discovery, source_event_id="two", sequence=2, token_identity="mint-B"),
    )

    left = materializer().process_batch(
        items_left,
        processing_time=PROCESSING_TIME,
        reference_time=REFERENCE_TIME,
    )
    right = materializer().process_batch(
        items_right,
        processing_time=PROCESSING_TIME,
        reference_time=REFERENCE_TIME,
    )

    assert left == right
    assert left[-1].state_version == right[-1].state_version


def test_explicit_context_times_are_required_and_freshness_is_stable() -> None:
    source = discovery(discovery_boundary())
    runner = materializer()

    with pytest.raises(TypeError):
        runner.process(source)  # type: ignore[call-arg]

    result = process(
        runner,
        source,
        processing_time=PROCESSING_TIME.replace(tzinfo=None),
    )

    assert result.outcome is MaterializationOutcome.INVALID
    assert result.processing_time is None


def test_materialization_evaluation_times_may_differ_from_discovery_times() -> None:
    source = discovery(discovery_boundary())
    later_processing = PROCESSING_TIME + timedelta(minutes=1)
    later_reference = REFERENCE_TIME + timedelta(minutes=1)

    result = materializer().process(
        source,
        processing_time=later_processing,
        reference_time=later_reference,
    )

    assert result.outcome is MaterializationOutcome.MATERIALIZED
    assert result.processing_time == later_processing
    assert result.reference_time == later_reference