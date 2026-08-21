"""Deterministic P06-T02 Decision Intent evaluation boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.decision.decision_intent import (
    DecisionAction,
    DecisionIntent,
    EntryPosture,
    P06_T02_EVALUATOR_VERSION,
    P06_T02_RULESET_VERSION,
    create_decision_intent,
)
from core.opportunity.opportunity_context import OpportunityContext
from core.opportunity.opportunity_risk import CandidateViabilityStatus


@dataclass(frozen=True)
class DecisionEvaluationRuleset:
    """Immutable, versioned thresholds for one deterministic evaluation."""

    buy_score_threshold: Decimal = Decimal("75")
    watch_score_threshold: Decimal = Decimal("50")
    max_evidence_age_seconds: int = 3600
    version: str = P06_T02_RULESET_VERSION

    def __post_init__(self) -> None:
        for value, name in (
            (self.buy_score_threshold, "buy_score_threshold"),
            (self.watch_score_threshold, "watch_score_threshold"),
        ):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ValueError(f"{name} must be a finite Decimal")
            if not Decimal("0") <= value <= Decimal("100"):
                raise ValueError(f"{name} must be between 0 and 100")
        if self.buy_score_threshold <= self.watch_score_threshold:
            raise ValueError("buy threshold must exceed watch threshold")
        if (
            not isinstance(self.max_evidence_age_seconds, int)
            or isinstance(self.max_evidence_age_seconds, bool)
            or self.max_evidence_age_seconds < 0
        ):
            raise ValueError("max_evidence_age_seconds must be a non-negative integer")
        if self.version != P06_T02_RULESET_VERSION:
            raise ValueError("unsupported P06-T02 ruleset version")
        object.__setattr__(
            self,
            "buy_score_threshold",
            (
                Decimal("0")
                if self.buy_score_threshold == 0
                else self.buy_score_threshold.normalize()
            ),
        )
        object.__setattr__(
            self,
            "watch_score_threshold",
            (
                Decimal("0")
                if self.watch_score_threshold == 0
                else self.watch_score_threshold.normalize()
            ),
        )

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "buy_score_threshold": _decimal_text(self.buy_score_threshold),
                "watch_score_threshold": _decimal_text(self.watch_score_threshold),
                "max_evidence_age_seconds": self.max_evidence_age_seconds,
                "version": self.version,
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


DEFAULT_DECISION_EVALUATION_RULESET = DecisionEvaluationRuleset()


def evaluate_decision_intent(
    context: OpportunityContext,
    *,
    ruleset: DecisionEvaluationRuleset = DEFAULT_DECISION_EVALUATION_RULESET,
    decision_time: datetime | None = None,
) -> DecisionIntent:
    """Evaluate one context into one immutable DecisionIntent."""

    _validate_ruleset(ruleset)
    timestamp = context.reference_time if decision_time is None else _to_utc(
        decision_time,
        "decision_time",
    )
    if timestamp < context.reference_time:
        raise ValueError("decision_time cannot precede reference_time")

    reasons: list[str] = []
    invalidation: list[str] = []
    _validate_context_shape(context)
    if context.risk_evaluation.viability_status is not CandidateViabilityStatus.ELIGIBLE:
        reasons.append("HARD_RISK_NOT_ELIGIBLE")
        if context.risk_evaluation.rejection_reason:
            invalidation.append(context.risk_evaluation.rejection_reason)
    stale = _stale_evidence(context, timestamp, ruleset.max_evidence_age_seconds)
    if stale:
        reasons.append("STALE_EVIDENCE")
        invalidation.extend(stale)

    score = context.opportunity_score.score
    if reasons:
        action = DecisionAction.NO_TRADE
        confidence = Decimal("0")
    elif score >= ruleset.buy_score_threshold:
        action = DecisionAction.BUY
        confidence = score / Decimal("100")
    elif score >= ruleset.watch_score_threshold:
        action = DecisionAction.WATCH
        confidence = score / Decimal("100")
    else:
        action = DecisionAction.NO_TRADE
        confidence = Decimal("0")

    assumptions = (
        f"BUY score >= { _decimal_text(ruleset.buy_score_threshold) }",
        f"WATCH score >= { _decimal_text(ruleset.watch_score_threshold) }",
        "confidence is analytical and not probability of profit",
    )
    if action is DecisionAction.NO_TRADE and not reasons:
        reasons.append("SCORE_BELOW_WATCH_THRESHOLD")
    return create_decision_intent(
        context,
        action=action,
        entry_posture=EntryPosture.WAIT,
        expected_edge_assumptions=assumptions,
        uncertainty=tuple(reasons),
        invalidation_conditions=tuple(invalidation),
        confidence=confidence,
        decision_time=timestamp,
        ruleset_version=ruleset.version,
        evaluator_version=P06_T02_EVALUATOR_VERSION,
    )


evaluate_decision = evaluate_decision_intent


def _validate_ruleset(ruleset: DecisionEvaluationRuleset) -> None:
    if not isinstance(ruleset, DecisionEvaluationRuleset):
        raise ValueError("ruleset must be a DecisionEvaluationRuleset")
    if (
        ruleset.canonical_representation != ruleset.deterministic_representation
        or ruleset.digest != _digest(ruleset.canonical_representation)
    ):
        raise ValueError("ruleset is not canonical")
    try:
        validated = DecisionEvaluationRuleset(
            buy_score_threshold=ruleset.buy_score_threshold,
            watch_score_threshold=ruleset.watch_score_threshold,
            max_evidence_age_seconds=ruleset.max_evidence_age_seconds,
            version=ruleset.version,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("ruleset is invalid or unsupported") from error
    if validated != ruleset or validated.digest != ruleset.digest:
        raise ValueError("ruleset is tampered")


def _validate_context_shape(context: OpportunityContext) -> None:
    try:
        create_decision_intent(
            context,
            action=DecisionAction.NO_TRADE,
            decision_time=context.reference_time,
            ruleset_version=P06_T02_RULESET_VERSION,
            evaluator_version=P06_T02_EVALUATOR_VERSION,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("context is invalid, incomplete, or tampered") from error


def _stale_evidence(
    context: OpportunityContext,
    decision_time: datetime,
    max_age_seconds: int,
) -> tuple[str, ...]:
    timestamps = [
        ("risk_evaluation", context.risk_evaluation.evaluated_at),
        ("feature_evaluation", context.feature_evaluation.evaluated_at),
        ("opportunity_score", context.opportunity_score.evaluated_at),
    ]
    timestamps.extend(
        (f"signal_observation_{index}", value)
        for index, value in enumerate(context.signal_snapshot.observation_timestamps)
        if value is not None
    )
    stale: list[str] = []
    for name, timestamp in timestamps:
        age = (decision_time - _to_utc(timestamp, name)).total_seconds()
        if age < 0 or age > max_age_seconds:
            stale.append(f"{name}:STALE_OR_FUTURE")
    return tuple(sorted(stale))


def _to_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _canonical_decimal(value: Decimal) -> Decimal:
    return Decimal("0") if value == 0 else value.normalize()


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


__all__ = [
    "DEFAULT_DECISION_EVALUATION_RULESET",
    "DecisionEvaluationRuleset",
    "evaluate_decision",
    "evaluate_decision_intent",
]