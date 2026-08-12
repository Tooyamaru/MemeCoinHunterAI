"""Deterministic signal evidence quality contract for P04-T03.

This module validates the data quality of normalized signal evidence only.  It
does not interpret direction, score signals, derive eligibility, or authorize
execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping

from core.signals.signal_evidence import SignalProvenance
from core.signals.signal_normalization import (
    NormalizedSignalEvidence,
    NormalizedSignalEvidenceCollection,
)


P04_T03_CONTRACT_VERSION = "p04-t03-v1"


class SignalQualityStatus(StrEnum):
    """Quality states without market or trading meaning."""

    ACCEPTABLE = "ACCEPTABLE"
    INSUFFICIENT = "INSUFFICIENT"
    INVALID = "INVALID"


@dataclass(frozen=True)
class SignalEvidenceQualityResult:
    """Immutable, fail-closed quality result for normalized signal evidence."""

    chain_id: str | None
    token_identity: str | None
    quality_status: SignalQualityStatus
    acceptable: bool
    reason_codes: tuple[str, ...]
    evidence_references: tuple[str, ...]
    provenance: tuple[SignalProvenance, ...]
    observation_timestamps: tuple[datetime | None, ...]
    normalized_evidence_digest: str
    contract_version: str = P04_T03_CONTRACT_VERSION

    def __post_init__(self) -> None:
        status = _status_value(self.quality_status)
        object.__setattr__(self, "quality_status", status)
        if self.acceptable is not (status is SignalQualityStatus.ACCEPTABLE):
            raise ValueError("acceptable must match quality_status")

        reasons = tuple(self.reason_codes)
        if any(not isinstance(value, str) or not value.strip() for value in reasons):
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
                "quality_status": self.quality_status.value,
                "acceptable": self.acceptable,
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
                "contract_version": self.contract_version,
            }
        )

    @property
    def representation_digest(self) -> str:
        return _digest(self.canonical_representation)


def assess_signal_evidence_quality(
    evidence: NormalizedSignalEvidenceCollection,
) -> SignalEvidenceQualityResult:
    """Assess data quality without evaluating the meaning of a signal."""

    if not isinstance(evidence, NormalizedSignalEvidenceCollection):
        raise ValueError(
            "evidence must be a NormalizedSignalEvidenceCollection"
        )

    reasons: set[str] = set()
    references: list[str] = []
    provenance: list[SignalProvenance] = []
    timestamps: list[datetime | None] = []

    if not _is_text(evidence.chain_id):
        reasons.add("INVALID_CHAIN_ID")
    if not _is_text(evidence.token_identity):
        reasons.add("INVALID_TOKEN_IDENTITY")
    if not _is_text(evidence.contract_version):
        reasons.add("INVALID_NORMALIZATION_CONTRACT_VERSION")

    values = evidence.evidence
    if not values:
        reasons.add("NO_EVIDENCE")

    if not isinstance(values, tuple):
        reasons.add("INVALID_EVIDENCE_COLLECTION")
        values = tuple(values) if _is_sequence(values) else ()

    for item in values:
        if not isinstance(item, NormalizedSignalEvidence):
            reasons.add("INVALID_EVIDENCE")
            continue

        references.append(item.evidence_reference)
        if isinstance(item.provenance, SignalProvenance):
            provenance.append(item.provenance)
        timestamps.append(
            item.observed_at if _is_aware(item.observed_at) else None
        )

        reasons.update(_quality_issues(item, evidence))

    status = (
        SignalQualityStatus.INVALID
        if reasons - {"NO_EVIDENCE"}
        else (
            SignalQualityStatus.INSUFFICIENT
            if not values
            else SignalQualityStatus.ACCEPTABLE
        )
    )
    digest = _safe_normalized_digest(evidence)
    return SignalEvidenceQualityResult(
        chain_id=evidence.chain_id if _is_text(evidence.chain_id) else None,
        token_identity=(
            evidence.token_identity if _is_text(evidence.token_identity) else None
        ),
        quality_status=status,
        acceptable=status is SignalQualityStatus.ACCEPTABLE,
        reason_codes=tuple(reasons),
        evidence_references=tuple(references),
        provenance=tuple(provenance),
        observation_timestamps=tuple(timestamps),
        normalized_evidence_digest=digest,
    )


def _quality_issues(
    item: NormalizedSignalEvidence,
    collection: NormalizedSignalEvidenceCollection,
) -> set[str]:
    issues: set[str] = set()
    for name in (
        "chain_id",
        "token_identity",
        "signal_type",
        "signal_status",
        "source_id",
        "evidence_reference",
        "contract_version",
    ):
        if not _is_text(getattr(item, name, None)):
            issues.add(f"INVALID_{name.upper()}")

    if item.token_key != (collection.chain_id, collection.token_identity):
        issues.add("IDENTITY_MISMATCH")

    if not _is_aware(item.observed_at):
        issues.add("INVALID_TIMESTAMP")
    elif item.observed_at.utcoffset() != timezone.utc.utcoffset(item.observed_at):
        issues.add("UNNORMALIZED_TIMESTAMP")

    if (
        isinstance(item.confidence, bool)
        or not isinstance(item.confidence, (int, float))
        or not math.isfinite(item.confidence)
        or not 0 <= item.confidence <= 1
    ):
        issues.add("INVALID_CONFIDENCE")

    if not isinstance(item.reason_codes, tuple):
        issues.add("UNNORMALIZED_REASON_CODES")
    elif tuple(item.reason_codes) != tuple(sorted(dict.fromkeys(item.reason_codes))):
        issues.add("UNNORMALIZED_REASON_CODES")
    elif any(not _is_text(value) for value in item.reason_codes):
        issues.add("INVALID_REASON_CODES")

    if not isinstance(item.provenance, SignalProvenance):
        issues.add("INVALID_PROVENANCE")
        return issues
    if item.provenance.source_id != item.source_id:
        issues.add("PROVENANCE_SOURCE_MISMATCH")
    if not _is_aware(item.provenance.observed_at):
        issues.add("INVALID_PROVENANCE_TIMESTAMP")
    else:
        if item.provenance.observed_at != item.observed_at:
            issues.add("PROVENANCE_TIMESTAMP_MISMATCH")
        if item.provenance.observed_at.utcoffset() != timezone.utc.utcoffset(
            item.provenance.observed_at
        ):
            issues.add("UNNORMALIZED_PROVENANCE_TIMESTAMP")
    if not isinstance(item.provenance.metadata, Mapping):
        issues.add("INVALID_PROVENANCE_METADATA")
    return issues


def _safe_normalized_digest(
    evidence: NormalizedSignalEvidenceCollection,
) -> str:
    try:
        return evidence.representation_digest
    except (TypeError, ValueError):
        return "invalid-normalized-evidence"


def _status_value(value: SignalQualityStatus | str) -> SignalQualityStatus:
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


def _is_sequence(value: Any) -> bool:
    return isinstance(value, (list, tuple))


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_text(value: Any, name: str) -> None:
    if not _is_text(value):
        raise ValueError(f"{name} must be a non-empty string")