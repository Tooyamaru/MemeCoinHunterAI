"""Deterministic P05-T04 per-candidate feature availability boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.features.feature_snapshot import (
    FeatureCalculationSnapshot,
    P04_T10_CONTRACT_VERSION,
)
from core.features.price_features import P04_T09_CONTRACT_VERSION
from core.opportunity.opportunity_candidate import OpportunityUpstreamReference
from core.opportunity.opportunity_normalization import (
    NormalizedOpportunityCandidate,
    P05_T02_CONTRACT_VERSION,
)
from core.opportunity.opportunity_risk import (
    CandidateRiskEvaluation,
    P05_T03_CONTRACT_VERSION,
    P05_T03_EVALUATOR_VERSION,
    CandidateViabilityStatus,
)
from core.signals.signal_snapshot import (
    P04_T06_CONTRACT_VERSION,
    SignalEvidenceSnapshot,
)


P05_T04_CONTRACT_VERSION = "p05-t04-v1"
P05_T04_EVALUATOR_VERSION = "p05-t04-features-v1"
AUTHORIZED_FEATURES = frozenset(
    {
        ("price_velocity", "price-velocity-v1"),
        ("price_acceleration", "price-acceleration-v1"),
    }
)


@dataclass(frozen=True)
class CandidateFeatureEvaluation:
    """Immutable preservation of one candidate's existing feature snapshots."""

    candidate_id: str
    chain_id: str
    token_identity: str
    reference_time: datetime
    evaluated_at: datetime
    input_candidate_digest: str
    risk_evaluation: CandidateRiskEvaluation
    feature_snapshots: tuple[FeatureCalculationSnapshot, ...]
    signal_snapshot: SignalEvidenceSnapshot
    upstream_references: tuple[OpportunityUpstreamReference, ...]
    evaluator_version: str = P05_T04_EVALUATOR_VERSION
    contract_version: str = P05_T04_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.candidate_id, "candidate_id"),
            (self.chain_id, "chain_id"),
            (self.token_identity, "token_identity"),
            (self.input_candidate_digest, "input_candidate_digest"),
            (self.evaluator_version, "evaluator_version"),
            (self.contract_version, "contract_version"),
        ):
            _require_text(value, name)
        if self.evaluator_version != P05_T04_EVALUATOR_VERSION:
            raise ValueError("unsupported P05-T04 evaluator version")
        if self.contract_version != P05_T04_CONTRACT_VERSION:
            raise ValueError("unsupported P05-T04 contract version")

        object.__setattr__(
            self,
            "reference_time",
            _to_utc(self.reference_time, "reference_time"),
        )
        object.__setattr__(
            self,
            "evaluated_at",
            _to_utc(self.evaluated_at, "evaluated_at"),
        )
        if not isinstance(self.risk_evaluation, CandidateRiskEvaluation):
            raise ValueError("risk_evaluation must be a CandidateRiskEvaluation")
        if self.risk_evaluation.candidate_id != self.candidate_id:
            raise ValueError("risk evaluation candidate identity does not match")
        if self.risk_evaluation.input_candidate_digest != self.input_candidate_digest:
            raise ValueError("risk evaluation candidate digest does not match")
        if not isinstance(self.signal_snapshot, SignalEvidenceSnapshot):
            raise ValueError("signal_snapshot must be a SignalEvidenceSnapshot")
        if (
            self.signal_snapshot.chain_id != self.chain_id
            or self.signal_snapshot.token_identity != self.token_identity
        ):
            raise ValueError("signal snapshot identity does not match")

        snapshots = tuple(self.feature_snapshots)
        if not all(isinstance(value, FeatureCalculationSnapshot) for value in snapshots):
            raise ValueError(
                "feature_snapshots must contain FeatureCalculationSnapshot values"
            )
        object.__setattr__(self, "feature_snapshots", snapshots)

        references = tuple(self.upstream_references)
        if not all(
            isinstance(value, OpportunityUpstreamReference) for value in references
        ):
            raise ValueError(
                "upstream_references must contain OpportunityUpstreamReference values"
            )
        object.__setattr__(self, "upstream_references", references)

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "candidate_id": self.candidate_id,
                "chain_id": self.chain_id,
                "token_identity": self.token_identity,
                "reference_time": self.reference_time.isoformat(),
                "evaluated_at": self.evaluated_at.isoformat(),
                "input_candidate_digest": self.input_candidate_digest,
                "risk_evaluation": self.risk_evaluation.canonical_representation,
                "feature_snapshots": tuple(
                    value.canonical_representation for value in self.feature_snapshots
                ),
                "signal_snapshot": self.signal_snapshot.canonical_representation,
                "upstream_references": tuple(
                    value.canonical_representation
                    for value in self.upstream_references
                ),
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


