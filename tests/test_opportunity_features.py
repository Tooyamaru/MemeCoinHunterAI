from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone

import pytest

from core.features import FeatureCalculationStatus
from core.opportunity import (
    CandidateFeatureEvaluation,
    CandidateViabilityStatus,
    NormalizedOpportunityCandidate,
    P05_T04_CONTRACT_VERSION,
    P05_T04_EVALUATOR_VERSION,
    evaluate_candidate_features,
    evaluate_hard_risks,
)
from core.risk.safety_eligibility import EligibilityStatus
from tests.test_opportunity_candidate import (
    REFERENCE_TIME,
    _candidate,
    _eligibility,
    _feature_snapshot,
)


def _inputs(status: EligibilityStatus = EligibilityStatus.ELIGIBLE):
    candidate = _candidate(
        eligibility=_eligibility(status),
        feature_snapshots=[_feature_snapshot()],
    )
    normalized = NormalizedOpportunityCandidate.from_candidate(candidate)
    return normalized, evaluate_hard_risks(normalized)


def test_eligible_candidate_preserves_authorized_feature_and_provenance():
    candidate, risk = _inputs()
    result = evaluate_candidate_features(candidate, risk)

    assert isinstance(result, CandidateFeatureEvaluation)
    assert result.risk_evaluation is risk
    assert result.feature_snapshots is candidate.feature_snapshots
    assert result.signal_snapshot is candidate.signal_snapshot
    assert result.input_candidate_digest == candidate.representation_digest
    assert result.evaluator_version == P05_T04_EVALUATOR_VERSION
    assert result.contract_version == P05_T04_CONTRACT_VERSION


@pytest.mark.parametrize(
    "status",
    [EligibilityStatus.INELIGIBLE, EligibilityStatus.UNKNOWN],
)
def test_closed_p05_t03_gates_fail_closed_without_admitting_features(status):
    candidate, risk = _inputs(status)

    assert risk.viability_status in {
        CandidateViabilityStatus.DISQUALIFIED,
        CandidateViabilityStatus.INSUFFICIENT_EVIDENCE,
    }
    with pytest.raises(ValueError, match="viability gate is closed"):
        evaluate_candidate_features(candidate, risk)


def test_empty_feature_snapshots_remain_empty_without_synthetic_status_or_reasons():
    candidate = NormalizedOpportunityCandidate.from_candidate(_candidate())
    risk = evaluate_hard_risks(candidate)
    result = evaluate_candidate_features(candidate, risk)

    assert result.feature_snapshots == ()
    assert not hasattr(result, "reason_codes")
    assert not hasattr(result, "status")


def test_non_calculated_authorized_snapshot_is_not_admitted_when_gate_is_closed():
    snapshot = _feature_snapshot()
    snapshot = replace(
        snapshot,
        status=FeatureCalculationStatus.UNKNOWN,
        value=None,
        value_unit=None,
        reason_codes=("INSUFFICIENT_PRICE_OBSERVATIONS",),
    )
    candidate = _candidate(feature_snapshots=[snapshot])
    normalized = NormalizedOpportunityCandidate.from_candidate(candidate)
    risk = evaluate_hard_risks(normalized)
    assert risk.viability_status is CandidateViabilityStatus.INSUFFICIENT_EVIDENCE
    with pytest.raises(ValueError, match="viability gate is closed"):
        evaluate_candidate_features(normalized, risk)


def test_unauthorized_feature_pair_is_not_admitted_when_gate_is_closed():
    snapshot = replace(
        _feature_snapshot(),
        status=FeatureCalculationStatus.UNSUPPORTED,
        reason_codes=("UNSUPPORTED_FEATURE",),
        feature_id="volume",
        feature_version="volume-v1",
        value=None,
        value_unit=None,
    )
    candidate = _candidate(feature_snapshots=[snapshot])
    normalized = NormalizedOpportunityCandidate.from_candidate(candidate)
    risk = evaluate_hard_risks(normalized)
    assert risk.viability_status is CandidateViabilityStatus.INSUFFICIENT_EVIDENCE
    with pytest.raises(ValueError, match="viability gate is closed"):
        evaluate_candidate_features(normalized, risk)


def test_malformed_snapshot_provenance_still_fails_closed():
    malformed = _feature_snapshot()
    object.__setattr__(
        malformed,
        "snapshot_linkage",
        replace(
            malformed.snapshot_linkage,
            feature_representation_digest="tampered-digest",
        ),
    )
    candidate = _candidate(feature_snapshots=[malformed])
    normalized = NormalizedOpportunityCandidate.from_candidate(candidate)
    risk = evaluate_hard_risks(normalized)

    with pytest.raises(ValueError, match="canonical"):
        evaluate_candidate_features(normalized, risk)


def test_identity_and_digest_mismatches_fail_closed():
    candidate, risk = _inputs()

    with pytest.raises(ValueError, match="identity"):
        evaluate_candidate_features(
            candidate,
            replace(risk, candidate_id="other-candidate"),
        )
    with pytest.raises(ValueError, match="digest"):
        evaluate_candidate_features(
            candidate,
            replace(risk, input_candidate_digest="wrong-digest"),
        )


def test_repeated_evaluation_is_deterministic_and_uses_reference_time_by_default():
    candidate, risk = _inputs()
    first = evaluate_candidate_features(candidate, risk)
    second = evaluate_candidate_features(candidate, risk)

    assert first == second
    assert first.evaluated_at == REFERENCE_TIME.astimezone(timezone.utc)
    assert first.canonical_representation == second.canonical_representation
    assert first.representation_digest == second.representation_digest


def test_explicit_evaluation_time_is_normalized_without_changing_upstream_times():
    candidate, risk = _inputs()
    explicit = REFERENCE_TIME + timedelta(minutes=2)
    result = evaluate_candidate_features(candidate, risk, evaluated_at=explicit)

    assert result.evaluated_at == explicit
    assert result.reference_time == candidate.reference_time
    assert result.feature_snapshots[0].reference_time != result.evaluated_at


def test_result_is_immutable_and_preserves_upstream_objects():
    candidate, risk = _inputs()
    before = (
        candidate.representation_digest,
        risk.canonical_representation,
        candidate.signal_snapshot.canonical_representation,
        candidate.feature_snapshots[0].canonical_representation,
    )
    result = evaluate_candidate_features(candidate, risk)

    with pytest.raises(FrozenInstanceError):
        result.candidate_id = "changed"
    assert result.risk_evaluation is risk
    assert result.signal_snapshot is candidate.signal_snapshot
    assert (
        candidate.representation_digest,
        risk.canonical_representation,
        candidate.signal_snapshot.canonical_representation,
        candidate.feature_snapshots[0].canonical_representation,
    ) == before