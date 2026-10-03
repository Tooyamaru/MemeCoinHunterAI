"""Only injected synthetic wire facts; the operational endpoint is not qualified."""
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest

from core.data import a1_rti11_collection as r
from core.data.a1_collection_budget import A1OperationalBudget
from core.data.a1_operational_collection import _digest
from core.data.a1_p03_collection import CommonCollectionPacket, CommonCollectionContext
from core.data.a1_cpmm_sources import A1SourceError
from core.data.a1_source_verification import MAINNET_GENESIS_HASH
from core.data.bounded_cycle_sources import BoundedDiscoveryOwner, BoundedPoolCandidateOwner
from core.data.contracts import FreshnessPolicy
from core.risk.safety_evaluation import evaluate_safety_evidence
from core.risk.safety_eligibility import derive_token_eligibility
from backend.application.market_to_opportunity_composition import P01Rti11CompositionRequest
from tests.test_a1_p03_collection import SafetyProvider, ManyProvider, network_guard  # noqa: F401
from tests.test_a1_operational_collection import FakeClock, FakeResponse
from tests import test_a1_cpmm_sources as f

FRESHNESS = FreshnessPolicy(timedelta(minutes=4))
TIMEOUT = timedelta(seconds=10)
CAP = 1048576


class DiagnosticProvider(SafetyProvider):
    def __init__(self, *, diagnostic_change=None, **kwargs):
        super().__init__(**kwargs)
        self.diagnostic_change = diagnostic_change

    def __call__(self, request, *, timeout):
        response = super().__call__(request, timeout=timeout)
        if request.scope == "diagnostic":
            data = json.loads(response.stream.getvalue())
            mint = parse_qs(urlsplit(request.endpoint).query)["token"][0]
            quote = f.M1 if mint == f.M0 else f.M0
            data["meta"] = {"base": {"address": mint}, "quote": {"address": quote}}
            if self.diagnostic_change: self.diagnostic_change(data)
            return FakeResponse(f.encode(data))
        return response


class ManyDiagnostics(ManyProvider):
    def __call__(self, request, *, timeout):
        response = super().__call__(request, timeout=timeout)
        if request.scope == "diagnostic":
            data = json.loads(response.stream.getvalue())
            mint = parse_qs(urlsplit(request.endpoint).query)["token"][0]
            pool = request.endpoint.split("/pools/")[1].split("/")[0]
            a, b, _, _ = self.pairs[pool]
            data["meta"] = {"base": {"address": mint}, "quote": {"address": b if mint == a else a}}
            return FakeResponse(f.encode(data))
        return response


class TracedCollection(r.A1Rti11CollectionService):
    def _make_ledger(self, started):
        self.ledger = super()._make_ledger(started)
        return self.ledger

    def _closed(self):
        self.closed_clock = self.clock.value
        self.closed_calls = len(self.opener.calls) if hasattr(self.opener, "calls") else None
        super()._closed()


def collect(provider=None, clock=None, **overrides):
    provider, clock = provider or DiagnosticProvider(), clock or FakeClock()
    args = dict(collection_id="rti11:one", environment="test", intended_chain_identity=MAINNET_GENESIS_HASH,
        rpc_endpoint="https://solana.example.invalid", opener=provider, clock=clock,
        budget=A1OperationalBudget(timedelta(seconds=55)), policy=f.POLICY,
        freshness_policy=FRESHNESS, max_top_holder_fraction=0.1,
        safety_timeout=TIMEOUT, safety_max_bytes=262144,
        diagnostic_timeout=TIMEOUT, diagnostic_max_bytes=CAP)
    args.update(overrides)
    return TracedCollection(**args), clock, provider


def graph(packet):
    discovery, safety, pools, market = packet.replay_sources()
    T = packet.context.reference_time
    snapshot = discovery.discover(reference_time=T, processing_time=T,
                                 freshness_policy=FRESHNESS, evaluation_id="exact")
    return discovery, safety, pools, market, snapshot


def handoff(packet, owners=None, index=0):
    discovery, safety, pools, market, snapshot = owners or graph(packet)
    candidate = snapshot.candidates[index]
    T = packet.context.reference_time
    collection = safety.evidence_once(candidate, snapshot, reference_time=T)
    evaluation = evaluate_safety_evidence(collection, evaluation_timestamp=T)
    eligibility = derive_token_eligibility(evaluation)
    pool = pools.select(candidate, reference_time=T, freshness_policy=FRESHNESS)
    request = P01Rti11CompositionRequest(candidate.candidate_id, snapshot.predecessor, pool.target(),
        evaluation, eligibility, T, packet.context.diagnostic_timeout, packet.context.diagnostic_max_bytes,
        FRESHNESS, T, T, "exact")
    return (discovery, safety, pools, market, snapshot), (candidate, snapshot, collection, evaluation, eligibility, pool, request)


