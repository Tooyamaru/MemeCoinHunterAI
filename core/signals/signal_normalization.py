"""Deterministic normalization contracts for P04-T02.

This module normalizes provider-neutral signal evidence for later evaluation.
It does not evaluate, score, rank, aggregate, authorize, or trade signals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping

from core.signals.signal_evidence import (
    SignalEvidence,
    SignalEvidenceCollection,
    SignalProvenance,
)


P04_T02_CONTRACT_VERSION = "p04-t02-v1"


@dataclass(frozen=True)
class NormalizedSignalEvidence:
    """One immutable, UTC-normalized copy of signal evidence."""

    chain_id: str
    token_identity: str
    signal_type: str
    signal_status: str
    observed_at: datetime
    source_id: str
    evidence_reference: str
    reason_codes: tuple[str, ...]
    confidence: float
    provenance: SignalProvenance
    contract_version: str

    @classmethod
    def from_evidence(cls, evidence: SignalEvidence) -> NormalizedSignalEvidence:
        if not isinstance(evidence, SignalEvidence):
            raise ValueError("evidence must be a SignalEvidence value")
        observed_at = _to_utc(evidence.observed_at, "observed_at")
        provenance = SignalProvenance(
            source_id=evidence.provenance.source_id,
            method=evidence.provenance.method,
            observed_at=_to_utc(evidence.provenance.observed_at, "provenance.observed_at"),
            metadata=evidence.provenance.metadata,
        )
        return cls(
            chain_id=evidence.chain_id,
            token_identity=evidence.token_identity,
            signal_type=evidence.signal_type,
            signal_status=evidence.signal_status,
            observed_at=observed_at,
            source_id=evidence.source_id,
            evidence_reference=evidence.evidence_reference,
            reason_codes=evidence.reason_codes,
            confidence=evidence.confidence,
            provenance=provenance,
            contract_version=evidence.contract_version,
        )

    def __post_init__(self) -> None:
        for name in (
            "chain_id",
            "token_identity",
            "signal_type",
            "signal_status",
            "source_id",
            "evidence_reference",
            "contract_version",
        ):
            _require_text(getattr(self, name), name)

        observed_at = _to_utc(self.observed_at, "observed_at")
        object.__setattr__(self, "observed_at", observed_at)
        _require_confidence(self.confidence)
        object.__setattr__(self, "confidence", float(self.confidence))

        if not isinstance(self.provenance, SignalProvenance):
            raise ValueError("provenance is required")
        provenance_at = _to_utc(
            self.provenance.observed_at,
            "provenance.observed_at",
        )
        if self.provenance.source_id != self.source_id:
            raise ValueError("provenance source_id must match source_id")
        if provenance_at != observed_at:
            raise ValueError("provenance observed_at must match observed_at")
        if provenance_at != self.provenance.observed_at:
            object.__setattr__(
                self,
                "provenance",
                SignalProvenance(
                    source_id=self.provenance.source_id,
                    method=self.provenance.method,
                    observed_at=provenance_at,
                    metadata=self.provenance.metadata,
                ),
            )

        reasons = tuple(self.reason_codes)
        if any(not isinstance(value, str) or not value.strip() for value in reasons):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(self, "reason_codes", tuple(sorted(dict.fromkeys(reasons))))

    @property
    def token_key(self) -> tuple[str, str]:
        return self.chain_id, self.token_identity

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        """Return the immutable representation used for deterministic hashing."""

        return _freeze(_normalized_material(self))

    @property
    def representation_digest(self) -> str:
        return _digest(self.canonical_representation)


@dataclass(frozen=True)
class NormalizedSignalEvidenceCollection:
    """Immutable, canonically ordered normalized signal evidence."""

    chain_id: str
    token_identity: str
    evidence: tuple[NormalizedSignalEvidence, ...]
    contract_version: str = P04_T02_CONTRACT_VERSION

    @classmethod
    def from_collection(
        cls,
        collection: SignalEvidenceCollection,
    ) -> NormalizedSignalEvidenceCollection:
        if not isinstance(collection, SignalEvidenceCollection):
            raise ValueError("collection must be a SignalEvidenceCollection value")
        return cls(
            chain_id=collection.chain_id,
            token_identity=collection.token_identity,
            evidence=tuple(
                NormalizedSignalEvidence.from_evidence(item)
                for item in collection.evidence
            ),
        )

    def __post_init__(self) -> None:
        _require_text(self.chain_id, "chain_id")
        _require_text(self.token_identity, "token_identity")
        _require_text(self.contract_version, "contract_version")
        values = tuple(self.evidence)
        if not all(isinstance(item, NormalizedSignalEvidence) for item in values):
            raise ValueError(
                "evidence must contain NormalizedSignalEvidence values"
            )
        if any(item.token_key != (self.chain_id, self.token_identity) for item in values):
            raise ValueError("all evidence must belong to the collection token")
        object.__setattr__(
            self,
            "evidence",
            tuple(
                sorted(
                    values,
                    key=lambda item: _canonical_json(
                        item.canonical_representation
                    ),
                )
            ),
        )

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        """Return the immutable representation used for deterministic hashing."""

        return _freeze(
            {
                "chain_id": self.chain_id,
                "token_identity": self.token_identity,
                "evidence": tuple(item.canonical_representation for item in self.evidence),
                "contract_version": self.contract_version,
            }
        )

    @property
    def representation_digest(self) -> str:
        return _digest(self.canonical_representation)


def normalize_signal_evidence(
    collection: SignalEvidenceCollection,
) -> NormalizedSignalEvidenceCollection:
    """Normalize a P04-T01 collection without evaluating its evidence."""

    return NormalizedSignalEvidenceCollection.from_collection(collection)


def _normalized_material(value: NormalizedSignalEvidence) -> dict[str, Any]:
    return {
        "chain_id": value.chain_id,
        "token_identity": value.token_identity,
        "signal_type": value.signal_type,
        "signal_status": value.signal_status,
        "observed_at": _utc_iso(value.observed_at),
        "source_id": value.source_id,
        "evidence_reference": value.evidence_reference,
        "reason_codes": tuple(value.reason_codes),
        "confidence": value.confidence,
        "provenance": {
            "source_id": value.provenance.source_id,
            "method": value.provenance.method,
            "observed_at": _utc_iso(value.provenance.observed_at),
            "metadata": value.provenance.metadata,
        },
        "contract_version": value.contract_version,
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


def _require_confidence(value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be a number between 0 and 1")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("confidence must be a number between 0 and 1")


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
