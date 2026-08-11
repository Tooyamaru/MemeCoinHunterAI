from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from types import MappingProxyType

import pytest

from core.data.contracts import DataQuality, FreshnessPolicy
from core.data.discovery import (
    DiscoveryKind,
    DiscoveryOrdering,
    DiscoveryProvenance,
)
from core.data.materialization import TokenUniverseEntry
from core.data.market_observations import (
    AcceptedMarketObservationEvidence,
    MarketObservationCandidate,
    MarketObservationContext,
    MarketObservationKind,
    MarketObservationProcessor,
    MarketObservationProvenance,
    P02T07PredecessorContext,
)
from core.data.market_state import (
    MarketStateContext,
    MarketStateMaterializer,
    MarketStateOutcome,
    MarketStateReason,
)


UTC = timezone.utc
OBSERVATION_TIME = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
RECEIVED_TIME = OBSERVATION_TIME + timedelta(seconds=1)
PROCESSING_TIME = RECEIVED_TIME + timedelta(seconds=1)
REFERENCE_TIME = OBSERVATION_TIME + timedelta(seconds=10)


def predecessor(*, chain_id="solana", token_identity="mint-A"):
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
        state_version="p02-t06-state",
        state_digest="p02-t06-state-digest",
        materializer_contract_version="p02-t06-fixture",
        evaluation_id="evaluation-1",
    )


def candidate(**overrides):
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


def accepted(*, p07_prior=False, **overrides) -> AcceptedMarketObservationEvidence:
    observation = candidate(**overrides)
    p07_context = MarketObservationContext(evaluation_id="evaluation-1")
    p07_processor = MarketObservationProcessor(
        predecessor=predecessor(
            chain_id=observation.chain_id,
            token_identity=observation.token_identity,
        ),
        context=p07_context,
        freshness_policy=FreshnessPolicy(stale_after=timedelta(minutes=1)),
    )
    if p07_prior:
        prior = candidate(
            source_id=observation.source_id,
            chain_id=observation.chain_id,
            token_identity=observation.token_identity,
            market_subject_id=observation.market_subject_id,
            source_event_id="prior",
            sequence=1,
        )
        prior_result = p07_processor.process(
            prior,
            processing_time=PROCESSING_TIME,
            reference_time=REFERENCE_TIME,
        )
        assert prior_result.evidence is not None
    result = MarketObservationProcessor(
        predecessor=predecessor(
            chain_id=observation.chain_id,
            token_identity=observation.token_identity,
        ),
        context=p07_context,
        freshness_policy=FreshnessPolicy(stale_after=timedelta(minutes=1)),
    ).process(
        observation,
        processing_time=PROCESSING_TIME,
        reference_time=REFERENCE_TIME,
    )
    assert result.evidence is not None
    return result.evidence


def materializer(*, context=None):
    return MarketStateMaterializer(
        context=context,
        evaluation_id="market-evaluation",
    )


def test_empty_input_is_deterministic():
    left = materializer()
    right = materializer()
    assert left.process_batch([]) == ()
    assert left.snapshot() == ()
    assert left.context.state_digest() == right.context.state_digest()


def test_first_observed_materializes_one_entry():
    result = materializer().process(accepted())
    assert result.outcome is MarketStateOutcome.MATERIALIZED
    assert result.quality is DataQuality.VALID
    assert result.accepted is True
    assert result.state_changed is True
    assert len(materializer().snapshot()) == 0


def test_updated_replaces_same_source_scoped_subject():
    runner = materializer()
    first = accepted(sequence=1, source_event_id="first")
    update = accepted(
        p07_prior=True,
        observation_kind=MarketObservationKind.UPDATED,
        sequence=2,
        source_event_id="second",
        observation_time=OBSERVATION_TIME + timedelta(seconds=2),
        received_time=RECEIVED_TIME + timedelta(seconds=2),
    )
    assert runner.process(first).outcome is MarketStateOutcome.MATERIALIZED
    result = runner.process(update)
    assert result.outcome is MarketStateOutcome.UPDATED
    assert runner.snapshot()[0].evidence.observation_id == update.observation_id


