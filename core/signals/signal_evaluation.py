"""Deterministic signal evidence evaluation contract for P04-T04.

This module evaluates only whether acceptable normalized signal evidence can
pass through the signal-evaluation boundary.  It does not score, rank, predict,
authorize, or turn signal status into a trading instruction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.signals.signal_evidence import SignalProvenance
from core.signals.signal_normalization import (
    NormalizedSignalEvidence,
    NormalizedSignalEvidenceCollection,
)
from core.signals.signal_quality import (
    SignalEvidenceQualityResult,
    SignalQualityStatus,
)


P04_T04_CONTRACT_VERSION = "p04-t04-v1"


class SignalEvaluationStatus(StrEnum):
    """Evaluation states with no trading or authorization meaning."""

    EVALUATED = "EVALUATED"
    QUALITY_BLOCKED = "QUALITY_BLOCKED"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class SignalEvidenceEvaluationResult:
    """Immutable, fail-closed result for normalized signal evidence."""

    chain_id: str | None
    token_identity: str | None
    evaluation_status: SignalEvaluationStatus
    evaluated: bool
    quality_status: SignalQualityStatus | None
    signal_statuses: tuple[str, ...]
    reason_codes: tuple[str, ...]
    normalized_evidence_digest: str
    evidence_references: tuple[str, ...]
    provenance: tuple[SignalProvenance, ...]
    observation_timestamps: tuple[datetime | None, ...]
    contract_version: str = P04_T04_CONTRACT_VERSION

    def __post_init__(self) -> None:
        status = _evaluation_status(self.evaluation_status)
        object.__setattr__(self, "evaluation_status", status)
        if self.evaluated is not (status is SignalEvaluationStatus.EVALUATED):
            raise ValueError("evaluated must match evaluation_status")

        if self.quality_status is not None:
            object.__setattr__(
                self,
                "quality_status",
                _quality_status(self.quality_status),
            )

        signal_statuses = tuple(self.signal_statuses)
        object.__setattr__(self, "signal_statuses", signal_statuses)

        reasons = tuple(self.reason_codes)
        if any(not _is_text(value) for value in reasons):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(self, "reason_codes", tuple(sorted(dict.fromkeys(reasons))))

        object.__setattr__(
            self,
            "evidence_references",
            tuple(self.evidence_references),
        )
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
        if len(self.evidence_references) != len(self.provenance):
            raise ValueError(
                "evidence_references and provenance must have equal lengths"
            )
        if len(self.evidence_references) != len(self.observation_timestamps):
            raise ValueError(
                "evidence_references and observation_timestamps must have equal lengths"
            )

        _require_text(self.normalized_evidence_digest, "normalized_evidence_digest")
        _require_text(self.contract_version, "contract_version")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        """Return the immutable representation used for deterministic hashing."""

        return _freeze(
            {
                "chain_id": self.chain_id,
                "token_identity": self.token_identity,
                "evaluation_status": self.evaluation_status.value,
                "evaluated": self.evaluated,
                "quality_status": (
                    None
                    if self.quality_status is None
                    else self.quality_status.value
                ),
                "signal_statuses": self.signal_statuses,
                "reason_codes": self.reason_codes,
                "normalized_evidence_digest": self.normalized_evidence_digest,
                "evidence_references": self.evidence_references,
                "provenance": tuple(
                    _provenance_material(value) for value in self.provenance
                ),
                "observation_timestamps": tuple(
                    None if value is None else _utc_iso(value)
                    for value in self.observation_timestamps
                ),
                "contract_version": self.contract_version,
            }
        )

    @property
    def representation_digest(self) -> str:
        return _digest(self.canonical_representation)


def evaluate_signal_evidence(
    evidence: NormalizedSignalEvidenceCollection,
    quality: SignalEvidenceQualityResult,
) -> SignalEvidenceEvaluationResult:
    """Evaluate normalized evidence only when its supplied quality is valid."""

    if not isinstance(evidence, NormalizedSignalEvidenceCollection):
        return _invalid_result(reason_codes=("INVALID_NORMALIZED_EVIDENCE",))
    if not isinstance(quality, SignalEvidenceQualityResult):
        return _invalid_result(
            evidence=evidence,
            reason_codes=("INVALID_QUALITY_RESULT",),
        )

    trace = _trace(evidence)
    try:
        quality_status = _quality_status(quality.quality_status)
    except ValueError:
        return _result(
            evidence=evidence,
            quality_status=None,
            evaluation_status=SignalEvaluationStatus.INVALID_INPUT,
            reason_codes=("INVALID_QUALITY_STATUS",),
            trace=trace,
        )

    mismatch_reasons = _quality_alignment_issues(evidence, quality, trace)
    if mismatch_reasons:
        return _result(
            evidence=evidence,
            quality_status=quality_status,
            evaluation_status=SignalEvaluationStatus.INVALID_INPUT,
            reason_codes=tuple(mismatch_reasons),
            trace=trace,
        )

    if quality_status is not SignalQualityStatus.ACCEPTABLE:
        reasons = quality.reason_codes or ("QUALITY_NOT_ACCEPTABLE",)
        return _result(
            evidence=evidence,
            quality_status=quality_status,
            evaluation_status=SignalEvaluationStatus.QUALITY_BLOCKED,
            reason_codes=reasons,
            trace=trace,
        )

    return _result(
        evidence=evidence,
        quality_status=quality_status,
        evaluation_status=SignalEvaluationStatus.EVALUATED,
        reason_codes=(),
        trace=trace,
    )


def _result(
    *,
    evidence: NormalizedSignalEvidenceCollection,
    quality_status: SignalQualityStatus | None,
    evaluation_status: SignalEvaluationStatus,
    reason_codes: tuple[str, ...],
    trace: tuple[
        tuple[str, ...],
        tuple[SignalProvenance, ...],
        tuple[datetime | None, ...],
        tuple[str, ...],
    ],
) -> SignalEvidenceEvaluationResult:
    references, provenance, timestamps, signal_statuses = trace
    return SignalEvidenceEvaluationResult(
        chain_id=evidence.chain_id,
        token_identity=evidence.token_identity,
        evaluation_status=evaluation_status,
        evaluated=evaluation_status is SignalEvaluationStatus.EVALUATED,
        quality_status=quality_status,
        signal_statuses=signal_statuses,
        reason_codes=reason_codes,
        normalized_evidence_digest=_safe_digest(evidence),
        evidence_references=references,
        provenance=provenance,
        observation_timestamps=timestamps,
    )


def _invalid_result(
    *,
    evidence: NormalizedSignalEvidenceCollection | None = None,
    reason_codes: tuple[str, ...],
) -> SignalEvidenceEvaluationResult:
    if evidence is None:
        return SignalEvidenceEvaluationResult(
            chain_id=None,
            token_identity=None,
            evaluation_status=SignalEvaluationStatus.INVALID_INPUT,
            evaluated=False,
            quality_status=None,
            signal_statuses=(),
            reason_codes=reason_codes,
            normalized_evidence_digest="invalid-normalized-evidence",
            evidence_references=(),
            provenance=(),
            observation_timestamps=(),
        )
    return _result(
        evidence=evidence,
        quality_status=None,
        evaluation_status=SignalEvaluationStatus.INVALID_INPUT,
        reason_codes=reason_codes,
        trace=_trace(evidence),
    )


def _quality_alignment_issues(
    evidence: NormalizedSignalEvidenceCollection,
    quality: SignalEvidenceQualityResult,
    trace: tuple[
        tuple[str, ...],
        tuple[SignalProvenance, ...],
        tuple[datetime | None, ...],
        tuple[str, ...],
    ],
) -> set[str]:
    references, provenance, timestamps, _ = trace
    issues: set[str] = set()
    if quality.quality_status is SignalQualityStatus.ACCEPTABLE and not quality.acceptable:
        issues.add("QUALITY_ACCEPTABILITY_MISMATCH")
    if quality.quality_status is not SignalQualityStatus.ACCEPTABLE and quality.acceptable:
        issues.add("QUALITY_ACCEPTABILITY_MISMATCH")
    if quality.chain_id != evidence.chain_id:
        issues.add("QUALITY_CHAIN_ID_MISMATCH")
    if quality.token_identity != evidence.token_identity:
        issues.add("QUALITY_TOKEN_IDENTITY_MISMATCH")
    if quality.normalized_evidence_digest != _safe_digest(evidence):
        issues.add("NORMALIZED_DIGEST_MISMATCH")
    if quality.evidence_references != references:
        issues.add("EVIDENCE_REFERENCES_MISMATCH")
    if quality.provenance != provenance:
        issues.add("PROVENANCE_MISMATCH")
    if quality.observation_timestamps != timestamps:
        issues.add("OBSERVATION_TIMESTAMPS_MISMATCH")
    return issues


def _trace(
    evidence: NormalizedSignalEvidenceCollection,
) -> tuple[
    tuple[str, ...],
    tuple[SignalProvenance, ...],
    tuple[datetime | None, ...],
    tuple[str, ...],
]:
    references: list[str] = []
    provenance: list[SignalProvenance] = []
    timestamps: list[datetime | None] = []
    signal_statuses: list[str] = []
    for item in evidence.evidence:
        if not isinstance(item, NormalizedSignalEvidence):
            continue
        references.append(item.evidence_reference)
        provenance.append(item.provenance)
        timestamps.append(item.observed_at if _is_aware(item.observed_at) else None)
        signal_statuses.append(item.signal_status)
    return (
        tuple(references),
        tuple(provenance),
        tuple(timestamps),
        tuple(signal_statuses),
    )


def _safe_digest(evidence: NormalizedSignalEvidenceCollection) -> str:
    try:
        return evidence.representation_digest
    except (TypeError, ValueError):
        return "invalid-normalized-evidence"


def _evaluation_status(value: SignalEvaluationStatus | str) -> SignalEvaluationStatus:
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