def resign(packet):
    return replace(packet, packet_digest=_digest(packet.material()))


def test_common_session_reuses_only_exact_orientation_and_one_final_T():
    owner, clock, provider = collect()
    with (patch.object(BoundedDiscoveryOwner, "discover", side_effect=AssertionError("pre-T P02 forbidden")),
          patch.object(BoundedPoolCandidateOwner, "select", side_effect=AssertionError("pre-T selection forbidden"))):
        packet = owner.collect_once()
    c = packet.context
    assert owner.transitions == ("CREATED", "COLLECTING", "CLOSED", "SEALED", "FROZEN")
    assert c.reference_time == c.completed_at == c.budget.completed_at == owner.closed_clock
    assert clock.value == c.reference_time + clock.step  # only one final clock read after CLOSED
    assert owner.closed_calls == len(provider.calls) == len(c.requests) == len(c.budget.attempts) == 21
    assert [a.kind for a in c.budget.attempts].count("diagnostic") == 1
    assert [a.kind for a in c.budget.attempts].count("safety") == 8
    assert [d.reused_a1 for d in packet.diagnostics] == [True, False]
    reused, separate = packet.diagnostics
    assert reused.response is next(v.response for v in packet.a1.valuations if v.key == reused.key)
    assert separate.response.request.base_mint == f.M1 and separate.returned_quote == f.M0
    # Same URL/candles for M1 cannot authorize reuse: original metadata is M0/M1.
    original = next(v for v in packet.a1.valuations if v.key.mint == f.M1)
    assert original.key.endpoint_url == separate.key.endpoint_url and original.key != separate.key
    assert original.response.body != separate.response.body
    assert c.budget.reserved_response_bytes == sum(a.response_cap for a in c.budget.attempts)
    assert c.budget.actual_response_bytes == sum(a.response_bytes for a in c.budget.attempts)
    assert all(d.candle_opens[0] < d.candle_ends[-1] <= d.response.received_at <= c.reference_time
               for d in packet.diagnostics)
    clock.closed = provider.closed = True
    packet.validate()
    with pytest.raises(FrozenInstanceError): c.reference_time = f.T
    with pytest.raises(FrozenInstanceError): separate.response.body = b"replacement"
    with pytest.raises(A1SourceError): owner.ledger.seal(c.reference_time)
    with pytest.raises(A1SourceError): owner.collect_once()
    assert len(provider.calls) == 21 and owner.packet is packet


def test_original_request_p02_p03_pool_and_canonical_owners_pure_replay():
    owner, clock, provider = collect(); packet = owner.collect_once()
    clock.closed = provider.closed = True
    with (patch.object(BoundedDiscoveryOwner, "discover", autospec=True,
                       side_effect=BoundedDiscoveryOwner.discover) as discovery_call,
          patch.object(BoundedPoolCandidateOwner, "select", autospec=True,
                       side_effect=BoundedPoolCandidateOwner.select) as selection,
          patch.object(r, "derive_price_direction", wraps=r.derive_price_direction) as diagnostic):
        owners = graph(packet)
        for i in range(2):
            owners, args = handoff(packet, owners, i)
            market = owners[3]
            market.bind_upstream(*args)
            result = market.compose(args[-1])
            assert result.request is args[-1]
            assert result.outcome.value == "COMPOSED"
            record = market.bindings[-1]
            assert record.snapshot is owners[-1] and record.request.predecessor is owners[-1].predecessor
            assert record.collection is args[2] and record.evaluation is args[3] and record.eligibility is args[4]
            assert record.pool_record.selected is args[5]
            assert record.request.target is args[-1].target
            assert diagnostic.call_args.kwargs["response"] is record.fact.response
            assert diagnostic.call_args.kwargs["predecessor"] is args[-1].predecessor
            assert diagnostic.call_args.kwargs["evaluation_time"] == packet.context.reference_time
            assert market.lineage[-1].result_digest == result.result_digest
        assert discovery_call.call_count == 1 and selection.call_count == diagnostic.call_count == 2
    owners2, args2 = handoff(packet)
    owners2[3].bind_upstream(*args2)
    assert owners2[3].compose(args2[-1]).result_digest == owners[3].lineage[0].result_digest
    assert len(provider.calls) == 21


