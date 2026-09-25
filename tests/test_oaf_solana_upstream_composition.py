from datetime import datetime, timedelta, timezone

import pytest

from core.data.contracts import FreshnessPolicy
from core.data.solana_oaf_source import SolanaMintSnapshot, SolanaRpcObservation
from core.risk.safety_evidence import EligibilityStatus, SafetyDomain, SafetyStatus
from backend.application.oaf_solana_upstream_composition import (
    OafSolanaCanonicalComposer,
    OafUpstreamCompositionError,
)

MINT="So11111111111111111111111111111111111111112"
T=datetime(2026,9,25,4,0,tzinfo=timezone.utc)

def snapshot(authority=None,freeze=None,largest="100",supply="1000"):
    mint={"owner":"TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA","data":{"parsed":{"type":"mint","info":{"mintAuthority":authority,"freezeAuthority":freeze,"decimals":9}}}}
    return SolanaMintSnapshot(MINT,SolanaRpcObservation("getAccountInfo",10,T,mint),SolanaRpcObservation("getTokenLargestAccounts",11,T,[{"amount":largest,"decimals":9}]),SolanaRpcObservation("getTokenSupply",12,T,{"amount":supply,"decimals":9}))

def compose(s, reference=T+timedelta(seconds=5), stale=timedelta(minutes=1), threshold=.2):
    return OafSolanaCanonicalComposer().compose(snapshot=s,processing_time=reference,reference_time=reference,evaluation_time=reference,freshness_policy=FreshnessPolicy(stale_after=stale),evaluation_id="oaf-test",max_top_holder_fraction=threshold)

def test_composes_exact_p02_identity_and_paired_p03():
    r=compose(snapshot())
    assert r.predecessor.contains("solana",MINT)
    assert r.safety_evaluation.token_identity==MINT
    assert r.eligibility.status is EligibilityStatus.ELIGIBLE
    assert r.source_slots==(10,11,12)
    assert r.safety_evaluation.domain_results[SafetyDomain.MINT_FREEZE_AUTHORITY] is SafetyStatus.PASS
    assert r.safety_evaluation.domain_results[SafetyDomain.TOP_HOLDER_CONCENTRATION] is SafetyStatus.PASS

def test_authority_or_concentration_failure_is_not_overridden():
    r=compose(snapshot(authority="authority",largest="900"),threshold=.2)
    assert r.eligibility.status is EligibilityStatus.INELIGIBLE
    assert r.safety_evaluation.domain_results[SafetyDomain.MINT_FREEZE_AUTHORITY] is SafetyStatus.FAIL
    assert r.safety_evaluation.domain_results[SafetyDomain.TOP_HOLDER_CONCENTRATION] is SafetyStatus.FAIL

def test_stale_p02_source_fails_closed_before_p03_and_rti11():
    with pytest.raises(OafUpstreamCompositionError, match="P02 discovery rejected"):
        compose(snapshot(),reference=T+timedelta(minutes=2),stale=timedelta(seconds=30))
