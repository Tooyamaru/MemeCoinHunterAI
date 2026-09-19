"""Canonical deterministic composition of the P04 inputs into the P05 chain.

This module is intentionally an assembly boundary.  It creates the required
P04 snapshots from already-validated P04 results and then invokes the actual
P05-T01 through P05-T05 contracts.  It does not create provider evidence,
relax validation, score independently, or perform I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from core.features.feature_snapshot import (
    FeatureCalculationSnapshot,
    snapshot_feature_calculation,
)
from core.features.price_features import FeatureCalculationResult
from core.opportunity.opportunity_candidate import (
    OpportunityCandidate,
    create_opportunity_candidate,
)
from core.opportunity.opportunity_features import (
    CandidateFeatureEvaluation,
    evaluate_candidate_features,
)
from core.opportunity.opportunity_normalization import (
    NormalizedOpportunityCandidate,
    normalize_opportunity_candidate,
)
from core.opportunity.opportunity_risk import (
    CandidateRiskEvaluation,
    evaluate_hard_risks,
)
from core.opportunity.opportunity_score import (
    OpportunityScore,
    evaluate_opportunity_score,
)
from core.risk.safety_evidence import DerivedEligibilityOutput
from core.signals.signal_aggregation import SignalEvidenceAggregationResult
from core.signals.signal_snapshot import (
    SignalEvidenceSnapshot,
    snapshot_signal_evidence,
)


@dataclass(frozen=True)
class CanonicalP04ToP05Composition:
    """All validated outputs produced by one deterministic P04→P05 run."""

    signal_snapshot: SignalEvidenceSnapshot
    feature_snapshots: tuple[FeatureCalculationSnapshot, ...]
    candidate: OpportunityCandidate
    normalized_candidate: NormalizedOpportunityCandidate
    risk_evaluation: CandidateRiskEvaluation
    feature_evaluation: CandidateFeatureEvaluation
    score: OpportunityScore

    @property
    def candidate_state(self) -> str:
        """Return the existing P05-T01 state without introducing new status."""

        return self.candidate.state.value

    @property
    def viability_status(self) -> str:
        """Return the existing P05-T03 viability status."""

        return self.risk_evaluation.viability_status.value

    @property
    def score_value(self):
        """Return the P05-T05 Decimal score."""

        return self.score.score

    @property
    def provenance_digests(self) -> tuple[str, ...]:
        """Return the candidate's preserved upstream representation digests."""

        return self.candidate.upstream_representation_digests

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        """Expose the final score representation as the composition record."""

        return self.score.canonical_representation

    @property
    def digest(self) -> str:
        return self.score.digest


def compose_canonical_p04_to_p05(
    *,
    candidate_id: str,
    chain_id: str,
    token_identity: str,
    reference_time: datetime,
    eligibility: DerivedEligibilityOutput,
    signal_aggregation: SignalEvidenceAggregationResult,
    feature_results: tuple[FeatureCalculationResult, ...]
    | list[FeatureCalculationResult],
    analytical_context: Mapping[str, Any] | None = None,
    evaluated_at: datetime | None = None,
) -> CanonicalP04ToP05Composition:
    """Compose canonical P04 snapshots and execute the real P05 chain.

    Invalid, incomplete, ineligible, non-canonical, or mismatched inputs are
    allowed to raise the existing boundary exceptions.  In particular, this
    function never turns a blocked P03/P04/P05 result into a successful score.
    The default evaluation timestamp is inherited from the existing P05
    evaluators, which is the candidate reference time and does not read a
    system clock.
    """

    signal_snapshot = snapshot_signal_evidence(signal_aggregation)
    feature_snapshots = tuple(
        snapshot_feature_calculation(result) for result in feature_results
    )

    candidate = create_opportunity_candidate(
        candidate_id=candidate_id,
        chain_id=chain_id,
        token_identity=token_identity,
        reference_time=reference_time,
        eligibility=eligibility,
        signal_snapshot=signal_snapshot,
        feature_snapshots=feature_snapshots,
        analytical_context=analytical_context,
    )
    normalized_candidate = normalize_opportunity_candidate(candidate)
    risk_evaluation = evaluate_hard_risks(
        normalized_candidate,
        evaluated_at=evaluated_at,
    )
    feature_evaluation = evaluate_candidate_features(
        normalized_candidate,
        risk_evaluation,
        evaluated_at=evaluated_at,
    )
    score = evaluate_opportunity_score(
        feature_evaluation,
        evaluated_at=evaluated_at,
    )

    return CanonicalP04ToP05Composition(
        signal_snapshot=signal_snapshot,
        feature_snapshots=candidate.feature_snapshots,
        candidate=candidate,
        normalized_candidate=normalized_candidate,
        risk_evaluation=risk_evaluation,
        feature_evaluation=feature_evaluation,
        score=score,
    )


compose_p04_to_p05 = compose_canonical_p04_to_p05


__all__ = [
    "CanonicalP04ToP05Composition",
    "compose_canonical_p04_to_p05",
    "compose_p04_to_p05",
]