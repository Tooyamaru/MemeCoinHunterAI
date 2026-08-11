from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from types import MappingProxyType

import pytest

from core.data.contracts import DataQuality, FreshnessPolicy, OrderingStatus
from core.data.discovery import (
    DiscoveryKind,
    DiscoveryOrdering,
    DiscoveryProvenance,
)
from core.data.materialization import TokenUniverseEntry
from core.data.market_observations import (
    MarketObservationCandidate,
    MarketObservationContext,
    MarketObservationKind,
    MarketObservationOutcome,
    MarketObservationProcessor,
    MarketObservationReason,
    P02T07PredecessorContext,
    derive_observation_id,
)


UTC = timezone.utc
OBSERVATION_TIME = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
RECEIVED_TIME = OBSERVATION_TIME + timedelta(seconds=1)
PROCESSING_TIME = RECEIVED_TIME + timedelta(seconds=1)
REFERENCE_TIME = OBSERVATION_TIME + timedelta(seconds=10)


def predecessor(
    *,
    chain_id: str = "solana",
    token_identity: str = "mint-A",
    state_version: str = "p02-t06-state",
) -> P02T07PredecessorContext:
    entry = TokenUniverseEntry(
        token_identity=token_identity,
        chain_id=chain_id,
        discovery_id="discovery-1",
        discovery_kind=DiscoveryKind.DISCOVERED,
        discovery_reason="fixture",
        quality_status=DataQuality.VALID,
        ordering=DiscoveryOrdering.FIRST,
        data_age=timedelta(seconds=1),
        metadata={"symbol": "MINT"},
        provenance=DiscoveryProvenance(
            source_id="discovery-source",
            source_event_id="discovery-event",
            observation_time=OBSERVATION_TIME,
            discovery_time=OBSERVATION_TIME,
            received_time=RECEIVED_TIME,
            sequence=1,
            source_metadata={"fixture": "local"},
        ),
        discovery_contract_version="p02-t04-fixture",
        materializer_contract_version="p02-t06-fixture",
    )
    return P02T07PredecessorContext(
        snapshot=(entry,),
        state_version=state_version,
        state_digest=f"{state_version}-digest",
        materializer_contract_version="p02-t06-fixture",
        evaluation_id="evaluation-1",
    )


def candidate(**overrides) -> MarketObservationCandidate:
    values = {
        "source_id": "market-source",
        "chain_id": "solana",
        "token_identity": "mint-A",
        "market_subject_id": "subject-1",
        "observation_kind": MarketObservationKind.OBSERVED,
        "observation_time": OBSERVATION_TIME,
        "received_time": RECEIVED_TIME,
        "observation_metadata": {"symbol": "MINT", "venue": "fixture"},
        "source_metadata": {"adapter": "fixture"},
        "contract_version": "p02-t07-candidate",
        "sequence": 1,
    }
    values.update(overrides)
    return MarketObservationCandidate(**values)


def processor(
    *,
    context: MarketObservationContext | None = None,
    stale_after: timedelta | None = timedelta(minutes=1),
    predecessor_context: P02T07PredecessorContext | None = None,
) -> MarketObservationProcessor:
    return MarketObservationProcessor(
        predecessor=predecessor_context or predecessor(),
        context=context,
        freshness_policy=FreshnessPolicy(stale_after=stale_after),
    )


def process(runner: MarketObservationProcessor, item, **overrides):
    return runner.process(
        item,
        processing_time=overrides.get("processing_time", PROCESSING_TIME),
        reference_time=overrides.get("reference_time", REFERENCE_TIME),
    )


def test_valid_observed_is_accepted_against_p02_t06_snapshot() -> None:
    result = process(processor(), candidate())

    assert result.outcome is MarketObservationOutcome.OBSERVED
    assert result.quality is DataQuality.VALID
    assert result.accepted is True
    assert result.state_changed is True
    assert result.evidence is not None
    assert result.evidence.ordering_status is OrderingStatus.FIRST
    assert result.evidence.materializer_contract_version == "p02-t06-fixture"
    assert result.evidence.predecessor_state_version == "p02-t06-state"
    assert result.evidence.provenance.source_id == "market-source"


