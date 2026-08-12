"""Provider-neutral token safety evidence contract for P03-T01.

This module defines immutable evidence records for a future safety evaluator.
It does not collect chain data, evaluate safety, resolve conflicts, or derive
eligibility.  A PASS record is only a qualifying observation; it is not an
aggregate approval or trading authorization.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timedelta
from enum import StrEnum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping

from core.data.contracts import DataQuality


P03_T01_CONTRACT_VERSION = "p03-t01-v1"


class SafetyStatus(StrEnum):
    """The only safety statuses admitted by this boundary."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class SafetyDomain(StrEnum):
    """Provider-neutral safety domains reserved by the P03 architecture."""

    MINT_FREEZE_AUTHORITY = "MINT_FREEZE_AUTHORITY"
    LP_STATUS_CONCENTRATION = "LP_STATUS_CONCENTRATION"
    LIQUIDITY_QUALITY = "LIQUIDITY_QUALITY"
    METADATA_MUTABILITY = "METADATA_MUTABILITY"
    TOP_HOLDER_CONCENTRATION = "TOP_HOLDER_CONCENTRATION"
    FUNDING_WALLET_RELATIONSHIPS = "FUNDING_WALLET_RELATIONSHIPS"
    PROXY_CONTROL_PATTERNS = "PROXY_CONTROL_PATTERNS"
    SUSPICIOUS_MUTABLE_BEHAVIOR = "SUSPICIOUS_MUTABLE_BEHAVIOR"
    TRADABILITY_SELLABILITY = "TRADABILITY_SELLABILITY"
    STALE_UNAVAILABLE_EVIDENCE = "STALE_UNAVAILABLE_EVIDENCE"


@dataclass(frozen=True)
class P02StateReference:
    """Copied point-in-time reference to a completed P02 representation."""

    state_version: str
    state_digest: str
    contract_version: str
    evaluation_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("state_version", "state_digest", "contract_version"):
            _require_text(getattr(self, name), name)
        if self.evaluation_id is not None:
            _require_text(self.evaluation_id, "evaluation_id")


@dataclass(frozen=True)
class SafetyProvenance:
    """Auditable, provider-neutral provenance for one evidence observation."""

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
class TokenSafetyEvidence:
    """One immutable safety observation, not an aggregate safety decision."""

    chain_id: str
    token_identity: str
    domain: SafetyDomain | str
    status: SafetyStatus | str
    source_id: str
    observed_at: datetime
    quality: DataQuality | str
    freshness_status: DataQuality | str
    data_age: timedelta | None
    provenance: SafetyProvenance
    evidence_reference: str
    evidence_context: Mapping[str, Any] = field(default_factory=dict)
    p02_reference: P02StateReference | None = None
    reason_codes: tuple[str, ...] = ()
    contract_version: str = P03_T01_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.chain_id, "chain_id")
        _require_text(self.token_identity, "token_identity")
        _require_text(self.source_id, "source_id")
        _require_text(self.evidence_reference, "evidence_reference")
        _require_text(self.contract_version, "contract_version")
        _require_aware_datetime(self.observed_at, "observed_at")

        domain = _enum_value(self.domain, SafetyDomain, "domain")
        status = _enum_value(self.status, SafetyStatus, "status")
        quality = _enum_value(self.quality, DataQuality, "quality")
        freshness_status = _enum_value(
            self.freshness_status, DataQuality, "freshness_status"
        )
        object.__setattr__(self, "domain", domain)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "quality", quality)
        object.__setattr__(self, "freshness_status", freshness_status)

        if not isinstance(self.provenance, SafetyProvenance):
            raise ValueError("provenance is required")
        if self.provenance.source_id != self.source_id:
            raise ValueError("provenance source_id must match source_id")
        if self.provenance.observed_at != self.observed_at:
            raise ValueError("provenance observed_at must match observed_at")
        if self.p02_reference is not None and not isinstance(
            self.p02_reference, P02StateReference
        ):
            raise ValueError("p02_reference must be a P02StateReference")

        if self.data_age is not None and (
            not isinstance(self.data_age, timedelta)
            or self.data_age < timedelta(0)
        ):
            raise ValueError("data_age must be a non-negative timedelta when provided")

        context = _canonical_mapping(self.evidence_context)
        object.__setattr__(self, "evidence_context", _freeze(context))
        reasons = _normalise_reason_codes(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)

        if status is SafetyStatus.FAIL and not reasons:
            raise ValueError("FAIL evidence requires at least one reason code")
        if status is SafetyStatus.UNKNOWN and not reasons:
            raise ValueError("UNKNOWN evidence requires at least one reason code")
        if status is SafetyStatus.PASS:
            _validate_qualifying_pass(
                evidence_context=context,
                quality=quality,
                freshness_status=freshness_status,
                data_age=self.data_age,
            )

    @property
    def token_key(self) -> tuple[str, str]:
        return self.chain_id, self.token_identity

    @property
    def is_positive_evidence(self) -> bool:
        """Whether this item is explicit PASS evidence only.

        This is intentionally not an eligibility or authorization decision.
        """

        return self.status is SafetyStatus.PASS

    @property
    def is_non_positive(self) -> bool:
        return not self.is_positive_evidence

    @property
    def representation_digest(self) -> str:
        return _digest(self)


