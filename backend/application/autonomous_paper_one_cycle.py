"""Explicit, finite provider-neutral paper cycle; no operational wiring."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Callable, Protocol

from core.data.bounded_cycle_sources import (
    BoundedDiscoveryOwner, BoundedPoolCandidateOwner, CycleSourceError,
    CycleSourceUnavailable, DiscoverySnapshot, DiscoveredCandidate, fresh, aware, text,
)
from core.data.contracts import FreshnessPolicy
from core.risk.safety_evidence import SafetyEvidenceCollection, EligibilityStatus
from core.risk.safety_evaluation import evaluate_safety_evidence
from core.risk.safety_eligibility import derive_token_eligibility
from core.opportunity.opportunity_score import DEFAULT_SCORING_RULESET
from core.risk.paper_risk_capital_authorization import AuthorizationStatus
from core.runtime.controlled_paper_lifecycle import ControlledPaperLifecycleOutcome
from backend.application.market_to_opportunity_composition import (
    P01Rti11CompositionRequest, P01Rti11CompositionResult,
    MarketToOpportunityCompositionOutcome,
)
from backend.application.oaf_prepare_case import OafPrepareCaseRequest
from backend.application.prevalidated_decision_risk_capital_prefix import (
    PrevalidatedDecisionRiskCapitalPrefixService, PrevalidatedPrefixOutcome, P01Pfx01Result,
)
from backend.application.paper_fact_sourcing import PaperFactSourcingService, PaperFactSourcingOutcome, PaperFactSourcingResult
from backend.application.controlled_paper_experiment_input_preparation import (
    ControlledPaperExperimentInputPreparer, P01Cip01Request, P01Cip01Result, ControlledInputPreparationOutcome,
)
from backend.application.prepared_paper_case_invocation import (
    PreparedPaperCaseInvocationService, P01Oci01Request, P01Oci01Result, PreparedPaperInvocationOutcome,
)
from backend.application.prevalidated_risk_capital_suffix_caller import PrevalidatedSuffixOutcome
from backend.application.paper_lifecycle_persistence import (
    PaperLifecyclePersistenceResult, PaperLifecyclePersistenceOutcome,
    PaperLifecycleReadResult, PaperLifecycleReadOutcome,
)

CONTRACT_VERSION = "autonomous-paper-one-cycle-v1"


class CycleOutcome(StrEnum):
    CYCLE_COMPLETED = "CYCLE_COMPLETED"
    NO_DISCOVERY_CANDIDATES = "NO_DISCOVERY_CANDIDATES"
    NO_ELIGIBLE_CANDIDATE = "NO_ELIGIBLE_CANDIDATE"
    NO_VALID_POOL = "NO_VALID_POOL"
    MARKET_EVIDENCE_UNAVAILABLE = "MARKET_EVIDENCE_UNAVAILABLE"
    OPPORTUNITY_REJECTED = "OPPORTUNITY_REJECTED"
    DECISION_REJECTED = "DECISION_REJECTED"
    RISK_OR_CAPITAL_REJECTED = "RISK_OR_CAPITAL_REJECTED"
    PAPER_NOT_ADMITTED = "PAPER_NOT_ADMITTED"
    PAPER_TERMINATED_WITHOUT_PERSIST = "PAPER_TERMINATED_WITHOUT_PERSIST"
    PERSISTENCE_FAILED = "PERSISTENCE_FAILED"
    READBACK_FAILED = "READBACK_FAILED"
    INVALID_INPUT = "INVALID_INPUT"
    OWNER_UNAVAILABLE = "OWNER_UNAVAILABLE"


@dataclass(frozen=True)
class AutonomousPaperCycleRequest:
    invocation_id: str
    reference_time: datetime
    processing_time: datetime
    evaluated_at: datetime
    freshness_policy: FreshnessPolicy
    timeout: timedelta
    max_response_bytes: int
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self):
        text(self.invocation_id, "invocation_id")
        for name in ("reference_time", "processing_time", "evaluated_at"):
            aware(getattr(self, name), name)
        if self.evaluated_at != self.reference_time or self.processing_time < self.reference_time:
            raise ValueError("cycle requires one common reference/evaluation clock")
        if not isinstance(self.freshness_policy, FreshnessPolicy) or self.freshness_policy.stale_after is None:
            raise ValueError("explicit freshness policy required")
        if not isinstance(self.timeout, timedelta) or not timedelta(0) < self.timeout <= timedelta(seconds=30):
            raise ValueError("invalid diagnostic timeout")
        if type(self.max_response_bytes) is not int or not 1 <= self.max_response_bytes <= 1_048_576:
            raise ValueError("invalid response size")
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError("unsupported cycle contract")


@dataclass(frozen=True)
class CycleEvidence:
    stage: str
    owner_outcome: str
    reason_codes: tuple[str, ...]
    candidate_id: str | None = None
    owner_digest: str | None = None
    source_reference: str | None = None


@dataclass(frozen=True)
class AutonomousPaperCycleResult:
    invocation_id: str
    outcome: CycleOutcome
    terminal_stage: str
    evidence: tuple[CycleEvidence, ...]
    candidates_considered: int
    diagnostic_invocations: int
    selected_candidate_id: str | None = None
    selected_chain_id: str | None = None
    selected_token_mint: str | None = None
    selected_pool_address: str | None = None
    lifecycle_digest: str | None = None
    persistence_digest: str | None = None
    readback_digest: str | None = None
    simulation_only: bool = True
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self):
        if type(self.outcome) is not CycleOutcome or self.simulation_only is not True or self.contract_version != CONTRACT_VERSION:
            raise ValueError("invalid paper-cycle result")
        if not 0 <= self.diagnostic_invocations <= self.candidates_considered <= 5:
            raise ValueError("cycle budget exceeded")
        if self.outcome is CycleOutcome.CYCLE_COMPLETED and not all((
            self.selected_candidate_id, self.selected_token_mint, self.selected_pool_address,
            self.lifecycle_digest, self.persistence_digest, self.readback_digest,
        )):
            raise ValueError("completed cycle requires durable evidence")


class SafetySource(Protocol):
    def evidence_once(self, candidate: DiscoveredCandidate, snapshot: DiscoverySnapshot,
                      *, reference_time: datetime) -> SafetyEvidenceCollection: ...


class AutonomousPaperOneCycleService:
    """One direct application invocation; only injected source/diagnostic seams.

    No default concrete provider is constructed. Paper request facts are explicit
    and built only after canonical candidate/pool selection. Closed owners retain
    decision, risk, admission, lifecycle and persistence authority.
    """
    def __init__(self, *, discovery: BoundedDiscoveryOwner, pools: BoundedPoolCandidateOwner,
                 safety: SafetySource, market, paper_request_factory: Callable,
                 persistence, pfx=None, pfs=None, cip=None, invocation=None):
        self.discovery, self.pools, self.safety, self.market = discovery, pools, safety, market
        if type(discovery) is not BoundedDiscoveryOwner or type(pools) is not BoundedPoolCandidateOwner:
            raise ValueError("canonical bounded source owners required")
        self.factory, self.persistence = paper_request_factory, persistence
        self.pfx = pfx or PrevalidatedDecisionRiskCapitalPrefixService()
        self.pfs = pfs or PaperFactSourcingService()
        self.cip = cip or ControlledPaperExperimentInputPreparer()
        self.invocation = invocation or PreparedPaperCaseInvocationService()

    async def run(self, request: AutonomousPaperCycleRequest) -> AutonomousPaperCycleResult:
        evidence = []
        considered = diagnostics = 0
        selected = None
        lifecycle = persisted = readback = None
        stage = "INPUT"

        def finish(outcome):
            target = selected.request.target if selected else None
            return AutonomousPaperCycleResult(
                getattr(request, "invocation_id", "invalid"), outcome, stage, tuple(evidence),
                considered, diagnostics, selected.request.candidate_id if selected else None,
                target.chain_id if target else None, target.token_mint if target else None,
                target.pool_address if target else None, lifecycle.digest if lifecycle else None,
                persisted.digest if persisted else None, readback.digest if readback else None,
            )

        def record(owner, candidate_id=None):
            evidence.append(CycleEvidence(stage, owner.outcome.value, tuple(owner.reason_codes),
                                          candidate_id, getattr(owner, "digest", getattr(owner, "result_digest", None))))

        try:
            if type(request) is not AutonomousPaperCycleRequest:
                return finish(CycleOutcome.INVALID_INPUT)
            request.__post_init__()
            stage = "DISCOVERY"
            snapshot = self.discovery.discover(reference_time=request.reference_time,
                processing_time=request.processing_time, freshness_policy=request.freshness_policy,
                evaluation_id=request.invocation_id)
            considered = len(snapshot.candidates)
            evidence.append(CycleEvidence(stage, "ADMITTED", (), owner_digest=snapshot.predecessor.state_digest,
                source_reference=snapshot.source_id + "/" + snapshot.receipt_id))
            if not considered:
                return finish(CycleOutcome.NO_DISCOVERY_CANDIDATES)
            scored = []
            eligible = valid_pools = 0
            failed_market = False
            policy_key = None
            for candidate in snapshot.candidates:
                stage = "P03"
                collection = self.safety.evidence_once(candidate, snapshot, reference_time=request.reference_time)
                if type(collection) is not SafetyEvidenceCollection or (collection.chain_id, collection.token_identity) != (candidate.chain_id, candidate.token_mint):
                    raise ValueError("safety source identity mismatch")
                collection.__post_init__()
                for item in collection.evidence:
                    if item.p02_reference is None or (
                        item.p02_reference.state_digest != snapshot.predecessor.state_digest
                        or item.p02_reference.state_version != snapshot.predecessor.state_version
                        or item.p02_reference.contract_version != snapshot.predecessor.materializer_contract_version
                    ):
                        raise ValueError("safety evidence lacks exact discovery lineage")
                    fresh(item.observed_at, item.observed_at, request.reference_time, request.freshness_policy)
                evaluation = evaluate_safety_evidence(collection, evaluation_timestamp=request.evaluated_at)
                eligibility = derive_token_eligibility(evaluation)
                evidence.append(CycleEvidence(stage, eligibility.status.value, eligibility.reason_codes, candidate.candidate_id))
                if eligibility.status is not EligibilityStatus.ELIGIBLE:
                    continue
                eligible += 1
                stage = "POOL"
                try:
                    pool = self.pools.select(candidate, reference_time=request.reference_time, freshness_policy=request.freshness_policy)
                except CycleSourceError:
                    evidence.append(CycleEvidence(stage, "INVALID", ("INVALID_POOL_FACTS",), candidate.candidate_id))
                    continue
                if pool is None:
                    evidence.append(CycleEvidence(stage, "EMPTY", ("NO_POOL_CANDIDATES",), candidate.candidate_id))
                    continue
                valid_pools += 1
                target = pool.target()
                evidence.append(CycleEvidence(stage, "SELECTED", (), candidate.candidate_id,
                    target.target_reference_digest, pool.source_id + "/" + pool.reference_id))
                stage = "RTI-11"
                market_request = P01Rti11CompositionRequest(
                    candidate_id=candidate.candidate_id, predecessor=snapshot.predecessor,
                    target=target, safety_evaluation=evaluation, eligibility=eligibility,
                    reference_time=request.reference_time, timeout=request.timeout,
                    max_response_bytes=request.max_response_bytes, freshness_policy=request.freshness_policy,
                    processing_time=request.processing_time, evaluated_at=request.evaluated_at,
                    evaluation_id=request.invocation_id,
                )
                diagnostics += 1
                result = self.market.compose(market_request)
                if type(result) is not P01Rti11CompositionResult or result.request is not market_request:
                    raise ValueError("market owner did not preserve exact request")
                replace(result)
                record(result, candidate.candidate_id)
                if result.outcome is not MarketToOpportunityCompositionOutcome.COMPOSED:
                    failed_market = failed_market or result.outcome is MarketToOpportunityCompositionOutcome.DIAGNOSTIC_NOT_PRODUCED or any(
                        reason.startswith("CONTROLLED_DIAGNOSTIC") for reason in result.reason_codes)
                    continue
                score = result.composition.score
                # Check exact numerical rules, common clocks, feature versions and
                # candle window. Never compare candidate-specific scales/windows.
                observations = result.diagnostic.diagnostic.market.observations
                # Canonical P05 snapshots may be ordered by their candidate-bound
                # digest. Compare policy sets by feature identity, not digest order.
                features = sorted(result.composition.feature_snapshots,
                                  key=lambda f: (f.feature_id, f.feature_version))
                if any(f.freshness_policy != request.freshness_policy or f.reference_time != request.reference_time for f in features):
                    raise ValueError("incomparable feature freshness/reference")
                key = (score.ruleset.digest, score.contract_version, score.evaluator_version,
                       score.reference_time, score.evaluated_at, tuple(o.observation_time for o in observations),
                       tuple((f.feature_id, f.feature_version, f.calculation_contract_version,
                              f.value_unit, f.price_unit, f.quote_asset, f.freshness_policy) for f in features))
                if score.ruleset.digest != DEFAULT_SCORING_RULESET.digest or (policy_key is not None and key != policy_key):
                    raise ValueError("incomparable P05 scoring policy or window")
                policy_key = key
                scored.append(result)
            if not eligible:
                return finish(CycleOutcome.NO_ELIGIBLE_CANDIDATE)
            if not valid_pools:
                return finish(CycleOutcome.NO_VALID_POOL)
            if not scored:
                return finish(CycleOutcome.MARKET_EVIDENCE_UNAVAILABLE if failed_market else CycleOutcome.OPPORTUNITY_REJECTED)
            selected = min(scored, key=lambda r: (-r.composition.score.score, r.request.candidate_id,
                                                 r.request.target.chain_id, r.request.target.token_mint))
            stage = "PAPER_INPUT"
            paper_request = self.factory(selected, request)
            if type(paper_request) is not OafPrepareCaseRequest or paper_request.rti11_result is not selected:
                raise ValueError("paper factory lost selected result identity")
            paper_request.__post_init__()
            stage = "PFX"
            prefix = self.pfx.run(paper_request.pfx_request)
            if type(prefix) is not P01Pfx01Result:
                raise ValueError("noncanonical prefix result")
            prefix.__post_init__()
            if prefix.request is not paper_request.pfx_request:
                raise ValueError("prefix identity mismatch")
            record(prefix)
            if prefix.outcome is PrevalidatedPrefixOutcome.OWNER_UNAVAILABLE:
                return finish(CycleOutcome.OWNER_UNAVAILABLE)
            if prefix.rti13_result is not None and prefix.rti13_result.decision_intent is not None and prefix.rti13_result.decision_intent.action.value != "BUY":
                return finish(CycleOutcome.DECISION_REJECTED)
            if prefix.outcome is not PrevalidatedPrefixOutcome.PREFIX_MATERIALIZED:
                return finish(CycleOutcome.RISK_OR_CAPITAL_REJECTED if prefix.terminal_stage == "RTI-14" else CycleOutcome.DECISION_REJECTED)
            authorization = prefix.rti14_result.authorization_result
            if authorization is None or authorization.status is not AuthorizationStatus.APPROVED:
                evidence.append(CycleEvidence("RTI-14", authorization.status.value if authorization else "MISSING", tuple(authorization.reason_codes) if authorization else ("MISSING_AUTHORIZATION",)))
                return finish(CycleOutcome.RISK_OR_CAPITAL_REJECTED)
            stage = "PFS"
            facts = self.pfs.source(paper_request.pfs_request)
            if type(facts) is not PaperFactSourcingResult:
                raise ValueError("noncanonical paper facts")
            facts.__post_init__()
            if facts.request is not paper_request.pfs_request:
                raise ValueError("fact identity mismatch")
            record(facts)
            if facts.outcome is not PaperFactSourcingOutcome.FACTS_MATERIALIZED:
                return finish(CycleOutcome.PAPER_NOT_ADMITTED)
            stage = "CIP"
            cip_request = P01Cip01Request(invocation_id=paper_request.invocation_id, pfx_result=prefix, pfs_result=facts)
            prepared = self.cip.prepare(cip_request)
            if type(prepared) is not P01Cip01Result:
                raise ValueError("noncanonical prepared case")
            prepared.__post_init__()
            if prepared.request is not cip_request:
                raise ValueError("prepared case identity mismatch")
            record(prepared)
            if prepared.outcome is not ControlledInputPreparationOutcome.REQUEST_PREPARED:
                return finish(CycleOutcome.PAPER_NOT_ADMITTED)
            stage = "OCI/OSC"
            run_request = P01Oci01Request(prepared)
            run = self.invocation.run(run_request)
            if type(run) is not P01Oci01Result:
                raise ValueError("noncanonical invocation result")
            run.__post_init__()
            if run.request is not run_request:
                raise ValueError("invocation identity mismatch")
            record(run)
            if run.outcome is not PreparedPaperInvocationOutcome.OSC_RESULT_RETURNED:
                return finish(CycleOutcome.OWNER_UNAVAILABLE)
            suffix = run.osc02_result
            if suffix.outcome is not PrevalidatedSuffixOutcome.LIFECYCLE_RETURNED:
                return finish(CycleOutcome.OWNER_UNAVAILABLE if suffix.outcome is PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE else CycleOutcome.PAPER_NOT_ADMITTED)
            lifecycle = suffix.rti16_result.lifecycle_result
            if lifecycle.outcome is not ControlledPaperLifecycleOutcome.OBSERVATION_PRODUCED:
                return finish(CycleOutcome.PAPER_TERMINATED_WITHOUT_PERSIST)
            stage = "RTI-03_PERSIST"
            persisted = await self.persistence.persist(lifecycle)
            if type(persisted) is not PaperLifecyclePersistenceResult:
                persisted = None
                return finish(CycleOutcome.PERSISTENCE_FAILED)
            replace(persisted)
            record(persisted)
            if persisted.lifecycle_result_digest != lifecycle.digest or persisted.outcome not in (PaperLifecyclePersistenceOutcome.STORED, PaperLifecyclePersistenceOutcome.ALREADY_STORED):
                return finish(CycleOutcome.PERSISTENCE_FAILED)
            stage = "RTI-03_READ"
            readback = await self.persistence.read(lifecycle.digest)
            if type(readback) is not PaperLifecycleReadResult:
                readback = None
                return finish(CycleOutcome.READBACK_FAILED)
            replace(readback)
            record(readback)
            if readback.outcome is not PaperLifecycleReadOutcome.FOUND or readback.lifecycle_result_digest != lifecycle.digest or readback.run.artifact_count != persisted.artifact_count:
                return finish(CycleOutcome.READBACK_FAILED)
            return finish(CycleOutcome.CYCLE_COMPLETED)
        except CycleSourceUnavailable:
            evidence.append(CycleEvidence(stage, "UNAVAILABLE", ("SOURCE_UNAVAILABLE",)))
            return finish(CycleOutcome.OWNER_UNAVAILABLE)
        except (ValueError, TypeError, AttributeError, KeyError, ArithmeticError):
            evidence.append(CycleEvidence(stage, "INVALID", ("OWNER_CONTRACT_INVALID",)))
            return finish(CycleOutcome.PERSISTENCE_FAILED if stage == "RTI-03_PERSIST" else CycleOutcome.READBACK_FAILED if stage == "RTI-03_READ" else CycleOutcome.INVALID_INPUT)
        except (RuntimeError, OSError):
            evidence.append(CycleEvidence(stage, "UNAVAILABLE", ("OWNER_UNAVAILABLE",)))
            return finish(CycleOutcome.PERSISTENCE_FAILED if stage == "RTI-03_PERSIST" else CycleOutcome.READBACK_FAILED if stage == "RTI-03_READ" else CycleOutcome.OWNER_UNAVAILABLE)
