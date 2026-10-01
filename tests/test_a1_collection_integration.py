"""Fake wire collection replay through real paper owners and durable SQLite.

P03 evidence remains a synthetic replay fixture. Diagnostic mapping reuses the
collected raw candle body and source clocks, with exact same wire parameters.
This proves offline composition, never provider-backed safety readiness.
"""
from dataclasses import replace
from datetime import timedelta
import socket

import pytest

from backend.application.autonomous_paper_one_cycle import (
    AutonomousPaperOneCycleService, AutonomousPaperCycleRequest, CycleOutcome,
)
from backend.application.market_to_opportunity_composition import MarketToOpportunityCompositionService
from backend.application.paper_lifecycle_persistence import ControlledPaperPersistenceService
from core.data.bounded_cycle_sources import BoundedDiscoveryOwner, BoundedPoolCandidateOwner
from core.data.contracts import DataQuality
from core.risk.safety_evidence import (
    SafetyEvidenceCollection, TokenSafetyEvidence, SafetyDomain, SafetyStatus,
    SafetyProvenance, P02StateReference,
)
from core.signals.price_direction_policy import derive_price_direction
from tests.test_a1_cpmm_sources import M0, M1
from tests.test_a1_operational_collection import collector, FakeClock, FakeProvider
from tests.test_autonomous_paper_one_cycle import factory
from tests.test_coingecko_onchain_ohlcv import REFERENCE, FRESHNESS
from tests.test_controlled_paper_persistence import sqlite_runtime  # noqa: F401


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("operational network forbidden")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


class ReplayOwners:
    def __init__(self, packet):
        self.packet, self.calls = packet, []

    def evidence_once(self, candidate, snapshot, *, reference_time):
        self.calls.append(("safety", candidate.token_mint))
        assert reference_time == self.packet.context.reference_time
        observed = reference_time-timedelta(seconds=5)
        predecessor = snapshot.predecessor
        rejected = candidate.token_mint == M1
        return SafetyEvidenceCollection.from_evidence((TokenSafetyEvidence(
            chain_id=candidate.chain_id, token_identity=candidate.token_mint,
            domain=SafetyDomain.LIQUIDITY_QUALITY,
            status=SafetyStatus.FAIL if rejected else SafetyStatus.PASS,
            source_id="synthetic-p03-replay", observed_at=observed, quality=DataQuality.VALID,
            freshness_status=DataQuality.VALID, data_age=reference_time-observed,
            provenance=SafetyProvenance("synthetic-p03-replay", "synthetic-evidence-v1", observed),
            evidence_reference="safety:"+candidate.token_mint,
            evidence_context={"scope":"offline-synthetic-evidence"},
            reason_codes=("SYNTHETIC_SAFETY_VETO",) if rejected else (),
            p02_reference=P02StateReference(predecessor.state_version, predecessor.state_digest,
                                             predecessor.materializer_contract_version),
        ),))

    def diagnostic(self, **kwargs):
        request = kwargs["request"]
        self.calls.append(("diagnostic", request.token_mint))
        original = next(v.response for v in self.packet.valuations
                        if (v.response.request.pool_address,v.response.request.token_mint)
                        == (request.pool_address,request.token_mint))
        assert request.reference_time == self.packet.context.reference_time
        assert request.url == original.request.url and request.parameters == original.request.parameters
        assert (request.base_mint,request.quote_mint) == (original.request.base_mint,original.request.quote_mint)
        replay = replace(original, request=request)
        assert replay.body is original.body
        assert (replay.started_at,replay.received_at) == (original.started_at,original.received_at)
        return derive_price_direction(request=request,response=replay,
            predecessor=kwargs["predecessor"],freshness_policy=kwargs["freshness_policy"],
            evaluation_time=request.reference_time)


def prepared(sqlite_runtime, *, blocked=False):
    owner,clock,provider=collector(clock=FakeClock(REFERENCE),provider=FakeProvider(REFERENCE))
    packet=owner.collect_once()
    reference=packet.context.reference_time
    before=len(provider.calls)
    clock.closed=provider.closed=True
    discovery,pools=packet.replay_sources()
    replay=ReplayOwners(packet)
    persistence_owner=ControlledPaperPersistenceService(sqlite_runtime)
    mutations=[]
    class Persistence:
        async def persist(self,result):
            mutations.append(("persist",result.digest))
            stored = await persistence_owner.persist(result)
            assert stored.lifecycle_result_digest == result.digest
            self.stored = stored
            return stored
        async def read(self,digest):
            mutations.append(("read",digest))
            readback = await persistence_owner.read(digest)
            assert readback.lifecycle_result_digest == digest
            assert readback.run.lifecycle_result_digest == digest
            assert readback.run.artifact_count == self.stored.artifact_count
            return readback
    service=AutonomousPaperOneCycleService(discovery=BoundedDiscoveryOwner(discovery),
        pools=BoundedPoolCandidateOwner(pools),safety=replay,
        market=MarketToOpportunityCompositionService(diagnostic=replay.diagnostic),
        paper_request_factory=lambda r,c:factory(r,c,blocked=blocked),persistence=Persistence())
    command=AutonomousPaperCycleRequest("collected:paper",reference,reference,reference,
                                        FRESHNESS,timedelta(seconds=10),16384)
    return service,command,replay,packet,provider,before,mutations


@pytest.mark.asyncio
async def test_fake_collection_complete_real_paper_chain_and_durable_readback(sqlite_runtime):
    service,command,replay,packet,provider,before,mutations=prepared(sqlite_runtime)
    result=await service.run(command)
    assert result.outcome is CycleOutcome.CYCLE_COMPLETED,result
    assert result.simulation_only is True
    assert result.selected_token_mint == M0
    assert result.candidates_considered == 2 and result.diagnostic_invocations == 1
    assert all((result.lifecycle_digest,result.persistence_digest,result.readback_digest))
    assert mutations == [("persist",result.lifecycle_digest),("read",result.lifecycle_digest)]
    assert replay.calls.count(("diagnostic",M0)) == 1
    assert ("diagnostic",M1) not in replay.calls
    assert len(provider.calls) == before == len(packet.context.budget.attempts)
    assert before == 12
    assert packet.context.program.source_equivalence == "NOT_VERIFIED"


@pytest.mark.asyncio
async def test_collected_facts_still_obey_real_risk_governor_veto(sqlite_runtime):
    service,command,replay,packet,provider,before,mutations=prepared(sqlite_runtime,blocked=True)
    class Forbidden:
        def source(self,request):
            raise AssertionError("PFS must not follow risk veto")
    service.pfs=Forbidden()
    result=await service.run(command)
    assert result.outcome is CycleOutcome.RISK_OR_CAPITAL_REJECTED,result
    assert result.simulation_only is True and result.lifecycle_digest is None
    assert mutations == []
    assert len(provider.calls) == before
    assert ("diagnostic",M0) in replay.calls
