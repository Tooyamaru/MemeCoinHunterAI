"""Deterministic, non-authoritative safety evaluation for P03-T02.

This module consumes P03-T01 evidence only.  It does not collect evidence,
resolve conflicts by selecting a winner, derive eligibility, authorize a
decision, or perform any external I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.risk.safety_evidence import (
    SafetyDomain,
    SafetyEvidenceCollection,
    SafetyProvenance,
    SafetyStatus,
    TokenSafetyEvidence,
)


P03_T02_CONTRACT_VERSION = "p03-t02-v1"


@dataclass(frozen=True)
class SafetyEvaluationResult:
    """Immutable, non-authoritative evaluation of preserved safety evidence."""

    chain_id: str
    token_identity: str
    input_evidence_digest: str
    evaluation_timestamp: datetime
    contract_version: str
    domain_results: Mapping[SafetyDomain, SafetyStatus]
    evidence_references: tuple[str, ...]
    reason_codes: tuple[str, ...]
    provenance: tuple[SafetyProvenance, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.chain_id, "chain_id")
        _require_text(self.token_identity, "token_identity")
        _require_text(self.input_evidence_digest, "input_evidence_digest")
        _require_aware_datetime(self.evaluation_timestamp, "evaluation_timestamp")
        _require_text(self.contract_version, "contract_version")

        if not isinstance(self.domain_results, Mapping):
            raise ValueError("domain_results must be a mapping")
        domain_results: dict[SafetyDomain, SafetyStatus] = {}
        for domain, status in self.domain_results.items():
            domain_value = _enum_value(domain, SafetyDomain, "domain")
            status_value = _enum_value(status, SafetyStatus, "status")
            domain_results[domain_value] = status_value
        object.__setattr__(
            self,
            "domain_results",
            MappingProxyType(
                {
                    domain: domain_results[domain]
                    for domain in sorted(domain_results, key=lambda value: value.value)
                }
            ),
        )

        references = tuple(self.evidence_references)
        if any(not isinstance(value, str) or not value.strip() for value in references):
            raise ValueError("evidence_references must contain non-empty references")

        reasons = tuple(self.reason_codes)
        if any(not isinstance(value, str) or not value.strip() for value in reasons):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(self, "reason_codes", tuple(sorted(dict.fromkeys(reasons))))

        provenance = tuple(self.provenance)
        if not all(isinstance(value, SafetyProvenance) for value in provenance):
            raise ValueError("provenance must contain SafetyProvenance values")
        if len(references) != len(provenance):
            raise ValueError(
                "evidence_references and provenance must have equal lengths"
            )
        traceable_records = tuple(
            sorted(
                zip(references, provenance),
                key=lambda pair: (pair[0], _provenance_sort_key(pair[1])),
            )
        )
        object.__setattr__(
            self,
            "evidence_references",
            tuple(reference for reference, _ in traceable_records),
        )
        object.__setattr__(
            self,
            "provenance",
            tuple(provenance for _, provenance in traceable_records),
        )

    @property
    def representation_digest(self) -> str:
        return _digest(self)

    @property
    def is_authoritative(self) -> bool:
        """Always false: this result is not eligibility or authorization."""

        return False


SafetyEvidenceEvaluation = SafetyEvaluationResult


def evaluate_safety_evidence(
    evidence: SafetyEvidenceCollection,
    *,
    evaluation_timestamp: datetime,
) -> SafetyEvaluationResult:
    """Evaluate each represented domain without mutating the input collection."""

    if not isinstance(evidence, SafetyEvidenceCollection):
        raise ValueError("evidence must be a SafetyEvidenceCollection")
    _require_aware_datetime(evaluation_timestamp, "evaluation_timestamp")

    by_domain: dict[SafetyDomain, list[TokenSafetyEvidence]] = {}
    future_by_domain: dict[SafetyDomain, list[TokenSafetyEvidence]] = {}
    for item in evidence.evidence:
        target = (
            future_by_domain
            if item.observed_at > evaluation_timestamp
            else by_domain
        )
        target.setdefault(item.domain, []).append(item)

    domain_results: dict[SafetyDomain, SafetyStatus] = {}
    reason_codes: set[str] = set()
    if not evidence.evidence:
        reason_codes.add("NO_EVIDENCE")

    for domain in sorted(
        set(by_domain) | set(future_by_domain),
        key=lambda value: value.value,
    ):
        records = by_domain.get(domain, [])
        future_records = future_by_domain.get(domain, [])

        if not records:
            result = SafetyStatus.UNKNOWN
            reason = "FUTURE_DATED_EVIDENCE"
        else:
            statuses = {item.status for item in records}

            if SafetyStatus.UNKNOWN in statuses:
                result = SafetyStatus.UNKNOWN
                reason = "UNKNOWN_EVIDENCE"
            elif SafetyStatus.PASS in statuses and SafetyStatus.FAIL in statuses:
                result = SafetyStatus.UNKNOWN
                reason = "CONTRADICTORY_EVIDENCE"
            elif SafetyStatus.PASS in statuses:
                result = SafetyStatus.PASS
                reason = "PASS_EVIDENCE"
            else:
                result = SafetyStatus.FAIL
                reason = "FAIL_EVIDENCE"

        domain_results[domain] = result
        reason_codes.add(reason)
        reason_codes.add(f"{domain.value}:{reason}")
        for item in records:
            for item_reason in item.reason_codes:
                reason_codes.add(f"{domain.value}:{item_reason}")
        if future_records:
            reason_codes.add("FUTURE_DATED_EVIDENCE")
            reason_codes.add(f"{domain.value}:FUTURE_DATED_EVIDENCE")

    return SafetyEvaluationResult(
        chain_id=evidence.chain_id,
        token_identity=evidence.token_identity,
        input_evidence_digest=evidence.representation_digest,
        evaluation_timestamp=evaluation_timestamp,
        contract_version=P03_T02_CONTRACT_VERSION,
        domain_results=domain_results,
        evidence_references=tuple(
            item.evidence_reference for item in evidence.evidence
        ),
        reason_codes=tuple(reason_codes),
        provenance=tuple(item.provenance for item in evidence.evidence),
    )


def _enum_value(
    value: Any,
    enum_type: type[StrEnum],
    name: str,
) -> StrEnum:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError as exc:
            raise ValueError(
                f"{name} must be one of {[item.value for item in enum_type]}"
            ) from exc
    raise ValueError(f"{name} must be a supported enum value")


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_aware_datetime(value: Any, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")


def _provenance_sort_key(value: SafetyProvenance) -> tuple[str, str, str, str]:
    metadata = json.dumps(
        _canonical_general(value.metadata),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return (
        value.source_id,
        value.method,
        value.observed_at.astimezone(timezone.utc).isoformat(),
        metadata,
    )


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
    if isinstance(value, StrEnum):
        return value.value
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