from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from types import MappingProxyType

import pytest

from core.data.contracts import DataQuality, FreshnessPolicy
from core.data.discovery import (
    DiscoveryKind,
    DiscoveryOrdering,
    DiscoveryProvenance,
)
from core.data.market_intelligence import (
    AcceptedMarketIntelligenceObservation,
    MarketIntelligenceCategory,
    MarketIntelligenceCategoryContract,
    MarketIntelligenceContext,
    MarketIntelligenceOutcome,
    MarketIntelligenceObservation,
    MarketIntelligenceProcessor,
    MarketIntelligenceReason,
    MarketIntelligenceStateReference,
    MarketIntelligenceValueKind,
)
from core.data.market_observations import (
    MarketObservationCandidate,
    MarketObservationContext,
    MarketObservationKind,
    MarketObservationProcessor,
    P02T07PredecessorContext,
)
from core.data.market_state import MarketStateEntry, MarketStateMaterializer
from core.data.materialization import TokenUniverseEntry


UTC = timezone.utc
OBSERVATION_TIME = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
RECEIVED_TIME = OBSERVATION_TIME + timedelta(seconds=1)
REFERENCE_TIME = OBSERVATION_TIME + timedelta(seconds=10)
PROCESSING_TIME = RECEIVED_TIME + timedelta(seconds=1)


def _p07_predecessor(chain_id: str = "solana", token_identity: str = "mint-A"):
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
        state_digest="p02-t06-digest",
        materializer_contract_version="p02-t06-fixture",
        evaluation_id="evaluation-1",
    )


def _accepted_p08_evidence(
    *,
    source_id: str = "market-source",
    chain_id: str = "solana",
    token_identity: str = "mint-A",
    market_subject_id: str = "subject-1",
    source_event_id: str = "market-event",
    sequence: int | str | None = 1,
    observation_kind: MarketObservationKind = MarketObservationKind.OBSERVED,
):
    candidate = MarketObservationCandidate(
        source_id=source_id,
        chain_id=chain_id,
        token_identity=token_identity,
        market_subject_id=market_subject_id,
        observation_kind=observation_kind,
        observation_time=OBSERVATION_TIME,
        received_time=RECEIVED_TIME,
        observation_metadata={"venue": "fixture"},
        source_metadata={"adapter": "fixture"},
        contract_version="p02-t07-fixture",
        source_event_id=source_event_id,
        sequence=sequence,
    )
    p07 = MarketObservationProcessor(
        predecessor=_p07_predecessor(chain_id, token_identity),
        context=MarketObservationContext(evaluation_id="evaluation-1"),
        freshness_policy=FreshnessPolicy(stale_after=timedelta(minutes=1)),
    )
    result = p07.process(
        candidate,
        processing_time=PROCESSING_TIME,
        reference_time=REFERENCE_TIME,
    )
    assert result.evidence is not None
    return result.evidence


def _upstream(*, source_id="market-source", chain_id="solana", token_identity="mint-A"):
    evidence = _accepted_p08_evidence(
        source_id=source_id, chain_id=chain_id, token_identity=token_identity
    )
    entry = MarketStateEntry(
        key=(source_id, chain_id, token_identity, "subject-1"),
        evidence=evidence,
        entry_fingerprint="p02-t08-entry-fingerprint",
    )
    return MarketIntelligenceStateReference(
        state_entry=entry,
        state_version="p02-t08-state-version",
        state_digest="p02-t08-state-digest",
        evaluation_id="intelligence-evaluation",
    )


