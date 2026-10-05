"""Adapter conformance with fake connections; every real network entry blocked."""
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
import io
import json
import ssl
from unittest.mock import patch

import pytest

from core.data import a1_http_adapter as adapter
from core.data.a1_bounded_transport import A1BoundedTransport, A1HttpRequest
from core.data.a1_collection_budget import A1BudgetLedger, A1OperationalBudget
from core.data.a1_cpmm_sources import A1SourceError
from core.data.coingecko_onchain_ohlcv import OhlcvRequest
from tests.test_a1_operational_collection import FakeClock
from tests.test_a1_p03_collection import network_guard  # noqa: F401
from tests import test_a1_cpmm_sources as f

ORIGIN = "https://solana.example.invalid"
RPC_ROUTE = ORIGIN + "/private/fake-rpc-route?access=fake-route-value"
KEY = "fake-demo-key-for-offline-tests"


class Tick:
    def __init__(self, step=0.001):
        self.value, self.step = 0.0, step

    def __call__(self):
        value = self.value
        self.value += self.step
        return value


class Socket:
    def __init__(self):
        self.timeouts = []

    def settimeout(self, value):
        self.timeouts.append(value)


class Response:
    def __init__(self, body=b"abc", status=200):
        self.status, self.stream = status, io.BytesIO(body)
        self.reads, self.closed = [], False

    def read1(self, amount):
        self.reads.append(amount)
        return self.stream.read(amount)

    def close(self):
        self.closed = True


class Connection:
    def __init__(self, response=None, fail=None):
        self.sock, self.response = Socket(), response or Response()
        self.calls, self.closed, self.fail = [], False, fail

    def request(self, method, target, *, body, headers):
        self.calls.append((method, target, body, headers))
        if self.fail:
            raise self.fail

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class Factory:
    def __init__(self, response=None, fail=None):
        self.connections, self.calls = [], []
        self.response, self.fail = response, fail

    def __call__(self, host, *, timeout):
        self.calls.append((host, timeout))
        connection = Connection(self.response, self.fail)
        self.connections.append(connection)
        return connection


def opener(factory=None, clock=None, **kwargs):
    return adapter.A1HttpAdapter(rpc_origin=ORIGIN, rpc_url=RPC_ROUTE,
        coingecko_api_key=KEY, connection_factory=factory or Factory(), monotonic=clock or Tick(), **kwargs)


def rpc(scope="solana", cap=64):
    envelope = dict(jsonrpc="2.0", id=1, method="getBlockTime" if scope == "safety" else "getGenesisHash",
                    params=[123] if scope == "safety" else [])
    body = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    return A1HttpRequest(scope, ORIGIN, "POST", body, timedelta(seconds=10), cap)


def ohlcv(scope="valuation", cap=64):
    source = OhlcvRequest("solana", f.M0, f.POOL, f.M0, f.M1, f.T, timedelta(seconds=10), cap)
    return A1HttpRequest(scope, source.url, "GET", b"", source.timeout, cap)


def transport(factory, *, cap=64, request=None):
    clock = FakeClock()
    budget = A1OperationalBudget(timedelta(seconds=55))
    ledger = A1BudgetLedger(budget, "adapter:one", clock(), ORIGIN, "https://api.coingecko.com")
    wire = request or rpc(cap=cap)
    owner = A1BoundedTransport(rpc_endpoint=ORIGIN, opener=opener(factory), clock=clock, ledger=ledger)
    return owner, ledger, wire