@pytest.mark.parametrize("changes", [dict(diagnostic_timeout=timedelta(seconds=9)),
                                     dict(diagnostic_max_bytes=16384)])
def test_different_profile_requires_two_separate_pre_T_attempts(changes):
    owner, _, provider = collect(**changes); packet = owner.collect_once()
    assert not any(d.reused_a1 for d in packet.diagnostics)
    assert len(provider.calls) == 22
    assert sum(a.kind == "diagnostic" for a in packet.context.budget.attempts) == 2


@pytest.mark.parametrize("field,value", [
    ("collection_id", "foreign"), ("endpoint_version", "foreign-v1"), ("network", "ethereum"),
    ("pool", f.key(60)), ("mint", f.M1), ("base_mint", f.M1), ("quote_mint", f.M0),
    ("planned_cutoff", 0), ("endpoint_url", "https://api.coingecko.com/foreign"),
    ("parameters", (("aggregate", "2"),)), ("timeout", timedelta(seconds=9)), ("maxbytes", 16384),
])
def test_invalid_reuse_key_rejected_after_recomputed_packet_digest(field, value):
    owner, _, _ = collect(); packet = owner.collect_once(); fact = packet.diagnostics[0]
    changed = replace(fact, key=replace(fact.key, **{field: value}))
    with pytest.raises((A1SourceError, ValueError)):
        resign(replace(packet, diagnostics=(changed, *packet.diagnostics[1:]))).validate()


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "reordered", "orphan", "attempt", "body",
    "request", "response_copy", "reuse_flag", "reserve", "event", "timestamps", "mutable"])
def test_exact_fact_coverage_and_underlying_material_tamper(mutation):
    owner, _, _ = collect(); packet = owner.collect_once()
    fact, other = packet.diagnostics
    if mutation == "missing": changed = (fact,)
    elif mutation == "duplicate": changed = (fact, fact, other)
    elif mutation == "reordered": changed = (other, fact)
    elif mutation == "mutable": changed = list(packet.diagnostics)
    else:
        if mutation == "orphan": fact = replace(fact, record_identity=other.record_identity)
        elif mutation == "attempt": fact = replace(fact, attempt_identity=other.attempt_identity)
        elif mutation == "body": fact = replace(fact, response=replace(fact.response, body=fact.response.body+b" "))
        elif mutation == "request": fact = replace(fact, response=replace(fact.response,
            request=replace(fact.response.request, max_response_bytes=16384)))
        elif mutation == "response_copy": fact = replace(fact, response=replace(fact.response))
        elif mutation == "reuse_flag": fact = replace(fact, reused_a1=False)
        elif mutation == "reserve": fact = replace(fact, target=replace(fact.target,
            reserve=replace(fact.target.reserve, reserve_0=fact.target.reserve.reserve_0+1)))
        elif mutation == "event": fact = replace(fact, target=replace(fact.target, source_event_id="different"))
        elif mutation == "timestamps": fact = replace(fact, source_timestamps=fact.source_timestamps[::-1])
        changed = (fact, other)
    with pytest.raises((A1SourceError, ValueError, TypeError)):
        resign(replace(packet, diagnostics=changed)).validate()


@pytest.mark.parametrize("mutation", ["snapshot", "candidate", "predecessor", "collection", "evaluation",
    "eligibility", "pool", "target_reference", "target_mints", "time", "limits", "processing", "evaluation_id"])
def test_handoff_requires_actual_canonical_objects_and_exact_target(mutation):
    owner, _, _ = collect(); packet = owner.collect_once()
    owners, args = handoff(packet)
    args = list(args); request = args[-1]
    if mutation in ("snapshot", "candidate", "collection", "evaluation", "eligibility", "pool"):
        index = {"candidate": 0, "snapshot": 1, "collection": 2, "evaluation": 3, "eligibility": 4, "pool": 5}[mutation]
        args[index] = replace(args[index])
    elif mutation == "predecessor": args[-1] = replace(request, predecessor=replace(request.predecessor))
    elif mutation == "target_reference": args[-1] = replace(request,
        target=replace(request.target, target_reference_digest="f"*64))
    elif mutation == "target_mints": args[-1] = replace(request,
        target=replace(request.target, base_mint=f.M1, quote_mint=f.M0))
    elif mutation == "time": args[-1] = replace(request, reference_time=request.reference_time+timedelta(seconds=1))
    elif mutation == "limits": args[-1] = replace(request, max_response_bytes=16384)
    elif mutation == "processing": args[-1] = replace(request, processing_time=request.processing_time+timedelta(seconds=1))
    elif mutation == "evaluation_id": args[-1] = replace(request, evaluation_id="different")
    with pytest.raises(A1SourceError): owners[3].bind_upstream(*args)
    assert owners[0].stopped
    with pytest.raises(A1SourceError): owners[3].compose(request)


