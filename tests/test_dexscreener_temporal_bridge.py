from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

import core.data.dexscreener_temporal_bridge as bridge
from core.data.dexscreener_transport import AttemptRecord, TokenPairsResponse
from core.data.market_data_temporal_evidence import TemporalEvidenceError


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "market_data" / "temporal_evidence.json"
RECEIVED_AT = "2026-09-18T10:00:00.000000Z"
EVALUATION_TIME = datetime(2026, 9, 18, 10, 0, 12, 500000, tzinfo=timezone.utc)


def mocked_transport(calls: list[tuple[str, str]]):
    def transport(chain_id: str, token_address: str) -> TokenPairsResponse:
        calls.append((chain_id, token_address))
        body = json.dumps(json.loads(FIXTURE_PATH.read_text())["pairs"]).encode()
        return TokenPairsResponse(
            endpoint=f"https://api.dexscreener.com/token-pairs/v1/{chain_id}/{token_address}",
            chain_id=chain_id,
            token_address=token_address,
            status_code=200,
            body=body,
            received_at=RECEIVED_AT,
            attempts=(
                AttemptRecord(
                    attempt=1,
                    status_code=200,
                    response_bytes=len(body),
                    received_at=RECEIVED_AT,
                ),
            ),
        )

    return transport


def test_bridge_composes_real_inspector_and_converter_with_one_fetch() -> None:
    calls: list[tuple[str, str]] = []

    result = bridge.inspect_token_with_temporal(
        "chain-A",
        "token-A",
        transport=mocked_transport(calls),
        evaluation_clock=lambda: EVALUATION_TIME,
    )

    assert calls == [("chain-A", "token-A")]
    assert result["evaluation_time"] == "2026-09-18T10:00:12.500000Z"
    report = result["report"]
    temporal = result["temporal_evidence"]
    assert report["payload"]["pair_count"] == 3
    assert [record["market_subject_id"] for record in temporal["records"]] == [
        "chain-A:Pool-A",
        "chain-A:Pool-A",
        "chain-A:Pool-B",
    ]
    assert temporal["records"][0]["occurrence_id"] != temporal["records"][1]["occurrence_id"]
    assert temporal["records"][0]["received_at"] == RECEIVED_AT
    assert temporal["records"][0]["source_observed_at"] is None
    assert temporal["records"][0]["source_freshness"]["status"] == "UNKNOWN"
    assert temporal["records"][0]["receipt_recency"]["age_seconds"] == "12.5"
    assert temporal["records"][0]["pair_created_at_source_value"] == "1710000000000"


def test_empty_report_keeps_converter_empty_and_receipt_evaluation_distinct() -> None:
    body = b"[]"
    calls = 0

    def transport(chain_id: str, token_address: str) -> TokenPairsResponse:
        nonlocal calls
        calls += 1
        return TokenPairsResponse(
            endpoint="https://api.dexscreener.com/token-pairs/v1/chain-A/token-A",
            chain_id=chain_id,
            token_address=token_address,
            status_code=200,
            body=body,
            received_at=RECEIVED_AT,
            attempts=(
                AttemptRecord(
                    attempt=1,
                    status_code=200,
                    response_bytes=len(body),
                    received_at=RECEIVED_AT,
                ),
            ),
        )

    result = bridge.inspect_token_with_temporal(
        "chain-A",
        "token-A",
        transport=transport,
        evaluation_clock=lambda: EVALUATION_TIME,
    )

    assert calls == 1
    assert result["report"]["receipt"]["received_at"] == RECEIVED_AT
    assert result["evaluation_time"] == "2026-09-18T10:00:12.500000Z"
    assert result["temporal_evidence"]["records"] == []


def test_conversion_failure_fails_closed_without_second_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fail_conversion(*args: object, **kwargs: object) -> object:
        raise TemporalEvidenceError("conversion failed")

    monkeypatch.setattr(bridge, "convert_inspection_report", fail_conversion)

    with pytest.raises(TemporalEvidenceError, match="conversion failed"):
        bridge.inspect_token_with_temporal(
            "chain-A",
            "token-A",
            transport=mocked_transport(calls),
            evaluation_clock=lambda: EVALUATION_TIME,
        )

    assert calls == [("chain-A", "token-A")]