def evaluate_candidate_features(
    candidate: NormalizedOpportunityCandidate,
    risk_evaluation: CandidateRiskEvaluation,
    *,
    evaluated_at: datetime | None = None,
) -> CandidateFeatureEvaluation:
    """Preserve and validate existing P04 results behind the P05-T03 gate."""

    _validate_candidate(candidate)
    _validate_risk(candidate, risk_evaluation)
    for snapshot in candidate.feature_snapshots:
        _validate_snapshot(snapshot)

    timestamp = candidate.reference_time if evaluated_at is None else evaluated_at
    return CandidateFeatureEvaluation(
        candidate_id=candidate.candidate_id,
        chain_id=candidate.chain_id,
        token_identity=candidate.token_identity,
        reference_time=candidate.reference_time,
        evaluated_at=_to_utc(timestamp, "evaluated_at"),
        input_candidate_digest=candidate.representation_digest,
        risk_evaluation=risk_evaluation,
        feature_snapshots=candidate.feature_snapshots,
        signal_snapshot=candidate.signal_snapshot,
        upstream_references=candidate.upstream_references,
    )


def _validate_candidate(candidate: NormalizedOpportunityCandidate) -> None:
    if not isinstance(candidate, NormalizedOpportunityCandidate):
        raise ValueError("candidate must be a NormalizedOpportunityCandidate")
    if candidate.contract_version != P05_T02_CONTRACT_VERSION:
        raise ValueError("unsupported P05-T02 candidate contract version")
    if candidate.candidate.contract_version != "p05-t01-v1":
        raise ValueError("unsupported P05-T01 candidate contract version")
    if (
        candidate.canonical_representation
        != candidate.deterministic_representation
        or not _is_text(candidate.representation_digest)
    ):
        raise ValueError("candidate representation is not deterministic")
    if not isinstance(candidate.signal_snapshot, SignalEvidenceSnapshot):
        raise ValueError("candidate signal snapshot is invalid")
    if candidate.signal_snapshot.contract_version != P04_T06_CONTRACT_VERSION:
        raise ValueError("unsupported P04 signal snapshot contract version")


def _validate_risk(
    candidate: NormalizedOpportunityCandidate,
    risk_evaluation: CandidateRiskEvaluation,
) -> None:
    if not isinstance(risk_evaluation, CandidateRiskEvaluation):
        raise ValueError("risk_evaluation must be a CandidateRiskEvaluation")
    if risk_evaluation.contract_version != P05_T03_CONTRACT_VERSION:
        raise ValueError("unsupported P05-T03 risk contract version")
    if risk_evaluation.evaluator_version != P05_T03_EVALUATOR_VERSION:
        raise ValueError("unsupported P05-T03 risk evaluator version")
    if risk_evaluation.candidate_id != candidate.candidate_id:
        raise ValueError("risk evaluation candidate identity does not match")
    if risk_evaluation.input_candidate_digest != candidate.representation_digest:
        raise ValueError("risk evaluation candidate digest does not match")
    if not isinstance(risk_evaluation.viability_status, CandidateViabilityStatus):
        raise ValueError("risk evaluation viability status is invalid")
    if risk_evaluation.viability_status is not CandidateViabilityStatus.ELIGIBLE:
        raise ValueError("P05-T03 viability gate is closed")
    _require_text(risk_evaluation.representation_digest, "risk evaluation digest")
    if (
        risk_evaluation.canonical_representation
        != risk_evaluation.deterministic_representation
    ):
        raise ValueError("risk evaluation representation is not deterministic")


def _validate_snapshot(snapshot: FeatureCalculationSnapshot) -> None:
    if snapshot.contract_version != P04_T10_CONTRACT_VERSION:
        raise ValueError("unsupported P04 feature snapshot contract version")
    if snapshot.calculation_contract_version != P04_T09_CONTRACT_VERSION:
        raise ValueError("unsupported P04 feature calculation contract version")
    if (
        snapshot.canonical_representation
        != snapshot.deterministic_representation
        or snapshot.calculation_result_id
        != _digest({"representation_digest": snapshot.result_representation_digest})
        or snapshot.snapshot_linkage.feature_representation_digest
        != snapshot.result_representation_digest
    ):
        raise ValueError("feature snapshot is not canonical")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonicalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return _to_utc(value, "timestamp").isoformat()
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ValueError(f"{type(value).__name__} cannot be deterministically serialized")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


def _to_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_text(value: Any, name: str) -> None:
    if not _is_text(value):
        raise ValueError(f"{name} must be a non-empty string")


__all__ = [
    "AUTHORIZED_FEATURES",
    "CandidateFeatureEvaluation",
    "P05_T04_CONTRACT_VERSION",
    "P05_T04_EVALUATOR_VERSION",
    "evaluate_candidate_features",
]