"""Immutable, deterministic P06-T01 Decision Intent contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.opportunity.opportunity_context import OpportunityContext
from core.opportunity.opportunity_risk import CandidateViabilityStatus


P06_T01_CONTRACT_VERSION = "p06-t01-v1"
P06_T01_RULESET_VERSION = "p06-t01-rules-v1"
P06_T01_EVALUATOR_VERSION = "p06-t01-intent-v1"
P06_T02_RULESET_VERSION = "p06-t02-rules-v1"
P06_T02_EVALUATOR_VERSION = "p06-t02-evaluator-v1"


class DecisionAction(StrEnum):
    """Analytical actions; none is an order or execution authorization."""

    BUY = "BUY"
    WATCH = "WATCH"
    HOLD = "HOLD"
    TAKE_PROFIT = "TAKE_PROFIT"
    REDUCE = "REDUCE"
    EXIT = "EXIT"
    AVOID = "AVOID"
    NO_TRADE = "NO_TRADE"


class EntryPosture(StrEnum):
    """Entry posture kept separate from the analytical action."""

    WAIT = "WAIT"
    DEFERRED = "DEFERRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class DecisionIntent:
    """One immutable analytical intent for exactly one validated P05-T08 context."""

    context: OpportunityContext
    action: DecisionAction
    entry_posture: EntryPosture
    expected_edge_assumptions: tuple[str, ...]
    uncertainty: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    confidence: Decimal
    decision_time: datetime
    ruleset_version: str = P06_T01_RULESET_VERSION
    evaluator_version: str = P06_T01_EVALUATOR_VERSION
    contract_version: str = P06_T01_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _validate_context(self.context)
        try:
            action = DecisionAction(self.action)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported decision action") from error
        object.__setattr__(self, "action", action)
        try:
            posture = EntryPosture(self.entry_posture)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported entry posture") from error
        object.__setattr__(self, "entry_posture", posture)

        for value, name in (
            (self.ruleset_version, "ruleset_version"),
            (self.evaluator_version, "evaluator_version"),
            (self.contract_version, "contract_version"),
        ):
            _require_text(value, name)
        if self.ruleset_version not in {
            P06_T01_RULESET_VERSION,
            P06_T02_RULESET_VERSION,
        }:
            raise ValueError(f"unsupported P06-T01 {self.ruleset_version}")
        if self.evaluator_version not in {
            P06_T01_EVALUATOR_VERSION,
            P06_T02_EVALUATOR_VERSION,
        }:
            raise ValueError(f"unsupported P06-T01 {self.evaluator_version}")
        if self.contract_version != P06_T01_CONTRACT_VERSION:
            raise ValueError("unsupported P06-T01 contract_version")

        for value, name in (
            (self.expected_edge_assumptions, "expected_edge_assumptions"),
            (self.uncertainty, "uncertainty"),
            (self.invalidation_conditions, "invalidation_conditions"),
        ):
            normalized = _normalized_texts(value, name)
            object.__setattr__(self, name, normalized)

        if not isinstance(self.confidence, Decimal) or not self.confidence.is_finite():
            raise ValueError("confidence must be a finite Decimal")
        if not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "confidence", _canonical_decimal(self.confidence))
        decision_time = _to_utc(self.decision_time, "decision_time")
        if decision_time < self.context.reference_time:
            raise ValueError("decision_time cannot precede reference_time")
        object.__setattr__(self, "decision_time", decision_time)

        risk_status = self.context.risk_evaluation.viability_status
        evidence_is_uncertain = bool(self.uncertainty or self.invalidation_conditions)
        if (
            (risk_status is not CandidateViabilityStatus.ELIGIBLE or evidence_is_uncertain)
            and action is not DecisionAction.NO_TRADE
        ):
            raise ValueError("uncertain or invalid evidence requires NO_TRADE")

    @property
    def candidate_id(self) -> str:
        return self.context.candidate_id

    @property
    def chain_id(self) -> str:
        return self.context.chain_id

    @property
    def token_identity(self) -> str:
        return self.context.token_identity

    @property
    def context_digest(self) -> str:
        return self.context.digest

    @property
    def risk_evaluation(self):
        return self.context.risk_evaluation

    @property
    def feature_evaluation(self):
        return self.context.feature_evaluation

    @property
    def signal_snapshot(self):
        return self.context.signal_snapshot

    @property
    def opportunity_score(self):
        return self.context.opportunity_score

    @property
    def opportunity_record(self):
        return self.context.opportunity_record

    @property
    def record_history(self):
        return self.context.record_history

    @property
    def analytical_confidence(self) -> Decimal:
        return self.confidence

    @property
    def probability_of_profit(self) -> None:
        """Confidence is intentionally never exposed as profit probability."""

        return None

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "context": self.context.canonical_representation,
                "action": self.action.value,
                "entry_posture": self.entry_posture.value,
                "expected_edge_assumptions": self.expected_edge_assumptions,
                "uncertainty": self.uncertainty,
                "invalidation_conditions": self.invalidation_conditions,
                "confidence": _decimal_text(self.confidence),
                "decision_time": self.decision_time.isoformat(),
                "ruleset_version": self.ruleset_version,
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
        return True

    @property
    def is_authorization(self) -> bool:
        return False

    @property
    def is_order(self) -> bool:
        return False


def create_decision_intent(
    context: OpportunityContext,
    *,
    action: DecisionAction | str = DecisionAction.NO_TRADE,
    entry_posture: EntryPosture | str = EntryPosture.WAIT,
    expected_edge_assumptions: tuple[str, ...] | list[str] = (),
    uncertainty: tuple[str, ...] | list[str] = (),
    invalidation_conditions: tuple[str, ...] | list[str] = (),
    confidence: Decimal = Decimal("0"),
    decision_time: datetime | None = None,
    ruleset_version: str = P06_T01_RULESET_VERSION,
    evaluator_version: str = P06_T01_EVALUATOR_VERSION,
    contract_version: str = P06_T01_CONTRACT_VERSION,
) -> DecisionIntent:
    """Create one deterministic intent without wall-clock or external input."""

    _validate_context(context)
    timestamp = context.reference_time if decision_time is None else decision_time
    return DecisionIntent(
        context=context,
        action=action,
        entry_posture=entry_posture,
        expected_edge_assumptions=tuple(expected_edge_assumptions),
        uncertainty=tuple(uncertainty),
        invalidation_conditions=tuple(invalidation_conditions),
        confidence=confidence,
        decision_time=timestamp,
        ruleset_version=ruleset_version,
        evaluator_version=evaluator_version,
        contract_version=contract_version,
    )


materialize_decision_intent = create_decision_intent


def _validate_context(context: OpportunityContext) -> None:
    if not isinstance(context, OpportunityContext):
        raise ValueError("context must be an OpportunityContext")
    if (
        context.canonical_representation != context.deterministic_representation
        or context.digest != _digest(context.canonical_representation)
    ):
        raise ValueError("OpportunityContext is not canonical")
    try:
        validated = OpportunityContext(
            candidate_id=context.candidate_id,
            chain_id=context.chain_id,
            token_identity=context.token_identity,
            reference_time=context.reference_time,
            record_digest=context.record_digest,
            history_digest=context.history_digest,
            opportunity_record=context.opportunity_record,
            record_history=context.record_history,
            risk_evaluation=context.risk_evaluation,
            feature_evaluation=context.feature_evaluation,
            signal_snapshot=context.signal_snapshot,
            opportunity_score=context.opportunity_score,
            evaluator_version=context.evaluator_version,
            contract_version=context.contract_version,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("OpportunityContext is invalid or incomplete") from error
    if validated != context or validated.digest != context.digest:
        raise ValueError("OpportunityContext is tampered")


def _normalized_texts(values: Any, name: str) -> tuple[str, ...]:
    try:
        normalized = tuple(values)
    except TypeError as error:
        raise ValueError(f"{name} must be a tuple or list") from error
    if any(not isinstance(value, str) or not value.strip() for value in normalized):
        raise ValueError(f"{name} must contain non-empty strings")
    return tuple(sorted(dict.fromkeys(normalized)))


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


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
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


__all__ = [
    "DecisionAction",
    "DecisionIntent",
    "EntryPosture",
    "P06_T01_CONTRACT_VERSION",
    "P06_T01_EVALUATOR_VERSION",
    "P06_T01_RULESET_VERSION",
    "P06_T02_EVALUATOR_VERSION",
    "P06_T02_RULESET_VERSION",
    "create_decision_intent",
    "materialize_decision_intent",
]