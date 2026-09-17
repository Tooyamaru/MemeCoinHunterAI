"""Inspection-only DexScreener token-pairs report and command-line tool.

The report preserves source-shaped pair data and transport provenance.  It is
not a P08 observation and intentionally has no dependency on the P08 validator
or any discovery, decision, paper-admission, wallet, or execution boundary.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
import sys
from typing import Any, Callable, Mapping

from core.data.dexscreener_transport import (
    AttemptRecord,
    DexScreenerTransportError,
    TokenPairsResponse,
    build_token_pairs_url,
    fetch_token_pairs,
)


TOOL_VERSION = "dexscreener-inspection-v1"
EXPECTED_PAIR_FIELDS = (
    "pairAddress",
    "chainId",
    "dexId",
    "baseToken",
    "quoteToken",
    "priceUsd",
    "liquidity",
    "volume",
    "txns",
    "pairCreatedAt",
)
NUMERIC_FIELD_NAMES = frozenset(
    {
        "priceNative",
        "priceUsd",
        "fdv",
        "marketCap",
        "pairCreatedAt",
        "usd",
        "base",
        "quote",
        "m5",
        "h1",
        "h6",
        "h24",
        "buys",
        "sells",
    }
)


class InspectionError(ValueError):
    """Explicit parser or source-shape failure."""

    code = "INSPECTION_ERROR"

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.path = path
        self.response: TokenPairsResponse | None = None


class MalformedJsonError(InspectionError):
    code = "MALFORMED_JSON"


class InvalidSourceShapeError(InspectionError):
    code = "INVALID_SOURCE_SHAPE"


class InvalidNumericFieldError(InspectionError):
    code = "INVALID_NUMERIC_FIELD"


class NonFiniteNumberError(InspectionError):
    code = "NON_FINITE_NUMBER"


def _reject_non_finite(token: str) -> None:
    raise NonFiniteNumberError(f"non-finite JSON number {token!r}")


def _parse_json(body: bytes) -> Any:
    try:
        return json.loads(
            body.decode("utf-8"),
            parse_int=Decimal,
            parse_float=Decimal,
            parse_constant=_reject_non_finite,
        )
    except NonFiniteNumberError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MalformedJsonError("response was not valid UTF-8 JSON") from error


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise NonFiniteNumberError("non-finite numeric value")
    return str(value)


def _normalize_value(
    value: Any,
    *,
    path: str,
    field_provenance: dict[str, dict[str, Any]],
) -> Any:
    if isinstance(value, Decimal):
        normalized = _decimal_text(value)
    elif isinstance(value, Mapping):
        normalized = {
            str(key): _normalize_value(
                child,
                path=f"{path}.{key}",
                field_provenance=field_provenance,
            )
            for key, child in value.items()
        }
    elif isinstance(value, list):
        normalized = [
            _normalize_value(
                child,
                path=f"{path}[{index}]",
                field_provenance=field_provenance,
            )
            for index, child in enumerate(value)
        ]
    elif value is None or isinstance(value, (str, bool)):
        normalized = value
    else:
        raise InvalidSourceShapeError(f"unsupported JSON value at {path}", path=path)

    field_provenance[path] = {
        "source_field": path,
        "normalized_value": normalized,
    }
    return normalized


def _leaf_values(value: Any, *, path: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            result.update(_leaf_values(child, path=child_path))
        return result
    if isinstance(value, list):
        result = {}
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]" if path else f"[{index}]"
            result.update(_leaf_values(child, path=child_path))
        return result
    return {path: value}


def _numeric_findings(value: Any, *, path: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in NUMERIC_FIELD_NAMES:
                if isinstance(child, str):
                    try:
                        parsed = Decimal(child)
                    except (InvalidOperation, ValueError):
                        findings.append(
                            {
                                "code": "INVALID_NUMERIC_FIELD",
                                "source_field": child_path,
                                "value": child,
                            }
                        )
                    else:
                        if not parsed.is_finite():
                            findings.append(
                                {
                                    "code": "INVALID_NUMERIC_FIELD",
                                    "source_field": child_path,
                                    "value": child,
                                }
                            )
                elif not isinstance(child, (Decimal, int)) or isinstance(child, bool):
                    findings.append(
                        {
                            "code": "INVALID_NUMERIC_FIELD",
                            "source_field": child_path,
                            "value": child,
                        }
                    )
            findings.extend(_numeric_findings(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_numeric_findings(child, path=f"{path}[{index}]"))
    return findings


def _pair_findings(pair: Mapping[str, Any], *, index: int) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for field in EXPECTED_PAIR_FIELDS:
        if field not in pair:
            findings.append(
                {
                    "code": "MISSING_SOURCE_FIELD",
                    "source_field": f"pairs[{index}].{field}",
                }
            )
    findings.extend(_numeric_findings(pair, path=f"pairs[{index}]"))
    return findings


def _duplicate_findings(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_address: dict[str, list[int]] = {}
    for index, pair in enumerate(pairs):
        address = pair.get("pairAddress")
        if isinstance(address, str):
            by_address.setdefault(address, []).append(index)

    findings: list[dict[str, Any]] = []
    for address, indices in by_address.items():
        if len(indices) < 2:
            continue
        findings.append(
            {
                "code": "DUPLICATE_PAIR",
                "pair_address": address,
                "indices": indices,
            }
        )
        normalized_pairs = [
            {key: value for key, value in pairs[index].items() if key != "inspection"}
            for index in indices
        ]
        if any(pair != normalized_pairs[0] for pair in normalized_pairs[1:]):
            first_leaves = _leaf_values(normalized_pairs[0], path="")
            differing_paths = sorted(
                {
                    f"pairs[{indices[0]}].{path}"
                    for current_index, current in zip(indices[1:], normalized_pairs[1:])
                    for path in set(first_leaves)
                    | set(_leaf_values(current, path=""))
                    if first_leaves.get(path)
                    != _leaf_values(current, path="").get(path)
                }
            )
            findings.append(
                {
                    "code": "CONFLICTING_DUPLICATE_PAIR",
                    "pair_address": address,
                    "indices": indices,
                    "different_source_fields": differing_paths,
                }
            )
    return findings


def _evidence() -> dict[str, Any]:
    return {
        "p08_acceptance": "NOT_ATTEMPTED",
        "p08_observed_at": None,
        "asset_age": {
            "status": "UNAVAILABLE",
            "value": None,
            "reason": "SOURCE_DOES_NOT_DOCUMENT_TOKEN_ORIGIN_SEMANTICS",
        },
        "unavailable_fields": [
            {
                "field": "observed_at",
                "reason": "NO_DOCUMENTED_MARKET_FIELD_OBSERVATION_TIMESTAMP",
            },
            {
                "field": "asset_age",
                "reason": "NO_DOCUMENTED_TOKEN_ORIGIN_SEMANTICS",
            },
            {
                "field": "volume.measurement_window",
                "reason": "NO_EXACT_UTC_WINDOW_ENDPOINTS",
            },
        ],
    }


def _attempt_dicts(attempts: tuple[AttemptRecord, ...]) -> list[dict[str, Any]]:
    return [attempt.as_dict() for attempt in attempts]


def inspect_response(response: TokenPairsResponse) -> dict[str, Any]:
    """Normalize one successful transport response without selecting a pair."""

    try:
        raw_payload_sha256 = hashlib.sha256(response.body).hexdigest()
        payload = _parse_json(response.body)
        if not isinstance(payload, list):
            raise InvalidSourceShapeError("response root must be an array", path="$")
        if len(payload) > 128:
            raise InvalidSourceShapeError(
                "response contained more than 128 pairs",
                path="$",
            )

        pairs: list[dict[str, Any]] = []
        for index, raw_pair in enumerate(payload):
            if not isinstance(raw_pair, Mapping):
                raise InvalidSourceShapeError(
                    f"pair at index {index} must be an object",
                    path=f"pairs[{index}]",
                )
            provenance: dict[str, dict[str, Any]] = {}
            normalized_pair = _normalize_value(
                raw_pair,
                path=f"pairs[{index}]",
                field_provenance=provenance,
            )
            if not isinstance(normalized_pair, dict):
                raise InvalidSourceShapeError(
                    f"pair at index {index} must normalize to an object",
                    path=f"pairs[{index}]",
                )
            findings = _pair_findings(raw_pair, index=index)
            inspection: dict[str, Any] = {
                "field_provenance": provenance,
                "findings": findings,
            }
            if "pairCreatedAt" in normalized_pair:
                inspection["source_pair_created_at"] = normalized_pair["pairCreatedAt"]
            normalized_pair["inspection"] = inspection
            pairs.append(normalized_pair)

        duplicate_findings = _duplicate_findings(pairs)
        if duplicate_findings:
            for finding in duplicate_findings:
                for index in finding["indices"]:
                    pairs[index]["inspection"]["findings"].append(finding)

        return {
            "tool_version": TOOL_VERSION,
            "source": "DexScreener",
            "request": {
                "endpoint": response.endpoint,
                "chain_id": response.chain_id,
                "token_address": response.token_address,
                "attempts": len(response.attempts),
                "retry_count": max(0, len(response.attempts) - 1),
                "attempt_log": _attempt_dicts(response.attempts),
            },
            "receipt": {
                "received_at": response.received_at,
                "http_status": response.status_code,
                "response_bytes": len(response.body),
            },
            "payload": {
                "raw_payload_sha256": raw_payload_sha256,
                "pair_count": len(pairs),
                "pairs": pairs,
            },
            "evidence": _evidence(),
        }
    except InspectionError as error:
        error.response = response
        raise


def inspect_token(
    chain_id: str,
    token_address: str,
    *,
    transport: Callable[..., TokenPairsResponse] = fetch_token_pairs,
) -> dict[str, Any]:
    """Fetch exactly one requested token and return its inspection report."""

    return inspect_response(transport(chain_id, token_address))


def _error_report(
    error: BaseException,
    *,
    chain_id: str,
    token_address: str,
) -> dict[str, Any]:
    response = getattr(error, "response", None)
    attempts = getattr(error, "attempts", ())
    try:
        endpoint = build_token_pairs_url(chain_id, token_address)
    except ValueError:
        endpoint = "<invalid-request>"
    if response is not None:
        attempts = response.attempts
        response_bytes = len(response.body)
        received_at = response.received_at
        status_code = response.status_code
        digest = hashlib.sha256(response.body).hexdigest()
    else:
        response_bytes = attempts[-1].response_bytes if attempts else 0
        received_at = attempts[-1].received_at if attempts else None
        status_code = attempts[-1].status_code if attempts else None
        digest = None
    code = getattr(error, "code", "INSPECTION_ERROR")
    return {
        "tool_version": TOOL_VERSION,
        "source": "DexScreener",
        "request": {
            "endpoint": endpoint,
            "chain_id": chain_id,
            "token_address": token_address,
            "attempts": len(attempts),
            "retry_count": max(0, len(attempts) - 1),
            "attempt_log": _attempt_dicts(tuple(attempts)),
        },
        "receipt": {
            "received_at": received_at,
            "http_status": status_code,
            "response_bytes": response_bytes,
        },
        "payload": {
            "raw_payload_sha256": digest,
            "pair_count": 0,
            "pairs": [],
        },
        "evidence": _evidence(),
        "error": {
            "code": code,
            "message": str(error),
            "path": getattr(error, "path", None),
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch one DexScreener token lookup and print an inspection-only "
            "report; this does not produce a validated P08 observation."
        )
    )
    parser.add_argument("--chain-id", required=True)
    parser.add_argument("--token-address", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = inspect_token(args.chain_id, args.token_address)
    except (DexScreenerTransportError, InspectionError, ValueError) as error:
        report = _error_report(
            error,
            chain_id=args.chain_id,
            token_address=args.token_address,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())