def test_valid_updated_is_accepted_and_preserves_prior_evidence() -> None:
    runner = processor()
    first = process(runner, candidate(source_event_id="event-1", sequence=1))
    prior = runner.context.accepted_evidence[("market-source", "solana", "mint-A", "subject-1")]

    updated = process(
        runner,
        candidate(
            observation_kind=MarketObservationKind.UPDATED,
            source_event_id="event-2",
            sequence=2,
            observation_metadata={"symbol": "MINT", "venue": "updated"},
        ),
    )

    assert first.outcome is MarketObservationOutcome.OBSERVED
    assert updated.outcome is MarketObservationOutcome.UPDATED
    assert updated.evidence is not prior
    assert prior.observation_id == first.observation_id
    assert prior.observation_metadata["venue"] == "fixture"
    assert updated.evidence.ordering_status is OrderingStatus.IN_ORDER


def test_updated_without_prior_observation_is_rejected() -> None:
    result = process(
        processor(),
        candidate(observation_kind=MarketObservationKind.UPDATED),
    )

    assert result.outcome is MarketObservationOutcome.REJECTED
    assert result.quality is DataQuality.INCOMPLETE
    assert MarketObservationReason.UPDATE_REQUIRES_PRIOR_OBSERVATION.value in result.reasons


@pytest.mark.parametrize(
    "overrides, expected_outcome, expected_quality",
    [
        (
            {"token_identity": "missing"},
            MarketObservationOutcome.TOKEN_NOT_CURRENT,
            DataQuality.INCOMPLETE,
        ),
        (
            {"chain_id": "ethereum"},
            MarketObservationOutcome.TOKEN_NOT_CURRENT,
            DataQuality.INCOMPLETE,
        ),
        (
            {"market_subject_id": ""},
            MarketObservationOutcome.INCOMPLETE,
            DataQuality.INCOMPLETE,
        ),
    ],
)
def test_current_token_and_identity_validation(overrides, expected_outcome, expected_quality) -> None:
    result = process(processor(), candidate(**overrides))

    assert result.outcome is expected_outcome
    assert result.quality is expected_quality
    assert result.accepted is False


def test_duplicate_identical_content_does_not_mutate_state() -> None:
    runner = processor()
    accepted = process(runner, candidate(source_event_id="same"))
    before = runner.context.state_digest()

    duplicate = process(runner, candidate(source_event_id="same"))

    assert accepted.outcome is MarketObservationOutcome.OBSERVED
    assert duplicate.outcome is MarketObservationOutcome.DUPLICATE
    assert duplicate.quality is DataQuality.DUPLICATE
    assert duplicate.state_changed is False
    assert duplicate.local_state_digest == before


def test_contradictory_identity_does_not_replace_prior_evidence() -> None:
    runner = processor()
    process(runner, candidate(source_event_id="same"))
    before = runner.context.state_digest()

    contradictory = process(
        runner,
        candidate(source_event_id="same", observation_metadata={"different": True}),
    )

    assert contradictory.outcome is MarketObservationOutcome.CONTRADICTORY
    assert contradictory.quality is DataQuality.CONTRADICTORY
    assert contradictory.local_state_digest == before
    assert runner.context.accepted_evidence[("market-source", "solana", "mint-A", "subject-1")].observation_metadata[
        "venue"
    ] == "fixture"


def test_repeated_observed_same_subject_is_duplicate_or_contradictory() -> None:
    runner = processor()
    first = process(runner, candidate(source_event_id="first", sequence=None))
    before = runner.context.state_digest()

    equivalent = process(runner, candidate(source_event_id="second", sequence=None))
    conflicting = process(
        runner,
        candidate(
            source_event_id="third",
            sequence=None,
            observation_metadata={"symbol": "CHANGED", "venue": "fixture"},
        ),
    )

    assert first.outcome is MarketObservationOutcome.OBSERVED
    assert first.accepted is True
    assert equivalent.outcome is MarketObservationOutcome.DUPLICATE
    assert equivalent.accepted is False
    assert equivalent.local_state_digest == before
    assert conflicting.outcome is MarketObservationOutcome.CONTRADICTORY
    assert conflicting.accepted is False
    assert conflicting.local_state_digest == before
    assert runner.context.state_digest() == before