def _observation(*, source_id="market-source", sequence=1, **overrides):
    values = {
        "source_id": source_id,
        "chain_id": "solana",
        "token_identity": "mint-A",
        "market_subject_id": "subject-1",
        "intelligence_category": MarketIntelligenceCategory.PRICE,
        "value": {"raw": "provider-neutral"},
        "observation_time": OBSERVATION_TIME,
        "received_time": RECEIVED_TIME,
        "reference_time": REFERENCE_TIME,
        "data_age": REFERENCE_TIME - OBSERVATION_TIME,
        "upstream": _upstream(source_id=source_id),
        "source_event_id": "intelligence-event",
        "sequence": sequence,
        "source_metadata": {"adapter": "fixture"},
        "observation_metadata": {"window": "explicit"},
    }
    values.update(overrides)
    return MarketIntelligenceObservation(**values)


def _processor(*, context=None):
    return MarketIntelligenceProcessor(context=context)


def test_empty_context_has_stable_digest_and_snapshot():
    left = _processor()
    right = _processor()
    assert left.snapshot() == ()
    assert left.context.state_digest() == right.context.state_digest()


def test_valid_observation_is_represented_with_p02_t08_provenance():
    result = _processor().process(_observation())

    assert result.outcome is MarketIntelligenceOutcome.REPRESENTED
    assert result.quality is DataQuality.VALID
    assert result.accepted is True
    assert result.observation is not None
    assert result.observation.upstream.state_version == "p02-t08-state-version"
    assert result.observation.provenance.upstream_state_digest == "p02-t08-state-digest"
    assert result.observation.intelligence_category is MarketIntelligenceCategory.PRICE
    assert result.observation.value == {"raw": "provider-neutral"}


def test_new_observation_for_same_category_subject_updates_current_projection():
    runner = _processor()
    first = runner.process(_observation(source_event_id="first", sequence=1))
    second = runner.process(
        _observation(
            source_event_id="second",
            sequence=2,
            value={"raw": "updated"},
        )
    )

    assert first.outcome is MarketIntelligenceOutcome.REPRESENTED
    assert second.outcome is MarketIntelligenceOutcome.UPDATED
    assert runner.snapshot()[0] is second.observation
    assert first.observation is not second.observation


def test_duplicate_does_not_change_state_or_digest():
    runner = _processor()
    accepted = runner.process(_observation())
    before = runner.context.state_digest()

    duplicate = runner.process(_observation())

    assert accepted.accepted
    assert duplicate.outcome is MarketIntelligenceOutcome.DUPLICATE
    assert duplicate.quality is DataQuality.DUPLICATE
    assert duplicate.local_state_digest == before
    assert runner.context.state_digest() == before


def test_same_identity_with_changed_content_is_contradictory():
    runner = _processor()
    runner.process(_observation())
    before = runner.context.state_digest()

    contradictory = runner.process(_observation(value={"changed": True}))

    assert contradictory.outcome is MarketIntelligenceOutcome.CONTRADICTORY
    assert contradictory.quality is DataQuality.CONTRADICTORY
    assert contradictory.state_changed is False
    assert runner.context.state_digest() == before


def test_lower_sequence_is_rejected_and_does_not_advance_ordering():
    runner = _processor()
    runner.process(_observation(sequence=3))
    before = runner.context.state_digest()

    result = runner.process(_observation(source_event_id="older", sequence=2))

    assert result.outcome is MarketIntelligenceOutcome.OUT_OF_ORDER
    assert result.quality is DataQuality.OUT_OF_ORDER
    assert result.local_state_digest == before


@pytest.mark.parametrize(
    "overrides, expected",
    [
        (
            {"intelligence_category": "NOT_APPROVED"},
            MarketIntelligenceOutcome.UNSUPPORTED,
        ),
        (
            {"value": object()},
            MarketIntelligenceOutcome.INVALID,
        ),
        (
            {"reference_time": None, "data_age": None},
            MarketIntelligenceOutcome.INCOMPLETE,
        ),
        (
            {"observation_time": REFERENCE_TIME + timedelta(seconds=1)},
            MarketIntelligenceOutcome.INVALID,
        ),
    ],
)
def test_invalid_incomplete_and_unsupported_inputs_fail_closed(overrides, expected):
    result = _processor().process(_observation(**overrides))

    assert result.outcome is expected
    assert result.accepted is False
    assert result.state_changed is False