def test_construction_is_no_contact_no_environment_frozen_and_redacted(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("construction must not use environment or connect")
    monkeypatch.setattr("os.getenv", forbidden)
    monkeypatch.setattr(adapter.http.client, "HTTPSConnection", forbidden)
    value = adapter.A1HttpAdapter(ORIGIN, RPC_ROUTE, KEY)
    assert KEY not in repr(value) and RPC_ROUTE not in repr(value)
    with pytest.raises(FrozenInstanceError):
        value.rpc_url = ORIGIN


@pytest.mark.parametrize("scope", ["solana", "safety", "valuation", "diagnostic"])
def test_exact_request_routing_authentication_and_remaining_socket_deadline(scope):
    factory = Factory()
    wire = rpc(scope) if scope in ("solana", "safety") else ohlcv(scope)
    response = opener(factory)(wire, timeout=10)
    assert response.status == 200 and response.final_url == wire.endpoint
    assert response.read(64) == b"abc" and response.read(61) == b""
    response.close(); response.close()
    conn = factory.connections[0]
    assert len(factory.calls) == len(conn.calls) == 1
    assert conn.closed and conn.response.closed
    assert 0 < conn.timeout <= factory.calls[0][1] < 10
    assert all(0 < t < 10 for t in conn.sock.timeouts)
    assert conn.sock.timeouts == sorted(conn.sock.timeouts, reverse=True)
    method, target, body, headers = conn.calls[0]
    assert method == wire.method
    if scope in ("solana", "safety"):
        assert factory.calls[0][0] == "solana.example.invalid"
        assert target == "/private/fake-rpc-route?access=fake-route-value"
        assert body is wire.body and KEY not in headers.values()
    else:
        assert factory.calls[0][0] == "api.coingecko.com"
        assert wire.endpoint == "https://api.coingecko.com" + target
        assert body is None and headers["x-cg-demo-api-key"] == KEY
    assert KEY not in repr(wire) and "fake-route-value" not in repr(wire)


@pytest.mark.parametrize("change", [
    {"rpc_origin": ORIGIN + "/"}, {"rpc_origin": ORIGIN + "?key=fake"},
    {"rpc_url": "http://solana.example.invalid"}, {"rpc_url": "https://other.example.invalid/"},
    {"rpc_url": "https://user:fake@solana.example.invalid"}, {"rpc_url": ORIGIN + ":444/"},
    {"rpc_url": ORIGIN + "/#secret"}, {"rpc_url": ORIGIN + "/\r\nsecret"},
    {"coingecko_api_key": ""}, {"coingecko_api_key": "fake\r\nheader"},
    {"coingecko_api_key": "x" * 513}, {"connection_factory": None}, {"monotonic": None},
])
def test_invalid_configuration_fails_before_connection_without_secret_echo(change):
    factory = Factory()
    args = dict(rpc_origin=ORIGIN, rpc_url=RPC_ROUTE, coingecko_api_key=KEY,
                connection_factory=factory, monotonic=Tick())
    args.update(change)
    with pytest.raises(A1SourceError) as caught:
        adapter.A1HttpAdapter(**args)
    assert "fake" not in str(caught.value) and factory.calls == []


@pytest.mark.parametrize("mode", ["rpc_path", "rpc_host", "rpc_get", "cg_host", "cg_path",
    "cg_query_extra", "cg_query_duplicate", "cg_query_order", "cg_cap", "cg_cutoff", "cg_mint"])
def test_route_refusal_before_any_connection(mode):
    factory = Factory()
    wire = rpc() if mode.startswith("rpc") else ohlcv()
    if mode == "rpc_path": wire = replace(wire, endpoint=ORIGIN + "/other")
    elif mode == "rpc_host": wire = replace(wire, endpoint="https://other.example.invalid")
    elif mode == "rpc_get": wire = replace(wire, method="GET", body=b"")
    elif mode == "cg_host": wire = replace(wire, endpoint=wire.endpoint.replace("api.coingecko.com", "other.example.invalid"))
    elif mode == "cg_path": wire = replace(wire, endpoint=wire.endpoint.replace("/minute?", "/hour?"))
    elif mode == "cg_query_extra": wire = replace(wire, endpoint=wire.endpoint + "&api_key=fake")
    elif mode == "cg_query_duplicate": wire = replace(wire, endpoint=wire.endpoint + "&token=" + f.M0)
    elif mode == "cg_query_order": wire = replace(wire, endpoint=wire.endpoint.replace("aggregate=1&limit=3", "limit=3&aggregate=1"))
    elif mode == "cg_cap": wire = replace(wire, endpoint=wire.endpoint.replace("limit=3", "limit=4"))
    elif mode == "cg_cutoff": wire = replace(wire, endpoint=wire.endpoint.replace("before_timestamp=", "before_timestamp=0"))
    elif mode == "cg_mint": wire = replace(wire, endpoint=wire.endpoint.replace("token=" + f.M0, "token=bad"))
    with pytest.raises(A1SourceError):
        opener(factory)(wire, timeout=10)
    assert factory.calls == []


@pytest.mark.parametrize("body", [
    b'{"id":1,"jsonrpc":"2.0","method":"sendTransaction","params":[]}',
    b'{"id":1,"jsonrpc":"2.0","method":"requestAirdrop","params":[]}',
    b'{"id":1,"id":2,"jsonrpc":"2.0","method":"getGenesisHash","params":[]}',
    b'{"id":true,"jsonrpc":"2.0","method":"getGenesisHash","params":[]}',
    b'{"id":1,"jsonrpc":"2.0","method":"getGenesisHash","params":[NaN]}',
    b'not-json',
])
def test_rpc_wire_rejects_mutating_methods_and_noncanonical_envelopes_before_connection(body):
    factory = Factory()
    with pytest.raises(A1SourceError): opener(factory)(replace(rpc(), body=body), timeout=10)
    assert factory.calls == []


def test_safety_scope_preserves_finalized_read_only_owner_profile():
    factory = Factory()
    value = dict(id=1, jsonrpc="2.0", method="getTokenSupply", params=[f.M0, {"commitment": "processed"}])
    wire = replace(rpc("safety"), body=json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
    with pytest.raises(A1SourceError): opener(factory)(wire, timeout=10)
    assert factory.calls == []


@pytest.mark.parametrize("timeout", [9, True, float("nan"), float("inf"), "10"])
def test_exact_timeout_binding_required(timeout):
    factory = Factory()
    with pytest.raises(A1SourceError, match="ADAPTER_TIMEOUT_BINDING"):
        opener(factory)(rpc(), timeout=timeout)
    assert factory.calls == []


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308, 401, 403, 429, 500])
def test_redirect_auth_rate_limit_and_http_failure_stop_without_read_retry_or_fallback(status):
    factory = Factory(Response(status=status))
    owner, ledger, wire = transport(factory)
    with pytest.raises(A1SourceError, match="ADAPTER_HTTP_STATUS"):
        owner.http(wire)
    conn = factory.connections[0]
    assert len(factory.calls) == len(conn.calls) == 1
    assert conn.response.reads == [] and conn.closed and conn.response.closed
    assert len(ledger.snapshot().attempts) == 1
    with pytest.raises(A1SourceError): owner.http(wire)
    assert len(factory.calls) == 1


