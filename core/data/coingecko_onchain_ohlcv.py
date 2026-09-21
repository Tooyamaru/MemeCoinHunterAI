"""P04-LME-01: bounded, offline CoinGecko OHLCV admission.

No network client, environment lookup, clock, retry, or application wiring.
Callers supply a source envelope and an already-admitted P02-T06 snapshot.
Fresh local P02 processors make replay deterministic and failures atomic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, DecimalException
from enum import StrEnum
import hashlib
import json
import re
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlencode

from core.data.contracts import FreshnessPolicy
from core.data.market_intelligence import (
    AcceptedMarketIntelligenceObservation,
    MarketIntelligenceCategory,
    MarketIntelligenceObservation,
    MarketIntelligenceProcessor,
    MarketIntelligenceStateReference,
)
from core.data.market_observations import (
    MarketObservationCandidate,
    MarketObservationKind,
    MarketObservationProcessor,
    P02T07PredecessorContext,
)
from core.data.market_state import MarketStateMaterializer


PROVIDER_ID = "coingecko-onchain-demo"
ADAPTER_VERSION = "p04-lme-01-v1"
ENDPOINT_VERSION = "coingecko-demo-v3-pool-ohlcv-v1"
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


class OhlcvOutcome(StrEnum):
    PRODUCED = "PRODUCED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    TEMPORAL_INVALID = "TEMPORAL_INVALID"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    CONTRADICTORY_EVIDENCE = "CONTRADICTORY_EVIDENCE"
    UPSTREAM_ADMISSION_REJECTED = "UPSTREAM_ADMISSION_REJECTED"


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return value.astimezone(timezone.utc)


def _address(value: str) -> None:
    # Solana identities are case-sensitive base58-encoded 32-byte public keys.
    if not isinstance(value, str) or not 32 <= len(value) <= 44:
        raise ValueError("invalid Solana address")
    number = 0
    for char in value:
        if char not in _BASE58:
            raise ValueError("invalid Solana address")
        number = number * 58 + _BASE58.index(char)
    leading_zeroes = len(value) - len(value.lstrip("1"))
    if leading_zeroes + (number.bit_length() + 7) // 8 != 32:
        raise ValueError("invalid Solana address")


@dataclass(frozen=True)
class OhlcvRequest:
    chain_id: str
    token_mint: str
    pool_address: str
    base_mint: str
    quote_mint: str
    reference_time: datetime
    timeout: timedelta
    max_response_bytes: int

    def __post_init__(self) -> None:
        if self.chain_id != "solana":
            raise ValueError("only canonical solana network is supported")
        for value in (self.token_mint, self.pool_address, self.base_mint, self.quote_mint):
            _address(value)
        if self.base_mint == self.quote_mint or self.token_mint not in (
            self.base_mint, self.quote_mint,
        ):
            raise ValueError("candidate token and pool composition must agree")
        object.__setattr__(self, "reference_time", _utc(self.reference_time))
        if not isinstance(self.timeout, timedelta) or self.timeout <= timedelta(0):
            raise ValueError("positive explicit timeout required")
        if type(self.max_response_bytes) is not int or not 1 <= self.max_response_bytes <= 1048576:
            raise ValueError("response limit must be between 1 and 1048576 bytes")

    @property
    def cutoff(self) -> int:
        elapsed = self.reference_time - _EPOCH
        return (elapsed.days * 86400 + elapsed.seconds) // 60 * 60

    @property
    def parameters(self) -> tuple[tuple[str, str], ...]:
        return (
            ("aggregate", "1"), ("limit", "3"), ("currency", "usd"),
            ("token", self.token_mint), ("include_empty_intervals", "false"),
            ("before_timestamp", str(self.cutoff)),
        )

    @property
    def url(self) -> str:
        return (
            "https://api.coingecko.com/api/v3/onchain/networks/solana/pools/"
            f"{self.pool_address}/ohlcv/minute?{urlencode(self.parameters)}"
        )


@dataclass(frozen=True, repr=False)
class AuthenticatedOhlcvRequest:
    """Request preparation only; never executes HTTP or enters provenance."""

    request: OhlcvRequest
    headers: Mapping[str, str] = field(repr=False, compare=False)
    follow_redirects: bool = field(default=False, init=False)

    def __repr__(self) -> str:
        return "AuthenticatedOhlcvRequest(headers=<redacted>, follow_redirects=False)"


def prepare_authenticated_request(
    request: OhlcvRequest, *, api_key: str | None,
) -> AuthenticatedOhlcvRequest:
    """Caller supplies the environment secret; errors never echo its value."""
    if not isinstance(request, OhlcvRequest):
        raise ValueError("validated request required")
    if not isinstance(api_key, str) or not 1 <= len(api_key) <= 512 or any(
        ord(char) < 33 or ord(char) > 126 for char in api_key
    ):
        raise ValueError(OhlcvOutcome.AUTHENTICATION_FAILED.value)
    return AuthenticatedOhlcvRequest(
        request, MappingProxyType({"x-cg-demo-api-key": api_key}),
    )


@dataclass(frozen=True)
class OhlcvResponse:
    """Transport facts supplied by a trusted server-side caller, not a browser.

    HTTP is deliberately absent. A future bounded transport must enforce the
    request's size/time limits while reading, disable redirects, and report
    failures without retaining provider error text or credential headers.
    """

    request: OhlcvRequest
    started_at: datetime
    received_at: datetime
    body: bytes = field(repr=False)
    http_status: int | None = 200
    transport_failure: OhlcvOutcome | None = None


@dataclass(frozen=True)
class OhlcvProvenance:
    request: OhlcvRequest
    started_at: datetime
    received_at: datetime
    http_status: int | None
    response_digest: str | None
    provider_request_id: str | None = None
    returned_base: str | None = None
    returned_quote: str | None = None
    raw_timestamps: tuple[int, ...] = ()
    provider_id: str = PROVIDER_ID
    adapter_version: str = ADAPTER_VERSION
    endpoint_version: str = ENDPOINT_VERSION


@dataclass(frozen=True)
class OhlcvResult:
    outcome: OhlcvOutcome
    reason_codes: tuple[str, ...]
    retryable: bool
    provenance: OhlcvProvenance | None
    observations: tuple[AcceptedMarketIntelligenceObservation, ...] = ()


class _Rejected(ValueError):
    def __init__(self, outcome: OhlcvOutcome, reason: str):
        self.outcome = outcome
        self.reason = reason


def _reject(outcome: OhlcvOutcome, reason: str) -> None:
    raise _Rejected(outcome, reason)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _number(text: str) -> Decimal:
    # Bound numeric complexity before formatting or downstream arithmetic.
    if len(text) > 160:
        raise ValueError("numeric bounds")
    value = Decimal(text)
    if not value.is_finite() or len(value.as_tuple().digits) > 128 or abs(value.as_tuple().exponent) > 100:
        raise ValueError("numeric bounds")
    return value


def _parse(body: bytes, request: OhlcvRequest) -> tuple[str | None, str, str, tuple, tuple]:
    data = json.loads(
        body.decode("utf-8"), parse_int=_number, parse_float=_number,
        parse_constant=_number, object_pairs_hook=_unique_object,
    )
    if not isinstance(data, dict) or set(data) != {"data", "meta"}:
        raise ValueError("unexpected root")
    resource = data["data"]
    if not isinstance(resource, dict) or set(resource) - {"id", "type", "attributes"}:
        raise ValueError("unexpected resource")
    if resource["type"] != "ohlcv_request_response":
        raise ValueError("unexpected resource type")
    request_id = resource.get("id")
    if request_id is not None and (
        not isinstance(request_id, str) or re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", request_id) is None
    ):
        raise ValueError("invalid request ID")
    meta = data["meta"]
    if not isinstance(meta, dict) or set(meta) != {"base", "quote"}:
        raise ValueError("invalid composition")
    base, quote = meta["base"]["address"], meta["quote"]["address"]
    _address(base)
    _address(quote)
    if (base, quote) != (request.base_mint, request.quote_mint):
        _reject(OhlcvOutcome.IDENTITY_MISMATCH, "POOL_COMPOSITION_MISMATCH")
    attributes = resource["attributes"]
    if not isinstance(attributes, dict) or set(attributes) != {"ohlcv_list"}:
        raise ValueError("unexpected attributes")
    rows = attributes["ohlcv_list"]
    if not isinstance(rows, list) or len(rows) > 3:
        raise ValueError("invalid candle list")
    if len(rows) < 3:
        _reject(OhlcvOutcome.INSUFFICIENT_HISTORY, "THREE_CANDLES_REQUIRED")
    candles = []
    for row in rows:
        if not isinstance(row, list) or len(row) != 6 or any(type(v) is not Decimal for v in row):
            raise ValueError("invalid candle")
        stamp, opening, high, low, close, volume = row
        if stamp != stamp.to_integral_value() or not 0 <= stamp < request.cutoff:
            _reject(OhlcvOutcome.TEMPORAL_INVALID, "INVALID_CANDLE_TIMESTAMP")
        timestamp = int(stamp)
        if timestamp % 60:
            _reject(OhlcvOutcome.TEMPORAL_INVALID, "CANDLE_NOT_MINUTE_ALIGNED")
        if not (0 < low <= opening <= high and low <= close <= high and volume >= 0):
            raise ValueError("invalid OHLCV values")
        candles.append((timestamp, close))
    stamps = tuple(item[0] for item in candles)
    if len(set(stamps)) != 3:
        outcome = OhlcvOutcome.CONTRADICTORY_EVIDENCE if len(set(map(tuple, rows))) != len(set(stamps)) else OhlcvOutcome.TEMPORAL_INVALID
        _reject(outcome, "DUPLICATE_CANDLE_TIMESTAMP")
    if stamps not in (tuple(sorted(stamps)), tuple(sorted(stamps, reverse=True))):
        _reject(OhlcvOutcome.TEMPORAL_INVALID, "NON_MONOTONIC_CANDLES")
    candles.sort()
    if any(b[0] - a[0] != 60 for a, b in zip(candles, candles[1:])):
        _reject(OhlcvOutcome.INSUFFICIENT_HISTORY, "NON_CONTIGUOUS_CANDLES")
    return request_id, base, quote, stamps, tuple(candles)


def map_pool_ohlcv(
    *, request: OhlcvRequest, response: OhlcvResponse,
    predecessor: P02T07PredecessorContext, freshness_policy: FreshnessPolicy,
    evaluation_time: datetime | None = None,
) -> OhlcvResult:
    """Admit exactly three closed candles through T07 -> T08 -> T09.

    No caller-owned processor is mutated and no partial history escapes a
    failure. Freshness is caller-owned and must have a finite explicit limit.
    """
    provenance = None
    try:
        if not isinstance(request, OhlcvRequest) or not isinstance(response, OhlcvResponse):
            raise ValueError("request and response required")
        if response.request != request:
            _reject(OhlcvOutcome.IDENTITY_MISMATCH, "REQUEST_BINDING_MISMATCH")
        evaluation = _utc(evaluation_time or request.reference_time)
        try:
            start, received = _utc(response.started_at), _utc(response.received_at)
        except ValueError:
            _reject(OhlcvOutcome.TEMPORAL_INVALID, "INVALID_RECEIPT_TIMESTAMP")
        if not start <= received <= evaluation:
            _reject(OhlcvOutcome.TEMPORAL_INVALID, "INVALID_RECEIPT_TIMELINE")
        if type(response.body) is not bytes:
            raise ValueError("bytes required")
        provenance = OhlcvProvenance(request, start, received, response.http_status, None)
        if len(response.body) > request.max_response_bytes:
            _reject(OhlcvOutcome.RESPONSE_TOO_LARGE, "RESPONSE_SIZE_LIMIT")
        if response.transport_failure is not None:
            if type(response.transport_failure) is not OhlcvOutcome or response.transport_failure not in {
                OhlcvOutcome.TIMEOUT, OhlcvOutcome.SOURCE_UNAVAILABLE,
                OhlcvOutcome.AUTHENTICATION_FAILED, OhlcvOutcome.RESPONSE_TOO_LARGE,
            }:
                raise ValueError("invalid transport failure")
            _reject(response.transport_failure, response.transport_failure.value)
        if received - start > request.timeout:
            _reject(OhlcvOutcome.TIMEOUT, "REQUEST_TIMEOUT")
        if type(response.http_status) is not int or not 100 <= response.http_status <= 599:
            raise ValueError("invalid HTTP status")
        if response.http_status in (401, 403):
            _reject(OhlcvOutcome.AUTHENTICATION_FAILED, "HTTP_AUTHENTICATION_FAILED")
        if response.http_status == 429:
            _reject(OhlcvOutcome.RATE_LIMITED, "HTTP_RATE_LIMITED")
        if not 200 <= response.http_status < 300:
            _reject(OhlcvOutcome.SOURCE_UNAVAILABLE, "HTTP_SOURCE_UNAVAILABLE")
        digest = hashlib.sha256(response.body).hexdigest()
        provenance = OhlcvProvenance(request, start, received, response.http_status, digest)
        request_id, base, quote, stamps, candles = _parse(response.body, request)
        provenance = OhlcvProvenance(
            request, start, received, response.http_status, digest,
            request_id, base, quote, stamps,
        )
        if not isinstance(predecessor, P02T07PredecessorContext):
            _reject(OhlcvOutcome.UPSTREAM_ADMISSION_REJECTED, "P02_PREDECESSOR_REQUIRED")
        if not isinstance(freshness_policy, FreshnessPolicy) or freshness_policy.stale_after is None:
            _reject(OhlcvOutcome.UPSTREAM_ADMISSION_REJECTED, "EXPLICIT_FRESHNESS_REQUIRED")
        admission = MarketObservationProcessor(predecessor=predecessor, freshness_policy=freshness_policy)
        materializer = MarketStateMaterializer()
        intelligence = MarketIntelligenceProcessor()
        observations = []
        source_metadata = {
            "adapter_version": ADAPTER_VERSION, "endpoint_version": ENDPOINT_VERSION,
            "response_digest": digest, "provider_request_id": request_id,
            "request_started_at": start.isoformat(), "pool_address": request.pool_address,
            "base_mint": base, "quote_mint": quote,
            "request_parameters": dict(request.parameters),
        }
        for index, (stamp, close) in enumerate(candles):
            observed = _EPOCH + timedelta(seconds=stamp)
            if observed + timedelta(minutes=1) > received:
                _reject(OhlcvOutcome.TEMPORAL_INVALID, "CANDLE_NOT_CLOSED_AT_RECEIPT")
            source_event_id = f"{PROVIDER_ID}:solana:{request.pool_address}:{request.token_mint}:60s:{stamp}"
            candidate = MarketObservationCandidate(
                source_id=PROVIDER_ID, chain_id=request.chain_id,
                token_identity=request.token_mint, market_subject_id=request.pool_address,
                observation_kind=MarketObservationKind.OBSERVED if index == 0 else MarketObservationKind.UPDATED,
                observation_time=observed, received_time=received,
                source_event_id=source_event_id, sequence=stamp,
                source_metadata=source_metadata,
                observation_metadata={"pool_address": request.pool_address, "interval": "60s"},
            )
            admitted = admission.process(
                candidate,
                processing_time=received,
                reference_time=evaluation,
            )
            if not admitted.accepted or admitted.evidence is None:
                _reject(OhlcvOutcome.UPSTREAM_ADMISSION_REJECTED, "P02_T07_" + admitted.outcome.value)
            state = materializer.process(admitted.evidence)
            if not state.accepted or state.entry is None:
                _reject(OhlcvOutcome.UPSTREAM_ADMISSION_REJECTED, "P02_T08_" + state.outcome.value)
            represented = intelligence.process(MarketIntelligenceObservation(
                source_id=PROVIDER_ID, chain_id=request.chain_id,
                token_identity=request.token_mint, market_subject_id=request.pool_address,
                intelligence_category=MarketIntelligenceCategory.PRICE,
                value=format(close, "f"), observation_time=observed,
                received_time=received, reference_time=evaluation,
                data_age=evaluation - observed,
                upstream=MarketIntelligenceStateReference(
                    state.entry, state.local_state_version, state.local_state_digest,
                ), source_event_id=source_event_id, sequence=stamp,
                ordering_status=admitted.evidence.ordering_status,
                source_metadata=source_metadata,
                observation_metadata={
                    "measurement": "price", "unit": "USD", "quote_asset": "USD",
                    "pool_address": request.pool_address, "interval": "60s", "response_digest": digest,
                },
            ))
            if not represented.accepted or represented.observation is None:
                _reject(OhlcvOutcome.UPSTREAM_ADMISSION_REJECTED, "P02_T09_" + represented.outcome.value)
            observations.append(represented.observation)
        return OhlcvResult(OhlcvOutcome.PRODUCED, (), False, provenance, tuple(observations))
    except _Rejected as error:
        return OhlcvResult(error.outcome, (error.reason,), error.outcome in {
            OhlcvOutcome.SOURCE_UNAVAILABLE, OhlcvOutcome.RATE_LIMITED, OhlcvOutcome.TIMEOUT,
        }, provenance)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError, DecimalException):
        return OhlcvResult(OhlcvOutcome.INVALID_RESPONSE, ("INVALID_RESPONSE",), False, provenance)
