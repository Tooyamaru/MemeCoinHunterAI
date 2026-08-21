"""Deterministic P05-T06 opportunity-record materialization boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.opportunity.opportunity_score import (
    OpportunityScore,
    OpportunityScoringRuleset,
    P05_T05_EVALUATOR_VERSION,
    P05_T05_RULESET_VERSION,
    P05_T05_CONTRACT_VERSION,
)


P05_T06_CONTRACT_VERSION = "p05-t06-v1"
P05_T06_EVALUATOR_VERSION = "p05-t06-record-v1"


@dataclass(frozen=True)
class OpportunityRecord:
    """Immutable one-to-one record preserving one validated P05-T05 score."""

    candidate_id: str
    chain_id: str
    token_identity: str
    reference_time: datetime
    input_score_digest: str
    opportunity_score: OpportunityScore
    evaluator_version: str = P05_T06_EVALUATOR_VERSION
    contract_version: str = P05_T06_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.candidate_id, "candidate_id"),
            (self.chain_id, "chain_id"),
            (self.token_identity, "token_identity"),
            (self.input_score_digest, "input_score_digest"),
            (self.evaluator_version, "evaluator_version"),
            (self.contract_version, "contract_version"),
        ):
            _require_text(value, name)
        if self.evaluator_version != P05_T06_EVALUATOR_VERSION:
            raise ValueError("unsupported P05-T06 evaluator version")
        if self.contract_version != P05_T06_CONTRACT_VERSION:
            raise ValueError("unsupported P05-T06 contract version")
        object.__setattr__(
            self,
            "reference_time",
            _to_utc(self.reference_time, "reference_time"),
        )
        _validate_score(self.opportunity_score)
        if self.input_score_digest != self.opportunity_score.digest:
            raise ValueError("opportunity score digest does not match")
        if (
            self.candidate_id != self.opportunity_score.candidate_id
            or self.chain_id != self.opportunity_score.chain_id
            or self.token_identity != self.opportunity_score.token_identity
            or self.reference_time != self.opportunity_score.reference_time
        ):
            raise ValueError("opportunity score identity does not match")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "candidate_id": self.candidate_id,
                "chain_id": self.chain_id,
                "token_identity": self.token_identity,
                "reference_time": self.reference_time.isoformat(),
                "input_score_digest": self.input_score_digest,
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


def materialize_opportunity_record(
    opportunity_score: OpportunityScore,
) -> OpportunityRecord:
    """Materialize one validated P05-T05 score without adding semantics."""

    _validate_score(opportunity_score)
    return OpportunityRecord(
        candidate_id=opportunity_score.candidate_id,
        chain_id=opportunity_score.chain_id,
        token_identity=opportunity_score.token_identity,
        reference_time=opportunity_score.reference_time,
        input_score_digest=opportunity_score.digest,
        opportunity_score=opportunity_score,
    )


create_opportunity_record = materialize_opportunity_record


def _validate_score(opportunity_score: OpportunityScore) -> None:
    if not isinstance(opportunity_score, OpportunityScore):
        raise ValueError("opportunity_score must be an OpportunityScore")
    if opportunity_score.contract_version != P05_T05_CONTRACT_VERSION:
        raise ValueError("unsupported P05-T05 contract version")
    if opportunity_score.evaluator_version != P05_T05_EVALUATOR_VERSION:
        raise ValueError("unsupported P05-T05 evaluator version")
    if opportunity_score.ruleset.version != P05_T05_RULESET_VERSION:
        raise ValueError("unsupported P05-T05 ruleset version")
    if (
        opportunity_score.canonical_representation
        != opportunity_score.deterministic_representation
        or opportunity_score.digest
        != _digest(opportunity_score.canonical_representation)
    ):
        raise ValueError("opportunity score is not canonical")
    try:
        validated_ruleset = OpportunityScoringRuleset(
            version=opportunity_score.ruleset.version,
            velocity_scale=opportunity_score.ruleset.velocity_scale,
            acceleration_scale=opportunity_score.ruleset.acceleration_scale,
            velocity_weight=opportunity_score.ruleset.velocity_weight,
            acceleration_weight=opportunity_score.ruleset.acceleration_weight,
        )
        OpportunityScore(
            candidate_id=opportunity_score.candidate_id,
            chain_id=opportunity_score.chain_id,
            token_identity=opportunity_score.token_identity,
            reference_time=opportunity_score.reference_time,
            evaluated_at=opportunity_score.evaluated_at,
            input_feature_evaluation_digest=(
                opportunity_score.input_feature_evaluation_digest
            ),
            feature_evaluation=opportunity_score.feature_evaluation,
            ruleset=validated_ruleset,
            price_velocity=opportunity_score.price_velocity,
            price_acceleration=opportunity_score.price_acceleration,
            velocity_signal=opportunity_score.velocity_signal,
            acceleration_signal=opportunity_score.acceleration_signal,
            score=opportunity_score.score,
            evaluator_version=opportunity_score.evaluator_version,
            contract_version=opportunity_score.contract_version,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("opportunity score is invalid") from error


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
            str(key): _canonicalize(value[key])
            for key in sorted(value, key=str)
        }
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


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


__all__ = [
    "OpportunityRecord",
    "P05_T06_CONTRACT_VERSION",
    "P05_T06_EVALUATOR_VERSION",
    "create_opportunity_record",
    "materialize_opportunity_record",
]