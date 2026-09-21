"""One bounded server-side GET for the approved CoinGecko OHLCV request.

This module owns transport only. It does not read environment variables, parse
JSON, retry, schedule work, select markets, or produce signal evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
import socket
from typing import Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from core.data.coingecko_onchain_ohlcv import (
    AuthenticatedOhlcvRequest,
    OhlcvOutcome,
    OhlcvResponse,
)


USER_AGENT = "mch-p04-lme-02/1"
READ_CHUNK_BYTES = 65_536


class ResponseLike(Protocol):
    status: int

    def read(self, amount: int = -1) -> bytes: ...

    def close(self) -> None: ...


Clock = Callable[[], datetime]
Opener = Callable[..., ResponseLike]


class _NoRedirectHandler(HTTPRedirectHandler):
    """Make every redirect observable as its original non-2xx response."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _ResponseTooLarge(ValueError):
    pass


class _InvalidTransportResponse(ValueError):
    pass


def _clock_utc(clock: Clock) -> datetime:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("transport clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _open_without_redirects(request: Request, *, timeout: float) -> ResponseLike:
    return build_opener(_NoRedirectHandler()).open(request, timeout=timeout)


def _status(response: ResponseLike) -> int:
    value = getattr(response, "status", None)
    if value is None:
        getcode = getattr(response, "getcode", None)
        value = getcode() if callable(getcode) else None
    if type(value) is not int or not 100 <= value <= 599:
        raise _InvalidTransportResponse("invalid HTTP status")
    return value


def _read_bounded(response: ResponseLike, maximum: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        amount = min(READ_CHUNK_BYTES, maximum - total + 1)
        chunk = response.read(amount)
        if not isinstance(chunk, (bytes, bytearray)):
            raise _InvalidTransportResponse("response body was not bytes")
        if not chunk:
            return b"".join(chunks)
        value = bytes(chunk)
        total += len(value)
        if total > maximum:
            raise _ResponseTooLarge("response exceeded configured limit")
        chunks.append(value)


def fetch_pool_ohlcv(
    authenticated: AuthenticatedOhlcvRequest,
    *,
    opener: Opener = _open_without_redirects,
    clock: Clock = _default_clock,
) -> OhlcvResponse:
    """Perform exactly one request and return source facts for pure mapping."""

    if not isinstance(authenticated, AuthenticatedOhlcvRequest):
        raise ValueError("authenticated OHLCV request required")
    source_request = authenticated.request
    started_at = _clock_utc(clock)
    request = Request(
        source_request.url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            **dict(authenticated.headers),
        },
    )
    response: ResponseLike | None = None
    try:
        response = opener(request, timeout=source_request.timeout.total_seconds())
        status = _status(response)
        if not 200 <= status < 300:
            received_at = _clock_utc(clock)
            return OhlcvResponse(
                source_request, started_at, received_at, b"", status,
            )
        body = _read_bounded(response, source_request.max_response_bytes)
        received_at = _clock_utc(clock)
        return OhlcvResponse(
            source_request, started_at, received_at, body, status,
        )
    except HTTPError as error:
        response = error
        received_at = _clock_utc(clock)
        status = error.code if type(error.code) is int else None
        if status is None or not 100 <= status <= 599:
            return OhlcvResponse(
                source_request, started_at, received_at, b"", None,
                OhlcvOutcome.SOURCE_UNAVAILABLE,
            )
        return OhlcvResponse(
            source_request, started_at, received_at, b"", status,
        )
    except _ResponseTooLarge:
        received_at = _clock_utc(clock)
        return OhlcvResponse(
            source_request, started_at, received_at, b"", None,
            OhlcvOutcome.RESPONSE_TOO_LARGE,
        )
    except (TimeoutError, socket.timeout):
        received_at = _clock_utc(clock)
        return OhlcvResponse(
            source_request, started_at, received_at, b"", None,
            OhlcvOutcome.TIMEOUT,
        )
    except URLError as error:
        received_at = _clock_utc(clock)
        outcome = (
            OhlcvOutcome.TIMEOUT
            if isinstance(error.reason, (TimeoutError, socket.timeout))
            else OhlcvOutcome.SOURCE_UNAVAILABLE
        )
        return OhlcvResponse(
            source_request, started_at, received_at, b"", None, outcome,
        )
    except (ConnectionError, OSError, _InvalidTransportResponse):
        received_at = _clock_utc(clock)
        return OhlcvResponse(
            source_request, started_at, received_at, b"", None,
            OhlcvOutcome.SOURCE_UNAVAILABLE,
        )
    finally:
        if response is not None:
            response.close()


__all__ = ["fetch_pool_ohlcv"]
