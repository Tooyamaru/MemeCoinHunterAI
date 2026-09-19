"""Produce canonical P04 inputs from already-admitted upstream evidence.

This module connects existing P02 and P04 producers to the canonical P04→P05
composition. It does not collect provider data, infer signal policy, create
historical observations, or define a second evaluator.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping

from core.data.contracts import FreshnessPolicy
from core.data.market_intelligence import AcceptedMarketIntelligenceObservation
from core.features.price_features import (
    FeatureCalculationContext,
    FeatureCalculationResult,
    calculate_price_acceleration,
    calculate_price_velocity,
)
from core.opportunity.p04_p05_composition import (
    CanonicalP04ToP05Composition,
    compose_canonical_p04_to_p05,
)
from core.risk.safety_evidence import DerivedEligibilityOutput
from core.signals.signal_aggregation import (
    SignalEvidenceAggregationResult,
    aggregate_signal_evidence,
)
from core.signals.signal_evaluation import (
    SignalEvidenceEvaluationResult,
    evaluate_signal_evidence,
)
from core.signals.signal_evidence import SignalEvidenceCollection
from core.signals.signal_normalization import (
    NormalizedSignalEvidenceCollection,
    normalize_signal_evidence,
)
from core.signals.signal_quality import (
    SignalEvidenceQualityResult,
    assess_signal_evidence_quality,
)


@dataclass(frozen=True)
class CanonicalP04ToP05EvidenceInputs:
    """P04 outputs produced before the existing P05 composition boundary."""

    normalized_signal_evidence: NormalizedSignalEvidenceCollection
    signal_quality: SignalEvidenceQualityResult
    signal_evaluation: SignalEvidenceEvaluationResult
    signal_aggregation: SignalEvidenceAggregationResult
    feature_results: tuple[FeatureCalculationResult, ...]


def produce_canonical_p04_to_p05_inputs(
    *,
    signal_evidence: SignalEvidenceCollection,
    market_observations: Iterable[AcceptedMarketIntelligenceObservation],
    reference_time: datetime,
    freshness_policy: FreshnessPolicy,
    evaluation_id: str | None = None,
    processing_time: datetime | None = None,
) -> CanonicalP04ToP05EvidenceInputs:
    """Run existing P04 producers over validated upstream evidence.

    The signal collection is the already-admitted P04-T01 evidence boundary;
    this function deliberately does not derive signal types or statuses from
    market data. The market observations are P02-T09 values used by the
    already-authorized P04-T09 price feature calculators.
    """

    normalized_signal_evidence = normalize_signal_evidence(signal_evidence)
    signal_quality = assess_signal_evidence_quality(normalized_signal_evidence)
    signal_evaluation = evaluate_signal_evidence(
        normalized_signal_evidence,
        signal_quality,
    )
    signal_aggregation = aggregate_signal_evidence(signal_evaluation)

    observations = tuple(market_observations)
    feature_context = FeatureCalculationContext(
        reference_time=reference_time,
        freshness_policy=freshness_policy,
        evaluation_id=evaluation_id,
        processing_time=processing_time,
    )
    feature_results = (
        calculate_price_velocity(observations, context=feature_context),
        calculate_price_acceleration(observations, context=feature_context),
    )

    return CanonicalP04ToP05EvidenceInputs(
        normalized_signal_evidence=normalized_signal_evidence,
        signal_quality=signal_quality,
        signal_evaluation=signal_evaluation,
        signal_aggregation=signal_aggregation,
        feature_results=feature_results,
    )


def produce_canonical_p04_to_p05(
    *,
    candidate_id: str,
    chain_id: str,
    token_identity: str,
    reference_time: datetime,
    eligibility: DerivedEligibilityOutput,
    signal_evidence: SignalEvidenceCollection,
    market_observations: Iterable[AcceptedMarketIntelligenceObservation],
    freshness_policy: FreshnessPolicy,
    analytical_context: Mapping[str, Any] | None = None,
    evaluation_id: str | None = None,
    processing_time: datetime | None = None,
    evaluated_at: datetime | None = None,
) -> CanonicalP04ToP05Composition:
    """Produce P04 inputs and execute the existing canonical P05 chain."""

    inputs = produce_canonical_p04_to_p05_inputs(
        signal_evidence=signal_evidence,
        market_observations=market_observations,
        reference_time=reference_time,
        freshness_policy=freshness_policy,
        evaluation_id=evaluation_id,
        processing_time=processing_time,
    )
    return compose_canonical_p04_to_p05(
        candidate_id=candidate_id,
        chain_id=chain_id,
        token_identity=token_identity,
        reference_time=reference_time,
        eligibility=eligibility,
        signal_aggregation=inputs.signal_aggregation,
        feature_results=inputs.feature_results,
        analytical_context=analytical_context,
        evaluated_at=evaluated_at,
    )


__all__ = [
    "CanonicalP04ToP05EvidenceInputs",
    "produce_canonical_p04_to_p05",
    "produce_canonical_p04_to_p05_inputs",
]