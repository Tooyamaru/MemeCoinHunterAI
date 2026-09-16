"""Pure, provider-neutral P08 read-only market-data observations.

This module deliberately owns no source client, transport, persistence, clock,
or mutable global state.  It validates explicit immutable values supplied by a
caller and returns deterministic evidence-only results.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import hashlib
import json
import re
import unicodedata
from types import MappingProxyType
from typing import Any, Mapping, TypeAlias


CONTRACT_VERSION = "p08-read-only-market-data-observation-v1"
P08_READ_ONLY_MARKET_DATA_CONTRACT_VERSION = CONTRACT_VERSION

MAX_CANONICAL_TEXT_SCALARS = 256
MAX_CANONICAL_TEXT_BYTES = 1024
MAX_BOUNDED_MAPPING_DEPTH = 8
MAX_BOUNDED_MAPPING_MEMBERS = 64
MAX_IMMUTABLE_SEQUENCE_ELEMENTS = 128
MAX_BOUNDED_MAPPING_BYTES = 16_384

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_NON_NEGATIVE_INTEGER_RE = re.compile(r"^(?:0|[1-9][0-9]{0,19})$")
_SUPPORTED_METRICS = frozenset(
    {"price", "liquidity", "volume", "asset_age", "holders", "transactions"}
)
_REQUIRED_METRICS = frozenset({"price", "liquidity", "volume", "asset_age"})
_OPTIONAL_METRICS = frozenset({"holders", "transactions"})


class ObservationKind(StrEnum):
    DISCOVERY = "DISCOVERY"
    PAPER_EVALUATION = "PAPER_EVALUATION"


class FieldStatus(StrEnum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


class FreshnessBoundary(StrEnum):
    INCLUSIVE = "INCLUSIVE"
    EXCLUSIVE = "EXCLUSIVE"


class OrderingStatus(StrEnum):
    ORDERED = "ORDERED"
    UNORDERED = "UNORDERED"
    UNKNOWN = "UNKNOWN"


class ReasonCode(StrEnum):
    INVALID_TYPE = "INVALID_TYPE"
    MISSING_REQUIRED_INPUT = "MISSING_REQUIRED_INPUT"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    INVALID_CANONICAL_REPRESENTATION = "INVALID_CANONICAL_REPRESENTATION"
    DIGEST_MISMATCH = "DIGEST_MISMATCH"
    INVALID_IDENTITY = "INVALID_IDENTITY"
    PROVENANCE_FAILURE = "PROVENANCE_FAILURE"
    CONTRADICTORY_INPUT = "CONTRADICTORY_INPUT"
    FUTURE_OBSERVATION = "FUTURE_OBSERVATION"
    STALE_OBSERVATION = "STALE_OBSERVATION"
    UNAVAILABLE_INPUT = "UNAVAILABLE_INPUT"
    INCOMPLETE_INPUT = "INCOMPLETE_INPUT"
    UNSUPPORTED_FIELD = "UNSUPPORTED_FIELD"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    REPLAY = "REPLAY"
    DUPLICATE = "DUPLICATE"
    DETERMINISM_FAILURE = "DETERMINISM_FAILURE"
    VALID = "VALID"


REASON_PRECEDENCE: tuple[ReasonCode, ...] = (
    ReasonCode.INVALID_TYPE,
    ReasonCode.MISSING_REQUIRED_INPUT,
    ReasonCode.UNSUPPORTED_VERSION,
    ReasonCode.INVALID_CANONICAL_REPRESENTATION,
    ReasonCode.DIGEST_MISMATCH,
    ReasonCode.INVALID_IDENTITY,
    ReasonCode.PROVENANCE_FAILURE,
    ReasonCode.CONTRADICTORY_INPUT,
    ReasonCode.FUTURE_OBSERVATION,
    ReasonCode.STALE_OBSERVATION,
    ReasonCode.UNAVAILABLE_INPUT,
    ReasonCode.INCOMPLETE_INPUT,
    ReasonCode.UNSUPPORTED_FIELD,
    ReasonCode.OUT_OF_ORDER,
    ReasonCode.REPLAY,
    ReasonCode.DUPLICATE,
    ReasonCode.DETERMINISM_FAILURE,
    ReasonCode.VALID,
)


class _ContractError(ValueError):
    def __init__(self, reason: ReasonCode, message: str = "") -> None:
        super().__init__(message or reason.value)
        self.reason = reason


def _freeze(value: Any, *, allow_int: bool = False) -> Any:
    """Recursively freeze caller-owned mappings and sequences."""

    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if allow_int:
            return value
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    if isinstance(value, float):
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
        return MappingProxyType(
            {key: _freeze(value[key], allow_int=allow_int) for key in sorted(value)}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item, allow_int=allow_int) for item in value)
    if isinstance(value, set):
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    return value


def _canonical_text(value: Any) -> str:
    if not isinstance(value, str):
        raise _ContractError(ReasonCode.INVALID_TYPE)
    normalized = unicodedata.normalize("NFC", value)
    trimmed = normalized.strip()
    if value != normalized or normalized != trimmed or not trimmed:
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    if any(0xD800 <= ord(char) <= 0xDFFF for char in trimmed):
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    if len(trimmed) > MAX_CANONICAL_TEXT_SCALARS:
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    try:
        encoded = trimmed.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION) from exc
    if len(encoded) > MAX_CANONICAL_TEXT_BYTES:
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    return trimmed


def _nullable_text(value: Any) -> str | None:
    if value is None:
        return None
    return _canonical_text(value)


def _decimal_text(value: Any) -> str:
    if not isinstance(value, str):
        raise _ContractError(ReasonCode.INVALID_TYPE)
    if not _DECIMAL_RE.fullmatch(value):
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    if value == "-0":
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    integer, separator, fraction = value.partition(".")
    if fraction:
        if fraction.endswith("0"):
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
        if integer == "-0":
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    if integer.startswith("-"):
        digits = integer[1:]
        if len(digits) > 1 and digits.startswith("0"):
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    elif len(integer) > 1 and integer.startswith("0"):
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    return value


def _non_negative_integer(value: Any) -> str:
    if not isinstance(value, str):
        raise _ContractError(ReasonCode.INVALID_TYPE)
    if not _NON_NEGATIVE_INTEGER_RE.fullmatch(value):
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    if int(value) > 99_999_999_999_999_999_999:
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    return value


def _timestamp(value: Any) -> str:
    if not isinstance(value, datetime):
        raise _ContractError(ReasonCode.INVALID_TYPE)
    if value.tzinfo is None or value.utcoffset() is None:
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    utc = value.astimezone(timezone.utc)
    return utc.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    if not isinstance(value, str):
        raise _ContractError(ReasonCode.INVALID_TYPE)
    if not _DIGEST_RE.fullmatch(value):
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    return value


def _wire(value: Any, *, allow_sequence_int: bool = True) -> Any:
    """Convert an already validated value into canonical JSON-compatible data."""

    if isinstance(value, StrEnum):
        return value.value
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if allow_sequence_int:
            return value
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    if isinstance(value, float):
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
        return {key: _wire(value[key], allow_sequence_int=allow_sequence_int) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_wire(item, allow_sequence_int=allow_sequence_int) for item in value]
    raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)


def canonical_json(value: Any) -> str:
    """Return compact canonical UTF-8 JSON text for a validated wire value."""

    return json.dumps(
        _wire(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def sha256_digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(
        term in normalized
        for term in (
            "secret",
            "password",
            "credential",
            "api_key",
            "access_token",
            "private_key",
            "seed_phrase",
            "signing",
        )
    )


def _validate_bounded(
    value: Any,
    *,
    depth: int = 1,
    allow_sequence_int: bool = False,
    path: str = "",
) -> Any:
    if depth > MAX_BOUNDED_MAPPING_DEPTH:
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION, path)
    if value is None or isinstance(value, (bool, str)):
        if isinstance(value, str):
            _canonical_text(value)
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if not allow_sequence_int:
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION, path)
        return value
    if isinstance(value, float) or isinstance(value, (set, frozenset)):
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION, path)
    if isinstance(value, Mapping):
        if len(value) > MAX_BOUNDED_MAPPING_MEMBERS:
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION, path)
        if not all(isinstance(key, str) for key in value):
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION, path)
        for key in value:
            _canonical_text(key)
            if _sensitive_key(key):
                raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION, path)
        result = {
            key: _validate_bounded(
                value[key],
                depth=depth + 1,
                allow_sequence_int=allow_sequence_int,
                path=f"{path}.{key}",
            )
            for key in sorted(value)
        }
        try:
            encoded = canonical_bytes(result)
        except (TypeError, ValueError, _ContractError) as exc:
            if isinstance(exc, _ContractError):
                raise
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION, path) from exc
        if len(encoded) > MAX_BOUNDED_MAPPING_BYTES:
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION, path)
        return result
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_IMMUTABLE_SEQUENCE_ELEMENTS:
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION, path)
        return [
            _validate_bounded(
                item,
                depth=depth + 1,
                allow_sequence_int=allow_sequence_int,
                path=f"{path}[{index}]",
            )
            for index, item in enumerate(value)
        ]
    raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION, path)


def _enum(value: Any, enum_type: type[StrEnum]) -> StrEnum:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError as exc:
            raise _ContractError(ReasonCode.UNSUPPORTED_VERSION) from exc
    raise _ContractError(ReasonCode.INVALID_TYPE)


def _version(value: Any, *, exact: str | None = None) -> str:
    text = _canonical_text(value)
    if exact is not None and text != exact:
        raise _ContractError(ReasonCode.UNSUPPORTED_VERSION)
    if exact is None and not (text == "v1" or text.endswith("-v1")):
        raise _ContractError(ReasonCode.UNSUPPORTED_VERSION)
    return text


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _ContractError(ReasonCode.INVALID_TYPE, name)
    return value


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime
    boundary: FreshnessBoundary | str

    def __post_init__(self) -> None:
        if isinstance(self.boundary, str):
            try:
                object.__setattr__(self, "boundary", FreshnessBoundary(self.boundary))
            except ValueError:
                pass


@dataclass(frozen=True)
class MetricEnvelope:
    status: FieldStatus | str
    value: Mapping[str, Any] | None
    unit: str | None
    semantic_version: str | None
    measurement_window: TimeWindow | None
    reference_semantics: str | None
    source_field: str | None
    field_digest: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            try:
                object.__setattr__(self, "status", FieldStatus(self.status))
            except ValueError:
                pass
        if isinstance(self.value, Mapping):
            object.__setattr__(self, "value", _freeze(self.value))
        if self.field_digest is None:
            try:
                object.__setattr__(
                    self,
                    "field_digest",
                    sha256_digest(_metric_material(self, include_digest=False)),
                )
            except (TypeError, ValueError, _ContractError):
                pass

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> MetricEnvelope:
        return cls(
            status=value.get("status"),
            value=value.get("value"),
            unit=value.get("unit"),
            semantic_version=value.get("semantic_version"),
            measurement_window=_time_window_from_mapping(value.get("measurement_window")),
            reference_semantics=value.get("reference_semantics"),
            source_field=value.get("source_field"),
            field_digest=value.get("field_digest"),
        )


@dataclass(frozen=True)
class SourceEnvelope:
    source_id: str
    source_event_id: str | None
    source_contract_version: str
    adapter_contract_version: str
    source_observed_at: datetime | None
    source_metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        if isinstance(self.source_metadata, Mapping):
            object.__setattr__(self, "source_metadata", _freeze(self.source_metadata))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> SourceEnvelope:
        return cls(
            source_id=value.get("source_id"),
            source_event_id=value.get("source_event_id"),
            source_contract_version=value.get("source_contract_version"),
            adapter_contract_version=value.get("adapter_contract_version"),
            source_observed_at=value.get("source_observed_at"),
            source_metadata=value.get("source_metadata"),
        )


@dataclass(frozen=True)
class ProvenanceEnvelope:
    source_id: str
    source_event_id: str | None
    candidate_id: str
    chain_id: str | None
    token_identity: str
    market_subject_id: str | None
    observation_id: str
    observed_at: datetime
    availability_at: datetime
    cutoff_time: datetime
    freshness_policy_version: str
    consumer_profile_version: str
    predecessor_digest: str | None
    field_provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        if isinstance(self.field_provenance, Mapping):
            object.__setattr__(self, "field_provenance", _freeze(self.field_provenance))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ProvenanceEnvelope:
        return cls(
            source_id=value.get("source_id"),
            source_event_id=value.get("source_event_id"),
            candidate_id=value.get("candidate_id"),
            chain_id=value.get("chain_id"),
            token_identity=value.get("token_identity"),
            market_subject_id=value.get("market_subject_id"),
            observation_id=value.get("observation_id"),
            observed_at=value.get("observed_at"),
            availability_at=value.get("availability_at"),
            cutoff_time=value.get("cutoff_time"),
            freshness_policy_version=value.get("freshness_policy_version"),
            consumer_profile_version=value.get("consumer_profile_version"),
            predecessor_digest=value.get("predecessor_digest"),
            field_provenance=value.get("field_provenance"),
        )


@dataclass(frozen=True)
class EvaluationContext:
    cutoff_time: datetime
    freshness_policy_version: str
    max_age_seconds: str | None
    freshness_boundary: FreshnessBoundary | str
    consumer_profile_version: str
    required_fields: tuple[str, ...]
    permitted_optional_fields: tuple[str, ...]
    predecessor_context_digest: str | None
    processing_context_identity: str

    def __post_init__(self) -> None:
        if isinstance(self.freshness_boundary, str):
            try:
                object.__setattr__(
                    self,
                    "freshness_boundary",
                    FreshnessBoundary(self.freshness_boundary),
                )
            except ValueError:
                pass
        if isinstance(self.required_fields, (list, tuple)):
            object.__setattr__(self, "required_fields", tuple(self.required_fields))
        if isinstance(self.permitted_optional_fields, (list, tuple)):
            object.__setattr__(
                self,
                "permitted_optional_fields",
                tuple(self.permitted_optional_fields),
            )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> EvaluationContext:
        return cls(
            cutoff_time=value.get("cutoff_time"),
            freshness_policy_version=value.get("freshness_policy_version"),
            max_age_seconds=value.get("max_age_seconds"),
            freshness_boundary=value.get("freshness_boundary"),
            consumer_profile_version=value.get("consumer_profile_version"),
            required_fields=tuple(value.get("required_fields", ())),
            permitted_optional_fields=tuple(value.get("permitted_optional_fields", ())),
            predecessor_context_digest=value.get("predecessor_context_digest"),
            processing_context_identity=value.get("processing_context_identity"),
        )


@dataclass(frozen=True)
class ReadOnlyMarketDataObservation:
    contract_version: str
    observation_id: str
    candidate_id: str
    chain_id: str | None
    token_identity: str
    market_subject_id: str | None
    observation_kind: ObservationKind | str
    observed_at: datetime
    availability_at: datetime
    sequence: int | str | None
    ordering_status: OrderingStatus | str
    source: SourceEnvelope
    provenance: ProvenanceEnvelope
    metrics: Mapping[str, MetricEnvelope]
    evaluation_context: EvaluationContext
    raw_payload_digest: str
    observation_digest: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.observation_kind, str):
            try:
                object.__setattr__(
                    self, "observation_kind", ObservationKind(self.observation_kind)
                )
            except ValueError:
                pass
        if isinstance(self.ordering_status, str):
            try:
                object.__setattr__(
                    self, "ordering_status", OrderingStatus(self.ordering_status)
                )
            except ValueError:
                pass
        if isinstance(self.metrics, Mapping):
            object.__setattr__(
                self,
                "metrics",
                MappingProxyType(
                    {
                        key: value
                        for key, value in sorted(self.metrics.items())
                    }
                ),
            )
        if self.observation_digest is None:
            try:
                object.__setattr__(
                    self,
                    "observation_digest",
                    sha256_digest(_observation_material(self, include_digest=False)),
                )
            except (TypeError, ValueError, _ContractError):
                pass

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ReadOnlyMarketDataObservation:
        metrics_value = value.get("metrics", {})
        metrics = {
            name: (
                item
                if isinstance(item, MetricEnvelope)
                else MetricEnvelope.from_mapping(item)
            )
            for name, item in metrics_value.items()
        }
        source = value.get("source")
        provenance = value.get("provenance")
        context = value.get("evaluation_context")
        return cls(
            contract_version=value.get("contract_version"),
            observation_id=value.get("observation_id"),
            candidate_id=value.get("candidate_id"),
            chain_id=value.get("chain_id"),
            token_identity=value.get("token_identity"),
            market_subject_id=value.get("market_subject_id"),
            observation_kind=value.get("observation_kind"),
            observed_at=value.get("observed_at"),
            availability_at=value.get("availability_at"),
            sequence=value.get("sequence"),
            ordering_status=value.get("ordering_status"),
            source=source if isinstance(source, SourceEnvelope) else SourceEnvelope.from_mapping(source),
            provenance=(
                provenance
                if isinstance(provenance, ProvenanceEnvelope)
                else ProvenanceEnvelope.from_mapping(provenance)
            ),
            metrics=metrics,
            evaluation_context=(
                context
                if isinstance(context, EvaluationContext)
                else EvaluationContext.from_mapping(context)
            ),
            raw_payload_digest=value.get("raw_payload_digest"),
            observation_digest=value.get("observation_digest"),
        )


@dataclass(frozen=True)
class ProcessingContext:
    """Explicit immutable state used for replay, duplicate, and ordering checks."""

    processing_context_identity: str
    accepted_fingerprints: Mapping[str, str] = field(default_factory=dict)
    replay_fingerprints: tuple[str, ...] = ()
    latest_sequences: Mapping[str, int] = field(default_factory=dict)
    prior_context_identity: str | None = None
    context_digest: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.accepted_fingerprints, Mapping):
            object.__setattr__(
                self,
                "accepted_fingerprints",
                MappingProxyType(dict(sorted(self.accepted_fingerprints.items()))),
            )
        if isinstance(self.latest_sequences, Mapping):
            object.__setattr__(
                self,
                "latest_sequences",
                MappingProxyType(dict(sorted(self.latest_sequences.items()))),
            )
        if isinstance(self.replay_fingerprints, list):
            object.__setattr__(self, "replay_fingerprints", tuple(self.replay_fingerprints))
        if self.context_digest is None:
            try:
                object.__setattr__(self, "context_digest", self.compute_digest())
            except (TypeError, ValueError, _ContractError):
                pass

    def compute_digest(self) -> str:
        return hashlib.sha256(
            canonical_bytes(
                {
                    "processing_context_identity": self.processing_context_identity,
                    "accepted_fingerprints": dict(self.accepted_fingerprints),
                    "replay_fingerprints": list(self.replay_fingerprints),
                    "latest_sequences": dict(self.latest_sequences),
                    "prior_context_identity": self.prior_context_identity,
                }
            )
        ).hexdigest()

    def record(
        self,
        observation: ReadOnlyMarketDataObservation,
        evaluation_context: EvaluationContext,
    ) -> ProcessingContext:
        request = _request_fingerprint(
            observation,
            evaluation_context,
            self,
        )
        accepted = dict(self.accepted_fingerprints)
        accepted[observation.observation_id] = observation.observation_digest or ""
        replay = tuple((*self.replay_fingerprints, request))
        sequences = dict(self.latest_sequences)
        if isinstance(observation.sequence, int) and not isinstance(observation.sequence, bool):
            sequences[_sequence_key(observation)] = observation.sequence
        return ProcessingContext(
            processing_context_identity=self.processing_context_identity,
            accepted_fingerprints=accepted,
            replay_fingerprints=replay,
            latest_sequences=sequences,
            prior_context_identity=self.context_digest,
        )


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    reason_code: ReasonCode
    observation: ReadOnlyMarketDataObservation | None
    observation_digest: str | None
    processing_context_identity: str | None
    state_changed: bool
    provenance: ProvenanceEnvelope | None
    next_context: ProcessingContext | None = None

    @property
    def valid(self) -> bool:
        return self.accepted and self.reason_code is ReasonCode.VALID


def _time_window_from_mapping(value: Any) -> TimeWindow | None:
    if value is None or isinstance(value, TimeWindow):
        return value
    if isinstance(value, Mapping):
        return TimeWindow(
            start=value.get("start"),
            end=value.get("end"),
            boundary=value.get("boundary"),
        )
    return value


def _metric_material(metric: MetricEnvelope, *, include_digest: bool) -> dict[str, Any]:
    material: dict[str, Any] = {
        "status": metric.status,
        "value": metric.value,
        "unit": metric.unit,
        "semantic_version": metric.semantic_version,
        "measurement_window": (
            {
                "start": _timestamp(metric.measurement_window.start),
                "end": _timestamp(metric.measurement_window.end),
                "boundary": metric.measurement_window.boundary,
            }
            if isinstance(metric.measurement_window, TimeWindow)
            else metric.measurement_window
        ),
        "reference_semantics": metric.reference_semantics,
        "source_field": metric.source_field,
    }
    if include_digest:
        material["field_digest"] = metric.field_digest
    return material


def _source_material(source: SourceEnvelope) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "source_event_id": source.source_event_id,
        "source_contract_version": source.source_contract_version,
        "adapter_contract_version": source.adapter_contract_version,
        "source_observed_at": (
            _timestamp(source.source_observed_at)
            if source.source_observed_at is not None
            else None
        ),
        "source_metadata": source.source_metadata,
    }


def _provenance_material(provenance: ProvenanceEnvelope) -> dict[str, Any]:
    return {
        "source_id": provenance.source_id,
        "source_event_id": provenance.source_event_id,
        "candidate_id": provenance.candidate_id,
        "chain_id": provenance.chain_id,
        "token_identity": provenance.token_identity,
        "market_subject_id": provenance.market_subject_id,
        "observation_id": provenance.observation_id,
        "observed_at": _timestamp(provenance.observed_at),
        "availability_at": _timestamp(provenance.availability_at),
        "cutoff_time": _timestamp(provenance.cutoff_time),
        "freshness_policy_version": provenance.freshness_policy_version,
        "consumer_profile_version": provenance.consumer_profile_version,
        "predecessor_digest": provenance.predecessor_digest,
        "field_provenance": provenance.field_provenance,
    }


def _context_material(context: EvaluationContext) -> dict[str, Any]:
    return {
        "cutoff_time": _timestamp(context.cutoff_time),
        "freshness_policy_version": context.freshness_policy_version,
        "max_age_seconds": context.max_age_seconds,
        "freshness_boundary": context.freshness_boundary,
        "consumer_profile_version": context.consumer_profile_version,
        "required_fields": list(context.required_fields),
        "permitted_optional_fields": list(context.permitted_optional_fields),
        "predecessor_context_digest": context.predecessor_context_digest,
        "processing_context_identity": context.processing_context_identity,
    }


def _observation_material(
    observation: ReadOnlyMarketDataObservation,
    *,
    include_digest: bool,
) -> dict[str, Any]:
    material: dict[str, Any] = {
        "contract_version": observation.contract_version,
        "observation_id": observation.observation_id,
        "candidate_id": observation.candidate_id,
        "chain_id": observation.chain_id,
        "token_identity": observation.token_identity,
        "market_subject_id": observation.market_subject_id,
        "observation_kind": observation.observation_kind,
        "observed_at": _timestamp(observation.observed_at),
        "availability_at": _timestamp(observation.availability_at),
        "sequence": observation.sequence,
        "ordering_status": observation.ordering_status,
        "source": _source_material(observation.source),
        "provenance": _provenance_material(observation.provenance),
        "metrics": {
            name: _metric_material(metric, include_digest=True)
            for name, metric in observation.metrics.items()
        },
        "evaluation_context": _context_material(observation.evaluation_context),
        "raw_payload_digest": observation.raw_payload_digest,
    }
    if include_digest:
        material["observation_digest"] = observation.observation_digest
    return material


def canonical_observation(observation: ReadOnlyMarketDataObservation) -> Mapping[str, Any]:
    """Return the complete canonical observation mapping, including its digest."""

    if not isinstance(observation, ReadOnlyMarketDataObservation):
        raise ValueError("observation must be a ReadOnlyMarketDataObservation")
    return _observation_material(observation, include_digest=True)


def observation_digest(observation: ReadOnlyMarketDataObservation) -> str:
    return hashlib.sha256(
        canonical_bytes(_observation_material(observation, include_digest=False))
    ).hexdigest()


def derive_observation_id(
    observation: ReadOnlyMarketDataObservation | Mapping[str, Any],
) -> str:
    """Derive the fixed identity used when no source event identity exists."""

    if isinstance(observation, Mapping):
        observation = ReadOnlyMarketDataObservation.from_mapping(observation)
    if not isinstance(observation, ReadOnlyMarketDataObservation):
        raise ValueError("observation is required")
    projection = {
        "source_id": observation.source.source_id,
        "candidate_id": observation.candidate_id,
        "chain_id": observation.chain_id,
        "token_identity": observation.token_identity,
        "market_subject_id": observation.market_subject_id,
        "observed_at": _timestamp(observation.observed_at),
        "sequence": observation.sequence,
        "observation_kind": observation.observation_kind,
        "metrics": {
            name: _metric_material(metric, include_digest=True)
            for name, metric in observation.metrics.items()
        },
    }
    return hashlib.sha256(
        b"p08-read-only-market-data:observation-id:v1\0"
        + canonical_bytes(projection)
    ).hexdigest()


def _sequence_key(observation: ReadOnlyMarketDataObservation) -> str:
    return "|".join(
        (
            observation.source.source_id,
            observation.chain_id or "",
            observation.token_identity,
            observation.market_subject_id or "",
        )
    )


def _request_fingerprint(
    observation: ReadOnlyMarketDataObservation,
    context: EvaluationContext,
    processing_context: ProcessingContext,
) -> str:
    return hashlib.sha256(
        canonical_bytes(
            {
                "observation_digest": observation.observation_digest,
                "evaluation_context": _context_material(context),
                "predecessor_context_identity": context.predecessor_context_digest,
                "prior_context_identity": processing_context.context_digest,
            }
        )
    ).hexdigest()


def _result(
    *,
    reason: ReasonCode,
    observation: ReadOnlyMarketDataObservation | None,
    context: EvaluationContext | None,
    state_changed: bool = False,
    next_context: ProcessingContext | None = None,
) -> ValidationResult:
    return ValidationResult(
        accepted=reason is ReasonCode.VALID,
        reason_code=reason,
        observation=observation,
        observation_digest=(
            observation.observation_digest
            if isinstance(observation, ReadOnlyMarketDataObservation)
            else None
        ),
        processing_context_identity=(
            context.processing_context_identity
            if isinstance(context, EvaluationContext)
            and isinstance(context.processing_context_identity, str)
            else None
        ),
        state_changed=state_changed if reason is ReasonCode.VALID else False,
        provenance=(
            observation.provenance
            if isinstance(observation, ReadOnlyMarketDataObservation)
            and isinstance(observation.provenance, ProvenanceEnvelope)
            else None
        ),
        next_context=next_context,
    )


def _first(reasons: set[ReasonCode]) -> ReasonCode | None:
    for reason in REASON_PRECEDENCE:
        if reason in reasons:
            return reason
    return None


def _check_time_window(window: Any) -> None:
    if not isinstance(window, TimeWindow):
        raise _ContractError(ReasonCode.INVALID_TYPE)
    _timestamp(window.start)
    _timestamp(window.end)
    _enum(window.boundary, FreshnessBoundary)
    if window.start > window.end:
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)


def _check_value_shape(metric_name: str, value: Any) -> None:
    if not isinstance(value, Mapping):
        raise _ContractError(ReasonCode.INVALID_TYPE)
    expected = {
        "price": {"amount", "quote_asset"},
        "liquidity": {"amount", "valuation_unit", "valuation_context"},
        "volume": {"amount"},
        "asset_age": {"amount"},
        "holders": {"count"},
        "transactions": {"count"},
    }[metric_name]
    if set(value) != expected or not all(isinstance(key, str) for key in value):
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    for key in value:
        _canonical_text(key)
    if metric_name in {"holders", "transactions"}:
        _non_negative_integer(value["count"])
    else:
        _decimal_text(value["amount"])
        if metric_name == "price":
            _canonical_text(value["quote_asset"])
        elif metric_name == "liquidity":
            _canonical_text(value["valuation_unit"])
            _canonical_text(value["valuation_context"])


def _check_metric(metric_name: str, metric: Any) -> None:
    if not isinstance(metric, MetricEnvelope):
        raise _ContractError(ReasonCode.INVALID_TYPE)
    status = _enum(metric.status, FieldStatus)
    if metric.value is not None and status is not FieldStatus.PRESENT:
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    if metric.value is None and status is FieldStatus.PRESENT:
        raise _ContractError(ReasonCode.INVALID_TYPE)
    for value in (metric.unit, metric.semantic_version, metric.reference_semantics, metric.source_field):
        _nullable_text(value)
    if metric.measurement_window is not None:
        _check_time_window(metric.measurement_window)
    if metric.value is not None:
        _check_value_shape(metric_name, metric.value)
    if status is FieldStatus.PRESENT:
        if metric.unit is None or metric.semantic_version is None:
            raise _ContractError(ReasonCode.INVALID_TYPE)
        if metric_name in {"volume", "transactions"} and metric.measurement_window is None:
            raise _ContractError(ReasonCode.INVALID_TYPE)
        if metric_name == "asset_age" and metric.reference_semantics is None:
            raise _ContractError(ReasonCode.INVALID_TYPE)
    _digest(metric.field_digest)
    expected = sha256_digest(_metric_material(metric, include_digest=False))
    if metric.field_digest != expected:
        raise _ContractError(ReasonCode.DIGEST_MISMATCH)


def _check_context(context: EvaluationContext) -> None:
    _timestamp(context.cutoff_time)
    _version(context.freshness_policy_version)
    if context.max_age_seconds is not None:
        maximum = _decimal_text(context.max_age_seconds)
        if Decimal(maximum) < Decimal("0"):
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    _enum(context.freshness_boundary, FreshnessBoundary)
    _version(context.consumer_profile_version)
    if not isinstance(context.required_fields, tuple) or not isinstance(
        context.permitted_optional_fields, tuple
    ):
        raise _ContractError(ReasonCode.INVALID_TYPE)
    for sequence in (context.required_fields, context.permitted_optional_fields):
        if len(sequence) > MAX_IMMUTABLE_SEQUENCE_ELEMENTS:
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
        if tuple(sorted(sequence)) != sequence or len(set(sequence)) != len(sequence):
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
        for item in sequence:
            _canonical_text(item)
            if item not in _SUPPORTED_METRICS:
                raise _ContractError(ReasonCode.UNSUPPORTED_FIELD)
    if set(context.required_fields) & set(context.permitted_optional_fields):
        raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    if not isinstance(context.processing_context_identity, str):
        raise _ContractError(ReasonCode.INVALID_TYPE)
    _canonical_text(context.processing_context_identity)
    if context.predecessor_context_digest is not None:
        _digest(context.predecessor_context_digest)


def _check_source(source: SourceEnvelope) -> None:
    if not isinstance(source, SourceEnvelope):
        raise _ContractError(ReasonCode.INVALID_TYPE)
    _canonical_text(source.source_id)
    _nullable_text(source.source_event_id)
    _version(source.source_contract_version)
    _version(source.adapter_contract_version, exact=CONTRACT_VERSION)
    if source.source_observed_at is not None:
        _timestamp(source.source_observed_at)
    _validate_bounded(source.source_metadata)


def _check_provenance(provenance: ProvenanceEnvelope) -> None:
    if not isinstance(provenance, ProvenanceEnvelope):
        raise _ContractError(ReasonCode.INVALID_TYPE)
    _canonical_text(provenance.source_id)
    _nullable_text(provenance.source_event_id)
    _canonical_text(provenance.candidate_id)
    _nullable_text(provenance.chain_id)
    _canonical_text(provenance.token_identity)
    _nullable_text(provenance.market_subject_id)
    _canonical_text(provenance.observation_id)
    _timestamp(provenance.observed_at)
    _timestamp(provenance.availability_at)
    _timestamp(provenance.cutoff_time)
    _version(provenance.freshness_policy_version)
    _version(provenance.consumer_profile_version)
    if provenance.predecessor_digest is not None:
        _digest(provenance.predecessor_digest)
    _validate_bounded(provenance.field_provenance)


def _check_observation_structure(
    observation: ReadOnlyMarketDataObservation,
) -> set[ReasonCode]:
    reasons: set[ReasonCode] = set()
    try:
        _version(observation.contract_version, exact=CONTRACT_VERSION)
        _canonical_text(observation.observation_id)
        _canonical_text(observation.candidate_id)
        _nullable_text(observation.chain_id)
        _canonical_text(observation.token_identity)
        _nullable_text(observation.market_subject_id)
        _enum(observation.observation_kind, ObservationKind)
        _timestamp(observation.observed_at)
        _timestamp(observation.availability_at)
        if observation.sequence is not None and not (
            (isinstance(observation.sequence, int) and not isinstance(observation.sequence, bool))
            or isinstance(observation.sequence, str)
        ):
            raise _ContractError(ReasonCode.INVALID_TYPE)
        if isinstance(observation.sequence, str):
            _canonical_text(observation.sequence)
        if isinstance(observation.sequence, int) and observation.sequence < 0:
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
        _enum(observation.ordering_status, OrderingStatus)
        _check_source(observation.source)
        _check_provenance(observation.provenance)
        if not isinstance(observation.metrics, Mapping):
            raise _ContractError(ReasonCode.INVALID_TYPE)
        if len(observation.metrics) > MAX_BOUNDED_MAPPING_MEMBERS:
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
        if not all(isinstance(key, str) for key in observation.metrics):
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
        for key in observation.metrics:
            _canonical_text(key)
            if key not in _SUPPORTED_METRICS:
                raise _ContractError(ReasonCode.UNSUPPORTED_FIELD)
            _check_metric(key, observation.metrics[key])
        if not _REQUIRED_METRICS.issubset(observation.metrics):
            raise _ContractError(ReasonCode.MISSING_REQUIRED_INPUT)
        _check_context(observation.evaluation_context)
        _digest(observation.raw_payload_digest)
        _digest(observation.observation_digest)
        encoded = canonical_bytes(_observation_material(observation, include_digest=True))
        if len(encoded) > MAX_BOUNDED_MAPPING_BYTES:
            raise _ContractError(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    except _ContractError as exc:
        reasons.add(exc.reason)
    except (AttributeError, TypeError, ValueError):
        reasons.add(ReasonCode.INVALID_TYPE)
    return reasons


def _check_digest_and_identity(
    observation: ReadOnlyMarketDataObservation,
) -> set[ReasonCode]:
    reasons: set[ReasonCode] = set()
    try:
        expected_observation_digest = observation_digest(observation)
        if observation.observation_digest != expected_observation_digest:
            reasons.add(ReasonCode.DIGEST_MISMATCH)
        source_event_id = observation.source.source_event_id
        if source_event_id is None and observation.observation_id != derive_observation_id(observation):
            reasons.add(ReasonCode.INVALID_IDENTITY)
    except (TypeError, ValueError, _ContractError):
        reasons.add(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    return reasons


def _check_provenance_links(
    observation: ReadOnlyMarketDataObservation,
) -> set[ReasonCode]:
    reasons: set[ReasonCode] = set()
    source = observation.source
    provenance = observation.provenance
    context = observation.evaluation_context
    pairs = (
        (provenance.source_id, source.source_id),
        (provenance.source_event_id, source.source_event_id),
        (provenance.candidate_id, observation.candidate_id),
        (provenance.chain_id, observation.chain_id),
        (provenance.token_identity, observation.token_identity),
        (provenance.market_subject_id, observation.market_subject_id),
        (provenance.observation_id, observation.observation_id),
        (provenance.observed_at, observation.observed_at),
        (provenance.availability_at, observation.availability_at),
        (provenance.cutoff_time, context.cutoff_time),
        (provenance.freshness_policy_version, context.freshness_policy_version),
        (provenance.consumer_profile_version, context.consumer_profile_version),
        (provenance.predecessor_digest, context.predecessor_context_digest),
    )
    if not all(left == right for left, right in pairs):
        reasons.add(ReasonCode.PROVENANCE_FAILURE)
    if source.source_observed_at is not None and source.source_observed_at != observation.observed_at:
        reasons.add(ReasonCode.PROVENANCE_FAILURE)
    if set(provenance.field_provenance) != set(observation.metrics):
        reasons.add(ReasonCode.PROVENANCE_FAILURE)
    if observation.chain_id is None:
        profile = context.consumer_profile_version.lower()
        if "neutral" not in profile or context.predecessor_context_digest is not None:
            reasons.add(ReasonCode.INVALID_IDENTITY)
    if observation.chain_id is not None and context.predecessor_context_digest is not None:
        if provenance.chain_id is None:
            reasons.add(ReasonCode.PROVENANCE_FAILURE)
    if observation.market_subject_id is None:
        profile = context.consumer_profile_version.lower()
        if "neutral" not in profile:
            reasons.add(ReasonCode.INVALID_IDENTITY)
    return reasons


def _check_freshness(
    observation: ReadOnlyMarketDataObservation,
) -> set[ReasonCode]:
    reasons: set[ReasonCode] = set()
    context = observation.evaluation_context
    if observation.observed_at > observation.availability_at:
        reasons.add(ReasonCode.INVALID_CANONICAL_REPRESENTATION)
    if observation.availability_at > context.cutoff_time:
        reasons.add(ReasonCode.FUTURE_OBSERVATION)
    if observation.observed_at > context.cutoff_time:
        reasons.add(ReasonCode.FUTURE_OBSERVATION)
    if reasons:
        return reasons
    age_microseconds = int(
        (context.cutoff_time.astimezone(timezone.utc) - observation.observed_at.astimezone(timezone.utc))
        .total_seconds()
        * 1_000_000
    )
    if age_microseconds < 0:
        reasons.add(ReasonCode.FUTURE_OBSERVATION)
        return reasons
    if context.max_age_seconds is not None:
        maximum = Decimal(context.max_age_seconds)
        age = Decimal(age_microseconds) / Decimal(1_000_000)
        boundary = _enum(context.freshness_boundary, FreshnessBoundary)
        stale = age > maximum if boundary is FreshnessBoundary.INCLUSIVE else age >= maximum
        if stale:
            reasons.add(ReasonCode.STALE_OBSERVATION)
    return reasons


def _check_metrics(
    observation: ReadOnlyMarketDataObservation,
) -> set[ReasonCode]:
    reasons: set[ReasonCode] = set()
    context = observation.evaluation_context
    for field_name in context.required_fields:
        if field_name not in observation.metrics:
            reasons.add(ReasonCode.INCOMPLETE_INPUT)
            continue
        status = _enum(observation.metrics[field_name].status, FieldStatus)
        if status is FieldStatus.MISSING:
            reasons.add(ReasonCode.INCOMPLETE_INPUT)
        elif status in {FieldStatus.UNAVAILABLE, FieldStatus.INVALID}:
            reasons.add(ReasonCode.UNAVAILABLE_INPUT)
    for field_name in observation.metrics:
        if field_name in _OPTIONAL_METRICS and field_name not in context.permitted_optional_fields:
            reasons.add(ReasonCode.UNSUPPORTED_FIELD)
        status = _enum(observation.metrics[field_name].status, FieldStatus)
        if status is FieldStatus.UNAVAILABLE:
            reasons.add(ReasonCode.UNAVAILABLE_INPUT)
        elif status is FieldStatus.INVALID:
            reasons.add(ReasonCode.UNAVAILABLE_INPUT)
    return reasons


def _check_processing_context(
    observation: ReadOnlyMarketDataObservation,
    context: EvaluationContext,
    processing_context: ProcessingContext,
) -> set[ReasonCode]:
    reasons: set[ReasonCode] = set()
    if not isinstance(processing_context.processing_context_identity, str):
        return {ReasonCode.INVALID_TYPE}
    try:
        _canonical_text(processing_context.processing_context_identity)
        if processing_context.context_digest != processing_context.compute_digest():
            reasons.add(ReasonCode.DETERMINISM_FAILURE)
        request = _request_fingerprint(observation, context, processing_context)
        if request in processing_context.replay_fingerprints:
            reasons.add(ReasonCode.REPLAY)
            return reasons
        existing = processing_context.accepted_fingerprints.get(observation.observation_id)
        if existing is not None:
            if existing == observation.observation_digest:
                reasons.add(ReasonCode.DUPLICATE)
            else:
                reasons.add(ReasonCode.CONTRADICTORY_INPUT)
        if isinstance(observation.sequence, int) and not isinstance(observation.sequence, bool):
            previous = processing_context.latest_sequences.get(_sequence_key(observation))
            if previous is not None and observation.sequence <= previous:
                reasons.add(ReasonCode.OUT_OF_ORDER)
    except (TypeError, ValueError, _ContractError):
        reasons.add(ReasonCode.DETERMINISM_FAILURE)
    return reasons


def validate_observation(
    observation: ReadOnlyMarketDataObservation | Mapping[str, Any] | object,
    context: EvaluationContext | None,
    processing_context: ProcessingContext | None = None,
) -> ValidationResult:
    """Validate one explicit observation without mutating caller state."""

    if not isinstance(context, EvaluationContext):
        return _result(reason=ReasonCode.INVALID_TYPE, observation=None, context=None)
    if processing_context is None:
        processing_context = ProcessingContext(
            processing_context_identity=context.processing_context_identity
        )
    if not isinstance(processing_context, ProcessingContext):
        return _result(reason=ReasonCode.INVALID_TYPE, observation=None, context=context)
    if isinstance(observation, Mapping):
        try:
            observation = ReadOnlyMarketDataObservation.from_mapping(observation)
        except Exception:
            return _result(reason=ReasonCode.INVALID_TYPE, observation=None, context=context)
    if not isinstance(observation, ReadOnlyMarketDataObservation):
        return _result(reason=ReasonCode.INVALID_TYPE, observation=None, context=context)

    structural = _check_observation_structure(observation)
    structural_reason = _first(structural)
    if structural_reason is not None:
        return _result(reason=structural_reason, observation=observation, context=context)

    reasons = set()
    reasons.update(_check_digest_and_identity(observation))
    reasons.update(_check_provenance_links(observation))
    reasons.update(_check_freshness(observation))
    reasons.update(_check_metrics(observation))
    reasons.update(_check_processing_context(observation, context, processing_context))
    reason = _first(reasons) or ReasonCode.VALID
    if reason is not ReasonCode.VALID:
        return _result(reason=reason, observation=observation, context=context)
    next_context = processing_context.record(observation, context)
    return _result(
        reason=ReasonCode.VALID,
        observation=observation,
        context=context,
        state_changed=True,
        next_context=next_context,
    )


def process_observation(
    observation: ReadOnlyMarketDataObservation | Mapping[str, Any] | object,
    *,
    evaluation_context: EvaluationContext | None = None,
    context: EvaluationContext | None = None,
    processing_context: ProcessingContext | None = None,
) -> ValidationResult:
    """Alias-friendly functional entry point for one-shot validation."""

    selected = evaluation_context if evaluation_context is not None else context
    return validate_observation(observation, selected, processing_context)


ReadOnlyMarketDataProcessingContext = ProcessingContext
MarketDataEvaluationContext = EvaluationContext
MarketDataValidationResult = ValidationResult
MetricStatus = FieldStatus