@dataclass(frozen=True)
class SafetyEvidenceCollection:
    """Immutable collection that preserves independent evidence and conflicts."""

    token_identity: str
    chain_id: str
    evidence: tuple[TokenSafetyEvidence, ...]
    contract_version: str = P03_T01_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.chain_id, "chain_id")
        _require_text(self.token_identity, "token_identity")
        _require_text(self.contract_version, "contract_version")
        values = tuple(self.evidence)
        if not all(isinstance(item, TokenSafetyEvidence) for item in values):
            raise ValueError("evidence must contain TokenSafetyEvidence values")
        if any(item.token_key != (self.chain_id, self.token_identity) for item in values):
            raise ValueError("all evidence must belong to the collection token")
        object.__setattr__(self, "evidence", values)

    @classmethod
    def from_evidence(
        cls,
        evidence: tuple[TokenSafetyEvidence, ...] | list[TokenSafetyEvidence],
    ) -> SafetyEvidenceCollection:
        values = tuple(evidence)
        if not values:
            raise ValueError("at least one evidence item is required")
        first = values[0]
        return cls(
            chain_id=first.chain_id,
            token_identity=first.token_identity,
            evidence=values,
        )

    @property
    def conflicting_domains(self) -> tuple[SafetyDomain, ...]:
        """Return domains with both explicit PASS and FAIL evidence.

        No winner is selected.  The independent records remain available in
        ``evidence`` for a later, separately authorized evaluation policy.
        """

        statuses_by_domain: dict[SafetyDomain, set[SafetyStatus]] = {}
        for item in self.evidence:
            statuses_by_domain.setdefault(item.domain, set()).add(item.status)
        return tuple(
            domain
            for domain in sorted(statuses_by_domain, key=lambda value: value.value)
            if SafetyStatus.PASS in statuses_by_domain[domain]
            and SafetyStatus.FAIL in statuses_by_domain[domain]
        )

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicting_domains)

    @property
    def representation_digest(self) -> str:
        return _digest(self)


class EligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DerivedEligibilityOutput:
    """Future evaluator output; never caller authorization or safety proof."""

    status: EligibilityStatus | str
    evaluator_id: str
    evaluated_at: datetime
    evidence_references: tuple[str, ...]
    contract_version: str = P03_T01_CONTRACT_VERSION

    def __post_init__(self) -> None:
        status = _enum_value(self.status, EligibilityStatus, "status")
        object.__setattr__(self, "status", status)
        _require_text(self.evaluator_id, "evaluator_id")
        _require_aware_datetime(self.evaluated_at, "evaluated_at")
        references = tuple(self.evidence_references)
        if not references or any(not isinstance(value, str) or not value.strip() for value in references):
            raise ValueError("evidence_references must contain non-empty references")
        if len(set(references)) != len(references):
            raise ValueError("evidence_references must be unique")
        _require_text(self.contract_version, "contract_version")

    @property
    def is_authoritative(self) -> bool:
        """Always false: only a future evaluator may derive this output."""

        return False


# Descriptive aliases make the narrow boundary discoverable without creating
# another implementation vocabulary.
TokenSafetyEvidenceRecord = TokenSafetyEvidence
TokenSafetyEvidenceSet = SafetyEvidenceCollection
SafetyEvidenceStatus = SafetyStatus


def validate_safety_evidence(evidence: object) -> tuple[bool, tuple[str, ...]]:
    """Validate an already-created record without evaluating its safety."""

    if not isinstance(evidence, TokenSafetyEvidence):
        return False, ("INVALID_EVIDENCE",)
    return True, ()


def _validate_qualifying_pass(
    *,
    evidence_context: Mapping[str, Any],
    quality: DataQuality,
    freshness_status: DataQuality,
    data_age: timedelta | None,
) -> None:
    if not evidence_context:
        raise ValueError("PASS evidence requires qualifying evidence_context")
    if quality is not DataQuality.VALID:
        raise ValueError("PASS evidence requires VALID quality")
    if freshness_status is not DataQuality.VALID:
        raise ValueError("PASS evidence requires VALID freshness_status")
    if data_age is None:
        raise ValueError("PASS evidence requires data_age")


def _enum_value(value: Any, enum_type: type[StrEnum], name: str) -> StrEnum:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be one of {[item.value for item in enum_type]}") from exc
    raise ValueError(f"{name} must be a supported status/domain")


def _normalise_reason_codes(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    reasons = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in reasons):
        raise ValueError("reason_codes must contain non-empty strings")
    return tuple(dict.fromkeys(reasons))


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_aware_datetime(value: Any, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _canonical_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("metadata must be a mapping")
    result = _canonicalise(value, depth=0, counter=[0])
    if not isinstance(result, dict):
        raise ValueError("metadata must be a mapping")
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > 8192:
        raise ValueError("metadata exceeds the bounded limit")
    return result


def _canonicalise(value: Any, *, depth: int, counter: list[int]) -> Any:
    if depth > 8:
        raise ValueError("metadata exceeds the bounded depth")
    counter[0] += 1
    if counter[0] > 64:
        raise ValueError("metadata exceeds the bounded item count")
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("metadata contains a non-finite number")
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("metadata keys must be strings")
        return {
            key: _canonicalise(value[key], depth=depth + 1, counter=counter)
            for key in sorted(value)
        }
    if isinstance(value, (list, tuple)):
        return [
            _canonicalise(item, depth=depth + 1, counter=counter)
            for item in value
        ]
    raise ValueError(f"metadata value type {type(value).__name__} is not supported")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def _digest(value: Any) -> str:
    material = _canonical_general(value)
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _canonical_general(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Mapping):
        return {str(key): _canonical_general(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonical_general(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_canonical_general(item) for item in value]
        return sorted(
            items,
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    if is_dataclass(value):
        return {
            item.name: _canonical_general(getattr(value, item.name))
            for item in fields(value)
        }
    raise ValueError(f"{type(value).__name__} cannot be deterministically serialized")