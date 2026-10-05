"""Explicit A1 HTTP opener; offline conformance is not provider qualification.

No environment lookup, default wiring, retry, redirect, proxy or provider probe.
Credential-bearing routing/authentication stays outside canonical A1 evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import http.client
import json
import math
import re
import ssl
import time
from urllib.parse import parse_qsl, urlencode, urlsplit

from core.data.a1_bounded_transport import A1HttpRequest, _METHODS, validate_safety_params
from core.data.a1_cpmm_sources import A1SourceError
from core.data.coingecko_onchain_ohlcv import _address

CONTRACT_VERSION = "a1-explicit-http-adapter-v1"
_QUERY_NAMES = ("aggregate", "limit", "currency", "token", "include_empty_intervals", "before_timestamp")


class _Refused(ValueError):
    pass


def _require(ok, reason):
    if not ok:
        raise _Refused(reason)


def _object(pairs):
    result = dict(pairs)
    _require(len(result) == len(pairs), "ADAPTER_RPC_BODY")
    return result


def _rpc_body(request):
    try:
        value = json.loads(request.body, object_pairs_hook=_object)
        _require(type(value) is dict and set(value) == {"jsonrpc", "id", "method", "params"}
                 and value["jsonrpc"] == "2.0" and type(value["id"]) is int
                 and 0 < value["id"] < 2**31 and type(value["method"]) is str
                 and type(value["params"]) is list
                 and json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
                     == request.body, "ADAPTER_RPC_BODY")
        if request.scope == "safety":
            validate_safety_params(value["method"], value["params"])
        else:
            _require(value["method"] in _METHODS, "ADAPTER_RPC_READ_ONLY")
    except _Refused:
        raise
    except Exception:
        raise _Refused("ADAPTER_RPC_BODY") from None


def _url(value):
    _require(type(value) is str and 0 < len(value) <= 4096
             and all(32 < ord(c) < 127 for c in value), "ADAPTER_ENDPOINT")
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == "https" and parts.hostname and not parts.username
                 and not parts.password and not parts.fragment and parts.port in (None, 443))
    except ValueError:
        valid = False
    _require(valid, "ADAPTER_ENDPOINT")
    return parts


def _https_connection(host, *, timeout):
    # http.client uses no environment proxies, redirect/auth handlers or HTTP
    # retry loop. Platform TLS trust and DNS remain operational prerequisites.
    return http.client.HTTPSConnection(host, port=443, timeout=timeout,
                                      context=ssl.create_default_context())


class _Deadline:
    def __init__(self, clock, timeout):
        self.clock, self.timeout = clock, timeout
        self.start = self.last = self._now()

    def _now(self):
        value = self.clock()
        _require(type(value) in (int, float) and math.isfinite(value), "ADAPTER_CLOCK")
        return value

    def remaining(self):
        now = self._now()
        _require(now >= self.last, "ADAPTER_CLOCK")
        self.last = now
        remaining = self.timeout - (now - self.start)
        _require(remaining > 0, "TRANSPORT_TIMEOUT")
        return remaining


class _Response:
    def __init__(self, response, connection, sock, deadline, request):
        self._response, self._connection, self._socket = response, connection, sock
        self._deadline, self._cap = deadline, request.max_response_bytes
        self._total, self._closed = 0, False
        self.status, self.final_url = 200, request.endpoint

    def read(self, amount):
        try:
            _require(not self._closed and type(amount) is int
                     and 0 < amount <= min(65536, self._cap - self._total + 1), "ADAPTER_READ")
            self._socket.settimeout(self._deadline.remaining())
            # read1 avoids a body-filling loop hiding multiple blocking receives
            # under one unchanged socket timeout. HTTP framing remains stdlib's.
            body = self._response.read1(amount)
            self._deadline.remaining()
            _require(type(body) is bytes and len(body) <= amount, "ADAPTER_BODY")
            _require(body or getattr(self._response, "length", None) in (None, 0), "ADAPTER_TRUNCATED_BODY")
            self._total += len(body)
            _require(self._total <= self._cap, "TRANSPORT_RESPONSE_TOO_LARGE")
            return body
        except _Refused as exc:
            self.close()
            raise A1SourceError(str(exc)) from None
        except TimeoutError:
            self.close()
            raise A1SourceError("TRANSPORT_TIMEOUT") from None
        except Exception:
            self.close()
            raise A1SourceError("ADAPTER_UNAVAILABLE") from None

    def close(self):
        if self._closed:
            return
        self._closed = True
        for resource in (self._response, self._connection):
            try:
                resource.close()
            except Exception:
                pass


@dataclass(frozen=True, repr=False)
class A1HttpAdapter:
    """Pin one RPC origin/route and Demo authentication, then inject explicitly.

    Construction performs no connection or credential/environment lookup.
    The physical RPC path/query may carry a secret; it must share the exact
    public origin. No arbitrary alias host, fallback or endpoint switch exists.
    """

    rpc_origin: str
    rpc_url: str = field(repr=False)
    coingecko_api_key: str = field(repr=False)
    connection_factory: object = field(default=_https_connection, repr=False, compare=False)
    monotonic: object = field(default=time.monotonic, repr=False, compare=False)

    def __repr__(self):
        return "A1HttpAdapter(configuration=<redacted>, contract='a1-explicit-http-adapter-v1')"

    def __post_init__(self):
        try:
            origin, target = _url(self.rpc_origin), _url(self.rpc_url)
            _require(self.rpc_origin == f"https://{origin.hostname}"
                     and not origin.path and not origin.query
                     and target.hostname == origin.hostname, "ADAPTER_RPC_ORIGIN")
            key = self.coingecko_api_key
            _require(type(key) is str and 0 < len(key) <= 512
                     and all(32 < ord(c) < 127 for c in key), "ADAPTER_AUTH_CONFIGURATION")
            _require(callable(self.connection_factory) and callable(self.monotonic), "ADAPTER_INJECTIONS")
        except _Refused as exc:
            raise A1SourceError(str(exc)) from None

    def _route(self, request):
        # The canonical request remains secret-free and is never replaced.
        if request.scope in ("solana", "safety"):
            _require(request.method == "POST" and request.endpoint == self.rpc_origin, "ADAPTER_RPC_ROUTE")
            _rpc_body(request)
            return _url(self.rpc_url), dict(request.headers)
        _require(request.scope in ("valuation", "diagnostic") and request.method == "GET",
                 "ADAPTER_OHLCV_ROUTE")
        parts = _url(request.endpoint)
        _require(parts.netloc == "api.coingecko.com", "ADAPTER_OHLCV_ROUTE")
        match = re.fullmatch(r"/api/v3/onchain/networks/solana/pools/([1-9A-HJ-NP-Za-km-z]+)/ohlcv/minute", parts.path)
        _require(match is not None, "ADAPTER_OHLCV_ROUTE")
        query = tuple(parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True))
        _require(tuple(k for k, _ in query) == _QUERY_NAMES
                 and parts.query == urlencode(query), "ADAPTER_OHLCV_QUERY")
        values = dict(query)
        _address(match[1]); _address(values["token"])
        _require((values["aggregate"], values["limit"], values["currency"], values["include_empty_intervals"])
                 == ("1", "3", "usd", "false") and re.fullmatch(r"[0-9]{1,12}", values["before_timestamp"]),
                 "ADAPTER_OHLCV_QUERY")
        cutoff = int(values["before_timestamp"])
        _require(str(cutoff) == values["before_timestamp"] and cutoff % 60 == 0, "ADAPTER_OHLCV_QUERY")
        return parts, {**dict(request.headers), "x-cg-demo-api-key": self.coingecko_api_key}

    def __call__(self, request, *, timeout):
        connection = response = None
        try:
            _require(type(request) is A1HttpRequest, "ADAPTER_REQUEST")
            request.__post_init__()
            _require(type(timeout) in (float, int) and math.isfinite(timeout)
                     and timeout == request.timeout.total_seconds(), "ADAPTER_TIMEOUT_BINDING")
            parts, headers = self._route(request)
            deadline = _Deadline(self.monotonic, timeout)
            connection = self.connection_factory(parts.hostname, timeout=deadline.remaining())
            connection.timeout = deadline.remaining()
            # Initial connection/send uses the constructor's remaining timeout.
            # No explicit connect, redirect handler, retry or second request.
            target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
            connection.request(request.method, target, body=request.body if request.method == "POST" else None,
                               headers=headers)
            sock = connection.sock
            _require(callable(getattr(sock, "settimeout", None)), "ADAPTER_SOCKET")
            sock.settimeout(deadline.remaining())
            response = connection.getresponse()
            deadline.remaining()
            _require(type(response.status) is int and response.status == 200, "ADAPTER_HTTP_STATUS")
            return _Response(response, connection, sock, deadline, request)
        except _Refused as exc:
            reason = str(exc)
        except TimeoutError:
            reason = "TRANSPORT_TIMEOUT"
        except Exception:
            reason = "ADAPTER_UNAVAILABLE"
        for resource in (response, connection):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    pass
        raise A1SourceError(reason) from None
