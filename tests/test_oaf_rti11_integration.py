from datetime import datetime, timedelta, timezone

import pytest

from backend.application.market_to_opportunity_composition import (
    MarketToOpportunityCompositionOutcome,
    P01Rti11CompositionResult,
)
from backend.application.oaf_rti11_integration import (
    OafRti11IntegrationError,
    OafRti11IntegrationRequest,
    OafRti11IntegrationService,
)
from backend.application.oaf_solana_upstream_composition import OafSolanaCanonicalComposer
from core.data.coingecko_onchain_orchestration import ExactPoolDiagnosticTarget
from core.data.contracts import FreshnessPolicy
from core.data.solana_oaf_source import SolanaMintSnapshot, SolanaRpcObservation

MINT = "So11111111111111111111111111111111111111112"
OTHER = "11111111111111111111111111111111"
POOL = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
T = datetime(2026, 9, 25, 6, 0, tzinfo=timezone.utc)
FRESHNESS = FreshnessPolicy(stale_after=timedelta(minutes=5))


def _snapshot():
    mint = {
        "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "data": {
            "parsed": {
                "type": "mint",
                "info": {
                    "mintAuthority": None,
                    "freezeAuthority": None,
                    "decimals": 9,
                },
            }
        },
    }
    return SolanaMintSnapshot(
        MINT,
        SolanaRpcObservation("getAccountInfo", 10, T, mint),
        SolanaRpcObservation(
            "getTokenLargestAccounts", 11, T, [{"amount": "100", "decimals": 9}]
        ),
        SolanaRpcObservation("getTokenSupply", 12, T, {"amount": "1000", "decimals": 9}),
    )


def _upstream():
    reference = T + timedelta(seconds=5)
    return OafSolanaCanonicalComposer().compose(
        snapshot=_snapshot(),
        processing_time=reference,
        reference_time=reference,
        evaluation_time=reference,
        freshness_policy=FRESHNESS,
        evaluation_id="oaf-rti11-test",
        max_top_holder_fraction=0.2,
    )


def _target(token=MINT):
    return ExactPoolDiagnosticTarget(
        chain_id="solana",
        token_mint=token,
        pool_address=POOL,
        base_mint=token,
        quote_mint=OTHER,
        target_reference_id="caller:exact-pool:1",
        target_reference_digest="a" * 64,
        target_contract_version="exact-pool-target-v1",
    )


def _request(**changes):
    reference = T + timedelta(seconds=5)
    values = dict(
        candidate_id="candidate:explicit:1",
        upstream=_upstream(),
        target=_target(),
        reference_time=reference,
        timeout=timedelta(seconds=10),
        max_response_bytes=16384,
        freshness_policy=FRESHNESS,
        processing_time=reference,
        evaluated_at=reference,
        evaluation_id="oaf-rti11-test",
        analytical_context={"source": "operator-facade"},
    )
    values.update(changes)
    return OafRti11IntegrationRequest(**values)


def test_delegates_exact_canonical_p02_p03_objects_once():
    calls = []

    class FakeRti11:
        def compose(self, request):
            calls.append(request)
            return P01Rti11CompositionResult(
                request=request,
                outcome=MarketToOpportunityCompositionOutcome.COMPOSITION_UNAVAILABLE,
                reason_codes=("TEST_STOP",),
            )

    request = _request()
    result = OafRti11IntegrationService(rti11=FakeRti11()).compose(request)

    assert len(calls) == 1
    exact = calls[0]
    assert exact.predecessor is request.upstream.predecessor
    assert exact.safety_evaluation is request.upstream.safety_evaluation
    assert exact.eligibility is request.upstream.eligibility
    assert exact.target is request.target
    assert result.request is exact


def test_target_identity_mismatch_fails_before_rti11():
    calls = 0

    class FakeRti11:
        def compose(self, request):
            nonlocal calls
            calls += 1
            raise AssertionError("RTI-11 must not run")

    with pytest.raises(OafRti11IntegrationError, match="target token"):
        OafRti11IntegrationService(rti11=FakeRti11()).compose(
            _request(target=_target(OTHER))
        )
    assert calls == 0


def test_noncanonical_rti11_result_is_rejected():
    class FakeRti11:
        def compose(self, request):
            return object()

    with pytest.raises(OafRti11IntegrationError, match="noncanonical"):
        OafRti11IntegrationService(rti11=FakeRti11()).compose(_request())
