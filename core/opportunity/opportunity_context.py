"""Deterministic final P05 opportunity-context boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.opportunity.opportunity_features import (
    AUTHORIZED_FEATURES,
    CandidateFeatureEvaluation,
)
from core.opportunity.opportunity_record import OpportunityRecord
from core.opportunity.opportunity_record_history import (
    OpportunityRecordHistory,
    P05_T07_CONTRACT_VERSION,
)
from core.opportunity.opportunity_risk import CandidateRiskEvaluation
from core.opportunity.opportunity_score import OpportunityScore
from core.signals.signal_snapshot import SignalEvidenceSnapshot


P05_T08_CONTRACT_VERSION = "p05-t08-v1"
P05_T08_EVALUATOR_VERSION = "p05-t08-context-v1"


@dataclass(frozen=True)
class OpportunityContext:
    """Immutable, evidence-first context handed to the future P06 boundary."""

    candidate_id: str
    chain_id: str
    token_identity: str
    reference_time: datetime
    record_digest: str
    history_digest: str
    opportunity_record: OpportunityRecord
    record_history: OpportunityRecordHistory
    risk_evaluation: CandidateRiskEvaluation
    feature_evaluation: CandidateFeatureEvaluation
    signal_snapshot: SignalEvidenceSnapshot
    opportunity_score: OpportunityScore
    evaluator_version: str = P05_T08_EVALUATOR_VERSION
    contract_version: str = P05_T08_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.candidate_id, "candidate_id"),
            (self.chain_id, "chain_id"),
            (self.token_identity, "token_identity"),
            (self.record_digest, "record_digest"),
            (self.history_digest, "history_digest"),
            (self.evaluator_version, "evaluator_version"),
            (self.contract_version, "contract_version"),
        ):
            _require_text(value, name)
        if self.evaluator_version != P05_T08_EVALUATOR_VERSION:
            raise ValueError("unsupported P05-T08 evaluator version")
        if self.contract_version != P05_T08_CONTRACT_VERSION:
            raise ValueError("unsupported P05-T08 contract version")
        object.__setattr__(
            self,
            "reference_time",
            _to_utc(self.reference_time, "reference_time"),
        )
        if not isinstance(self.opportunity_record, OpportunityRecord):
            raise ValueError("opportunity_record must be an OpportunityRecord")
        if not isinstance(self.record_history, OpportunityRecordHistory):
            raise ValueError(
                "record_history must be an OpportunityRecordHistory"
            )
        if not isinstance(self.risk_evaluation, CandidateRiskEvaluation):
            raise ValueError("risk_evaluation must be a CandidateRiskEvaluation")
        if not isinstance(self.feature_evaluation, CandidateFeatureEvaluation):
            raise ValueError(
                "feature_evaluation must be a CandidateFeatureEvaluation"
            )
        if not isinstance(self.signal_snapshot, SignalEvidenceSnapshot):
            raise ValueError("signal_snapshot must be a SignalEvidenceSnapshot")
        if not isinstance(self.opportunity_score, OpportunityScore):
            raise ValueError("opportunity_score must be an OpportunityScore")

        record = self.opportunity_record
        if self.record_digest != record.digest:
            raise ValueError("opportunity record digest does not match")
        if self.history_digest != self.record_history.digest:
            raise ValueError("opportunity record history digest does not match")
        if record.contract_version != "p05-t06-v1":
            raise ValueError("unsupported P05-T06 record contract version")
        if self.record_history.records.count(record) != 1:
            raise ValueError("opportunity record is not linked exactly once")
        if not any(item is record for item in self.record_history.records):
            raise ValueError("opportunity record identity is not preserved")
        if record.feature_evaluation is not self.feature_evaluation:
            raise ValueError("feature evaluation linkage does not match")
        if record.risk_evaluation is not self.risk_evaluation:
            raise ValueError("risk evaluation linkage does not match")
        if record.signal_snapshot is not self.signal_snapshot:
            raise ValueError("signal snapshot linkage does not match")
        if record.opportunity_score is not self.opportunity_score:
            raise ValueError("opportunity score linkage does not match")
        if (
            self.candidate_id != record.candidate_id
            or self.chain_id != record.chain_id
            or self.token_identity != record.token_identity
            or self.reference_time != record.reference_time
        ):
            raise ValueError("opportunity context identity does not match")
        _validate_feature_identity(self.feature_evaluation)
        _validate_upstream_provenance(
            self.risk_evaluation,
            self.feature_evaluation,
            self.signal_snapshot,
            self.opportunity_score,
        )

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "candidate_id": self.candidate_id,
                "chain_id": self.chain_id,
                "token_identity": self.token_identity,
                "reference_time": self.reference_time.isoformat(),
                "record_digest": self.record_digest,
                "history_digest": self.history_digest,
                "opportunity_record": self.opportunity_record.canonical_representation,
                "record_history_contract_version": P05_T07_CONTRACT_VERSION,
                "risk_evaluation": self.risk_evaluation.canonical_representation,
                "feature_evaluation": self.feature_evaluation.canonical_representation,
                "signal_snapshot": self.signal_snapshot.canonical_representation,
                "opportunity_score": self.opportunity_score.canonical_representation,
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
    def is_decision(self) -> bool:
        return False

    @property
    def is_authorization(self) -> bool:
        return False

    @property
    def is_order(self) -> bool:
        return False


def materialize_opportunity_context(
    opportunity_record: OpportunityRecord,
    record_history: OpportunityRecordHistory,
) -> OpportunityContext:
    """Link one validated T06 record to one validated T07 history."""

    if not isinstance(opportunity_record, OpportunityRecord):
        raise ValueError("opportunity_record must be an OpportunityRecord")
    if not isinstance(record_history, OpportunityRecordHistory):
        raise ValueError(
            "record_history must be an OpportunityRecordHistory"
        )
    return OpportunityContext(
        candidate_id=opportunity_record.candidate_id,
        chain_id=opportunity_record.chain_id,
        token_identity=opportunity_record.token_identity,
        reference_time=opportunity_record.reference_time,
        record_digest=opportunity_record.digest,
        history_digest=record_history.digest,
        opportunity_record=opportunity_record,
        record_history=record_history,
        risk_evaluation=opportunity_record.risk_evaluation,
        feature_evaluation=opportunity_record.feature_evaluation,
        signal_snapshot=opportunity_record.signal_snapshot,
        opportunity_score=opportunity_record.opportunity_score,
    )


create_opportunity_context = materialize_opportunity_context


def _validate_feature_identity(
    feature_evaluation: CandidateFeatureEvaluation,
) -> None:
    pairs = tuple(
        (snapshot.feature_id, snapshot.feature_version)
        for snapshot in feature_evaluation.feature_snapshots
    )
    if len(pairs) != len(set(pairs)) or set(pairs) != set(AUTHORIZED_FEATURES):
        raise ValueError("feature identity is unsupported or incomplete")


def _validate_upstream_provenance(
    risk_evaluation: CandidateRiskEvaluation,
    feature_evaluation: CandidateFeatureEvaluation,
    signal_snapshot: SignalEvidenceSnapshot,
    opportunity_score: OpportunityScore,
) -> None:
    for value, name in (
        (risk_evaluation, "risk evaluation"),
        (feature_evaluation, "feature evaluation"),
        (signal_snapshot, "signal snapshot"),
        (opportunity_score, "opportunity score"),
    ):
        if (
            value.canonical_representation
            != value.deterministic_representation
            or value.digest != _digest(value.canonical_representation)
        ):
            raise ValueError(f"{name} provenance is not canonical")


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
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("decimal must be finite")
        return format(value.normalize(), "f")
    if isinstance(value, datetime):
        return _to_utc(value, "timestamp").isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key]) for key in sorted(value, key=str)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ValueError(f"{type(value).__name__} cannot be deterministically serialized")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(child) for key, child in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


def _to_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


__all__ = [
    "OpportunityContext",
    "P05_T08_CONTRACT_VERSION",
    "P05_T08_EVALUATOR_VERSION",
    "create_opportunity_context",
    "materialize_opportunity_context",
]