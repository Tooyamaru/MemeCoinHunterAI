from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pytest

from core.data.dexscreener_inspection import inspect_response
from core.data.dexscreener_transport import AttemptRecord, TokenPairsResponse
from core.data.market_data_temporal_evidence import (
    CONTRACT_VERSION,
    P08_ACCEPTANCE,
    SourceFreshnessStatus,
    TemporalEvidenceError,
    canonical_json,
    convert_inspection_report,
    temporal_evidence_digest,
)


UTC = timezone.utc
RECEIVED_AT = "2026-09-18T10:00:00.000000Z"
REFERENCE_TIME = datetime(2026, 9, 18, 10, 0, 12, 500000, tzinfo=UTC)
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "market_data" / "temporal_evidence.json"


def raw_pairs() -> list[dict[str, object]]:
    return json.loads(FIXTURE_PATH.read_text())["pairs"]


def inspected_report(
    *,
    pairs: list[dict[str, object]] | None = None,
    received_at: str = RECEIVED_AT,
) -> dict[str, object]:
    body = json.dumps(raw_pairs() if pairs is None else pairs, separators=(",", ":")).encode()
    response = TokenPairsResponse(
        endpoint="https://api.dexscreener.com/token-pairs/v1/chain-A/token-A",
        chain_id="chain-A",
        token_address="token-A",
        status_code=200,
        body=body,
        received_at=received_at,
        attempts=(
            AttemptRecord(
                attempt=1,
                status_code=200,
                response_bytes=len(body),
                received_at=received_at,
            ),
        ),
    )
    return inspect_response(response)


def test_actual_inspector_report_converts_one_record_per_pair() -> None:
    result = convert_inspection_report(
        inspected_report(),
        evaluation_time=REFERENCE_TIME,
    )

    assert result.p08_acceptance == P08_ACCEPTANCE
    assert result.source_id == "DexScreener"
    assert result.token_identity == "token-A"
    assert result.chain_id == "chain-A"
    assert len(result.records) == 3
    assert result.records[0].market_subject_id == "chain-A:Pool-A"
    assert result.records[0].volume_window.source_label == "h24"
    assert result.records[0].volume_window.exact_window is None
    assert result.records[0].pair_created_at_source_value == "1710000000000"
    assert result.records[2].pair_created_at_source_value is None


def test_missing_null_and_present_pair_creation_preserve_order_and_digest() -> None:
    pairs = raw_pairs()
    omitted = deepcopy(pairs[0])
    omitted.pop("pairCreatedAt")
    pairs = [omitted, deepcopy(pairs[1]), deepcopy(pairs[2])]

    report = inspected_report(pairs=pairs)
    source_pairs = report["payload"]["pairs"]
    assert "pairCreatedAt" not in source_pairs[0]
    assert "pairCreatedAt" not in source_pairs[0]["inspection"]["field_provenance"]
    assert source_pairs[0]["inspection"].get("source_pair_created_at") is None
    assert source_pairs[2]["pairCreatedAt"] is None
    assert source_pairs[2]["inspection"]["field_provenance"][
        "pairs[2].pairCreatedAt"
    ] == {
        "source_field": "pairs[2].pairCreatedAt",
        "normalized_value": None,
    }
    assert source_pairs[2]["inspection"]["source_pair_created_at"] is None

    result = convert_inspection_report(report, evaluation_time=REFERENCE_TIME)

    assert [record.market_subject_id for record in result.records] == [
        "chain-A:Pool-A",
        "chain-A:Pool-A",
        "chain-A:Pool-B",
    ]
    assert [
        record.pair_created_at_source_value for record in result.records
    ] == [None, "1710000000000", None]
    assert len({record.occurrence_id for record in result.records}) == 3
    assert '"pair_created_at_source_value":null' in canonical_json(
        result.as_mapping()
    )
    assert temporal_evidence_digest(result) == temporal_evidence_digest(
        convert_inspection_report(report, evaluation_time=REFERENCE_TIME)
    )


