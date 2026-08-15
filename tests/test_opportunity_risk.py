from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone

import pytest

from core.opportunity import (
    CandidateRiskEvaluation,
    CandidateRiskFlag,
    CandidateViabilityStatus,
    NormalizedOpportunityCandidate,
    OpportunityCandidateState,
    P05_T03_CONTRACT_VERSION,
    P05_T03_EVALUATOR_VERSION,
    evaluate_hard_risks,
)
from core.risk.safety_eligibility import EligibilityStatus
from tests.test_opportunity_candidate import (
    REFERENCE_TIME,
    _candidate,
    _eligibility,
)


def _normalized(
    status: EligibilityStatus = EligibilityStatus.ELIGIBLE,
):
    return NormalizedOpportunityCandidate.from_candidate(
        _candidate(eligibility=_eligibility(status))
    )


def test_all_required_evidence_passing_produces_eligible_result():
    result = evaluate_hard_risks(_normalized())

    assert isinstance(result, CandidateRiskEvaluation)
    assert result.viability_status is CandidateViabilityStatus.ELIGIBLE
    assert result.is_eligible is True
    assert result.risk_flags == ()
    assert result.rejection_reason is None
    assert result.contract_version == P05_T03_CONTRACT_VERSION
    assert result.evaluator_version == P05_T03_EVALUATOR_VERSION


def test_one_hard_risk_failure_disqualifies_candidate():
    result = evaluate_hard_risks(_normalized(EligibilityStatus.INELIGIBLE))

    assert result.viability_status is CandidateViabilityStatus.DISQUALIFIED
    assert result.is_disqualified is True
    assert result.rejection_reason == "UPSTREAM_INELIGIBLE"
    assert result.risk_flags == (
        CandidateRiskFlag.UPSTREAM_INELIGIBLE.value,
    )


def test_multiple_upstream_failure_reasons_are_preserved_as_risk_flags():
    eligibility = replace(
        _eligibility(EligibilityStatus.INELIGIBLE),
        reason_codes=("FAIL_FREEZE_AUTHORITY", "FAIL_LP_STATUS"),
    )
    result = evaluate_hard_risks(
        NormalizedOpportunityCandidate.from_candidate(
            _candidate(eligibility=eligibility)
        )
    )

    assert result.viability_status is CandidateViabilityStatus.DISQUALIFIED
    assert result.risk_flags == (
        "FAIL_FREEZE_AUTHORITY",
        "FAIL_LP_STATUS",
        CandidateRiskFlag.UPSTREAM_INELIGIBLE.value,
    )
    assert result.evidence_references == (
        "evidence-1",
    )


def test_unknown_mandatory_evidence_is_never_eligible():
    result = evaluate_hard_risks(_normalized(EligibilityStatus.UNKNOWN))

    assert result.viability_status is CandidateViabilityStatus.INSUFFICIENT_EVIDENCE
    assert result.is_insufficient_evidence is True
    assert result.rejection_reason == "UNKNOWN_UPSTREAM_ELIGIBILITY"
    assert result.risk_flags == (
        CandidateRiskFlag.UNKNOWN_UPSTREAM_ELIGIBILITY.value,
    )


def test_blocked_candidate_with_otherwise_eligible_upstream_fails_closed():
    candidate = replace(
        _candidate(),
        state=OpportunityCandidateState.BLOCKED,
        reason_codes=("NON_CALCULATED_FEATURE",),
    )
    normalized = NormalizedOpportunityCandidate.from_candidate(candidate)

    result = evaluate_hard_risks(normalized)

    assert result.viability_status is CandidateViabilityStatus.INSUFFICIENT_EVIDENCE
    assert result.rejection_reason == "INSUFFICIENT_CRITICAL_EVIDENCE"
    assert result.risk_flags == (
        CandidateRiskFlag.INSUFFICIENT_CRITICAL_EVIDENCE.value,
    )


@pytest.mark.parametrize("invalid", [None, object(), "candidate"])
def test_missing_or_invalid_mandatory_candidate_fails_closed(invalid):
    with pytest.raises(ValueError):
        evaluate_hard_risks(invalid)


def test_malformed_normalized_evidence_is_rejected():
    normalized = _normalized()
    with pytest.raises(ValueError, match="upstream evidence references"):
        replace(
            normalized,
            candidate=replace(
                normalized.candidate,
                eligibility=replace(
                    normalized.eligibility,
                    evidence_references=(),
                ),
            ),
        )


def test_repeated_evaluation_is_deterministic_without_wall_clock_dependency():
    candidate = _normalized(EligibilityStatus.INELIGIBLE)

    first = evaluate_hard_risks(candidate)
    second = evaluate_hard_risks(candidate)

    assert first == second
    assert first.canonical_representation == second.canonical_representation
    assert first.representation_digest == second.representation_digest
    assert first.evaluated_at == REFERENCE_TIME.astimezone(timezone.utc)


def test_explicit_evaluation_time_is_used_and_normalized_to_utc():
    candidate = _normalized()
    explicit = REFERENCE_TIME + timedelta(minutes=2)

    result = evaluate_hard_risks(candidate, evaluated_at=explicit)

    assert result.evaluated_at == explicit


def test_digest_and_evidence_provenance_are_preserved():
    candidate = _normalized()
    result = evaluate_hard_risks(candidate)

    assert result.candidate_id == candidate.candidate_id
    assert result.input_candidate_digest == candidate.representation_digest
    assert result.evidence_references == candidate.eligibility.evidence_references


def test_result_is_immutable_and_has_no_decision_semantics():
    result = evaluate_hard_risks(_normalized())

    with pytest.raises(FrozenInstanceError):
        result.viability_status = CandidateViabilityStatus.DISQUALIFIED
    assert not hasattr(result, "score")
    assert not hasattr(result, "ranking")
    assert not hasattr(result, "decision")
    assert not hasattr(result, "action")
    assert not hasattr(result, "buy")
    assert not hasattr(result, "sell")
    assert not hasattr(result, "hold")
    assert result.is_authoritative is False


def test_upstream_candidate_and_evidence_are_not_mutated():
    candidate = _normalized()
    before = (
        candidate.candidate,
        candidate.eligibility,
        candidate.evidence_references
        if hasattr(candidate, "evidence_references")
        else candidate.eligibility.evidence_references,
        candidate.representation_digest,
    )

    evaluate_hard_risks(candidate)

    assert (
        candidate.candidate,
        candidate.eligibility,
        candidate.eligibility.evidence_references,
        candidate.representation_digest,
    ) == (
        before[0],
        before[1],
        before[2],
        before[3],
    )