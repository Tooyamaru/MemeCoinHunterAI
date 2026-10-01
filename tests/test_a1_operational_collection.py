"""Fake wire providers only; source time is independent of transport clocks."""
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
import base64
import io
import json
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

from core.data.a1_operational_collection import A1OperationalCollectionService
from core.data.a1_collection_budget import A1OperationalBudget
from core.data.a1_source_verification import MAINNET_GENESIS_HASH, PROGRAM
from core.data.a1_cpmm_sources import A1SourceError
from core.data.bounded_cycle_sources import BoundedDiscoveryOwner, BoundedPoolCandidateOwner
from core.data.contracts import FreshnessPolicy
from tests import test_a1_cpmm_sources as fixture
from tests import test_a1_source_verification as identity


class FakeClock:
    def __init__(self, start=fixture.T, step=timedelta(milliseconds=1)):
        self.value, self.step = start, step
        self.closed = False
    def __call__(self):
        if self.closed: raise AssertionError("clock/transport unavailable after frozen T")
        value = self.value; self.value += self.step
        return value


class FakeResponse:
    status = 200
    def __init__(self, body): self.stream = io.BytesIO(body); self.closed = False
    def read(self, amount): return self.stream.read(amount)
    def close(self): self.closed = True


class FakeProvider:
    def __init__(self, start=fixture.T):
        self.start = start
        self.calls = []
        self.closed = False
        self.genesis = MAINNET_GENESIS_HASH
        self.http_failure = None
    def __call__(self, request, *, timeout):
        if self.closed: raise AssertionError("provider invoked after T")
        self.calls.append(request)
        if request.method == "GET":
            qs=parse_qs(urlsplit(request.endpoint).query)
            cutoff=int(qs["before_timestamp"][0]); mint=qs["token"][0]
            # Increasing base history supports the independent P04/P05 integration.
            prices = ("13","11","10") if mint == fixture.M0 else ("1.000001",)*3
            rows=",".join(f"[{cutoff-i*60},{p},{p},{p},{p},100]" for i,p in zip((1,2,3),prices))
            body=('{"data":{"id":"fake-collected-a1","type":"ohlcv_request_response",'
                  '"attributes":{"ohlcv_list":['+rows+']}},"meta":{"base":{"address":"'
                  +fixture.M0+'"},"quote":{"address":"'+fixture.M1+'"}}}').encode()
            response=FakeResponse(body)
            if self.http_failure: response.status=self.http_failure
            return response
        rpc=json.loads(request.body); method,params=rpc["method"],rpc["params"]
        if method == "getGenesisHash": result=self.genesis
        elif method == "getSlot": result=123
        elif method == "getBlock":
            result=json.loads(fixture.discovery_envelopes()[1].body)["result"]
            result["blockTime"]=int((self.start-timedelta(seconds=20)).timestamp())
        elif method == "getBlockTime":
            result=int((self.start-timedelta(seconds=20 if params[0]==123 else 3)).timestamp())
        elif method == "getMultipleAccounts" and params[0] == [PROGRAM]:
            result={"context":{"slot":120},"value":[identity.program()]}
        elif method == "getMultipleAccounts" and params[0] == [PROGRAM,identity.PROGRAMDATA]:
            result={"context":{"slot":121},"value":[identity.program(),identity.programdata()]}
        elif method == "getMultipleAccounts":
            result=json.loads(fixture.reserve_envelopes()[0].body)["result"]
            keys=fixture.a1.pool_account_keys(fixture.facts(),fixture.M0)
            account_map=dict(zip(keys,result["value"]))
            result={"context":{"slot":124},"value":[account_map[k] for k in params[0]]}
        else: raise AssertionError("unplanned provider request")
        return FakeResponse(fixture.encode({"jsonrpc":"2.0","id":rpc["id"],"result":result}))


def collector(clock=None, provider=None, budget=None, collection_id="collection:one"):
    clock=clock or FakeClock();provider=provider or FakeProvider()
    owner=A1OperationalCollectionService(collection_id=collection_id,environment="test",
        intended_chain_identity=MAINNET_GENESIS_HASH,rpc_endpoint="https://solana.example.invalid",
        opener=provider,clock=clock,budget=budget or A1OperationalBudget(timedelta(seconds=55)),policy=fixture.POLICY)
    return owner,clock,provider