@pytest.mark.parametrize("mutation", ["request_copy", "evaluation_copy", "eligibility_copy", "predecessor_copy",
                                     "target_copy", "metric", "source", "reference", "repeat"])
def test_registered_originals_cannot_be_substituted_after_binding(mutation):
    owner, _, _ = collect(); packet = owner.collect_once()
    owners, args = handoff(packet); market = owners[3]; market.bind_upstream(*args); request = args[-1]
    if mutation == "request_copy": request = replace(request)
    elif mutation.endswith("_copy"):
        field = {"evaluation_copy": "safety_evaluation", "eligibility_copy": "eligibility",
                 "predecessor_copy": "predecessor", "target_copy": "target"}[mutation]
        object.__setattr__(request, field, replace(getattr(request, field)))
    elif mutation in ("metric", "source", "reference"):
        field, value = {"metric": ("liquidity_usd", args[5].liquidity_usd+1),
                        "source": ("source_id", "foreign"), "reference": ("reference_id", "foreign")}[mutation]
        object.__setattr__(args[5], field, value)
    else: market.compose(request)
    with pytest.raises(A1SourceError): market.compose(request)
    assert owners[0].stopped


@pytest.mark.parametrize("change", [
    lambda d: d["meta"]["base"].update(address=f.M0),
    lambda d: d["meta"]["quote"].update(address=f.key(60)),
    lambda d: d["data"]["attributes"]["ohlcv_list"].pop(),
    lambda d: d["data"]["attributes"]["ohlcv_list"][0].__setitem__(0, d["data"]["attributes"]["ohlcv_list"][0][0]+60),
    lambda d: d["data"]["attributes"]["ohlcv_list"][0].__setitem__(0, d["data"]["attributes"]["ohlcv_list"][0][0]+1),
    lambda d: d["data"]["attributes"].update(ohlcv_list=[[row[0]-60, *row[1:]] for row in d["data"]["attributes"]["ohlcv_list"]]),
])
def test_wrong_returned_reserves_window_future_or_interval_STOP(change):
    owner, _, provider = collect(DiagnosticProvider(diagnostic_change=change))
    with pytest.raises(A1SourceError): owner.collect_once()
    assert owner.status == "STOPPED" and owner.packet is None
    assert sum(p.scope == "diagnostic" for p in provider.calls) == 1


def test_oldest_candle_age_is_not_just_A1_latest_close_age():
    owner, _, provider = collect(freshness_policy=FreshnessPolicy(timedelta(seconds=180)))
    with pytest.raises(A1SourceError, match="RTI11_SOURCE_WINDOW"): owner.collect_once()
    assert owner.packet is None and not any(p.scope == "diagnostic" for p in provider.calls)


def test_complete_plan_over_lower_cap_STOP_before_any_separate_call():
    owner, _, provider = collect(ManyDiagnostics(), diagnostic_max_bytes=16384,
                                budget=A1OperationalBudget(timedelta(seconds=55), max_diagnostics=4))
    with pytest.raises(A1SourceError, match="RTI11_DIAGNOSTIC_PLAN_BUDGET"): owner.collect_once()
    assert len(provider.calls) == len(owner.ledger.snapshot().attempts) == 52
    assert owner.packet is None and not any(p.scope == "diagnostic" for p in provider.calls)
    with pytest.raises(A1SourceError): owner.collect_once()
    assert len(provider.calls) == 52


def test_five_mints_all_incidence_coverage_and_thirty_safety_calls():
    owner, _, provider = collect(ManyDiagnostics()); packet = owner.collect_once()
    assert len(packet.manifest) == len(packet.diagnostics) == 5
    assert sum(a.kind == "solana" for a in packet.context.budget.attempts) == 16
    assert sum(a.kind == "safety" for a in packet.context.budget.attempts) == 30
    assert sum(a.kind == "diagnostic" for a in packet.context.budget.attempts) == 2
    assert len(provider.calls) == 54
    assert packet.context.budget.reserved_response_bytes <= 86597632


