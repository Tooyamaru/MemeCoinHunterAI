from datetime import timedelta

import pytest

from core.data.coingecko_onchain_diagnostic import (
    API_KEY_ENVIRONMENT_NAME,
    run_ohlcv_diagnostic,
)
from core.data.coingecko_onchain_ohlcv import OhlcvOutcome, OhlcvResponse
from core.data.coingecko_onchain_transport import fetch_pool_ohlcv
from tests.test_coingecko_onchain_ohlcv import (
    FIXTURE,
    FRESHNESS,
    REFERENCE,
    predecessor,
    request,
)
from tests.test_coingecko_onchain_transport import FakeResponse, clock


SECRET = "diagnostic-only-test-key"


def test_missing_environment_secret_fails_closed_without_transport():
    called = False

    def transport(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("transport must not run")

    result = run_ohlcv_diagnostic(
        request=request(), predecessor=predecessor(), freshness_policy=FRESHNESS,
        environment={}, transport=transport,
        clock=clock(REFERENCE + timedelta(seconds=1)),
    )
    assert result.outcome is OhlcvOutcome.AUTHENTICATION_FAILED
    assert result.signal_evidence is None
    assert result.market.observations == ()
    assert called is False


@pytest.mark.parametrize("value", ["", "bad\nheader", 123])
def test_invalid_environment_secret_fails_closed(value):
    result = run_ohlcv_diagnostic(
        request=request(), predecessor=predecessor(), freshness_policy=FRESHNESS,
        environment={API_KEY_ENVIRONMENT_NAME: value},
        clock=clock(REFERENCE + timedelta(seconds=1)),
    )
    assert result.outcome is OhlcvOutcome.AUTHENTICATION_FAILED
    assert result.signal_evidence is None


def test_mocked_one_shot_diagnostic_uses_post_receipt_evaluation_time():
    started = REFERENCE + timedelta(seconds=1)
    received = REFERENCE + timedelta(seconds=2)
    evaluated = REFERENCE + timedelta(seconds=3)
    calls = []

    def transport(authenticated, *, clock):
        calls.append(authenticated)
        assert authenticated.headers["x-cg-demo-api-key"] == SECRET
        return OhlcvResponse(
            authenticated.request, started, received, FIXTURE.read_bytes(), 200,
        )

    result = run_ohlcv_diagnostic(
        request=request(), predecessor=predecessor(), freshness_policy=FRESHNESS,
        environment={API_KEY_ENVIRONMENT_NAME: SECRET}, transport=transport,
        clock=clock(evaluated),
    )
    assert len(calls) == 1
    assert result.outcome is OhlcvOutcome.PRODUCED
    assert result.signal_evidence.evidence[0].signal_status == "RISING"
    assert all(item.reference_time == evaluated for item in result.market.observations)
    assert all(item.received_time == received for item in result.market.observations)
    assert SECRET not in repr(result)


def test_actual_transport_composes_with_mapper_using_only_mocked_http():
    started = REFERENCE + timedelta(seconds=1)
    received = REFERENCE + timedelta(seconds=2)
    evaluated = REFERENCE + timedelta(seconds=3)
    response = FakeResponse(FIXTURE.read_bytes())
    transport_clock = clock(started, received)

    def transport(authenticated, *, clock):
        return fetch_pool_ohlcv(
            authenticated,
            opener=lambda *args, **kwargs: response,
            clock=transport_clock,
        )

    result = run_ohlcv_diagnostic(
        request=request(), predecessor=predecessor(), freshness_policy=FRESHNESS,
        environment={API_KEY_ENVIRONMENT_NAME: SECRET}, transport=transport,
        clock=clock(evaluated),
    )
    assert result.outcome is OhlcvOutcome.PRODUCED
    assert response.closed
    assert result.market.provenance.http_status == 200
    assert result.signal_evidence is not None


def test_transport_failure_never_produces_signal():
    moment = REFERENCE + timedelta(seconds=1)

    def transport(authenticated, *, clock):
        return OhlcvResponse(
            authenticated.request, moment, moment, b"", None,
            OhlcvOutcome.TIMEOUT,
        )

    result = run_ohlcv_diagnostic(
        request=request(), predecessor=predecessor(), freshness_policy=FRESHNESS,
        environment={API_KEY_ENVIRONMENT_NAME: SECRET}, transport=transport,
        clock=clock(moment + timedelta(seconds=1)),
    )
    assert result.outcome is OhlcvOutcome.TIMEOUT
    assert result.signal_evidence is None


def test_evaluation_before_receipt_fails_temporally():
    received = REFERENCE + timedelta(seconds=2)

    def transport(authenticated, *, clock):
        return OhlcvResponse(
            authenticated.request, REFERENCE + timedelta(seconds=1), received,
            FIXTURE.read_bytes(), 200,
        )

    result = run_ohlcv_diagnostic(
        request=request(), predecessor=predecessor(), freshness_policy=FRESHNESS,
        environment={API_KEY_ENVIRONMENT_NAME: SECRET}, transport=transport,
        clock=clock(REFERENCE + timedelta(seconds=1)),
    )
    assert result.outcome is OhlcvOutcome.TEMPORAL_INVALID
    assert result.signal_evidence is None


def test_explicit_freshness_still_controls_live_diagnostic():
    moment = REFERENCE + timedelta(seconds=5)

    def transport(authenticated, *, clock):
        return OhlcvResponse(
            authenticated.request, REFERENCE + timedelta(seconds=1),
            REFERENCE + timedelta(seconds=2), FIXTURE.read_bytes(), 200,
        )

    result = run_ohlcv_diagnostic(
        request=request(), predecessor=predecessor(),
        freshness_policy=type(FRESHNESS)(stale_after=timedelta(seconds=30)),
        environment={API_KEY_ENVIRONMENT_NAME: SECRET}, transport=transport,
        clock=clock(moment),
    )
    assert result.outcome is OhlcvOutcome.UPSTREAM_ADMISSION_REJECTED
    assert result.signal_evidence is None


def test_environment_mapping_and_aware_clock_are_required():
    with pytest.raises(ValueError, match="environment"):
        run_ohlcv_diagnostic(
            request=request(), predecessor=predecessor(), freshness_policy=FRESHNESS,
            environment=object(),
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        run_ohlcv_diagnostic(
            request=request(), predecessor=predecessor(), freshness_policy=FRESHNESS,
            environment={}, clock=lambda: REFERENCE.replace(tzinfo=None),
        )
