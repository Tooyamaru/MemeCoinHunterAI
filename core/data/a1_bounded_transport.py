"""Injected bounded A1 transport; no network implementation or default opener.

The injected opener must honor the immutable no-redirect/no-retry request.
Returned redirect/final-location evidence is checked independently. Transport
owns byte/deadline/accounting contracts, never source or trading decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
from urllib.parse import urlsplit

from core.data.a1_cpmm_sources import A1SourceError, RpcEnvelope, _utc

TRANSPORT_VERSION = "a1-injected-bounded-transport-v1"
_READ_CHUNK = 65536
_METHODS = {"getSlot", "getBlock", "getBlockTime", "getMultipleAccounts", "getGenesisHash", "getAccountInfo"}


def _require(ok, reason):
    if not ok:
        raise A1SourceError(reason)


@dataclass(frozen=True)
class A1HttpRequest:
    scope: str
    endpoint: str
    method: str
    body: bytes
    timeout: timedelta
    max_response_bytes: int
    follow_redirects: bool = field(default=False, init=False)
    retries: int = field(default=0, init=False)
    contract_version: str = field(default=TRANSPORT_VERSION, init=False)

    def __post_init__(self):
        _require(self.scope in ("solana", "valuation", "diagnostic", "safety"), "TRANSPORT_SCOPE")
        _require(type(self.endpoint) is str and len(self.endpoint) <= 4096, "TRANSPORT_ENDPOINT")
        try:
            parts = urlsplit(self.endpoint)
            port = parts.port
        except ValueError:
            raise A1SourceError("TRANSPORT_ENDPOINT") from None
        _require(parts.scheme == "https" and parts.hostname and not parts.username
                 and not parts.password and not parts.fragment and port in (None, 443)
                 and not any(ord(c) <= 32 or ord(c) >= 127 for c in self.endpoint), "TRANSPORT_ENDPOINT")
        _require(self.method in ("GET", "POST") and type(self.body) is bytes
                 and len(self.body) <= 65536 and (self.method != "GET" or not self.body), "TRANSPORT_REQUEST")
        maximum_timeout = timedelta(seconds=10 if self.scope == "solana" else 30)
        _require(type(self.timeout) is timedelta and timedelta(0) < self.timeout <= maximum_timeout,
                 "TRANSPORT_TIMEOUT_CONFIG")
        _require(type(self.max_response_bytes) is int and 1 <= self.max_response_bytes <= 1048576,
                 "TRANSPORT_BYTE_CONFIG")
        _require(self.follow_redirects is False and type(self.retries) is int and self.retries == 0
                 and self.contract_version == TRANSPORT_VERSION, "TRANSPORT_CONTRACT")

    @property
    def headers(self):
        return (("Accept", "application/json"),) + ((("Content-Type", "application/json"),) if self.method == "POST" else ())

    @property
    def request_identity(self):
        packet = [TRANSPORT_VERSION, self.scope, self.endpoint, self.method,
                  hashlib.sha256(self.body).hexdigest(), self.timeout // timedelta(microseconds=1),
                  self.max_response_bytes, False, 0]
        return hashlib.sha256(json.dumps(packet, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class A1HttpReceipt:
    request: A1HttpRequest
    started_at: datetime
    received_at: datetime
    body: bytes = field(repr=False)
    status: int = 200

    @property
    def body_digest(self):
        return hashlib.sha256(self.body).hexdigest()


class A1BoundedTransport:
    def __init__(self, *, rpc_endpoint, opener, clock, ledger):
        _require(callable(opener) and callable(clock) and callable(getattr(ledger, "reserve_attempt", None))
                 and callable(getattr(ledger, "observe_receipt", None))
                 and callable(getattr(ledger, "check_time", None))
                 and callable(getattr(ledger, "abort", None)), "INJECTED_TRANSPORT_REQUIRED")
        A1HttpRequest("solana", rpc_endpoint, "POST", b"{}", timedelta(seconds=10), 8192)
        self.rpc_endpoint, self.opener, self.clock, self.ledger = rpc_endpoint, opener, clock, ledger

    def http(self, request):
        _require(type(request) is A1HttpRequest, "CANONICAL_TRANSPORT_REQUEST")
        request.__post_init__()
        start = _utc(self.clock())
        try:
            self.ledger.reserve_attempt(kind=request.scope, host=urlsplit(request.endpoint).hostname,
                                        response_cap=request.max_response_bytes, timeout=request.timeout, now=start)
        except A1SourceError:
            self.ledger.abort()
            raise
        response = None
        total = 0
        accounted = False
        try:
            response = self.opener(request, timeout=request.timeout.total_seconds())
            self.ledger.check_time(_utc(self.clock()))
            status = getattr(response, "status", None)
            _require(type(status) is int and status == 200, "TRANSPORT_HTTP_ERROR")
            location = getattr(response, "final_url", None)
            geturl = getattr(response, "geturl", None)
            if callable(geturl):
                location = geturl()
            _require(location is None or location == request.endpoint, "TRANSPORT_REDIRECT_REFUSED")
            chunks = []
            while True:
                now = self.ledger.check_time(_utc(self.clock()))
                _require(start <= now and now-start <= request.timeout, "TRANSPORT_TIMEOUT")
                chunk = response.read(min(_READ_CHUNK, request.max_response_bytes-total+1))
                _require(type(chunk) is bytes, "TRANSPORT_BODY_TYPE")
                total += len(chunk)
                _require(total <= request.max_response_bytes, "TRANSPORT_RESPONSE_TOO_LARGE")
                now = self.ledger.check_time(_utc(self.clock()))
                _require(start <= now and now-start <= request.timeout, "TRANSPORT_TIMEOUT")
                if not chunk:
                    break
                chunks.append(chunk)
            _require(total > 0, "TRANSPORT_EMPTY_BODY")
            received = self.ledger.check_time(_utc(self.clock()))
            _require(start <= received and received-start <= request.timeout, "TRANSPORT_TIMEOUT")
            self.ledger.observe_receipt(now=received, bodylen=total)
            accounted = True
            return A1HttpReceipt(request, start, received, b"".join(chunks), status)
        except A1SourceError:
            raise
        except TimeoutError:
            raise A1SourceError("TRANSPORT_TIMEOUT") from None
        except Exception:
            raise A1SourceError("TRANSPORT_UNAVAILABLE") from None
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
            if not accounted:
                # Failed attempts remain charged; record bounded observed bytes.
                # Invalid/backward clocks or aggregate limits leave a terminal
                # pending attempt; they can never permit another invocation.
                try:
                    self.ledger.observe_receipt(now=_utc(self.clock()), bodylen=total)
                except Exception:
                    pass
                self.ledger.abort()

    def rpc(self, method, params, *, request_id, timeout=timedelta(seconds=10), max_bytes=8192):
        _require(type(method) is str and method in _METHODS and type(params) is list and type(request_id) is int
                 and 0 < request_id < 2**31, "RPC_REQUEST_CONFIG")
        try:
            params_json = json.dumps(params, sort_keys=True, separators=(",", ":"), allow_nan=False)
            body = json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
                              sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        except (ValueError, TypeError, RecursionError):
            raise A1SourceError("RPC_REQUEST_CONFIG") from None
        receipt = self.http(A1HttpRequest("solana", self.rpc_endpoint, "POST", body, timeout, max_bytes))
        envelope = RpcEnvelope(method, params_json, request_id, receipt.started_at, receipt.received_at, receipt.body)
        try:
            envelope.read(method, params, receipt.received_at, max_bytes)
        except A1SourceError:
            self.ledger.abort()
            raise
        return envelope
