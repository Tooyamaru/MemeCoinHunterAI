from datetime import timedelta
from io import BytesIO
import socket
from urllib.error import HTTPError, URLError

import pytest

from core.data.coingecko_onchain_ohlcv import (
    OhlcvOutcome,
    prepare_authenticated_request,
)
from core.data.coingecko_onchain_transport import (
    USER_AGENT,
    _NoRedirectHandler,
    fetch_pool_ohlcv,
)
from tests.test_coingecko_onchain_ohlcv import FIXTURE, REFERENCE, request


SECRET = "server-side-test-key"


class FakeResponse:
    def __init__(self, body=b"{}", *, status=200, non_bytes=False):
        self.body = body
        self.status = status
        self.non_bytes = non_bytes
        self.offset = 0
        self.closed = False
        self.read_amounts = []

    def read(self, amount=-1):
        self.read_amounts.append(amount)
        if self.non_bytes:
            return "not-bytes"
        if self.offset >= len(self.body):
            return b""
        end = len(self.body) if amount < 0 else self.offset + amount
        value = self.body[self.offset:end]
        self.offset += len(value)
        return value

    def close(self):
        self.closed = True


def clock(*values):
    iterator = iter(values)
    return lambda: next(iterator)


def prepared(**changes):
    return prepare_authenticated_request(request(**changes), api_key=SECRET)


def test_exact_get_header_url_timeout_single_attempt_and_close():
    response = FakeResponse(FIXTURE.read_bytes())
    calls = []

    def opener(value, *, timeout):
        calls.append((value, timeout))
        return response

    result = fetch_pool_ohlcv(
        prepared(), opener=opener,
        clock=clock(REFERENCE, REFERENCE + timedelta(seconds=1)),
    )

    assert len(calls) == 1
    outgoing, timeout = calls[0]
    assert outgoing.full_url == request().url
    assert outgoing.get_method() == "GET"
    headers = {key.lower(): value for key, value in outgoing.header_items()}
    assert headers == {
        "accept": "application/json",
        "user-agent": USER_AGENT,
        "x-cg-demo-api-key": SECRET,
    }
    assert timeout == 10.0
    assert result.body == FIXTURE.read_bytes()
    assert result.http_status == 200
    assert result.transport_failure is None
    assert response.closed is True
    assert SECRET not in repr(result)


def test_streaming_limit_is_request_owned_and_closes_response():
    response = FakeResponse(b"123456")
    result = fetch_pool_ohlcv(
        prepared(max_response_bytes=5),
        opener=lambda *args, **kwargs: response,
        clock=clock(REFERENCE, REFERENCE + timedelta(seconds=1)),
    )
    assert result.transport_failure is OhlcvOutcome.RESPONSE_TOO_LARGE
    assert result.body == b""
    assert response.closed
    assert all(amount <= 6 for amount in response.read_amounts)


@pytest.mark.parametrize("status", [300, 302, 401, 403, 429, 500])
def test_returned_non_2xx_is_preserved_without_reading_error_body(status):
    response = FakeResponse(b"provider error containing untrusted text", status=status)
    result = fetch_pool_ohlcv(
        prepared(), opener=lambda *args, **kwargs: response,
        clock=clock(REFERENCE, REFERENCE + timedelta(seconds=1)),
    )
    assert result.http_status == status
    assert result.body == b""
    assert response.read_amounts == []
    assert response.closed
    assert "untrusted" not in repr(result)


def test_http_error_is_preserved_and_body_is_discarded():
    provider_body = BytesIO(b"secret provider error")
    error = HTTPError(request().url, 429, "rate limited", {}, provider_body)
    result = fetch_pool_ohlcv(
        prepared(), opener=lambda *args, **kwargs: (_ for _ in ()).throw(error),
        clock=clock(REFERENCE, REFERENCE + timedelta(seconds=1)),
    )
    assert result.http_status == 429
    assert result.body == b""
    assert provider_body.closed


@pytest.mark.parametrize("error", [
    TimeoutError(), socket.timeout(), URLError(TimeoutError()),
])
def test_timeouts_map_to_existing_outcome(error):
    result = fetch_pool_ohlcv(
        prepared(), opener=lambda *args, **kwargs: (_ for _ in ()).throw(error),
        clock=clock(REFERENCE, REFERENCE + timedelta(seconds=1)),
    )
    assert result.transport_failure is OhlcvOutcome.TIMEOUT
    assert result.body == b""


@pytest.mark.parametrize("error", [
    ConnectionError(), ConnectionResetError(), URLError("dns"), OSError("tls"),
])
def test_connection_failures_map_to_source_unavailable_without_detail(error):
    result = fetch_pool_ohlcv(
        prepared(), opener=lambda *args, **kwargs: (_ for _ in ()).throw(error),
        clock=clock(REFERENCE, REFERENCE + timedelta(seconds=1)),
    )
    assert result.transport_failure is OhlcvOutcome.SOURCE_UNAVAILABLE
    assert result.body == b""
    assert "dns" not in repr(result)
    assert "tls" not in repr(result)


@pytest.mark.parametrize("response", [
    FakeResponse(status=True), FakeResponse(status=None), FakeResponse(non_bytes=True),
])
def test_invalid_transport_response_fails_closed_and_closes(response):
    result = fetch_pool_ohlcv(
        prepared(), opener=lambda *args, **kwargs: response,
        clock=clock(REFERENCE, REFERENCE + timedelta(seconds=1)),
    )
    assert result.transport_failure is OhlcvOutcome.SOURCE_UNAVAILABLE
    assert response.closed


def test_naive_transport_clock_is_rejected_before_network():
    called = False

    def opener(*args, **kwargs):
        nonlocal called
        called = True
        return FakeResponse()

    with pytest.raises(ValueError, match="timezone-aware"):
        fetch_pool_ohlcv(
            prepared(), opener=opener,
            clock=lambda: REFERENCE.replace(tzinfo=None),
        )
    assert called is False


def test_redirect_handler_never_constructs_followup_request():
    assert _NoRedirectHandler().redirect_request(
        object(), object(), 302, "redirect", {}, "https://evil.example/"
    ) is None


def test_authenticated_type_is_required():
    with pytest.raises(ValueError, match="authenticated"):
        fetch_pool_ohlcv(object())
