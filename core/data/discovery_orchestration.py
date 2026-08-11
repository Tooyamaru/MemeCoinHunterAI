"""Deterministic discovery-to-orchestration boundary for P02-T05.

This module converts an accepted P02-T04 discovery result into the existing
P02-T02 adapter-observation contract. It contains no provider, network,
database, persistence, strategy, AI, wallet, or trading behavior.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Mapping

from core.data.contracts import DataQuality, RawEvent
from core.data.discovery import (
    DiscoveryKind,
    DiscoveryOutcome,
    DiscoveryResult,
    DiscoveryOrdering,
    DiscoveryProvenance,
    TokenDiscoveryRecord,
)
from core.data.orchestration import (
    AdapterObservation,
    CursorContinuity,
    IngestionOrchestrator,
    IngestionResult,
    ObservationKind,
)


class DiscoveryOrchestrationOutcome(StrEnum):
    """Observable result of the P02-T05 conversion boundary."""

    FORWARDED = "FORWARDED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class DiscoveryOrchestrationConversion:
    """Validated conversion output before optional orchestration processing."""

    discovery_id: str
    source_id: str
    discovery_outcome: DiscoveryOutcome | None
    discovery_quality_status: DataQuality | None
    observation: AdapterObservation | None
    outcome: DiscoveryOrchestrationOutcome
    forwarded: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class DiscoveryOrchestrationResult:
    """Auditable conversion and downstream orchestration result."""

    conversion: DiscoveryOrchestrationConversion
    ingestion_result: IngestionResult | None
    published_as_current: bool
    reasons: tuple[str, ...] = ()


class DiscoveryToOrchestrationBoundary:
    """Convert accepted discovery output and delegate to existing orchestration."""

    def __init__(self, *, orchestrator: IngestionOrchestrator) -> None:
        if not isinstance(orchestrator, IngestionOrchestrator):
            raise ValueError("orchestrator is required")
        self.orchestrator = orchestrator

    def convert(
        self,
        result: DiscoveryResult,
    ) -> DiscoveryOrchestrationConversion:
        """Validate and convert one P02-T04 result without mutating state."""

        errors = _validate_result(result)
        if errors:
            return DiscoveryOrchestrationConversion(
                discovery_id=_text_or_default(getattr(result, "discovery_id", None), "<invalid-discovery>"),
                source_id=_text_or_default(getattr(result, "source_id", None), "<invalid-source>"),
                discovery_outcome=_enum_or_none(
                    getattr(result, "outcome", None), DiscoveryOutcome
                ),
                discovery_quality_status=_enum_or_none(
                    getattr(result, "quality_status", None), DataQuality
                ),
                observation=None,
                outcome=DiscoveryOrchestrationOutcome.REJECTED,
                forwarded=False,
                reasons=errors,
            )

        assert result.record is not None
        observation = _to_adapter_observation(result, result.record)
        return DiscoveryOrchestrationConversion(
            discovery_id=result.discovery_id,
            source_id=result.source_id,
            discovery_outcome=result.outcome,
            discovery_quality_status=result.quality_status,
            observation=observation,
            outcome=DiscoveryOrchestrationOutcome.FORWARDED,
            forwarded=True,
        )

    def process(
        self,
        result: DiscoveryResult,
        *,
        processing_time: datetime,
        reference_time: datetime,
    ) -> DiscoveryOrchestrationResult:
        """Convert one discovery result and use the existing publisher protocol."""

        conversion = self.convert(result)
        if not conversion.forwarded or conversion.observation is None:
            return DiscoveryOrchestrationResult(
                conversion=conversion,
                ingestion_result=None,
                published_as_current=False,
                reasons=conversion.reasons,
            )

        ingestion_result = self.orchestrator.process(
            conversion.observation,
            processing_time=processing_time,
            reference_time=reference_time,
        )
        return DiscoveryOrchestrationResult(
            conversion=conversion,
            ingestion_result=ingestion_result,
            published_as_current=ingestion_result.published_as_current,
            reasons=ingestion_result.reasons,
        )


def _validate_result(result: Any) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(result, DiscoveryResult):
        return ("result must be a DiscoveryResult",)

    if not _non_empty(result.discovery_id):
        errors.append("discovery_id is required")
    if not _non_empty(result.source_id):
        errors.append("source_id is required")
    if not isinstance(result.outcome, DiscoveryOutcome):
        errors.append("outcome must be a DiscoveryOutcome")
    if not isinstance(result.quality_status, DataQuality):
        errors.append("quality_status must be a DataQuality")
    if not _aware(result.processing_time):
        errors.append("processing_time must be timezone-aware")
    if not _aware(result.reference_time):
        errors.append("reference_time must be timezone-aware")
    if not isinstance(result.accepted, bool):
        errors.append("accepted must be a boolean")
    if not isinstance(result.published_as_current, bool):
        errors.append("published_as_current must be a boolean")
    if not isinstance(result.resynchronization_required, bool):
        errors.append("resynchronization_required must be a boolean")

    if result.outcome is not DiscoveryOutcome.ACCEPTED:
        errors.append("only ACCEPTED discovery outcomes may be forwarded")
    if result.quality_status is not DataQuality.VALID:
        errors.append("only VALID discovery quality may be forwarded")
    if result.accepted is not True:
        errors.append("discovery result must be accepted")
    if result.published_as_current is not True:
        errors.append("discovery result must be current")
    if result.resynchronization_required is not False:
        errors.append("discovery result must not require resynchronization")

    record = result.record
    if not isinstance(record, TokenDiscoveryRecord):
        errors.append("accepted discovery result requires a TokenDiscoveryRecord")
        return tuple(errors)

    errors.extend(_validate_record(result, record))
    return tuple(errors)


def _validate_record(result: DiscoveryResult, record: TokenDiscoveryRecord) -> tuple[str, ...]:
    errors: list[str] = []
    if not _non_empty(record.discovery_id):
        errors.append("record discovery_id is required")
    if not _non_empty(record.token_identity):
        errors.append("record token_identity is required")
    if not _non_empty(record.chain_id):
        errors.append("record chain_id is required")
    if not isinstance(record.discovery_kind, DiscoveryKind):
        errors.append("record discovery_kind must be a DiscoveryKind")
    if not _non_empty(record.discovery_reason):
        errors.append("record discovery_reason is required")
    if not isinstance(record.quality_status, DataQuality):
        errors.append("record quality_status must be a DataQuality")
    if not isinstance(record.ordering, DiscoveryOrdering):
        errors.append("record ordering must be a DiscoveryOrdering")
    if not isinstance(record.contract_version, str) or not record.contract_version.strip():
        errors.append("record contract_version is required")
    if not isinstance(record.metadata, Mapping) or not _canonical(record.metadata):
        errors.append("record metadata must be canonical")

    provenance = record.provenance
    if not isinstance(provenance, DiscoveryProvenance):
        errors.append("record provenance must be a DiscoveryProvenance")
        return tuple(errors)

    if result.discovery_id != record.discovery_id:
        errors.append("result and record discovery_id must match")
    if result.source_id != provenance.source_id:
        errors.append("result source_id must match provenance source_id")
    if result.sequence != provenance.sequence:
        errors.append("result sequence must match provenance sequence")
    if not _non_empty(provenance.source_id):
        errors.append("provenance source_id is required")
    if not _aware(provenance.observation_time):
        errors.append("provenance observation_time must be timezone-aware")
    if not _aware(provenance.discovery_time):
        errors.append("provenance discovery_time must be timezone-aware")
    if not _aware(provenance.received_time):
        errors.append("provenance received_time must be timezone-aware")
    elif _aware(provenance.discovery_time) and (
        provenance.discovery_time > provenance.received_time
    ):
        errors.append("provenance discovery_time must not be later than received_time")
    if (
        _aware(provenance.received_time)
        and _aware(provenance.observation_time)
        and provenance.received_time > provenance.observation_time
    ):
        errors.append("provenance received_time must not be later than observation_time")
    if (
        _aware(provenance.discovery_time)
        and _aware(result.reference_time)
        and provenance.discovery_time > result.reference_time
    ):
        errors.append("provenance discovery_time must not be later than reference_time")
    if provenance.source_event_id is not None and not _non_empty(provenance.source_event_id):
        errors.append("provenance source_event_id must be non-empty when provided")
    if not _valid_sequence(provenance.sequence):
        errors.append("provenance sequence must be an integer or string when provided")
    if isinstance(provenance.sequence, int) and provenance.sequence < 0:
        errors.append("provenance sequence must not be negative")
    if not isinstance(provenance.source_metadata, Mapping) or not _canonical(
        provenance.source_metadata
    ):
        errors.append("provenance source_metadata must be canonical")
    if not isinstance(record.data_age, timedelta):
        errors.append("record data_age must be a timedelta")
    elif _aware(provenance.discovery_time) and _aware(result.reference_time):
        if record.data_age != result.reference_time - provenance.discovery_time:
            errors.append("record data_age must match reference_time and discovery_time")

    if record.discovery_id != result.discovery_id:
        errors.append("record discovery_id must match result discovery_id")
    if record.quality_status is not DataQuality.VALID:
        errors.append("record quality_status must be VALID")
    if record.ordering is DiscoveryOrdering.OUT_OF_ORDER:
        errors.append("record ordering must not be OUT_OF_ORDER")
    if record.discovery_kind is DiscoveryKind.RESYNC and record.ordering is not DiscoveryOrdering.FIRST:
        errors.append("accepted RESYNC must have FIRST ordering")
    return tuple(errors)


def _to_adapter_observation(
    result: DiscoveryResult,
    record: TokenDiscoveryRecord,
) -> AdapterObservation:
    provenance = record.provenance
    discovery_kind = record.discovery_kind
    payload = {
        "chain_id": record.chain_id,
        "data_age_microseconds": record.data_age // timedelta(microseconds=1),
        "discovery_id": record.discovery_id,
        "discovery_kind": discovery_kind.value,
        "discovery_outcome": result.outcome.value,
        "discovery_reason": record.discovery_reason,
        "metadata": deepcopy(dict(record.metadata)),
        "ordering": record.ordering.value,
        "quality_status": record.quality_status.value,
        "token_identity": record.token_identity,
    }
    return AdapterObservation(
        source_id=provenance.source_id,
        kind=(
            ObservationKind.RESYNC
            if discovery_kind is DiscoveryKind.RESYNC
            else ObservationKind.EVENT
        ),
        observed_time=provenance.observation_time,
        raw_event=RawEvent(
            source_id=provenance.source_id,
            payload=payload,
            received_time=provenance.received_time,
            event_time=provenance.discovery_time,
            source_event_id=provenance.source_event_id,
            sequence=provenance.sequence,
            source_metadata=deepcopy(dict(provenance.source_metadata)),
        ),
        cursor=provenance.sequence,
        cursor_continuity=(
            CursorContinuity.CONTINUOUS
            if discovery_kind is DiscoveryKind.RESYNC
            else CursorContinuity.NOT_PROVIDED
        ),
        source_metadata={
            "discovery_id": record.discovery_id,
            "discovery_outcome": result.outcome.value,
            "discovery_quality_status": result.quality_status.value,
            "discovery_ordering": record.ordering.value,
            "discovery_contract_version": record.contract_version,
        },
        correlation_id=record.discovery_id,
    )


def _enum_or_none(value: Any, enum_type: type[StrEnum]) -> StrEnum | None:
    return value if isinstance(value, enum_type) else None


def _text_or_default(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value.strip() else default


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_sequence(value: Any) -> bool:
    return value is None or isinstance(value, (int, str))


def _aware(value: Any) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


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