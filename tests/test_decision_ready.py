from datetime import datetime, timedelta, timezone

import pytest

from core.data.contracts import DataQuality, FreshnessPolicy
from core.data.discovery import (
    DiscoveryKind,
    DiscoveryOrdering,
    DiscoveryProvenance,
)
from core.data.market_intelligence import (
    DecisionReadyAssessmentStatus,
    DecisionReadyCandidate,
    DecisionReadyDataQuality,
    DecisionReadyEligibility,
    DecisionReadyEligibilityStatus,
    DecisionReadyEvidence,
    DecisionReadyIdentity,
    DecisionReadyLiquidity,
    DecisionReadyMarketActivity,
    DecisionReadyMarketSnapshot,
    DecisionReadyOutcome,
    DecisionReadyReason,
    DecisionReadySafety,
    DecisionReadySellability,
    MarketIntelligenceStateReference,
    validate_decision_ready_candidate,
)
from core.data.market_observations import (
    MarketObservationCandidate,
    MarketObservationContext,
    MarketObservationKind,
    MarketObservationProcessor,
    P02T07PredecessorContext,
)
from core.data.market_state import MarketStateEntry
from core.data.materialization import TokenUniverseEntry


UTC = timezone.utc
OBSERVED_AT = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
RECEIVED_AT = OBSERVED_AT + timedelta(seconds=1)
PROCESSING_AT = RECEIVED_AT + timedelta(seconds=1)


def _upstream() -> MarketIntelligenceStateReference:
    entry = TokenUniverseEntry(
        token_identity="mint-A",
        chain_id="solana",
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
            observation_time=OBSERVED_AT,
            discovery_time=OBSERVED_AT,
            received_time=RECEIVED_AT,
            sequence=1,
            source_metadata={"fixture": "local"},
        ),
        discovery_contract_version="p02-t04-fixture",
        materializer_contract_version="p02-t06-fixture",
    )
    predecessor = P02T07PredecessorContext(
        snapshot=(entry,),
        state_version="p02-t06-state",
        state_digest="p02-t06-digest",
        materializer_contract_version="p02-t06-fixture",
    )
    p07 = MarketObservationProcessor(
        predecessor=predecessor,
        context=MarketObservationContext(),
        freshness_policy=FreshnessPolicy(),
    )
    result = p07.process(
        MarketObservationCandidate(
            source_id="market-source",
            chain_id="solana",
            token_identity="mint-A",
            market_subject_id="subject-1",
            observation_kind=MarketObservationKind.OBSERVED,
            observation_time=OBSERVED_AT,
            received_time=RECEIVED_AT,
            observation_metadata={"fixture": "market"},
            source_metadata={"adapter": "fixture"},
            source_event_id="market-event",
            sequence=1,
        ),
        processing_time=PROCESSING_AT,
        reference_time=PROCESSING_AT,
    )
    assert result.evidence is not None
    state_entry = MarketStateEntry(
        key=("market-source", "solana", "mint-A", "subject-1"),
        evidence=result.evidence,
        entry_fingerprint="p02-t08-entry",
    )
    return MarketIntelligenceStateReference(
        state_entry=state_entry,
        state_version="p02-t08-state",
        state_digest="p02-t08-digest",
        evaluation_id="decision-evaluation",
    )


def _candidate(**overrides) -> DecisionReadyCandidate:
    upstream = _upstream()
    values = {
        "identity": DecisionReadyIdentity(
            chain_id="solana",
            token_identity="mint-A",
            source_id="market-source",
            symbol="MINT",
            decimals=9,
            market_subject_id="subject-1",
            exposure_identity="solana:mint-A",
        ),
        "market_snapshot": DecisionReadyMarketSnapshot(
            observed_at=OBSERVED_AT,
            values={"observed_market_state": "bounded"},
            source_id="market-source",
            upstream=upstream,
        ),
        "liquidity": DecisionReadyLiquidity(
            observed_at=OBSERVED_AT,
            values={"liquidity_observation": "bounded"},
        ),
        "market_activity": DecisionReadyMarketActivity(
            observed_at=OBSERVED_AT,
            values={"activity_observation": "bounded"},
        ),
        "safety": DecisionReadySafety(),
        "sellability": DecisionReadySellability(),
        "data_quality": DecisionReadyDataQuality(
            overall_status=DataQuality.VALID,
            completeness=True,
            freshness_status=DataQuality.VALID,
            source_count=1,
            latest_observed_at=OBSERVED_AT,
        ),
        "evidence": (
            DecisionReadyEvidence(
                source_id="market-source",
                observed_at=OBSERVED_AT,
                field="market_snapshot",
                value={"observed_market_state": "bounded"},
                provenance={
                    "observation_id": "market-event",
                    "upstream_state_version": "p02-t08-state",
                },
                observation_id="market-event",
                upstream_state_version="p02-t08-state",
                upstream_state_digest="p02-t08-digest",
            ),
        ),
        "observed_at": OBSERVED_AT,
        "eligibility": DecisionReadyEligibility(
            status=DecisionReadyEligibilityStatus.UNKNOWN,
            reasons=("safety and exit evidence are unknown",),
        ),
    }
    values.update(overrides)
    return DecisionReadyCandidate(**values)