class CollectionTests(unittest.TestCase):
    def setUp(self):
        for name in ("socket.create_connection","socket.socket.connect"):
            guard=patch(name,side_effect=AssertionError("real provider/network prohibited"));guard.start();self.addCleanup(guard.stop)

    def test_complete_facts_freeze_reference_and_replay_real_bounded_owners(self):
        owner,clock,provider=collector();packet=owner.collect_once()
        T=packet.context.reference_time
        self.assertEqual(T,packet.context.completed_at)
        self.assertGreater(T,max(r.received_at for r in packet.context.requests))
        self.assertEqual(len(provider.calls),12)  # ten RPC, two unique USD
        self.assertEqual(sum(r.method=="GET" for r in provider.calls),2)
        self.assertEqual([u.reused for u in packet.context.reuse],[False,False,True,True])
        self.assertEqual(len(packet.context.budget.attempts),12)
        self.assertEqual(packet.context.program.verification_level,"LEVEL_1")
        clock.closed=provider.closed=True
        discovery,pools=packet.replay_sources()
        snapshot=BoundedDiscoveryOwner(discovery).discover(reference_time=T,processing_time=T,
            freshness_policy=FreshnessPolicy(stale_after=timedelta(seconds=180)),evaluation_id="collected")
        self.assertEqual(discovery.facts.observed_at,fixture.T-timedelta(seconds=20))
        for candidate in snapshot.candidates:
            selected=BoundedPoolCandidateOwner(pools).select(candidate,reference_time=T,
                freshness_policy=FreshnessPolicy(stale_after=timedelta(seconds=180)))
            self.assertEqual(selected.liquidity_usd,fixture.valued().liquidity_usd)
            self.assertEqual(selected.observed_at,fixture.T-timedelta(seconds=3))
        with self.assertRaisesRegex(A1SourceError,"SECOND_COLLECTION_FORBIDDEN"):owner.collect_once()
        self.assertEqual(owner.status,"COLLECTION_COMPLETED")

    def test_deterministic_digest_and_frozen_context(self):
        a,_,_=collector();b,_,_=collector()
        left,right=a.collect_once(),b.collect_once()
        self.assertEqual(left,right)
        with self.assertRaises(FrozenInstanceError):left.context.reference_time=fixture.T
        other,_,_=collector(collection_id="collection:two")
        self.assertNotEqual(other.collect_once().context.collection_digest,left.context.collection_digest)

    def test_cluster_cannot_be_skipped_before_discovery(self):
        owner,_,provider=collector();provider.genesis=fixture.key(100)
        with self.assertRaisesRegex(A1SourceError,"CLUSTER_IDENTITY_MISMATCH"):owner.collect_once()
        self.assertEqual(len(provider.calls),1)
        self.assertEqual(owner.status,"COLLECTION_STOPPED")
        with self.assertRaisesRegex(A1SourceError,"SECOND_COLLECTION_FORBIDDEN"):owner.collect_once()

    def test_small_call_budget_fails_before_next_transport(self):
        owner,_,provider=collector(budget=A1OperationalBudget(timedelta(seconds=55),max_http_calls=3))
        with self.assertRaisesRegex(A1SourceError,"HTTP_CALL_BUDGET_EXHAUSTED"):owner.collect_once()
        self.assertEqual(len(provider.calls),3)

    def test_candidate_and_pool_caps_stop_without_silent_truncation(self):
        owner,_,provider=collector(budget=A1OperationalBudget(timedelta(seconds=55),max_discovery_candidates=1))
        with self.assertRaisesRegex(A1SourceError,"COLLECTION_CANDIDATE_BUDGET"):owner.collect_once()
        self.assertEqual(len(provider.calls),6)
        owner,_,provider=collector(budget=A1OperationalBudget(timedelta(seconds=55),max_pools_per_candidate=0))
        with self.assertRaisesRegex(A1SourceError,"COLLECTION_POOL_BUDGET"):owner.collect_once()
        self.assertEqual(len(provider.calls),6)

    def test_cutoff_rollover_stops_instead_of_changing_query(self):
        owner,_,provider=collector(clock=FakeClock(fixture.T.replace(second=59),timedelta(milliseconds=20)))
        with self.assertRaises(A1SourceError):owner.collect_once()
        self.assertIsNone(owner.packet)
        self.assertEqual(owner.status,"COLLECTION_STOPPED")
        with self.assertRaisesRegex(A1SourceError,"SECOND_COLLECTION_FORBIDDEN"):owner.collect_once()

    def test_http_failure_not_retried_and_no_partial_packet(self):
        owner,_,provider=collector();provider.http_failure=429
        with self.assertRaises(A1SourceError):owner.collect_once()
        self.assertEqual(sum(r.method=="GET" for r in provider.calls),1)
        self.assertIsNone(owner.packet)

    def test_packet_response_tamper_breaks_lineage(self):
        owner,_,_=collector();packet=owner.collect_once()
        item=packet.valuations[0]
        bad=replace(packet,valuations=(replace(item,response=replace(item.response,body=b"tampered")),*packet.valuations[1:]))
        with self.assertRaisesRegex(A1SourceError,"COLLECTION_USD_LINEAGE"):bad.replay_sources()
        env=packet.discovery_envelopes[0]
        bad=replace(packet,discovery_envelopes=(replace(env,body=env.body+b" "),*packet.discovery_envelopes[1:]))
        with self.assertRaisesRegex(A1SourceError,"COLLECTION_RPC_LINEAGE"):bad.replay_sources()

    def test_packet_wire_and_cutoff_contract_rechecked(self):
        from core.data.a1_operational_collection import _digest
        owner,_,_=collector();packet=owner.collect_once()
        record=packet.context.requests[0]
        wire=replace(record.wire_request,body=record.wire_request.body+b" ")
        altered=replace(record,wire_request=wire,wire_digest=wire.request_identity)
        context=replace(packet.context,requests=(altered,*packet.context.requests[1:]))
        context=replace(context,collection_digest=_digest(context.material()))
        with self.assertRaisesRegex(A1SourceError,"COLLECTION_RPC_WIRE_LINEAGE"):
            replace(packet,context=context).replay_sources()
        context=replace(packet.context,planned_cutoff=packet.context.planned_cutoff-60)
        context=replace(context,collection_digest=_digest(context.material()))
        with self.assertRaisesRegex(A1SourceError,"COLLECTION_CUTOFF_REFERENCE"):
            replace(packet,context=context).replay_sources()

    def test_registry_response_reuse_retains_single_clock_and_body(self):
        owner,_,_=collector();packet=owner.collect_once()
        for original,reuse in zip(packet.context.reuse[:2],packet.context.reuse[2:]):
            self.assertEqual((original.request_digest,original.response_digest,original.started_at,original.received_at),
                             (reuse.request_digest,reuse.response_digest,reuse.started_at,reuse.received_at))


if __name__=="__main__":unittest.main()