def test_out_of_order_integer_sequence_does_not_advance_ordering() -> None:
    runner = processor()
    process(runner, candidate(source_event_id="new", sequence=3))
    before = runner.context.state_digest()

    result = process(runner, candidate(source_event_id="old", sequence=2))

    assert result.outcome is MarketObservationOutcome.OUT_OF_ORDER
    assert result.quality is DataQuality.OUT_OF_ORDER
    assert result.local_state_digest == before
    assert runner.context.latest_sequence_by_subject[("market-source", "solana", "mint-A", "subject-1")] == 3


def test_missing_sequence_does_not_infer_arrival_order() -> None:
    runner = processor()
    first = process(runner, candidate(source_event_id="one", sequence=None))
    second = process(
        runner,
        candidate(
            source_event_id="two",
            sequence=None,
            observation_kind=MarketObservationKind.UPDATED,
        ),
    )

    assert first.outcome is MarketObservationOutcome.OBSERVED
    assert first.evidence.ordering_status is OrderingStatus.NOT_PROVIDED
    assert second.outcome is MarketObservationOutcome.UPDATED
    assert second.evidence.ordering_status is OrderingStatus.NOT_PROVIDED
    assert runner.context.latest_sequence_by_subject == {}


def test_stale_negative_age_and_timestamp_relationships_fail_closed() -> None:
    runner = processor(stale_after=timedelta(seconds=2))
    stale = process(
        runner,
        candidate(
            source_event_id="stale",
            observation_time=OBSERVATION_TIME - timedelta(minutes=1),
            received_time=OBSERVATION_TIME,
        ),
    )
    assert stale.outcome is MarketObservationOutcome.STALE
    assert stale.quality is DataQuality.STALE
    assert stale.state_changed is False

    negative = process(
        runner,
        candidate(
            source_event_id="future",
            observation_time=REFERENCE_TIME + timedelta(seconds=1),
            received_time=REFERENCE_TIME + timedelta(seconds=2),
        ),
    )
    assert negative.outcome is MarketObservationOutcome.INVALID
    assert MarketObservationReason.NEGATIVE_DATA_AGE.value in negative.reasons

    invalid_relationship = process(
        runner,
        candidate(
            source_event_id="received-first",
            observation_time=OBSERVATION_TIME + timedelta(seconds=2),
            received_time=OBSERVATION_TIME + timedelta(seconds=1),
        ),
    )
    assert invalid_relationship.outcome is MarketObservationOutcome.INVALID
    assert MarketObservationReason.INVALID_TIMESTAMP_RELATIONSHIP.value in invalid_relationship.reasons


def test_source_unavailable_and_resynchronization_do_not_accept_or_advance() -> None:
    runner = processor()
    before = runner.context.state_digest()

    unavailable = process(runner, candidate(source_unavailable=True))
    assert unavailable.outcome is MarketObservationOutcome.SOURCE_UNAVAILABLE
    assert unavailable.quality is DataQuality.SOURCE_UNAVAILABLE
    assert unavailable.local_state_digest == before

    resync = process(runner, candidate(source_event_id="resync", resynchronization_required=True))
    assert resync.outcome is MarketObservationOutcome.RESYNCHRONIZATION_REQUIRED
    assert resync.state_changed is False
    assert resync.local_state_digest == before
    assert runner.context.state_digest() == before
    assert runner.context.accepted_evidence == {}
    assert runner.context.latest_sequence_by_subject == {}
    assert runner.context.resynchronization_required == set()


def test_unsupported_kind_and_measurements_are_rejected() -> None:
    unsupported_kind = process(processor(), candidate(observation_kind="POOL_CREATED"))
    assert unsupported_kind.outcome is MarketObservationOutcome.UNSUPPORTED

    unsupported_measurement = process(
        processor(),
        candidate(observation_metadata={"price": 1}),
    )
    assert unsupported_measurement.outcome is MarketObservationOutcome.UNSUPPORTED
    assert unsupported_measurement.accepted is False


