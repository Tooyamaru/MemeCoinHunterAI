"""Bounded Solana JSON-RPC source for the P01-OAF-01 trusted upstream path.

This module is transport/evidence plumbing only. It performs no autonomous
selection, polling, retry, subscription, trading, wallet, signing, or
eligibility decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any, Callable, Mapping
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError


SOLANA_OAF_SOURCE_VERSION = "p01-oaf-01-solana-rpc-v1"
DEFAULT_MAX_RESPONSE_BYTES = 262_144


class SolanaSourceUnavailable(RuntimeError):
    """Safe bounded failure for an unavailable or invalid RPC source."""


@dataclass(frozen=True)
class SolanaRpcObservation:
    method: str
    slot: int
    observed_at: datetime
    result: Any
    received_at: datetime | None = None
    source_id: str = "solana-json-rpc"
    source_version: str = SOLANA_OAF_SOURCE_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.method, str) or not self.method:
            raise ValueError("method is required")
        if not isinstance(self.slot, int) or self.slot < 0:
            raise ValueError("slot must be a non-negative integer")
        if (
            not isinstance(self.observed_at, datetime)
            or self.observed_at.tzinfo is None
            or self.observed_at.utcoffset() is None
        ):
            raise ValueError("observed_at must be timezone-aware")
        if self.received_at is not None:
            if (
                not isinstance(self.received_at, datetime)
                or self.received_at.tzinfo is None
                or self.received_at.utcoffset() is None
            ):
                raise ValueError("received_at must be timezone-aware")
            if self.received_at < self.observed_at:
                raise ValueError("received_at cannot precede source observed_at")


@dataclass(frozen=True)
class SolanaMintSnapshot:
    token_mint: str
    mint_account: SolanaRpcObservation
    largest_accounts: SolanaRpcObservation
    token_supply: SolanaRpcObservation

    def __post_init__(self) -> None:
        if not isinstance(self.token_mint, str) or not self.token_mint.strip():
            raise ValueError("token_mint is required")


RpcCall = Callable[[str, list[Any]], Mapping[str, Any]]
Clock = Callable[[], datetime]


class SolanaJsonRpcSource:
    """One-shot finalized reads with finite bounds and no automatic retry."""

    def __init__(
        self,
        *,
        rpc_url: str,
        timeout_seconds: float,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        rpc_call: RpcCall | None = None,
        clock: Clock | None = None,
    ) -> None:
        if not isinstance(rpc_url, str) or not rpc_url.startswith(("http://", "https://")):
            raise ValueError("rpc_url must be an HTTP(S) URL")
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if (
            not isinstance(max_response_bytes, int)
            or max_response_bytes < 1024
            or max_response_bytes > 1_048_576
        ):
            raise ValueError("max_response_bytes is outside the bounded range")
        self._rpc_url = rpc_url
        self._timeout_seconds = float(timeout_seconds)
        self._max_response_bytes = max_response_bytes
        self._rpc_call = rpc_call or self._http_call
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._block_times: dict[int, datetime] = {}

    def snapshot_mint(self, token_mint: str) -> SolanaMintSnapshot:
        if not isinstance(token_mint, str) or not token_mint.strip():
            raise ValueError("token_mint is required")
        mint = self._context_observation(
            "getAccountInfo",
            [token_mint, {"encoding": "jsonParsed", "commitment": "finalized"}],
        )
        self._validate_mint_account(mint.result)
        largest = self._context_observation(
            "getTokenLargestAccounts",
            [token_mint, {"commitment": "finalized"}],
        )
        supply = self._context_observation(
            "getTokenSupply",
            [token_mint, {"commitment": "finalized"}],
        )
        return SolanaMintSnapshot(token_mint, mint, largest, supply)

    def _context_observation(self, method: str, params: list[Any]) -> SolanaRpcObservation:
        payload = self._rpc_call(method, params)
        received_at = self._utc_clock()
        result = _rpc_result(payload)
        if not isinstance(result, Mapping):
            raise SolanaSourceUnavailable("RPC_RESULT_INVALID")
        context = result.get("context")
        if not isinstance(context, Mapping) or type(context.get("slot")) is not int:
            raise SolanaSourceUnavailable("RPC_CONTEXT_SLOT_MISSING")
        slot = context["slot"]
        if slot < 0:
            raise SolanaSourceUnavailable("RPC_CONTEXT_SLOT_INVALID")
        observed_at = self._block_time(slot)
        try:
            return SolanaRpcObservation(
                method,
                slot,
                observed_at,
                result.get("value"),
                received_at=received_at,
            )
        except ValueError:
            raise SolanaSourceUnavailable("RPC_RECEIPT_TIMELINE_INVALID") from None

    def _block_time(self, slot: int) -> datetime:
        cached = self._block_times.get(slot)
        if cached is not None:
            return cached
        payload = self._rpc_call("getBlockTime", [slot])
        value = _rpc_result(payload)
        if type(value) not in (int, float):
            raise SolanaSourceUnavailable("RPC_BLOCK_TIME_UNAVAILABLE")
        try:
            observed = datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            raise SolanaSourceUnavailable("RPC_BLOCK_TIME_INVALID") from None
        self._block_times[slot] = observed
        return observed

    def _utc_clock(self) -> datetime:
        value = self._clock()
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise SolanaSourceUnavailable("RPC_RECEIPT_TIME_INVALID")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _validate_mint_account(value: Any) -> None:
        if not isinstance(value, Mapping):
            raise SolanaSourceUnavailable("MINT_ACCOUNT_NOT_FOUND")
        owner = value.get("owner")
        if owner not in {
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
        }:
            raise SolanaSourceUnavailable("MINT_PROGRAM_UNSUPPORTED")
        data = value.get("data")
        if not isinstance(data, Mapping):
            raise SolanaSourceUnavailable("MINT_ACCOUNT_DATA_INVALID")
        parsed = data.get("parsed")
        if not isinstance(parsed, Mapping) or parsed.get("type") != "mint":
            raise SolanaSourceUnavailable("ACCOUNT_IS_NOT_MINT")

    def _http_call(self, method: str, params: list[Any]) -> Mapping[str, Any]:
        body = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            separators=(",", ":"),
        ).encode("utf-8")
        req = urllib_request.Request(
            self._rpc_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=self._timeout_seconds) as response:
                raw = response.read(self._max_response_bytes + 1)
        except (HTTPError, URLError, TimeoutError, OSError):
            raise SolanaSourceUnavailable("RPC_TRANSPORT_UNAVAILABLE") from None
        if len(raw) > self._max_response_bytes:
            raise SolanaSourceUnavailable("RPC_RESPONSE_TOO_LARGE")
        try:
            decoded = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SolanaSourceUnavailable("RPC_RESPONSE_INVALID_JSON") from None
        if not isinstance(decoded, Mapping):
            raise SolanaSourceUnavailable("RPC_RESPONSE_INVALID")
        return decoded


def _rpc_result(payload: Mapping[str, Any]) -> Any:
    if not isinstance(payload, Mapping) or payload.get("jsonrpc") != "2.0":
        raise SolanaSourceUnavailable("RPC_ENVELOPE_INVALID")
    if payload.get("error") is not None:
        raise SolanaSourceUnavailable("RPC_SOURCE_ERROR")
    if "result" not in payload:
        raise SolanaSourceUnavailable("RPC_RESULT_MISSING")
    return payload["result"]


__all__ = [
    "DEFAULT_MAX_RESPONSE_BYTES",
    "SOLANA_OAF_SOURCE_VERSION",
    "SolanaJsonRpcSource",
    "SolanaMintSnapshot",
    "SolanaRpcObservation",
    "SolanaSourceUnavailable",
]
