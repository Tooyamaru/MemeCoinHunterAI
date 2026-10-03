"""Injected pre-T diagnostic collection and pure, exact-object RTI-11 replay.

This contract extends the common ledger, not the authority of any canonical
owner. The exported replay graph contains only immutable facts and pure owners.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
import hashlib
from types import MappingProxyType
from urllib.parse import urlsplit

from core.data import a1_cpmm_sources as m
from core.data.a1_bounded_transport import A1HttpRequest
from core.data.a1_collection_budget import A1ValuationRequestKey
from core.data.a1_operational_collection import (
    A1CollectionPacket, A1CollectionRequestRecord, _digest,
)
from core.data.a1_p03_collection import (
    A1P03CollectionService, CommonCollectionContext, CommonCollectionPacket,
    ExactDiscoveryBinding, P03SafetyReplay,
)
from core.data.bounded_cycle_sources import BoundedPoolCandidateOwner, DiscoveredCandidate, DiscoverySnapshot
from core.data.coingecko_onchain_ohlcv import (
    ADAPTER_VERSION, ENDPOINT_VERSION, OhlcvOutcome, OhlcvRequest, OhlcvResponse, _parse,
)
from core.data.coingecko_onchain_orchestration import ControlledDiagnosticOutcome
from core.risk.safety_evaluation import SafetyEvaluationResult
from core.risk.safety_evidence import EligibilityStatus, SafetyEvidenceCollection, DerivedEligibilityOutput
from core.signals.price_direction_policy import POLICY_VERSION, SIGNAL_TYPE, derive_price_direction

VERSION = "a1-rti11-diagnostic-precollection-replay-v1"
SELECTION_POLICY = "highest-exact-liquidity-usd-then-lexical-pool-v1"


def _limits(timeout, cap):
    m._require(type(timeout) is timedelta and timedelta(0) < timeout <= timedelta(seconds=30)
        and type(cap) is int and 0 < cap <= 1048576, "RTI11_DIAGNOSTIC_LIMITS")


@dataclass(frozen=True, kw_only=True)
class DiagnosticCollectionContext(CommonCollectionContext):
    diagnostic_timeout: timedelta
    diagnostic_max_bytes: int
    endpoint_version: str = ENDPOINT_VERSION
    adapter_version: str = ADAPTER_VERSION
    price_direction_version: str = POLICY_VERSION
    signal_type: str = SIGNAL_TYPE
    interval_seconds: int = 60
    price_unit: str = "USD"

    def validate(self):
        self._validate_common(VERSION, ("solana", "valuation", "safety", "diagnostic"))
        _limits(self.diagnostic_timeout, self.diagnostic_max_bytes)
        m._require(type(self.interval_seconds) is int
            and (self.endpoint_version, self.adapter_version, self.price_direction_version,
            self.signal_type, self.interval_seconds, self.price_unit) ==
            (ENDPOINT_VERSION, ADAPTER_VERSION, POLICY_VERSION, SIGNAL_TYPE, 60, "USD"), "RTI11_VERSION_PINS")
        m._require(all((a.timeout, a.response_cap) == (self.diagnostic_timeout, self.diagnostic_max_bytes)
            for a in self.budget.attempts if a.kind == "diagnostic"), "RTI11_DIAGNOSTIC_PROFILE")


@dataclass(frozen=True)
class RawDiagnosticTarget:
    mint: str
    source_event_id: str
    reserve: m.ReserveFact


def _targets(facts, manifest, reserve_sets, reference_time, policy):
    m._require(tuple(mint for mint, _ in reserve_sets) == tuple(mint for mint, _ in manifest),
               "RTI11_RESERVE_MANIFEST")
    targets = []
    for (mint, event), (_, envelopes) in zip(manifest, reserve_sets):
        reserves = m.map_reserves(facts, mint, envelopes, reference_time=reference_time, policy=policy)
        targets.extend(RawDiagnosticTarget(mint, event, r) for r in sorted(reserves, key=lambda r: r.pool))
    return tuple(targets)


def _request(target, reference_time, timeout, cap):
    r = target.reserve
    quote = r.mint_1 if target.mint == r.mint_0 else r.mint_0
    return OhlcvRequest("solana", target.mint, r.pool, target.mint, quote, reference_time, timeout, cap)


def _key(collection_id, request):
    return A1ValuationRequestKey.from_parameters(collection_id=collection_id, planned_cutoff=request.cutoff,
        endpoint_version=ENDPOINT_VERSION, endpoint_url=request.url, network=request.chain_id,
        pool=request.pool_address, mint=request.token_mint, parameters=request.parameters,
        base_mint=request.base_mint, quote_mint=request.quote_mint,
        timeout=request.timeout, maxbytes=request.max_response_bytes)


def _window(body, request, started_at, received_at, reference_time, freshness, policy):
    """Reparse original bytes; use both captured source and diagnostic clocks."""
    m._require(type(body) is bytes and 0 < len(body) <= request.max_response_bytes
        and m._utc(started_at) <= m._utc(received_at) <= m._utc(reference_time)
        and received_at - started_at <= request.timeout, "RTI11_RECEIPT_CLOCK")
    resource, base, quote, stamps, candles = _parse(body, request)
    opens = tuple(m._EPOCH + timedelta(seconds=s) for s, _ in candles)
    ends = tuple(t + timedelta(seconds=60) for t in opens)
    m._require(len(opens) == 3 and all(a <= b <= received_at for a, b in zip(opens, ends))
        and candles[-1][0] == request.cutoff - 60
        and reference_time - opens[0] <= freshness.stale_after
        and reference_time - opens[-1] <= policy.stale_after, "RTI11_SOURCE_WINDOW")
    return resource, base, quote, tuple(stamps), opens, ends


@dataclass(frozen=True)
class DiagnosticFact:
    target: RawDiagnosticTarget
    key: A1ValuationRequestKey
    response: OhlcvResponse
    record_identity: str
    attempt_identity: int
    reused_a1: bool
    resource_id: str | None
    returned_base: str
    returned_quote: str
    source_timestamps: tuple[int, ...]
    candle_opens: tuple[datetime, ...]
    candle_ends: tuple[datetime, ...]


@dataclass(frozen=True, kw_only=True)
class DiagnosticCollectionPacket(CommonCollectionPacket):
    diagnostics: tuple[DiagnosticFact, ...]
    contract_version: str = VERSION

    def material(self):
        return {**super().material(), "diagnostics": self.diagnostics}

    def validate(self):
        c = self.context
        m._require(type(c) is DiagnosticCollectionContext and self.contract_version == VERSION,
                   "RTI11_COMMON_CONTRACT")
        facts = self._validate_stages()
        m._require(type(self.diagnostics) is tuple
            and all(type(f) is DiagnosticFact and type(f.target) is RawDiagnosticTarget
                and type(f.target.reserve) is m.ReserveFact and type(f.key) is A1ValuationRequestKey
                and type(f.response) is OhlcvResponse and type(f.response.request) is OhlcvRequest
                and type(f.reused_a1) is bool and type(f.attempt_identity) is int
                and all(type(v) is tuple for v in (f.source_timestamps, f.candle_opens, f.candle_ends))
                for f in self.diagnostics), "RTI11_IMMUTABLE_FACTS")
        expected = _targets(facts, self.manifest, self.a1.reserve_envelopes, c.reference_time, c.policy)
        m._require(tuple(f.target for f in self.diagnostics) == expected, "RTI11_TARGET_COVERAGE")
        physical = {r.request_identity: (r, a) for r, a in zip(c.requests, c.budget.attempts)}
        valuations = {v.key: v for v in self.a1.valuations}
        diagnostic_rows = {r.request_identity for r in c.requests if r.scope == "diagnostic"}
        seen = set()
        for fact in self.diagnostics:
            request = _request(fact.target, c.reference_time, c.diagnostic_timeout, c.diagnostic_max_bytes)
            fact.key.validate()
            m._require(fact.key == _key(c.collection_id, request) and fact.response.request == request
                and fact.key.planned_cutoff == c.planned_cutoff, "RTI11_EXACT_REQUEST")
            reuse = valuations.get(fact.key)
            m._require(fact.reused_a1 == (reuse is not None), "RTI11_REUSE_EQUIVALENCE")
            identity = ("usd:" if fact.reused_a1 else "diagnostic:") + fact.key.request_digest
            m._require(fact.record_identity == identity and identity in physical, "RTI11_PHYSICAL_DEPENDENCY")
            record, attempt = physical[identity]
            response = fact.response
            scope = "valuation" if fact.reused_a1 else "diagnostic"
            wire = A1HttpRequest(scope, request.url, "GET", b"", request.timeout, request.max_response_bytes)
            m._require(record.wire_request == wire and record.wire_digest == wire.request_identity
                and record.scope == scope and attempt.identity == fact.attempt_identity
                and (record.started_at, record.received_at) == (response.started_at, response.received_at)
                and response.http_status == 200 and type(response.http_status) is int
                and response.transport_failure is None
                and record.response_digest == hashlib.sha256(response.body).hexdigest()
                and attempt.response_bytes == len(response.body), "RTI11_RESPONSE_LINEAGE")
            if fact.reused_a1:
                m._require(response is reuse.response, "RTI11_ORIGINAL_A1_RESPONSE")
            else:
                m._require(identity not in seen, "RTI11_DUPLICATE_DIAGNOSTIC")
                seen.add(identity)
            material = _window(response.body, request, response.started_at, response.received_at,
                               c.reference_time, c.freshness_policy, c.policy)
            m._require(material == (fact.resource_id, fact.returned_base, fact.returned_quote,
                fact.source_timestamps, fact.candle_opens, fact.candle_ends), "RTI11_SOURCE_LINEAGE")
            m._price(response, reference_time=c.reference_time, policy=c.policy)
        m._require(seen == diagnostic_rows, "RTI11_DIAGNOSTIC_COVERAGE")
        return facts

    def replay_sources(self):
        self.validate()
        discovery, source = self.a1._replay_stage(tuple(r for r in self.context.requests
                                                       if r.scope in ("solana", "valuation")))
        binding = ExactDiscoveryBinding(self, discovery)
        safety = DiagnosticSafetyReplay(binding)
        pools = ExactPoolBinding(binding, safety, source)
        return binding, safety, pools, RTI11DiagnosticReplay(binding, safety, pools)


class A1Rti11CollectionService(A1P03CollectionService):
    def __init__(self, *, diagnostic_timeout, diagnostic_max_bytes, **kwargs):
        _limits(diagnostic_timeout, diagnostic_max_bytes)
        self.diagnostic_timeout, self.diagnostic_max_bytes = diagnostic_timeout, diagnostic_max_bytes
        super().__init__(**kwargs)

    def _configuration(self):
        return (*super()._configuration(), self.diagnostic_timeout, self.diagnostic_max_bytes)

    def _collect_extra_stage(self, transport, next_id, facts, tokens, records,
                             *, reserve_sets, registry, started):
        next_id = super()._collect_extra_stage(transport, next_id, facts, tokens, records,
            reserve_sets=reserve_sets, registry=registry, started=started)
        self._check_configuration()
        # No canonical discovery, P03 evaluation, selection or liquidity ranking.
        targets = _targets(facts, self._manifest, reserve_sets, records[-1].received_at, self.policy)
        entries = dict(registry.entries)
        plan = tuple((t, _request(t, started, self.diagnostic_timeout, self.diagnostic_max_bytes)) for t in targets)
        m._require(sum(_key(self.collection_id, r) not in entries for _, r in plan)
                   <= self.budget.max_diagnostics, "RTI11_DIAGNOSTIC_PLAN_BUDGET")
        raw = []
        for target, request in plan:
            self._check_configuration()
            key = _key(self.collection_id, request)
            receipt = entries.get(key)
            reused = receipt is not None
            if not reused:
                receipt = transport.http(A1HttpRequest("diagnostic", request.url, "GET", b"",
                                                       request.timeout, request.max_response_bytes))
                records.append(A1CollectionRequestRecord("diagnostic:" + key.request_digest,
                    receipt.request.request_identity, receipt.body_digest, receipt.started_at,
                    receipt.received_at, "diagnostic", receipt.request))
            _window(receipt.body, request, receipt.started_at, receipt.received_at,
                    records[-1].received_at, self.freshness_policy, self.policy)
            raw.append((target, key, receipt, reused))
        self._diagnostic_raw = tuple(raw)
        return next_id

    def _make_context(self, material):
        self._check_configuration()
        material.update(contract_version=VERSION, freshness_policy=self.freshness_policy,
            max_top_holder_fraction=self.max_top_holder_fraction, safety_timeout=self.safety_timeout,
            safety_max_bytes=self.safety_max_bytes, provider_identity=urlsplit(self.rpc_endpoint).hostname,
            diagnostic_timeout=self.diagnostic_timeout, diagnostic_max_bytes=self.diagnostic_max_bytes)
        context = DiagnosticCollectionContext(**material, collection_digest="")
        return replace(context, collection_digest=_digest(context.material()))

    def _make_packet(self, context, verification, discovery, reserves, valuations):
        a1 = A1CollectionPacket(context, self.policy, verification, discovery, reserves, valuations)
        existing = {v.key: v.response for v in valuations}
        physical = {r.request_identity: a.identity for r, a in zip(context.requests, context.budget.attempts)}
        diagnostics = []
        for target, key, receipt, reused in self._diagnostic_raw:
            request = _request(target, context.reference_time, context.diagnostic_timeout, context.diagnostic_max_bytes)
            m._require(_key(context.collection_id, request) == key, "RTI11_FINAL_WIRE_IDENTITY")
            response = existing[key] if reused else OhlcvResponse(request, receipt.started_at,
                                                                  receipt.received_at, receipt.body, receipt.status)
            identity = ("usd:" if reused else "diagnostic:") + key.request_digest
            diagnostics.append(DiagnosticFact(target, key, response, identity, physical[identity], reused,
                *_window(response.body, request, response.started_at, response.received_at,
                         context.reference_time, context.freshness_policy, context.policy)))
        packet = DiagnosticCollectionPacket(a1=a1, manifest=self._manifest, discovery_scope_digest=self._scope_digest,
            safety=self._raw, diagnostics=tuple(diagnostics), packet_digest="")
        packet = replace(packet, packet_digest=_digest(packet.material()))
        packet.validate()
        return packet


class DiagnosticSafetyReplay(P03SafetyReplay):
    """Retain original evidence; canonical evaluation stays in the caller."""
    def __init__(self, binding):
        super().__init__(binding)
        self.emissions = ()

    def evidence_once(self, candidate, snapshot, *, reference_time):
        collection = super().evidence_once(candidate, snapshot, reference_time=reference_time)
        self.emissions += ((candidate, collection),)
        return collection


def _discovery_record(binding, candidate):
    binding.packet.validate()
    r = binding.record
    m._require(not binding.stopped and r is not None and r.packet_digest == binding.packet.packet_digest
        and r.binding_digest == _digest(r.material())
        and any(candidate is p for p in r.snapshot.candidates), "RTI11_EXACT_DISCOVERY")
    return r


class _CapturedPools:
    def __init__(self, source):
        self.source, self.observations = source, None

    def pools_once(self, candidate, *, reference_time):
        self.observations = self.source.pools_once(candidate, reference_time=reference_time)
        return self.observations


@dataclass(frozen=True)
class PoolBindingRecord:
    candidate: DiscoveredCandidate
    observations: tuple
    selected: object
    discovery_binding_digest: str
    valuation_lineage: tuple[str, ...]
    binding_digest: str
    selection_policy: str = SELECTION_POLICY

    def material(self):
        return {"candidate": self.candidate, "observations": tuple(p.target() for p in self.observations),
            "selected": self.selected.target() if self.selected else None,
            "discovery_binding_digest": self.discovery_binding_digest,
            "valuation_lineage": self.valuation_lineage, "selection_policy": self.selection_policy}


class ExactPoolBinding(BoundedPoolCandidateOwner):
    def __init__(self, binding, safety, source):
        m._require(type(binding.packet) is DiagnosticCollectionPacket
            and type(source) is m.OfflineA1PoolSource
            and source.discovery is binding._owner.source, "RTI11_PURE_POOL_SOURCE")
        self.binding, self.safety, self.raw_source = binding, safety, source
        super().__init__(_CapturedPools(source))
        self.records = ()
        self._called = set()

    def validate_record(self, record):
        r = _discovery_record(self.binding, record.candidate)
        valuations = self.raw_source.valuation_facts[record.candidate.token_mint]
        m._require(any(record is v for v in self.records)
            and type(record.observations) is tuple and len(record.observations) == len(valuations)
            and all(p is v.observation for p, v in zip(record.observations, valuations))
            and (record.selected is None or any(record.selected is p for p in record.observations))
            and record.discovery_binding_digest == r.binding_digest
            and record.valuation_lineage == tuple(v.lineage_json for v in valuations)
            and record.selection_policy == SELECTION_POLICY and record.binding_digest == _digest(record.material()),
            "RTI11_EXACT_POOL")
        for pool in record.observations:
            pool.validate(record.candidate, r.reference_time, r.freshness_policy)
        return record

    def select(self, candidate, *, reference_time, freshness_policy):
        try:
            r = _discovery_record(self.binding, candidate)
            m._require(candidate.token_mint not in self._called
                and any(candidate is c for c, _ in self.safety.emissions)
                and reference_time == r.reference_time and freshness_policy == r.freshness_policy
                and type(self.source) is _CapturedPools and self.source.source is self.raw_source,
                "RTI11_POOL_BIND_ARGUMENTS")
            self._called.add(candidate.token_mint)
            # Sole selection/ranking delegation; keep its actual result and tuple.
            selected = super().select(candidate, reference_time=reference_time, freshness_policy=freshness_policy)
            record = PoolBindingRecord(candidate, self.source.observations, selected, r.binding_digest,
                tuple(v.lineage_json for v in self.raw_source.valuation_facts[candidate.token_mint]), "")
            record = replace(record, binding_digest=_digest(record.material()))
            self.records += (record,)
            self.validate_record(record)
            return selected
        except Exception:
            self.binding.stopped = True
            raise m.A1SourceError("RTI11_POOL_BIND_INVALID") from None


def _request_digest(request):
    # The canonical owner handles Decimal and read-only provenance/context.
    from backend.application.market_to_opportunity_composition import _digest as canonical_digest
    return canonical_digest(request.canonical_representation)


@dataclass(frozen=True)
class DiagnosticBindingRecord:
    candidate: DiscoveredCandidate
    snapshot: DiscoverySnapshot
    collection: SafetyEvidenceCollection
    evaluation: SafetyEvaluationResult
    eligibility: DerivedEligibilityOutput
    pool_record: PoolBindingRecord
    request: object
    target: object
    fact: DiagnosticFact
    request_digest: str
    binding_digest: str

    def material(self):
        return {"candidate": self.candidate, "snapshot": self.snapshot,
            "collection_digest": self.collection.representation_digest,
            "evaluation_digest": self.evaluation.representation_digest, "eligibility": self.eligibility,
            "pool_binding_digest": self.pool_record.binding_digest,
            "request_digest": _request_digest(self.request), "target": self.target, "fact": self.fact}


@dataclass(frozen=True)
class ReplayLineageRecord:
    binding_digest: str
    request_digest: str
    result_digest: str
    fact_digest: str
    record_identity: str
    attempt_identity: int
    reused_a1: bool
    discovery_binding_digest: str
    evidence_binding_digest: str
    pool_binding_digest: str


class RTI11DiagnosticReplay:
    def __init__(self, binding, safety, pools):
        self.binding, self.safety, self.pools = binding, safety, pools
        self.bindings = self.lineage = ()
        self._pending = None
        self._diagnostic_called = False

    def _validate(self, record):
        from backend.application.market_to_opportunity_composition import P01Rti11CompositionRequest
        r = _discovery_record(self.binding, record.candidate)
        c, request = self.binding.packet.context, record.request
        self.pools.validate_record(record.pool_record)
        request.__post_init__()
        m._require(type(request) is P01Rti11CompositionRequest
            and type(record.evaluation) is SafetyEvaluationResult and type(record.eligibility) is DerivedEligibilityOutput
            and record.snapshot is r.snapshot
            and any(record.candidate is candidate and record.collection is evidence
                for candidate, evidence in self.safety.emissions)
            and request.predecessor is r.snapshot.predecessor
            and request.safety_evaluation is record.evaluation and request.eligibility is record.eligibility
            and request.candidate_id == record.candidate.candidate_id
            and record.pool_record.candidate is record.candidate and record.pool_record.selected is not None
            and request.target is record.target and request.target == record.pool_record.selected.target()
            and request.target.token_mint == record.fact.target.mint
            and request.target.pool_address == record.fact.target.reserve.pool
            and record.candidate.source_event_id == record.fact.target.source_event_id
            and request.eligibility.status is EligibilityStatus.ELIGIBLE
            and request.safety_evaluation.input_evidence_digest == record.collection.representation_digest
            and request.safety_evaluation.evaluation_timestamp == request.eligibility.evaluated_at == c.reference_time
            and request.safety_evaluation.evidence_references == tuple(e.evidence_reference for e in record.collection.evidence)
            and request.reference_time == request.evaluated_at == c.reference_time
            and request.processing_time == r.processing_time and request.evaluation_id == r.evaluation_id
            and request.freshness_policy == c.freshness_policy
            and (request.timeout, request.max_response_bytes) == (c.diagnostic_timeout, c.diagnostic_max_bytes)
            and any(record.fact is f for f in self.binding.packet.diagnostics)
            and record.request_digest == _request_digest(request)
            and record.binding_digest == _digest(record.material()), "RTI11_EXACT_HANDOFF")

    def bind_upstream(self, candidate, snapshot, collection, evaluation, eligibility, pool, request):
        try:
            m._require(not self.binding.stopped and self._pending is None
                and not any(candidate is r.candidate for r in self.bindings), "RTI11_SECOND_BIND")
            pool_record = next(r for r in self.pools.records if r.candidate is candidate)
            m._require(pool is pool_record.selected and request.safety_evaluation is evaluation
                and request.eligibility is eligibility, "RTI11_ORIGINAL_UPSTREAM")
            fact = next(f for f in self.binding.packet.diagnostics
                        if f.target.mint == candidate.token_mint and f.target.reserve.pool == pool.pool_address)
            record = DiagnosticBindingRecord(candidate, snapshot, collection, evaluation, eligibility,
                pool_record, request, request.target, fact, _request_digest(request), "")
            record = replace(record, binding_digest=_digest(record.material()))
            self._validate(record)
            self.bindings += (record,)
            self._pending = record
        except Exception:
            self.binding.stopped = True
            raise m.A1SourceError("RTI11_BIND_INVALID") from None

    def _diagnostic(self, *, request, predecessor, freshness_policy, environment):
        try:
            record = self._pending
            self._validate(record)
            m._require(not self._diagnostic_called and request == record.fact.response.request
                and predecessor is record.snapshot.predecessor
                and freshness_policy == self.binding.packet.context.freshness_policy
                and type(environment) is MappingProxyType and not environment, "RTI11_DIAGNOSTIC_IDENTITY")
            self._diagnostic_called = True
            result = derive_price_direction(request=request, response=record.fact.response,
                predecessor=predecessor, freshness_policy=freshness_policy,
                evaluation_time=record.request.reference_time)
            m._require(result.market.outcome is OhlcvOutcome.PRODUCED and result.signal_evidence is not None,
                       "RTI11_DIAGNOSTIC_NOT_PRODUCED")
            return result
        except Exception:
            self.binding.stopped = True
            raise m.A1SourceError("RTI11_DIAGNOSTIC_INVALID") from None

    def compose(self, request):
        from backend.application.market_to_opportunity_composition import MarketToOpportunityCompositionService
        try:
            record = self._pending
            m._require(record is not None and request is record.request, "RTI11_ORIGINAL_REQUEST")
            self._validate(record)
            self._diagnostic_called = False
            result = MarketToOpportunityCompositionService(environment=MappingProxyType({}),
                diagnostic=self._diagnostic).compose(request)
            m._require(not self.binding.stopped and self._diagnostic_called and result.request is request
                and result.diagnostic is not None and result.diagnostic.diagnostic is not None
                and result.diagnostic.outcome is ControlledDiagnosticOutcome.DIAGNOSTIC_COMPLETED
                and result.diagnostic.diagnostic.market.outcome is OhlcvOutcome.PRODUCED,
                "RTI11_REPLAY_NOT_PRODUCED")
            self.lineage += (ReplayLineageRecord(record.binding_digest, record.request_digest,
                result.result_digest, _digest(record.fact), record.fact.record_identity, record.fact.attempt_identity,
                record.fact.reused_a1, self.binding.record.binding_digest,
                _digest(next(r for r in self.safety.evidence_bindings
                             if r.evidence_digest == record.collection.representation_digest)),
                record.pool_record.binding_digest),)
            self._pending = None
            return result
        except Exception:
            self.binding.stopped = True
            raise m.A1SourceError("RTI11_REPLAY_INVALID") from None