def test_updated_without_prior_state_is_rejected():
    observed = accepted()
    updated = replace(
        observed,
        observation_kind=MarketObservationKind.UPDATED,
        provenance=replace(
            observed.provenance,
            observation_kind=MarketObservationKind.UPDATED,
        ),
    )
    result = materializer().process(updated)
    assert result.outcome is MarketStateOutcome.REJECTED
    assert MarketStateReason.UPDATE_REQUIRES_PRIOR_STATE.value in result.reasons


def test_identity_includes_source_chain_token_and_subject():
    runner = materializer()
    result = runner.process(accepted())
    assert result.key == ("market-source", "solana", "mint-A", "subject-1")


def test_different_chains_are_isolated():
    runner = materializer()
    assert runner.process(accepted(source_event_id="solana")).accepted
    assert runner.process(accepted(chain_id="other-chain", source_event_id="other")).accepted
    assert len(runner.snapshot()) == 2


def test_different_tokens_are_isolated():
    runner = materializer()
    assert runner.process(accepted(source_event_id="mint-A")).accepted
    assert runner.process(accepted(token_identity="mint-B", source_event_id="mint-B")).accepted
    assert len(runner.snapshot()) == 2


def test_different_sources_are_not_merged():
    runner = materializer()
    assert runner.process(accepted(source_event_id="source-A")).accepted
    assert runner.process(accepted(source_id="source-B", source_event_id="source-B")).accepted
    assert len(runner.snapshot()) == 2


def test_equivalent_duplicate_does_not_mutate_state():
    evidence = accepted(source_event_id="duplicate")
    runner = materializer()
    first = runner.process(evidence)
    before = runner.context.state_digest()
    duplicate = runner.process(evidence)
    assert first.accepted
    assert duplicate.outcome is MarketStateOutcome.DUPLICATE
    assert duplicate.state_changed is False
    assert runner.context.state_digest() == before


def test_same_identity_conflict_is_contradictory():
    evidence = accepted(source_event_id="conflict")
    runner = materializer()
    runner.process(evidence)
    before = runner.context.state_digest()
    conflicting = object.__new__(AcceptedMarketObservationEvidence)
    for field_name in evidence.__dataclass_fields__:
        object.__setattr__(conflicting, field_name, getattr(evidence, field_name))
    object.__setattr__(conflicting, "observation_metadata", MappingProxyType({"changed": True}))
    result = runner.process(conflicting)
    assert result.outcome is MarketStateOutcome.CONTRADICTORY
    assert runner.context.state_digest() == before


def test_greater_integer_sequence_updates():
    runner = materializer()
    runner.process(accepted(sequence=1, source_event_id="one"))
    result = runner.process(
        accepted(
            p07_prior=True,
            observation_kind=MarketObservationKind.UPDATED,
            sequence=2,
            source_event_id="two",
            observation_time=OBSERVATION_TIME + timedelta(seconds=2),
            received_time=RECEIVED_TIME + timedelta(seconds=2),
        )
    )
    assert result.outcome is MarketStateOutcome.UPDATED


def test_equal_integer_sequence_duplicate_or_contradictory():
    runner = materializer()
    first = accepted(sequence=4, source_event_id="one")
    runner.process(first)
    result = runner.process(first)
    assert result.outcome in {
        MarketStateOutcome.DUPLICATE,
        MarketStateOutcome.CONTRADICTORY,
    }


def test_lower_integer_sequence_is_out_of_order():
    runner = materializer()
    runner.process(accepted(sequence=4, source_event_id="high"))
    result = runner.process(
        accepted(
            p07_prior=True,
            observation_kind=MarketObservationKind.UPDATED,
            sequence=3,
            source_event_id="low",
        )
    )
    assert result.outcome is MarketStateOutcome.OUT_OF_ORDER
    assert result.state_changed is False


def test_missing_and_string_sequence_are_not_compared():
    runner = materializer()
    assert runner.process(accepted(sequence=None, source_event_id="none")).accepted
    assert runner.process(
        accepted(
            p07_prior=True,
            observation_kind=MarketObservationKind.UPDATED,
            sequence="cursor-2",
            source_event_id="string",
        )
    ).accepted


