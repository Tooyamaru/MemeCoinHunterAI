"""Offline adapter -> common packet -> exact owners -> lifecycle/audit linkage."""
from urllib.parse import urlsplit

import pytest

from backend.application.a1_collection_audit import A1CollectionAuditService, AuditReadOutcome, AuditWriteOutcome
from backend.application.paper_lifecycle_persistence import ControlledPaperPersistenceService
from core.data.a1_http_adapter import A1HttpAdapter
from tests.test_a1_http_adapter import Connection, Tick, ORIGIN, RPC_ROUTE, KEY
from tests.test_a1_collection_audit import CapturedInvocation, counts
from tests.test_a1_rti11_collection import collect, DiagnosticProvider
from tests.test_a1_rti11_collection_integration import service_for
from tests.test_a1_operational_collection import FakeClock
from tests.test_a1_p03_collection import network_guard  # noqa: F401
from tests.test_coingecko_onchain_ohlcv import REFERENCE
from tests.test_controlled_paper_persistence import sqlite_runtime  # noqa: F401


class ProviderFactory:
    def __init__(self, provider):
        self.provider, self.connections = provider, []
        self.current = None
        self.closed = False

    def __call__(self, host, *, timeout):
        assert not self.closed, "post-T connection forbidden"
        wire = self.current
        assert host == urlsplit(wire.endpoint).hostname
        factory = self
        class ProviderConnection(Connection):
            def request(self, method, target, *, body, headers):
                assert not factory.closed, "post-T HTTP forbidden"
                assert method == wire.method
                if method == "POST":
                    assert target == "/private/fake-rpc-route?access=fake-route-value"
                    assert body is wire.body and KEY not in headers.values()
                else:
                    assert ORIGIN not in wire.endpoint
                    assert wire.endpoint == "https://api.coingecko.com" + target
                    assert headers["x-cg-demo-api-key"] == KEY and body is None
                self.calls.append((method, target, body, headers))
                self.response = factory.provider(wire, timeout=wire.timeout.total_seconds())
                self.response.read1 = self.response.read
        connection = ProviderConnection()
        self.connections.append(connection)
        return connection


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked", [False, True])
async def test_adapter_collection_exact_paper_audit_or_independent_Risk_veto(sqlite_runtime, blocked):
    provider, clock = DiagnosticProvider(start=REFERENCE), FakeClock(REFERENCE)
    factory = ProviderFactory(provider)
    value = A1HttpAdapter(ORIGIN, RPC_ROUTE, KEY, factory, Tick())
    def injected(wire, *, timeout):
        factory.current = wire
        return value(wire, timeout=timeout)
    owner, _, _ = collect(provider, clock, opener=injected)
    packet = owner.collect_once()
    assert len(factory.connections) == len(provider.calls) == len(packet.context.budget.attempts) == 21
    assert all(len(c.calls) == 1 and c.closed and c.response.closed for c in factory.connections)
    clock.closed = provider.closed = factory.closed = True
    service, request = service_for(packet, blocked=blocked, persistence=ControlledPaperPersistenceService(sqlite_runtime))
    service.invocation = CapturedInvocation()
    result = await service.run(request)
    if blocked:
        assert result.outcome.value == "RISK_OR_CAPITAL_REJECTED"
        assert await counts(sqlite_runtime) == (0, 0, 0)
    else:
        assert result.outcome.value == "CYCLE_COMPLETED"
        audit = A1CollectionAuditService(sqlite_runtime)
        write = await audit.persist(packet, service.market, service.invocation.result)
        assert write.outcome is AuditWriteOutcome.STORED
        read = await audit.read(result.lifecycle_digest)
        assert read.outcome is AuditReadOutcome.FOUND
        assert KEY not in read.snapshot.canonical_payload
        assert "fake-route-value" not in read.snapshot.canonical_payload
        assert "/private/fake-rpc-route" not in read.snapshot.canonical_payload
        assert await counts(sqlite_runtime) == (1, 13, 1)
    assert len(factory.connections) == 21
