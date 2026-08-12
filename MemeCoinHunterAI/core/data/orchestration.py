"""Provider-neutral ingestion orchestration for P02-T02.

This module coordinates adapter observations with the canonical P02-T01
contracts. It deliberately contains no network, provider, database, queue,
trading, or strategy behavior.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
import hashlib
import json
from typing import Any, Mapping, Protocol

from core.data.contracts import (
    DataQuality,
    FreshnessPolicy,
    NormalizationContext,
    NormalizedMarketState,
    RawEvent,
    SequenceValue,
    SourceHealth,
    SourceHealthStatus,
    SourceHealthTracker,
    canonical_identity,
    normalize_raw_event,
)


class ObservationKind(StrEnum):
    """Kinds of observations an adapter may hand to the boundary."""

    EVENT = "EVENT"
    FAILURE = "FAILURE"
    RECOVERY = "RECOVERY"
    RESYNC = "RESYNC"
    RESYNC_REQUIRED = "RESYNC_REQUIRED"


class CursorContinuity(StrEnum):
    """Evidence supplied by an adapter about cursor continuity."""

    NOT_PROVIDED = "NOT_PROVIDED"
    UNKNOWN = "UNKNOWN"
    CONTINUOUS = "CONTINUOUS"
    DISCONTINUOUS = "DISCONTINUOUS"


class IngestionOutcome(StrEnum):
    """Observable result category for every orchestration input."""

    ACCEPTED = "ACCEPTED"
    QUALITY_REJECTED = "QUALITY_REJECTED"
    OBSERVATION_REJECTED = "OBSERVATION_REJECTED"
    SOURCE_FAILURE = "SOURCE_FAILURE"
    SOURCE_RECOVERY = "SOURCE_RECOVERY"
    RESYNCHRONIZATION_REQUIRED = "RESYNCHRONIZATION_REQUIRED"


@dataclass(frozen=True)
class AdapterObservation:
    """Provider-neutral envelope emitted by a future adapter."""

    source_id: str
    kind: ObservationKind
    observed_time: datetime
    raw_event: RawEvent | None = None
    failure_reason: str | None = None
    cursor: SequenceValue = None
    cursor_continuity: CursorContinuity = CursorContinuity.NOT_PROVIDED
    source_metadata: Mapping[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None


@dataclass
class IngestionContext:
    """Explicit mutable state required for deterministic orchestration."""

    freshness_policy: FreshnessPolicy
    contract_version: str
    normalization: NormalizationContext = field(default_factory=NormalizationContext)
    source_health: SourceHealthTracker = field(default_factory=SourceHealthTracker)
    cursor_by_source: dict[str, SequenceValue] = field(default_factory=dict)
    resynchronization_required: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not isinstance(self.freshness_policy, FreshnessPolicy):
            raise ValueError("freshness_policy is required")
        if not isinstance(self.contract_version, str) or not self.contract_version.strip():
            raise ValueError("contract_version is required")


@dataclass(frozen=True)
class IngestionResult:
    """Auditable output produced for every adapter observation."""

    observation_id: str
    source_id: str
    kind: ObservationKind | None
    outcome: IngestionOutcome
    quality_status: DataQuality | None
    state: NormalizedMarketState | None
    source_health: SourceHealth | None
    observed_time: datetime | None
    processing_time: datetime | None
    reference_time: datetime | None
    cursor: SequenceValue
    contract_version: str | None
    accepted: bool
    published_as_current: bool
    recovered: bool
    resynchronization_required: bool
    reasons: tuple[str, ...] = ()


class IngestionPublisher(Protocol):
    """Provider-neutral publication boundary for observable results."""

    def publish(self, result: IngestionResult) -> None:
        """Publish one result without requiring a particular transport."""


class IngestionOrchestrator:
    """Apply P02-T01 deterministically to provider-neutral observations."""

    def __init__(
        self,
        *,
        context: IngestionContext,
        publisher: IngestionPublisher | None = None,
    ) -> None:
        if not isinstance(context, IngestionContext):
            raise ValueError("context is required")
        self.context = context
        self.publisher = publisher

    def process(
        self,
        observation: AdapterObservation,
        *,
        processing_time: datetime,
        reference_time: datetime,
    ) -> IngestionResult:
        """Process one observation using only explicit time and context."""

        observation_id = _observation_identity(observation)
        source_id = _source_text(getattr(observation, "source_id", None))
        kind = _enum_or_none(getattr(observation, "kind", None), ObservationKind)
        observed_time = getattr(observation, "observed_time", None)
        cursor = getattr(observation, "cursor", None)

        if not _is_aware_datetime(processing_time) or not _is_aware_datetime(reference_time):
            return self._emit(
                self._rejected(
                    observation_id,
                    source_id,
                    kind,
                    observed_time,
                    processing_time,
                    reference_time,
                    cursor,
                    ("processing_time and reference_time must be timezone-aware",),
                )
            )
        if not isinstance(observation, AdapterObservation):
            return self._emit(
                self._rejected(
                    observation_id,
                    source_id,
                    kind,
                    observed_time,
                    processing_time,
                    reference_time,
                    cursor,
                    ("observation must be an AdapterObservation",),
                )
            )

        errors = _validate_observation(observation)
        if errors:
            return self._emit(
                self._rejected(
                    observation_id,
                    source_id,
                    kind,
                    observed_time,
                    processing_time,
                    reference_time,
                    cursor,
                    errors,
                )
            )

        if observation.kind is ObservationKind.FAILURE:
            health = self.context.source_health.observe_failure(
                observation.source_id,
                observation.observed_time,
                observation.failure_reason or "source failure",
            )
            return self._emit(
                IngestionResult(
                    observation_id=observation_id,
                    source_id=observation.source_id,
                    kind=observation.kind,
                    outcome=IngestionOutcome.SOURCE_FAILURE,
                    quality_status=DataQuality.SOURCE_UNAVAILABLE,
                    state=None,
                    source_health=health,
                    observed_time=observation.observed_time,
                    processing_time=processing_time,
                    reference_time=reference_time,
                    cursor=observation.cursor,
                    contract_version=self.context.contract_version,
                    accepted=False,
                    published_as_current=False,
                    recovered=False,
                    resynchronization_required=observation.source_id
                    in self.context.resynchronization_required,
                    reasons=(observation.failure_reason or "source failure",),
                )
            )

        if observation.kind is ObservationKind.RESYNC_REQUIRED:
            self.context.resynchronization_required.add(observation.source_id)
            return self._emit(
                IngestionResult(
                    observation_id=observation_id,
                    source_id=observation.source_id,
                    kind=observation.kind,
                    outcome=IngestionOutcome.RESYNCHRONIZATION_REQUIRED,
                    quality_status=None,
                    state=None,
                    source_health=self.context.source_health.get(observation.source_id),
                    observed_time=observation.observed_time,
                    processing_time=processing_time,
                    reference_time=reference_time,
                    cursor=observation.cursor,
                    contract_version=self.context.contract_version,
                    accepted=False,
                    published_as_current=False,
                    recovered=False,
                    resynchronization_required=True,
                    reasons=("source requested resynchronization",),
                )
            )

        if observation.source_id in self.context.resynchronization_required and (
            observation.kind is not ObservationKind.RESYNC
        ):
            return self._emit(
                self._resync_result(
                    observation,
                    observation_id,
                    processing_time,
                    reference_time,
                    "resynchronization is required before accepting observations",
                )
            )

        resync_mode = observation.kind is ObservationKind.RESYNC
        health = self.context.source_health.get(observation.source_id)
        normalization_context = self.context.normalization
        if resync_mode:
            normalization_context = deepcopy(normalization_context)
            normalization_context.last_sequence_by_source.pop(observation.source_id, None)

        if health.status is SourceHealthStatus.FAILED:
            candidate_context = deepcopy(normalization_context)
            candidate = normalize_raw_event(
                observation.raw_event,
                processing_time=processing_time,
                reference_time=reference_time,
                freshness_policy=self.context.freshness_policy,
                context=candidate_context,
            )
            if candidate.quality_status is DataQuality.VALID:
                self.context.normalization = candidate_context
                return self._accepted_result(
                    observation,
                    observation_id,
                    candidate.state,
                    processing_time,
                    reference_time,
                    recovered=True,
                    resync_mode=resync_mode,
                )
            normalized = normalize_raw_event(
                observation.raw_event,
                processing_time=processing_time,
                reference_time=reference_time,
                freshness_policy=self.context.freshness_policy,
                context=self.context.normalization,
                source_health=health,
            )
        else:
            normalized = normalize_raw_event(
                observation.raw_event,
                processing_time=processing_time,
                reference_time=reference_time,
                freshness_policy=self.context.freshness_policy,
                context=normalization_context,
                source_health=health,
            )
            if resync_mode:
                self.context.normalization = normalization_context

        if normalized.quality_status is DataQuality.VALID:
            self.context.source_health.observe_success(
                observation.source_id,
                observation.observed_time,
                accepted_event=True,
            )
            self._record_cursor(observation)
            if resync_mode:
                self.context.resynchronization_required.discard(observation.source_id)
            return self._emit(
                IngestionResult(
                    observation_id=observation_id,
                    source_id=observation.source_id,
                    kind=observation.kind,
                    outcome=IngestionOutcome.SOURCE_RECOVERY
                    if health.status is SourceHealthStatus.FAILED
                    else IngestionOutcome.ACCEPTED,
                    quality_status=normalized.quality_status,
                    state=normalized.state,
                    source_health=self.context.source_health.get(observation.source_id),
                    observed_time=observation.observed_time,
                    processing_time=processing_time,
                    reference_time=reference_time,
                    cursor=_effective_cursor(observation),
                    contract_version=self.context.contract_version,
                    accepted=True,
                    published_as_current=True,
                    recovered=health.status is SourceHealthStatus.FAILED,
                    resynchronization_required=False,
                    reasons=normalized.errors,
                )
            )

        return self._emit(
            IngestionResult(
                observation_id=observation_id,
                source_id=observation.source_id,
                kind=observation.kind,
                outcome=IngestionOutcome.QUALITY_REJECTED,
                quality_status=normalized.quality_status,
                state=normalized.state,
                source_health=self.context.source_health.get(observation.source_id),
                observed_time=observation.observed_time,
                processing_time=processing_time,
                reference_time=reference_time,
                cursor=_effective_cursor(observation),
                contract_version=self.context.contract_version,
                accepted=False,
                published_as_current=False,
                recovered=False,
                resynchronization_required=observation.source_id
                in self.context.resynchronization_required,
                reasons=normalized.errors,
            )
        )

    def _accepted_result(
        self,
        observation: AdapterObservation,
        observation_id: str,
        state: NormalizedMarketState | None,
        processing_time: datetime,
        reference_time: datetime,
        *,
        recovered: bool,
        resync_mode: bool,
    ) -> IngestionResult:
        self.context.source_health.observe_success(
            observation.source_id,
            observation.observed_time,
            accepted_event=True,
        )
        self._record_cursor(observation)
        if resync_mode:
            self.context.resynchronization_required.discard(observation.source_id)
        return self._emit(
            IngestionResult(
                observation_id=observation_id,
                source_id=observation.source_id,
                kind=observation.kind,
                outcome=IngestionOutcome.SOURCE_RECOVERY if recovered else IngestionOutcome.ACCEPTED,
                quality_status=DataQuality.VALID,
                state=state,
                source_health=self.context.source_health.get(observation.source_id),
                observed_time=observation.observed_time,
                processing_time=processing_time,
                reference_time=reference_time,
                cursor=_effective_cursor(observation),
                contract_version=self.context.contract_version,
                accepted=True,
                published_as_current=True,
                recovered=recovered,
                resynchronization_required=False,
                reasons=(),
            )
        )

    def _record_cursor(self, observation: AdapterObservation) -> None:
        cursor = _effective_cursor(observation)
        if cursor is not None:
            self.context.cursor_by_source[observation.source_id] = cursor

    def _resync_result(
        self,
        observation: AdapterObservation,
        observation_id: str,
        processing_time: datetime,
        reference_time: datetime,
        reason: str,
    ) -> IngestionResult:
        return IngestionResult(
            observation_id=observation_id,
            source_id=observation.source_id,
            kind=observation.kind,
            outcome=IngestionOutcome.RESYNCHRONIZATION_REQUIRED,
            quality_status=None,
            state=None,
            source_health=self.context.source_health.get(observation.source_id),
            observed_time=observation.observed_time,
            processing_time=processing_time,
            reference_time=reference_time,
            cursor=_effective_cursor(observation),
            contract_version=self.context.contract_version,
            accepted=False,
            published_as_current=False,
            recovered=False,
            resynchronization_required=True,
            reasons=(reason,),
        )

    def _rejected(
        self,
        observation_id: str,
        source_id: str,
        kind: ObservationKind | None,
        observed_time: Any,
        processing_time: datetime | None,
        reference_time: datetime | None,
        cursor: SequenceValue,
        reasons: tuple[str, ...],
    ) -> IngestionResult:
        return IngestionResult(
            observation_id=observation_id,
            source_id=source_id,
            kind=kind,
            outcome=IngestionOutcome.OBSERVATION_REJECTED,
            quality_status=DataQuality.INVALID,
            state=None,
            source_health=None,
            observed_time=observed_time if _is_aware_datetime(observed_time) else None,
            processing_time=processing_time if _is_aware_datetime(processing_time) else None,
            reference_time=reference_time if _is_aware_datetime(reference_time) else None,
            cursor=cursor if _valid_sequence(cursor) else None,
            contract_version=self.context.contract_version,
            accepted=False,
            published_as_current=False,
            recovered=False,
            resynchronization_required=False,
            reasons=reasons,
        )

    def _emit(self, result: IngestionResult) -> IngestionResult:
        if self.publisher is not None:
            self.publisher.publish(result)
        return result


def _validate_observation(observation: AdapterObservation) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(observation.source_id, str) or not observation.source_id.strip():
        errors.append("source_id is required")
    if not isinstance(observation.kind, ObservationKind):
        errors.append("kind must be an ObservationKind")
    if not _is_aware_datetime(observation.observed_time):
        errors.append("observed_time must be a timezone-aware datetime")
    if not isinstance(observation.cursor_continuity, CursorContinuity):
        errors.append("cursor_continuity must be a CursorContinuity")
    if not _valid_sequence(observation.cursor):
        errors.append("cursor must be an integer or string when provided")
    if not isinstance(observation.source_metadata, Mapping):
        errors.append("source_metadata must be a mapping")
    elif not _is_canonical(observation.source_metadata):
        errors.append("source_metadata contains unsupported values")
    if observation.correlation_id is not None and (
        not isinstance(observation.correlation_id, str) or not observation.correlation_id.strip()
    ):
        errors.append("correlation_id must be a non-empty string when provided")

    if isinstance(observation.kind, ObservationKind):
        if observation.kind in {ObservationKind.EVENT, ObservationKind.RECOVERY, ObservationKind.RESYNC}:
            if not isinstance(observation.raw_event, RawEvent):
                errors.append("event observations require a RawEvent")
            elif observation.raw_event.source_id != observation.source_id:
                errors.append("raw_event source_id must match observation source_id")
            if observation.failure_reason is not None:
                errors.append("event observations must not include failure_reason")
        elif observation.kind is ObservationKind.FAILURE:
            if observation.raw_event is not None:
                errors.append("failure observations must not include raw_event")
            if not isinstance(observation.failure_reason, str) or not observation.failure_reason.strip():
                errors.append("failure observations require failure_reason")
        elif observation.kind is ObservationKind.RESYNC_REQUIRED:
            if observation.raw_event is not None:
                errors.append("resync-required observations must not include raw_event")
            if observation.failure_reason is not None:
                errors.append("resync-required observations must not include failure_reason")

        if observation.kind is ObservationKind.RESYNC and (
            observation.cursor_continuity is not CursorContinuity.CONTINUOUS
        ):
            errors.append("resync observations require CONTINUOUS cursor evidence")
    if isinstance(observation.raw_event, RawEvent):
        raw_cursor = observation.raw_event.sequence
        if observation.cursor is not None and raw_cursor is not None and observation.cursor != raw_cursor:
            errors.append("cursor must match raw_event sequence when both are provided")
    if (
        observation.cursor_continuity is CursorContinuity.DISCONTINUOUS
        and observation.kind is not ObservationKind.RESYNC_REQUIRED
    ):
        errors.append("cursor discontinuity requires a resynchronization observation")
    return tuple(errors)


def _effective_cursor(observation: AdapterObservation) -> SequenceValue:
    return observation.cursor if observation.cursor is not None else (
        observation.raw_event.sequence if observation.raw_event is not None else None
    )


def _observation_identity(observation: Any) -> str:
    if isinstance(observation, AdapterObservation) and isinstance(observation.raw_event, RawEvent):
        try:
            return f"{observation.source_id}:{observation.kind}:{canonical_identity(observation.raw_event)}"
        except ValueError:
            pass
    material = {
        "source_id": _source_text(getattr(observation, "source_id", None)),
        "kind": _source_text(getattr(observation, "kind", None)),
        "observed_time": _timestamp_text(getattr(observation, "observed_time", None)),
        "cursor": _safe_value(getattr(observation, "cursor", None)),
        "correlation_id": _safe_value(getattr(observation, "correlation_id", None)),
    }
    digest = hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return f"observation:{digest}"


def _enum_or_none(value: Any, enum_type: type[StrEnum]) -> StrEnum | None:
    return value if isinstance(value, enum_type) else None


def _source_text(value: Any) -> str:
    return value if isinstance(value, str) else "<invalid-source>"


def _timestamp_text(value: Any) -> str | None:
    return value.isoformat() if _is_aware_datetime(value) else None


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, StrEnum):
        return value.value
    return f"<unsupported:{type(value).__name__}>"


def _valid_sequence(value: Any) -> bool:
    return value is None or isinstance(value, (int, str))


def _is_aware_datetime(value: Any) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _is_canonical(value: Any) -> bool:
    try:
        _canonicalize(value)
    except ValueError:
        return False
    return True


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("mapping keys must be strings")
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ValueError(f"unsupported value type: {type(value).__name__}")