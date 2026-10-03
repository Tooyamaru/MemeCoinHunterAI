"""Injected common A1/P03 collection and exact, evidence-only frozen replay.

No default transport, operational adapter, diagnostic or economic authority.
The original A1-only packet/entry point retains its complete-ledger validator.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
import hashlib
import json
import math
from urllib.parse import urlsplit
from types import SimpleNamespace

from core.data import a1_cpmm_sources as m
from core.data.a1_operational_collection import (
    A1OperationalCollectionService, A1CollectionContext, A1CollectionPacket,
    A1CollectionRequestRecord, A1CollectedValuation, _digest, COINGECKO_ORIGIN,
)
from core.data.a1_bounded_transport import A1HttpRequest, validate_safety_params
from core.data.a1_collection_budget import A1BudgetLedger, A1BudgetSnapshot
from core.data.coingecko_onchain_ohlcv import OhlcvRequest, OhlcvResponse
from core.data.bounded_cycle_sources import BoundedDiscoveryOwner, DiscoverySnapshot
from core.data.contracts import FreshnessPolicy
from core.data.solana_oaf_source import SolanaMintSnapshot, SolanaRpcObservation
from core.risk.safety_evidence import P02StateReference, SafetyEvidenceCollection

VERSION = "a1-p03-safety-precollection-replay-v1"


class _CommonLedger(A1BudgetLedger):
    def check_time(self, now):
        now = super().check_time(now)
        if now.replace(second=0, microsecond=0) != self.started_at.replace(second=0, microsecond=0):
            self.abort()
            raise m.A1SourceError("P03_CUTOFF_ROLLOVER")
        return now

_READS = ("getAccountInfo", "getTokenLargestAccounts", "getTokenSupply")


def _params(method, mint):
    return [mint, {"commitment":"finalized", **({"encoding":"jsonParsed"} if method == _READS[0] else {})}]


def _policy(freshness, threshold, timeout, cap):
    m._require(type(freshness) is FreshnessPolicy and type(freshness.stale_after) is timedelta
        and freshness.stale_after > timedelta(0), "P03_FINITE_FRESHNESS")
    m._require(type(threshold) in (int, float) and math.isfinite(threshold)
        and 0 <= threshold <= 1, "P03_EXPLICIT_THRESHOLD")
    m._require(type(timeout) is timedelta and timedelta(0) < timeout <= timedelta(seconds=30)
        and type(cap) is int and 0 < cap <= 262144, "P03_SAFETY_LIMITS")


@dataclass(frozen=True, kw_only=True)
class CommonCollectionContext(A1CollectionContext):
    freshness_policy: FreshnessPolicy
    max_top_holder_fraction: float
    safety_timeout: timedelta
    safety_max_bytes: int
    provider_identity: str
    mapper_contract_version: str = m.VERSION
    source_contract_version: str = "bounded-paper-cycle-source-v1"

    def validate(self):
        self._validate_common(VERSION, ("solana", "valuation", "safety"))

    def _validate_common(self, version, admitted_stages):
        """Full global accounting; public v1 retains its original stage set."""
        m._require(type(self.requests) is tuple and type(self.reuse) is tuple
            and type(self.budget) is A1BudgetSnapshot and type(self.budget.attempts) is tuple
            and type(self.policy) is m.A1Policy
            and all(type(r) is A1CollectionRequestRecord and type(r.wire_request) is A1HttpRequest for r in self.requests),
            "P03_IMMUTABLE_CONTEXT")
        self._validate(version)
        m._require(self.mapper_contract_version == m.VERSION
            and self.source_contract_version == "bounded-paper-cycle-source-v1", "P03_SOURCE_VERSION")
        _policy(self.freshness_policy, self.max_top_holder_fraction, self.safety_timeout, self.safety_max_bytes)
        m._require(type(self.provider_identity) is str and self.provider_identity
                   and self.provider_identity == urlsplit(self.requests[0].wire_request.endpoint).hostname,
                   "P03_PROVIDER_IDENTITY")
        # Re-execute accounting from immutable physical records; no fake sub-ledger.
        ledger = _CommonLedger(self.operational_budget, self.collection_id, self.started_at,
                               "https://"+self.provider_identity, COINGECKO_ORIGIN)
        for record, attempt in zip(self.requests, self.budget.attempts):
            wire = record.wire_request
            parts = urlsplit(wire.endpoint)
            if wire.scope in ("solana", "safety"):
                m._require(parts.hostname == self.provider_identity and not parts.query
                    and parts.path in ("", "/"), "P03_SAFE_PROVIDER_ORIGIN")
            m._require(attempt.identity == ledger.reserve_attempt(kind=wire.scope, host=parts.hostname,
                response_cap=wire.max_response_bytes, timeout=wire.timeout, now=record.started_at), "P03_ATTEMPT_ID")
            ledger.observe_receipt(now=record.received_at, bodylen=attempt.response_bytes)
        m._require(ledger.seal(self.reference_time) == self.budget, "P03_BUDGET_LINEAGE")
        m._require(sum(a.kind == "solana" for a in self.budget.attempts) <= 16
            and sum(a.kind == "safety" for a in self.budget.attempts) <= 30
            and all(a.kind in admitted_stages for a in self.budget.attempts),
            "P03_STAGE_BUDGET")


@dataclass(frozen=True)
class SafetyRead:
    envelope: m.RpcEnvelope
    block_time: m.RpcEnvelope
    context_slot: int
    source_time: datetime


@dataclass(frozen=True)
class RawMintSafety:
    mint: str
    reads: tuple[SafetyRead, ...]

    @property
    def physical_envelopes(self):
        times = {r.block_time.request_id:r.block_time for r in self.reads}
        return tuple(r.envelope for r in self.reads) + tuple(times.values())

    def view(self, context, facts):
        """Replay-local mutable parser views never become packet state."""
        m._decode(self.mint, 32)
        m._require(type(self.reads) is tuple and len(self.reads) == 3
            and all(type(r) is SafetyRead for r in self.reads)
            and tuple(r.envelope.method for r in self.reads) == _READS, "P03_COMPLETE_READ_SET")
        observations, clocks = [], {}
        for read, method in zip(self.reads, _READS):
            env, time = read.envelope, read.block_time
            value = env.read_safety(method, _params(method, self.mint), context.reference_time, context.safety_max_bytes)
            m._require(type(value) is dict and set(("context", "value")) <= set(value)
                and type(value["context"]) is dict, "P03_CONTEXT_REQUIRED")
            slot = m._slot(value["context"].get("slot"))
            source = m._time(time.read_safety("getBlockTime", [slot], context.reference_time, context.safety_max_bytes))
            m._require(read.context_slot == slot and read.source_time == source, "P03_SOURCE_LINEAGE")
            m._require(env.received_at <= time.started_at or time.received_at <= env.started_at,
                       "P03_CLOCK_DEPENDENCY_ORDER")
            previous = clocks.get(slot)
            m._require(previous is None or previous == time, "P03_SAME_SLOT_REUSE")
            clocks[slot] = time
            m._require(slot >= facts.slot and source >= facts.observed_at
                and (slot != facts.slot or source == facts.observed_at)
                and source <= env.received_at <= context.reference_time
                and context.reference_time-source <= min(context.freshness_policy.stale_after, context.policy.stale_after),
                "P03_SOURCE_CLOCK")
            observations.append(SolanaRpcObservation(method, slot, source, value["value"], env.received_at))
        # A later slot cannot report an earlier ledger time.
        ordered = sorted((o.slot, o.observed_at) for o in observations)
        m._require(all(a[1] <= b[1] for a,b in zip(ordered, ordered[1:])), "P03_SLOT_TIME_ORDER")
        snapshot = SolanaMintSnapshot(self.mint, *observations)
        _validate_values(snapshot)
        return snapshot


def _amount(value, positive=False):
    m._require(type(value) is str and 0 < len(value) <= 20 and value.isascii() and value.isdigit(), "P03_RAW_AMOUNT")
    result = int(value)
    m._require(result < 2**64 and (not positive or result > 0), "P03_RAW_SUPPLY")
    return result


def _mint_decimals(value):
    m._require(type(value) is dict and value.get("owner") == m.TOKEN_PROGRAM
        and value.get("executable") is False and type(value.get("data")) is dict, "P03_LEGACY_MINT")
    parsed = value["data"].get("parsed")
    m._require(type(parsed) is dict and parsed.get("type") == "mint"
        and type(parsed.get("info")) is dict, "P03_PARSED_MINT")
    info = parsed["info"]
    decimals = info.get("decimals")
    m._require(info.get("isInitialized") is True and type(decimals) is int
        and 0 <= decimals <= 255, "P03_MINT_DECIMALS")
    for name in ("mintAuthority", "freezeAuthority"):
        m._require(name in info, "P03_AUTHORITY_REQUIRED")
        if info[name] is not None: m._decode(info[name], 32)
    return decimals


def _holder_total(holders, decimals):
    m._require(type(holders) is list and 1 <= len(holders) <= 20, "P03_HOLDER_SHAPE")
    addresses, largest = set(), 0
    for item in holders:
        m._require(type(item) is dict and type(item.get("decimals")) is int
            and item["decimals"] == decimals, "P03_HOLDER_DECIMALS")
        address = item.get("address")
        m._decode(address, 32)
        m._require(address not in addresses, "P03_DUPLICATE_HOLDER")
        addresses.add(address)
        largest += _amount(item.get("amount"))
    return largest


def _supply_total(supply, decimals):
    m._require(type(supply) is dict and type(supply.get("decimals")) is int
        and supply["decimals"] == decimals, "P03_SUPPLY_SHAPE")
    return _amount(supply.get("amount"), True)


def _validate_values(snapshot):
    decimals = _mint_decimals(snapshot.mint_account.result)
    m._require(_holder_total(snapshot.largest_accounts.result, decimals)
        <= _supply_total(snapshot.token_supply.result, decimals), "P03_HOLDERS_EXCEED_SUPPLY")


@dataclass(frozen=True)
class CommonCollectionPacket:
    a1: A1CollectionPacket
    manifest: tuple[tuple[str, str], ...]
    discovery_scope_digest: str
    safety: tuple[RawMintSafety, ...]
    packet_digest: str
    contract_version: str = VERSION

    @property
    def context(self):
        return self.a1.context

    def material(self):
        return {"contract_version":self.contract_version, "a1":self.a1,
                "manifest":self.manifest, "discovery_scope_digest":self.discovery_scope_digest, "safety":self.safety}

    def validate(self):
        c = self.context
        m._require(type(c) is CommonCollectionContext and self.contract_version == VERSION, "P03_COMMON_CONTRACT")
        return self._validate_stages()

    def _validate_stages(self):
        """Pure A1/P03 ownership checks under an already exact global context."""
        c = self.context
        c.validate()
        m._require(type(self.a1) is A1CollectionPacket
            and type(self.a1.verification_envelopes) is tuple
            and type(self.a1.reserve_envelopes) is tuple
            and all(type(pair) is tuple and len(pair) == 2 and type(pair[1]) is tuple for pair in self.a1.reserve_envelopes)
            and type(self.a1.valuations) is tuple
            and all(type(v) is A1CollectedValuation and type(v.response) is OhlcvResponse
                    and type(v.response.request) is OhlcvRequest for v in self.a1.valuations)
            and type(self.safety) is tuple and all(type(raw) is RawMintSafety for raw in self.safety),
            "P03_IMMUTABLE_PACKET")
        m._require(self.packet_digest == _digest(self.material()), "P03_PACKET_DIGEST")
        lengths = {"rpc:"+str(e.request_id):len(e.body) for e in (*self.a1.verification_envelopes,
            *self.a1.discovery_envelopes, *(e for _,es in self.a1.reserve_envelopes for e in es))}
        lengths.update({"usd:"+v.key.request_digest:len(v.response.body) for v in self.a1.valuations})
        m._require(all(a.response_bytes == lengths[r.request_identity] for r,a in zip(c.requests,c.budget.attempts)
                       if r.scope in ("solana", "valuation")), "P03_A1_BODY_LENGTH")
        a1_records = tuple(r for r in c.requests if r.scope in ("solana", "valuation"))
        self.a1._replay_stage(a1_records)
        facts = m.map_discovery(self.a1.discovery_envelopes, reference_time=c.reference_time, policy=c.policy)
        tokens = sorted({s for sw in facts.swaps for s in (sw.mint_0, sw.mint_1)})[:5]
        events = {o.raw_event.payload["token_identity"]:o.raw_event.source_event_id for o in facts.batch.observations}
        m._require(type(self.manifest) is tuple and self.manifest == tuple((mint,events[mint]) for mint in tokens)
            and len(self.manifest) <= c.operational_budget.max_discovery_candidates
            and self.discovery_scope_digest == facts.scope_digest
            and type(self.safety) is tuple and tuple(s.mint for s in self.safety) == tuple(tokens), "P03_MANIFEST")
        records = {r.request_identity:(r,a) for r,a in zip(c.requests,c.budget.attempts) if r.scope == "safety"}
        seen, rpc_ids = set(), {e.request_id for e in (*self.a1.verification_envelopes,
            *self.a1.discovery_envelopes, *(e for _,es in self.a1.reserve_envelopes for e in es))}
        for raw in self.safety:
            raw.view(c, facts)
            for env in raw.physical_envelopes:
                identity = "rpc:"+str(env.request_id)
                m._require(identity in records and identity not in seen and env.request_id not in rpc_ids,
                           "P03_PHYSICAL_COVERAGE")
                record, attempt = records[identity]
                params = json.loads(env.params_json)
                validate_safety_params(env.method, params)
                body = json.dumps({"jsonrpc":"2.0", "id":env.request_id, "method":env.method, "params":params},
                                  sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
                wire = record.wire_request
                m._require(wire.method == "POST" and wire.body == body and wire.scope == "safety"
                    and wire.timeout == c.safety_timeout and wire.max_response_bytes == c.safety_max_bytes
                    and (record.started_at,record.received_at) == (env.started_at,env.received_at)
                    and record.response_digest == hashlib.sha256(env.body).hexdigest()
                    and attempt.response_bytes == len(env.body), "P03_WIRE_LINEAGE")
                seen.add(identity); rpc_ids.add(env.request_id)
        m._require(seen == set(records), "P03_PHYSICAL_COVERAGE")
        # Consistency comparison is not lookup reuse: each mint still owns its
        # own physical time receipts, including equal slots across mints.
        clocks = [(facts.slot, facts.observed_at)]
        for _, envelopes in self.a1.reserve_envelopes:
            lookup = envelopes[1]
            slot = json.loads(lookup.params_json)[0]
            clocks.append((slot, m._time(lookup.read("getBlockTime", [slot], c.reference_time, 8192))))
        clocks.extend((r.context_slot, r.source_time) for raw in self.safety for r in raw.reads)
        clocks.sort()
        m._require(all(a[1] <= b[1] and (a[0] != b[0] or a[1] == b[1])
                       for a,b in zip(clocks, clocks[1:])), "P03_SESSION_CLOCK_CONFLICT")
        return facts

    def replay_sources(self):
        self.validate()
        discovery, pools = self.a1._replay_stage(tuple(r for r in self.context.requests if r.scope != "safety"))
        binding = ExactDiscoveryBinding(self, discovery)
        return binding, P03SafetyReplay(binding), pools


class A1P03CollectionService(A1OperationalCollectionService):
    def __init__(self, *, freshness_policy, max_top_holder_fraction, safety_timeout, safety_max_bytes, **kwargs):
        super().__init__(**kwargs)
        _policy(freshness_policy, max_top_holder_fraction, safety_timeout, safety_max_bytes)
        # The offline common contract only exports a sanitized origin. Credential
        # adapters with path/query authority require their separate future gate.
        parts = urlsplit(self.rpc_endpoint)
        m._require(not parts.query and parts.path in ("", "/"), "P03_SAFE_PROVIDER_ORIGIN")
        self.freshness_policy, self.max_top_holder_fraction = freshness_policy, max_top_holder_fraction
        self.safety_timeout, self.safety_max_bytes = safety_timeout, safety_max_bytes
        self.status = "CREATED"
        self.transitions = ("CREATED",)
        self._captured_configuration = self._configuration()

    def _configuration(self):
        return (self.collection_id, self.environment, self.intended_chain_identity, self.rpc_endpoint,
                self.budget, self.policy, self.rpc_timeout, self.usd_timeout, self.usd_max_bytes,
                self.freshness_policy, self.max_top_holder_fraction, self.safety_timeout, self.safety_max_bytes)

    def _check_configuration(self):
        m._require(self._configuration() == self._captured_configuration
            and (self.opener,self.clock) == self._active_injections, "P03_CONFIGURATION_MUTATION")

    def _transition(self, status):
        self.status = status
        self.transitions += (status,)

    def collect_once(self):
        if self.called:
            self._stopped()
            raise m.A1SourceError("SECOND_COLLECTION_FORBIDDEN")
        self._active_injections = (self.opener, self.clock)
        self._transition("COLLECTING")
        return super().collect_once()

    def _make_ledger(self, started):
        self._check_configuration()
        return _CommonLedger(self.budget, self.collection_id, started, self.rpc_endpoint, COINGECKO_ORIGIN)

    def _collect_extra_stage(self, transport, next_id, facts, tokens, records,
                             *, reserve_sets, registry, started):
        events = {o.raw_event.payload["token_identity"]:o.raw_event.source_event_id for o in facts.batch.observations}
        self._manifest = tuple((mint,events[mint]) for mint in tokens)
        self._scope_digest = facts.scope_digest
        raw = []
        def rpc(method, params):
            self._check_configuration()
            nonlocal next_id
            next_id += 1
            env = transport.rpc_safety(method, params, request_id=next_id,
                timeout=self.safety_timeout, max_bytes=self.safety_max_bytes)
            body = json.dumps({"jsonrpc":"2.0", "id":next_id, "method":method, "params":params},
                              sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            wire = A1HttpRequest("safety", self.rpc_endpoint, "POST", body, self.safety_timeout, self.safety_max_bytes)
            records.append(A1CollectionRequestRecord("rpc:"+str(next_id), wire.request_identity,
                hashlib.sha256(env.body).hexdigest(),env.started_at,env.received_at,"safety",wire))
            return env
        for mint in tokens:
            times, reads = {}, []
            for method in _READS:
                env = rpc(method, _params(method, mint))
                result = env.read_safety(method, _params(method,mint), env.received_at, self.safety_max_bytes)
                m._require(type(result) is dict and type(result.get("context")) is dict, "P03_CONTEXT_REQUIRED")
                if method == "getAccountInfo": decimals = _mint_decimals(result.get("value"))
                elif method == "getTokenLargestAccounts": largest = _holder_total(result.get("value"), decimals)
                else: m._require(largest <= _supply_total(result.get("value"), decimals), "P03_HOLDERS_EXCEED_SUPPLY")
                slot = m._slot(result["context"].get("slot"))
                m._require(slot >= facts.slot, "P03_SOURCE_SLOT")
                if slot not in times: times[slot] = rpc("getBlockTime", [slot])
                source = m._time(times[slot].read_safety("getBlockTime", [slot], times[slot].received_at, self.safety_max_bytes))
                m._require(facts.observed_at <= source <= env.received_at
                    and (slot != facts.slot or source == facts.observed_at)
                    and max(env.received_at,times[slot].received_at)-source <= min(self.freshness_policy.stale_after,self.policy.stale_after),
                    "P03_SOURCE_CLOCK")
                reads.append(SafetyRead(env, times[slot], slot, source))
            item = RawMintSafety(mint, tuple(reads))
            provisional = SimpleNamespace(reference_time=max(e.received_at for e in item.physical_envelopes),
                policy=self.policy, freshness_policy=self.freshness_policy, safety_max_bytes=self.safety_max_bytes)
            item.view(provisional, facts)
            raw.append(item)
        self._raw = tuple(raw)
        return next_id

    def _closed(self): self._transition("CLOSED")
    def _sealed(self): self._transition("SEALED")
    def _success(self): self._transition("FROZEN")
    def _stopped(self): self._transition("STOPPED")

    def _make_context(self, material):
        self._check_configuration()
        material.update(contract_version=VERSION, freshness_policy=self.freshness_policy,
            max_top_holder_fraction=self.max_top_holder_fraction, safety_timeout=self.safety_timeout,
            safety_max_bytes=self.safety_max_bytes, provider_identity=urlsplit(self.rpc_endpoint).hostname)
        context = CommonCollectionContext(**material, collection_digest="")
        return replace(context, collection_digest=_digest(context.material()))

    def _make_packet(self, context, verification, discovery, reserves, valuations):
        a1 = A1CollectionPacket(context, self.policy, verification, discovery, reserves, valuations)
        packet = CommonCollectionPacket(a1,self._manifest,self._scope_digest,self._raw,"")
        packet = replace(packet, packet_digest=_digest(packet.material()))
        packet.validate()
        return packet


@dataclass(frozen=True)
class DiscoveryBindingRecord:
    packet_digest: str
    snapshot: DiscoverySnapshot
    reference_time: datetime
    processing_time: datetime
    freshness_policy: FreshnessPolicy
    evaluation_id: str | None
    binding_digest: str

    def material(self):
        return {name:getattr(self,name) for name in self.__dataclass_fields__ if name != "binding_digest"}


@dataclass(frozen=True)
class EvidenceBindingRecord:
    discovery_binding_digest: str
    raw_dependency_digest: str
    evidence_digest: str
    evidence_references: tuple[str, ...]


class ExactDiscoveryBinding:
    """One canonical owner call, retaining its actual snapshot for the caller."""
    def __init__(self, packet, source):
        self.packet, self._owner = packet, BoundedDiscoveryOwner(source)
        self.record = None
        self.called = self.stopped = False

    def discover(self, *, reference_time, processing_time, freshness_policy, evaluation_id):
        if self.called or self.stopped:
            self.stopped = True
            raise m.A1SourceError("P03_SECOND_BIND")
        self.called = True
        try:
            facts = self.packet.validate()
            c = self.packet.context
            m._require(reference_time == c.reference_time and freshness_policy == c.freshness_policy
                and m._utc(processing_time) >= reference_time, "P03_BIND_ARGUMENTS")
            snapshot = self._owner.discover(reference_time=reference_time, processing_time=processing_time,
                freshness_policy=freshness_policy, evaluation_id=evaluation_id)
            m._require(type(snapshot) is DiscoverySnapshot
                and tuple((p.token_mint,p.source_event_id) for p in snapshot.candidates) == self.packet.manifest
                and all(p.chain_id == "solana" and snapshot.predecessor.contains("solana",p.token_mint) for p in snapshot.candidates)
                and (snapshot.source_id,snapshot.receipt_id,snapshot.received_at)
                    == (m.VERSION,facts.batch.receipt_id,facts.batch.received_at)
                and snapshot.predecessor.materializer_contract_version == "p02-t06-v1"
                and snapshot.predecessor.evaluation_id == evaluation_id, "P03_FINAL_MEMBERSHIP")
            record = DiscoveryBindingRecord(self.packet.packet_digest,snapshot,reference_time,processing_time,
                                             freshness_policy,evaluation_id,"")
            self.record = replace(record,binding_digest=_digest(record.material()))
            return snapshot
        except Exception:
            self.stopped = True
            raise


class P03SafetyReplay:
    def __init__(self, binding):
        self._binding = binding
        self._emitted = set()
        self._records = ()

    @property
    def evidence_bindings(self):
        return self._records

    def evidence_once(self, candidate, snapshot, *, reference_time):
        b = self._binding
        m._require(not b.stopped, "P03_REPLAY_STOPPED")
        try:
            record, packet = b.record, b.packet
            facts = packet.validate()
            m._require(record is not None and snapshot is record.snapshot
                and any(candidate is p for p in snapshot.candidates)
                and candidate.token_mint not in self._emitted
                and reference_time == record.reference_time == packet.context.reference_time
                and record.packet_digest == packet.packet_digest
                and record.binding_digest == _digest(record.material()), "P03_EXACT_PREDECESSOR")
            raw = next(r for r in packet.safety if r.mint == candidate.token_mint)
            view = raw.view(packet.context, facts)
            predecessor = snapshot.predecessor
            p02 = P02StateReference(predecessor.state_version,predecessor.state_digest,
                                   predecessor.materializer_contract_version,predecessor.evaluation_id)
            # Only the existing pure mapping is reused. No P02/evaluation/eligibility call.
            from backend.application.oaf_solana_upstream_composition import OafSolanaCanonicalComposer
            evidence = OafSolanaCanonicalComposer._compose_p03(view,reference_time,
                packet.context.freshness_policy,p02,packet.context.max_top_holder_fraction)
            collection = SafetyEvidenceCollection.from_evidence(evidence)
            m._require(all(e.p02_reference == p02 and e.token_key == (candidate.chain_id,candidate.token_mint)
                           for e in collection.evidence), "P03_EVIDENCE_BINDING")
            self._records += (EvidenceBindingRecord(record.binding_digest,_digest(raw),collection.representation_digest,
                tuple(e.evidence_reference for e in evidence)),)
            self._emitted.add(candidate.token_mint)
            return collection
        except Exception:
            b.stopped = True
            raise m.A1SourceError("P03_REPLAY_INVALID") from None