@pytest.mark.parametrize(
    ("field", "malformed"),
    [
        ("baseToken", "malformed"),
        ("quoteToken", "malformed"),
        ("priceUsd", "not-a-number"),
        ("liquidity", "malformed"),
        ("volume", {"h24": "not-a-number"}),
        ("txns", "malformed"),
        ("pairCreatedAt", "not-a-number"),
    ],
)
@pytest.mark.parametrize("state", ["omitted", "null", "valid", "malformed"])
def test_optional_market_field_policy(
    field: str,
    malformed: object,
    state: str,
) -> None:
    pair = deepcopy(raw_pairs()[0])
    if state == "omitted":
        pair.pop(field)
    elif state == "null":
        pair[field] = None
    elif state == "malformed":
        pair[field] = malformed

    if state == "malformed":
        with pytest.raises(TemporalEvidenceError, match=field):
            convert_inspection_report(
                inspected_report(pairs=[pair]),
                evaluation_time=REFERENCE_TIME,
            )
        return

    result = convert_inspection_report(
        inspected_report(pairs=[pair]),
        evaluation_time=REFERENCE_TIME,
    )

    assert len(result.records) == 1
    if field == "volume":
        assert result.records[0].volume_window.source_label == (
            "h24" if state == "valid" else None
        )
    if field == "pairCreatedAt":
        assert result.records[0].pair_created_at_source_value == (
            "1710000000000" if state == "valid" else None
        )


@pytest.mark.parametrize("field", ["pairAddress", "chainId"])
@pytest.mark.parametrize("state", ["omitted", "null"])
def test_structural_pair_identity_fields_remain_required(
    field: str,
    state: str,
) -> None:
    pair = deepcopy(raw_pairs()[0])
    if state == "omitted":
        pair.pop(field)
    else:
        pair[field] = None

    with pytest.raises(TemporalEvidenceError, match=field):
        convert_inspection_report(
            inspected_report(pairs=[pair]),
            evaluation_time=REFERENCE_TIME,
        )


@pytest.mark.parametrize("value", ["not-a-number", "NaN", "Infinity"])
def test_present_malformed_pair_creation_fails_closed(value: str) -> None:
    pairs = raw_pairs()
    pairs[0]["pairCreatedAt"] = value

    with pytest.raises(TemporalEvidenceError, match="pairCreatedAt"):
        convert_inspection_report(
            inspected_report(pairs=pairs),
            evaluation_time=REFERENCE_TIME,
        )


def test_duplicate_and_conflicting_pairs_remain_distinct_occurrences() -> None:
    result = convert_inspection_report(
        inspected_report(),
        evaluation_time=REFERENCE_TIME,
    )

    assert [record.market_subject_id for record in result.records[:2]] == [
        "chain-A:Pool-A",
        "chain-A:Pool-A",
    ]
    assert result.records[0].occurrence_id != result.records[1].occurrence_id
    assert result.records[0].as_mapping() != result.records[1].as_mapping()


def test_empty_pair_report_is_a_valid_empty_result() -> None:
    result = convert_inspection_report(
        inspected_report(pairs=[]),
        evaluation_time=REFERENCE_TIME,
    )

    assert result.empty is True
    assert result.records == ()


def test_receipt_recency_uses_only_explicit_reference_time() -> None:
    result = convert_inspection_report(
        inspected_report(),
        evaluation_time=REFERENCE_TIME,
    )

    assert result.records[0].received_at == RECEIVED_AT
    assert result.records[0].receipt_recency.reference_time == (
        "2026-09-18T10:00:12.500000Z"
    )
    assert result.records[0].receipt_recency.age_seconds == "12.5"


def test_reference_time_before_receipt_is_rejected() -> None:
    with pytest.raises(TemporalEvidenceError, match="precedes receipt"):
        convert_inspection_report(
            inspected_report(),
            evaluation_time=datetime(2026, 9, 18, 9, 59, 59, tzinfo=UTC),
        )


def test_unknown_source_freshness_is_not_changed_by_recent_receipt() -> None:
    result = convert_inspection_report(
        inspected_report(),
        evaluation_time=datetime(2026, 9, 18, 10, 0, 1, tzinfo=UTC),
    )

    record = result.records[0]
    assert record.source_observed_at is None
    assert record.source_freshness.status is SourceFreshnessStatus.UNKNOWN
    assert record.source_freshness.reason == (
        "NO_DOCUMENTED_MARKET_FIELD_OBSERVATION_TIMESTAMP"
    )
    assert record.receipt_recency.age_seconds == "1"
    assert result.p08_acceptance == "NOT_ATTEMPTED"


