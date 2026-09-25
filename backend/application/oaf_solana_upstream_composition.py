"""Canonical P02/P03 composition for one trusted OAF Solana snapshot."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping
from core.data.contracts import DataQuality, FreshnessPolicy
from core.data.discovery import DiscoveryContext, DiscoveryKind, DiscoveryOutcome, DiscoveryObservation, TokenDiscoveryBoundary
from core.data.materialization import MaterializationContext, MaterializationOutcome, TokenUniverseMaterializer
from core.data.market_observations import P02T07PredecessorContext
from core.data.solana_oaf_source import SolanaMintSnapshot
from core.risk.safety_evidence import P02StateReference, SafetyDomain, SafetyEvidenceCollection, SafetyProvenance, SafetyStatus, TokenSafetyEvidence, DerivedEligibilityOutput
from core.risk.safety_evaluation import SafetyEvaluationResult, evaluate_safety_evidence
from core.risk.safety_eligibility import derive_token_eligibility

P01_OAF_UPSTREAM_COMPOSITION_VERSION = "p01-oaf-01-upstream-composition-v1"

class OafUpstreamCompositionError(ValueError):
    pass

@dataclass(frozen=True)
class OafCanonicalUpstreamResult:
    token_mint: str
    predecessor: P02T07PredecessorContext
    safety_evaluation: SafetyEvaluationResult
    eligibility: DerivedEligibilityOutput
    source_slots: tuple[int, ...]
    contract_version: str = P01_OAF_UPSTREAM_COMPOSITION_VERSION

class OafSolanaCanonicalComposer:
    def compose(self, *, snapshot: SolanaMintSnapshot, processing_time: datetime, reference_time: datetime, evaluation_time: datetime, freshness_policy: FreshnessPolicy, evaluation_id: str, max_top_holder_fraction: float) -> OafCanonicalUpstreamResult:
        for name, value in (("processing_time", processing_time), ("reference_time", reference_time), ("evaluation_time", evaluation_time)):
            _require_aware(value, name)
        if not isinstance(snapshot, SolanaMintSnapshot): raise OafUpstreamCompositionError("snapshot must be a SolanaMintSnapshot")
        if not isinstance(freshness_policy, FreshnessPolicy): raise OafUpstreamCompositionError("freshness_policy is required")
        if not isinstance(evaluation_id, str) or not evaluation_id.strip(): raise OafUpstreamCompositionError("evaluation_id is required")
        if isinstance(max_top_holder_fraction, bool) or not isinstance(max_top_holder_fraction, (int,float)) or not 0 <= float(max_top_holder_fraction) <= 1: raise OafUpstreamCompositionError("max_top_holder_fraction must be between 0 and 1")
        observations=(snapshot.mint_account,snapshot.largest_accounts,snapshot.token_supply)
        if any(x.observed_at > reference_time for x in observations): raise OafUpstreamCompositionError("source observation is newer than reference_time")
        predecessor,p02_ref=self._compose_p02(snapshot,processing_time,reference_time,freshness_policy,evaluation_id)
        evidence=self._compose_p03(snapshot,reference_time,freshness_policy,p02_ref,float(max_top_holder_fraction))
        evaluation=evaluate_safety_evidence(SafetyEvidenceCollection.from_evidence(evidence),evaluation_timestamp=evaluation_time)
        eligibility=derive_token_eligibility(evaluation)
        if evaluation.token_identity != snapshot.token_mint: raise OafUpstreamCompositionError("P03 token identity mismatch")
        return OafCanonicalUpstreamResult(snapshot.token_mint,predecessor,evaluation,eligibility,tuple(sorted({x.slot for x in observations})))

    @staticmethod
    def _compose_p02(snapshot,processing_time,reference_time,freshness_policy,evaluation_id):
        src=snapshot.mint_account
        result=TokenDiscoveryBoundary(context=DiscoveryContext(freshness_policy=freshness_policy,contract_version="p02-t04-v1")).process(
            DiscoveryObservation(source_id=src.source_id,kind=DiscoveryKind.DISCOVERED,token_identity=snapshot.token_mint,chain_id="solana",observation_time=src.observed_at,discovery_time=src.observed_at,received_time=src.observed_at,source_event_id=f"solana-slot:{src.slot}:mint:{snapshot.token_mint}",discovery_reason="EXPLICIT_FINALIZED_MINT_VERIFICATION",metadata={"mint":snapshot.token_mint},source_metadata={"rpc_method":src.method,"slot":src.slot,"source_version":src.source_version}),
            processing_time=processing_time,reference_time=reference_time)
        if result.outcome is not DiscoveryOutcome.ACCEPTED or not result.accepted or not result.published_as_current: raise OafUpstreamCompositionError("P02 discovery rejected: "+",".join(result.reasons))
        mat=TokenUniverseMaterializer(context=MaterializationContext(evaluation_id=evaluation_id))
        mr=mat.process(result,processing_time=processing_time,reference_time=reference_time)
        if mr.outcome is not MaterializationOutcome.MATERIALIZED or not mr.current_view_present: raise OafUpstreamCompositionError("P02 materialization rejected: "+",".join(mr.reasons))
        digest=mat.state.state_digest()
        pred=P02T07PredecessorContext(snapshot=mat.snapshot(),state_version=mat.state.state_version,state_digest=digest,materializer_contract_version=mat.state.materializer_contract_version,evaluation_id=evaluation_id)
        if not pred.contains("solana",snapshot.token_mint): raise OafUpstreamCompositionError("P02 predecessor does not contain selected mint")
        return pred,P02StateReference(state_version=pred.state_version,state_digest=pred.state_digest,contract_version=pred.materializer_contract_version,evaluation_id=pred.evaluation_id)

    @staticmethod
    def _compose_p03(snapshot,reference_time,freshness_policy,p02_ref,max_fraction):
        info=_mint_info(snapshot.mint_account.result)
        age,fresh=_age(snapshot.mint_account.observed_at,reference_time,freshness_policy)
        clear=info.get("mintAuthority") is None and info.get("freezeAuthority") is None
        authority=_evidence(snapshot,snapshot.mint_account,SafetyDomain.MINT_FREEZE_AUTHORITY,SafetyStatus.PASS if clear else SafetyStatus.FAIL,age,fresh,p02_ref,{"mint_authority_present":info.get("mintAuthority") is not None,"freeze_authority_present":info.get("freezeAuthority") is not None},() if clear else ("MINT_OR_FREEZE_AUTHORITY_PRESENT",))
        fraction=_fraction(snapshot)
        holder_age=max(reference_time-snapshot.largest_accounts.observed_at,reference_time-snapshot.token_supply.observed_at)
        holder_fresh=_fresh(holder_age,freshness_policy)
        passed=fraction <= max_fraction
        holders=_evidence(snapshot,snapshot.largest_accounts,SafetyDomain.TOP_HOLDER_CONCENTRATION,SafetyStatus.PASS if passed else SafetyStatus.FAIL,holder_age,holder_fresh,p02_ref,{"top_holder_fraction":fraction,"max_top_holder_fraction":max_fraction,"supply_slot":snapshot.token_supply.slot},() if passed else ("TOP_HOLDER_CONCENTRATION_EXCEEDS_POLICY",))
        return authority,holders

def _evidence(snapshot,obs,domain,status,data_age,freshness,p02_ref,context,reasons):
    effective=status if freshness is DataQuality.VALID else SafetyStatus.UNKNOWN
    return TokenSafetyEvidence(chain_id="solana",token_identity=snapshot.token_mint,domain=domain,status=effective,source_id=obs.source_id,observed_at=obs.observed_at,quality=DataQuality.VALID,freshness_status=freshness,data_age=data_age,provenance=SafetyProvenance(source_id=obs.source_id,method=obs.method,observed_at=obs.observed_at,metadata={"slot":obs.slot,"source_version":obs.source_version}),evidence_reference=f"{obs.source_id}:{obs.slot}:{domain.value}:{snapshot.token_mint}",evidence_context=dict(context),p02_reference=p02_ref,reason_codes=("STALE_SOURCE_EVIDENCE",) if effective is SafetyStatus.UNKNOWN else reasons)

def _mint_info(value):
    try: info=value["data"]["parsed"]["info"]
    except (KeyError,TypeError): raise OafUpstreamCompositionError("mint parsed info is unavailable") from None
    if not isinstance(info,Mapping): raise OafUpstreamCompositionError("mint parsed info is invalid")
    return info

def _fraction(snapshot):
    supply=snapshot.token_supply.result; holders=snapshot.largest_accounts.result
    if not isinstance(supply,Mapping) or not isinstance(holders,list): raise OafUpstreamCompositionError("holder/supply source shape is invalid")
    amount=supply.get("amount")
    if not isinstance(amount,str) or not amount.isdigit() or int(amount)<=0: raise OafUpstreamCompositionError("token supply amount is invalid")
    total=int(amount); top=0
    for item in holders:
        if not isinstance(item,Mapping) or not isinstance(item.get("amount"),str) or not item["amount"].isdigit(): raise OafUpstreamCompositionError("largest account amount is invalid")
        top+=int(item["amount"])
    if top>total: raise OafUpstreamCompositionError("largest-account amounts exceed total supply")
    return top/total

def _age(observed,reference,policy):
    age=reference-observed
    if age<timedelta(0): raise OafUpstreamCompositionError("source observation is future-dated")
    return age,_fresh(age,policy)

def _fresh(age,policy):
    return DataQuality.STALE if policy.stale_after is not None and age>policy.stale_after else DataQuality.VALID

def _require_aware(value,name):
    if not isinstance(value,datetime) or value.tzinfo is None or value.utcoffset() is None: raise OafUpstreamCompositionError(f"{name} must be timezone-aware")
