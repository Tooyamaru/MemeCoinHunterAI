"""Immutable, bounded, non-authoritative P06-T03 analysis context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.decision.decision_intent import _validate_context
from core.opportunity.opportunity_context import OpportunityContext


P06_T03_CONTRACT_VERSION = "p06-t03-v1"
P06_T03_EVALUATOR_VERSION = "p06-t03-analysis-v1"
P06_T03_MAX_OBSERVATIONS = 32
P06_T03_MAX_NARRATIVE_ITEMS = 8
P06_T03_MAX_TEXT_LENGTH = 2_048
P06_T03_MAX_TOTAL_TEXT_LENGTH = 16_384


@dataclass(frozen=True)
class BoundedAnalysisObservation:
    """A supplied observation reference, never a generated conclusion."""

    source_id: str
    source_version: str
    evidence_reference: str
    observed_at: datetime
    content: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.source_id, "source_id"),
            (self.source_version, "source_version"),
            (self.evidence_reference, "evidence_reference"),
            (self.content, "content"),
        ):
            _bounded_text(value, name)
        object.__setattr__(
            self, "observed_at", _to_utc(self.observed_at, "observed_at")
        )

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "source_id": self.source_id,
                "source_version": self.source_version,
                "evidence_reference": self.evidence_reference,
                "observed_at": self.observed_at.isoformat(),
                "content": self.content,
            }
        )


@dataclass(frozen=True)
class BoundedDeepAnalysis:
    """Optional analytical context that cannot alter the P06-T02 result.

    This record preserves supplied observations separately from generated
    narrative.  It contains no action, ranking, authorization, capital, or
    execution vocabulary and is safe to omit from deterministic evaluation.
    """

    context: OpportunityContext
    source_id: str
    source_version: str
    analysis_time: datetime
    validation_time: datetime
    observations: tuple[BoundedAnalysisObservation, ...] = ()
    generated_narrative: tuple[str, ...] = ()
    max_age_seconds: int = 3_600
    evaluator_version: str = P06_T03_EVALUATOR_VERSION
    contract_version: str = P06_T03_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _validate_context(self.context)
        _bounded_text(self.source_id, "source_id")
        _bounded_text(self.source_version, "source_version")
        analysis_time = _to_utc(self.analysis_time, "analysis_time")
        validation_time = _to_utc(self.validation_time, "validation_time")
        if analysis_time < self.context.reference_time:
            raise ValueError("analysis_time cannot precede context reference_time")
        if validation_time < self.context.reference_time:
            raise ValueError("validation_time cannot precede context reference_time")
        if analysis_time > validation_time:
            raise ValueError("analysis_time cannot be in the future")
        if (
            not isinstance(self.max_age_seconds, int)
            or isinstance(self.max_age_seconds, bool)
            or self.max_age_seconds < 0
        ):
            raise ValueError("max_age_seconds must be a non-negative integer")
        if validation_time.timestamp() - analysis_time.timestamp() > self.max_age_seconds:
            raise ValueError("analysis is stale")
        if self.evaluator_version != P06_T03_EVALUATOR_VERSION:
            raise ValueError("unsupported P06-T03 evaluator version")
        if self.contract_version != P06_T03_CONTRACT_VERSION:
            raise ValueError("unsupported P06-T03 contract version")

        observations = tuple(self.observations)
        if len(observations) > P06_T03_MAX_OBSERVATIONS:
            raise ValueError("analysis observations exceed bounded size")
        if any(not isinstance(item, BoundedAnalysisObservation) for item in observations):
            raise ValueError("observations must be BoundedAnalysisObservation values")
        for item in observations:
            if item.observed_at < self.context.reference_time:
                raise ValueError("observation precedes context reference_time")
            if item.observed_at > validation_time:
                raise ValueError("observation is in the future")
        object.__setattr__(self, "observations", observations)

        narrative = _normalized_texts(
            self.generated_narrative, "generated_narrative", P06_T03_MAX_NARRATIVE_ITEMS
        )
        object.__setattr__(self, "generated_narrative", narrative)
        total_text = sum(
            len(item.content) + len(item.evidence_reference) for item in observations
        ) + sum(len(item) for item in narrative)
        if total_text > P06_T03_MAX_TOTAL_TEXT_LENGTH:
            raise ValueError("analysis exceeds bounded total size")
        object.__setattr__(self, "analysis_time", analysis_time)
        object.__setattr__(self, "validation_time", validation_time)

    @property
    def reference_time(self) -> datetime:
        return self.context.reference_time

    @property
    def context_digest(self) -> str:
        return self.context.digest

    @property
    def evaluation_time(self) -> datetime:
        return self.analysis_time

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "context_digest": self.context_digest,
                "source_id": self.source_id,
                "source_version": self.source_version,
                "reference_time": self.reference_time.isoformat(),
                "analysis_time": self.analysis_time.isoformat(),
                "validation_time": self.validation_time.isoformat(),
                "observations": tuple(
                    item.canonical_representation for item in self.observations
                ),
                "generated_narrative": self.generated_narrative,
                "max_age_seconds": self.max_age_seconds,
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
    def is_authoritative(self) -> bool:
        return False

    @property
    def is_generated_analysis(self) -> bool:
        return True


create_bounded_deep_analysis = BoundedDeepAnalysis
BoundedAnalysis = BoundedDeepAnalysis


def _bounded_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if len(value) > P06_T03_MAX_TEXT_LENGTH:
        raise ValueError(f"{name} exceeds bounded size")


def _normalized_texts(
    values: Any, name: str, max_items: int
) -> tuple[str, ...]:
    try:
        normalized = tuple(values)
    except TypeError as error:
        raise ValueError(f"{name} must be a tuple or list") from error
    if len(normalized) > max_items:
        raise ValueError(f"{name} exceeds bounded size")
    for value in normalized:
        _bounded_text(value, name)
    return tuple(dict.fromkeys(normalized))


def _to_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


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
    "BoundedAnalysis",
    "BoundedAnalysisObservation",
    "BoundedDeepAnalysis",
    "P06_T03_CONTRACT_VERSION",
    "P06_T03_EVALUATOR_VERSION",
    "P06_T03_MAX_NARRATIVE_ITEMS",
    "P06_T03_MAX_OBSERVATIONS",
    "P06_T03_MAX_TEXT_LENGTH",
    "P06_T03_MAX_TOTAL_TEXT_LENGTH",
    "create_bounded_deep_analysis",
]