def test_empty_manifest_preserves_empty_canonical_discovery():
    owner, _, provider = collect(ManyDiagnostics(empty=True)); packet = owner.collect_once()
    assert packet.manifest == packet.safety == packet.diagnostics == ()
    assert graph(packet)[-1].candidates == ()
    assert len(provider.calls) == 6


def test_legacy_v1_public_validators_reject_diagnostic_packet():
    owner, _, _ = collect(); packet = owner.collect_once()
    with pytest.raises(A1SourceError): packet.a1.replay_sources()
    with pytest.raises(A1SourceError): CommonCollectionPacket.validate(packet)
    with pytest.raises(A1SourceError): CommonCollectionContext.validate(packet.context)


@pytest.mark.parametrize("mode", ["timeout", "overflow", "status", "duplicate", "nonfinite"])
def test_failed_attempt_remains_charged_and_never_retried(mode):
    provider = DiagnosticProvider()
    def opener(request, **kw):
        response = provider(request, **kw)
        if request.scope == "diagnostic":
            if mode == "timeout": raise TimeoutError("synthetic timeout")
            if mode == "overflow": return FakeResponse(b"x"*1048577)
            if mode == "status": response.status = 503
            if mode == "duplicate": return FakeResponse(b'{"data":null,"data":null}')
            if mode == "nonfinite": return FakeResponse(response.stream.getvalue().replace(b'"meta":', b'"extra":1e999,"meta":'))
        return response
    owner, _, _ = collect(provider, opener=opener)
    with pytest.raises(A1SourceError): owner.collect_once()
    attempts = owner.ledger.snapshot().attempts
    assert len(attempts) == len(provider.calls) == 21 and attempts[-1].kind == "diagnostic"
    assert attempts[-1].response_cap == CAP
    with pytest.raises(A1SourceError): owner.collect_once()
    assert len(provider.calls) == 21 and owner.packet is None


def test_budget_exhaustion_does_not_invoke_diagnostic_opener():
    owner, _, provider = collect(budget=A1OperationalBudget(timedelta(seconds=55), max_http_calls=20))
    with pytest.raises(A1SourceError): owner.collect_once()
    assert len(provider.calls) == 20 and not any(p.scope == "diagnostic" for p in provider.calls)
    assert owner.packet is None


def test_cutoff_rollover_and_nonmonotone_clock_STOP():
    for clock in (FakeClock(f.T.replace(second=59), timedelta(milliseconds=20)),
                  FakeClock(step=-timedelta(milliseconds=1))):
        owner, _, _ = collect(clock=clock)
        with pytest.raises(A1SourceError): owner.collect_once()
        assert owner.packet is None and owner.status == "STOPPED"


@pytest.mark.parametrize("kwargs", [dict(diagnostic_timeout=timedelta(0)),
    dict(diagnostic_timeout=timedelta(seconds=31)), dict(diagnostic_max_bytes=0), dict(diagnostic_max_bytes=1048577)])
def test_explicit_diagnostic_limits_rejected_before_I_O(kwargs):
    provider = DiagnosticProvider()
    with pytest.raises(A1SourceError): collect(provider, **kwargs)
    assert provider.calls == []


@pytest.mark.parametrize("mutation", ["wire_body", "url", "kind", "host", "body_digest", "length",
    "start", "receipt", "pending", "missing", "extra", "version", "policy", "cutoff", "final_T"])
