"""Bounded bridge for re-evaluating already-held P03 safety evidence.

The bridge performs no provider I/O.  It accepts one serialized assessment
already held by the caller and reuses the canonical P03 evaluator so the API
does not maintain a second safety policy.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import sys
from typing import Any, Mapping

from core.data.contracts import DataQuality
from core.risk.safety_eligibility import derive_token_eligibility
from core.risk.safety_evaluation import evaluate_safety_evidence
from core.risk.safety_evidence import (
    SafetyEvidenceCollection,
    SafetyProvenance,
    TokenSafetyEvidence,
)


class SafetyDiagnosticInputError(ValueError):
    """The supplied assessment cannot cross the bounded evaluator bridge."""


def evaluate_supplied_safety(payload: Mapping[str, Any]) -> dict[str, Any]:
    chain_id, token_identity, evaluation_time = _read_identity_and_time(payload)
    raw_evidence = payload.get("evidence")
    if not isinstance(raw_evidence, list):
        raise SafetyDiagnosticInputError("evidence must be a list")

    if not raw_evidence:
        return {
            "status": "UNKNOWN",
            "evidence_references": [],
            "reason_codes": ["NO_EVIDENCE"],
            "domain_results": {},
        }

    evidence = tuple(
        _build_evidence(
            item,
            chain_id=chain_id,
            token_identity=token_identity,
            evaluation_time=evaluation_time,
        )
        for item in raw_evidence
    )
    collection = SafetyEvidenceCollection.from_evidence(list(evidence))
    evaluation = evaluate_safety_evidence(
        collection,
        evaluation_timestamp=evaluation_time,
    )
    eligibility = derive_token_eligibility(evaluation)
    return {
        "status": eligibility.status.value,
        "evidence_references": list(evaluation.evidence_references),
        "reason_codes": list(evaluation.reason_codes),
        "domain_results": {
            domain.value: status.value
            for domain, status in evaluation.domain_results.items()
        },
    }


def _read_identity_and_time(
    payload: Mapping[str, Any],
) -> tuple[str, str, datetime]:
    identity = payload.get("identity")
    evaluation = payload.get("evaluation")
    if not isinstance(identity, Mapping) or not isinstance(evaluation, Mapping):
        raise SafetyDiagnosticInputError("identity and evaluation are required")
    chain_id = _required_text(identity.get("chain_id"), "identity.chain_id")
    token_identity = _required_text(
        identity.get("token_address"),
        "identity.token_address",
    )
    evaluation_time = _timestamp(
        evaluation.get("evaluation_timestamp"),
        "evaluation.evaluation_timestamp",
    )
    return chain_id, token_identity, evaluation_time


def _build_evidence(
    item: Any,
    *,
    chain_id: str,
    token_identity: str,
    evaluation_time: datetime,
) -> TokenSafetyEvidence:
    if not isinstance(item, Mapping):
        raise SafetyDiagnosticInputError("evidence items must be objects")
    source_id = _required_text(item.get("source_id"), "evidence.source_id")
    method = _required_text(item.get("method"), "evidence.method")
    observed_at = _timestamp(item.get("observed_at"), "evidence.observed_at")
    context = item.get("evidence_context", {})
    if not isinstance(context, Mapping):
        raise SafetyDiagnosticInputError("evidence.evidence_context must be an object")

    status = _required_text(item.get("status"), "evidence.status")
    quality = _quality(item.get("quality"))
    freshness = _quality(item.get("freshness_status"))
    data_age = (
        evaluation_time - observed_at
        if observed_at <= evaluation_time
        else None
    )
    return TokenSafetyEvidence(
        chain_id=chain_id,
        token_identity=token_identity,
        domain=_required_text(item.get("domain"), "evidence.domain"),
        status=status,
        source_id=source_id,
        observed_at=observed_at,
        quality=quality,
        freshness_status=freshness,
        data_age=data_age,
        provenance=SafetyProvenance(
            source_id=source_id,
            method=method,
            observed_at=observed_at,
            metadata=dict(context),
        ),
        evidence_reference=_required_text(
            item.get("evidence_reference"),
            "evidence.evidence_reference",
        ),
        evidence_context=dict(context),
        reason_codes=tuple(_required_texts(item.get("reason_codes", []))),
    )


def _quality(value: Any) -> DataQuality:
    # The public report preserves UNKNOWN as a non-positive state while the
    # P03 contract represents it as incomplete data quality.
    if value == "UNKNOWN":
        return DataQuality.INCOMPLETE
    try:
        return DataQuality(value)
    except (TypeError, ValueError) as error:
        raise SafetyDiagnosticInputError("unsupported evidence quality") from error


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SafetyDiagnosticInputError(f"{name} is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise SafetyDiagnosticInputError(f"{name} must be an ISO timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SafetyDiagnosticInputError(f"{name} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SafetyDiagnosticInputError(f"{name} must be non-empty text")
    return value


def _required_texts(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise SafetyDiagnosticInputError("reason_codes must be a list")
    return tuple(
        _required_text(item, "reason_codes item")
        for item in value
    )


def main() -> int:
    try:
        raw = json.load(sys.stdin)
        if not isinstance(raw, Mapping):
            raise SafetyDiagnosticInputError("request must be an object")
        result = evaluate_supplied_safety(raw)
    except (SafetyDiagnosticInputError, TypeError, ValueError) as error:
        json.dump(
            {"error": {"code": "INVALID_EVIDENCE", "message": str(error)}},
            sys.stdout,
        )
        return 2
    json.dump(result, sys.stdout, separators=(",", ":"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["SafetyDiagnosticInputError", "evaluate_supplied_safety", "main"]