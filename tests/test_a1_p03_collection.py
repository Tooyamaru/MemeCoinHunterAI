"""All source facts use an injected fake; real/default network is forbidden."""
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
import json
from unittest.mock import patch

import pytest

from core.data.a1_p03_collection import A1P03CollectionService, _digest
from core.data.a1_collection_budget import A1OperationalBudget, A1BudgetLedger
from core.data.a1_bounded_transport import A1BoundedTransport
from core.data.a1_cpmm_sources import A1SourceError, TOKEN_PROGRAM
from core.data.a1_source_verification import MAINNET_GENESIS_HASH
from core.data.contracts import FreshnessPolicy
from core.data.bounded_cycle_sources import BoundedDiscoveryOwner, BoundedPoolCandidateOwner
from core.risk.safety_evaluation import evaluate_safety_evidence
from core.risk.safety_eligibility import derive_token_eligibility
from tests.test_a1_operational_collection import FakeProvider, FakeClock, FakeResponse
from tests import test_a1_cpmm_sources as f

FRESHNESS = FreshnessPolicy(timedelta(seconds=180))


class SafetyProvider(FakeProvider):
    def __init__(self, *, distinct_slots=False, change=None, start=f.T):
        super().__init__(start)
        self.distinct_slots, self.change = distinct_slots, change

    def __call__(self, request, *, timeout):
        if request.scope != "safety": return super().__call__(request, timeout=timeout)
        assert not self.closed, "post-T transport forbidden"
        self.calls.append(request)
        rpc = json.loads(request.body)
        method, params = rpc["method"], rpc["params"]
        slots = {"getAccountInfo":124,"getTokenLargestAccounts":125,"getTokenSupply":126}
        slot = slots.get(method,124) if self.distinct_slots else 124
        if method == "getAccountInfo":
            value = {"owner":TOKEN_PROGRAM,"executable":False,"data":{"parsed":{"type":"mint","info":{
                "decimals":6,"isInitialized":True,"mintAuthority":None,"freezeAuthority":None}}}}
        elif method == "getTokenLargestAccounts":
            value = [{"address":f.key(99),"amount":"10","decimals":6}]
        elif method == "getTokenSupply": value = {"amount":"1000","decimals":6}
        elif method == "getBlockTime": value = int((self.start-timedelta(seconds=3)).timestamp())
        else: raise AssertionError(method)
        result = value if method == "getBlockTime" else {"context":{"slot":slot},"value":value}
        data = {"jsonrpc":"2.0","id":rpc["id"],"result":result}
        if self.change: self.change(method, data, rpc)
        return FakeResponse(json.dumps(data, separators=(",", ":")).encode())


def collect(provider=None, clock=None, **overrides):
    provider, clock = provider or SafetyProvider(), clock or FakeClock()
    args = dict(collection_id="common:one",environment="test",intended_chain_identity=MAINNET_GENESIS_HASH,
        rpc_endpoint="https://solana.example.invalid",opener=provider,clock=clock,
        budget=A1OperationalBudget(timedelta(seconds=55)),policy=f.POLICY,
        freshness_policy=FRESHNESS,max_top_holder_fraction=0.1,
        safety_timeout=timedelta(seconds=10),safety_max_bytes=262144)
    args.update(overrides)
    return A1P03CollectionService(**args), clock, provider


