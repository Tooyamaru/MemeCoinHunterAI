"""Deterministic signal evidence aggregation contract for P04-T05.

This module combines an already evaluated signal-evidence trace into one
immutable evidence representation.  It does not score, rank, authorize, or
turn signals into trading instructions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.signals.signal_evaluation import (
    SignalEvaluationStatus,
    SignalEvidenceEvaluationResult,
)
from core.signals.signal_evidence import SignalProvenance
from core.signals.signal_quality import SignalQualityStatus


P04_T05_CONTRACT_VERSION = "p04-t05-v1"


class SignalAggregationStatus(StrEnum):
    """Aggregation states with no market or trading meaning."""

    AGGREGATED = "AGGREGATED"
    EMPTY_INPUT = "EMPTY_INPUT"
    EVALUATION_BLOCKED = "EVALUATION_BLOCKED"
    INVALID_INPUT = "INVALID_INPUT"

    EMPTY = "EMPTY_INPUT"
    BLOCKED = "EVALUATION_BLOCKED"


SignalEvidenceAggregationStatus = SignalAggregationStatus


@dataclass(frozen=True)
class SignalEvidenceAggregationResult:
    """Immutable, deterministic aggregate of an evaluated evidence trace."""

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
    contract_version: str = P04_T05_CONTRACT_VERSION

    def __post_init__(self) -> None:
        status = _aggregation_status(self.aggregation_status)
        object.__setattr__(self, "aggregation_status", status)
        if self.aggregated is not (status is SignalAggregationStatus.AGGREGATED):
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

        statuses = tuple(self.signal_statuses)
        if any(not _is_text(value) for value in statuses):
            raise ValueError("signal_statuses must contain non-empty strings")
        object.__setattr__(self, "signal_statuses", statuses)

        reasons = tuple(self.reason_codes)
        if any(not _is_text(value) for value in reasons):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(self, "reason_codes", tuple(sorted(dict.fromkeys(reasons))))

        references = tuple(self.evidence_references)
        if any(not _is_text(value) for value in references):
            raise ValueError("evidence_references must contain non-empty strings")
        object.__setattr__(self, "evidence_references", references)

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
            len(statuses),
            len(references),
            len(provenance),
            len(timestamps),
        }
        if len(trace_lengths) != 1:
            raise ValueError("aggregate trace fields must have equal lengths")

        _require_text(self.normalized_evidence_digest, "normalized_evidence_digest")
        _require_text(self.evaluation_digest, "evaluation_digest")
        _require_text(self.contract_version, "contract_version")

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
                "contract_version": self.contract_version,
            }
        )

    @property
    def representation_digest(self) -> str:
        return _digest(self.canonical_representation)


def aggregate_signal_evidence(
    evaluation: SignalEvidenceEvaluationResult,
) -> SignalEvidenceAggregationResult:
    """Aggregate an evaluated signal trace without performing new evaluation."""

    if not isinstance(evaluation, SignalEvidenceEvaluationResult):
        return _invalid_result(("INVALID_EVALUATION_RESULT",))

    issues: set[str] = set()
    evaluation_status = _safe_evaluation_status(evaluation.evaluation_status, issues)
    quality_status = _safe_quality_status(evaluation.quality_status, issues)
    trace = _canonical_trace(evaluation, issues)

    if not isinstance(evaluation.evaluated, bool):
        issues.add("INVALID_EVALUATED_FLAG")
    elif evaluation_status is not None and (
        evaluation.evaluated is (evaluation_status is SignalEvaluationStatus.EVALUATED)
    ) is False:
        issues.add("EVALUATED_STATUS_MISMATCH")

    if evaluation_status is SignalEvaluationStatus.EVALUATED:
        if quality_status is not SignalQualityStatus.ACCEPTABLE:
            issues.add("EVALUATED_WITHOUT_ACCEPTABLE_QUALITY")
        if not trace:
            issues.add("EVALUATED_WITHOUT_EVIDENCE")

    if issues:
        return _invalid_result(
            tuple(sorted(issues)),
            evaluation=evaluation,
            trace=trace,
            evaluation_status=evaluation_status,
            quality_status=quality_status,
        )

    if evaluation_status is SignalEvaluationStatus.INVALID_INPUT:
        return _result(
            evaluation=evaluation,
            aggregation_status=SignalAggregationStatus.INVALID_INPUT,
            aggregated=False,
            evaluation_status=evaluation_status,
            quality_status=quality_status,
            reason_codes=_reasons(evaluation.reason_codes),
            trace=trace,
        )

    if not trace:
        return _result(
            evaluation=evaluation,
            aggregation_status=SignalAggregationStatus.EMPTY_INPUT,
            aggregated=False,
            evaluation_status=evaluation_status,
            quality_status=quality_status,
            reason_codes=_reasons(evaluation.reason_codes or ("NO_EVIDENCE",)),
            trace=trace,
        )

    if evaluation_status is SignalEvaluationStatus.QUALITY_BLOCKED:
        return _result(
            evaluation=evaluation,
            aggregation_status=SignalAggregationStatus.EVALUATION_BLOCKED,
            aggregated=False,
            evaluation_status=evaluation_status,
            quality_status=quality_status,
            reason_codes=_reasons(
                evaluation.reason_codes or ("QUALITY_NOT_ACCEPTABLE",)
            ),
            trace=trace,
        )

    return _result(
        evaluation=evaluation,
        aggregation_status=SignalAggregationStatus.AGGREGATED,
        aggregated=True,
        evaluation_status=evaluation_status,
        quality_status=quality_status,
        reason_codes=_reasons(evaluation.reason_codes),
        trace=trace,
    )


def _result(
    *,
    evaluation: SignalEvidenceEvaluationResult,
    aggregation_status: SignalAggregationStatus,
    aggregated: bool,
    evaluation_status: SignalEvaluationStatus | None,
    quality_status: SignalQualityStatus | None,
    reason_codes: tuple[str, ...],
    trace: tuple[
        tuple[str, SignalProvenance, datetime | None, str],
        ...,
    ],
) -> SignalEvidenceAggregationResult:
    references, provenance, timestamps, statuses = _split_trace(trace)
    return SignalEvidenceAggregationResult(
        chain_id=evaluation.chain_id,
        token_identity=evaluation.token_identity,
        aggregation_status=aggregation_status,
        aggregated=aggregated,
        evaluation_status=evaluation_status,
        quality_status=quality_status,
        signal_statuses=statuses,
        reason_codes=reason_codes,
        evidence_references=references,
        provenance=provenance,
        observation_timestamps=timestamps,
        normalized_evidence_digest=_safe_digest(
            evaluation.normalized_evidence_digest,
            "invalid-normalized-evidence",
        ),
        evaluation_digest=_safe_digest(
            evaluation.representation_digest,
            "invalid-evaluation",
        ),
    )


def _invalid_result(
    reason_codes: tuple[str, ...],
    *,
    evaluation: SignalEvidenceEvaluationResult | None = None,
    trace: tuple[
        tuple[str, SignalProvenance, datetime | None, str],
        ...,
    ] = (),
    evaluation_status: SignalEvaluationStatus | None = None,
    quality_status: SignalQualityStatus | None = None,
) -> SignalEvidenceAggregationResult:
    if evaluation is None:
        return SignalEvidenceAggregationResult(
            chain_id=None,
            token_identity=None,
            aggregation_status=SignalAggregationStatus.INVALID_INPUT,
            aggregated=False,
            evaluation_status=None,
            quality_status=None,
            signal_statuses=(),
            reason_codes=_reasons(reason_codes),
            evidence_references=(),
            provenance=(),
            observation_timestamps=(),
            normalized_evidence_digest="invalid-normalized-evidence",
            evaluation_digest="invalid-evaluation",
        )
    return _result(
        evaluation=evaluation,
        aggregation_status=SignalAggregationStatus.INVALID_INPUT,
        aggregated=False,
        evaluation_status=evaluation_status,
        quality_status=quality_status,
        reason_codes=_reasons(reason_codes),
        trace=trace,
    )


def _canonical_trace(
    evaluation: SignalEvidenceEvaluationResult,
    issues: set[str],
) -> tuple[tuple[str, SignalProvenance, datetime | None, str], ...]:
    references = tuple(evaluation.evidence_references)
    provenance = tuple(evaluation.provenance)
    timestamps = tuple(evaluation.observation_timestamps)
    statuses = tuple(evaluation.signal_statuses)

    if len({len(references), len(provenance), len(timestamps), len(statuses)}) != 1:
        issues.add("MISALIGNED_EVALUATION_TRACE")
        return ()

    records: list[tuple[str, SignalProvenance, datetime | None, str]] = []
    for reference, source, timestamp, status in zip(
        references,
        provenance,
        timestamps,
        statuses,
    ):
        if not _is_text(reference):
            issues.add("INVALID_EVIDENCE_REFERENCE")
        if not isinstance(source, SignalProvenance):
            issues.add("INVALID_PROVENANCE")
        if timestamp is not None and not _is_aware(timestamp):
            issues.add("INVALID_OBSERVATION_TIMESTAMP")
        if not _is_text(status):
            issues.add("INVALID_SIGNAL_STATUS")
        if (
            not _is_text(reference)
            or not isinstance(source, SignalProvenance)
            or (timestamp is not None and not _is_aware(timestamp))
            or not _is_text(status)
        ):
            continue
        records.append(
            (
                reference,
                source,
                (
                    None
                    if timestamp is None
                    else _to_utc(timestamp, "observation_timestamp")
                ),
                status,
            )
        )

    return tuple(sorted(records, key=_trace_sort_key))


def _trace_sort_key(
    value: tuple[str, SignalProvenance, datetime | None, str],
) -> str:
    reference, provenance, timestamp, status = value
    return _canonical_json(
        {
            "evidence_reference": reference,
            "provenance": _provenance_material(provenance),
            "observation_timestamp": (
                None if timestamp is None else _utc_iso(timestamp)
            ),
            "signal_status": status,
        }
    )


def _split_trace(
    trace: tuple[
        tuple[str, SignalProvenance, datetime | None, str],
        ...,
    ],
) -> tuple[
    tuple[str, ...],
    tuple[SignalProvenance, ...],
    tuple[datetime | None, ...],
    tuple[str, ...],
]:
    return (
        tuple(item[0] for item in trace),
        tuple(item[1] for item in trace),
        tuple(item[2] for item in trace),
        tuple(item[3] for item in trace),
    )


def _safe_evaluation_status(
    value: SignalEvaluationStatus | str,
    issues: set[str],
) -> SignalEvaluationStatus | None:
    try:
        return _evaluation_status(value)
    except ValueError:
        issues.add("INVALID_EVALUATION_STATUS")
        return None


def _aggregation_status(value: SignalAggregationStatus | str) -> SignalAggregationStatus:
    try:
        return SignalAggregationStatus(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "aggregation_status must be a SignalAggregationStatus"
        ) from error


def _safe_quality_status(
    value: SignalQualityStatus | str | None,
    issues: set[str],
) -> SignalQualityStatus | None:
    if value is None:
        return None
    try:
        return _quality_status(value)
    except ValueError:
        issues.add("INVALID_QUALITY_STATUS")
        return None


def _evaluation_status(value: SignalEvaluationStatus | str) -> SignalEvaluationStatus:
    try:
        return SignalEvaluationStatus(value)
    except (TypeError, ValueError) as error:
        raise ValueError("evaluation_status must be a SignalEvaluationStatus") from error


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


def _reasons(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(dict.fromkeys(value for value in values if _is_text(value))))


def _safe_digest(value: Any, fallback: str) -> str:
    return value if _is_text(value) else fallback


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


def _to_utc(value: datetime, name: str) -> datetime:
    if not _is_aware(value):
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return _to_utc(value, "timestamp").isoformat()


def _is_aware(value: Any) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_text(value: Any, name: str) -> None:
    if not _is_text(value):
        raise ValueError(f"{name} must be a non-empty string")