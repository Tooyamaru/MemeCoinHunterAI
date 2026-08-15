"""Deterministic P05-T03 hard-risk and disqualification boundary.

This boundary consumes only the normalized P05-T02 candidate.  It does not
collect or reevaluate safety evidence, score, rank, decide, authorize, execute,
or perform external I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.opportunity.opportunity_candidate import (
    OpportunityCandidateState,
    OpportunityUpstreamReference,
)
from core.opportunity.opportunity_normalization import (
    NormalizedOpportunityCandidate,
    P05_T02_CONTRACT_VERSION,
)
from core.risk.safety_evidence import (
    DerivedEligibilityOutput,
    EligibilityStatus,
)


P05_T03_CONTRACT_VERSION = "p05-t03-v1"
P05_T03_EVALUATOR_VERSION = "p05-t03-rules-v1"


class CandidateViabilityStatus(StrEnum):
    """Hard-risk outcomes without decision or execution meaning."""

    ELIGIBLE = "ELIGIBLE"
    DISQUALIFIED = "DISQUALIFIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CandidateRiskFlag(StrEnum):
    """Boundary-level reasons preserved in a risk evaluation."""

    UPSTREAM_INELIGIBLE = "UPSTREAM_INELIGIBLE"
    UNKNOWN_UPSTREAM_ELIGIBILITY = "UNKNOWN_UPSTREAM_ELIGIBILITY"
    INSUFFICIENT_CRITICAL_EVIDENCE = "INSUFFICIENT_CRITICAL_EVIDENCE"


@dataclass(frozen=True)
class CandidateRiskEvaluation:
    """Immutable, versioned result of the P05-T03 hard-risk boundary."""

    candidate_id: str
    evaluated_at: datetime
    input_candidate_digest: str
    risk_flags: tuple[str, ...]
    viability_status: CandidateViabilityStatus
    rejection_reason: str | None
    evidence_references: tuple[str, ...]
    evaluator_version: str = P05_T03_EVALUATOR_VERSION
    contract_version: str = P05_T03_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        evaluated_at = _to_utc(self.evaluated_at, "evaluated_at")
        object.__setattr__(self, "evaluated_at", evaluated_at)
        _require_text(self.input_candidate_digest, "input_candidate_digest")
        _require_text(self.evaluator_version, "evaluator_version")
        _require_text(self.contract_version, "contract_version")
        if self.evaluator_version != P05_T03_EVALUATOR_VERSION:
            raise ValueError("unsupported P05-T03 evaluator version")
        if self.contract_version != P05_T03_CONTRACT_VERSION:
            raise ValueError("unsupported P05-T03 contract version")

        try:
            status = (
                self.viability_status
                if isinstance(self.viability_status, CandidateViabilityStatus)
                else CandidateViabilityStatus(self.viability_status)
            )
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported viability status") from error
        object.__setattr__(self, "viability_status", status)

        flags = tuple(self.risk_flags)
        if any(not _is_text(value) for value in flags):
            raise ValueError("risk_flags must contain non-empty strings")
        object.__setattr__(self, "risk_flags", tuple(sorted(dict.fromkeys(flags))))

        references = tuple(self.evidence_references)
        if any(not _is_text(value) for value in references):
            raise ValueError(
                "evidence_references must contain non-empty strings"
            )
        object.__setattr__(
            self,
            "evidence_references",
            tuple(sorted(dict.fromkeys(references))),
        )

        if self.rejection_reason is not None:
            _require_text(self.rejection_reason, "rejection_reason")
        if status is CandidateViabilityStatus.ELIGIBLE:
            if self.rejection_reason is not None:
                raise ValueError(
                    "eligible evaluation cannot contain rejection_reason"
                )
        elif self.rejection_reason is None:
            raise ValueError(
                "non-eligible evaluation requires rejection_reason"
            )

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return MappingProxyType(
            {
                "candidate_id": self.candidate_id,
                "evaluated_at": self.evaluated_at.isoformat(),
                "input_candidate_digest": self.input_candidate_digest,
                "risk_flags": self.risk_flags,
                "viability_status": self.viability_status.value,
                "rejection_reason": self.rejection_reason,
                "evidence_references": self.evidence_references,
                "evaluator_version": self.evaluator_version,
                "contract_version": self.contract_version,
            }
        )

    @property
    def deterministic_representation(self) -> Mapping[str, Any]:
        return self.canonical_representation

    @property
    def representation_digest(self) -> str:
        return _digest(self.canonical_representation)

    @property
    def digest(self) -> str:
        return self.representation_digest

    @property
    def is_eligible(self) -> bool:
        return self.viability_status is CandidateViabilityStatus.ELIGIBLE

    @property
    def is_disqualified(self) -> bool:
        return self.viability_status is CandidateViabilityStatus.DISQUALIFIED

    @property
    def is_insufficient_evidence(self) -> bool:
        return self.viability_status is CandidateViabilityStatus.INSUFFICIENT_EVIDENCE

    @property
    def is_authoritative(self) -> bool:
        return False


def evaluate_hard_risks(
    candidate: NormalizedOpportunityCandidate,
    *,
    evaluated_at: datetime | None = None,
) -> CandidateRiskEvaluation:
    """Evaluate one normalized candidate without external or wall-clock input."""

    _validate_normalized_candidate(candidate)
    timestamp = candidate.reference_time if evaluated_at is None else evaluated_at
    timestamp = _to_utc(timestamp, "evaluated_at")

    eligibility = candidate.eligibility
    status = eligibility.status
    if status is EligibilityStatus.INELIGIBLE:
        viability = CandidateViabilityStatus.DISQUALIFIED
        base_flag = CandidateRiskFlag.UPSTREAM_INELIGIBLE.value
        reason = "UPSTREAM_INELIGIBLE"
        preserved_reasons = eligibility.reason_codes
    elif status is EligibilityStatus.UNKNOWN:
        viability = CandidateViabilityStatus.INSUFFICIENT_EVIDENCE
        base_flag = CandidateRiskFlag.UNKNOWN_UPSTREAM_ELIGIBILITY.value
        reason = "UNKNOWN_UPSTREAM_ELIGIBILITY"
        preserved_reasons = eligibility.reason_codes
    elif status is EligibilityStatus.ELIGIBLE:
        if candidate.state is OpportunityCandidateState.VALID:
            viability = CandidateViabilityStatus.ELIGIBLE
            base_flag = None
            reason = None
            preserved_reasons = ()
        else:
            viability = CandidateViabilityStatus.INSUFFICIENT_EVIDENCE
            base_flag = CandidateRiskFlag.INSUFFICIENT_CRITICAL_EVIDENCE.value
            reason = "INSUFFICIENT_CRITICAL_EVIDENCE"
            preserved_reasons = candidate.reason_codes
    else:
        raise ValueError("unsupported upstream eligibility status")

    flags = ()
    if base_flag is not None:
        flags = _risk_flags(base_flag, preserved_reasons)

    return CandidateRiskEvaluation(
        candidate_id=candidate.candidate_id,
        evaluated_at=timestamp,
        input_candidate_digest=candidate.representation_digest,
        risk_flags=flags,
        viability_status=viability,
        rejection_reason=reason,
        evidence_references=eligibility.evidence_references,
    )


def _validate_normalized_candidate(
    candidate: NormalizedOpportunityCandidate,
) -> None:
    if not isinstance(candidate, NormalizedOpportunityCandidate):
        raise ValueError(
            "candidate must be a NormalizedOpportunityCandidate"
        )
    if candidate.contract_version != P05_T02_CONTRACT_VERSION:
        raise ValueError("unsupported P05-T02 candidate contract version")
    if not _is_text(candidate.candidate_id):
        raise ValueError("candidate_id is required")
    if not _is_text(candidate.candidate_representation_digest):
        raise ValueError("candidate digest is required")
    if not isinstance(candidate.state, OpportunityCandidateState):
        raise ValueError("candidate state is invalid")
    if not isinstance(candidate.eligibility, DerivedEligibilityOutput):
        raise ValueError("candidate eligibility is invalid")
    if not isinstance(candidate.eligibility.status, EligibilityStatus):
        raise ValueError("candidate eligibility status is invalid")
    if not candidate.eligibility.evidence_references:
        raise ValueError("mandatory evidence references are missing")
    if any(
        not _is_text(value)
        for value in candidate.eligibility.evidence_references
    ):
        raise ValueError("mandatory evidence references are invalid")
    references = candidate.upstream_references
    if not references or not all(
        isinstance(value, OpportunityUpstreamReference) for value in references
    ):
        raise ValueError("mandatory upstream references are invalid")
    if (
        candidate.canonical_representation
        != candidate.deterministic_representation
    ):
        raise ValueError("candidate representation is not deterministic")


def _risk_flags(base_flag: str, reasons: tuple[str, ...]) -> tuple[str, ...]:
    """Keep the boundary flag and preserve multiple upstream reasons."""

    values = {base_flag}
    if len(reasons) > 1:
        values.update(reasons)
    return tuple(sorted(values))


def _digest(value: Any) -> str:
    material = _canonicalize(value)
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return _to_utc(value, "timestamp").isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value, key=str)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ValueError(
        f"{type(value).__name__} cannot be deterministically serialized"
    )


def _to_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_text(value: Any, name: str) -> None:
    if not _is_text(value):
        raise ValueError(f"{name} must be a non-empty string")


evaluate_candidate_risk = evaluate_hard_risks
HardRiskEvaluation = CandidateRiskEvaluation


__all__ = [
    "CandidateRiskEvaluation",
    "CandidateRiskFlag",
    "CandidateViabilityStatus",
    "HardRiskEvaluation",
    "P05_T03_CONTRACT_VERSION",
    "P05_T03_EVALUATOR_VERSION",
    "evaluate_candidate_risk",
    "evaluate_hard_risks",
]