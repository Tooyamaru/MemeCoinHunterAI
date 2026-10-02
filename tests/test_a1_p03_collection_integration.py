"""Raw injected P03 replay through existing cycle/Risk/paper persistence owners.

Diagnostics remain the existing offline A1 candle fixture, not a new collector.
"""
from datetime import timedelta
from unittest.mock import patch

import pytest

from backend.application import autonomous_paper_one_cycle as cycle
from backend.application.market_to_opportunity_composition import MarketToOpportunityCompositionService
from backend.application.paper_lifecycle_persistence import ControlledPaperPersistenceService
from core.data.bounded_cycle_sources import BoundedPoolCandidateOwner
from tests.test_a1_p03_collection import collect, SafetyProvider, network_guard  # noqa: F401
from tests.test_a1_operational_collection import FakeClock
from tests.test_a1_collection_integration import ReplayOwners
from tests.test_autonomous_paper_one_cycle import factory
from tests.test_coingecko_onchain_ohlcv import REFERENCE, FRESHNESS
from tests.test_controlled_paper_persistence import sqlite_runtime  # noqa: F401


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked",[False,True])
async def test_source_backed_p03_preserves_real_risk_and_paper_lifecycle(sqlite_runtime,blocked):
    owner,clock,provider=collect(SafetyProvider(start=REFERENCE),FakeClock(REFERENCE),freshness_policy=FRESHNESS)
    packet=owner.collect_once();clock.closed=provider.closed=True
    discovery,safety,pools=packet.replay_sources()
    diagnostic_fixture=ReplayOwners(packet.a1)
    persistence=ControlledPaperPersistenceService(sqlite_runtime)
    service=cycle.AutonomousPaperOneCycleService(discovery=discovery,pools=BoundedPoolCandidateOwner(pools),
        safety=safety,market=MarketToOpportunityCompositionService(diagnostic=diagnostic_fixture.diagnostic),
        paper_request_factory=lambda r,c:factory(r,c,blocked=blocked),persistence=persistence)
    if blocked:
        class ForbiddenPFS:
            def source(self,request): raise AssertionError("PFS forbidden after Risk veto")
        service.pfs=ForbiddenPFS()
    T=packet.context.reference_time
    request=cycle.AutonomousPaperCycleRequest("raw-p03:paper",T,T,T,FRESHNESS,timedelta(seconds=10),16384)
    with (patch.object(cycle,"evaluate_safety_evidence",wraps=cycle.evaluate_safety_evidence) as evaluation,
          patch.object(cycle,"derive_token_eligibility",wraps=cycle.derive_token_eligibility) as eligibility):
        result=await service.run(request)
    assert evaluation.call_count==eligibility.call_count==2
    assert len(safety.evidence_bindings)==2
    assert result.simulation_only is True
    assert len(provider.calls)==len(packet.context.budget.attempts)==20
    if blocked:
        assert result.outcome is cycle.CycleOutcome.RISK_OR_CAPITAL_REJECTED,result
        assert result.lifecycle_digest is None
    else:
        assert result.outcome is cycle.CycleOutcome.CYCLE_COMPLETED,result
        assert result.lifecycle_digest and result.persistence_digest and result.readback_digest
