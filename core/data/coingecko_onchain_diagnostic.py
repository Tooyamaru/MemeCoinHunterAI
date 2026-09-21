"""One-shot server-side diagnostic composition for P04-LME-02."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Callable, Mapping

from core.data.coingecko_onchain_ohlcv import (
    OhlcvOutcome,
    OhlcvRequest,
    OhlcvResponse,
    prepare_authenticated_request,
)
from core.data.coingecko_onchain_transport import fetch_pool_ohlcv
from core.data.contracts import FreshnessPolicy
from core.data.market_observations import P02T07PredecessorContext
from core.signals.price_direction_policy import (
    PriceDirectionResult,
    derive_price_direction,
)


API_KEY_ENVIRONMENT_NAME = "COINGECKO_DEMO_API_KEY"
Clock = Callable[[], datetime]
Transport = Callable[..., OhlcvResponse]


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _utc(clock: Clock) -> datetime:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("diagnostic clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def run_ohlcv_diagnostic(
    *,
    request: OhlcvRequest,
    predecessor: P02T07PredecessorContext,
    freshness_policy: FreshnessPolicy,
    environment: Mapping[str, str] | None = None,
    transport: Transport = fetch_pool_ohlcv,
    clock: Clock = _default_clock,
) -> PriceDirectionResult:
    """Fetch once and run the existing mapper/policy from original inputs."""

    if not isinstance(request, OhlcvRequest):
        raise ValueError("validated request required")
    values = os.environ if environment is None else environment
    if not isinstance(values, Mapping):
        raise ValueError("environment must be a mapping")
    api_key = values.get(API_KEY_ENVIRONMENT_NAME)
    try:
        authenticated = prepare_authenticated_request(request, api_key=api_key)
    except ValueError:
        moment = _utc(clock)
        response = OhlcvResponse(
            request, moment, moment, b"", None,
            OhlcvOutcome.AUTHENTICATION_FAILED,
        )
        return derive_price_direction(
            request=request,
            response=response,
            predecessor=predecessor,
            freshness_policy=freshness_policy,
            evaluation_time=moment,
        )
    response = transport(authenticated, clock=clock)
    evaluation_time = _utc(clock)
    return derive_price_direction(
        request=request,
        response=response,
        predecessor=predecessor,
        freshness_policy=freshness_policy,
        evaluation_time=evaluation_time,
    )


__all__ = ["API_KEY_ENVIRONMENT_NAME", "run_ohlcv_diagnostic"]
