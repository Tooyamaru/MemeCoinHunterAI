"""Pure temporal evidence derived from the existing inspection-report contract.

This module deliberately does not fetch, parse, select, aggregate, or admit
market data.  It preserves the current inspector's explicit evidence while
making receipt recency, unknown source freshness, rolling volume labels, and
pair-age evidence machine-checkable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping


CONTRACT_VERSION = "p08-market-data-temporal-evidence-v1"
INSPECTOR_TOOL_VERSION = "dexscreener-inspection-v1"
INSPECTOR_SOURCE = "DexScreener"
P08_ACCEPTANCE = "NOT_ATTEMPTED"
MAX_TEXT_SCALARS = 256
MAX_TEXT_BYTES = 1024
MAX_SEQUENCE_ELEMENTS = 128
MAX_MAPPING_DEPTH = 8
MAX_MAPPING_MEMBERS = 64
MAX_MAPPING_BYTES = 16_384
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


class TemporalEvidenceError(ValueError):
    """The inspection report cannot be represented by this contract."""


class SourceFreshnessStatus(StrEnum):
    UNKNOWN = "UNKNOWN"


class AssetAgeStatus(StrEnum):
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class SourceFreshnessEvidence:
    status: SourceFreshnessStatus
    reason: str

    def __post_init__(self) -> None:
        if self.status is not SourceFreshnessStatus.UNKNOWN:
            raise TemporalEvidenceError("source freshness must remain UNKNOWN")
        _canonical_text(self.reason, "source_freshness.reason")

    def as_mapping(self) -> dict[str, Any]:
        return {"status": self.status.value, "reason": self.reason}


@dataclass(frozen=True)
class ReceiptRecency:
    reference_time: str
    age_seconds: str

    def __post_init__(self) -> None:
        _timestamp(self.reference_time, "receipt_recency.reference_time")
        _decimal_text(self.age_seconds, "receipt_recency.age_seconds")
        if Decimal(self.age_seconds) < Decimal("0"):
            raise TemporalEvidenceError("receipt recency cannot be negative")

    def as_mapping(self) -> dict[str, str]:
        return {
            "reference_time": self.reference_time,
            "age_seconds": self.age_seconds,
        }


@dataclass(frozen=True)
class VolumeWindowEvidence:
    source_label: str | None
    exact_window: None = None

    def __post_init__(self) -> None:
        if self.source_label is not None:
            _canonical_text(self.source_label, "volume_window.source_label")
        if self.exact_window is not None:
            raise TemporalEvidenceError("exact volume endpoints are unsupported")

    def as_mapping(self) -> dict[str, Any]:
        return {
            "source_label": self.source_label,
            "exact_window": self.exact_window,
        }


@dataclass(frozen=True)
class AssetAgeEvidence:
    status: AssetAgeStatus
    amount: None = None
    unit: None = None
    reference_semantics: None = None
    source_field: None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if self.status is not AssetAgeStatus.UNAVAILABLE:
            raise TemporalEvidenceError("asset age must remain UNAVAILABLE")
        for name, value in (
            ("asset_age.amount", self.amount),
            ("asset_age.unit", self.unit),
            ("asset_age.reference_semantics", self.reference_semantics),
            ("asset_age.source_field", self.source_field),
        ):
            if value is not None:
                raise TemporalEvidenceError(f"{name} must be null when unavailable")
        _canonical_text(self.reason, "asset_age.reason")

    def as_mapping(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "amount": self.amount,
            "unit": self.unit,
            "reference_semantics": self.reference_semantics,
            "source_field": self.source_field,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class MarketDataTemporalEvidence:
    contract_version: str
    source_id: str
    source_event_id: None
    token_identity: str
    chain_id: str
    market_subject_id: str
    occurrence_id: str
    source_observed_at: None
    received_at: str
    source_freshness: SourceFreshnessEvidence
    receipt_recency: ReceiptRecency
    volume_window: VolumeWindowEvidence
    asset_age: AssetAgeEvidence
    pair_created_at_source_value: str | None
    raw_payload_digest: str

    def __post_init__(self) -> None:
        if self.contract_version != CONTRACT_VERSION:
            raise TemporalEvidenceError("unsupported temporal-evidence version")
        _canonical_text(self.source_id, "source_id")
        if self.source_event_id is not None:
            raise TemporalEvidenceError("source_event_id is unavailable")
        _canonical_text(self.token_identity, "token_identity")
        _canonical_text(self.chain_id, "chain_id")
        _canonical_text(self.market_subject_id, "market_subject_id")
        _digest(self.occurrence_id, "occurrence_id")
        if self.source_observed_at is not None:
            raise TemporalEvidenceError("source_observed_at must remain null")
        _timestamp(self.received_at, "received_at")
        if not isinstance(self.source_freshness, SourceFreshnessEvidence):
            raise TemporalEvidenceError("source_freshness is invalid")
        if not isinstance(self.receipt_recency, ReceiptRecency):
            raise TemporalEvidenceError("receipt_recency is invalid")
        if not isinstance(self.volume_window, VolumeWindowEvidence):
            raise TemporalEvidenceError("volume_window is invalid")
        if not isinstance(self.asset_age, AssetAgeEvidence):
            raise TemporalEvidenceError("asset_age is invalid")
        if self.pair_created_at_source_value is not None:
            _canonical_text(
                self.pair_created_at_source_value,
                "pair_created_at_source_value",
            )
        _digest(self.raw_payload_digest, "raw_payload_digest")

    def as_mapping(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "source_id": self.source_id,
            "source_event_id": self.source_event_id,
            "token_identity": self.token_identity,
            "chain_id": self.chain_id,
            "market_subject_id": self.market_subject_id,
            "occurrence_id": self.occurrence_id,
            "source_observed_at": self.source_observed_at,
            "received_at": self.received_at,
            "source_freshness": self.source_freshness.as_mapping(),
            "receipt_recency": self.receipt_recency.as_mapping(),
            "volume_window": self.volume_window.as_mapping(),
            "asset_age": self.asset_age.as_mapping(),
            "pair_created_at_source_value": self.pair_created_at_source_value,
            "raw_payload_digest": self.raw_payload_digest,
            "p08_acceptance": P08_ACCEPTANCE,
        }


@dataclass(frozen=True)
class MarketDataTemporalEvidenceReport:
    source_id: str
    token_identity: str
    chain_id: str
    raw_payload_digest: str
    records: tuple[MarketDataTemporalEvidence, ...]
    p08_acceptance: str = P08_ACCEPTANCE

    def __post_init__(self) -> None:
        _canonical_text(self.source_id, "source_id")
        _canonical_text(self.token_identity, "token_identity")
        _canonical_text(self.chain_id, "chain_id")
        _digest(self.raw_payload_digest, "raw_payload_digest")
        if self.p08_acceptance != P08_ACCEPTANCE:
            raise TemporalEvidenceError("P08 acceptance must remain NOT_ATTEMPTED")
        if not isinstance(self.records, tuple) or not all(
            isinstance(record, MarketDataTemporalEvidence) for record in self.records
        ):
            raise TemporalEvidenceError("records must be an immutable evidence tuple")

    @property
    def empty(self) -> bool:
        return not self.records

    def as_mapping(self) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "source_id": self.source_id,
            "token_identity": self.token_identity,
            "chain_id": self.chain_id,
            "raw_payload_digest": self.raw_payload_digest,
            "p08_acceptance": self.p08_acceptance,
            "records": [record.as_mapping() for record in self.records],
        }


def canonical_json(value: Any) -> str:
    return json.dumps(
        _wire(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def temporal_evidence_digest(
    evidence: MarketDataTemporalEvidence | MarketDataTemporalEvidenceReport,
) -> str:
    if isinstance(evidence, MarketDataTemporalEvidence):
        material = evidence.as_mapping()
    elif isinstance(evidence, MarketDataTemporalEvidenceReport):
        material = evidence.as_mapping()
    else:
        raise TemporalEvidenceError("unsupported evidence value")
    return hashlib.sha256(canonical_bytes(material)).hexdigest()


def convert_inspection_report(
    report: Mapping[str, Any],
    *,
    evaluation_time: datetime | str,
) -> MarketDataTemporalEvidenceReport:
    """Convert one current DexScreener inspection report without I/O."""

    if not isinstance(report, Mapping):
        raise TemporalEvidenceError("inspection report must be a mapping")
    _require_keys(
        report,
        {
            "tool_version",
            "source",
            "request",
            "receipt",
            "payload",
            "evidence",
        },
        "report",
    )
    if set(report) - {
        "tool_version",
        "source",
        "request",
        "receipt",
        "payload",
        "evidence",
        "error",
    }:
        raise TemporalEvidenceError("unknown report field")
    if report.get("error") is not None:
        raise TemporalEvidenceError("error reports cannot produce temporal evidence")
    if report["tool_version"] != INSPECTOR_TOOL_VERSION:
        raise TemporalEvidenceError("unsupported inspector version")
    if report["source"] != INSPECTOR_SOURCE:
        raise TemporalEvidenceError("unsupported inspector source")

    request = _mapping(report["request"], "request")
    receipt = _mapping(report["receipt"], "receipt")
    payload = _mapping(report["payload"], "payload")
    evidence = _mapping(report["evidence"], "evidence")
    _require_keys(
        request,
        {
            "endpoint",
            "chain_id",
            "token_address",
            "attempts",
            "retry_count",
            "attempt_log",
        },
        "request",
    )
    _require_keys(
        receipt,
        {"received_at", "http_status", "response_bytes"},
        "receipt",
    )
    _require_keys(
        payload,
        {"raw_payload_sha256", "pair_count", "pairs"},
        "payload",
    )
    _require_keys(
        evidence,
        {"p08_acceptance", "p08_observed_at", "asset_age", "unavailable_fields"},
        "evidence",
    )

    source_id = _canonical_text(report["source"], "source")
    chain_id = _canonical_text(request["chain_id"], "request.chain_id")
    token_identity = _canonical_text(request["token_address"], "request.token_address")
    received_at = _timestamp(receipt["received_at"], "receipt.received_at")
    reference_time = _timestamp(evaluation_time, "evaluation_time")
    received_dt = _parse_timestamp(received_at, "receipt.received_at")
    reference_dt = _parse_timestamp(reference_time, "evaluation_time")
    if reference_dt < received_dt:
        raise TemporalEvidenceError("evaluation time precedes receipt time")

    raw_payload_digest = _digest(
        payload["raw_payload_sha256"],
        "payload.raw_payload_sha256",
    )
    pairs = payload["pairs"]
    if not isinstance(pairs, (list, tuple)):
        raise TemporalEvidenceError("payload.pairs must be a sequence")
    if len(pairs) > MAX_SEQUENCE_ELEMENTS:
        raise TemporalEvidenceError("payload.pairs exceeds the sequence limit")
    if payload["pair_count"] != len(pairs):
        raise TemporalEvidenceError("payload.pair_count contradicts payload.pairs")
    if evidence["p08_acceptance"] != P08_ACCEPTANCE:
        raise TemporalEvidenceError("P08 acceptance was attempted")
    if evidence["p08_observed_at"] is not None:
        raise TemporalEvidenceError("source observation time is contradictory")
    _validate_asset_age_evidence(evidence["asset_age"])
    freshness_reason = _unavailable_reason(
        evidence["unavailable_fields"],
        "observed_at",
        "NO_DOCUMENTED_MARKET_FIELD_OBSERVATION_TIMESTAMP",
    )
    asset_age_reason = _unavailable_reason(
        evidence["unavailable_fields"],
        "asset_age",
        "NO_DOCUMENTED_TOKEN_ORIGIN_SEMANTICS",
    )
    _unavailable_reason(
        evidence["unavailable_fields"],
        "volume.measurement_window",
        "NO_EXACT_UTC_WINDOW_ENDPOINTS",
    )
    asset_age = AssetAgeEvidence(
        status=AssetAgeStatus.UNAVAILABLE,
        reason=asset_age_reason,
    )
    receipt_age = _decimal_seconds(reference_dt - received_dt)

    records: list[MarketDataTemporalEvidence] = []
    for index, pair_value in enumerate(pairs):
        pair = _mapping(pair_value, f"payload.pairs[{index}]")
        for field_name in ("pairAddress", "chainId"):
            if field_name not in pair:
                raise TemporalEvidenceError(
                    f"payload.pairs[{index}] missing {field_name}"
                )
        pair_chain_id = _canonical_text(
            pair["chainId"],
            f"payload.pairs[{index}].chainId",
        )
        if pair_chain_id != chain_id:
            raise TemporalEvidenceError("pair chain contradicts request chain")
        pair_address = _canonical_text(
            pair["pairAddress"],
            f"payload.pairs[{index}].pairAddress",
        )
        for field_name in ("baseToken", "quoteToken", "liquidity", "txns"):
            _optional_mapping(
                pair,
                field_name,
                f"payload.pairs[{index}].{field_name}",
            )
        price_usd = pair.get("priceUsd")
        if price_usd is not None:
            _finite_numeric_text(
                price_usd,
                f"payload.pairs[{index}].priceUsd",
            )
        volume = _optional_mapping(
            pair,
            "volume",
            f"payload.pairs[{index}].volume",
        )
        source_label = None
        if volume is not None and "h24" in volume and volume["h24"] is not None:
            _finite_numeric_text(
                volume["h24"],
                f"payload.pairs[{index}].volume.h24",
            )
            source_label = "h24"
        pair_created = pair.get("pairCreatedAt")
        if pair_created is not None:
            pair_created = _finite_numeric_text(
                pair_created,
                f"payload.pairs[{index}].pairCreatedAt",
            )
        market_subject_id = _canonical_text(
            f"{chain_id}:{pair_address}",
            f"payload.pairs[{index}].market_subject_id",
        )
        occurrence_id = _occurrence_id(
            source_id=source_id,
            raw_payload_digest=raw_payload_digest,
            report_index=index,
            market_subject_id=market_subject_id,
            pair=pair,
        )
        records.append(
            MarketDataTemporalEvidence(
                contract_version=CONTRACT_VERSION,
                source_id=source_id,
                source_event_id=None,
                token_identity=token_identity,
                chain_id=chain_id,
                market_subject_id=market_subject_id,
                occurrence_id=occurrence_id,
                source_observed_at=None,
                received_at=received_at,
                source_freshness=SourceFreshnessEvidence(
                    status=SourceFreshnessStatus.UNKNOWN,
                    reason=freshness_reason,
                ),
                receipt_recency=ReceiptRecency(
                    reference_time=reference_time,
                    age_seconds=receipt_age,
                ),
                volume_window=VolumeWindowEvidence(source_label=source_label),
                asset_age=asset_age,
                pair_created_at_source_value=pair_created,
                raw_payload_digest=raw_payload_digest,
            )
        )

    return MarketDataTemporalEvidenceReport(
        source_id=source_id,
        token_identity=token_identity,
        chain_id=chain_id,
        raw_payload_digest=raw_payload_digest,
        records=tuple(records),
    )


def _require_keys(
    value: Mapping[str, Any],
    required: set[str],
    path: str,
) -> None:
    if set(value) - required:
        raise TemporalEvidenceError(f"{path} contains unknown fields")
    missing = required - set(value)
    if missing:
        raise TemporalEvidenceError(f"{path} missing required fields")


def _validate_asset_age_evidence(value: Any) -> None:
    asset_age = _mapping(value, "evidence.asset_age")
    _require_keys(asset_age, {"status", "value", "reason"}, "evidence.asset_age")
    if asset_age["status"] != "UNAVAILABLE" or asset_age["value"] is not None:
        raise TemporalEvidenceError("asset age evidence is contradictory")
    _canonical_text(asset_age["reason"], "evidence.asset_age.reason")


def _unavailable_reason(
    value: Any,
    field: str,
    expected_reason: str,
) -> str:
    if not isinstance(value, (list, tuple)):
        raise TemporalEvidenceError("evidence.unavailable_fields must be a sequence")
    for item in value:
        if not isinstance(item, Mapping):
            raise TemporalEvidenceError("unavailable evidence must be mappings")
        if item.get("field") == field:
            reason = _canonical_text(item.get("reason"), f"{field}.reason")
            if reason != expected_reason:
                raise TemporalEvidenceError(f"contradictory unavailable reason for {field}")
            return reason
    raise TemporalEvidenceError(f"missing unavailable evidence for {field}")


def _optional_mapping(
    pair: Mapping[str, Any],
    field: str,
    path: str,
) -> Mapping[str, Any] | None:
    value = pair.get(field)
    if value is None:
        return None
    return _mapping(value, path)


def _finite_numeric_text(value: Any, path: str) -> str:
    normalized = _canonical_text(value, path)
    try:
        parsed = Decimal(normalized)
    except InvalidOperation as exc:
        raise TemporalEvidenceError(f"{path} must be numeric text") from exc
    if not parsed.is_finite():
        raise TemporalEvidenceError(f"{path} must be finite numeric text")
    return normalized


def _occurrence_id(
    *,
    source_id: str,
    raw_payload_digest: str,
    report_index: int,
    market_subject_id: str,
    pair: Mapping[str, Any],
) -> str:
    source_pair = {
        key: value for key, value in pair.items() if key != "inspection"
    }
    material = {
        "source_id": source_id,
        "raw_payload_digest": raw_payload_digest,
        "report_index": report_index,
        "market_subject_id": market_subject_id,
        "pair": source_pair,
    }
    return hashlib.sha256(canonical_bytes(material)).hexdigest()


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TemporalEvidenceError(f"{path} must be a mapping")
    if not all(isinstance(key, str) for key in value):
        raise TemporalEvidenceError(f"{path} keys must be strings")
    return value


def _canonical_text(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise TemporalEvidenceError(f"{path} must be text")
    normalized = unicodedata.normalize("NFC", value)
    if normalized != value or normalized.strip() != normalized or not normalized:
        raise TemporalEvidenceError(f"{path} is not canonical text")
    if len(normalized) > MAX_TEXT_SCALARS:
        raise TemporalEvidenceError(f"{path} exceeds text scalar limit")
    try:
        encoded = normalized.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise TemporalEvidenceError(f"{path} contains an invalid scalar") from exc
    if len(encoded) > MAX_TEXT_BYTES:
        raise TemporalEvidenceError(f"{path} exceeds text byte limit")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in normalized):
        raise TemporalEvidenceError(f"{path} contains an unpaired surrogate")
    return normalized


def _timestamp(value: Any, path: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise TemporalEvidenceError(f"{path} must be timezone-aware")
        value = value.astimezone(timezone.utc).isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z")
    if not isinstance(value, str):
        raise TemporalEvidenceError(f"{path} must be a UTC timestamp")
    parsed = _parse_timestamp(value, path)
    canonical = parsed.astimezone(timezone.utc).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")
    if value != canonical:
        raise TemporalEvidenceError(f"{path} is not canonical")
    return canonical


def _parse_timestamp(value: str, path: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TemporalEvidenceError(f"{path} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TemporalEvidenceError(f"{path} must be timezone-aware")
    return parsed


def _decimal_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _DECIMAL_RE.fullmatch(value):
        raise TemporalEvidenceError(f"{path} must be canonical decimal text")
    if value == "-0" or (value.endswith("0") and "." in value):
        raise TemporalEvidenceError(f"{path} is not normalized")
    if value.startswith("-0") and len(value) > 2 and value[2] != ".":
        raise TemporalEvidenceError(f"{path} is not normalized")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise TemporalEvidenceError(f"{path} is invalid") from exc
    if not parsed.is_finite():
        raise TemporalEvidenceError(f"{path} must be finite")
    return value


def _decimal_seconds(delta: Any) -> str:
    total_microseconds = delta.days * 86_400_000_000 + delta.seconds * 1_000_000
    total_microseconds += delta.microseconds
    if total_microseconds < 0:
        raise TemporalEvidenceError("receipt recency cannot be negative")
    seconds, microseconds = divmod(total_microseconds, 1_000_000)
    if microseconds == 0:
        return str(seconds)
    return f"{seconds}.{microseconds:06d}".rstrip("0")


def _digest(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise TemporalEvidenceError(f"{path} must be lowercase SHA-256")
    return value


def _wire(value: Any, *, depth: int = 0) -> Any:
    if depth > MAX_MAPPING_DEPTH:
        raise TemporalEvidenceError("canonical mapping depth exceeded")
    if value is None or isinstance(value, (bool, str, int)):
        if isinstance(value, int) and isinstance(value, bool):
            return value
        return value
    if isinstance(value, float):
        raise TemporalEvidenceError("binary floats are forbidden")
    if isinstance(value, Mapping):
        if len(value) > MAX_MAPPING_MEMBERS:
            raise TemporalEvidenceError("canonical mapping member limit exceeded")
        if not all(isinstance(key, str) for key in value):
            raise TemporalEvidenceError("canonical mapping keys must be strings")
        result = {
            key: _wire(value[key], depth=depth + 1)
            for key in sorted(value)
        }
        if (
            len(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            )
            > MAX_MAPPING_BYTES
        ):
            raise TemporalEvidenceError("canonical mapping byte limit exceeded")
        return result
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_SEQUENCE_ELEMENTS:
            raise TemporalEvidenceError("canonical sequence limit exceeded")
        return [_wire(item, depth=depth + 1) for item in value]
    raise TemporalEvidenceError("opaque canonical value is forbidden")


__all__ = [
    "AssetAgeEvidence",
    "AssetAgeStatus",
    "CONTRACT_VERSION",
    "MarketDataTemporalEvidence",
    "MarketDataTemporalEvidenceReport",
    "P08_ACCEPTANCE",
    "ReceiptRecency",
    "SourceFreshnessEvidence",
    "SourceFreshnessStatus",
    "TemporalEvidenceError",
    "VolumeWindowEvidence",
    "canonical_bytes",
    "canonical_json",
    "convert_inspection_report",
    "temporal_evidence_digest",
]