@pytest.mark.parametrize("fail", [TimeoutError("fake-private-value"), OSError("fake-private-value")])
def test_send_failure_sanitized_and_connection_closed(fail):
    factory = Factory(fail=fail)
    owner, ledger, wire = transport(factory)
    with pytest.raises(A1SourceError) as caught:
        owner.http(wire)
    assert "fake-private-value" not in str(caught.value)
    assert factory.connections[0].closed and len(ledger.snapshot().attempts) == 1


@pytest.mark.parametrize("size", [4, 5])
def test_byte_cap_exact_boundary_and_one_sentinel_byte(size):
    factory = Factory(Response(b"a" * size))
    owner, ledger, wire = transport(factory, cap=4)
    if size == 4:
        assert owner.http(wire).body == b"aaaa"
    else:
        with pytest.raises(A1SourceError, match="TRANSPORT_RESPONSE_TOO_LARGE"):
            owner.http(wire)
    conn = factory.connections[0]
    assert conn.response.reads == ([5, 1] if size == 4 else [5])
    assert conn.closed and conn.response.closed and len(ledger.snapshot().attempts) == 1


@pytest.mark.parametrize("phase", ["construction", "read", "backward", "nonfinite"])
def test_deadline_and_bad_clock_fail_closed(phase):
    tick, factory = Tick(), Factory()
    if phase == "construction": tick.step = 6
    if phase == "nonfinite": tick.value = float("nan")
    value = opener(factory, tick)
    if phase in ("construction", "nonfinite"):
        with pytest.raises(A1SourceError): value(rpc(), timeout=10)
        assert all(c.closed and c.calls == [] for c in factory.connections)
        return
    response = value(rpc(), timeout=10)
    tick.value = 11 if phase == "read" else -1
    with pytest.raises(A1SourceError): response.read(64)
    assert factory.connections[0].response.reads == []
    assert factory.connections[0].closed