def test_explicit_category_shape_contract_rejects_wrong_value_shape():
    contracts = {
        MarketIntelligenceCategory.PRICE: MarketIntelligenceCategoryContract(
            MarketIntelligenceCategory.PRICE,
            MarketIntelligenceValueKind.SCALAR,
        )
    }
    result = MarketIntelligenceProcessor(category_contracts=contracts).process(_observation())

    assert result.outcome is MarketIntelligenceOutcome.UNSUPPORTED
    assert MarketIntelligenceReason.VALUE_KIND_MISMATCH.value in result.reasons


def test_upstream_identity_mismatch_is_rejected_without_mutation():
    upstream = _upstream()
    observation = _observation(
        upstream=MarketIntelligenceStateReference(
            state_entry=upstream.state_entry,
            state_version=upstream.state_version,
            state_digest=upstream.state_digest,
            evaluation_id=upstream.evaluation_id,
        ),
        token_identity="different-token",
    )
    before = _processor().context.state_digest()
    result = _processor().process(observation)

    assert result.outcome is MarketIntelligenceOutcome.INVALID
    assert MarketIntelligenceReason.UPSTREAM_IDENTITY_MISMATCH.value in result.reasons
    assert result.local_state_digest == before


def test_source_unavailable_is_observable_and_not_current():
    runner = _processor()
    before = runner.context.state_digest()

    result = runner.process(_observation(source_unavailable=True))

    assert result.outcome is MarketIntelligenceOutcome.UNAVAILABLE
    assert result.quality is DataQuality.SOURCE_UNAVAILABLE
    assert result.local_state_digest == before
    assert runner.snapshot() == ()


def test_public_observation_and_metadata_are_immutable():
    result = _processor().process(_observation())
    assert result.observation is not None

    with pytest.raises(FrozenInstanceError):
        result.observation.accepted = False
    assert isinstance(result.observation.value, MappingProxyType)
    with pytest.raises(TypeError):
        result.observation.value["new"] = "value"


def test_replay_is_deterministic_and_upstream_is_not_mutated():
    observation = _observation()
    upstream_before = upstream_digest = (
        observation.upstream.state_version,
        observation.upstream.state_digest,
        observation.upstream.state_entry,
    )
    left = _processor()
    right = _processor()

    left_result = left.process(observation)
    right_result = right.process(observation)

    assert left_result == right_result
    assert left.context.state_digest() == right.context.state_digest()
    assert (
        observation.upstream.state_version,
        observation.upstream.state_digest,
        observation.upstream.state_entry,
    ) == upstream_before
    assert upstream_digest == (
        "p02-t08-state-version",
        "p02-t08-state-digest",
        observation.upstream.state_entry,
    )


def test_metadata_bounds_and_sensitive_values_fail_closed():
    too_large = _processor().process(
        _observation(observation_metadata={f"key-{i}": i for i in range(100)})
    )
    sensitive = _processor().process(
        _observation(observation_metadata={"api_key": "must-not-cross"})
    )

    assert too_large.outcome is MarketIntelligenceOutcome.INVALID
    assert MarketIntelligenceReason.METADATA_BOUNDS_EXCEEDED.value in too_large.reasons
    assert sensitive.outcome is MarketIntelligenceOutcome.INVALID
    assert "must-not-cross" not in str(sensitive)


def test_different_categories_remain_separate_subjects():
    runner = _processor()
    first = runner.process(_observation())
    second = runner.process(
        _observation(
            intelligence_category=MarketIntelligenceCategory.STREAM_HEALTH,
            source_event_id="health",
            value={"status": "observed"},
        )
    )

    assert first.accepted and second.accepted
    assert len(runner.snapshot()) == 2
    assert {item.intelligence_category for item in runner.snapshot()} == {
        MarketIntelligenceCategory.PRICE,
        MarketIntelligenceCategory.STREAM_HEALTH,
    }