@pytest.mark.parametrize(
    "metadata",
    [
        {"api_key": "hidden"},
        {"nested": object()},
        {1: "non-string-key"},
        {"nested": {"private_key": "hidden"}},
    ],
)
def test_opaque_sensitive_and_noncanonical_metadata_is_rejected(metadata) -> None:
    result = process(processor(), candidate(observation_metadata=metadata))

    assert result.outcome is MarketObservationOutcome.INVALID
    assert result.accepted is False
    assert "hidden" not in " ".join(result.reasons)


def test_metadata_bounds_are_enforced() -> None:
    result = process(
        processor(),
        candidate(observation_metadata={f"key-{index}": index for index in range(100)}),
    )

    assert result.outcome is MarketObservationOutcome.INVALID
    assert MarketObservationReason.METADATA_BOUNDS_EXCEEDED.value in result.reasons


def test_observation_id_is_deterministic_and_contradictory_ids_are_rejected() -> None:
    left = candidate(source_event_id=None, observation_metadata={"b": 2, "a": 1})
    right = candidate(source_event_id=None, observation_metadata={"a": 1, "b": 2})
    assert derive_observation_id(left) == derive_observation_id(right)

    result = process(processor(), candidate(observation_id="not-the-canonical-id"))
    assert result.outcome is MarketObservationOutcome.INVALID
    assert MarketObservationReason.OBSERVATION_ID_MISMATCH.value in result.reasons


def test_provenance_and_p02_t06_context_are_preserved() -> None:
    result = process(processor(), candidate(sequence="cursor-1"))

    assert result.evidence is not None
    assert result.evidence.provenance.sequence == "cursor-1"
    assert result.evidence.provenance.source_metadata["adapter"] == "fixture"
    assert result.evidence.predecessor_state_version == "p02-t06-state"
    assert result.evidence.predecessor_state_digest == "p02-t06-state-digest"
    assert result.evidence.data_age == REFERENCE_TIME - OBSERVATION_TIME


def test_rejected_candidates_leave_owned_state_unchanged() -> None:
    runner = processor()
    before = runner.context.state_digest()

    result = process(runner, candidate(token_identity="not-current"))

    assert result.accepted is False
    assert result.state_changed is False
    assert runner.context.state_digest() == before


def test_different_chains_and_sources_remain_separate_subjects() -> None:
    runner = processor(
        predecessor_context=P02T07PredecessorContext(
            snapshot=predecessor().snapshot
            + (
                TokenUniverseEntry(
                    token_identity="mint-A",
                    chain_id="other-chain",
                    discovery_id="discovery-2",
                    discovery_kind=DiscoveryKind.DISCOVERED,
                    discovery_reason="fixture",
                    quality_status=DataQuality.VALID,
                    ordering=DiscoveryOrdering.FIRST,
                    data_age=timedelta(seconds=1),
                    metadata={},
                    provenance=predecessor().snapshot[0].provenance,
                    discovery_contract_version="p02-t04-fixture",
                    materializer_contract_version="p02-t06-fixture",
                ),
            ),
            state_version="two-chain-state",
            state_digest="two-chain-digest",
            materializer_contract_version="p02-t06-fixture",
        )
    )
    first = process(runner, candidate(source_event_id="one"))
    second = process(runner, candidate(source_id="other-source", source_event_id="two"))
    third = process(runner, candidate(chain_id="other-chain", source_event_id="three"))

    assert first.outcome is MarketObservationOutcome.OBSERVED
    assert second.outcome is MarketObservationOutcome.OBSERVED
    assert third.outcome is MarketObservationOutcome.OBSERVED
    assert len(runner.context.accepted_evidence) == 3


def test_deterministic_replay_and_state_digest() -> None:
    left = processor()
    right = processor()
    item = candidate(source_event_id="replay", sequence=7)

    left_result = process(left, item)
    right_result = process(right, item)

    assert left_result == right_result
    assert left.context.state_digest() == right.context.state_digest()


def test_accepted_evidence_is_immutable() -> None:
    result = process(processor(), candidate())
    assert result.evidence is not None

    with pytest.raises(FrozenInstanceError):
        result.evidence.accepted = False
    with pytest.raises(TypeError):
        result.evidence.observation_metadata["new"] = "value"
    assert isinstance(result.evidence.observation_metadata, MappingProxyType)