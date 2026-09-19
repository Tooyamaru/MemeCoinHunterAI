from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from core.data.contracts import DataQuality, FreshnessPolicy
from core.data.market_intelligence import (
    MarketIntelligenceCategory,
    MarketIntelligenceOutcome,
    MarketIntelligenceProcessor,
)
from core.opportunity import (
    P05_T04_EVALUATOR_VERSION,
    P05_T05_EVALUATOR_VERSION,
    produce_canonical_p04_to_p05,
    produce_canonical_p04_to_p05_inputs,
)
from core.risk.safety_evidence import EligibilityStatus
from core.signals.signal_aggregation import SignalAggregationStatus
from core.signals.signal_evaluation import SignalEvaluationStatus
from core.signals.signal_quality import SignalQualityStatus
from tests.test_market_intelligence import _observation, _upstream
from tests.test_opportunity_candidate import REFERENCE_TIME, _eligibility
from tests.test_signal_normalization import _evidence
from core.signals.signal_evidence import SignalEvidenceCollection


UTC = timezone.utc
FRESHNESS_POLICY = FreshnessPolicy(stale_after=timedelta(minutes=1))


def _signal_evidence() -> SignalEvidenceCollection:
    observed_at = REFERENCE_TIME - timedelta(minutes=1)
    return SignalEvidenceCollection.from_evidence(
        [
            _evidence(
                observed_at=observed_at,
                evidence_reference="signal-1",
            )
        ]
    )


def _accepted_price_observations():
    processor = MarketIntelligenceProcessor()
    observations = []
    for sequence, (offset, value) in enumerate(
        ((0, "10"), (1, "11"), (2, "13")),
        start=1,
    ):
        observed_at = REFERENCE_TIME - timedelta(seconds=5 - offset)
        candidate = replace(
            _observation(
                sequence=sequence,
                source_event_id=f"price-event-{sequence}",
            ),
            value=value,
            observation_time=observed_at,
            received_time=observed_at + timedelta(seconds=1),
            reference_time=REFERENCE_TIME,
            data_age=REFERENCE_TIME - observed_at,
            upstream=_upstream(),
            observation_metadata={
                "measurement": "price",
                "unit": "USD",
                "quote_asset": "USDC",
            },
        )
        result = processor.process(candidate)
        assert result.outcome in {
            MarketIntelligenceOutcome.REPRESENTED,
            MarketIntelligenceOutcome.UPDATED,
        }
        assert result.accepted is True
        assert result.observation is not None
        observations.append(result.observation)
    return tuple(observations)


def _produce(**overrides):
    values = {
        "candidate_id": "producer-candidate",
        "chain_id": "solana",
        "token_identity": "mint-A",
        "reference_time": REFERENCE_TIME,
        "eligibility": _eligibility(),
        "signal_evidence": _signal_evidence(),
        "market_observations": _accepted_price_observations(),
        "freshness_policy": FRESHNESS_POLICY,
    }
    values.update(overrides)
    return produce_canonical_p04_to_p05(**values)


def test_producer_runs_p02_to_p04_to_p05_with_actual_existing_contracts():
    result = _produce()

    assert result.candidate_state == "VALID"
    assert result.viability_status == EligibilityStatus.ELIGIBLE.value
    assert result.feature_evaluation.evaluator_version == P05_T04_EVALUATOR_VERSION
    assert result.score.evaluator_version == P05_T05_EVALUATOR_VERSION
    assert result.feature_evaluation.feature_snapshots[0].value == Decimal("2")
    assert result.feature_evaluation.feature_snapshots[1].value == Decimal("1")
    assert result.score.score == Decimal("80.55555555555555555555555556")
    assert result.signal_snapshot.evidence_references == ("signal-1",)
    assert result.feature_snapshots[0].inputs[0].received_time != (
        result.feature_snapshots[0].inputs[0].observation_time
    )
    assert all(
        reference.state_digest == "p02-t08-state-digest"
        for snapshot in result.feature_snapshots
        for reference in snapshot.upstream_references
    )


def test_producer_exposes_actual_p04_intermediate_results_and_is_deterministic():
    observations = _accepted_price_observations()
    first = produce_canonical_p04_to_p05_inputs(
        signal_evidence=_signal_evidence(),
        market_observations=observations,
        reference_time=REFERENCE_TIME,
        freshness_policy=FRESHNESS_POLICY,
    )
    second = produce_canonical_p04_to_p05_inputs(
        signal_evidence=_signal_evidence(),
        market_observations=observations,
        reference_time=REFERENCE_TIME,
        freshness_policy=FRESHNESS_POLICY,
    )

    assert first == second
    assert first.signal_quality.quality_status is SignalQualityStatus.ACCEPTABLE
    assert first.signal_evaluation.evaluation_status is SignalEvaluationStatus.EVALUATED
    assert first.signal_aggregation.aggregation_status is SignalAggregationStatus.AGGREGATED
    assert first.feature_results[0].value == Decimal("2")
    assert first.feature_results[1].value == Decimal("1")


def test_missing_history_fails_closed_instead_of_becoming_a_favorable_default():
    incomplete = _accepted_price_observations()[:1]

    with pytest.raises(ValueError, match="P05-T03 viability gate is closed"):
        _produce(market_observations=incomplete)


def test_identity_mismatch_fails_closed_before_scoring():
    observations = list(_accepted_price_observations())
    observations[1] = replace(
        observations[1],
        token_identity="different-token",
    )

    with pytest.raises(ValueError, match="P05-T03 viability gate is closed"):
        _produce(market_observations=observations)


def test_invalid_provenance_fails_closed_before_scoring():
    observations = list(_accepted_price_observations())
    observations[1] = replace(
        observations[1],
        provenance=replace(
            observations[1].provenance,
            source_id="different-source",
        ),
    )

    with pytest.raises(ValueError, match="P05-T03 viability gate is closed"):
        _produce(market_observations=observations)


def test_stale_evidence_fails_closed_before_scoring():
    observations = list(_accepted_price_observations())
    observations[1] = replace(observations[1], quality=DataQuality.STALE)

    with pytest.raises(ValueError, match="P05-T03 viability gate is closed"):
        _produce(market_observations=observations)


def test_contradictory_evidence_fails_closed_before_scoring():
    observations = list(_accepted_price_observations())
    observations[1] = replace(
        observations[1],
        observation_id=observations[0].observation_id,
        value="99",
    )

    with pytest.raises(ValueError, match="P05-T03 viability gate is closed"):
        _produce(market_observations=observations)


def test_unknown_safety_cannot_become_eligible():
    with pytest.raises(ValueError, match="P05-T03 viability gate is closed"):
        _produce(eligibility=_eligibility(EligibilityStatus.UNKNOWN))