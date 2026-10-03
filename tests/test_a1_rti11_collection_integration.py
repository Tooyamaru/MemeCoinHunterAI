"""Actual A1/P03/RTI-11 owners, synthetic pre-T wire facts, real paper owners."""
from dataclasses import replace
from datetime import timedelta
from types import MappingProxyType
from unittest.mock import patch

import pytest

from backend.application import autonomous_paper_one_cycle as cycle
from backend.application.market_to_opportunity_composition import MarketToOpportunityCompositionService
from backend.application.paper_lifecycle_persistence import ControlledPaperPersistenceService
from core.data import a1_rti11_collection as r
from core.data.bounded_cycle_sources import BoundedDiscoveryOwner, BoundedPoolCandidateOwner
from tests.test_a1_rti11_collection import collect, DiagnosticProvider, ManyDiagnostics, handoff, FRESHNESS
from tests.test_a1_p03_collection import network_guard  # noqa: F401
from tests.test_a1_operational_collection import FakeClock
from tests.test_autonomous_paper_one_cycle import factory
from tests.test_coingecko_onchain_ohlcv import REFERENCE
from tests.test_controlled_paper_persistence import sqlite_runtime  # noqa: F401


def service_for(packet, *, blocked=False, persistence=None):
    discovery, safety, pools, market = packet.replay_sources()
    service = cycle.AutonomousPaperOneCycleService(discovery=discovery, safety=safety, pools=pools,
        market=market, paper_request_factory=lambda r, c: factory(r, c, blocked=blocked), persistence=persistence)
    T = packet.context.reference_time
    request = cycle.AutonomousPaperCycleRequest("rti11:paper", T, T, T, packet.context.freshness_policy,
        packet.context.diagnostic_timeout, packet.context.diagnostic_max_bytes)
    return service, request


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked", [False, True])
async def test_autonomous_one_cycle_preserves_owners_persistence_and_independent_Risk(sqlite_runtime, blocked):
    owner, clock, provider = collect(DiagnosticProvider(start=REFERENCE), FakeClock(REFERENCE))
    packet = owner.collect_once(); clock.closed = provider.closed = True
    service, request = service_for(packet, blocked=blocked,
                                   persistence=ControlledPaperPersistenceService(sqlite_runtime))
    if blocked:
        class ForbiddenPFS:
            def source(self, request): raise AssertionError("PFS forbidden after Risk veto")
        service.pfs = ForbiddenPFS()
    def forbidden(*a, **kw): raise AssertionError("post-T provider/clock/environment forbidden")
    class ForbiddenEnvironment(dict):
        def get(self, *a, **kw): forbidden()
        def __getitem__(self, key): forbidden()
    with (patch.object(cycle, "evaluate_safety_evidence", wraps=cycle.evaluate_safety_evidence) as evaluation,
          patch.object(cycle, "derive_token_eligibility", wraps=cycle.derive_token_eligibility) as eligibility,
          patch.object(BoundedDiscoveryOwner, "discover", autospec=True,
                       side_effect=BoundedDiscoveryOwner.discover) as discovery,
          patch.object(BoundedPoolCandidateOwner, "select", autospec=True,
                       side_effect=BoundedPoolCandidateOwner.select) as pools,
          patch.object(r, "derive_price_direction", wraps=r.derive_price_direction) as diagnostic,
          patch("os.environ", ForbiddenEnvironment()), patch("os.getenv", forbidden)):
        result = await service.run(request)
    assert evaluation.call_count == eligibility.call_count == pools.call_count == diagnostic.call_count == 2
    assert discovery.call_count == 1
    assert len(service.market.bindings) == len(service.market.lineage) == 2
    for ev, el, binding in zip(evaluation.call_args_list, eligibility.call_args_list, service.market.bindings):
        assert binding.collection is ev.args[0] and binding.evaluation is el.args[0]
        assert binding.request.target is binding.target
        assert binding.request.predecessor is service.discovery.record.snapshot.predecessor
        assert binding.pool_record.selected is next(p for p in binding.pool_record.observations
                                                    if p.pool_address == binding.request.target.pool_address)
    assert len(provider.calls) == len(packet.context.budget.attempts) == 21
    assert result.simulation_only is True
    if blocked:
        assert result.outcome is cycle.CycleOutcome.RISK_OR_CAPITAL_REJECTED, result
        assert result.lifecycle_digest is result.persistence_digest is result.readback_digest is None
    else:
        assert result.outcome is cycle.CycleOutcome.CYCLE_COMPLETED, result
        assert result.lifecycle_digest and result.persistence_digest and result.readback_digest


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["pool", "handoff", "diagnostic"])
async def test_new_replay_errors_STOP_entire_cycle_without_candidate_fallback(mode):
    owner, clock, provider = collect(); packet = owner.collect_once()
    clock.closed = provider.closed = True
    service, request = service_for(packet)
    if mode == "pool":
        original = BoundedPoolCandidateOwner.select
        def bad(self, *a, **kw):
            pool = original(self, *a, **kw)
            return replace(pool)
        scope = patch.object(BoundedPoolCandidateOwner, "select", bad)
    elif mode == "handoff":
        original = r.RTI11DiagnosticReplay.bind_upstream
        def bad(self, candidate, snapshot, *args): return original(self, candidate, replace(snapshot), *args)
        scope = patch.object(r.RTI11DiagnosticReplay, "bind_upstream", bad)
    else:
        original = r.RTI11DiagnosticReplay._diagnostic
        def bad(self, **kwargs):
            kwargs["predecessor"] = replace(kwargs["predecessor"])
            return original(self, **kwargs)
        scope = patch.object(r.RTI11DiagnosticReplay, "_diagnostic", bad)
    with scope: result = await service.run(request)
    assert result.outcome is cycle.CycleOutcome.INVALID_INPUT, result
    assert service.discovery.stopped and len(service.safety.emissions) == 1
    assert service.market.lineage == () and result.lifecycle_digest is None
    assert len(provider.calls) == 21


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["empty", "ineligible"])
async def test_existing_empty_and_ineligible_outcomes_preserved(mode):
    owner, clock, provider = collect(ManyDiagnostics(empty=True)) if mode == "empty" else collect(max_top_holder_fraction=0.001)
    packet = owner.collect_once(); clock.closed = provider.closed = True
    service, request = service_for(packet)
    result = await service.run(request)
    assert result.outcome is (cycle.CycleOutcome.NO_DISCOVERY_CANDIDATES if mode == "empty"
                             else cycle.CycleOutcome.NO_ELIGIBLE_CANDIDATE)
    assert service.pools.records == service.market.bindings == service.market.lineage == ()