@pytest.mark.parametrize("mode", ["type", "overread", "exception"])
def test_invalid_read_and_reader_errors_close_and_never_leak(mode):
    factory = Factory()
    response = opener(factory)(rpc(), timeout=10)
    def bad(amount):
        if mode == "exception": raise RuntimeError(KEY)
        return "not bytes" if mode == "type" else b"x" * (amount + 1)
    factory.connections[0].response.read1 = bad
    with pytest.raises(A1SourceError) as caught: response.read(2)
    assert KEY not in str(caught.value) and factory.connections[0].closed


def test_real_stdlib_factory_uses_verified_TLS_and_exact_host_timeout_without_connecting():
    with patch.object(adapter.http.client, "HTTPSConnection") as ctor:
        adapter._https_connection("solana.example.invalid", timeout=4.5)
    args, kwargs = ctor.call_args
    assert args == ("solana.example.invalid",) and kwargs["port"] == 443 and kwargs["timeout"] == 4.5
    assert kwargs["context"].check_hostname is True
    assert kwargs["context"].verify_mode == ssl.CERT_REQUIRED


@pytest.mark.parametrize("raw, succeeds", [
    (b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\nConnection: close\r\n\r\nabc", True),
    (b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabc\r\n0\r\n\r\n", True),
    (b"HTTP/1.1 302 Found\r\nLocation: https://other.example.invalid/\r\nContent-Length: 0\r\n\r\n", False),
    (b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nabcde", False),
    (b"HTTP/1.1 200 OK\r\nContent-Length: 6\r\n\r\nabc", False),
])
def test_default_stdlib_HTTP_framing_send_and_no_redirect_with_fake_socket(monkeypatch, raw, succeeds):
    class WireSocket(Socket):
        def __init__(self):
            super().__init__()
            self.sent, self.closed = [], False
        def sendall(self, body): self.sent.append(body)
        def makefile(self, mode): return io.BytesIO(raw)
        def close(self): self.closed = True
    sock, connections = WireSocket(), []
    def fake_connect(connection):
        connections.append(connection)
        connection.sock = sock
    monkeypatch.setattr(adapter.http.client.HTTPSConnection, "connect", fake_connect)
    value = adapter.A1HttpAdapter(ORIGIN, RPC_ROUTE, KEY, monotonic=Tick())
    clock = FakeClock()
    ledger = A1BudgetLedger(A1OperationalBudget(timedelta(seconds=55)), "stdlib:one", clock(),
                           ORIGIN, "https://api.coingecko.com")
    owner = A1BoundedTransport(rpc_endpoint=ORIGIN, opener=value, clock=clock, ledger=ledger)
    if succeeds:
        assert owner.http(ohlcv(cap=4)).body == b"abc"
    else:
        with pytest.raises(A1SourceError): owner.http(ohlcv(cap=4))
    wire = b"".join(sock.sent)
    assert wire.count(b"GET ") == 1 and KEY.encode() in wire
    assert len(connections) == 1 and sock.closed