@pytest.mark.parametrize(
    "field",
    ["received_at", "source_pair_created_at", "last_trade_timestamp"],
)
def test_non_source_times_cannot_populate_source_observed_at(field: str) -> None:
    report = inspected_report()
    if field == "received_at":
        report["receipt"]["received_at"] = "2026-09-18T09:59:59.000000Z"
    elif field == "source_pair_created_at":
        report["payload"]["pairs"][0]["inspection"]["source_pair_created_at"] = (
            "2026-09-18T09:59:59.000000Z"
        )
    else:
        report["payload"]["pairs"][0]["last_trade_timestamp"] = (
            "2026-09-18T09:59:59.000000Z"
        )

    result = convert_inspection_report(report, evaluation_time=REFERENCE_TIME)
    assert result.records[0].source_observed_at is None
    assert result.records[0].source_freshness.status is SourceFreshnessStatus.UNKNOWN


def test_contradictory_source_observation_time_is_rejected() -> None:
    report = inspected_report()
    report["evidence"]["p08_observed_at"] = "2026-09-18T09:59:59.000000Z"

    with pytest.raises(TemporalEvidenceError, match="source observation time"):
        convert_inspection_report(report, evaluation_time=REFERENCE_TIME)


def test_unavailable_age_and_unknown_volume_window_are_preserved() -> None:
    result = convert_inspection_report(
        inspected_report(),
        evaluation_time=REFERENCE_TIME,
    )
    age = result.records[0].asset_age

    assert age.status.value == "UNAVAILABLE"
    assert age.amount is None
    assert age.reason == "NO_DOCUMENTED_TOKEN_ORIGIN_SEMANTICS"
    assert result.records[0].volume_window.exact_window is None


def test_invalid_report_identity_version_and_digest_fail_closed() -> None:
    wrong_source = inspected_report()
    wrong_source["source"] = "OtherSource"
    with pytest.raises(TemporalEvidenceError, match="unsupported inspector source"):
        convert_inspection_report(wrong_source, evaluation_time=REFERENCE_TIME)

    wrong_version = inspected_report()
    wrong_version["tool_version"] = "other-inspector-v1"
    with pytest.raises(TemporalEvidenceError, match="unsupported inspector version"):
        convert_inspection_report(wrong_version, evaluation_time=REFERENCE_TIME)

    wrong_digest = inspected_report()
    wrong_digest["payload"]["raw_payload_sha256"] = "not-a-digest"
    with pytest.raises(TemporalEvidenceError, match="raw_payload_sha256"):
        convert_inspection_report(wrong_digest, evaluation_time=REFERENCE_TIME)

    invalid_timestamp = inspected_report()
    invalid_timestamp["receipt"]["received_at"] = "not-a-timestamp"
    with pytest.raises(TemporalEvidenceError, match="receipt.received_at"):
        convert_inspection_report(invalid_timestamp, evaluation_time=REFERENCE_TIME)


def test_contradictory_pair_identity_fails_closed() -> None:
    report = inspected_report()
    report["payload"]["pairs"][0]["chainId"] = "other-chain"

    with pytest.raises(TemporalEvidenceError, match="contradicts request chain"):
        convert_inspection_report(report, evaluation_time=REFERENCE_TIME)


def test_conversion_is_immutable_and_deterministic() -> None:
    report = inspected_report()
    before = deepcopy(report)
    first = convert_inspection_report(report, evaluation_time=REFERENCE_TIME)
    second = convert_inspection_report(report, evaluation_time=REFERENCE_TIME)

    assert report == before
    assert first == second
    assert temporal_evidence_digest(first.records[0]) == temporal_evidence_digest(
        second.records[0]
    )
    assert canonical_json(first.as_mapping()) == canonical_json(second.as_mapping())


def test_temporal_evidence_does_not_admit_p08_or_downstream_behavior() -> None:
    result = convert_inspection_report(
        inspected_report(),
        evaluation_time=REFERENCE_TIME,
    )

    assert result.p08_acceptance == "NOT_ATTEMPTED"
    assert all(record.source_observed_at is None for record in result.records)
    assert not hasattr(result.records[0], "accepted")
    assert "decision" not in result.as_mapping()
    assert "eligibility" not in result.as_mapping()


def test_report_raw_digest_is_preserved_not_recomputed_from_missing_raw_bytes() -> None:
    report = inspected_report()
    expected = report["payload"]["raw_payload_sha256"]

    result = convert_inspection_report(report, evaluation_time=REFERENCE_TIME)

    assert result.raw_payload_digest == expected
    assert result.records[0].raw_payload_digest == expected
    assert hashlib.sha256(b"not-the-report-bytes").hexdigest() != expected