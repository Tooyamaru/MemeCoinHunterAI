"""Immutable, deterministic signal evidence snapshots for P04-T06.

This module captures the already evaluated and aggregated signal-evidence
trace.  It does not recalculate quality or evaluation, add market meaning, or
perform any I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.signals.signal_aggregation import (
    SignalAggregationStatus,
    SignalEvidenceAggregationResult,
)
from core.signals.signal_evaluation import (
    SignalEvaluationStatus,
)
from core.signals.signal_evidence import SignalProvenance
from core.signals.signal_quality import SignalQualityStatus


P04_T06_CONTRACT_VERSION = "p04-t06-v1"


@dataclass(frozen=True)
class SignalEvidenceSnapshot:
    """A point-in-time immutable representation of an aggregated trace."""

    chain_id: str | None
    token_identity: str | None
    aggregation_status: SignalAggregationStatus
    aggregated: bool
    evaluation_status: SignalEvaluationStatus | None
    quality_status: SignalQualityStatus | None
    signal_statuses: tuple[str, ...]
    reason_codes: tuple[str, ...]
    evidence_references: tuple[str, ...]
    provenance: tuple[SignalProvenance, ...]
    observation_timestamps: tuple[datetime | None, ...]
    normalized_evidence_digest: str
    evaluation_digest: str
    aggregation_digest: str
    aggregation_contract_version: str
    contract_version: str = P04_T06_CONTRACT_VERSION

    @classmethod
    def from_aggregation(
        cls,
        aggregation: SignalEvidenceAggregationResult,
    ) -> SignalEvidenceSnapshot:
        """Capture a P04-T05 result without recalculating any state."""

        if not isinstance(aggregation, SignalEvidenceAggregationResult):
            raise ValueError(
                "aggregation must be a SignalEvidenceAggregationResult value"
            )
        return cls(
            chain_id=aggregation.chain_id,
            token_identity=aggregation.token_identity,
            aggregation_status=aggregation.aggregation_status,
            aggregated=aggregation.aggregated,
            evaluation_status=aggregation.evaluation_status,
            quality_status=aggregation.quality_status,
            signal_statuses=aggregation.signal_statuses,
            reason_codes=aggregation.reason_codes,
            evidence_references=aggregation.evidence_references,
            provenance=aggregation.provenance,
            observation_timestamps=aggregation.observation_timestamps,
            normalized_evidence_digest=aggregation.normalized_evidence_digest,
            evaluation_digest=aggregation.evaluation_digest,
            aggregation_digest=aggregation.representation_digest,
            aggregation_contract_version=aggregation.contract_version,
        )

    from_aggregation_result = from_aggregation

    def __post_init__(self) -> None:
        if self.chain_id is not None:
            _require_text(self.chain_id, "chain_id")
        if self.token_identity is not None:
            _require_text(self.token_identity, "token_identity")

        aggregation_status = _aggregation_status(self.aggregation_status)
        object.__setattr__(self, "aggregation_status", aggregation_status)
        if self.aggregated is not (
            aggregation_status is SignalAggregationStatus.AGGREGATED
        ):
            raise ValueError("aggregated must match aggregation_status")

        if self.evaluation_status is not None:
            object.__setattr__(
                self,
                "evaluation_status",
                _evaluation_status(self.evaluation_status),
            )
        if self.quality_status is not None:
            object.__setattr__(
                self,
                "quality_status",
                _quality_status(self.quality_status),
            )

        signal_statuses = tuple(self.signal_statuses)
        if any(not _is_text(value) for value in signal_statuses):
            raise ValueError("signal_statuses must contain non-empty strings")
        object.__setattr__(self, "signal_statuses", signal_statuses)

        reason_codes = tuple(self.reason_codes)
        if any(not _is_text(value) for value in reason_codes):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(
            self,
            "reason_codes",
            tuple(sorted(dict.fromkeys(reason_codes))),
        )

        evidence_references = tuple(self.evidence_references)
        if any(not _is_text(value) for value in evidence_references):
            raise ValueError(
                "evidence_references must contain non-empty strings"
            )
        object.__setattr__(self, "evidence_references", evidence_references)

        provenance = tuple(self.provenance)
        if not all(isinstance(value, SignalProvenance) for value in provenance):
            raise ValueError("provenance must contain SignalProvenance values")
        object.__setattr__(self, "provenance", provenance)

        timestamps = tuple(self.observation_timestamps)
        object.__setattr__(
            self,
            "observation_timestamps",
            tuple(
                None
                if value is None
                else _to_utc(value, "observation_timestamps")
                for value in timestamps
            ),
        )

        trace_lengths = {
            len(signal_statuses),
            len(evidence_references),
            len(provenance),
            len(timestamps),
        }
        if len(trace_lengths) != 1:
            raise ValueError("snapshot trace fields must have equal lengths")

        _require_text(
            self.normalized_evidence_digest,
            "normalized_evidence_digest",
        )
        _require_text(self.evaluation_digest, "evaluation_digest")
        _require_text(self.aggregation_digest, "aggregation_digest")
        _require_text(
            self.aggregation_contract_version,
            "aggregation_contract_version",
        )
        _require_text(self.contract_version, "contract_version")

    @property
    def source_contract_version(self) -> str:
        """Compatibility name for the consumed P04-T05 contract version."""

        return self.aggregation_contract_version

    @property
    def source_aggregation_digest(self) -> str:
        return self.aggregation_digest

    @property
    def evidence_count(self) -> int:
        return len(self.evidence_references)

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        """Return the immutable representation used for deterministic hashing."""

        return _freeze(
            {
                "chain_id": self.chain_id,
                "token_identity": self.token_identity,
                "aggregation_status": self.aggregation_status.value,
                "aggregated": self.aggregated,
                "evaluation_status": (
                    None
                    if self.evaluation_status is None
                    else self.evaluation_status.value
                ),
                "quality_status": (
                    None
                    if self.quality_status is None
                    else self.quality_status.value
                ),
                "signal_statuses": self.signal_statuses,
                "reason_codes": self.reason_codes,
                "evidence_references": self.evidence_references,
                "provenance": tuple(
                    _provenance_material(value) for value in self.provenance
                ),
                "observation_timestamps": tuple(
                    None if value is None else _utc_iso(value)
                    for value in self.observation_timestamps
                ),
                "normalized_evidence_digest": self.normalized_evidence_digest,
                "evaluation_digest": self.evaluation_digest,
                "aggregation_digest": self.aggregation_digest,
                "aggregation_contract_version": self.aggregation_contract_version,
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


@dataclass(frozen=True)
class SignalEvidenceSnapshotCollection:
    """Immutable, canonically ordered snapshots with duplicates preserved."""

    snapshots: tuple[SignalEvidenceSnapshot, ...]
    contract_version: str = P04_T06_CONTRACT_VERSION

    @classmethod
    def from_snapshots(
        cls,
        snapshots: tuple[SignalEvidenceSnapshot, ...]
        | list[SignalEvidenceSnapshot],
    ) -> SignalEvidenceSnapshotCollection:
        return cls(snapshots=tuple(snapshots))

    @classmethod
    def from_aggregations(
        cls,
        aggregations: tuple[SignalEvidenceAggregationResult, ...]
        | list[SignalEvidenceAggregationResult],
    ) -> SignalEvidenceSnapshotCollection:
        return cls(
            snapshots=tuple(
                SignalEvidenceSnapshot.from_aggregation(item)
                for item in aggregations
            )
        )

    def __post_init__(self) -> None:
        values = tuple(self.snapshots)
        if not all(isinstance(item, SignalEvidenceSnapshot) for item in values):
            raise ValueError(
                "snapshots must contain SignalEvidenceSnapshot values"
            )
        object.__setattr__(
            self,
            "snapshots",
            tuple(
                sorted(
                    values,
                    key=lambda item: _canonical_json(
                        item.canonical_representation
                    ),
                )
            ),
        )
        _require_text(self.contract_version, "contract_version")

    @property
    def snapshot_count(self) -> int:
        return len(self.snapshots)

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "snapshots": tuple(
                    item.canonical_representation for item in self.snapshots
                ),
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


def snapshot_signal_evidence(
    aggregation: SignalEvidenceAggregationResult,
) -> SignalEvidenceSnapshot:
    """Create a deterministic snapshot from an existing P04-T05 result."""

    return SignalEvidenceSnapshot.from_aggregation(aggregation)


create_signal_evidence_snapshot = snapshot_signal_evidence


def snapshot_signal_evidence_collection(
    aggregations: tuple[SignalEvidenceAggregationResult, ...]
    | list[SignalEvidenceAggregationResult],
) -> SignalEvidenceSnapshotCollection:
    return SignalEvidenceSnapshotCollection.from_aggregations(aggregations)


def _aggregation_status(
    value: SignalAggregationStatus | str,
) -> SignalAggregationStatus:
    try:
        return SignalAggregationStatus(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "aggregation_status must be a SignalAggregationStatus"
        ) from error


def _evaluation_status(
    value: SignalEvaluationStatus | str,
) -> SignalEvaluationStatus:
    try:
        return SignalEvaluationStatus(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "evaluation_status must be a SignalEvaluationStatus"
        ) from error


def _quality_status(value: SignalQualityStatus | str) -> SignalQualityStatus:
    try:
        return SignalQualityStatus(value)
    except (TypeError, ValueError) as error:
        raise ValueError("quality_status must be a SignalQualityStatus") from error


def _provenance_material(value: SignalProvenance) -> dict[str, Any]:
    return {
        "source_id": value.source_id,
        "method": value.method,
        "observed_at": _utc_iso(value.observed_at),
        "metadata": value.metadata,
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return _utc_iso(value)
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value, key=str)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ValueError(f"{type(value).__name__} cannot be deterministically serialized")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(child) for key, child in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    if isinstance(value, tuple):
        return tuple(_freeze(child) for child in value)
    return value


def _to_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return _to_utc(value, "timestamp").isoformat()


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_text(value: Any, name: str) -> None:
    if not _is_text(value):
        raise ValueError(f"{name} must be a non-empty string")
