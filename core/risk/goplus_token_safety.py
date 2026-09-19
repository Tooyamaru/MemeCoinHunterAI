"""Bounded GoPlus token-safety adapter and P03 evaluation composition.

The provider response is treated as external evidence only. This module does
not grant trading approval, alter the Risk Governor, or create P08 acceptance.
GoPlus's documented token-security response does not include a source
observation timestamp, so non-risk flags cannot become qualifying PASS evidence.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import re
import sys
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from core.data.contracts import DataQuality
from core.risk.safety_eligibility import derive_token_eligibility
from core.risk.safety_evaluation import evaluate_safety_evidence
from core.risk.safety_evidence import (
    EligibilityStatus,
    SafetyDomain,
    SafetyEvidenceCollection,
    SafetyProvenance,
    SafetyStatus,
    TokenSafetyEvidence,
)


SOURCE_ID = "GoPlus"
CONTRACT_VERSION = "p03-safety-assessment-v1"
GO_PLUS_BASE_URL = "https://api.gopluslabs.io"
MAX_RESPONSE_BYTES = 1_048_576
PROVIDER_TIMEOUT_SECONDS = 10
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._~-]+$")

# This is an intentionally bounded first integration. The identifiers and
# endpoint are documented by GoPlus's Token Security API.
SUPPORTED_CHAIN_IDS: dict[str, str] = {
    "ethereum": "1",
    "bsc": "56",
    "arbitrum": "42161",
    "polygon": "137",
    "base": "8453",
    "optimism": "10",
    "avalanche": "43114",
}

EVM_FIELD_DOMAINS: tuple[tuple[SafetyDomain, str], ...] = (
    (SafetyDomain.SUSPICIOUS_MUTABLE_BEHAVIOR, "is_open_source"),
    (SafetyDomain.PROXY_CONTROL_PATTERNS, "is_proxy"),
    (SafetyDomain.MINT_FREEZE_AUTHORITY, "is_mintable"),
    (SafetyDomain.TRADABILITY_SELLABILITY, "is_honeypot"),
    (SafetyDomain.TRADABILITY_SELLABILITY, "cannot_sell_all"),
    (SafetyDomain.TRADABILITY_SELLABILITY, "is_blacklisted"),
    (SafetyDomain.TRADABILITY_SELLABILITY, "is_whitelisted"),
    (SafetyDomain.SUSPICIOUS_MUTABLE_BEHAVIOR, "is_airdrop_scam"),
)


class GoPlusSafetyError(Exception):
    """Sanitized provider or response failure."""

    def __init__(
        self,
        message: str,
        code: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class ProviderResponse:
    endpoint: str
    status_code: int
    response_bytes: int
    received_at: datetime
    payload: Mapping[str, Any]


def normalize_chain_id(chain_id: str) -> str:
    if not isinstance(chain_id, str) or not chain_id.strip():
        raise GoPlusSafetyError(
            "A chain identifier is required.",
            "INVALID_INPUT",
        )
    normalized = chain_id.strip().lower()
    if normalized not in SUPPORTED_CHAIN_IDS:
        supported = ", ".join(sorted(SUPPORTED_CHAIN_IDS))
        raise GoPlusSafetyError(
            f"GoPlus token security is not configured for this chain. Supported chains: {supported}.",
            "UNSUPPORTED_CHAIN",
        )
    return normalized


def validate_token_identity(token_address: str) -> str:
    if (
        not isinstance(token_address, str)
        or not token_address.strip()
        or len(token_address.strip()) > 128
        or not IDENTIFIER_RE.fullmatch(token_address.strip())
    ):
        raise GoPlusSafetyError(
            "The token address contains unsupported characters.",
            "INVALID_INPUT",
        )
    return token_address.strip()


def build_endpoint(chain_id: str, token_address: str) -> str:
    normalized_chain = normalize_chain_id(chain_id)
    token = validate_token_identity(token_address)
    provider_chain = SUPPORTED_CHAIN_IDS[normalized_chain]
    return (
        f"{GO_PLUS_BASE_URL}/api/v1/token_security/{provider_chain}"
        f"?contract_addresses={quote(token, safe='')}"
    )


def _read_bounded(response: Any) -> tuple[bytes, int]:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(64 * 1024, MAX_RESPONSE_BYTES - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise GoPlusSafetyError(
                "The GoPlus response exceeded the configured size limit.",
                "PROVIDER_RESPONSE_TOO_LARGE",
            )
        chunks.append(chunk)
    return b"".join(chunks), total


def fetch_goplus_token_security(
    chain_id: str,
    token_address: str,
    *,
    opener: Callable[..., Any] = urlopen,
    received_at: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    access_token: str | None = None,
) -> ProviderResponse:
    endpoint = build_endpoint(chain_id, token_address)
    headers = {
        "Accept": "application/json",
        "User-Agent": "memecoin-inspection-token-safety/1",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    request = Request(endpoint, headers=headers, method="GET")
    try:
        with opener(request, timeout=PROVIDER_TIMEOUT_SECONDS) as response:
            body, response_bytes = _read_bounded(response)
            status_code = int(response.status)
    except HTTPError as error:
        if error.code in {401, 403}:
            code = "PROVIDER_AUTH_REQUIRED"
        elif error.code == 404:
            code = "PROVIDER_NOT_FOUND"
        else:
            code = "PROVIDER_HTTP_ERROR"
        raise GoPlusSafetyError(
            "The GoPlus token-security request failed.",
            code,
            status_code=error.code,
        ) from error
    except TimeoutError as error:
        raise GoPlusSafetyError(
            "The GoPlus token-security request timed out.",
            "PROVIDER_TIMEOUT",
        ) from error
    except URLError as error:
        raise GoPlusSafetyError(
            "The GoPlus token-security request failed.",
            "PROVIDER_FAILURE",
        ) from error

    if status_code < 200 or status_code >= 300:
        raise GoPlusSafetyError(
            "The GoPlus token-security request returned a non-success status.",
            "PROVIDER_HTTP_ERROR",
            status_code=status_code,
        )

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GoPlusSafetyError(
            "The GoPlus response was not valid JSON.",
            "PROVIDER_MALFORMED_RESPONSE",
        ) from error
    if not isinstance(payload, dict):
        raise GoPlusSafetyError(
            "The GoPlus response was not an object.",
            "PROVIDER_MALFORMED_RESPONSE",
        )

    return ProviderResponse(
        endpoint=endpoint,
        status_code=status_code,
        response_bytes=response_bytes,
        received_at=_aware(received_at(), "received_at"),
        payload=payload,
    )


def _aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return _aware(value, "timestamp").isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _provider_record(
    payload: Mapping[str, Any],
    token_address: str,
) -> Mapping[str, Any]:
    if payload.get("code") != 1:
        raise GoPlusSafetyError(
            "GoPlus did not return a successful token-security result.",
            "PROVIDER_RESPONSE_ERROR",
        )
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise GoPlusSafetyError(
            "GoPlus returned an invalid token-security result.",
            "PROVIDER_MALFORMED_RESPONSE",
        )
    if not result:
        raise GoPlusSafetyError(
            "GoPlus returned no token-security record.",
            "PROVIDER_NO_RESULT",
        )

    exact = result.get(token_address)
    if exact is None:
        matching = [
            value
            for key, value in result.items()
            if isinstance(key, str) and key.lower() == token_address.lower()
        ]
        exact = matching[0] if len(matching) == 1 else None
    if exact is None:
        raise GoPlusSafetyError(
            "GoPlus returned a token-security record for a different identity.",
            "PROVIDER_IDENTITY_MISMATCH",
        )
    if not isinstance(exact, Mapping):
        raise GoPlusSafetyError(
            "GoPlus returned an invalid token-security record.",
            "PROVIDER_MALFORMED_RESPONSE",
        )
    return exact


def _field_value(record: Mapping[str, Any], field: str) -> Any:
    return record.get(field)


def _field_evidence(
    *,
    chain_id: str,
    token_address: str,
    domain: SafetyDomain,
    field: str,
    value: Any,
    endpoint: str,
    assessment_time: datetime,
) -> TokenSafetyEvidence:
    source_observed_at = None
    context = {
        "provider": SOURCE_ID,
        "provider_field": field,
        "provider_value": value if isinstance(value, (str, int, bool)) else None,
        "source_observed_at": source_observed_at,
        "source_timestamp_status": "UNAVAILABLE",
    }
    reference = f"{SOURCE_ID}:{chain_id}:{token_address}:{field}"

    risk_value = "0" if field == "is_open_source" else "1"
    clear_value = "1" if field == "is_open_source" else "0"
    if value is True and risk_value == "1" or value == risk_value:
        status = SafetyStatus.FAIL
        quality = DataQuality.VALID
        freshness = DataQuality.INCOMPLETE
        data_age = None
        reason_codes = ("PROVIDER_RISK_FLAG",)
    elif value is False and clear_value == "0" or value == clear_value:
        status = SafetyStatus.UNKNOWN
        quality = DataQuality.INCOMPLETE
        freshness = DataQuality.INCOMPLETE
        data_age = None
        reason_codes = ("SOURCE_OBSERVATION_TIME_UNAVAILABLE",)
    elif value is None or value == "":
        status = SafetyStatus.UNKNOWN
        quality = DataQuality.INCOMPLETE
        freshness = DataQuality.INCOMPLETE
        data_age = None
        reason_codes = ("MISSING_PROVIDER_FIELD",)
    else:
        status = SafetyStatus.UNKNOWN
        quality = DataQuality.INVALID
        freshness = DataQuality.INVALID
        data_age = None
        reason_codes = ("UNRECOGNIZED_PROVIDER_VALUE",)

    context["endpoint"] = endpoint
    return TokenSafetyEvidence(
        chain_id=chain_id,
        token_identity=token_address,
        domain=domain,
        status=status,
        source_id=SOURCE_ID,
        observed_at=assessment_time,
        quality=quality,
        freshness_status=freshness,
        data_age=data_age,
        provenance=SafetyProvenance(
            source_id=SOURCE_ID,
            method="token-security-api",
            observed_at=assessment_time,
            metadata={
                "endpoint": endpoint,
                "source_observed_at": source_observed_at,
            },
        ),
        evidence_reference=reference,
        evidence_context=context,
        reason_codes=reason_codes,
    )


def _serialize_evidence(evidence: TokenSafetyEvidence) -> dict[str, Any]:
    return {
        "domain": evidence.domain.value,
        "status": evidence.status.value,
        "quality": evidence.quality.value,
        "freshness_status": evidence.freshness_status.value,
        "observed_at": _timestamp(evidence.observed_at),
        "source_id": evidence.source_id,
        "method": evidence.provenance.method,
        "evidence_reference": evidence.evidence_reference,
        "evidence_context": dict(evidence.evidence_context),
        "reason_codes": list(evidence.reason_codes),
    }


def compose_safety_assessment(
    *,
    chain_id: str,
    token_address: str,
    provider: ProviderResponse,
    assessment_time: datetime,
) -> dict[str, Any]:
    normalized_chain = normalize_chain_id(chain_id)
    token = validate_token_identity(token_address)
    evaluation_time = _aware(assessment_time, "assessment_time")
    record = _provider_record(provider.payload, token)

    present_fields = {
        field for _, field in EVM_FIELD_DOMAINS if field in record
    }
    evidence_items: list[TokenSafetyEvidence] = []
    for domain, field in EVM_FIELD_DOMAINS:
        if field in present_fields:
            evidence_items.append(
                _field_evidence(
                    chain_id=normalized_chain,
                    token_address=token,
                    domain=domain,
                    field=field,
                    value=_field_value(record, field),
                    endpoint=provider.endpoint,
                    assessment_time=evaluation_time,
                )
            )
    represented_domains = {domain for domain, _ in EVM_FIELD_DOMAINS}
    evidence_domains = {item.domain for item in evidence_items}
    for domain in sorted(represented_domains - evidence_domains, key=lambda item: item.value):
        evidence_items.append(
            _field_evidence(
                chain_id=normalized_chain,
                token_address=token,
                domain=domain,
                field=f"{domain.value}:unavailable",
                value=None,
                endpoint=provider.endpoint,
                assessment_time=evaluation_time,
            )
        )
    evidence = tuple(evidence_items)
    collection = SafetyEvidenceCollection.from_evidence(list(evidence))
    evaluation = evaluate_safety_evidence(
        collection,
        evaluation_timestamp=evaluation_time,
    )
    eligibility = derive_token_eligibility(evaluation)

    missing_evidence = [
        {
            "domain": domain.value,
            "requirement": "A documented provider safety field with a source observation timestamp.",
            "reason": (
                "GoPlus does not document a source observation timestamp in this "
                "response, so non-risk flags remain UNKNOWN."
            if domain not in represented_domains
            else "The provider did not return this mapped field."
            ),
            "provider_field": field,
        }
        for domain, field in EVM_FIELD_DOMAINS
        if field not in present_fields
    ]
    missing_evidence.extend(
        {
            "domain": domain.value,
            "requirement": "A documented provider safety field with a source observation timestamp.",
            "reason": "This first integration does not map a provider field to this domain.",
        }
        for domain in SafetyDomain
        if domain not in represented_domains
    )
    missing_evidence.extend(
        {
            "domain": item.domain.value,
            "requirement": "A documented provider safety field with a source observation timestamp.",
            "reason": "The provider did not document a source observation timestamp.",
            "provider_field": item.evidence_context.get("provider_field"),
        }
        for item in evidence
        if item.status is SafetyStatus.UNKNOWN
        and item.evidence_context.get("provider_field") in present_fields
    )

    limitations = [
        "This is non-authoritative safety evidence evaluation, not a safety guarantee.",
        "The GoPlus response does not document a source observation timestamp; receipt or assessment time is not substituted for source time.",
        "The documented response does not expose a mapped freeze-authority field; freeze-related evidence remains incomplete.",
        "Unknown or unavailable evidence remains non-positive and can never become favorable assessment evidence.",
        "This result does not approve trading, authorize capital, or establish P08 acceptance.",
        "The first integration supports only the bounded EVM chain set exposed by this adapter.",
    ]
    return {
        "assessment_version": CONTRACT_VERSION,
        "identity": {"chain_id": normalized_chain, "token_address": token},
        "source": {
            "source_id": SOURCE_ID,
            "endpoint": provider.endpoint,
            "http_status": provider.status_code,
            "response_bytes": provider.response_bytes,
            "received_at": _timestamp(provider.received_at),
            "source_observed_at": None,
            "source_freshness": "UNKNOWN",
        },
        "evaluation": {
            "status": eligibility.status.value,
            "is_authoritative": eligibility.is_authoritative,
            "evaluator_id": eligibility.evaluator_id,
            "contract_version": evaluation.contract_version,
            "evaluation_timestamp": _timestamp(evaluation.evaluation_timestamp),
            "input_evidence_digest": evaluation.input_evidence_digest,
            "domain_results": {
                domain.value: status.value
                for domain, status in evaluation.domain_results.items()
            },
            "evidence_references": list(evaluation.evidence_references),
            "reason_codes": list(evaluation.reason_codes),
        },
        "evidence": [_serialize_evidence(item) for item in evidence],
        "missing_evidence": missing_evidence,
        "limitations": limitations,
    }


def assess_token_safety(
    chain_id: str,
    token_address: str,
    *,
    fetcher: Callable[..., ProviderResponse] = fetch_goplus_token_security,
    assessment_time: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    access_token: str | None = None,
) -> dict[str, Any]:
    normalized_chain = normalize_chain_id(chain_id)
    token = validate_token_identity(token_address)
    provider = fetcher(
        normalized_chain,
        token,
        access_token=access_token,
    )
    return compose_safety_assessment(
        chain_id=normalized_chain,
        token_address=token,
        provider=provider,
        assessment_time=assessment_time(),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one explicit bounded GoPlus token-safety assessment."
    )
    parser.add_argument("--chain-id", required=True)
    parser.add_argument("--token-address", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = assess_token_safety(
            args.chain_id,
            args.token_address,
            access_token=os.environ.get("GOPLUS_ACCESS_TOKEN"),
        )
    except GoPlusSafetyError as error:
        print(
            json.dumps(
                {"error": {"code": error.code, "message": str(error)}},
                ensure_ascii=False,
            )
        )
        return 1
    except (ValueError, TypeError) as error:
        print(
            json.dumps(
                {"error": {"code": "SAFETY_ASSESSMENT_FAILURE", "message": str(error)}},
                ensure_ascii=False,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "CONTRACT_VERSION",
    "GO_PLUS_BASE_URL",
    "GoPlusSafetyError",
    "ProviderResponse",
    "SUPPORTED_CHAIN_IDS",
    "assess_token_safety",
    "build_endpoint",
    "compose_safety_assessment",
    "fetch_goplus_token_security",
    "main",
]