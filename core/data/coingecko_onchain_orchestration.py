"""Controlled one-shot composition into the approved OHLCV diagnostic.

This boundary validates a caller-directed exact pool target against a current
P02-T06 token predecessor before P04-LME-02 may read a credential or perform
network I/O. It never discovers, ranks, selects, retries, or schedules work.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
import re
from typing import Callable, Mapping

from core.data.coingecko_onchain_diagnostic import run_ohlcv_diagnostic
from core.data.coingecko_onchain_ohlcv import OhlcvRequest
from core.data.contracts import FreshnessPolicy
from core.data.market_observations import P02T07PredecessorContext
from core.signals.price_direction_policy import PriceDirectionResult


_REFERENCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_CONTRACT_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ControlledDiagnosticOutcome(StrEnum):
    DIAGNOSTIC_COMPLETED = "DIAGNOSTIC_COMPLETED"
    TOKEN_NOT_CURRENT = "TOKEN_NOT_CURRENT"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class ExactPoolDiagnosticTarget:
    """Exact target chosen upstream; this type does not approve or select it."""

    chain_id: str
    token_mint: str
    pool_address: str
    base_mint: str
    quote_mint: str
    target_reference_id: str
    target_reference_digest: str
    target_contract_version: str


@dataclass(frozen=True)
class ControlledDiagnosticResult:
    """Wrapper outcome; the nested diagnostic retains its own semantics."""

    outcome: ControlledDiagnosticOutcome
    reason_codes: tuple[str, ...]
    target: ExactPoolDiagnosticTarget | None
    request: OhlcvRequest | None = None
    diagnostic: PriceDirectionResult | None = None

    def __post_init__(self) -> None:
        if type(self.outcome) is not ControlledDiagnosticOutcome:
            raise ValueError("controlled diagnostic outcome required")
        if (
            not isinstance(self.reason_codes, tuple)
            or not self.reason_codes
            or not all(isinstance(code, str) and code for code in self.reason_codes)
        ):
            raise ValueError("non-empty reason codes required")
        completed = self.outcome is ControlledDiagnosticOutcome.DIAGNOSTIC_COMPLETED
        if completed and (
            not isinstance(self.target, ExactPoolDiagnosticTarget)
            or not isinstance(self.request, OhlcvRequest)
            or not isinstance(self.diagnostic, PriceDirectionResult)
        ):
            raise ValueError("completed result requires target, request, and diagnostic")
        if not completed and self.diagnostic is not None:
            raise ValueError("rejected result cannot contain a diagnostic")
        if self.outcome is ControlledDiagnosticOutcome.TOKEN_NOT_CURRENT and (
            not isinstance(self.target, ExactPoolDiagnosticTarget)
            or not isinstance(self.request, OhlcvRequest)
        ):
            raise ValueError("not-current result requires target and request")
        if self.outcome is ControlledDiagnosticOutcome.INVALID_INPUT and self.request is not None:
            raise ValueError("invalid-input result cannot contain a request")


Diagnostic = Callable[..., PriceDirectionResult]


def _invalid(
    reason: str,
    *,
    target: ExactPoolDiagnosticTarget | None = None,
) -> ControlledDiagnosticResult:
    return ControlledDiagnosticResult(
        ControlledDiagnosticOutcome.INVALID_INPUT,
        (reason,),
        target,
    )


def _valid_reference(target: ExactPoolDiagnosticTarget) -> bool:
    return (
        isinstance(target.target_reference_id, str)
        and _REFERENCE_ID.fullmatch(target.target_reference_id) is not None
        and isinstance(target.target_reference_digest, str)
        and _SHA256.fullmatch(target.target_reference_digest) is not None
        and isinstance(target.target_contract_version, str)
        and _CONTRACT_VERSION.fullmatch(target.target_contract_version) is not None
    )


def run_controlled_ohlcv_diagnostic(
    *,
    target: ExactPoolDiagnosticTarget,
    predecessor: P02T07PredecessorContext,
    reference_time: datetime,
    timeout: timedelta,
    max_response_bytes: int,
    freshness_policy: FreshnessPolicy,
    environment: Mapping[str, str] | None = None,
    diagnostic: Diagnostic = run_ohlcv_diagnostic,
    clock: Callable[[], datetime] | None = None,
) -> ControlledDiagnosticResult:
    """Validate one exact target and invoke P04-LME-02 at most once."""

    if type(target) is not ExactPoolDiagnosticTarget:
        return _invalid("EXACT_TARGET_REQUIRED")
    if not isinstance(predecessor, P02T07PredecessorContext):
        return _invalid("P02_PREDECESSOR_REQUIRED", target=target)
    if (
        not isinstance(freshness_policy, FreshnessPolicy)
        or freshness_policy.stale_after is None
    ):
        return _invalid("EXPLICIT_FRESHNESS_REQUIRED", target=target)
    if not callable(diagnostic):
        return _invalid("DIAGNOSTIC_CALLABLE_REQUIRED", target=target)
    if clock is not None and not callable(clock):
        return _invalid("CLOCK_CALLABLE_REQUIRED", target=target)
    if environment is not None and not isinstance(environment, Mapping):
        return _invalid("ENVIRONMENT_MAPPING_REQUIRED", target=target)
    if not _valid_reference(target):
        return _invalid("INVALID_TARGET_REFERENCE", target=target)

    try:
        request = OhlcvRequest(
            chain_id=target.chain_id,
            token_mint=target.token_mint,
            pool_address=target.pool_address,
            base_mint=target.base_mint,
            quote_mint=target.quote_mint,
            reference_time=reference_time,
            timeout=timeout,
            max_response_bytes=max_response_bytes,
        )
    except (TypeError, ValueError, OverflowError):
        return _invalid("INVALID_REQUEST", target=target)

    if not predecessor.contains(request.chain_id, request.token_mint):
        return ControlledDiagnosticResult(
            ControlledDiagnosticOutcome.TOKEN_NOT_CURRENT,
            ("TOKEN_NOT_CURRENT",),
            target,
            request,
        )

    arguments = {
        "request": request,
        "predecessor": predecessor,
        "freshness_policy": freshness_policy,
        "environment": environment,
    }
    if clock is not None:
        arguments["clock"] = clock
    result = diagnostic(**arguments)
    if not isinstance(result, PriceDirectionResult):
        raise TypeError("diagnostic must return PriceDirectionResult")
    return ControlledDiagnosticResult(
        ControlledDiagnosticOutcome.DIAGNOSTIC_COMPLETED,
        ("DIAGNOSTIC_INVOKED",),
        target,
        request,
        result,
    )


__all__ = [
    "ControlledDiagnosticOutcome",
    "ControlledDiagnosticResult",
    "ExactPoolDiagnosticTarget",
    "run_controlled_ohlcv_diagnostic",
]
