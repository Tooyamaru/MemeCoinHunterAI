import ast
from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path
import socket

import pytest

from core.data.coingecko_onchain_ohlcv import OhlcvOutcome
from core.opportunity.canonical_evidence_producer import produce_canonical_p04_to_p05
from core.risk.safety_eligibility import derive_token_eligibility
from core.risk.safety_evidence import SafetyDomain, SafetyStatus
from core.signals.price_direction_policy import derive_price_direction, POLICY_VERSION
from tests.test_coingecko_onchain_ohlcv import (
    request, response, predecessor, payload, encode, FRESHNESS, TOKEN, REFERENCE,
)
from tests.test_safety_eligibility import _evaluation


def derive(body=None, **changes):
    kwargs = dict(request=request(), response=response(body=body), predecessor=predecessor(), freshness_policy=FRESHNESS)
    kwargs.update(changes)
    return derive_price_direction(**kwargs)


@pytest.mark.parametrize("price,status,reason", [
    (13, "RISING", "PRICE_CLOSE_INCREASED"),
    (10, "FALLING", "PRICE_CLOSE_DECREASED"),
    (11, "FLAT", "PRICE_CLOSE_UNCHANGED"),
])
def test_exact_direction_and_non_predictive_confidence(price, status, reason):
    body = payload()
    body["data"]["attributes"]["ohlcv_list"][0][4] = price
    result = derive(encode(body))
    assert result.outcome is OhlcvOutcome.PRODUCED
    signal, = result.signal_evidence.evidence
    assert signal.signal_type == "PRICE_DIRECTION_1M"
    assert signal.signal_status == status
    assert signal.reason_codes == (reason,)
    assert signal.confidence == 1.0
    assert signal.observed_at == result.market.observations[-1].observation_time
    assert signal.provenance.metadata["confidence_meaning"] == "input_completeness_not_prediction"
    assert signal.provenance.method == POLICY_VERSION
    assert signal.provenance.metadata["observation_ids"] == tuple(o.observation_id for o in result.market.observations)


def test_replay_and_digest_bind_response_and_accepted_observations():
    first = derive()
    second = derive()
    assert first == second
    assert first.signal_evidence.representation_digest == second.signal_evidence.representation_digest
    body = payload()
    body["data"]["id"] = "provider-revision"
    third = derive(encode(body))
    assert first.signal_evidence.evidence[0].evidence_reference != third.signal_evidence.evidence[0].evidence_reference
    assert first.market.observations[-1].value == third.market.observations[-1].value


def test_exact_comparison_survives_low_decimal_precision():
    body = encode(payload()).replace(b",13,100", b",11.0000000000000000000000000000000000000001,100")
    with localcontext() as ctx:
        ctx.prec = 2
        result = derive(body)
    assert result.signal_evidence.evidence[0].signal_status == "RISING"


@pytest.mark.parametrize("failure", [
    OhlcvOutcome.TIMEOUT, OhlcvOutcome.SOURCE_UNAVAILABLE,
    OhlcvOutcome.AUTHENTICATION_FAILED, OhlcvOutcome.RESPONSE_TOO_LARGE,
])
def test_failure_never_produces_signal(failure):
    result = derive(response=response(transport_failure=failure))
    assert result.outcome is failure
    assert result.signal_evidence is None
    assert result.market.observations == ()


def test_bad_history_and_unadmitted_token_cannot_become_signals():
    body = payload()
    body["data"]["attributes"]["ohlcv_list"].pop()
    assert derive(encode(body)).signal_evidence is None
    assert derive(predecessor=replace(predecessor(), snapshot=())).signal_evidence is None


def test_end_to_end_existing_canonical_p04_p05_without_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("network forbidden")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    produced = derive()
    eligibility = derive_token_eligibility(replace(
        _evaluation({SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.PASS}),
        token_identity=TOKEN,
    ))
    result = produce_canonical_p04_to_p05(
        candidate_id="offline-coingecko-fixture", chain_id="solana", token_identity=TOKEN,
        reference_time=REFERENCE, eligibility=eligibility,
        signal_evidence=produced.signal_evidence, market_observations=produced.market.observations,
        freshness_policy=FRESHNESS,
    )
    assert result.candidate_state == "VALID"
    features = {item.feature_id: item for item in result.feature_snapshots}
    with localcontext() as ctx:
        ctx.prec = 50
        assert features["price_velocity"].value == Decimal(2) / Decimal(60)
    assert features["price_acceleration"].value > 0
    assert result.signal_snapshot.evidence_references == (produced.signal_evidence.evidence[0].evidence_reference,)
    unknown = derive_token_eligibility(replace(
        _evaluation({SafetyDomain.LIQUIDITY_QUALITY: SafetyStatus.UNKNOWN}), token_identity=TOKEN,
    ))
    with pytest.raises(ValueError, match="viability gate is closed"):
        produce_canonical_p04_to_p05(
            candidate_id="blocked", chain_id="solana", token_identity=TOKEN,
            reference_time=REFERENCE, eligibility=unknown,
            signal_evidence=produced.signal_evidence, market_observations=produced.market.observations,
            freshness_policy=FRESHNESS,
        )


def test_modules_have_no_network_execution_persistence_or_clock_dependencies():
    root = Path(__file__).parents[1]
    allowed = {"__future__", "dataclasses", "datetime", "decimal", "enum", "hashlib", "json", "re", "types", "typing", "urllib.parse", "core.data.contracts", "core.data.market_intelligence", "core.data.market_observations", "core.data.market_state", "core.data.coingecko_onchain_ohlcv", "core.signals.signal_evidence"}
    for file in ("core/data/coingecko_onchain_ohlcv.py", "core/signals/price_direction_policy.py"):
        tree = ast.parse((root / file).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(name.name in allowed for name in node.names)
            if isinstance(node, ast.ImportFrom):
                assert node.module in allowed
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"now", "utcnow", "urlopen", "connect", "write_text", "write_bytes"}
