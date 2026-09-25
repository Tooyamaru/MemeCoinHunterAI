"""Canonical P02/P03 composition for one trusted OAF Solana snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping

from core.data.contracts import DataQuality, FreshnessPolicy, RawEvent
from core.data.discovery import (
    DiscoveryContext,
    DiscoveryKind,
    DiscoveryOutcome,
    TokenDiscoveryBoundary,
)
from core.data.discovery_orchestration import DiscoveryToOrchestrationBoundary
from core.data.materialization import (
    MaterializationContext,
    MaterializationOutcome,
    TokenUniverseMaterializer,
)
from core.data.market_observations import P02T07PredecessorContext
from core.data.orchestration import (
    AdapterObservation,
    IngestionContext,
    IngestionOrchestrator,
    ObservationKind,
)
from core.data.solana_oaf_source import SolanaMintSnapshot
from core.risk.safety_evidence import (
    DerivedEligibilityOutput,
    P02StateReference,
    SafetyDomain,
    SafetyEvidenceCollection,
    SafetyProvenance,
    SafetyStatus,
    TokenSafetyEvidence,
)
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
    def compose(
        self,
        *,
        snapshot: SolanaMintSnapshot,
        processing_time: datetime,
        reference_time: datetime,
        evaluation_time: datetime,
        freshness_policy: FreshnessPolicy,
        evaluation_id: str,
        max_top_holder_fraction: float,
    ) -> OafCanonicalUpstreamResult:
        for name, value in (
            ("processing_time", processing_time),
            ("reference_time", reference_time),
            ("evaluation_time", evaluation_time),
        ):
            _require_aware(value, name)
        if not isinstance(snapshot, SolanaMintSnapshot):
            raise OafUpstreamCompositionError("snapshot must be a SolanaMintSnapshot")
        if not isinstance(freshness_policy, FreshnessPolicy):
            raise OafUpstreamCompositionError("freshness_policy is required")
        if not isinstance(evaluation_id, str) or not evaluation_id.strip():
            raise OafUpstreamCompositionError("evaluation_id is required")
        if (
            isinstance(max_top_holder_fraction, bool)
            or not isinstance(max_top_holder_fraction, (int, float))
            or not 0 <= float(max_top_holder_fraction) <= 1
        ):
            raise OafUpstreamCompositionError(
                "max_top_holder_fraction must be between 0 and 1"
            )

        observations = (
            snapshot.mint_account,
            snapshot.largest_accounts,
            snapshot.token_supply,
        )
        if any(item.observed_at > reference_time for item in observations):
            raise OafUpstreamCompositionError(
                "source observation is newer than reference_time"
            )
        if any(item.received_at is None for item in observations):
            raise OafUpstreamCompositionError(
                "trusted Solana receipt time is required separately from source time"
            )

        predecessor, p02_ref = self._compose_p02(
            snapshot,
            processing_time,
            reference_time,
            freshness_policy,
            evaluation_id,
        )
        evidence = self._compose_p03(
            snapshot,
            reference_time,
            freshness_policy,
            p02_ref,
            float(max_top_holder_fraction),
        )
        evaluation = evaluate_safety_evidence(
            SafetyEvidenceCollection.from_evidence(evidence),
            evaluation_timestamp=evaluation_time,
        )
        eligibility = derive_token_eligibility(evaluation)
        if evaluation.token_identity != snapshot.token_mint:
            raise OafUpstreamCompositionError("P03 token identity mismatch")
        return OafCanonicalUpstreamResult(
            snapshot.token_mint,
            predecessor,
            evaluation,
            eligibility,
            tuple(sorted({item.slot for item in observations})),
        )

    @staticmethod
    def _compose_p02(
        snapshot: SolanaMintSnapshot,
        processing_time: datetime,
        reference_time: datetime,
        freshness_policy: FreshnessPolicy,
        evaluation_id: str,
    ):
        src = snapshot.mint_account
        assert src.received_at is not None
        source_event_id = f"solana-slot:{src.slot}:mint:{snapshot.token_mint}"

        # P02-T03 provider-neutral adapter envelope. Ledger block time remains the
        # source event time; HTTP/RPC receipt time is retained separately.
        adapter_observation = AdapterObservation(
            source_id=src.source_id,
            kind=ObservationKind.EVENT,
            observed_time=src.received_at,
            raw_event=RawEvent(
                source_id=src.source_id,
                payload={
                    "discovery_kind": DiscoveryKind.DISCOVERED.value,
                    "token_identity": snapshot.token_mint,
                    "chain_id": "solana",
                    "discovery_reason": "EXPLICIT_FINALIZED_MINT_VERIFICATION",
                    "metadata": {"mint": snapshot.token_mint},
                },
                received_time=src.received_at,
                event_time=src.observed_at,
                source_event_id=source_event_id,
                sequence=src.slot,
                source_metadata={
                    "rpc_method": src.method,
                    "slot": src.slot,
                    "source_version": src.source_version,
                },
            ),
            cursor=src.slot,
            source_metadata={"adapter_contract_version": "p02-t03-v1"},
            correlation_id=source_event_id,
        )

        # P02-T04 canonical discovery owner consumes the T03 adapter envelope.
        discovery = TokenDiscoveryBoundary(
            context=DiscoveryContext(
                freshness_policy=freshness_policy,
                contract_version="p02-t04-v1",
            )
        ).process(
            adapter_observation,
            processing_time=processing_time,
            reference_time=reference_time,
        )
        if (
            discovery.outcome is not DiscoveryOutcome.ACCEPTED
            or not discovery.accepted
            or not discovery.published_as_current
        ):
            raise OafUpstreamCompositionError(
                "P02 discovery rejected: " + ",".join(discovery.reasons)
            )

        # P02-T05 must accept/forward the exact T04 result before T06 may
        # materialize current membership.
        orchestration = DiscoveryToOrchestrationBoundary(
            orchestrator=IngestionOrchestrator(
                context=IngestionContext(
                    freshness_policy=freshness_policy,
                    contract_version="p02-t02-v1",
                )
            )
        ).process(
            discovery,
            processing_time=processing_time,
            reference_time=reference_time,
        )
        if (
            not orchestration.published_as_current
            or orchestration.ingestion_result is None
            or not orchestration.ingestion_result.accepted
        ):
            raise OafUpstreamCompositionError(
                "P02 orchestration rejected: " + ",".join(orchestration.reasons)
            )

        # P02-T06 materializes the same accepted T04 discovery record.
        materializer = TokenUniverseMaterializer(
            context=MaterializationContext(evaluation_id=evaluation_id)
        )
        materialized = materializer.process(
            discovery,
            processing_time=processing_time,
            reference_time=reference_time,
        )
        if (
            materialized.outcome is not MaterializationOutcome.MATERIALIZED
            or not materialized.current_view_present
        ):
            raise OafUpstreamCompositionError(
                "P02 materialization rejected: " + ",".join(materialized.reasons)
            )
        digest = materializer.state.state_digest()
        predecessor = P02T07PredecessorContext(
            snapshot=materializer.snapshot(),
            state_version=materializer.state.state_version,
            state_digest=digest,
            materializer_contract_version=materializer.state.materializer_contract_version,
            evaluation_id=evaluation_id,
        )
        if not predecessor.contains("solana", snapshot.token_mint):
            raise OafUpstreamCompositionError(
                "P02 predecessor does not contain selected mint"
            )
        return predecessor, P02StateReference(
            state_version=predecessor.state_version,
            state_digest=predecessor.state_digest,
            contract_version=predecessor.materializer_contract_version,
            evaluation_id=predecessor.evaluation_id,
        )

    @staticmethod
    def _compose_p03(
        snapshot,
        reference_time,
        freshness_policy,
        p02_ref,
        max_fraction,
    ):
        info = _mint_info(snapshot.mint_account.result)
        age, fresh = _age(
            snapshot.mint_account.observed_at,
            reference_time,
            freshness_policy,
        )
        clear = (
            info.get("mintAuthority") is None
            and info.get("freezeAuthority") is None
        )
        authority = _evidence(
            snapshot,
            snapshot.mint_account,
            SafetyDomain.MINT_FREEZE_AUTHORITY,
            SafetyStatus.PASS if clear else SafetyStatus.FAIL,
            age,
            fresh,
            p02_ref,
            {
                "mint_authority_present": info.get("mintAuthority") is not None,
                "freeze_authority_present": info.get("freezeAuthority") is not None,
            },
            () if clear else ("MINT_OR_FREEZE_AUTHORITY_PRESENT",),
        )
        fraction = _fraction(snapshot)
        holder_age = max(
            reference_time - snapshot.largest_accounts.observed_at,
            reference_time - snapshot.token_supply.observed_at,
        )
        holder_fresh = _fresh(holder_age, freshness_policy)
        passed = fraction <= max_fraction
        holders = _evidence(
            snapshot,
            snapshot.largest_accounts,
            SafetyDomain.TOP_HOLDER_CONCENTRATION,
            SafetyStatus.PASS if passed else SafetyStatus.FAIL,
            holder_age,
            holder_fresh,
            p02_ref,
            {
                "top_holder_fraction": fraction,
                "max_top_holder_fraction": max_fraction,
                "supply_slot": snapshot.token_supply.slot,
            },
            () if passed else ("TOP_HOLDER_CONCENTRATION_EXCEEDS_POLICY",),
        )
        return authority, holders


def _evidence(
    snapshot,
    observation,
    domain,
    status,
    data_age,
    freshness,
    p02_ref,
    context,
    reasons,
):
    effective = status if freshness is DataQuality.VALID else SafetyStatus.UNKNOWN
    return TokenSafetyEvidence(
        chain_id="solana",
        token_identity=snapshot.token_mint,
        domain=domain,
        status=effective,
        source_id=observation.source_id,
        observed_at=observation.observed_at,
        quality=DataQuality.VALID,
        freshness_status=freshness,
        data_age=data_age,
        provenance=SafetyProvenance(
            source_id=observation.source_id,
            method=observation.method,
            observed_at=observation.observed_at,
            metadata={
                "slot": observation.slot,
                "source_version": observation.source_version,
            },
        ),
        evidence_reference=(
            f"{observation.source_id}:{observation.slot}:{domain.value}:"
            f"{snapshot.token_mint}"
        ),
        evidence_context=dict(context),
        p02_reference=p02_ref,
        reason_codes=("STALE_SOURCE_EVIDENCE",)
        if effective is SafetyStatus.UNKNOWN
        else reasons,
    )


def _mint_info(value):
    try:
        info = value["data"]["parsed"]["info"]
    except (KeyError, TypeError):
        raise OafUpstreamCompositionError(
            "mint parsed info is unavailable"
        ) from None
    if not isinstance(info, Mapping):
        raise OafUpstreamCompositionError("mint parsed info is invalid")
    return info


def _fraction(snapshot):
    supply = snapshot.token_supply.result
    holders = snapshot.largest_accounts.result
    if not isinstance(supply, Mapping) or not isinstance(holders, list):
        raise OafUpstreamCompositionError("holder/supply source shape is invalid")
    amount = supply.get("amount")
    if (
        not isinstance(amount, str)
        or not amount.isdigit()
        or int(amount) <= 0
    ):
        raise OafUpstreamCompositionError("token supply amount is invalid")
    total = int(amount)
    top = 0
    for item in holders:
        if (
            not isinstance(item, Mapping)
            or not isinstance(item.get("amount"), str)
            or not item["amount"].isdigit()
        ):
            raise OafUpstreamCompositionError(
                "largest account amount is invalid"
            )
        top += int(item["amount"])
    if top > total:
        raise OafUpstreamCompositionError(
            "largest-account amounts exceed total supply"
        )
    return top / total


def _age(observed, reference, policy):
    age = reference - observed
    if age < timedelta(0):
        raise OafUpstreamCompositionError("source observation is future-dated")
    return age, _fresh(age, policy)


def _fresh(age, policy):
    return (
        DataQuality.STALE
        if policy.stale_after is not None and age > policy.stale_after
        else DataQuality.VALID
    )


def _require_aware(value, name):
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise OafUpstreamCompositionError(
            f"{name} must be timezone-aware"
        )