@pytest.fixture(autouse=True)
def network_guard(monkeypatch):
    def forbidden(*a, **kw): raise AssertionError("real/default network forbidden")
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("socket.getaddrinfo", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("core.data.solana_oaf_source.SolanaJsonRpcSource.snapshot_mint", forbidden)
    monkeypatch.setattr("backend.application.oaf_solana_upstream_composition.OafSolanaCanonicalComposer.compose", forbidden)


def replay(packet):
    discovery, safety, pools = packet.replay_sources()
    T = packet.context.reference_time
    snapshot = discovery.discover(reference_time=T,processing_time=T,freshness_policy=FRESHNESS,evaluation_id="exact")
    return discovery,safety,pools,snapshot


def test_common_happy_path_exact_owner_once_no_io_deterministic():
    owner, clock, provider = collect()
    packet = owner.collect_once()
    assert owner.transitions == ("CREATED","COLLECTING","CLOSED","SEALED","FROZEN")
    assert len(packet.manifest) == 2
    assert len(packet.context.budget.attempts) == len(provider.calls) == 20
    assert sum(a.kind == "safety" for a in packet.context.budget.attempts) == 8
    clock.closed = provider.closed = True
    with patch.object(BoundedDiscoveryOwner,"discover",autospec=True,side_effect=BoundedDiscoveryOwner.discover) as owner_spy:
        discovery,safety,_,snapshot = replay(packet)
        assert owner_spy.call_count == 1
        assert discovery.record.snapshot is snapshot
        output = []
        for c in snapshot.candidates:
            evidence = safety.evidence_once(c,snapshot,reference_time=packet.context.reference_time)
            assert len(evidence.evidence) == 2
            for e in evidence.evidence:
                assert e.p02_reference.evaluation_id == "exact"
                assert e.p02_reference.state_digest == snapshot.predecessor.state_digest
                assert e.observed_at == f.T-timedelta(seconds=3)
                assert e.data_age == packet.context.reference_time-e.observed_at
            evaluation = evaluate_safety_evidence(evidence,evaluation_timestamp=packet.context.reference_time)
            eligibility = derive_token_eligibility(evaluation)
            output.append((evidence.representation_digest,evaluation.representation_digest,_digest(eligibility)))
        assert len(safety.evidence_bindings) == 2
        assert owner_spy.call_count == 1
    discovery2,safety2,_,snapshot2 = replay(packet)
    for c, expected in zip(snapshot2.candidates,output):
        evidence = safety2.evidence_once(c,snapshot2,reference_time=packet.context.reference_time)
        evaluation = evaluate_safety_evidence(evidence,evaluation_timestamp=packet.context.reference_time)
        eligibility = derive_token_eligibility(evaluation)
        assert (evidence.representation_digest,evaluation.representation_digest,_digest(eligibility)) == expected
    assert len(provider.calls) == 20


def test_same_slot_lookup_reuse_and_no_cross_mint_cache():
    owner,_,provider=collect();packet=owner.collect_once()
    lookups=[json.loads(r.body) for r in provider.calls if r.scope == "safety" and json.loads(r.body)["method"]=="getBlockTime"]
    assert len(lookups) == len(packet.manifest) == 2
    assert lookups[0]["id"] != lookups[1]["id"]
    for raw in packet.safety:
        assert all(r.block_time is raw.reads[0].block_time for r in raw.reads)


def test_distinct_slots_charge_six_per_mint():
    owner,_,_=collect(SafetyProvider(distinct_slots=True));packet=owner.collect_once()
    assert sum(a.kind == "safety" for a in packet.context.budget.attempts) == 12
    assert len({r.block_time.request_id for raw in packet.safety for r in raw.reads}) == 6


@pytest.mark.parametrize("change",[
    lambda method,d,r: d["result"]["value"]["data"]["parsed"]["info"].pop("mintAuthority") if method=="getAccountInfo" else None,
    lambda method,d,r: d["result"]["value"].update(owner=f.key(50)) if method=="getAccountInfo" else None,
    lambda method,d,r: d["result"]["value"].update(executable=True) if method=="getAccountInfo" else None,
    lambda method,d,r: d["result"]["value"]["data"]["parsed"].update(type="account") if method=="getAccountInfo" else None,
    lambda method,d,r: d["result"].update(value=None) if method=="getAccountInfo" else None,
    lambda method,d,r: d["result"].update(value=[]) if method=="getTokenLargestAccounts" else None,
    lambda method,d,r: d["result"]["value"].extend(d["result"]["value"]*20) if method=="getTokenLargestAccounts" else None,
    lambda method,d,r: d["result"]["value"].append(d["result"]["value"][0].copy()) if method=="getTokenLargestAccounts" else None,
    lambda method,d,r: d["result"]["value"][0].update(decimals=5) if method=="getTokenLargestAccounts" else None,
    lambda method,d,r: d["result"]["value"].update(decimals=5) if method=="getTokenSupply" else None,
    lambda method,d,r: d["result"]["value"].update(amount="0") if method=="getTokenSupply" else None,
    lambda method,d,r: d["result"]["value"].update(amount="1") if method=="getTokenSupply" else None,
    lambda method,d,r: d["result"]["value"].update(amount="1.2") if method=="getTokenSupply" else None,
    lambda method,d,r: d.update(result=None) if method=="getBlockTime" else None,
    lambda method,d,r: d.update(result=int((f.T+timedelta(seconds=1)).timestamp())) if method=="getBlockTime" else None,
    lambda method,d,r: d.update(result=int((f.T-timedelta(seconds=200)).timestamp())) if method=="getBlockTime" else None,
    lambda method,d,r: d["result"]["context"].update(slot=122) if method=="getTokenSupply" else None,
    lambda method,d,r: d.update(id=999) if method=="getAccountInfo" else None,
    lambda method,d,r: d.pop("result") if method=="getTokenSupply" else None,
])
def test_malformed_partial_clock_or_identity_stops(change):
    owner,_,provider=collect(SafetyProvider(change=change))
    with pytest.raises(A1SourceError): owner.collect_once()
    assert owner.status == "STOPPED" and owner.packet is None
    count=len(provider.calls)
    with pytest.raises(A1SourceError): owner.collect_once()
    assert len(provider.calls)==count


def test_budget_exhaustion_before_opener_and_failure_charged():
    owner,_,provider=collect(budget=A1OperationalBudget(timedelta(seconds=55),max_safety_calls=1))
    with pytest.raises(A1SourceError,match="KIND_CALL_BUDGET_EXHAUSTED"): owner.collect_once()
    assert sum(r.scope == "safety" for r in provider.calls) == 1


@pytest.mark.parametrize("cap",[20,262145])
def test_safety_body_limits(cap):
    with pytest.raises(A1SourceError):
        owner,_,_=collect(safety_max_bytes=cap);owner.collect_once()


def test_no_second_collection_or_mutation():
    owner,_,_=collect();packet=owner.collect_once()
    with pytest.raises(FrozenInstanceError): packet.context.reference_time=f.T
    with pytest.raises(FrozenInstanceError): packet.safety[0].reads[0].envelope.body=b"changed"
    with pytest.raises(A1SourceError): owner.collect_once()
    assert owner.status=="STOPPED"


def resign(packet): return replace(packet,packet_digest=_digest(packet.material()))


def test_exact_coverage_tamper_and_v1_rejects_safety_records():
    owner,_,_=collect();packet=owner.collect_once()
    with pytest.raises(A1SourceError,match="COLLECTION_REQUEST_SET_LINEAGE"): packet.a1.replay_sources()
    with pytest.raises(A1SourceError): resign(replace(packet,safety=packet.safety[:1])).validate()
    with pytest.raises(A1SourceError): resign(replace(packet,safety=packet.safety*2)).validate()
    raw=packet.safety[0];read=raw.reads[0]
    bad=replace(raw,reads=(replace(read,envelope=replace(read.envelope,body=read.envelope.body+b" ")),*raw.reads[1:]))
    with pytest.raises(A1SourceError): resign(replace(packet,safety=(bad,*packet.safety[1:]))).validate()


@pytest.mark.parametrize("mutation",["snapshot","candidate","time","evaluation","repeat"])
def test_exact_predecessor_and_emission_mismatch_terminal(mutation):
    owner,_,_=collect();packet=owner.collect_once();discovery,safety,_,snapshot=replay(packet)
    c=snapshot.candidates[0];T=packet.context.reference_time
    if mutation=="snapshot": snapshot=replace(snapshot)
    elif mutation=="candidate": c=replace(c)
    elif mutation=="time": T += timedelta(microseconds=1)
    elif mutation=="evaluation":
        # Even object.__setattr__ tampering is caught by binding digest validation.
        object.__setattr__(snapshot.predecessor,"evaluation_id","different")
    elif mutation=="repeat": safety.evidence_once(c,snapshot,reference_time=T)
    with pytest.raises(A1SourceError): safety.evidence_once(c,snapshot,reference_time=T)
    assert discovery.stopped


def test_final_canonical_membership_rejection_no_partial_success():
    owner,_,provider=collect();packet=owner.collect_once();discovery,safety,_=packet.replay_sources()
    real=BoundedDiscoveryOwner.discover
    def reject(self,**kw):
        result=real(self,**kw)
        return replace(result,candidates=result.candidates[:1])
    with patch.object(BoundedDiscoveryOwner,"discover",reject):
        with pytest.raises(A1SourceError,match="P03_FINAL_MEMBERSHIP"):
            discovery.discover(reference_time=packet.context.reference_time,processing_time=packet.context.reference_time,
                freshness_policy=FRESHNESS,evaluation_id="exact")
    assert discovery.record is None and discovery.stopped
    assert len(provider.calls)==20 and safety.evidence_bindings==()


def test_safety_method_profile_and_rpc_ids_do_not_loosen_legacy():
    clock=FakeClock();provider=SafetyProvider();ledger=A1BudgetLedger(A1OperationalBudget(timedelta(seconds=55)),
        "profile",f.T,"https://solana.example.invalid","https://api.coingecko.com")
    transport=A1BoundedTransport(rpc_endpoint="https://solana.example.invalid",opener=provider,clock=clock,ledger=ledger)
    with pytest.raises(A1SourceError): transport.rpc("getTokenSupply",[f.M0],request_id=1)
    assert not provider.calls
    transport.rpc("getSlot",[{"commitment":"finalized"}],request_id=1)
    with pytest.raises(A1SourceError): transport.rpc_safety("getBlockTime",[124],request_id=1,timeout=timedelta(seconds=10),max_bytes=262144)
    assert len(provider.calls)==1


def test_credential_projection_requires_sanitized_origin():
    with pytest.raises(A1SourceError,match="P03_SAFE_PROVIDER_ORIGIN"):
        collect(rpc_endpoint="https://solana.example.invalid/opaque-path?opaque-query=fake")
    owner,_,_=collect();packet=owner.collect_once()
    material=json.dumps(__import__('core.data.a1_operational_collection',fromlist=['_canonical'])._canonical(packet.material()))
    assert "Authorization" not in material
    assert packet.context.provider_identity=="solana.example.invalid"


class ManyProvider(SafetyProvider):
    """Six valid raw mints; source/canonical policy selects lexical five."""
    def __init__(self, empty=False):
        super().__init__(distinct_slots=True)
        self.empty = empty
        self.pairs = {f.key(30+i):(f.key(1+2*i),f.key(2+2*i),f.key(100+2*i),f.key(101+2*i)) for i in range(3)}

    def __call__(self,request,*,timeout):
        import base64
        from urllib.parse import urlsplit,parse_qs
        if request.scope == "safety": return super().__call__(request,timeout=timeout)
        rpc = json.loads(request.body) if request.method=="POST" else None
        if rpc and rpc["method"]=="getBlock":
            response=super().__call__(request,timeout=timeout)
            data=json.loads(response.stream.getvalue())
            instructions=[f.swap(pool=pool,m0=a,m1=b,v0=v0,v1=v1) for pool,(a,b,v0,v1) in self.pairs.items()]
            data["result"]["transactions"]=[] if self.empty else [f.transaction(instructions)]
            return FakeResponse(f.encode(data))
        if rpc and rpc["method"]=="getMultipleAccounts" and len(rpc["params"][0])>2:
            self.calls.append(request)
            accounts={}
            for pool,(a,b,v0,v1) in self.pairs.items():
                body=bytearray(f.pool_bytes())
                for index,key in {2:v0,3:v1,5:a,6:b}.items():
                    body[8+32*index:8+32*(index+1)]=f.a1._decode(key,32)
                body=bytes(body)
                def account(owner,data): return {"owner":owner,"executable":False,"data":[base64.b64encode(data).decode(),"base64"]}
                accounts[pool]=account(f.a1.PROGRAM,body)
                accounts[a]=account(TOKEN_PROGRAM,f.mint_bytes())
                accounts[b]=account(TOKEN_PROGRAM,f.mint_bytes())
                accounts[v0]=account(TOKEN_PROGRAM,f.vault_bytes(a,2_000_000))
                accounts[v1]=account(TOKEN_PROGRAM,f.vault_bytes(b,3_000_000))
            result={"context":{"slot":124},"value":[accounts[k] for k in rpc["params"][0]]}
            return FakeResponse(f.encode({"jsonrpc":"2.0","id":rpc["id"],"result":result}))
        if request.method=="GET":
            self.calls.append(request)
            pool=request.endpoint.split('/pools/')[1].split('/')[0]
            a,b,_,_=self.pairs[pool]
            cutoff=int(parse_qs(urlsplit(request.endpoint).query)["before_timestamp"][0])
            data={"data":{"id":"fake-many","type":"ohlcv_request_response","attributes":{"ohlcv_list":
                [[cutoff-i*60,1,1,1,1,100] for i in (1,2,3)]}},"meta":{"base":{"address":a},"quote":{"address":b}}}
            return FakeResponse(f.encode(data))
        return super().__call__(request,timeout=timeout)


def test_five_mints_thirty_safety_rpc_no_sixth_replacement():
    owner,_,provider=collect(ManyProvider());packet=owner.collect_once()
    assert len(packet.manifest)==5
    assert sum(a.kind=="safety" for a in packet.context.budget.attempts)==30
    assert sum(a.kind=="solana" for a in packet.context.budget.attempts)==16
    discovery,safety,_,snapshot=replay(packet)
    assert len(snapshot.candidates)==5
    for c in snapshot.candidates: safety.evidence_once(c,snapshot,reference_time=packet.context.reference_time)
    assert len(provider.calls)==52  # 46 RPC plus six distinct valuation requests.
    assert packet.context.budget.reserved_response_bytes <= 81354752


def test_empty_discovery_has_zero_safety_calls_and_existing_empty_snapshot():
    owner,_,provider=collect(ManyProvider(empty=True));packet=owner.collect_once()
    assert packet.manifest==packet.safety==()
    assert len(provider.calls)==6
    _,_,_,snapshot=replay(packet)
    assert snapshot.candidates==()


@pytest.mark.parametrize("target",[125,126])
def test_holder_and_supply_clock_each_checked_at_final_T(target):
    def change(method,data,rpc):
        if method=="getBlockTime" and rpc["params"]==[target]:
            data["result"]=int((f.T-timedelta(seconds=200)).timestamp())
    owner,_,_=collect(SafetyProvider(distinct_slots=True,change=change))
    with pytest.raises(A1SourceError): owner.collect_once()


def test_clock_cutoff_rollover_no_reopen():
    owner,_,_=collect(clock=FakeClock(f.T.replace(second=59),timedelta(milliseconds=20)))
    with pytest.raises(A1SourceError): owner.collect_once()
    assert owner.status=="STOPPED" and owner.packet is None


def test_duplicate_json_rpc_error_timeout_and_overflow_no_retry():
    for mode in ("duplicate","error","overflow","timeout"):
        provider=SafetyProvider()
        def opener(request,*,timeout):
            response=provider(request,timeout=timeout)
            if request.scope=="safety":
                if mode=="timeout": raise TimeoutError("fake")
                if mode=="overflow": return FakeResponse(b"x"*262145)
                rpc=json.loads(request.body)
                if mode=="error": return FakeResponse(f.encode({"jsonrpc":"2.0","id":rpc["id"],"error":{"code":-1}}))
                return FakeResponse(b'{"jsonrpc":"2.0","id":1,"id":2,"result":null}')
            return response
        owner,_,_=collect(provider,opener=opener)
        with pytest.raises(A1SourceError): owner.collect_once()
        assert sum(r.scope=="safety" for r in provider.calls)==1
        assert owner.status=="STOPPED"


def test_second_bind_terminal_and_fresh_instance_allowed():
    owner,_,_=collect();packet=owner.collect_once();discovery,_,_,_=replay(packet)
    with pytest.raises(A1SourceError,match="P03_SECOND_BIND"):
        discovery.discover(reference_time=packet.context.reference_time,processing_time=packet.context.reference_time,
                           freshness_policy=FRESHNESS,evaluation_id="exact")
    assert discovery.stopped
    replay(packet)


@pytest.mark.asyncio
async def test_real_caller_owns_evaluation_and_eligibility_once_per_candidate():
    from backend.application import autonomous_paper_one_cycle as cycle
    owner,clock,provider=collect();packet=owner.collect_once();clock.closed=provider.closed=True
    discovery,safety,pools=packet.replay_sources()
    class ForbiddenMarket:
        def compose(self,*a,**kw): raise AssertionError("no RTI-11 in P03-only harness")
    service=cycle.AutonomousPaperOneCycleService(discovery=discovery,safety=safety,pools=BoundedPoolCandidateOwner(
            type("EmptyPools",(),{"pools_once":lambda *a,**kw:()})()),
        market=ForbiddenMarket(),paper_request_factory=lambda *a:None,persistence=None)
    T=packet.context.reference_time
    command=cycle.AutonomousPaperCycleRequest("exact",T,T,T,FRESHNESS,timedelta(seconds=10),16384)
    with (patch.object(cycle,"evaluate_safety_evidence",wraps=cycle.evaluate_safety_evidence) as evaluation,
         patch.object(cycle,"derive_token_eligibility",wraps=cycle.derive_token_eligibility) as eligibility):
        result=await service.run(command)
    assert evaluation.call_count==eligibility.call_count==2
    assert result.outcome in (cycle.CycleOutcome.NO_VALID_POOL,cycle.CycleOutcome.NO_ELIGIBLE_CANDIDATE)
    for ev,el in zip(evaluation.call_args_list,eligibility.call_args_list):
        assert ev.kwargs["evaluation_timestamp"]==T
        assert el.args[0].input_evidence_digest==ev.args[0].representation_digest
    assert len(provider.calls)==20


@pytest.mark.parametrize("method,params",[("getSlot",[]),("getTokenSupply",[f.M0,{"commitment":"confirmed"}]),("getBlockTime",[True])])
def test_bad_safety_profile_is_terminal_before_any_io(method,params):
    provider=SafetyProvider();clock=FakeClock()
    ledger=A1BudgetLedger(A1OperationalBudget(timedelta(seconds=55)),"bad-profile",f.T,
        "https://solana.example.invalid","https://api.coingecko.com")
    transport=A1BoundedTransport(rpc_endpoint="https://solana.example.invalid",opener=provider,clock=clock,ledger=ledger)
    with pytest.raises(A1SourceError): transport.rpc_safety(method,params,request_id=1,timeout=timedelta(seconds=10),max_bytes=262144)
    with pytest.raises(A1SourceError): transport.rpc_safety("getBlockTime",[124],request_id=2,timeout=timedelta(seconds=10),max_bytes=262144)
    assert not provider.calls


def test_safety_thirty_second_profile_does_not_relax_legacy_envelope():
    provider=SafetyProvider();clock=FakeClock(step=timedelta(0))
    def opener(request,**kw):
        response=provider(request,**kw)
        clock.value+=timedelta(seconds=15)
        return response
    ledger=A1BudgetLedger(A1OperationalBudget(timedelta(seconds=55)),"safety-deadline",f.T,
        "https://solana.example.invalid","https://api.coingecko.com")
    transport=A1BoundedTransport(rpc_endpoint="https://solana.example.invalid",opener=opener,clock=clock,ledger=ledger)
    env=transport.rpc_safety("getBlockTime",[124],request_id=1,timeout=timedelta(seconds=30),max_bytes=262144)
    env.read_safety("getBlockTime",[124],env.received_at,262144)
    with pytest.raises(A1SourceError,match="RPC_RECEIPT_OR_DEADLINE"): env.read("getBlockTime",[124],env.received_at,262144)
    ledger.seal(env.received_at)
    count=len(provider.calls)
    with pytest.raises(A1SourceError): transport.rpc_safety("getBlockTime",[124],request_id=2,timeout=timedelta(seconds=30),max_bytes=262144)
    assert len(provider.calls)==count


@pytest.mark.parametrize("threshold,authority",[(0.001,None),(0.1,f.key(45))])
def test_canonical_safety_fail_preserved(threshold,authority):
    def change(method,data,rpc):
        if method=="getAccountInfo": data["result"]["value"]["data"]["parsed"]["info"]["mintAuthority"]=authority
    owner,_,_=collect(SafetyProvider(change=change),max_top_holder_fraction=threshold)
    packet=owner.collect_once();_,safety,_,snapshot=replay(packet)
    evidence=safety.evidence_once(snapshot.candidates[0],snapshot,reference_time=packet.context.reference_time)
    evaluation=evaluate_safety_evidence(evidence,evaluation_timestamp=packet.context.reference_time)
    eligibility=derive_token_eligibility(evaluation)
    assert eligibility.status.value=="INELIGIBLE"
    assert eligibility.evaluator_id=="p03-t03-eligibility-derivation"
    assert eligibility.contract_version==evaluation.contract_version=="p03-t02-v1"
    assert eligibility.evidence_references==evaluation.evidence_references


def test_exact_mapped_collection_matches_existing_pure_composer():
    from backend.application.oaf_solana_upstream_composition import OafSolanaCanonicalComposer
    from core.risk.safety_evidence import P02StateReference, SafetyEvidenceCollection
    owner,_,_=collect();packet=owner.collect_once();_,safety,_,snapshot=replay(packet)
    c=snapshot.candidates[0];p=snapshot.predecessor;T=packet.context.reference_time
    raw=next(r for r in packet.safety if r.mint==c.token_mint)
    expected=SafetyEvidenceCollection.from_evidence(OafSolanaCanonicalComposer._compose_p03(
        raw.view(packet.context,packet.validate()),T,FRESHNESS,
        P02StateReference(p.state_version,p.state_digest,p.materializer_contract_version,p.evaluation_id),0.1))
    assert safety.evidence_once(c,snapshot,reference_time=T)==expected


def test_cross_mint_clock_contradiction_stops_without_reusing_lookup():
    calls=0
    def change(method,data,rpc):
        nonlocal calls
        if method=="getBlockTime":
            calls+=1
            if calls==2: data["result"]-=1
    owner,_,provider=collect(SafetyProvider(change=change))
    with pytest.raises(A1SourceError,match="P03_SESSION_CLOCK_CONFLICT"): owner.collect_once()
    assert sum(r.scope=="safety" and json.loads(r.body)["method"]=="getBlockTime" for r in provider.calls)==2
    assert owner.packet is None


def test_mutated_slot_and_clock_fail_even_with_recomputed_packet_digest():
    owner,_,_=collect();packet=owner.collect_once();raw=packet.safety[0];read=raw.reads[0]
    changed=replace(raw,reads=(replace(read,source_time=read.source_time+timedelta(seconds=1)),*raw.reads[1:]))
    with pytest.raises(A1SourceError,match="P03_SOURCE_LINEAGE"):
        resign(replace(packet,safety=(changed,*packet.safety[1:]))).validate()


def test_captured_policy_mutation_stops_before_safety_io():
    provider=SafetyProvider()
    owner,_,_=collect(provider)
    real=owner.opener
    def opener(request,**kw):
        response=real(request,**kw)
        if request.method=="GET": owner.max_top_holder_fraction=0.9
        return response
    owner.opener=opener
    with pytest.raises(A1SourceError,match="P03_CONFIGURATION_MUTATION"): owner.collect_once()
    assert not any(r.scope=="safety" for r in provider.calls)
    assert owner.packet is None and owner.status=="STOPPED"


def test_safety_extra_nonfinite_json_value_rejected():
    provider=SafetyProvider()
    def opener(request,**kw):
        response=provider(request,**kw)
        if request.scope=="safety":
            body=response.stream.getvalue().replace(b'"value":',b'"extra":1e999,"value":')
            return FakeResponse(body)
        return response
    owner,_,_=collect(provider,opener=opener)
    with pytest.raises(A1SourceError,match="INVALID_JSON_NUMBER"): owner.collect_once()
    assert sum(r.scope=="safety" for r in provider.calls)==1


@pytest.mark.parametrize("field",["requests","valuations","safety","reads"])
def test_mutable_container_substitution_rejected_even_if_digest_identical(field):
    owner,_,_=collect();packet=owner.collect_once()
    if field=="requests":
        context=replace(packet.context,requests=list(packet.context.requests))
        changed=replace(packet,a1=replace(packet.a1,context=context))
    elif field=="valuations": changed=replace(packet,a1=replace(packet.a1,valuations=list(packet.a1.valuations)))
    elif field=="safety": changed=replace(packet,safety=list(packet.safety))
    else:
        raw=replace(packet.safety[0],reads=list(packet.safety[0].reads))
        changed=replace(packet,safety=(raw,*packet.safety[1:]))
    assert _digest(changed.material())==packet.packet_digest
    with pytest.raises(A1SourceError): changed.validate()