@pytest.mark.parametrize("mode", ["default_market", "foreign_safety", "foreign_pool", "foreign_discovery"])
def test_cycle_rejects_disconnected_or_provider_capable_replay_graph(mode):
    owner, _, _ = collect(); packet = owner.collect_once()
    discovery, safety, pools, market = packet.replay_sources()
    other = packet.replay_sources()
    args = dict(discovery=discovery, safety=safety, pools=pools, market=market,
                paper_request_factory=None, persistence=None)
    if mode == "default_market": args["market"] = MarketToOpportunityCompositionService()
    else: args[mode.removeprefix("foreign_")] = other[{"foreign_discovery": 0, "foreign_safety": 1, "foreign_pool": 2}[mode]]
    # Constructor parameter is plural pools.
    if "pool" in args: args["pools"] = args.pop("pool")
    with pytest.raises(ValueError, match="connected diagnostic replay graph"):
        cycle.AutonomousPaperOneCycleService(**args)


@pytest.mark.parametrize("mode", ["identity", "repeat", "nonproduction"])
def test_callback_request_identity_nonproduction_and_one_call_guard(mode):
    owner, _, _ = collect(); packet = owner.collect_once()
    owners, args = handoff(packet); market = owners[3]; market.bind_upstream(*args)
    kwargs = dict(request=market.bindings[0].fact.response.request, predecessor=args[1].predecessor,
        freshness_policy=FRESHNESS, environment=MappingProxyType({}))
    if mode == "identity": kwargs["request"] = replace(kwargs["request"], timeout=timedelta(seconds=9))
    elif mode == "repeat": market._diagnostic(**kwargs)
    else:
        actual = r.derive_price_direction(**{k:v for k,v in kwargs.items() if k != "environment"},
                                         response=market.bindings[0].fact.response,
                                         evaluation_time=packet.context.reference_time)
        with patch.object(r, "derive_price_direction", return_value=replace(actual, signal_evidence=None)):
            with pytest.raises(ValueError): market._diagnostic(**kwargs)
        assert owners[0].stopped
        return
    with pytest.raises(ValueError): market._diagnostic(**kwargs)
    assert owners[0].stopped
