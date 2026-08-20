from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from core.features import (
    FeatureCalculationStatus,
    calculate_price_acceleration,
    create_feature_calculation_snapshot,
)
from core.opportunity import (
    CandidateFeatureEvaluation,
    CandidateViabilityStatus,
    DEFAULT_SCORING_RULESET,
    OpportunityScore,
    P05_T05_CONTRACT_VERSION,
    P05_T05_EVALUATOR_VERSION,
    evaluate_candidate_features,
    evaluate_hard_risks,
    evaluate_opportunity_score,
    NormalizedOpportunityCandidate,
)
from tests.test_opportunity_candidate import (
    REFERENCE_TIME,
    _candidate,
    _context,
    _eligibility,
    _feature_snapshot,
    _price,
)


def _evaluation() -> CandidateFeatureEvaluation:
    velocity = _feature_snapshot()
    acceleration = create_feature_calculation_snapshot(
        calculate_price_acceleration(
            [_price(0, 10), _price(1, 12), _price(2, 15)],
            context=_context(reference_time=datetime(2026, 8, 11, 12, 0, 10, tzinfo=timezone.utc)),
        )
    )
    candidate = _candidate(
        eligibility=_eligibility(),
        feature_snapshots=[velocity, acceleration],
    )
    normalized = NormalizedOpportunityCandidate.from_candidate(candidate)
    return evaluate_candidate_features(
        normalized,
        evaluate_hard_risks(normalized),
    )


def test_score_preserves_t04_and_calculates_versioned_bounded_score():
    evaluation = _evaluation()

    result = evaluate_opportunity_score(evaluation)

    assert isinstance(result, OpportunityScore)
    assert result.feature_evaluation is evaluation
    assert result.input_feature_evaluation_digest == evaluation.digest
    assert result.ruleset is DEFAULT_SCORING_RULESET
    assert result.evaluator_version == P05_T05_EVALUATOR_VERSION
    assert result.contract_version == P05_T05_CONTRACT_VERSION
    assert Decimal("0") <= result.score <= Decimal("100")
    assert result.score == Decimal("80.55555555555555555555555556")


def test_score_is_deterministic_and_defaults_to_reference_time():
    evaluation = _evaluation()

    first = evaluate_opportunity_score(evaluation)
    second = evaluate_opportunity_score(evaluation)

    assert first == second
    assert first.evaluated_at == REFERENCE_TIME
    assert first.canonical_representation == second.canonical_representation
    assert first.digest == second.digest


def test_score_requires_both_calculated_authorized_features():
    candidate = _candidate(feature_snapshots=[_feature_snapshot()])
    normalized = NormalizedOpportunityCandidate.from_candidate(candidate)
    evaluation = evaluate_candidate_features(
        normalized,
        evaluate_hard_risks(normalized),
    )

    with pytest.raises(ValueError, match="required scoreable"):
        evaluate_opportunity_score(evaluation)


def test_score_rejects_non_calculated_required_feature():
    evaluation = _evaluation()
    tampered = replace(evaluation.feature_snapshots[0])
    object.__setattr__(tampered, "status", FeatureCalculationStatus.UNKNOWN)
    object.__setattr__(tampered, "value", None)
    object.__setattr__(tampered, "value_unit", None)
    object.__setattr__(tampered, "reason_codes", ("INSUFFICIENT_PRICE_OBSERVATIONS",))
    object.__setattr__(
        evaluation,
        "feature_snapshots",
        (tampered, evaluation.feature_snapshots[1]),
    )

    with pytest.raises(ValueError, match="scoreable feature snapshot is not calculated"):
        evaluate_opportunity_score(evaluation)


def test_score_rejects_closed_t03_gate_and_direct_t04_tampering():
    candidate = _candidate(
        eligibility=_eligibility(),
        feature_snapshots=[],
    )
    normalized = NormalizedOpportunityCandidate.from_candidate(candidate)
    evaluation = evaluate_candidate_features(
        normalized,
        evaluate_hard_risks(normalized),
    )
    tampered = replace(evaluation)
    object.__setattr__(
        tampered.risk_evaluation,
        "viability_status",
        CandidateViabilityStatus.DISQUALIFIED,
    )
    object.__setattr__(tampered.risk_evaluation, "rejection_reason", "closed")

    with pytest.raises(ValueError):
        evaluate_opportunity_score(tampered)


def test_score_output_is_immutable():
    result = evaluate_opportunity_score(_evaluation())

    with pytest.raises(FrozenInstanceError):
        result.score = Decimal("1")