from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

import pytest

from core.data.dexscreener_inspection import (
    InvalidSourceShapeError,
    MalformedJsonError,
    NonFiniteNumberError,
    inspect_response,
    inspect_token,
    main,
)
from core.data.dexscreener_transport import (
    MAX_RESPONSE_BYTES,
    RETRY_DELAY_SECONDS,
    AttemptRecord,
    ConnectionFailureError,
    HttpStatusError,
    ResponseTooLargeError,
    TokenPairsResponse,
    build_token_pairs_url,
    fetch_token_pairs,
)


FIXTURE_PATH = Path("tests/fixtures/dexscreener/token_pairs.json")
ENDPOINT = build_token_pairs_url(
    "ethereum",
    "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
)
RECEIVED_AT = "2026-09-17T03:00:00.000000Z"


class FakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.body = body
        self.closed = False

    def read(self, amount: int = -1) -> bytes:
        return self.body if amount < 0 else self.body[:amount]

    def close(self) -> None:
        self.closed = True


def response(body: bytes, *, status: int = 200) -> FakeResponse:
    return FakeResponse(status, body)


def response_contract(body: bytes, *, attempts: int = 1) -> TokenPairsResponse:
    records = tuple(
        AttemptRecord(
            attempt=index,
            status_code=200,
            response_bytes=len(body),
            received_at=RECEIVED_AT,
        )
        for index in range(1, attempts + 1)
    )
    return TokenPairsResponse(
        endpoint=ENDPOINT,
        chain_id="ethereum",
        token_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        status_code=200,
        body=body,
        received_at=RECEIVED_AT,
        attempts=records,
    )


def fixture_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()


def test_exact_endpoint_and_request_shape() -> None:
    calls: list[tuple[Any, float]] = []

    def opener(request: Any, *, timeout: float) -> FakeResponse:
        calls.append((request, timeout))
        return response(b"[]")

    result = fetch_token_pairs(
        "ethereum",
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        opener=opener,
        clock=lambda: datetime(2026, 9, 17, tzinfo=timezone.utc),
    )

    assert result.endpoint == ENDPOINT
    assert len(calls) == 1
    assert calls[0][0].full_url == ENDPOINT
    assert calls[0][0].method == "GET"
    assert calls[0][1] == 10.0
    assert calls[0][0].get_header("Authorization") is None


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_each_retryable_status_retries_once(status: int) -> None:
    calls: list[int] = []
    sleeps: list[float] = []

    def opener(request: Any, *, timeout: float) -> FakeResponse:
        calls.append(len(calls) + 1)
        return response(b"temporary", status=status) if len(calls) == 1 else response(b"[]")

    result = fetch_token_pairs(
        "ethereum",
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        opener=opener,
        sleeper=sleeps.append,
        clock=lambda: datetime(2026, 9, 17, tzinfo=timezone.utc),
    )

    assert result.body == b"[]"
    assert len(calls) == 2
    assert sleeps == [RETRY_DELAY_SECONDS]
    assert result.attempts[0].status_code == status


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_non_retryable_status_does_not_retry(status: int) -> None:
    calls: list[int] = []

    def opener(request: Any, *, timeout: float) -> FakeResponse:
        calls.append(1)
        return response(b"error", status=status)

    with pytest.raises(HttpStatusError) as raised:
        fetch_token_pairs(
            "ethereum",
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            opener=opener,
            sleeper=lambda _: pytest.fail("unexpected retry"),
        )

    assert raised.value.status_code == status
    assert len(raised.value.attempts) == 1


def test_connection_reset_retries_once_and_timeout_does_not() -> None:
    reset_calls: list[int] = []

    def reset_opener(request: Any, *, timeout: float) -> FakeResponse:
        reset_calls.append(1)
        if len(reset_calls) == 1:
            raise ConnectionResetError("reset")
        return response(b"[]")

    result = fetch_token_pairs(
        "ethereum",
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        opener=reset_opener,
        sleeper=lambda _: None,
    )
    assert len(result.attempts) == 2

    timeout_calls: list[int] = []

    def timeout_opener(request: Any, *, timeout: float) -> FakeResponse:
        timeout_calls.append(1)
        raise TimeoutError("timeout")

    with pytest.raises(ConnectionFailureError):
        fetch_token_pairs(
            "ethereum",
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            opener=timeout_opener,
            sleeper=lambda _: pytest.fail("unexpected retry"),
        )
    assert len(timeout_calls) == 1


