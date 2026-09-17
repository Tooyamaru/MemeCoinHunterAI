"""Bounded, provider-specific DexScreener token-pairs transport.

This module owns only HTTP transport.  It deliberately does not parse market
fields, select a pair, construct a P08 observation, or call any downstream
boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import socket
import time
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEXSCREENER_BASE_URL = "https://api.dexscreener.com"
TOKEN_PAIRS_PATH = "/token-pairs/v1/{chain_id}/{token_address}"
REQUEST_TIMEOUT_SECONDS = 10.0
MAX_RESPONSE_BYTES = 1_048_576
MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 1.0
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})

_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._~-]+$")


class ResponseLike(Protocol):
    status: int

    def read(self, amount: int = -1) -> bytes: ...

    def close(self) -> None: ...


Clock = Callable[[], datetime]
Sleeper = Callable[[float], None]
Opener = Callable[..., ResponseLike]


def utc_timestamp(value: datetime) -> str:
    """Render a receipt timestamp without using source observation semantics."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("receipt clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def build_token_pairs_url(chain_id: str, token_address: str) -> str:
    """Build the exact address-scoped endpoint from two explicit path segments."""

    for name, value in (("chain_id", chain_id), ("token_address", token_address)):
        if not isinstance(value, str) or not value or not _SEGMENT_RE.fullmatch(value):
            raise ValueError(
                f"{name} must be one non-empty URL-safe identifier without path separators"
            )
    return f"{DEXSCREENER_BASE_URL}{TOKEN_PAIRS_PATH.format(chain_id=chain_id, token_address=token_address)}"


@dataclass(frozen=True)
class AttemptRecord:
    """Observable metadata for one bounded request attempt."""

    attempt: int
    status_code: int | None
    response_bytes: int
    received_at: str
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "attempt": self.attempt,
            "status_code": self.status_code,
            "response_bytes": self.response_bytes,
            "received_at": self.received_at,
        }
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass(frozen=True)
class TokenPairsResponse:
    """Raw successful response plus transport-only provenance."""

    endpoint: str
    chain_id: str
    token_address: str
    status_code: int
    body: bytes
    received_at: str
    attempts: tuple[AttemptRecord, ...]


class DexScreenerTransportError(RuntimeError):
    """Base class for explicit transport failures."""

    code = "TRANSPORT_ERROR"

    def __init__(
        self,
        message: str,
        *,
        attempts: tuple[AttemptRecord, ...] = (),
    ) -> None:
        super().__init__(message)
        self.attempts = attempts


class HttpStatusError(DexScreenerTransportError):
    code = "HTTP_ERROR"

    def __init__(
        self,
        status_code: int,
        *,
        attempts: tuple[AttemptRecord, ...],
    ) -> None:
        super().__init__(
            f"DexScreener returned HTTP {status_code}",
            attempts=attempts,
        )
        self.status_code = status_code


class ResponseTooLargeError(DexScreenerTransportError):
    code = "RESPONSE_TOO_LARGE"

    def __init__(
        self,
        *,
        response_bytes: int,
        attempts: tuple[AttemptRecord, ...],
    ) -> None:
        super().__init__(
            f"DexScreener response exceeded {MAX_RESPONSE_BYTES} bytes",
            attempts=attempts,
        )
        self.response_bytes = response_bytes


class ConnectionFailureError(DexScreenerTransportError):
    code = "CONNECTION_FAILURE"


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _status_code(response: ResponseLike) -> int:
    value = getattr(response, "status", None)
    if value is None:
        getcode = getattr(response, "getcode", None)
        value = getcode() if callable(getcode) else None
    if not isinstance(value, int) or isinstance(value, bool):
        raise DexScreenerTransportError("response did not provide an integer HTTP status")
    return value


def _read_bounded(response: ResponseLike) -> bytes:
    body = response.read(MAX_RESPONSE_BYTES + 1)
    if not isinstance(body, (bytes, bytearray)):
        raise DexScreenerTransportError("response body was not bytes")
    if len(body) > MAX_RESPONSE_BYTES:
        raise ResponseTooLargeError(response_bytes=len(body), attempts=())
    return bytes(body)


def _is_retryable_connection_error(error: BaseException) -> bool:
    if isinstance(error, (TimeoutError, socket.timeout)):
        return False
    if isinstance(error, (ConnectionError, ConnectionResetError, BrokenPipeError)):
        return True
    if isinstance(error, URLError):
        return not isinstance(error.reason, (TimeoutError, socket.timeout))
    return False


