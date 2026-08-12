"""Deterministic, non-authoritative eligibility derivation for P03-T03.

This module consumes only the already-evaluated P03-T02 result.  It does not
collect or reevaluate evidence, authorize decisions, or perform external I/O.
"""

from __future__ import annotations

from core.risk.safety_evaluation import SafetyEvaluationResult
from core.risk.safety_evidence import (
    DerivedEligibilityOutput,
    EligibilityStatus,
    SafetyStatus,
)


P03_T03_EVALUATOR_ID = "p03-t03-eligibility-derivation"

REASON_ALL_DOMAINS_PASS = "ALL_DOMAINS_PASS"
REASON_FAIL_DOMAIN = "FAIL_DOMAIN"
REASON_UNKNOWN_DOMAIN = "UNKNOWN_DOMAIN"
REASON_NO_DOMAIN_RESULT = "NO_DOMAIN_RESULT"


def derive_token_eligibility(
    evaluation: SafetyEvaluationResult,
) -> DerivedEligibilityOutput:
    """Derive a fail-closed eligibility outcome from a T02 evaluation."""

    if not isinstance(evaluation, SafetyEvaluationResult):
        raise ValueError("evaluation must be a SafetyEvaluationResult")

    statuses = tuple(evaluation.domain_results.values())
    if SafetyStatus.FAIL in statuses:
        status = EligibilityStatus.INELIGIBLE
        reason_code = REASON_FAIL_DOMAIN
    elif not statuses:
        status = EligibilityStatus.UNKNOWN
        reason_code = REASON_NO_DOMAIN_RESULT
    elif SafetyStatus.UNKNOWN in statuses:
        status = EligibilityStatus.UNKNOWN
        reason_code = REASON_UNKNOWN_DOMAIN
    else:
        status = EligibilityStatus.ELIGIBLE
        reason_code = REASON_ALL_DOMAINS_PASS

    return DerivedEligibilityOutput(
        status=status,
        evaluator_id=P03_T03_EVALUATOR_ID,
        evaluated_at=evaluation.evaluation_timestamp,
        evidence_references=evaluation.evidence_references,
        contract_version=evaluation.contract_version,
        reason_codes=(reason_code,),
    )


derive_eligibility = derive_token_eligibility