def test_global_ledger_and_diagnostic_wires_cannot_be_resigned_into_validity(mutation):
    owner, _, _ = collect(); packet = owner.collect_once(); c = packet.context
    records, attempts = list(c.requests), list(c.budget.attempts)
    row, attempt = records[-1], attempts[-1]
    if mutation == "wire_body":
        wire = replace(row.wire_request, method="POST", body=b"{}")
        records[-1] = replace(row, wire_request=wire, wire_digest=wire.request_identity)
    elif mutation in ("url", "host"):
        endpoint = (row.wire_request.endpoint.replace("api.coingecko.com", "other.example.invalid")
                    if mutation == "host" else row.wire_request.endpoint.replace("aggregate=1", "aggregate=2"))
        wire = replace(row.wire_request, endpoint=endpoint)
        records[-1] = replace(row, wire_request=wire, wire_digest=wire.request_identity)
    elif mutation == "kind":
        wire = replace(row.wire_request, scope="valuation")
        records[-1] = replace(row, scope="valuation", wire_request=wire, wire_digest=wire.request_identity)
        attempts[-1] = replace(attempt, kind="valuation")
    elif mutation == "body_digest": records[-1] = replace(row, response_digest="f"*64)
    elif mutation == "length": attempts[-1] = replace(attempt, response_bytes=attempt.response_bytes-1)
    elif mutation == "start": records[-1] = replace(row, started_at=row.started_at-timedelta(seconds=1))
    elif mutation == "receipt": records[-1] = replace(row, received_at=row.received_at+timedelta(seconds=1))
    elif mutation == "pending": attempts[-1] = replace(attempt, received_at=None)
    elif mutation == "missing": records.pop(); attempts.pop()
    elif mutation == "extra":
        records.append(replace(row, request_identity="orphan"))
        attempts.append(replace(attempt, identity=attempt.identity+1))
    budget = replace(c.budget, attempts=tuple(attempts),
                     reserved_response_bytes=sum(a.response_cap for a in attempts),
                     actual_response_bytes=sum(a.response_bytes for a in attempts))
    c = replace(c, requests=tuple(records), budget=budget)
    if mutation == "version": c = replace(c, price_direction_version="foreign")
    elif mutation == "policy": c = replace(c, freshness_policy=FreshnessPolicy(timedelta(seconds=180)))
    elif mutation == "cutoff": c = replace(c, planned_cutoff=c.planned_cutoff-60)
    elif mutation == "final_T": c = replace(c, reference_time=c.reference_time+timedelta(microseconds=1))
    c = replace(c, collection_digest=_digest(c.material()))
    with pytest.raises((A1SourceError, ValueError, TypeError, KeyError)):
        resign(replace(packet, a1=replace(packet.a1, context=c))).validate()


def test_more_than_five_possible_independent_targets_STOP_with_unchanged_default_cap():
    provider = ManyDiagnostics()
    # Six event-scoped pools share two raw mints; neither selection nor ranking
    # can omit their twelve incidences before T. Six reversed requests exceed 5.
    provider.pairs = {f.key(30+i): (f.M0, f.M1, f.key(100+2*i), f.key(101+2*i)) for i in range(6)}
    owner, _, _ = collect(provider)
    with (patch.object(BoundedPoolCandidateOwner, "select", side_effect=AssertionError("pre-T ranking")),
          pytest.raises(A1SourceError, match="RTI11_DIAGNOSTIC_PLAN_BUDGET")):
        owner.collect_once()
    assert not any(p.scope == "diagnostic" for p in provider.calls)
    assert len(owner._manifest) == 2 and owner.packet is None and owner.status == "STOPPED"
    assert owner.budget.max_diagnostics == 5


def test_diagnostic_configuration_mutation_STOPS_before_first_diagnostic_attempt():
    provider = DiagnosticProvider(); owner, _, _ = collect(provider)
    def opener(request, **kw):
        response = provider(request, **kw)
        if request.scope == "safety": owner.diagnostic_max_bytes = 16384
        return response
    owner.opener = opener
    with pytest.raises(A1SourceError, match="P03_CONFIGURATION_MUTATION"): owner.collect_once()
    assert not any(p.scope == "diagnostic" for p in provider.calls) and owner.packet is None


def test_final_T_revalidates_oldest_source_age_after_every_receipt():
    owner, clock, provider = collect(freshness_policy=FreshnessPolicy(timedelta(seconds=190.5)))
    closed = owner._closed
    def later():
        closed()
        clock.value += timedelta(seconds=1)
    owner._closed = later
    with pytest.raises(A1SourceError, match="RTI11_SOURCE_WINDOW"): owner.collect_once()
    assert len(provider.calls) == 21 and owner.status == "STOPPED" and owner.packet is None
    assert owner.ledger.snapshot().completed_at is not None  # failed publication never reopens sealed ledger
    with pytest.raises(A1SourceError): owner.ledger.reserve_attempt(kind="diagnostic", host="api.coingecko.com",
        response_cap=CAP, timeout=TIMEOUT, now=clock.value)
    assert len(provider.calls) == 21


def test_independent_diagnostic_timeout_is_charged_and_terminal():
    provider, clock = DiagnosticProvider(), FakeClock()
    def opener(request, **kwargs):
        response = provider(request, **kwargs)
        if request.scope == "diagnostic": clock.value += TIMEOUT + timedelta(microseconds=1)
        return response
    owner, _, _ = collect(provider, clock, opener=opener)
    with pytest.raises(A1SourceError): owner.collect_once()
    assert len(provider.calls) == len(owner.ledger.snapshot().attempts) == 21
    assert owner.packet is None and owner.status == "STOPPED"
