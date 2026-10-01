"""Offline full canonical owner chain with bounded injected facts and SQLite."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import json
import socket
from types import SimpleNamespace

import pytest

from core.data.bounded_cycle_sources import (
    BoundedDiscoveryOwner, BoundedPoolCandidateOwner, DiscoveryBatch,
    CanonicalPoolObservation, CycleSourceError, MAX_DISCOVERY_OBSERVATIONS,
)
from core.data.contracts import RawEvent, DataQuality
from core.data.orchestration import AdapterObservation, ObservationKind
from core.risk.safety_evidence import (
    SafetyEvidenceCollection, TokenSafetyEvidence, SafetyDomain, SafetyStatus,
    SafetyProvenance, P02StateReference,
)
from core.signals.price_direction_policy import derive_price_direction
from core.data.coingecko_onchain_orchestration import ControlledDiagnosticResult, ControlledDiagnosticOutcome
from backend.application.market_to_opportunity_composition import MarketToOpportunityCompositionService
from backend.application.autonomous_paper_one_cycle import (
    AutonomousPaperOneCycleService, AutonomousPaperCycleRequest, CycleOutcome,
)
from backend.application.oaf_paper_request_factory import OafPaperRequestFactory
from backend.application.paper_lifecycle_persistence import ControlledPaperPersistenceService
from tests.test_coingecko_onchain_ohlcv import TOKEN, POOL, QUOTE, REFERENCE, FRESHNESS, response, payload, encode
from tests.test_oaf_paper_request_factory import _inputs
from tests.test_controlled_paper_persistence import sqlite_runtime  # noqa: F401


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("operational network forbidden")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def command():
    return AutonomousPaperCycleRequest("cycle:one", REFERENCE, REFERENCE, REFERENCE,
                                       FRESHNESS, timedelta(seconds=10), 16384)


def observation(token=TOKEN):
    received = REFERENCE - timedelta(seconds=1)
    return AdapterObservation(
        source_id="offline-discovery", kind=ObservationKind.EVENT, observed_time=received,
        raw_event=RawEvent("offline-discovery", {
            "discovery_kind": "DISCOVERED", "token_identity": token, "chain_id": "solana",
            "discovery_reason": "EXPLICIT_BOUNDED_SOURCE", "metadata": {},
        }, received, REFERENCE - timedelta(seconds=5), "event:" + token),
    )


class Sources:
    def __init__(self, tokens=(TOKEN,)):
        self.tokens = tokens
        self.calls = []
        self.blocked = set()
        self.pool_values = {}
        self.prices = {}

    def discover_once(self, **kwargs):
        self.calls.append(("discovery", None))
        return DiscoveryBatch("offline-discovery", "receipt:one", REFERENCE - timedelta(seconds=1),
                              tuple(observation(token) for token in self.tokens))

    def evidence_once(self, candidate, snapshot, **kwargs):
        self.calls.append(("safety", candidate.token_mint))
        observed = REFERENCE - timedelta(seconds=5)
        predecessor = snapshot.predecessor
        return SafetyEvidenceCollection.from_evidence((TokenSafetyEvidence(
            chain_id=candidate.chain_id, token_identity=candidate.token_mint,
            domain=SafetyDomain.LIQUIDITY_QUALITY,
            status=SafetyStatus.FAIL if candidate.token_mint in self.blocked else SafetyStatus.PASS,
            source_id="offline-safety", observed_at=observed, quality=DataQuality.VALID,
            freshness_status=DataQuality.VALID, data_age=REFERENCE - observed,
            provenance=SafetyProvenance("offline-safety", "offline-evidence-v1", observed),
            evidence_reference="safety:" + candidate.token_mint,
            evidence_context={"scope": "offline-qualifying-evidence"},
            reason_codes=("OFFLINE_SAFETY_VETO",) if candidate.token_mint in self.blocked else (),
            p02_reference=P02StateReference(predecessor.state_version, predecessor.state_digest, "p02-t06-v1"),
        ),))

    def pools_once(self, candidate, **kwargs):
        self.calls.append(("pools", candidate.token_mint))
        return self.pool_values.get(candidate.token_mint, (pool(candidate.token_mint),))

    def diagnostic(self, **kwargs):
        req = kwargs["request"]
        self.calls.append(("diagnostic", req.token_mint))
        body = payload()
        body["meta"]["base"]["address"] = req.base_mint
        body["meta"]["quote"]["address"] = req.quote_mint
        if req.token_mint in self.prices:
            for row, price in zip(body["data"]["attributes"]["ohlcv_list"], self.prices[req.token_mint]):
                row[1:5] = [price] * 4
        return derive_price_direction(request=req, response=response(req, encode(body)),
            predecessor=kwargs["predecessor"], freshness_policy=kwargs["freshness_policy"],
            evaluation_time=req.reference_time)


def pool(token=TOKEN, address=POOL, liquidity=Decimal("100")):
    return CanonicalPoolObservation("solana", token, address, token, QUOTE, liquidity,
                                    "offline-pool", "pool:reference", REFERENCE - timedelta(seconds=5),
                                    REFERENCE - timedelta(seconds=1))


def factory(rti11, request, *, blocked=False, reject=False):
    inputs = _inputs(rti11)
    policy = replace(inputs.simulation_policy, ledger_stream_identity={
        **inputs.simulation_policy.ledger_stream_identity,
        "candidate_id": rti11.request.candidate_id, "token_identity": rti11.request.target.token_mint,
        "pool_address": rti11.request.target.pool_address,
    })
    if blocked:
        from core.risk.paper_risk_capital_authorization import RiskStateStatus
        risk = replace(inputs.policy_seed.risk_state, status=RiskStateStatus.BLOCK,
                       risk_flags=("controller-stop",), state_digest=None)
        inputs = replace(inputs, policy_seed=replace(inputs.policy_seed, risk_state=risk, seed_digest=None))
    if reject:
        inputs = replace(inputs, decision_ruleset=replace(inputs.decision_ruleset,
                         buy_score_threshold=Decimal("100"), watch_score_threshold=Decimal("99")))
    return OafPaperRequestFactory().build(rti11, replace(inputs, simulation_policy=policy))


def service(sources, persistence=None, **kwargs):
    market = MarketToOpportunityCompositionService(diagnostic=sources.diagnostic)
    return AutonomousPaperOneCycleService(discovery=BoundedDiscoveryOwner(sources),
        pools=BoundedPoolCandidateOwner(sources), safety=sources, market=market,
        paper_request_factory=factory, persistence=persistence, **kwargs)


@pytest.mark.asyncio
async def test_complete_cycle_real_owners_exact_durable_readback(sqlite_runtime):
    sources = Sources()
    owner = ControlledPaperPersistenceService(sqlite_runtime)
    calls = []
    class Persistence:
        async def persist(self, value):
            calls.append(("persist", value.digest))
            return await owner.persist(value)
        async def read(self, digest):
            calls.append(("read", digest))
            return await owner.read(digest)
    result = await service(sources, Persistence()).run(command())
    assert result.outcome is CycleOutcome.CYCLE_COMPLETED, result
    assert sources.calls == [("discovery", None), ("safety", TOKEN), ("pools", TOKEN), ("diagnostic", TOKEN)]
    assert calls == [("persist", result.lifecycle_digest), ("read", result.lifecycle_digest)]
    assert result.selected_token_mint == TOKEN and result.selected_pool_address == POOL
    assert result.simulation_only and result.readback_digest


def test_discovery_order_duplicates_truncation_and_canonical_membership():
    tokens = tuple(str(i) * 32 for i in range(1, 8))
    sources = Sources(tuple(reversed(tokens)) + (tokens[0],))
    snapshot = BoundedDiscoveryOwner(sources).discover(reference_time=REFERENCE,
        processing_time=REFERENCE, freshness_policy=FRESHNESS, evaluation_id="cycle")
    assert tuple(c.token_mint for c in snapshot.candidates) == tokens[:5]
    assert sources.calls == [("discovery", None)]
    assert all(snapshot.predecessor.contains("solana", token) for token in tokens[:5])
    assert not snapshot.predecessor.contains("solana", tokens[5])


@pytest.mark.parametrize("bad", [None, "100", Decimal("NaN"), Decimal("-1")])
def test_missing_invalid_liquidity_fails_closed(bad):
    sources = Sources()
    sources.pool_values[TOKEN] = (pool(liquidity=bad),)
    from core.data.bounded_cycle_sources import DiscoveredCandidate
    with pytest.raises(CycleSourceError):
        BoundedPoolCandidateOwner(sources).select(DiscoveredCandidate("c", "solana", TOKEN, "e"),
                                                  reference_time=REFERENCE, freshness_policy=FRESHNESS)


def test_pool_liquidity_and_lexical_address_tie_break():
    sources = Sources()
    from core.data.bounded_cycle_sources import DiscoveredCandidate
    candidate = DiscoveredCandidate("c", "solana", TOKEN, "e")
    sources.pool_values[TOKEN] = (pool(address="z", liquidity=Decimal("200")),
                                 pool(address="a", liquidity=Decimal("200")), pool(address="b"))
    selected = BoundedPoolCandidateOwner(sources).select(candidate, reference_time=REFERENCE, freshness_policy=FRESHNESS)
    assert selected.pool_address == "a"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode, expected", [("empty", CycleOutcome.NO_DISCOVERY_CANDIDATES),
    ("safety", CycleOutcome.NO_ELIGIBLE_CANDIDATE), ("pool", CycleOutcome.NO_VALID_POOL)])
async def test_upstream_stop_has_no_diagnostic_or_mutation(mode, expected):
    sources = Sources(() if mode == "empty" else (TOKEN,))
    if mode == "safety": sources.blocked.add(TOKEN)
    if mode == "pool": sources.pool_values[TOKEN] = ()
    result = await service(sources).run(command())
    assert result.outcome is expected, result
    assert result.diagnostic_invocations == 0
    assert result.lifecycle_digest is None


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked, reject, expected", [(True, False, CycleOutcome.RISK_OR_CAPITAL_REJECTED),
                                                     (False, True, CycleOutcome.DECISION_REJECTED)])
async def test_decision_and_risk_veto_stop_before_pfs(blocked, reject, expected):
    sources = Sources()
    runner = service(sources)
    runner.factory = lambda r, c: factory(r, c, blocked=blocked, reject=reject)
    class Forbidden:
        def source(self, request): raise AssertionError("PFS after veto")
    runner.pfs = Forbidden()
    result = await runner.run(command())
    assert result.outcome is expected, result
    assert result.lifecycle_digest is None


@pytest.mark.asyncio
async def test_source_exception_no_retry():
    sources = Sources()
    def unavailable(**kwargs):
        sources.calls.append(("discovery", None))
        raise RuntimeError("source failed")
    sources.discover_once = unavailable
    result = await service(sources).run(command())
    assert result.outcome is CycleOutcome.OWNER_UNAVAILABLE
    assert sources.calls == [("discovery", None)]


@pytest.mark.asyncio
async def test_highest_score_only_one_candidate_reaches_paper(sqlite_runtime):
    other = TOKEN[:-1] + "3"
    sources = Sources((TOKEN, other))
    sources.prices[other] = (30, 15, 10)
    selected = []
    runner = service(sources, ControlledPaperPersistenceService(sqlite_runtime))
    runner.factory = lambda r, c: (selected.append(r.request.target.token_mint) or factory(r, c))
    result = await runner.run(command())
    assert result.outcome is CycleOutcome.CYCLE_COMPLETED, result
    assert selected == [other]
    assert result.diagnostic_invocations == 2


@pytest.mark.asyncio
async def test_score_tie_lexical_candidate_identity(sqlite_runtime):
    other = TOKEN[:-1] + "3"
    sources = Sources((TOKEN, other))
    snapshot = BoundedDiscoveryOwner(Sources((TOKEN, other))).discover(reference_time=REFERENCE,
        processing_time=REFERENCE, freshness_policy=FRESHNESS, evaluation_id="cycle")
    expected = min(snapshot.candidates, key=lambda c: (c.candidate_id, c.chain_id, c.token_mint))
    result = await service(sources, ControlledPaperPersistenceService(sqlite_runtime)).run(command())
    assert result.outcome is CycleOutcome.CYCLE_COMPLETED, result
    assert result.selected_candidate_id == expected.candidate_id


@pytest.mark.asyncio
async def test_max_five_candidates_and_p03_removes_one_before_pool():
    tokens = tuple(TOKEN[:-1] + str(i) for i in range(2, 8))
    sources = Sources(tuple(reversed(tokens)))
    sources.blocked.add(tokens[0])
    sources.pool_values = {t: () for t in tokens}
    result = await service(sources).run(command())
    assert result.outcome is CycleOutcome.NO_VALID_POOL, result
    assert result.candidates_considered == 5
    assert [t for stage, t in sources.calls if stage == "safety"] == list(tokens[:5])
    assert [t for stage, t in sources.calls if stage == "pools"] == list(tokens[1:5])
    assert sum(stage == "discovery" for stage, _ in sources.calls) == 1


@pytest.mark.parametrize("mode", ["conflict", "stale", "oversize", "not-admitted"])
def test_discovery_invalid_facts_fail_closed(mode):
    sources = Sources()
    original = observation()
    if mode == "conflict":
        entries = (original, replace(original, raw_event=replace(original.raw_event,
                    payload={**original.raw_event.payload, "metadata": {"conflict": True}})))
    elif mode == "stale":
        entries = (replace(original, raw_event=replace(original.raw_event, event_time=REFERENCE - timedelta(days=1))),)
    elif mode == "oversize":
        entries = (original,) * (MAX_DISCOVERY_OBSERVATIONS + 1)
    else:
        entries = (SimpleNamespace(status="NOT_ADMITTED"),)
    sources.discover_once = lambda **kwargs: DiscoveryBatch("offline-discovery", "receipt:one", original.observed_time, entries)
    with pytest.raises(CycleSourceError):
        BoundedDiscoveryOwner(sources).discover(reference_time=REFERENCE, processing_time=REFERENCE,
                                               freshness_policy=FRESHNESS, evaluation_id="cycle")


@pytest.mark.parametrize("mode", ["stale", "identity", "receipt", "oversize", "duplicate"])
def test_pool_invalid_identity_time_and_bounds(mode):
    sources = Sources()
    item = pool()
    if mode == "stale": item = replace(item, observed_at=REFERENCE - timedelta(days=1))
    if mode == "identity": item = replace(item, base_mint=QUOTE)
    if mode == "receipt": item = replace(item, received_at=REFERENCE + timedelta(seconds=1))
    sources.pool_values[TOKEN] = ((item,) * 21 if mode == "oversize" else
                                 (item, replace(item, liquidity_usd=Decimal("200"))) if mode == "duplicate" else (item,))
    from core.data.bounded_cycle_sources import DiscoveredCandidate
    with pytest.raises(CycleSourceError):
        BoundedPoolCandidateOwner(sources).select(DiscoveredCandidate("c", "solana", TOKEN, "e"),
                                                  reference_time=REFERENCE, freshness_policy=FRESHNESS)


@pytest.mark.asyncio
async def test_incomparable_score_rules_stop_before_selection():
    from core.opportunity.canonical_evidence_producer import produce_canonical_p04_to_p05
    from core.opportunity.opportunity_score import evaluate_opportunity_score, OpportunityScoringRuleset
    sources = Sources((TOKEN, TOKEN[:-1] + "3"))
    runner = service(sources)
    def producer(**kwargs):
        result = produce_canonical_p04_to_p05(**kwargs)
        if kwargs["token_identity"] != TOKEN:
            score = evaluate_opportunity_score(result.feature_evaluation,
                ruleset=OpportunityScoringRuleset(velocity_scale=Decimal("2")), evaluated_at=REFERENCE)
            result = replace(result, score=score)
        return result
    runner.market._canonical_producer = producer
    runner.factory = lambda *args: pytest.fail("incomparable score selected")
    result = await runner.run(command())
    assert result.outcome is CycleOutcome.INVALID_INPUT
    assert result.selected_candidate_id is None and result.diagnostic_invocations == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["persist-failed", "read-failed", "wrong-readback"])
async def test_persistence_failure_and_readback_mismatch_no_retry(sqlite_runtime, mode):
    from backend.application.paper_lifecycle_persistence import (
        PaperLifecyclePersistenceResult, PaperLifecyclePersistenceOutcome,
        PaperLifecycleReadResult, PaperLifecycleReadOutcome,
    )
    owner = ControlledPaperPersistenceService(sqlite_runtime)
    calls = []
    class Persistence:
        async def persist(self, value):
            calls.append("persist")
            if mode == "persist-failed":
                return PaperLifecyclePersistenceResult(PaperLifecyclePersistenceOutcome.STORAGE_UNAVAILABLE,
                    ("OFFLINE_STORAGE_FAILURE",), value.digest, 0)
            return await owner.persist(value)
        async def read(self, digest):
            calls.append("read")
            if mode == "read-failed":
                return PaperLifecycleReadResult(PaperLifecycleReadOutcome.STORAGE_UNAVAILABLE,
                                               ("OFFLINE_READ_FAILURE",), digest)
            return PaperLifecycleReadResult(PaperLifecycleReadOutcome.NOT_FOUND, ("MISSING",), "a" * 64)
    result = await service(Sources(), Persistence()).run(command())
    assert result.outcome is (CycleOutcome.PERSISTENCE_FAILED if mode == "persist-failed" else CycleOutcome.READBACK_FAILED), result
    assert calls == (["persist"] if mode == "persist-failed" else ["persist", "read"])


@pytest.mark.asyncio
async def test_noncompleted_lifecycle_is_never_persisted():
    sources = Sources()
    runner = service(sources)
    from backend.application.paper_fact_sourcing import PaperFactSourcingService
    class MismatchedExpectation:
        def source(self, request):
            facts = PaperFactSourcingService().source(request)
            expectation = replace(facts.lifecycle_evidence.reconciliation_expectation,
                expected_fields={"entry_digest": "e" * 64}, expectation_digest=None)
            evidence = replace(facts.lifecycle_evidence, reconciliation_expectation=expectation)
            return replace(facts, lifecycle_evidence=evidence, result_digest=None)
    runner.pfs = MismatchedExpectation()
    result = await runner.run(command())
    assert result.outcome is CycleOutcome.PAPER_TERMINATED_WITHOUT_PERSIST, result


def test_production_modules_have_no_operational_wiring():
    import ast
    from pathlib import Path
    for path in ("core/data/bounded_cycle_sources.py", "backend/application/autonomous_paper_one_cycle.py"):
        tree = ast.parse(Path(path).read_text())
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        assert not names.intersection({"requests", "httpx", "urllib", "threading", "schedule", "sleep", "create_task"})
