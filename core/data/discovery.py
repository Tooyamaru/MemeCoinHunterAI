"""Provider-neutral token discovery boundary for P02-T04.

The boundary consumes P02-T03 observations and produces auditable token
discovery records. It deliberately contains no chain validation, market data,
provider connectivity, persistence, strategy, or trading semantics.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
import hashlib
import json
from typing import Any, Mapping, Protocol

from core.data.contracts import (
    DataQuality,
    FreshnessPolicy,
    JsonValue,
    NormalizationContext,
    SequenceValue,
)
from core.data.orchestration import (
    AdapterObservation,
    CursorContinuity,
    ObservationKind,
)


class DiscoveryKind(StrEnum):
    """Provider-neutral token-universe observation kinds."""

    DISCOVERED = "DISCOVERED"
    METADATA_UPDATED = "METADATA_UPDATED"
    REMOVED = "REMOVED"
    RESYNC = "RESYNC"


class DiscoveryOutcome(StrEnum):
    """Structured result category for every discovery input."""

    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    INVALID = "INVALID"
    STALE = "STALE"
    CONTRADICTORY = "CONTRADICTORY"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    RESYNC_REQUIRED = "RESYNC_REQUIRED"
    UNAVAILABLE = "UNAVAILABLE"


class DiscoveryOrdering(StrEnum):
    """Ordering certainty retained on discovery records."""

    UNKNOWN = "UNKNOWN"
    FIRST = "FIRST"
    IN_ORDER = "IN_ORDER"
    OUT_OF_ORDER = "OUT_OF_ORDER"


@dataclass(frozen=True)
class DiscoveryObservation:
    """Canonical provider-neutral token discovery observation."""

    source_id: str
    kind: DiscoveryKind
    token_identity: str
    chain_id: str
    observation_time: datetime
    discovery_time: datetime
    source_event_id: str | None = None
    sequence: SequenceValue = None
    cursor_continuity: CursorContinuity = CursorContinuity.NOT_PROVIDED
    discovery_reason: str = "UNSPECIFIED"
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)
    source_metadata: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class DiscoveryProvenance:
    """Bounded provenance retained without storing an unbounded raw payload."""

    source_id: str
    source_event_id: str | None
    observation_time: datetime
    discovery_time: datetime
    sequence: SequenceValue
    source_metadata: Mapping[str, JsonValue]


@dataclass(frozen=True)
class TokenDiscoveryRecord:
    """Auditable token-universe record without market or trading fields."""

    discovery_id: str
    token_identity: str
    chain_id: str
    discovery_kind: DiscoveryKind
    discovery_reason: str
    quality_status: DataQuality
    ordering: DiscoveryOrdering
    data_age: Any
    metadata: Mapping[str, JsonValue]
    provenance: DiscoveryProvenance
    contract_version: str


@dataclass(frozen=True)
class DiscoveryResult:
    """Observable output for every discovery observation."""

    discovery_id: str
    source_id: str
    outcome: DiscoveryOutcome
    quality_status: DataQuality
    record: TokenDiscoveryRecord | None
    processing_time: datetime | None
    reference_time: datetime | None
    sequence: SequenceValue
    accepted: bool
    published_as_current: bool
    resynchronization_required: bool
    reasons: tuple[str, ...] = ()


class DiscoveryPublisher(Protocol):
    """Read-oriented publication boundary for discovery results."""

    def publish(self, result: DiscoveryResult) -> None:
        """Publish one result without requiring a transport."""


@dataclass
class DiscoveryContext:
    """Explicit mutable state required for deterministic discovery."""

    freshness_policy: FreshnessPolicy
    contract_version: str
    normalization: NormalizationContext = field(default_factory=NormalizationContext)
    last_sequence_by_source: dict[str, int] = field(default_factory=dict)
    resynchronization_required: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not isinstance(self.freshness_policy, FreshnessPolicy):
            raise ValueError("freshness_policy is required")
        if not isinstance(self.contract_version, str) or not self.contract_version.strip():
            raise ValueError("contract_version is required")


class InMemoryDiscoveryPublisher:
    """Deterministic local publisher used by contract tests."""

    def __init__(self) -> None:
        self.results: list[DiscoveryResult] = []

    def publish(self, result: DiscoveryResult) -> None:
        self.results.append(result)


class TokenDiscoveryBoundary:
    """Evaluate provider-neutral token observations with explicit context."""

    def __init__(
        self,
        *,
        context: DiscoveryContext,
        publisher: DiscoveryPublisher | None = None,
    ) -> None:
        if not isinstance(context, DiscoveryContext):
            raise ValueError("context is required")
        self.context = context
        self.publisher = publisher

    def process(
        self,
        observation: DiscoveryObservation | AdapterObservation,
        *,
        processing_time: datetime,
        reference_time: datetime,
    ) -> DiscoveryResult:
        """Process one direct or P02-T03 adapter observation deterministically."""

        if not _aware(processing_time) or not _aware(reference_time):
            return self._emit(
                self._invalid(
                    "<invalid-discovery>",
                    "<invalid-source>",
                    None,
                    processing_time,
                    reference_time,
                    ("processing_time and reference_time must be timezone-aware",),
                )
            )

        if isinstance(observation, AdapterObservation):
            if observation.kind is ObservationKind.FAILURE:
                return self._emit(
                    self._result(
                        discovery_id=_observation_id(observation),
                        source_id=observation.source_id,
                        outcome=DiscoveryOutcome.UNAVAILABLE,
                        quality_status=DataQuality.SOURCE_UNAVAILABLE,
                        record=None,
                        processing_time=processing_time,
                        reference_time=reference_time,
                        sequence=observation.cursor,
                        reasons=(observation.failure_reason or "source unavailable",),
                    )
                )
            if observation.kind is ObservationKind.RESYNC_REQUIRED:
                self.context.resynchronization_required.add(observation.source_id)
                return self._emit(
                    self._result(
                        discovery_id=_observation_id(observation),
                        source_id=observation.source_id,
                        outcome=DiscoveryOutcome.RESYNC_REQUIRED,
                        quality_status=DataQuality.INVALID,
                        record=None,
                        processing_time=processing_time,
                        reference_time=reference_time,
                        sequence=observation.cursor,
                        resynchronization_required=True,
                        reasons=("source requested resynchronization",),
                    )
                )
            try:
                observation = _from_adapter_observation(observation)
            except ValueError as exc:
                return self._emit(
                    self._invalid(
                        _observation_id(observation),
                        observation.source_id,
                        observation.cursor,
                        processing_time,
                        reference_time,
                        (str(exc),),
                    )
                )

        if not isinstance(observation, DiscoveryObservation):
            return self._emit(
                self._invalid(
                    "<invalid-discovery>",
                    "<invalid-source>",
                    None,
                    processing_time,
                    reference_time,
                    ("observation must be a DiscoveryObservation or AdapterObservation",),
                )
            )

        discovery_id = _discovery_id(observation)
        errors = _validate_observation(observation)
        if errors:
            return self._emit(
                self._invalid(
                    discovery_id,
                    _source_text(observation.source_id),
                    observation.sequence,
                    processing_time,
                    reference_time,
                    errors,
                )
            )

        if observation.source_id in self.context.resynchronization_required and (
            observation.kind is not DiscoveryKind.RESYNC
        ):
            return self._emit(
                self._result(
                    discovery_id=discovery_id,
                    source_id=observation.source_id,
                    outcome=DiscoveryOutcome.RESYNC_REQUIRED,
                    quality_status=DataQuality.INVALID,
                    record=None,
                    processing_time=processing_time,
                    reference_time=reference_time,
                    sequence=observation.sequence,
                    resynchronization_required=True,
                    reasons=("resynchronization is required before accepting discovery",),
                )
            )

        if observation.cursor_continuity is CursorContinuity.DISCONTINUOUS:
            self.context.resynchronization_required.add(observation.source_id)
            return self._emit(
                self._result(
                    discovery_id=discovery_id,
                    source_id=observation.source_id,
                    outcome=DiscoveryOutcome.RESYNC_REQUIRED,
                    quality_status=DataQuality.INVALID,
                    record=None,
                    processing_time=processing_time,
                    reference_time=reference_time,
                    sequence=observation.sequence,
                    resynchronization_required=True,
                    reasons=("cursor discontinuity requires resynchronization",),
                )
            )

        if observation.kind is DiscoveryKind.RESYNC:
            ordering = DiscoveryOrdering.FIRST
            self.context.last_sequence_by_source.pop(observation.source_id, None)
        else:
            ordering = self._ordering(observation)

        data_age = reference_time - observation.discovery_time
        if data_age < timedelta(0):
            return self._emit(
                self._record_result(
                    observation,
                    discovery_id,
                    DiscoveryOutcome.INVALID,
                    DataQuality.INVALID,
                    ordering,
                    processing_time,
                    reference_time,
                    ("discovery_time is later than reference_time",),
                )
            )
        if (
            self.context.freshness_policy.stale_after is not None
            and data_age > self.context.freshness_policy.stale_after
        ):
            return self._emit(
                self._record_result(
                    observation,
                    discovery_id,
                    DiscoveryOutcome.STALE,
                    DataQuality.STALE,
                    ordering,
                    processing_time,
                    reference_time,
                    ("discovery exceeds configured freshness policy",),
                )
            )

        fingerprint = _identity_fingerprint(observation)
        previous = self.context.normalization.seen_identities.get(discovery_id)
        if previous is not None:
            outcome = (
                DiscoveryOutcome.DUPLICATE
                if previous == fingerprint
                else DiscoveryOutcome.CONTRADICTORY
            )
            quality = DataQuality.DUPLICATE if previous == fingerprint else DataQuality.CONTRADICTORY
            return self._emit(
                self._record_result(
                    observation,
                    discovery_id,
                    outcome,
                    quality,
                    ordering,
                    processing_time,
                    reference_time,
                    (
                        "discovery identity was already observed"
                        if previous == fingerprint
                        else "discovery identity maps to different token identity",
                    ),
                )
            )

        if ordering is DiscoveryOrdering.OUT_OF_ORDER:
            return self._emit(
                self._record_result(
                    observation,
                    discovery_id,
                    DiscoveryOutcome.OUT_OF_ORDER,
                    DataQuality.OUT_OF_ORDER,
                    ordering,
                    processing_time,
                    reference_time,
                    ("sequence is not greater than the last accepted sequence",),
                )
            )

        self.context.normalization.seen_identities[discovery_id] = fingerprint
        if isinstance(observation.sequence, int):
            self.context.last_sequence_by_source[observation.source_id] = observation.sequence
        if observation.kind is DiscoveryKind.RESYNC:
            self.context.resynchronization_required.discard(observation.source_id)
        return self._emit(
            self._record_result(
                observation,
                discovery_id,
                DiscoveryOutcome.ACCEPTED,
                DataQuality.VALID,
                ordering,
                processing_time,
                reference_time,
                (),
                accepted=True,
                published_as_current=True,
                resynchronization_required=False,
            )
        )

    def _ordering(self, observation: DiscoveryObservation) -> DiscoveryOrdering:
        if not isinstance(observation.sequence, int):
            return DiscoveryOrdering.UNKNOWN
        previous = self.context.last_sequence_by_source.get(observation.source_id)
        if previous is None:
            return DiscoveryOrdering.FIRST
        if observation.sequence <= previous:
            return DiscoveryOrdering.OUT_OF_ORDER
        return DiscoveryOrdering.IN_ORDER

    def _record_result(
        self,
        observation: DiscoveryObservation,
        discovery_id: str,
        outcome: DiscoveryOutcome,
        quality_status: DataQuality,
        ordering: DiscoveryOrdering,
        processing_time: datetime,
        reference_time: datetime,
        reasons: tuple[str, ...],
        *,
        accepted: bool = False,
        published_as_current: bool = False,
        resynchronization_required: bool = False,
    ) -> DiscoveryResult:
        record = TokenDiscoveryRecord(
            discovery_id=discovery_id,
            token_identity=observation.token_identity,
            chain_id=observation.chain_id,
            discovery_kind=observation.kind,
            discovery_reason=observation.discovery_reason,
            quality_status=quality_status,
            ordering=ordering,
            data_age=reference_time - observation.discovery_time,
            metadata=deepcopy(dict(observation.metadata)),
            provenance=DiscoveryProvenance(
                source_id=observation.source_id,
                source_event_id=observation.source_event_id,
                observation_time=observation.observation_time,
                discovery_time=observation.discovery_time,
                sequence=observation.sequence,
                source_metadata=deepcopy(dict(observation.source_metadata)),
            ),
            contract_version=self.context.contract_version,
        )
        return self._result(
            discovery_id=discovery_id,
            source_id=observation.source_id,
            outcome=outcome,
            quality_status=quality_status,
            record=record,
            processing_time=processing_time,
            reference_time=reference_time,
            sequence=observation.sequence,
            accepted=accepted,
            published_as_current=published_as_current,
            resynchronization_required=resynchronization_required,
            reasons=reasons,
        )

    def _invalid(
        self,
        discovery_id: str,
        source_id: str,
        sequence: SequenceValue,
        processing_time: datetime | None,
        reference_time: datetime | None,
        reasons: tuple[str, ...],
    ) -> DiscoveryResult:
        return self._result(
            discovery_id=discovery_id,
            source_id=source_id,
            outcome=DiscoveryOutcome.INVALID,
            quality_status=DataQuality.INVALID,
            record=None,
            processing_time=processing_time if _aware(processing_time) else None,
            reference_time=reference_time if _aware(reference_time) else None,
            sequence=sequence,
            reasons=reasons,
        )

    def _result(self, **kwargs: Any) -> DiscoveryResult:
        kwargs.setdefault("accepted", kwargs.get("outcome") is DiscoveryOutcome.ACCEPTED)
        kwargs.setdefault(
            "published_as_current",
            kwargs.get("outcome") is DiscoveryOutcome.ACCEPTED,
        )
        kwargs.setdefault(
            "resynchronization_required",
            kwargs.get("outcome") is DiscoveryOutcome.RESYNC_REQUIRED,
        )
        return DiscoveryResult(**kwargs)

    def _emit(self, result: DiscoveryResult) -> DiscoveryResult:
        if self.publisher is not None:
            self.publisher.publish(result)
        return result


def _from_adapter_observation(observation: AdapterObservation) -> DiscoveryObservation:
    if observation.raw_event is None:
        raise ValueError("discovery observations require a RawEvent")
    payload = observation.raw_event.payload
    if not isinstance(payload, Mapping):
        raise ValueError("raw event payload must be a mapping")
    kind_value = payload.get("discovery_kind", DiscoveryKind.DISCOVERED.value)
    try:
        kind = DiscoveryKind(kind_value)
    except ValueError as exc:
        raise ValueError("discovery_kind must be a supported DiscoveryKind") from exc
    metadata = payload.get("metadata", {})
    reason = payload.get("discovery_reason", "UNSPECIFIED")
    chain_id = payload.get("chain_id")
    token_identity = payload.get("token_identity")
    if not isinstance(metadata, Mapping):
        raise ValueError("metadata must be a mapping")
    if not isinstance(chain_id, str) or not chain_id.strip():
        raise ValueError("chain_id is required")
    if not isinstance(token_identity, str) or not token_identity.strip():
        raise ValueError("token_identity is required")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("discovery_reason must be a non-empty string")
    return DiscoveryObservation(
        source_id=observation.source_id,
        kind=kind,
        token_identity=token_identity,
        chain_id=chain_id,
        observation_time=observation.observed_time,
        discovery_time=observation.raw_event.event_time,
        source_event_id=observation.raw_event.source_event_id,
        sequence=observation.cursor
        if observation.cursor is not None
        else observation.raw_event.sequence,
        cursor_continuity=observation.cursor_continuity,
        discovery_reason=reason,
        metadata=metadata,
        source_metadata=observation.source_metadata,
    )


def _validate_observation(observation: DiscoveryObservation) -> tuple[str, ...]:
    errors: list[str] = []
    for name, value in (
        ("source_id", observation.source_id),
        ("token_identity", observation.token_identity),
        ("chain_id", observation.chain_id),
        ("discovery_reason", observation.discovery_reason),
    ):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name} is required")
    if not isinstance(observation.kind, DiscoveryKind):
        errors.append("kind must be a DiscoveryKind")
    if not _aware(observation.observation_time):
        errors.append("observation_time must be timezone-aware")
    if not _aware(observation.discovery_time):
        errors.append("discovery_time must be timezone-aware")
    if not isinstance(observation.cursor_continuity, CursorContinuity):
        errors.append("cursor_continuity must be a CursorContinuity")
    if observation.sequence is not None and not isinstance(observation.sequence, (int, str)):
        errors.append("sequence must be an integer or string when provided")
    if observation.source_event_id is not None and (
        not isinstance(observation.source_event_id, str)
        or not observation.source_event_id.strip()
    ):
        errors.append("source_event_id must be a non-empty string when provided")
    if not isinstance(observation.metadata, Mapping):
        errors.append("metadata must be a mapping")
    elif not _canonical(observation.metadata):
        errors.append("metadata contains unsupported values")
    if not isinstance(observation.source_metadata, Mapping):
        errors.append("source_metadata must be a mapping")
    elif not _canonical(observation.source_metadata):
        errors.append("source_metadata contains unsupported values")
    if (
        isinstance(observation.sequence, int)
        and observation.sequence < 0
    ):
        errors.append("sequence must not be negative")
    return tuple(errors)


def _discovery_id(observation: DiscoveryObservation) -> str:
    if observation.source_event_id:
        return f"{observation.source_id}:{observation.source_event_id}"
    material = {
        "source_id": observation.source_id,
        "chain_id": observation.chain_id,
        "token_identity": observation.token_identity,
        "discovery_time": _timestamp(observation.discovery_time),
        "sequence": observation.sequence,
    }
    return f"{observation.source_id}:discovery:{_digest(material)}"


def _observation_id(observation: AdapterObservation) -> str:
    material = {
        "source_id": observation.source_id,
        "kind": str(observation.kind),
        "observed_time": _timestamp(observation.observed_time),
        "cursor": observation.cursor,
    }
    return f"{observation.source_id}:observation:{_digest(material)}"


def _identity_fingerprint(observation: DiscoveryObservation) -> str:
    return _digest(
        {
            "token_identity": observation.token_identity,
            "chain_id": observation.chain_id,
            "kind": observation.kind.value,
            "metadata": _canonicalize(observation.metadata),
        }
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _canonical(value: Any) -> bool:
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


def _timestamp(value: datetime) -> str:
    return value.isoformat() if _aware(value) else "<invalid-time>"


def _aware(value: Any) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _source_text(value: Any) -> str:
    return value if isinstance(value, str) else "<invalid-source>"