def fetch_token_pairs(
    chain_id: str,
    token_address: str,
    *,
    opener: Opener = urlopen,
    sleeper: Sleeper = time.sleep,
    clock: Clock = _default_clock,
) -> TokenPairsResponse:
    """Fetch one token lookup with at most one fixed-delay retry."""

    endpoint = build_token_pairs_url(chain_id, token_address)
    request = Request(
        endpoint,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": "p08-dexscreener-inspector/1",
        },
    )
    attempts: list[AttemptRecord] = []

    for attempt_number in range(1, MAX_ATTEMPTS + 1):
        status_code: int | None = None
        response_bytes = 0
        received_at = utc_timestamp(clock())
        response: ResponseLike | None = None
        try:
            response = opener(request, timeout=REQUEST_TIMEOUT_SECONDS)
            status_code = _status_code(response)
            body = _read_bounded(response)
            response_bytes = len(body)
            received_at = utc_timestamp(clock())
            attempts.append(
                AttemptRecord(
                    attempt=attempt_number,
                    status_code=status_code,
                    response_bytes=response_bytes,
                    received_at=received_at,
                )
            )
            if 200 <= status_code < 300:
                return TokenPairsResponse(
                    endpoint=endpoint,
                    chain_id=chain_id,
                    token_address=token_address,
                    status_code=status_code,
                    body=body,
                    received_at=received_at,
                    attempts=tuple(attempts),
                )
            if (
                status_code not in RETRYABLE_STATUS_CODES
                or attempt_number == MAX_ATTEMPTS
            ):
                raise HttpStatusError(status_code, attempts=tuple(attempts))
        except HTTPError as error:
            response = error
            status_code = error.code
            try:
                body = _read_bounded(error)
                response_bytes = len(body)
            except ResponseTooLargeError as oversized:
                attempts.append(
                    AttemptRecord(
                        attempt=attempt_number,
                        status_code=status_code,
                        response_bytes=oversized.response_bytes,
                        received_at=received_at,
                    )
                )
                oversized.attempts = tuple(attempts)
                raise
            received_at = utc_timestamp(clock())
            attempts.append(
                AttemptRecord(
                    attempt=attempt_number,
                    status_code=status_code,
                    response_bytes=response_bytes,
                    received_at=received_at,
                )
            )
            if (
                status_code not in RETRYABLE_STATUS_CODES
                or attempt_number == MAX_ATTEMPTS
            ):
                raise HttpStatusError(status_code, attempts=tuple(attempts)) from error
        except ResponseTooLargeError as error:
            attempts.append(
                AttemptRecord(
                    attempt=attempt_number,
                    status_code=status_code,
                    response_bytes=error.response_bytes,
                    received_at=received_at,
                )
            )
            error.attempts = tuple(attempts)
            raise
        except HttpStatusError:
            raise
        except DexScreenerTransportError as error:
            attempts.append(
                AttemptRecord(
                    attempt=attempt_number,
                    status_code=status_code,
                    response_bytes=response_bytes,
                    received_at=received_at,
                    error=type(error).__name__,
                )
            )
            error.attempts = tuple(attempts)
            raise
        except (TimeoutError, socket.timeout) as error:
            attempts.append(
                AttemptRecord(
                    attempt=attempt_number,
                    status_code=status_code,
                    response_bytes=response_bytes,
                    received_at=received_at,
                    error=type(error).__name__,
                )
            )
            raise ConnectionFailureError(
                "DexScreener request timed out",
                attempts=tuple(attempts),
            ) from error
        except (ConnectionError, ConnectionResetError, BrokenPipeError, URLError) as error:
            attempts.append(
                AttemptRecord(
                    attempt=attempt_number,
                    status_code=status_code,
                    response_bytes=response_bytes,
                    received_at=received_at,
                    error=type(error).__name__,
                )
            )
            if not _is_retryable_connection_error(error) or attempt_number == MAX_ATTEMPTS:
                raise ConnectionFailureError(
                    "DexScreener connection failed",
                    attempts=tuple(attempts),
                ) from error
        finally:
            if response is not None:
                response.close()

        if attempt_number < MAX_ATTEMPTS:
            sleeper(RETRY_DELAY_SECONDS)

    raise AssertionError("bounded transport loop exited without a result")