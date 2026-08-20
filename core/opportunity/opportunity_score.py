"""Deterministic P05-T05 per-candidate opportunity pre-score boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.features import FeatureCalculationStatus
from core.opportunity.opportunity_features import (
    CandidateFeatureEvaluation,
    P05_T04_CONTRACT_VERSION,
    P05_T04_EVALUATOR_VERSION,
)


P05_T05_CONTRACT_VERSION = "p05-t05-v1"
P05_T05_EVALUATOR_VERSION = "p05-t05-score-v1"
P05_T05_RULESET_VERSION = "p05-t05-rules-v1"
PRICE_VELOCITY = ("price_velocity", "price-velocity-v1")
PRICE_ACCELERATION = ("price_acceleration", "price-acceleration-v1")


def _require_decimal(value: Any, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{name} must be a finite Decimal")


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True)
class OpportunityScoringRuleset:
    """Immutable, versioned parameters for the P05-T05 score."""

    version: str = P05_T05_RULESET_VERSION
    velocity_scale: Decimal = Decimal("1")
    acceleration_scale: Decimal = Decimal("1")
    velocity_weight: Decimal = Decimal("2")
    acceleration_weight: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        _require_text(self.version, "ruleset version")
        if self.version != P05_T05_RULESET_VERSION:
            raise ValueError("unsupported P05-T05 ruleset version")
        for value, name in (
            (self.velocity_scale, "velocity_scale"),
            (self.acceleration_scale, "acceleration_scale"),
            (self.velocity_weight, "velocity_weight"),
            (self.acceleration_weight, "acceleration_weight"),
        ):
            _require_decimal(value, name)
            if value <= 0:
                raise ValueError(f"{name} must be positive")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "version": self.version,
                "velocity_scale": _decimal_text(self.velocity_scale),
                "acceleration_scale": _decimal_text(self.acceleration_scale),
                "velocity_weight": _decimal_text(self.velocity_weight),
                "acceleration_weight": _decimal_text(self.acceleration_weight),
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


DEFAULT_SCORING_RULESET = OpportunityScoringRuleset()


@dataclass(frozen=True)
class OpportunityScore:
    """Immutable, auditable score for exactly one eligible candidate."""

    candidate_id: str
    chain_id: str
    token_identity: str
    reference_time: datetime
    evaluated_at: datetime
    input_feature_evaluation_digest: str
    feature_evaluation: CandidateFeatureEvaluation
    ruleset: OpportunityScoringRuleset
    price_velocity: Decimal
    price_acceleration: Decimal
    velocity_signal: Decimal
    acceleration_signal: Decimal
    score: Decimal
    evaluator_version: str = P05_T05_EVALUATOR_VERSION
    contract_version: str = P05_T05_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.candidate_id, "candidate_id"),
            (self.chain_id, "chain_id"),
            (self.token_identity, "token_identity"),
            (self.input_feature_evaluation_digest, "input_feature_evaluation_digest"),
            (self.evaluator_version, "evaluator_version"),
            (self.contract_version, "contract_version"),
        ):
            _require_text(value, name)
        if self.evaluator_version != P05_T05_EVALUATOR_VERSION:
            raise ValueError("unsupported P05-T05 evaluator version")
        if self.contract_version != P05_T05_CONTRACT_VERSION:
            raise ValueError("unsupported P05-T05 contract version")
        object.__setattr__(
            self, "reference_time", _to_utc(self.reference_time, "reference_time")
        )
        object.__setattr__(
            self, "evaluated_at", _to_utc(self.evaluated_at, "evaluated_at")
        )
        if not isinstance(self.feature_evaluation, CandidateFeatureEvaluation):
            raise ValueError("feature_evaluation must be a CandidateFeatureEvaluation")
        _validate_feature_evaluation(self.feature_evaluation)
        if self.input_feature_evaluation_digest != self.feature_evaluation.digest:
            raise ValueError("feature evaluation digest does not match")
        if (
            self.feature_evaluation.candidate_id != self.candidate_id
            or self.feature_evaluation.chain_id != self.chain_id
            or self.feature_evaluation.token_identity != self.token_identity
        ):
            raise ValueError("feature evaluation identity does not match")
        if not isinstance(self.ruleset, OpportunityScoringRuleset):
            raise ValueError("ruleset must be an OpportunityScoringRuleset")
        for value, name in (
            (self.price_velocity, "price_velocity"),
            (self.price_acceleration, "price_acceleration"),
            (self.velocity_signal, "velocity_signal"),
            (self.acceleration_signal, "acceleration_signal"),
            (self.score, "score"),
        ):
            _require_decimal(value, name)
        expected = _calculate_values(
            self.price_velocity, self.price_acceleration, self.ruleset
        )
        if (self.velocity_signal, self.acceleration_signal, self.score) != expected:
            raise ValueError("score components do not match the ruleset")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "candidate_id": self.candidate_id,
                "chain_id": self.chain_id,
                "token_identity": self.token_identity,
                "reference_time": self.reference_time.isoformat(),
                "evaluated_at": self.evaluated_at.isoformat(),
                "input_feature_evaluation_digest": self.input_feature_evaluation_digest,
                "feature_evaluation": self.feature_evaluation.canonical_representation,
                "ruleset": self.ruleset.canonical_representation,
                "price_velocity": _decimal_text(self.price_velocity),
                "price_acceleration": _decimal_text(self.price_acceleration),
                "velocity_signal": _decimal_text(self.velocity_signal),
                "acceleration_signal": _decimal_text(self.acceleration_signal),
                "score": _decimal_text(self.score),
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


def evaluate_opportunity_score(
    feature_evaluation: CandidateFeatureEvaluation,
    *,
    ruleset: OpportunityScoringRuleset = DEFAULT_SCORING_RULESET,
    evaluated_at: datetime | None = None,
) -> OpportunityScore:
    """Calculate one deterministic score from one eligible T04 evaluation."""

    _validate_feature_evaluation(feature_evaluation)
    values = _scoreable_values(feature_evaluation)
    timestamp = (
        feature_evaluation.reference_time if evaluated_at is None else evaluated_at
    )
    velocity_signal, acceleration_signal, score = _calculate_values(
        values[PRICE_VELOCITY],
        values[PRICE_ACCELERATION],
        ruleset,
    )
    return OpportunityScore(
        candidate_id=feature_evaluation.candidate_id,
        chain_id=feature_evaluation.chain_id,
        token_identity=feature_evaluation.token_identity,
        reference_time=feature_evaluation.reference_time,
        evaluated_at=_to_utc(timestamp, "evaluated_at"),
        input_feature_evaluation_digest=feature_evaluation.digest,
        feature_evaluation=feature_evaluation,
        ruleset=ruleset,
        price_velocity=values[PRICE_VELOCITY],
        price_acceleration=values[PRICE_ACCELERATION],
        velocity_signal=velocity_signal,
        acceleration_signal=acceleration_signal,
        score=score,
    )


def _validate_feature_evaluation(
    feature_evaluation: CandidateFeatureEvaluation,
) -> None:
    if not isinstance(feature_evaluation, CandidateFeatureEvaluation):
        raise ValueError("feature_evaluation must be a CandidateFeatureEvaluation")
    if feature_evaluation.contract_version != P05_T04_CONTRACT_VERSION:
        raise ValueError("unsupported P05-T04 contract version")
    if feature_evaluation.evaluator_version != P05_T04_EVALUATOR_VERSION:
        raise ValueError("unsupported P05-T04 evaluator version")
    if feature_evaluation.risk_evaluation.viability_status.value != "ELIGIBLE":
        raise ValueError("P05-T03 eligibility gate is closed")
    if (
        feature_evaluation.canonical_representation
        != feature_evaluation.deterministic_representation
        or feature_evaluation.digest
        != _digest(feature_evaluation.canonical_representation)
    ):
        raise ValueError("P05-T04 evaluation is not canonical")
    try:
        CandidateFeatureEvaluation(
            candidate_id=feature_evaluation.candidate_id,
            chain_id=feature_evaluation.chain_id,
            token_identity=feature_evaluation.token_identity,
            reference_time=feature_evaluation.reference_time,
            evaluated_at=feature_evaluation.evaluated_at,
            input_candidate_digest=feature_evaluation.input_candidate_digest,
            risk_evaluation=feature_evaluation.risk_evaluation,
            feature_snapshots=feature_evaluation.feature_snapshots,
            signal_snapshot=feature_evaluation.signal_snapshot,
            upstream_references=feature_evaluation.upstream_references,
            evaluator_version=feature_evaluation.evaluator_version,
            contract_version=feature_evaluation.contract_version,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("P05-T04 evaluation is invalid") from error


def _scoreable_values(
    feature_evaluation: CandidateFeatureEvaluation,
) -> dict[tuple[str, str], Decimal]:
    values: dict[tuple[str, str], Decimal] = {}
    for snapshot in feature_evaluation.feature_snapshots:
        pair = (snapshot.feature_id, snapshot.feature_version)
        if pair not in (PRICE_VELOCITY, PRICE_ACCELERATION):
            continue
        if pair in values:
            raise ValueError("duplicate scoreable feature snapshot")
        if snapshot.status is not FeatureCalculationStatus.CALCULATED:
            raise ValueError("scoreable feature snapshot is not calculated")
        if not isinstance(snapshot.value, Decimal) or not snapshot.value.is_finite():
            raise ValueError("scoreable feature value is invalid")
        values[pair] = snapshot.value
    if set(values) != {PRICE_VELOCITY, PRICE_ACCELERATION}:
        raise ValueError("required scoreable feature snapshots are missing")
    return values


def _calculate_values(
    velocity: Decimal,
    acceleration: Decimal,
    ruleset: OpportunityScoringRuleset,
) -> tuple[Decimal, Decimal, Decimal]:
    if not isinstance(ruleset, OpportunityScoringRuleset):
        raise ValueError("ruleset must be an OpportunityScoringRuleset")
    with localcontext() as context:
        context.prec = 50
        velocity_signal = _bounded(velocity, ruleset.velocity_scale)
        acceleration_signal = _bounded(acceleration, ruleset.acceleration_scale)
        total_weight = ruleset.velocity_weight + ruleset.acceleration_weight
        weighted_signal = (
            ruleset.velocity_weight * velocity_signal
            + ruleset.acceleration_weight * acceleration_signal
        ) / total_weight
        score = Decimal("50") * (Decimal("1") + weighted_signal)
    return (
        _canonical_decimal(velocity_signal),
        _canonical_decimal(acceleration_signal),
        _canonical_decimal(score),
    )


def _bounded(value: Decimal, scale: Decimal) -> Decimal:
    return value / (scale + abs(value))


def _canonical_decimal(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("decimal must be finite")
    return Decimal(0) if value == 0 else value.normalize()


def _decimal_text(value: Decimal) -> str:
    return format(_canonical_decimal(value), "f")


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
        return _decimal_text(value)
    if isinstance(value, datetime):
        return _to_utc(value, "timestamp").isoformat()
    if isinstance(value, StrEnum):
        return value.value
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


__all__ = [
    "DEFAULT_SCORING_RULESET",
    "OpportunityScore",
    "OpportunityScoringRuleset",
    "P05_T05_CONTRACT_VERSION",
    "P05_T05_EVALUATOR_VERSION",
    "P05_T05_RULESET_VERSION",
    "evaluate_opportunity_score",
]