@pytest.mark.parametrize("quality", [DataQuality.STALE, DataQuality.INVALID, DataQuality.INCOMPLETE])
def test_non_valid_quality_is_rejected(quality):
    evidence = accepted()
    invalid = object.__new__(AcceptedMarketObservationEvidence)
    for field_name in evidence.__dataclass_fields__:
        object.__setattr__(invalid, field_name, getattr(evidence, field_name))
    object.__setattr__(invalid, "quality", quality)
    object.__setattr__(invalid, "quality_status", quality)
    result = materializer().process(invalid)
    assert result.accepted is False
    assert result.state_changed is False


def test_unaccepted_evidence_is_rejected():
    evidence = accepted()
    invalid = object.__new__(AcceptedMarketObservationEvidence)
    for field_name in evidence.__dataclass_fields__:
        object.__setattr__(invalid, field_name, getattr(evidence, field_name))
    object.__setattr__(invalid, "accepted", False)
    result = materializer().process(invalid)
    assert result.outcome is MarketStateOutcome.REJECTED


def test_invalid_timestamp_age_identity_and_provenance_are_rejected():
    evidence = accepted()
    for field_name, value in (
        ("observation_time", datetime(2026, 8, 11, 12, 0)),
        ("data_age", timedelta(seconds=-1)),
        ("source_id", ""),
    ):
        invalid = object.__new__(AcceptedMarketObservationEvidence)
        for name in evidence.__dataclass_fields__:
            object.__setattr__(invalid, name, getattr(evidence, name))
        object.__setattr__(invalid, field_name, value)
        result = materializer().process(invalid)
        assert result.accepted is False


def test_rejection_preserves_digest():
    runner = materializer()
    before = runner.context.state_digest()
    result = runner.process(object())
    assert result.local_state_digest == before
    assert result.state_changed is False


def test_p02_provenance_references_are_preserved():
    result = materializer().process(accepted()).entry
    assert result is not None
    assert result.evidence.predecessor_state_version == "p02-t06-state"
    assert result.evidence.predecessor_state_digest == "p02-t06-state-digest"
    assert result.evidence.local_state_version
    assert result.evidence.local_state_digest


def test_public_state_and_metadata_are_immutable():
    result = materializer().process(accepted())
    assert result.entry is not None
    with pytest.raises(FrozenInstanceError):
        result.entry.evidence.accepted = False
    assert isinstance(result.entry.evidence.observation_metadata, MappingProxyType)
    with pytest.raises(TypeError):
        result.entry.evidence.observation_metadata["new"] = "value"


def test_snapshot_key_order_is_canonical():
    runner = materializer()
    runner.process(accepted(source_id="z-source", source_event_id="z"))
    runner.process(accepted(source_id="a-source", source_event_id="a"))
    assert [entry.key[0] for entry in runner.snapshot()] == ["a-source", "z-source"]


def test_replay_is_identical():
    evidence = accepted(source_event_id="replay")
    left = materializer()
    right = materializer()
    assert left.process(evidence) == right.process(evidence)
    assert left.context.state_digest() == right.context.state_digest()
    assert left.snapshot() == right.snapshot()


def test_upstream_contexts_are_not_mutated():
    evidence = accepted()
    before = (
        evidence.local_state_digest,
        evidence.predecessor_state_digest,
    )
    runner = materializer()
    runner.process(evidence)
    assert (evidence.local_state_digest, evidence.predecessor_state_digest) == before


def test_measurement_like_metadata_is_not_projected_as_state():
    evidence = accepted()
    metadata = dict(evidence.observation_metadata)
    metadata["price"] = 1
    invalid = object.__new__(AcceptedMarketObservationEvidence)
    for field_name in evidence.__dataclass_fields__:
        object.__setattr__(invalid, field_name, getattr(evidence, field_name))
    object.__setattr__(invalid, "observation_metadata", MappingProxyType(metadata))
    result = materializer().process(invalid)
    assert result.accepted is False
    assert not hasattr(result.entry, "price")


def test_rejected_evidence_is_excluded_from_digest():
    runner = materializer()
    before = runner.context.state_digest()
    runner.process(object())
    assert runner.context.state_digest() == before
