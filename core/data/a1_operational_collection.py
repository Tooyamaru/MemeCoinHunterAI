"""Finite injected A1 collection and immutable replay; no default network.

Wire queries commit to one cutoff before collection. The mapper reference is
created only after receipts complete; crossing that cutoff minute stops the
collection. Safety/diagnostic operational replay remains a separate gate.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta
import hashlib
import json

from core.data import a1_cpmm_sources as mapping
from core.data.a1_bounded_transport import A1BoundedTransport, A1HttpRequest, TRANSPORT_VERSION
from core.data.a1_collection_budget import (
    A1OperationalBudget, A1BudgetLedger, A1BudgetSnapshot,
    A1ValuationRequestKey, A1CollectionRequestRegistry, A1RequestReuse,
)
from core.data.a1_source_verification import (
    MAINNET_GENESIS_HASH, A1ClusterEvidence, A1ProgramEvidence, cluster_params,
    program_probe_params, program_probe_identity, program_snapshot_params,
    verify_cluster, verify_program,
)
from core.data.coingecko_onchain_ohlcv import OhlcvRequest, OhlcvResponse, ENDPOINT_VERSION, _parse

VERSION = "a1-operational-collection-v1"
COINGECKO_ORIGIN = "https://api.coingecko.com"


def _canonical(value):
    if isinstance(value, bytes):
        return {"sha256": hashlib.sha256(value).hexdigest(), "length": len(value)}
    if is_dataclass(value):
        return {f.name: _canonical(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, datetime):
        return mapping._utc(value).isoformat()
    if isinstance(value, timedelta):
        return value // timedelta(microseconds=1)
    if isinstance(value, (tuple, list)):
        return [_canonical(v) for v in value]
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in value.items()}
    return value


def _digest(value):
    return hashlib.sha256(json.dumps(_canonical(value), sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class A1CollectionRequestRecord:
    request_identity: str
    wire_digest: str
    response_digest: str
    started_at: datetime
    received_at: datetime
    scope: str
    wire_request: A1HttpRequest


@dataclass(frozen=True)
class A1CollectionContext:
    collection_id: str
    environment: str
    intended_chain_identity: str
    started_at: datetime
    completed_at: datetime
    reference_time: datetime
    planned_cutoff: int
    requests: tuple[A1CollectionRequestRecord, ...]
    reuse: tuple[A1RequestReuse, ...]
    policy: mapping.A1Policy
    operational_budget: A1OperationalBudget
    budget: A1BudgetSnapshot
    cluster: A1ClusterEvidence
    program: A1ProgramEvidence
    collection_digest: str
    transport_contract_version: str = TRANSPORT_VERSION
    contract_version: str = VERSION

    def material(self):
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name != "collection_digest"}

    def validate(self):
        self._validate(VERSION)

    def _validate(self, version):
        # Shared complete-ledger checks. The v1 public validator stays strict.
        mapping._require(self.contract_version == version and self.transport_contract_version == TRANSPORT_VERSION,
                         "COLLECTION_CONTRACT")
        mapping._require(self.intended_chain_identity == MAINNET_GENESIS_HASH
                         and self.cluster.genesis_hash == MAINNET_GENESIS_HASH
                         and self.program.verification_level == "LEVEL_1"
                         and self.program.source_equivalence == "NOT_VERIFIED", "COLLECTION_VERIFICATION_REQUIRED")
        mapping._require(mapping._utc(self.started_at) <= mapping._utc(self.completed_at)
                         == mapping._utc(self.reference_time)
                         and self.budget.completed_at == self.completed_at
                         and self.budget.collection_id == self.collection_id, "COLLECTION_REFERENCE")
        mapping._require(all(self.started_at <= r.started_at <= r.received_at <= self.reference_time for r in self.requests)
                         and len(self.requests) == len(self.budget.attempts)
                         and len({r.request_identity for r in self.requests}) == len(self.requests), "COLLECTION_RECEIPT_LINEAGE")
        elapsed = self.reference_time - mapping._EPOCH
        mapping._require((elapsed.days*86400+elapsed.seconds)//60*60 == self.planned_cutoff,
                         "COLLECTION_CUTOFF_REFERENCE")
        for record, attempt in zip(self.requests, self.budget.attempts):
            record.wire_request.__post_init__()
            mapping._require(record.wire_digest == record.wire_request.request_identity
                and record.scope == record.wire_request.scope
                and (attempt.timeout,attempt.response_cap) == (record.wire_request.timeout,record.wire_request.max_response_bytes),
                "COLLECTION_WIRE_LINEAGE")
        self.policy.validate(); self.operational_budget.__post_init__()
        mapping._require(all((a.started_at,a.received_at,a.kind) == (r.started_at,r.received_at,r.scope)
                         for a,r in zip(self.budget.attempts,self.requests)), "COLLECTION_ATTEMPT_LINEAGE")
        mapping._require(self.collection_digest == _digest(self.material()), "COLLECTION_DIGEST_MISMATCH")


@dataclass(frozen=True)
class A1CollectedValuation:
    key: A1ValuationRequestKey
    response: OhlcvResponse


@dataclass(frozen=True)
class A1CollectionPacket:
    context: A1CollectionContext
    policy: mapping.A1Policy
    verification_envelopes: tuple[mapping.RpcEnvelope, ...]
    discovery_envelopes: tuple[mapping.RpcEnvelope, ...]
    reserve_envelopes: tuple[tuple[str, tuple[mapping.RpcEnvelope, ...]], ...]
    valuations: tuple[A1CollectedValuation, ...]

    def replay_sources(self):
        """Fresh one-shot mapper instances; the packet has no transport reference."""
        return self._replay_stage(self.context.requests)

    def _replay_stage(self, stage_records):
        """Pure A1-stage checks; common packets validate global coverage separately."""
        self.context.validate()
        mapping._require(self.policy == self.context.policy, "COLLECTION_POLICY_LINEAGE")
        reference = self.context.reference_time
        records = {r.request_identity:r for r in stage_records}
        envelopes = (*self.verification_envelopes,*self.discovery_envelopes,
                     *(e for _,es in self.reserve_envelopes for e in es))
        mapping._require(len({e.request_id for e in envelopes}) == len(envelopes), "COLLECTION_RPC_DUPLICATE")
        seen = set()
        for e in envelopes:
            identity = "rpc:"+str(e.request_id)
            record = records.get(identity)
            mapping._require(record is not None and record.response_digest == hashlib.sha256(e.body).hexdigest()
                and (record.started_at,record.received_at) == (e.started_at,e.received_at), "COLLECTION_RPC_LINEAGE")
            wire_body = json.dumps({"jsonrpc":"2.0","id":e.request_id,"method":e.method,
                "params":json.loads(e.params_json)},sort_keys=True,separators=(",", ":"),allow_nan=False).encode()
            mapping._require(record.wire_request.method == "POST" and record.wire_request.body == wire_body
                             and record.scope == "solana", "COLLECTION_RPC_WIRE_LINEAGE")
            seen.add(identity)
        mapping._require(len(self.verification_envelopes) == 3, "COLLECTION_VERIFICATION_REQUIRED")
        cluster = verify_cluster(self.verification_envelopes[0], reference_time=reference)
        program = verify_program(*self.verification_envelopes[1:], reference_time=reference)
        mapping._require(cluster == self.context.cluster and program == self.context.program,
                         "COLLECTION_VERIFICATION_LINEAGE")
        discovery = mapping.OfflineA1DiscoverySource(self.discovery_envelopes, self.policy)
        reserve_sets = dict(self.reserve_envelopes)
        mapping._require(len(reserve_sets) == len(self.reserve_envelopes), "COLLECTION_RESERVE_DUPLICATE")
        prices = {}
        for item in self.valuations:
            item.key.validate()
            req = item.response.request
            mapping._require(item.key.collection_id == self.context.collection_id
                and req.reference_time == reference and req.url == item.key.endpoint_url
                and req.parameters == item.key.parameters and req.cutoff == self.context.planned_cutoff
                and (req.base_mint,req.quote_mint,req.timeout,req.max_response_bytes)
                    == (item.key.base_mint,item.key.quote_mint,item.key.timeout,item.key.maxbytes),
                "COLLECTION_PRICE_REFERENCE")
            record_id = "usd:"+item.key.request_digest
            record = records.get(record_id)
            mapping._require(record is not None and record.response_digest == hashlib.sha256(item.response.body).hexdigest()
                and (record.started_at,record.received_at) == (item.response.started_at,item.response.received_at), "COLLECTION_USD_LINEAGE")
            wire = A1HttpRequest("valuation",req.url,"GET",b"",req.timeout,req.max_response_bytes)
            mapping._require(record.wire_request == wire, "COLLECTION_USD_WIRE_LINEAGE")
            seen.add(record_id)
            identity = (req.pool_address, req.token_mint)
            mapping._require(identity not in prices, "COLLECTION_PRICE_DUPLICATE")
            prices[identity] = item.response
        mapping._require(seen == set(records), "COLLECTION_REQUEST_SET_LINEAGE")
        def reserves(candidate, keys):
            mapping._require(candidate.token_mint in reserve_sets, "COLLECTION_RESERVE_MISSING")
            return reserve_sets[candidate.token_mint]
        def usd(reserve):
            mapping._require(all((reserve.pool, m) in prices for m in (reserve.mint_0, reserve.mint_1)),
                             "COLLECTION_PRICE_MISSING")
            return tuple(prices[(reserve.pool, m)] for m in (reserve.mint_0, reserve.mint_1))
        return discovery, mapping.OfflineA1PoolSource(discovery, reserves, usd)


class A1OperationalCollectionService:
    """One terminal collection, exclusively through a caller-supplied transport.

    Raw facts for lexical candidates may be collected before P03; collection
    does not decide eligibility, choose a pool, score or start a paper cycle.
    The existing bounded owners perform those decisions on the completed packet.
    """
    def __init__(self, *, collection_id, environment, intended_chain_identity,
                 rpc_endpoint, opener, clock, budget, policy,
                 rpc_timeout=timedelta(seconds=10), usd_timeout=timedelta(seconds=10),
                 usd_max_bytes=1048576):
        mapping._require(type(collection_id) is str and 0 < len(collection_id) <= 128
            and environment in ("development", "test", "staging", "production")
            and intended_chain_identity == MAINNET_GENESIS_HASH, "COLLECTION_CONFIGURATION")
        mapping._require(type(budget) is A1OperationalBudget and type(policy) is mapping.A1Policy
            and callable(opener) and callable(clock), "COLLECTION_INJECTIONS_REQUIRED")
        budget.__post_init__(); policy.validate()
        A1HttpRequest("solana", rpc_endpoint, "POST", b"{}", rpc_timeout, 8192)
        mapping._require(type(usd_timeout) is timedelta and timedelta(0) < usd_timeout <= timedelta(seconds=30)
            and type(usd_max_bytes) is int and 1 <= usd_max_bytes <= 1048576, "COLLECTION_USD_LIMITS")
        self.collection_id, self.environment, self.intended_chain_identity = collection_id, environment, intended_chain_identity
        self.rpc_endpoint, self.opener, self.clock = rpc_endpoint, opener, clock
        self.budget, self.policy = budget, policy
        self.rpc_timeout, self.usd_timeout, self.usd_max_bytes = rpc_timeout, usd_timeout, usd_max_bytes
        self.called = False
        self.status = "NOT_STARTED"
        self.failure_reason = None
        self.packet = None

    def _make_ledger(self, started):
        return A1BudgetLedger(self.budget, self.collection_id, started, self.rpc_endpoint, COINGECKO_ORIGIN)

    def _collect_extra_stage(self, transport, next_id, facts, tokens, records,
                             *, reserve_sets, registry, started):
        return next_id

    def _closed(self):
        pass

    def _sealed(self):
        pass

    def _make_context(self, material):
        return A1CollectionContext(**material, collection_digest=_digest(material))

    def _make_packet(self, context, verification, discovery, reserves, valuations):
        return A1CollectionPacket(context, self.policy, verification, discovery, reserves, valuations)

    def _success(self):
        self.status = "COLLECTION_COMPLETED"

    def _stopped(self):
        self.status = "COLLECTION_STOPPED"

    def collect_once(self):
        mapping._require(not self.called, "SECOND_COLLECTION_FORBIDDEN")
        self.called = True
        self.status = "COLLECTING"
        ledger = None
        try:
            started = mapping._utc(self.clock())
            ledger = self._make_ledger(started)
            transport = A1BoundedTransport(rpc_endpoint=self.rpc_endpoint, opener=self.opener, clock=self.clock, ledger=ledger)
            elapsed = started - mapping._EPOCH
            cutoff = (elapsed.days * 86400 + elapsed.seconds) // 60 * 60
            registry = A1CollectionRequestRegistry(self.collection_id, cutoff)
            records = []
            next_id = 0
            def rpc(method, params, cap):
                nonlocal next_id
                next_id += 1
                envelope = transport.rpc(method, params, request_id=next_id, timeout=self.rpc_timeout, max_bytes=cap)
                body = json.dumps({"jsonrpc":"2.0","id":next_id,"method":method,"params":params},
                                  sort_keys=True,separators=(",", ":"),allow_nan=False).encode()
                wire = A1HttpRequest("solana", self.rpc_endpoint, "POST", body, self.rpc_timeout, cap)
                records.append(A1CollectionRequestRecord("rpc:"+str(next_id), wire.request_identity,
                    hashlib.sha256(envelope.body).hexdigest(), envelope.started_at, envelope.received_at, "solana", wire))
                return envelope
            genesis = rpc("getGenesisHash", cluster_params(), 8192)
            verify_cluster(genesis, reference_time=genesis.received_at)
            probe = rpc("getMultipleAccounts", program_probe_params(), 8192)
            address, slot = program_probe_identity(probe, reference_time=probe.received_at)
            program_snapshot = rpc("getMultipleAccounts", program_snapshot_params(address, slot), 16384)
            program = verify_program(probe, program_snapshot, reference_time=program_snapshot.received_at)
            s = rpc("getSlot", [{"commitment":"finalized"}], 8192)
            slot = mapping._slot(s.read("getSlot", [{"commitment":"finalized"}], s.received_at, 8192))
            mapping._require(slot >= program.context_slot, "DISCOVERY_PRECEDES_VERIFICATION")
            block_params = [slot, {"commitment":"finalized","encoding":"jsonParsed","transactionDetails":"full",
                                   "maxSupportedTransactionVersion":0,"rewards":False}]
            block = rpc("getBlock", block_params, 1048576)
            event_time = rpc("getBlockTime", [slot], 8192)
            discovery_envelopes = (s, block, event_time)
            facts = mapping.map_discovery(discovery_envelopes, reference_time=event_time.received_at, policy=self.policy)
            tokens = sorted({m for sw in facts.swaps for m in (sw.mint_0, sw.mint_1)})[:5]
            mapping._require(len(tokens) <= self.budget.max_discovery_candidates, "COLLECTION_CANDIDATE_BUDGET")
            reserve_sets = []
            for mint in tokens:
                pools = {sw.pool for sw in facts.swaps if mint in (sw.mint_0, sw.mint_1)}
                mapping._require(len(pools) <= self.budget.max_pools_per_candidate, "COLLECTION_POOL_BUDGET")
                keys = mapping.pool_account_keys(facts, mint)
                account_params = [list(keys), {"commitment":"finalized","encoding":"base64","minContextSlot":facts.slot}]
                accounts = rpc("getMultipleAccounts", account_params, 1048576)
                result = accounts.read("getMultipleAccounts", account_params, accounts.received_at, 1048576)
                mapping._require(type(result) is dict and type(result.get("context")) is dict, "ACCOUNT_CONTEXT_REQUIRED")
                account_slot = mapping._slot(result["context"].get("slot"))
                time = rpc("getBlockTime", [account_slot], 8192)
                envelopes = (accounts, time)
                reserves = mapping.map_reserves(facts, mint, envelopes, reference_time=time.received_at, policy=self.policy)
                reserve_sets.append((mint, envelopes))
                for reserve in reserves:
                    for asset in (reserve.mint_0, reserve.mint_1):
                        planned = OhlcvRequest("solana", asset, reserve.pool, reserve.mint_0, reserve.mint_1,
                                               started, self.usd_timeout, self.usd_max_bytes)
                        key = A1ValuationRequestKey.from_parameters(collection_id=self.collection_id, planned_cutoff=cutoff,
                            endpoint_version=ENDPOINT_VERSION, endpoint_url=planned.url, network="solana",pool=reserve.pool,
                            mint=asset, parameters=planned.parameters, base_mint=reserve.mint_0,quote_mint=reserve.mint_1,
                            timeout=self.usd_timeout,maxbytes=self.usd_max_bytes)
                        def collect_price():
                            receipt = transport.http(A1HttpRequest("valuation", planned.url, "GET", b"", self.usd_timeout, self.usd_max_bytes))
                            # Parse source bytes before completion; do not invent a provisional mapper response/T.
                            _, _, _, _, candles = _parse(receipt.body, planned)
                            stamp, _ = candles[-1]
                            begin = mapping._EPOCH + timedelta(seconds=stamp)
                            end = begin + timedelta(seconds=60)
                            mapping._require(stamp == cutoff-60 and end <= receipt.received_at
                                and receipt.received_at-begin <= self.policy.stale_after, "STALE_OR_MISSING_CLOSED_INTERVAL")
                            records.append(A1CollectionRequestRecord("usd:"+key.request_digest, receipt.request.request_identity,
                                receipt.body_digest, receipt.started_at, receipt.received_at, "valuation", receipt.request))
                            return receipt
                        receipt = registry.get_or_collect(key, collect_price)
                        _, _, _, _, candles = _parse(receipt.body, planned)
                        begin = mapping._EPOCH + timedelta(seconds=candles[-1][0])
                        end = begin + timedelta(seconds=60)
                        mapping._require(max(abs(reserve.observed_at-begin), abs(reserve.observed_at-end))
                                         <= self.policy.max_skew, "RESERVE_PRICE_SKEW")
            self._collect_extra_stage(transport, next_id, facts, tokens, records,
                                      reserve_sets=tuple(reserve_sets), registry=registry, started=started)
            self._closed()
            completed = mapping._utc(self.clock())
            # This is the single final T. A cutoff change is terminal, never a recollection/retry.
            reuse = registry.seal(completed)
            snapshot = ledger.seal(completed)
            self._sealed()
            cluster = verify_cluster(genesis, reference_time=completed)
            program = verify_program(probe, program_snapshot, reference_time=completed)
            final_facts = mapping.map_discovery(discovery_envelopes, reference_time=completed, policy=self.policy)
            valuations = []
            price_map = {}
            for key, receipt in registry.entries:
                request = OhlcvRequest(key.network,key.mint,key.pool,key.base_mint,key.quote_mint,
                                      completed,key.timeout,key.maxbytes)
                mapping._require(request.url == key.endpoint_url and request.parameters == key.parameters
                                 and request.cutoff == cutoff, "REFERENCE_WIRE_IDENTITY_CONFLICT")
                response = OhlcvResponse(request,receipt.started_at,receipt.received_at,receipt.body,receipt.status)
                valuations.append(A1CollectedValuation(key,response))
                price_map[(key.pool,key.mint)] = response
            for mint, envelopes in reserve_sets:
                final_reserves = mapping.map_reserves(final_facts,mint,envelopes,reference_time=completed,policy=self.policy)
                for reserve in final_reserves:
                    mapping.value_pool(reserve,mint,tuple(price_map[(reserve.pool,m)] for m in (reserve.mint_0,reserve.mint_1)),
                                       reference_time=completed,policy=self.policy)
            material = dict(collection_id=self.collection_id,environment=self.environment,
                intended_chain_identity=self.intended_chain_identity,started_at=started,completed_at=completed,
                reference_time=completed,planned_cutoff=cutoff,requests=tuple(records),reuse=reuse,budget=snapshot,
                policy=self.policy,operational_budget=self.budget,cluster=cluster,program=program,
                transport_contract_version=TRANSPORT_VERSION,contract_version=VERSION)
            context = self._make_context(material)
            context.validate()
            packet = self._make_packet(context,(genesis,probe,program_snapshot),
                discovery_envelopes,tuple(reserve_sets),tuple(valuations))
            packet.replay_sources()
            self.packet = packet
            self._success()
            return packet
        except mapping.A1SourceError as exc:
            if ledger is not None: ledger.abort()
            self.failure_reason = str(exc)
            self._stopped()
            raise
        except Exception:
            if ledger is not None: ledger.abort()
            self.failure_reason = "COLLECTION_FAILED"
            self._stopped()
            raise mapping.A1SourceError("COLLECTION_FAILED") from None
