"""Immutable, provider-neutral signal evidence contracts for P04-T01.

This module records independent technical or market-derived observations.  It
does not evaluate, score, rank, authorize, or turn signals into trading
actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping


P04_T01_CONTRACT_VERSION = "p04-t01-v1"


@dataclass(frozen=True)
class SignalProvenance:
    """Auditable provenance for one independently observed signal."""

    source_id: str
    method: str
    observed_at: datetime
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        _require_text(self.method, "method")
        _require_aware_datetime(self.observed_at, "observed_at")
        canonical = _canonical_mapping(self.metadata)
        object.__setattr__(self, "metadata", _freeze(canonical))


@dataclass(frozen=True)
class SignalEvidence:
    """One immutable technical or market signal observation."""

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
    contract_version: str = P04_T01_CONTRACT_VERSION

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
        _require_aware_datetime(self.observed_at, "observed_at")
        _require_confidence(self.confidence)
        object.__setattr__(self, "confidence", float(self.confidence))

        if not isinstance(self.provenance, SignalProvenance):
            raise ValueError("provenance is required")
        if self.provenance.source_id != self.source_id:
            raise ValueError("provenance source_id must match source_id")
        if self.provenance.observed_at != self.observed_at:
            raise ValueError("provenance observed_at must match observed_at")

        reasons = tuple(self.reason_codes)
        if any(not isinstance(value, str) or not value.strip() for value in reasons):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(self, "reason_codes", tuple(sorted(dict.fromkeys(reasons))))

    @property
    def token_key(self) -> tuple[str, str]:
        return self.chain_id, self.token_identity

    @property
    def representation_digest(self) -> str:
        return _digest(self)


@dataclass(frozen=True)
class SignalEvidenceCollection:
    """Immutable, canonically ordered signal evidence for one token."""

    chain_id: str
    token_identity: str
    evidence: tuple[SignalEvidence, ...]
    contract_version: str = P04_T01_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.chain_id, "chain_id")
        _require_text(self.token_identity, "token_identity")
        _require_text(self.contract_version, "contract_version")

        values = tuple(self.evidence)
        if not all(isinstance(item, SignalEvidence) for item in values):
            raise ValueError("evidence must contain SignalEvidence values")
        if any(item.token_key != (self.chain_id, self.token_identity) for item in values):
            raise ValueError("all evidence must belong to the collection token")
        object.__setattr__(
            self,
            "evidence",
            tuple(sorted(values, key=_evidence_sort_key)),
        )

    @classmethod
    def from_evidence(
        cls,
        evidence: tuple[SignalEvidence, ...] | list[SignalEvidence],
        *,
        chain_id: str | None = None,
        token_identity: str | None = None,
    ) -> SignalEvidenceCollection:
        values = tuple(evidence)
        if values:
            first = values[0]
            if chain_id is not None and chain_id != first.chain_id:
                raise ValueError("chain_id must match evidence")
            if token_identity is not None and token_identity != first.token_identity:
                raise ValueError("token_identity must match evidence")
            return cls(
                chain_id=first.chain_id,
                token_identity=first.token_identity,
                evidence=values,
            )
        if chain_id is None or token_identity is None:
            raise ValueError(
                "empty evidence collections require chain_id and token_identity"
            )
        return cls(
            chain_id=chain_id,
            token_identity=token_identity,
            evidence=(),
        )

    @property
    def representation_digest(self) -> str:
        return _digest(self)


def _evidence_sort_key(value: SignalEvidence) -> tuple[str, ...]:
    return (
        value.signal_type,
        value.signal_status,
        value.observed_at.astimezone(timezone.utc).isoformat(),
        value.source_id,
        value.evidence_reference,
        json.dumps(value.reason_codes, separators=(",", ":")),
        format(value.confidence, ".17g"),
        value.provenance.method,
        json.dumps(
            _canonical_general(value.provenance.metadata),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ),
        value.contract_version,
    )


def _require_confidence(value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be a number between 0 and 1")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("confidence must be a number between 0 and 1")


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_aware_datetime(value: Any, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _canonical_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("metadata must be a mapping")
    result = _canonical_general(value)
    if not isinstance(result, dict):
        raise ValueError("metadata must be a mapping")
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > 8192:
        raise ValueError("metadata exceeds the bounded limit")
    return result


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def _digest(value: Any) -> str:
    material = _canonical_general(value)
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _canonical_general(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_general(value[key])
            for key in sorted(value, key=str)
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_general(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_canonical_general(item) for item in value]
        return sorted(
            items,
            key=lambda item: json.dumps(
                item,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    if is_dataclass(value):
        return {
            item.name: _canonical_general(getattr(value, item.name))
            for item in fields(value)
        }
    raise ValueError(f"{type(value).__name__} cannot be deterministically serialized")