"""Offline-only fixtures: addresses are syntactic identities, not a real pool."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import localcontext
import hashlib
import json
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.data import coingecko_onchain_ohlcv as module
from core.data.coingecko_onchain_ohlcv import (
    OhlcvOutcome, OhlcvRequest, OhlcvResponse, map_pool_ohlcv,
    prepare_authenticated_request, PROVIDER_ID,
)
from core.data.contracts import FreshnessPolicy
from core.data.market_observations import P02T07PredecessorContext
from tests.test_materialization import discovery, discovery_boundary, materializer, process


TOKEN = "So11111111111111111111111111111111111111112"
QUOTE = "11111111111111111111111111111111"
POOL = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
REFERENCE = datetime(2026, 8, 12, 12, 5, 5, tzinfo=timezone.utc)
FRESHNESS = FreshnessPolicy(stale_after=timedelta(minutes=4))
FIXTURE = Path(__file__).parent / "fixtures/coingecko_onchain/pool_ohlcv.json"


@pytest.fixture(autouse=True)
def prohibit_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network forbidden in offline tests")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def request(**changes):
    return replace(OhlcvRequest(
        "solana", TOKEN, POOL, TOKEN, QUOTE, REFERENCE,
        timedelta(seconds=10), 16384,
    ), **changes)


def predecessor(token=TOKEN):
    # Real discovery/materialization processors; no fabricated accepted T07/T09.
    runner = materializer()
    result = process(runner, discovery(discovery_boundary(), token_identity=token))
    assert result.current_view_present
    return P02T07PredecessorContext(
        runner.snapshot(), runner.context.initial_state.state_version,
        runner.context.initial_state.state_digest(), runner.context.materializer_contract_version,
    )


def response(req=None, body=None, **changes):
    req = req or request()
    return replace(OhlcvResponse(
        req, REFERENCE - timedelta(seconds=4), REFERENCE - timedelta(seconds=1),
        FIXTURE.read_bytes() if body is None else body,
    ), **changes)


def payload():
    return json.loads(FIXTURE.read_bytes())


def encode(value):
    return json.dumps(value, separators=(",", ":")).encode()


def mapped(body=None, req=None, resp=None, **changes):
    req = req or request()
    kwargs = dict(request=req, response=resp or response(req, body), predecessor=predecessor(req.token_mint), freshness_policy=FRESHNESS)
    kwargs.update(changes)
    return map_pool_ohlcv(**kwargs)


def test_real_p02_chain_preserves_all_three_observations_and_provenance():
    result = mapped()
    assert result.outcome is OhlcvOutcome.PRODUCED, result
    assert [x.value for x in result.observations] == ["10", "11", "13"]
    assert result.provenance.response_digest == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert result.provenance.raw_timestamps == (1786536240, 1786536180, 1786536120)
    assert result.provenance.returned_base == TOKEN
    assert result.provenance.returned_quote == QUOTE
    assert result.provenance.provider_request_id == "synthetic-offline-fixture-v1"
    assert result.provenance.request.parameters == request().parameters
    assert len({item.upstream.state_digest for item in result.observations}) == 3
    for item in result.observations:
        assert item.accepted
        assert item.source_id == PROVIDER_ID
        assert item.token_identity == TOKEN
        assert item.market_subject_id == POOL
        assert item.provenance.source_event_id.endswith(str(item.sequence))
        assert item.provenance.observation_metadata["quote_asset"] == "USD"
        assert item.provenance.source_metadata["response_digest"] == result.provenance.response_digest
        assert item.upstream.state_entry.evidence.predecessor_state_digest == predecessor().state_digest
        assert item.received_time == response().received_at
        assert item.data_age == REFERENCE - item.observation_time


def test_quote_token_is_explicitly_selected_not_inverted_locally():
    result = mapped(req=request(token_mint=QUOTE))
    assert result.outcome is OhlcvOutcome.PRODUCED
    assert all(item.token_identity == QUOTE for item in result.observations)
    assert dict(result.provenance.request.parameters)["token"] == QUOTE


def test_replay_is_deterministic_and_does_not_mutate_predecessor():
    upstream = predecessor()
    snapshot = upstream.snapshot
    left = mapped(predecessor=upstream)
    right = mapped(predecessor=upstream)
    assert left == right
    assert upstream.snapshot == snapshot
    with pytest.raises(FrozenInstanceError):
        left.retryable = True
    with pytest.raises(TypeError):
        left.observations[0].provenance.source_metadata["response_digest"] = "changed"


def test_decimal_precision_does_not_depend_on_ambient_context():
    body = FIXTURE.read_bytes().replace(b"13, 100", b"13.123456789012345678901234567890123456789, 100")
    normal = mapped(body)
    with localcontext() as ctx:
        ctx.prec = 2
        small = mapped(body)
    assert small == normal
    assert small.observations[-1].value == "13.123456789012345678901234567890123456789"


@pytest.mark.parametrize("change", [
    {"chain_id": "ethereum"}, {"token_mint": POOL}, {"base_mint": QUOTE},
    {"pool_address": "../pool"}, {"token_mint": TOKEN.lower()},
    {"reference_time": REFERENCE.replace(tzinfo=None)},
    {"timeout": timedelta(0)}, {"timeout": 10}, {"max_response_bytes": True},
    {"max_response_bytes": 0}, {"max_response_bytes": 1048577},
    {"pool_address": "1" * 44},
])
def test_invalid_request_configuration_raises_before_url_construction(change):
    with pytest.raises(ValueError):
        request(**change)


@pytest.mark.parametrize("key", [None, "", "secret\nheader", " spaces ", "x" * 513])
def test_missing_or_unsafe_credentials_fail_without_disclosure(key):
    with pytest.raises(ValueError, match="^AUTHENTICATION_FAILED$"):
        prepare_authenticated_request(request(), api_key=key)


def test_credential_only_enters_header_never_url_repr_result_digest_or_logs(caplog):
    fake_secret = "offline-only-test-credential"
    prepared = prepare_authenticated_request(request(), api_key=fake_secret)
    assert prepared.headers["x-cg-demo-api-key"] == fake_secret
    assert prepared.follow_redirects is False
    result = mapped()
    assert fake_secret not in repr(prepared) + request().url + repr(result) + caplog.text
    assert result.provenance.response_digest == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert prepare_authenticated_request(request(), api_key="other-test-value").request == prepared.request
    with pytest.raises(TypeError):
        prepared.headers["x-cg-demo-api-key"] = "new"


@pytest.mark.parametrize("status,outcome,retryable", [
    (401, OhlcvOutcome.AUTHENTICATION_FAILED, False),
    (403, OhlcvOutcome.AUTHENTICATION_FAILED, False),
    (429, OhlcvOutcome.RATE_LIMITED, True),
    (500, OhlcvOutcome.SOURCE_UNAVAILABLE, True),
    (302, OhlcvOutcome.SOURCE_UNAVAILABLE, True),
    (404, OhlcvOutcome.SOURCE_UNAVAILABLE, True),
    (True, OhlcvOutcome.INVALID_RESPONSE, False),
    (None, OhlcvOutcome.INVALID_RESPONSE, False),
])
def test_http_failures_return_no_partial_data_or_error_body(status, outcome, retryable):
    result = mapped(resp=response(body=b"untrusted-error-text", http_status=status))
    assert result.outcome is outcome
    assert result.retryable is retryable
    assert result.observations == ()
    assert "untrusted-error-text" not in repr(result)
    assert result.provenance.response_digest is None


@pytest.mark.parametrize("failure", [OhlcvOutcome.TIMEOUT, OhlcvOutcome.SOURCE_UNAVAILABLE, OhlcvOutcome.RESPONSE_TOO_LARGE, OhlcvOutcome.AUTHENTICATION_FAILED])
def test_explicit_transport_failures(failure):
    result = mapped(resp=response(http_status=None, body=b"", transport_failure=failure))
    assert result.outcome is failure
    assert result.observations == ()


def test_elapsed_timeout_and_oversized_body_fail_before_parsing():
    assert mapped(resp=response(started_at=REFERENCE - timedelta(minutes=1))).outcome is OhlcvOutcome.TIMEOUT
    req = request(max_response_bytes=5)
    result = mapped(req=req, body=b"123456")
    assert result.outcome is OhlcvOutcome.RESPONSE_TOO_LARGE
    assert result.provenance.response_digest is None


@pytest.mark.parametrize("changes", [
    {"received_at": REFERENCE + timedelta(seconds=1)},
    {"started_at": REFERENCE},
    {"received_at": REFERENCE.replace(tzinfo=None)},
])
def test_receipt_timeline_fails_closed(changes):
    result = mapped(resp=response(**changes))
    assert result.outcome is OhlcvOutcome.TEMPORAL_INVALID
    assert not result.observations


def test_request_binding_includes_pool_token_network_and_cutoff():
    for other in (request(pool_address=QUOTE), request(token_mint=QUOTE), request(reference_time=REFERENCE + timedelta(minutes=1))):
        assert mapped(resp=response(other)).outcome is OhlcvOutcome.IDENTITY_MISMATCH


@pytest.mark.parametrize("part", ["base", "quote"])
def test_composition_contradiction_fails_closed(part):
    value = payload()
    value["meta"][part]["address"] = POOL
    assert mapped(encode(value)).outcome is OhlcvOutcome.IDENTITY_MISMATCH


@pytest.mark.parametrize("body", [b"", b"{", b"null", b"[]", b"\xff", b'{"data":1,"data":2,"meta":{}}', b"[" * 2000])
def test_malformed_or_ambiguous_json_fails_closed(body):
    assert mapped(body).outcome is OhlcvOutcome.INVALID_RESPONSE


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity", "true", "null", '"13"', "1e999999", "1e-999999", "-1", "0"])
def test_invalid_numeric_material_fails_closed(raw):
    body = FIXTURE.read_bytes().replace(b"13, 100", (raw + ", 100").encode())
    assert mapped(body).outcome is OhlcvOutcome.INVALID_RESPONSE


@pytest.mark.parametrize("index,value", [(1, 15), (2, 9), (3, 12), (5, -1)])
def test_ohlcv_invariants(index, value):
    body = payload()
    body["data"]["attributes"]["ohlcv_list"][0][index] = value
    assert mapped(encode(body)).outcome is OhlcvOutcome.INVALID_RESPONSE


@pytest.mark.parametrize("mode,outcome", [
    ("forming", OhlcvOutcome.TEMPORAL_INVALID),
    ("future", OhlcvOutcome.TEMPORAL_INVALID),
    ("fraction", OhlcvOutcome.TEMPORAL_INVALID),
    ("unaligned", OhlcvOutcome.TEMPORAL_INVALID),
    ("duplicate", OhlcvOutcome.TEMPORAL_INVALID),
    ("contradictory", OhlcvOutcome.CONTRADICTORY_EVIDENCE),
    ("gap", OhlcvOutcome.INSUFFICIENT_HISTORY),
    ("missing", OhlcvOutcome.INSUFFICIENT_HISTORY),
    ("empty", OhlcvOutcome.INSUFFICIENT_HISTORY),
    ("extra", OhlcvOutcome.INVALID_RESPONSE),
    ("unordered", OhlcvOutcome.TEMPORAL_INVALID),
])
def test_temporal_failures(mode, outcome):
    body = payload()
    rows = body["data"]["attributes"]["ohlcv_list"]
    if mode == "forming": rows[0][0] = request().cutoff
    elif mode == "future": rows[0][0] = request().cutoff + 60
    elif mode == "fraction": rows[0][0] += 0.5
    elif mode == "unaligned": rows[0][0] += 1
    elif mode == "duplicate": rows[0] = rows[1][:]
    elif mode == "contradictory": rows[0][0] = rows[1][0]
    elif mode == "gap": rows[-1][0] -= 60
    elif mode == "missing": rows.pop()
    elif mode == "empty": rows.clear()
    elif mode == "extra": rows.append(rows[-1][:])
    elif mode == "unordered": rows[0], rows[1] = rows[1], rows[0]
    result = mapped(encode(body))
    assert result.outcome is outcome
    assert result.observations == ()


def test_ascending_and_provider_descending_order_are_supported():
    body = payload()
    body["data"]["attributes"]["ohlcv_list"].reverse()
    assert [x.value for x in mapped(encode(body)).observations] == ["10", "11", "13"]


def test_freshness_is_explicit_and_never_relaxed():
    for policy in (None, FreshnessPolicy(), FreshnessPolicy(timedelta(seconds=60))):
        result = mapped(freshness_policy=policy)
        assert result.outcome is OhlcvOutcome.UPSTREAM_ADMISSION_REJECTED
        assert not result.observations


def test_unknown_candidate_fails_actual_p02_admission():
    result = mapped(predecessor=replace(predecessor(), snapshot=()))
    assert result.outcome is OhlcvOutcome.UPSTREAM_ADMISSION_REJECTED
    assert result.reason_codes == ("P02_T07_TOKEN_NOT_CURRENT",)


def test_cutoff_and_replay_are_timezone_independent():
    req = request(reference_time=REFERENCE.astimezone(timezone(timedelta(hours=7))))
    assert req == request()
    assert req.cutoff == 1786536300
    assert mapped(req=req) == mapped()


def test_closed_candle_must_also_be_available_at_receipt():
    resp = response(
        started_at=REFERENCE - timedelta(seconds=9),
        received_at=REFERENCE - timedelta(seconds=6),
    )
    assert mapped(resp=resp).outcome is OhlcvOutcome.TEMPORAL_INVALID


def test_extreme_exponent_fails_closed_without_decimal_exception():
    body = FIXTURE.read_bytes().replace(b"13, 100", b"1e99999999999999999999999999, 100")
    assert mapped(body).outcome is OhlcvOutcome.INVALID_RESPONSE


@pytest.mark.parametrize("case", ["wrong-type", "attributes", "root", "row", "meta", "request-id", "volume-string"])
def test_unexpected_response_structures_fail_closed(case):
    value = payload()
    if case == "wrong-type": value["data"]["type"] = "other"
    elif case == "attributes": value["data"]["attributes"]["other"] = 1
    elif case == "root": value["other"] = 1
    elif case == "row": value["data"]["attributes"]["ohlcv_list"][0].append(1)
    elif case == "meta": value["meta"]["base"] = []
    elif case == "request-id": value["data"]["id"] = "bad\nrequest"
    elif case == "volume-string": value["data"]["attributes"]["ohlcv_list"][0][5] = "100"
    assert mapped(encode(value)).outcome is OhlcvOutcome.INVALID_RESPONSE


@pytest.mark.parametrize("processor,method", [("MarketObservationProcessor", "process"), ("MarketStateMaterializer", "process"), ("MarketIntelligenceProcessor", "process")])
def test_upstream_rejection_is_atomic_even_on_third_candle(monkeypatch, processor, method):
    cls = getattr(module, processor)
    original = getattr(cls, method)
    count = 0
    def reject_third(self, *args, **kwargs):
        nonlocal count
        count += 1
        if count == 3:
            return SimpleNamespace(accepted=False, outcome=OhlcvOutcome.UPSTREAM_ADMISSION_REJECTED)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(cls, method, reject_third)
    result = mapped()
    assert count == 3
    assert result.outcome is OhlcvOutcome.UPSTREAM_ADMISSION_REJECTED
    assert result.observations == ()
