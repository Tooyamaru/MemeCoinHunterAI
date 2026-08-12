"""Deterministic, provider-neutral contracts for P02-T01.

This module deliberately contains no network, database, provider, trading, or
strategy behavior. It defines the boundary at which a future adapter can hand
data to the canonical domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import hashlib
import json
from typing import Any, Mapping, Protocol, TypeAlias


JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
Timestamp: TypeAlias = datetime | None
SequenceValue: TypeAlias = int | str | None


class DataQuality(StrEnum):
    """Observable quality states required by the P02-T01 contract."""

    VALID = "VALID"
    STALE = "STALE"
    INVALID = "INVALID"
    INCOMPLETE = "INCOMPLETE"
    DUPLICATE = "DUPLICATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    CONTRADICTORY = "CONTRADICTORY"


class OrderingStatus(StrEnum):
    """Ordering evidence attached to every normalized state."""

    NOT_PROVIDED = "NOT_PROVIDED"
    FIRST = "FIRST"
    IN_ORDER = "IN_ORDER"
    OUT_OF_ORDER = "OUT_OF_ORDER"


class SourceHealthStatus(StrEnum):
    """Current health state of a source, independent of process lifecycle."""

    UNKNOWN = "UNKNOWN"
    AVAILABLE = "AVAILABLE"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RawEvent:
    """Provider-neutral event envelope received from an adapter boundary."""

    source_id: str
    payload: Mapping[str, Any]
    received_time: Timestamp
    event_time: Timestamp = None
    source_event_id: str | None = None
    sequence: SequenceValue = None
    source_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FreshnessPolicy:
    """Explicit freshness policy; no production threshold is implicit."""

    stale_after: timedelta | None = None

    def __post_init__(self) -> None:
        if self.stale_after is not None and self.stale_after < timedelta(0):
            raise ValueError("stale_after must not be negative")


@dataclass
class NormalizationContext:
    """Explicit observation state used for duplicate and ordering decisions."""

    seen_identities: dict[str, str] = field(default_factory=dict)
    last_sequence_by_source: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceHealth:
    """Auditable source availability state and failure/recovery observations."""

    source_id: str
    status: SourceHealthStatus
    failure_observed_time: datetime | None = None
    recovery_observed_time: datetime | None = None
    reason: str | None = None


@dataclass
class SourceHealthTracker:
    """In-memory, deterministic source failure/recovery state machine."""

    _states: dict[str, SourceHealth] = field(default_factory=dict)

    def observe_failure(self, source_id: str, observed_time: datetime, reason: str) -> SourceHealth:
        _require_aware_datetime(observed_time, "observed_time")
        _require_source_id(source_id)
        if not reason.strip():
            raise ValueError("reason must not be empty")
        current = self._states.get(source_id)
        state = SourceHealth(
            source_id=source_id,
            status=SourceHealthStatus.FAILED,
            failure_observed_time=observed_time,
            recovery_observed_time=current.recovery_observed_time if current else None,
            reason=reason,
        )
        self._states[source_id] = state
        return state

    def observe_success(
        self,
        source_id: str,
        observed_time: datetime,
        *,
        accepted_event: bool,
    ) -> SourceHealth:
        """Accept a source observation and recover only on an accepted event."""

        _require_aware_datetime(observed_time, "observed_time")
        _require_source_id(source_id)
        current = self._states.get(source_id)
        if not accepted_event:
            return current or SourceHealth(source_id=source_id, status=SourceHealthStatus.UNKNOWN)
        if current is not None and current.status is SourceHealthStatus.FAILED:
            state = SourceHealth(
                source_id=source_id,
                status=SourceHealthStatus.AVAILABLE,
                failure_observed_time=current.failure_observed_time,
                recovery_observed_time=observed_time,
                reason=None,
            )
        else:
            state = SourceHealth(
                source_id=source_id,
                status=SourceHealthStatus.AVAILABLE,
                failure_observed_time=current.failure_observed_time if current else None,
                recovery_observed_time=current.recovery_observed_time if current else None,
            )
        self._states[source_id] = state
        return state

    def get(self, source_id: str) -> SourceHealth:
        _require_source_id(source_id)
        return self._states.get(
            source_id,
            SourceHealth(source_id=source_id, status=SourceHealthStatus.UNKNOWN),
        )


class ProviderNeutralAdapter(Protocol):
    """Boundary contract for future adapters; no provider type is required."""

    def adapt(self, source_input: object) -> RawEvent:
        """Translate an external value into a provider-neutral raw event."""


@dataclass(frozen=True)
class NormalizedMarketState:
    """Canonical state preserving provenance, timing, quality, and ordering."""

    identity: str
    source_id: str
    source_event_id: str | None
    payload: Mapping[str, JsonValue]
    event_time: Timestamp
    received_time: Timestamp
    processing_time: datetime
    data_age: timedelta | None
    quality_status: DataQuality
    sequence: SequenceValue
    ordering_status: OrderingStatus
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class NormalizationResult:
    """Result wrapper that keeps validation outcomes explicit and observable."""

    state: NormalizedMarketState | None
    quality_status: DataQuality
    errors: tuple[str, ...] = ()


def validate_raw_event(event: RawEvent) -> tuple[DataQuality, tuple[str, ...]]:
    """Validate required envelope metadata without replacing missing values."""

    errors: list[str] = []
    if not isinstance(event.source_id, str) or not event.source_id.strip():
        errors.append("source_id is required")
    if not isinstance(event.payload, Mapping):
        errors.append("payload must be a mapping")
    if not _is_aware_datetime(event.received_time):
        errors.append("received_time must be a timezone-aware datetime")
    if event.event_time is None:
        errors.append("event_time is required")
    elif not _is_aware_datetime(event.event_time):
        errors.append("event_time must be a timezone-aware datetime")
    if not isinstance(event.source_metadata, Mapping):
        errors.append("source_metadata must be a mapping")
    if event.source_event_id is not None and (
        not isinstance(event.source_event_id, str) or not event.source_event_id.strip()
    ):
        errors.append("source_event_id must be a non-empty string when provided")
    if event.sequence is not None and not isinstance(event.sequence, (int, str)):
        errors.append("sequence must be an integer or string when provided")
    if errors:
        malformed = any(
            phrase in " ".join(errors)
            for phrase in ("must be a mapping", "must be a timezone-aware", "must be an integer")
        )
        return (DataQuality.INVALID if malformed else DataQuality.INCOMPLETE, tuple(errors))

    try:
        _canonical_json(event.payload)
        _canonical_json(event.source_metadata)
    except ValueError as exc:
        return DataQuality.INVALID, (str(exc),)
    if event.event_time > event.received_time:
        return DataQuality.INVALID, ("event_time is later than received_time",)
    return DataQuality.VALID, ()


def canonical_identity(event: RawEvent) -> str:
    """Return a stable identity from source identity or canonical event content."""

    quality, errors = validate_raw_event(event)
    if quality is not DataQuality.VALID:
        raise ValueError("; ".join(errors))
    if event.source_event_id is not None:
        identity_material = {
            "source_id": event.source_id,
            "source_event_id": event.source_event_id,
        }
    else:
        identity_material = {
            "source_id": event.source_id,
            "event_time": _timestamp_text(event.event_time),
            "sequence": event.sequence,
            "payload": _canonicalize(event.payload),
        }
    digest = hashlib.sha256(_canonical_json(identity_material).encode("utf-8")).hexdigest()
    return f"{event.source_id}:{digest}"


def normalize_raw_event(
    event: RawEvent,
    *,
    processing_time: datetime,
    reference_time: datetime,
    freshness_policy: FreshnessPolicy,
    context: NormalizationContext | None = None,
    source_health: SourceHealth | None = None,
) -> NormalizationResult:
    """Validate and normalize one event using only explicit time/context inputs."""

    _require_aware_datetime(processing_time, "processing_time")
    _require_aware_datetime(reference_time, "reference_time")
    quality, errors = validate_raw_event(event)
    context = context or NormalizationContext()
    identity = _safe_identity(event)
    data_age = (
        reference_time - event.event_time
        if _is_aware_datetime(event.event_time)
        else None
    )
    reasons = list(errors)
    ordering_status = OrderingStatus.NOT_PROVIDED

    if (
        source_health is not None
        and source_health.source_id == event.source_id
        and source_health.status is SourceHealthStatus.FAILED
    ):
        quality = DataQuality.SOURCE_UNAVAILABLE
        reasons.append("source is unavailable")
    elif quality is DataQuality.VALID:
        if data_age is not None and data_age < timedelta(0):
            quality = DataQuality.INVALID
            reasons.append("event_time is later than reference_time")
        elif (
            data_age is not None
            and freshness_policy.stale_after is not None
            and data_age > freshness_policy.stale_after
        ):
            quality = DataQuality.STALE
            reasons.append("event exceeds configured freshness policy")
        elif identity in context.seen_identities:
            if context.seen_identities[identity] == _payload_fingerprint(event):
                quality = DataQuality.DUPLICATE
                reasons.append("event identity was already observed")
            else:
                quality = DataQuality.CONTRADICTORY
                reasons.append("identity maps to a different payload")
        elif isinstance(event.sequence, int):
            previous = context.last_sequence_by_source.get(event.source_id)
            if previous is None:
                ordering_status = OrderingStatus.FIRST
            elif event.sequence <= previous:
                quality = DataQuality.OUT_OF_ORDER
                ordering_status = OrderingStatus.OUT_OF_ORDER
                reasons.append("sequence is not greater than the last accepted sequence")
            else:
                ordering_status = OrderingStatus.IN_ORDER

    state = NormalizedMarketState(
        identity=identity,
        source_id=event.source_id,
        source_event_id=event.source_event_id,
        payload=_safe_payload(event.payload),
        event_time=event.event_time if _is_aware_datetime(event.event_time) else None,
        received_time=event.received_time if _is_aware_datetime(event.received_time) else None,
        processing_time=processing_time,
        data_age=data_age,
        quality_status=quality,
        sequence=event.sequence,
        ordering_status=ordering_status,
        reasons=tuple(reasons),
    )
    if quality in {DataQuality.VALID, DataQuality.STALE, DataQuality.OUT_OF_ORDER}:
        context.seen_identities[identity] = _payload_fingerprint(event)
        if quality is DataQuality.VALID and isinstance(event.sequence, int):
            context.last_sequence_by_source[event.source_id] = event.sequence
    return NormalizationResult(state=state, quality_status=quality, errors=tuple(reasons))


def _safe_identity(event: RawEvent) -> str:
    try:
        return canonical_identity(event)
    except ValueError:
        material = {
            "source_id": event.source_id if isinstance(event.source_id, str) else None,
            "source_event_id": event.source_event_id
            if isinstance(event.source_event_id, str)
            else None,
        }
        digest = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
        return f"invalid:{digest}"


def _payload_fingerprint(event: RawEvent) -> str:
    return hashlib.sha256(_canonical_json(_safe_payload(event.payload)).encode("utf-8")).hexdigest()


def _safe_payload(payload: Any) -> dict[str, JsonValue]:
    if not isinstance(payload, Mapping):
        return {}
    try:
        canonical = _canonicalize(payload)
    except ValueError:
        return {}
    return canonical if isinstance(canonical, dict) else {}


def _canonical_json(value: Any) -> str:
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


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


def _is_aware_datetime(value: Any) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _require_aware_datetime(value: Any, name: str) -> None:
    if not _is_aware_datetime(value):
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _require_source_id(source_id: str) -> None:
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("source_id must be a non-empty string")


def _timestamp_text(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value is not None else None