def test_http_error_and_url_error_are_explicit() -> None:
    calls: list[int] = []

    def http_opener(request: Any, *, timeout: float) -> Any:
        calls.append(1)
        raise HTTPError(ENDPOINT, 503, "busy", {}, None)

    with pytest.raises(HttpStatusError):
        fetch_token_pairs(
            "ethereum",
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            opener=http_opener,
            sleeper=lambda _: None,
        )
    assert len(calls) == 2

    with pytest.raises(ConnectionFailureError):
        fetch_token_pairs(
            "ethereum",
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            opener=lambda request, timeout: (_ for _ in ()).throw(
                URLError("offline")
            ),
            sleeper=lambda _: None,
        )


def test_oversized_response_is_rejected_without_truncation() -> None:
    body = b"x" * (MAX_RESPONSE_BYTES + 1)

    with pytest.raises(ResponseTooLargeError) as raised:
        fetch_token_pairs(
            "ethereum",
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            opener=lambda request, timeout: response(body),
        )

    assert raised.value.response_bytes == MAX_RESPONSE_BYTES + 1
    assert len(raised.value.attempts) == 1


def test_normalization_preserves_pairs_digest_decimal_scale_and_provenance() -> None:
    body = fixture_bytes()
    report = inspect_response(response_contract(body))

    assert report["payload"]["raw_payload_sha256"] == hashlib.sha256(body).hexdigest()
    assert report["payload"]["pair_count"] == 2
    assert report["payload"]["pairs"][0]["priceUsd"] == "1.2300"
    assert report["payload"]["pairs"][0]["pairCreatedAt"] == "1710000000000"
    assert (
        report["payload"]["pairs"][0]["inspection"]["field_provenance"][
            "pairs[0].priceUsd"
        ]
        == {
            "source_field": "pairs[0].priceUsd",
            "normalized_value": "1.2300",
        }
    )
    assert (
        report["payload"]["pairs"][0]["inspection"]["source_pair_created_at"]
        == "1710000000000"
    )
    assert report["request"]["attempts"] == 1
    assert report["receipt"]["received_at"] == RECEIVED_AT


def test_complete_report_is_acyclic_and_json_serializable() -> None:
    report = inspect_response(response_contract(fixture_bytes()))

    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    parsed = json.loads(serialized)

    assert parsed["payload"]["pair_count"] == 2
    assert (
        parsed["payload"]["pairs"][0]["inspection"]["field_provenance"][
            "pairs[0]"
        ]["normalized_value"]["pairAddress"]
        == "0x1111111111111111111111111111111111111111"
    )
    assert (
        parsed["payload"]["pairs"][0]["inspection"]["findings"][0]["value"]
        == {"buys": "1", "sells": "2"}
    )


def test_report_is_not_a_p08_observation_and_never_uses_receipt_or_pair_time() -> None:
    report = inspect_response(response_contract(fixture_bytes()))
    assert report["evidence"]["p08_acceptance"] == "NOT_ATTEMPTED"
    assert report["evidence"]["p08_observed_at"] is None
    assert report["evidence"]["asset_age"]["status"] == "UNAVAILABLE"
    assert report["receipt"]["received_at"] != report["evidence"]["p08_observed_at"]
    assert report["evidence"]["unavailable_fields"] == [
        {
            "field": "observed_at",
            "reason": "NO_DOCUMENTED_MARKET_FIELD_OBSERVATION_TIMESTAMP",
        },
        {
            "field": "asset_age",
            "reason": "NO_DOCUMENTED_TOKEN_ORIGIN_SEMANTICS",
        },
        {
            "field": "volume.measurement_window",
            "reason": "NO_EXACT_UTC_WINDOW_ENDPOINTS",
        },
    ]


def test_missing_fields_are_explicit_findings_and_no_pair_is_selected() -> None:
    body = json.dumps(
        [
            {
                "pairAddress": "0x1",
                "priceUsd": "not-a-number",
                "pairCreatedAt": None,
            },
            {
                "pairAddress": "0x1",
                "priceUsd": "2.00",
                "pairCreatedAt": "not-a-number",
            },
        ]
    ).encode()
    report = inspect_response(response_contract(body))
    pairs = report["payload"]["pairs"]
    assert len(pairs) == 2
    codes = {finding["code"] for pair in pairs for finding in pair["inspection"]["findings"]}
    assert {
        "MISSING_SOURCE_FIELD",
        "INVALID_NUMERIC_FIELD",
        "DUPLICATE_PAIR",
        "CONFLICTING_DUPLICATE_PAIR",
    } <= codes