def test_valid_candidate_is_accepted_and_preserves_point_in_time_evidence():
    result = validate_decision_ready_candidate(_candidate())

    assert result.outcome is DecisionReadyOutcome.ACCEPTED
    assert result.quality is DataQuality.VALID
    assert result.accepted is True
    assert result.candidate is not None
    assert result.candidate.evidence[0].observed_at == OBSERVED_AT
    assert result.candidate.market_snapshot.upstream.state_digest == "p02-t08-digest"


@pytest.mark.parametrize(
    "identity, expected",
    [
        (None, DecisionReadyReason.INCOMPLETE_IDENTITY.value),
        (
            DecisionReadyIdentity(
                chain_id="",
                token_identity="mint-A",
                source_id="market-source",
            ),
            DecisionReadyReason.INVALID_IDENTITY.value,
        ),
    ],
)
def test_missing_and_invalid_identity_fail_closed(identity, expected):
    result = validate_decision_ready_candidate(_candidate(identity=identity))

    assert result.accepted is False
    assert expected in result.reasons


@pytest.mark.parametrize(
    "observed_at, expected",
    [
        (None, DecisionReadyOutcome.INCOMPLETE),
        (datetime(2026, 8, 11, 12, 0), DecisionReadyOutcome.INVALID),
    ],
)
def test_missing_and_naive_timestamps_are_classified(observed_at, expected):
    result = validate_decision_ready_candidate(_candidate(observed_at=observed_at))

    assert result.outcome is expected
    assert result.accepted is False


def test_incomplete_market_data_is_not_valid_candidate():
    snapshot = DecisionReadyMarketSnapshot(
        observed_at=OBSERVED_AT,
        values={},
        source_id="market-source",
        upstream=_upstream(),
    )
    result = validate_decision_ready_candidate(
        _candidate(
            market_snapshot=snapshot,
            liquidity=DecisionReadyMarketActivity(),
            market_activity=DecisionReadyMarketActivity(),
        )
    )

    assert result.outcome is DecisionReadyOutcome.INCOMPLETE
    assert DecisionReadyReason.INCOMPLETE_MARKET_DATA.value in result.reasons


def test_stale_data_is_explicitly_rejected():
    result = validate_decision_ready_candidate(
        _candidate(
            data_quality=DecisionReadyDataQuality(
                overall_status=DataQuality.STALE,
                completeness=True,
                freshness_status=DataQuality.STALE,
                source_count=1,
                latest_observed_at=OBSERVED_AT,
                reasons=("fixture is stale",),
            )
        )
    )

    assert result.outcome is DecisionReadyOutcome.STALE
    assert result.quality is DataQuality.STALE
    assert result.accepted is False


def test_invalid_quality_and_eligibility_states_are_rejected():
    invalid_quality = validate_decision_ready_candidate(
        _candidate(
            data_quality=DecisionReadyDataQuality(
                overall_status="NOT_A_QUALITY",
                completeness=True,
                freshness_status=DataQuality.VALID,
                source_count=1,
                latest_observed_at=OBSERVED_AT,
            )
        )
    )
    invalid_eligibility = validate_decision_ready_candidate(
        _candidate(
            eligibility=DecisionReadyEligibility(
                status="BUY_NOW",
                reasons=("not an allowed state",),
            )
        )
    )

    assert invalid_quality.outcome is DecisionReadyOutcome.INVALID
    assert DecisionReadyReason.INVALID_QUALITY.value in invalid_quality.reasons
    assert invalid_eligibility.outcome is DecisionReadyOutcome.INVALID
    assert DecisionReadyReason.INVALID_ELIGIBILITY_STATUS.value in invalid_eligibility.reasons


def test_incomplete_evidence_is_observable():
    result = validate_decision_ready_candidate(_candidate(evidence=()))

    assert result.outcome is DecisionReadyOutcome.INCOMPLETE
    assert DecisionReadyReason.INCOMPLETE_EVIDENCE.value in result.reasons


def test_unknown_safety_and_sellability_remain_unknown_without_decision():
    candidate = _candidate()
    result = validate_decision_ready_candidate(candidate)

    assert result.accepted is True
    assert candidate.safety.safety_status is DecisionReadyAssessmentStatus.UNKNOWN
    assert candidate.sellability.sellability_status is DecisionReadyAssessmentStatus.UNKNOWN
    assert candidate.sellability.exit_evidence_status is DecisionReadyAssessmentStatus.UNKNOWN
    assert candidate.eligibility.status is DecisionReadyEligibilityStatus.UNKNOWN


def test_evidence_and_identity_values_are_immutable():
    candidate = _candidate()

    with pytest.raises(TypeError):
        candidate.evidence[0].provenance["new"] = "value"
    with pytest.raises(TypeError):
        candidate.market_snapshot.values["new"] = "value"