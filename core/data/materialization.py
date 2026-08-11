"""Provider-neutral token-universe materialization for P02-T06.

This module consumes accepted P02-T04/P02-T05 discovery results and produces a
deterministic, read-oriented in-memory view. It deliberately contains no
provider, network, persistence, market, safety, trading, or autonomous
behavior.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
import hashlib
import json
from typing import Any, Mapping

from core.data.contracts import DataQuality
from core.data.discovery import (
    DiscoveryKind,
    DiscoveryOrdering,
    DiscoveryOutcome,
    DiscoveryResult,
    DiscoveryProvenance,
    TokenDiscoveryRecord,
)


TokenUniverseKey = tuple[str, str]


class MaterializationOutcome(StrEnum):
    """Observable outcome for every materialization input."""

    MATERIALIZED = "MATERIALIZED"
    UPDATED = "UPDATED"
    REMOVED = "REMOVED"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"
    INVALID = "INVALID"
    STALE = "STALE"
    CONTRADICTORY = "CONTRADICTORY"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    UNAVAILABLE = "UNAVAILABLE"
    RESYNCHRONIZATION_REQUIRED = "RESYNCHRONIZATION_REQUIRED"


@dataclass(frozen=True)
class TokenUniverseEntry:
    """One current discovery-derived token entry."""

    token_identity: str
    chain_id: str
    discovery_id: str
    discovery_kind: DiscoveryKind
    discovery_reason: str
    quality_status: DataQuality
    ordering: DiscoveryOrdering
    data_age: timedelta
    metadata: Mapping[str, Any]
    provenance: DiscoveryProvenance
    discovery_contract_version: str
    materializer_contract_version: str


@dataclass
class TokenUniverseState:
    """Explicit local state owned by one materializer instance."""

    entries: dict[TokenUniverseKey, TokenUniverseEntry] = field(default_factory=dict)
    accepted_discovery_fingerprints: dict[str, str] = field(default_factory=dict)
    latest_sequence_by_source: dict[str, int] = field(default_factory=dict)
    resynchronization_required: set[str] = field(default_factory=set)
    materializer_contract_version: str = "p02-t06-v1"

    def __post_init__(self) -> None:
        if not isinstance(self.materializer_contract_version, str) or not self.materializer_contract_version.strip():
            raise ValueError("materializer_contract_version is required")
        if not isinstance(self.entries, dict):
            raise ValueError("entries must be a dictionary")
        if not isinstance(self.accepted_discovery_fingerprints, dict):
            raise ValueError("accepted_discovery_fingerprints must be a dictionary")
        if not isinstance(self.latest_sequence_by_source, dict):
            raise ValueError("latest_sequence_by_source must be a dictionary")
        if not isinstance(self.resynchronization_required, set):
            raise ValueError("resynchronization_required must be a set")
        for key, entry in self.entries.items():
            if not _valid_key(key) or not isinstance(entry, TokenUniverseEntry):
                raise ValueError("entries must be keyed by token-universe keys and contain TokenUniverseEntry values")
        for source_id, sequence in self.latest_sequence_by_source.items():
            if not _non_empty(source_id) or not isinstance(sequence, int) or sequence < 0:
                raise ValueError("latest sequence state is invalid")

    @property
    def state_version(self) -> str:
        """Stable digest representing all owned materialization state."""

        return self.state_digest()

    def state_digest(self) -> str:
        return _digest(
            {
                "entries": [
                    {
                        "key": list(key),
                        "entry": _entry_material(entry),
                    }
                    for key, entry in sorted(self.entries.items())
                ],
                "accepted_discovery_fingerprints": dict(
                    sorted(self.accepted_discovery_fingerprints.items())
                ),
                "latest_sequence_by_source": dict(sorted(self.latest_sequence_by_source.items())),
                "resynchronization_required": sorted(self.resynchronization_required),
                "materializer_contract_version": self.materializer_contract_version,
            }
        )


@dataclass
class MaterializationContext:
    """Explicit processing context; no implicit clock or shared state is used."""

    initial_state: TokenUniverseState = field(default_factory=TokenUniverseState)
    materializer_contract_version: str = "p02-t06-v1"
    evaluation_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.initial_state, TokenUniverseState):
            raise ValueError("initial_state is required")
        if not isinstance(self.materializer_contract_version, str) or not self.materializer_contract_version.strip():
            raise ValueError("materializer_contract_version is required")
        if self.evaluation_id is not None and not _non_empty(self.evaluation_id):
            raise ValueError("evaluation_id must be non-empty when provided")
        self.initial_state.materializer_contract_version = self.materializer_contract_version


@dataclass(frozen=True)
class MaterializationResult:
    """Auditable output for one discovery result."""

    materialization_id: str
    discovery_id: str
    source_id: str
    token_identity: str | None
    chain_id: str | None
    discovery_kind: DiscoveryKind | None
    outcome: MaterializationOutcome
    entry: TokenUniverseEntry | None
    current_view: tuple[TokenUniverseEntry, ...]
    current_view_present: bool
    current_view_changed: bool
    reasons: tuple[str, ...]
    processing_time: datetime | None
    reference_time: datetime | None
    materializer_contract_version: str
    discovery_record: TokenDiscoveryRecord | None
    state_version: str


class TokenUniverseMaterializer:
    """Materialize accepted discovery records into an explicit local view."""

    def __init__(self, *, context: MaterializationContext) -> None:
        if not isinstance(context, MaterializationContext):
            raise ValueError("context is required")
        self.context = context
        self.state = context.initial_state
        self._seed_initial_state()

    def process(
        self,
        result: DiscoveryResult,
        *,
        processing_time: datetime,
        reference_time: datetime,
    ) -> MaterializationResult:
        """Evaluate one result using only explicit times and owned state."""

        if not _aware(processing_time) or not _aware(reference_time):
            return self._rejected(
                result,
                processing_time,
                reference_time,
                MaterializationOutcome.INVALID,
                ("processing_time and reference_time must be timezone-aware",),
            )

        validation = _validate_input(result, processing_time, reference_time)
        if validation:
            outcome = _quality_outcome(result)
            return self._rejected(result, processing_time, reference_time, outcome, validation)

        assert result.record is not None
        record = result.record
        key = (record.chain_id, record.token_identity)
        fingerprint = _record_fingerprint(record)

        previous_fingerprint = self.state.accepted_discovery_fingerprints.get(result.discovery_id)
        if previous_fingerprint is not None:
            if previous_fingerprint == fingerprint:
                return self._rejected(
                    result,
                    processing_time,
                    reference_time,
                    MaterializationOutcome.DUPLICATE,
                    ("discovery identity was already materialized",),
                )
            return self._rejected(
                result,
                processing_time,
                reference_time,
                MaterializationOutcome.CONTRADICTORY,
                ("discovery identity maps to different materialization content",),
            )

        if record.discovery_kind is DiscoveryKind.RESYNC:
            return self._rejected(
                result,
                processing_time,
                reference_time,
                MaterializationOutcome.RESYNCHRONIZATION_REQUIRED,
                ("a lone RESYNC record cannot establish a complete universe",),
            )

        ordering_error = self._ordering_error(record)
        if ordering_error is not None:
            return self._rejected(
                result,
                processing_time,
                reference_time,
                MaterializationOutcome.OUT_OF_ORDER,
                (ordering_error,),
            )

        existing = self.state.entries.get(key)
        if record.discovery_kind is DiscoveryKind.DISCOVERED and existing is not None:
            return self._rejected(
                result,
                processing_time,
                reference_time,
                MaterializationOutcome.CONTRADICTORY,
                ("DISCOVERED cannot replace an existing current entry",),
            )
        if record.discovery_kind is DiscoveryKind.METADATA_UPDATED and existing is None:
            return self._rejected(
                result,
                processing_time,
                reference_time,
                MaterializationOutcome.REJECTED,
                ("METADATA_UPDATED requires an existing current entry",),
            )

        entry = _entry_from_record(record, self.context.materializer_contract_version)
        if record.discovery_kind is DiscoveryKind.REMOVED:
            self.state.entries.pop(key, None)
            outcome = MaterializationOutcome.REMOVED
            result_entry = None
        elif record.discovery_kind is DiscoveryKind.METADATA_UPDATED:
            self.state.entries[key] = entry
            outcome = MaterializationOutcome.UPDATED
            result_entry = entry
        elif record.discovery_kind is DiscoveryKind.DISCOVERED:
            self.state.entries[key] = entry
            outcome = MaterializationOutcome.MATERIALIZED
            result_entry = entry
        else:
            return self._rejected(
                result,
                processing_time,
                reference_time,
                MaterializationOutcome.INVALID,
                ("unsupported discovery kind",),
            )

        self._record_acceptance(result.discovery_id, fingerprint, record)
        return self._result(
            result,
            processing_time,
            reference_time,
            outcome,
            result_entry,
            current_view_changed=existing != self.state.entries.get(key),
            reasons=(),
        )

    def process_batch(
        self,
        results: tuple[DiscoveryResult, ...] | list[DiscoveryResult],
        *,
        processing_time: datetime,
        reference_time: datetime,
    ) -> tuple[MaterializationResult, ...]:
        """Replay a supplied batch in its explicit order."""

        if not isinstance(results, (tuple, list)):
            raise ValueError("results must be a tuple or list")
        return tuple(
            self.process(
                result,
                processing_time=processing_time,
                reference_time=reference_time,
            )
            for result in results
        )

    def snapshot(self) -> tuple[TokenUniverseEntry, ...]:
        """Return the current read-only view in canonical key order."""

        return tuple(deepcopy(entry) for _, entry in sorted(self.state.entries.items()))

    def _seed_initial_state(self) -> None:
        for key, entry in self.state.entries.items():
            self.state.accepted_discovery_fingerprints.setdefault(
                entry.discovery_id,
                _entry_record_fingerprint(entry),
            )
            sequence = entry.provenance.sequence
            if isinstance(sequence, int):
                current = self.state.latest_sequence_by_source.get(entry.provenance.source_id)
                if current is None or sequence > current:
                    self.state.latest_sequence_by_source[entry.provenance.source_id] = sequence

    def _ordering_error(self, record: TokenDiscoveryRecord) -> str | None:
        sequence = record.provenance.sequence
        if not isinstance(sequence, int):
            return None
        previous = self.state.latest_sequence_by_source.get(record.provenance.source_id)
        if previous is not None and sequence <= previous:
            return "sequence is not greater than the last accepted materialization sequence"
        return None

    def _record_acceptance(
        self,
        discovery_id: str,
        fingerprint: str,
        record: TokenDiscoveryRecord,
    ) -> None:
        self.state.accepted_discovery_fingerprints[discovery_id] = fingerprint
        sequence = record.provenance.sequence
        if isinstance(sequence, int):
            self.state.latest_sequence_by_source[record.provenance.source_id] = sequence

    def _rejected(
        self,
        result: Any,
        processing_time: datetime | None,
        reference_time: datetime | None,
        outcome: MaterializationOutcome,
        reasons: tuple[str, ...],
    ) -> MaterializationResult:
        record = result.record if isinstance(result, DiscoveryResult) and isinstance(
            result.record, TokenDiscoveryRecord
        ) else None
        return self._result(
            result,
            processing_time,
            reference_time,
            outcome,
            None,
            current_view_changed=False,
            reasons=reasons,
            record=record,
        )

    def _result(
        self,
        result: Any,
        processing_time: datetime | None,
        reference_time: datetime | None,
        outcome: MaterializationOutcome,
        entry: TokenUniverseEntry | None,
        *,
        current_view_changed: bool,
        reasons: tuple[str, ...],
        record: TokenDiscoveryRecord | None = None,
    ) -> MaterializationResult:
        if record is None and isinstance(result, DiscoveryResult):
            record = result.record if isinstance(result.record, TokenDiscoveryRecord) else None
        discovery_id = _text(getattr(result, "discovery_id", None), "<invalid-discovery>")
        source_id = _text(getattr(result, "source_id", None), "<invalid-source>")
        token_identity = record.token_identity if record is not None else None
        chain_id = record.chain_id if record is not None else None
        kind = record.discovery_kind if record is not None else None
        state_version = self.state.state_version
        materialization_id = _digest(
            {
                "evaluation_id": self.context.evaluation_id,
                "discovery_id": discovery_id,
                "source_id": source_id,
                "outcome": outcome.value,
                "processing_time": _timestamp(processing_time),
                "reference_time": _timestamp(reference_time),
                "state_version": state_version,
            }
        )
        return MaterializationResult(
            materialization_id=materialization_id,
            discovery_id=discovery_id,
            source_id=source_id,
            token_identity=token_identity,
            chain_id=chain_id,
            discovery_kind=kind,
            outcome=outcome,
            entry=deepcopy(entry),
            current_view=self.snapshot(),
            current_view_present=(chain_id, token_identity) in self.state.entries
            if chain_id is not None and token_identity is not None
            else False,
            current_view_changed=current_view_changed,
            reasons=reasons,
            processing_time=processing_time if _aware(processing_time) else None,
            reference_time=reference_time if _aware(reference_time) else None,
            materializer_contract_version=self.context.materializer_contract_version,
            discovery_record=deepcopy(record),
            state_version=state_version,
        )


def _validate_input(
    result: Any,
    processing_time: datetime,
    reference_time: datetime,
) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(result, DiscoveryResult):
        return ("result must be a DiscoveryResult",)
    if not _non_empty(result.discovery_id):
        errors.append("discovery_id is required")
    if not _non_empty(result.source_id):
        errors.append("source_id is required")
    if result.outcome is not DiscoveryOutcome.ACCEPTED:
        errors.append("only ACCEPTED discovery outcomes may be materialized")
    if result.quality_status is not DataQuality.VALID:
        errors.append("only VALID discovery quality may be materialized")
    if result.accepted is not True:
        errors.append("discovery result must be accepted")
    if result.published_as_current is not True:
        errors.append("discovery result must be current")
    if result.resynchronization_required is not False:
        errors.append("discovery result must not require resynchronization")
    if not _aware(result.processing_time):
        errors.append("result processing_time must be timezone-aware")
    if not _aware(result.reference_time):
        errors.append("result reference_time must be timezone-aware")
    if not isinstance(result.record, TokenDiscoveryRecord):
        errors.append("accepted discovery result requires a TokenDiscoveryRecord")
        return tuple(errors)
    errors.extend(_validate_record(result.record, result))
    return tuple(errors)


def _validate_record(record: TokenDiscoveryRecord, result: DiscoveryResult) -> tuple[str, ...]:
    errors: list[str] = []
    if not _non_empty(record.discovery_id):
        errors.append("record discovery_id is required")
    if record.discovery_id != result.discovery_id:
        errors.append("record discovery_id must match result discovery_id")
    if not _non_empty(record.token_identity):
        errors.append("record token_identity is required")
    if not _non_empty(record.chain_id):
        errors.append("record chain_id is required")
    if not isinstance(record.discovery_kind, DiscoveryKind):
        errors.append("record discovery_kind must be a DiscoveryKind")
    if not _non_empty(record.discovery_reason):
        errors.append("record discovery_reason is required")
    if record.quality_status is not DataQuality.VALID:
        errors.append("record quality_status must be VALID")
    if not isinstance(record.ordering, DiscoveryOrdering):
        errors.append("record ordering must be a DiscoveryOrdering")
    elif record.ordering is DiscoveryOrdering.OUT_OF_ORDER:
        errors.append("record ordering must not be OUT_OF_ORDER")
    if not isinstance(record.data_age, timedelta) or record.data_age < timedelta(0):
        errors.append("record data_age must be a non-negative timedelta")
    if not isinstance(record.metadata, Mapping) or not _canonical(record.metadata):
        errors.append("record metadata must be canonical")
    if not isinstance(record.contract_version, str) or not record.contract_version.strip():
        errors.append("record contract_version is required")
    provenance = record.provenance
    if not isinstance(provenance, DiscoveryProvenance):
        errors.append("record provenance must be a DiscoveryProvenance")
        return tuple(errors)
    if result.source_id != provenance.source_id:
        errors.append("result source_id must match provenance source_id")
    for name, value in (
        ("observation_time", provenance.observation_time),
        ("discovery_time", provenance.discovery_time),
        ("received_time", provenance.received_time),
    ):
        if not _aware(value):
            errors.append(f"provenance {name} must be timezone-aware")
    if _aware(provenance.discovery_time) and _aware(provenance.received_time):
        if provenance.discovery_time > provenance.received_time:
            errors.append("provenance discovery_time must not be later than received_time")
    if _aware(provenance.received_time) and _aware(provenance.observation_time):
        if provenance.received_time > provenance.observation_time:
            errors.append("provenance received_time must not be later than observation_time")
    if _aware(provenance.discovery_time) and provenance.discovery_time > result.reference_time:
        errors.append("provenance discovery_time must not be later than reference_time")
    if not _valid_sequence(provenance.sequence):
        errors.append("provenance sequence must be an integer or string when provided")
    if isinstance(provenance.sequence, int) and provenance.sequence < 0:
        errors.append("provenance sequence must not be negative")
    if not isinstance(provenance.source_metadata, Mapping) or not _canonical(provenance.source_metadata):
        errors.append("provenance source_metadata must be canonical")
    if _aware(provenance.discovery_time) and record.data_age != result.reference_time - provenance.discovery_time:
        errors.append("record data_age must match reference_time and discovery_time")
    return tuple(errors)


def _entry_from_record(record: TokenDiscoveryRecord, contract_version: str) -> TokenUniverseEntry:
    return TokenUniverseEntry(
        token_identity=record.token_identity,
        chain_id=record.chain_id,
        discovery_id=record.discovery_id,
        discovery_kind=record.discovery_kind,
        discovery_reason=record.discovery_reason,
        quality_status=record.quality_status,
        ordering=record.ordering,
        data_age=record.data_age,
        metadata=deepcopy(dict(record.metadata)),
        provenance=deepcopy(record.provenance),
        discovery_contract_version=record.contract_version,
        materializer_contract_version=contract_version,
    )


def _quality_outcome(result: Any) -> MaterializationOutcome:
    if isinstance(result, DiscoveryResult):
        if result.outcome is DiscoveryOutcome.STALE or result.quality_status is DataQuality.STALE:
            return MaterializationOutcome.STALE
        if result.outcome is DiscoveryOutcome.DUPLICATE or result.quality_status is DataQuality.DUPLICATE:
            return MaterializationOutcome.DUPLICATE
        if result.outcome is DiscoveryOutcome.CONTRADICTORY or result.quality_status is DataQuality.CONTRADICTORY:
            return MaterializationOutcome.CONTRADICTORY
        if result.outcome is DiscoveryOutcome.OUT_OF_ORDER or result.quality_status is DataQuality.OUT_OF_ORDER:
            return MaterializationOutcome.OUT_OF_ORDER
        if result.outcome is DiscoveryOutcome.UNAVAILABLE or result.quality_status is DataQuality.SOURCE_UNAVAILABLE:
            return MaterializationOutcome.UNAVAILABLE
        if result.outcome is DiscoveryOutcome.RESYNC_REQUIRED or result.resynchronization_required:
            return MaterializationOutcome.RESYNCHRONIZATION_REQUIRED
    return MaterializationOutcome.INVALID


def _record_fingerprint(record: TokenDiscoveryRecord) -> str:
    return _digest(
        {
            "discovery_id": record.discovery_id,
            "token_identity": record.token_identity,
            "chain_id": record.chain_id,
            "discovery_kind": record.discovery_kind.value,
            "discovery_reason": record.discovery_reason,
            "quality_status": record.quality_status.value,
            "ordering": record.ordering.value,
            "data_age": _duration(record.data_age),
            "metadata": record.metadata,
            "provenance": _provenance_material(record.provenance),
            "contract_version": record.contract_version,
        }
    )


def _entry_fingerprint(entry: TokenUniverseEntry) -> str:
    return _digest(_entry_material(entry))


def _entry_record_fingerprint(entry: TokenUniverseEntry) -> str:
    return _digest(
        {
            "discovery_id": entry.discovery_id,
            "token_identity": entry.token_identity,
            "chain_id": entry.chain_id,
            "discovery_kind": entry.discovery_kind.value,
            "discovery_reason": entry.discovery_reason,
            "quality_status": entry.quality_status.value,
            "ordering": entry.ordering.value,
            "data_age": _duration(entry.data_age),
            "metadata": entry.metadata,
            "provenance": _provenance_material(entry.provenance),
            "contract_version": entry.discovery_contract_version,
        }
    )


def _entry_material(entry: TokenUniverseEntry) -> dict[str, Any]:
    return {
        "token_identity": entry.token_identity,
        "chain_id": entry.chain_id,
        "discovery_id": entry.discovery_id,
        "discovery_kind": entry.discovery_kind.value,
        "discovery_reason": entry.discovery_reason,
        "quality_status": entry.quality_status.value,
        "ordering": entry.ordering.value,
        "data_age": _duration(entry.data_age),
        "metadata": entry.metadata,
        "provenance": _provenance_material(entry.provenance),
        "discovery_contract_version": entry.discovery_contract_version,
        "materializer_contract_version": entry.materializer_contract_version,
    }


def _provenance_material(provenance: DiscoveryProvenance) -> dict[str, Any]:
    return {
        "source_id": provenance.source_id,
        "source_event_id": provenance.source_event_id,
        "observation_time": _timestamp(provenance.observation_time),
        "discovery_time": _timestamp(provenance.discovery_time),
        "received_time": _timestamp(provenance.received_time),
        "sequence": provenance.sequence,
        "source_metadata": provenance.source_metadata,
    }


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
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
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        if not _aware(value):
            raise ValueError("datetime must be timezone-aware")
        return _timestamp(value)
    if isinstance(value, timedelta):
        return _duration(value)
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("mapping keys must be strings")
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ValueError(f"unsupported value type: {type(value).__name__}")


def _duration(value: timedelta) -> int:
    return value // timedelta(microseconds=1)


def _timestamp(value: datetime | None) -> str | None:
    return value.isoformat() if _aware(value) else None


def _aware(value: Any) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _text(value: Any, default: str) -> str:
    return value if _non_empty(value) else default


def _valid_sequence(value: Any) -> bool:
    return value is None or isinstance(value, (int, str))


def _valid_key(value: Any) -> bool:
    return (
        isinstance(value, tuple)
        and len(value) == 2
        and _non_empty(value[0])
        and _non_empty(value[1])
    )