def test_duplicate_equal_pairs_are_retained_and_marked() -> None:
    pair = {"pairAddress": "0x1", "priceUsd": 1.0}
    report = inspect_response(response_contract(json.dumps([pair, pair]).encode()))
    assert report["payload"]["pair_count"] == 2
    assert all(
        any(
            finding["code"] == "DUPLICATE_PAIR"
            for finding in pair["inspection"]["findings"]
        )
        for pair in report["payload"]["pairs"]
    )


@pytest.mark.parametrize(
    ("body", "exception"),
    [
        (b"{", MalformedJsonError),
        (b'{"not": "an array"}', InvalidSourceShapeError),
        (b"[1]", InvalidSourceShapeError),
        (b"[NaN]", NonFiniteNumberError),
    ],
)
def test_malformed_and_invalid_shapes_fail_closed(
    body: bytes,
    exception: type[BaseException],
) -> None:
    with pytest.raises(exception):
        inspect_response(response_contract(body))


def test_over_limit_pair_array_is_rejected() -> None:
    body = json.dumps([{} for _ in range(129)]).encode()
    with pytest.raises(InvalidSourceShapeError):
        inspect_response(response_contract(body))


def test_normalization_has_zero_network_calls() -> None:
    calls: list[int] = []

    def never_call(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        raise AssertionError("network call")

    report = inspect_token(
        "ethereum",
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        transport=lambda chain_id, token_address: response_contract(fixture_bytes()),
    )
    assert report["payload"]["pair_count"] == 2
    assert calls == []


def test_cli_success_uses_mocked_transport_and_prints_complete_report(
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, str]] = []

    def mocked_transport(chain_id: str, token_address: str) -> TokenPairsResponse:
        calls.append((chain_id, token_address))
        return response_contract(fixture_bytes())

    code = main(
        [
            "--chain-id",
            "ethereum",
            "--token-address",
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        ],
        transport=mocked_transport,
    )
    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert code == 0
    assert calls == [
        ("ethereum", "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    ]
    assert set(report) == {
        "tool_version",
        "source",
        "request",
        "receipt",
        "payload",
        "evidence",
    }
    assert report["tool_version"] == "dexscreener-inspection-v1"
    assert report["source"] == "DexScreener"
    assert report["request"] == {
        "endpoint": ENDPOINT,
        "chain_id": "ethereum",
        "token_address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "attempts": 1,
        "retry_count": 0,
        "attempt_log": [
            {
                "attempt": 1,
                "status_code": 200,
                "response_bytes": len(fixture_bytes()),
                "received_at": RECEIVED_AT,
            }
        ],
    }
    assert report["receipt"] == {
        "received_at": RECEIVED_AT,
        "http_status": 200,
        "response_bytes": len(fixture_bytes()),
    }
    assert report["payload"]["raw_payload_sha256"] == hashlib.sha256(
        fixture_bytes()
    ).hexdigest()
    assert report["payload"]["pair_count"] == 2
    assert len(report["payload"]["pairs"]) == 2
    assert report["payload"]["pairs"][0]["priceUsd"] == "1.2300"
    assert report["payload"]["pairs"][0]["liquidity"]["usd"] == "987654.3200"
    assert report["payload"]["pairs"][0]["volume"]["h24"] == "123456.7800"
    assert report["evidence"]["p08_acceptance"] == "NOT_ATTEMPTED"
    assert report["evidence"]["p08_observed_at"] is None


def test_cli_error_report_is_json_serializable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def no_network(*args: Any, **kwargs: Any) -> Any:
        raise ConnectionFailureError("simulated offline transport")

    code = main(
        [
            "--chain-id",
            "ethereum",
            "--token-address",
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        ],
        transport=no_network,
    )
    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert code == 1
    assert report["request"]["endpoint"] == ENDPOINT
    assert report["payload"] == {
        "raw_payload_sha256": None,
        "pair_count": 0,
        "pairs": [],
    }
    assert report["error"] == {
        "code": "CONNECTION_FAILURE",
        "message": "simulated offline transport",
        "path": None,
    }
    assert report["evidence"]["p08_acceptance"] == "NOT_ATTEMPTED"
    assert report["evidence"]["p08_observed_at"] is None
    assert "Authorization" not in captured.out
