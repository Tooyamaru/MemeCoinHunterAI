"""Synthetic pre-T collection, canonical paper owners, isolated audit storage."""
import asyncio
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from backend.application.a1_collection_audit import (
    A1CollectionAuditService, AuditReadOutcome, AuditWriteOutcome,
    capture_collection_audit,
)
from backend.application.paper_lifecycle_persistence import (
    ControlledPaperPersistenceService, PaperLifecycleReadOutcome,
)
from backend.application.prepared_paper_case_invocation import PreparedPaperCaseInvocationService
from backend.core.config import Settings
from backend.core.database import DatabaseRuntime
from backend.core.models import A1CollectionAudit, PaperLifecycleArtifact, PaperLifecycleRun
from backend.core.repositories import A1CollectionAuditRepository
from tests.test_a1_rti11_collection import collect, DiagnosticProvider
from tests.test_a1_rti11_collection_integration import service_for
from tests.test_a1_operational_collection import FakeClock
from tests.test_a1_p03_collection import network_guard  # noqa: F401
from tests.test_coingecko_onchain_ohlcv import REFERENCE
from tests.test_controlled_paper_persistence import sqlite_runtime  # noqa: F401


class CapturedInvocation(PreparedPaperCaseInvocationService):
    def run(self, request):
        self.result = super().run(request)
        return self.result


async def complete_case(runtime, *, collection_id="audit:one", blocked=False):
    owner, clock, provider = collect(DiagnosticProvider(start=REFERENCE), FakeClock(REFERENCE),
                                     collection_id=collection_id)
    packet = owner.collect_once()
    clock.closed = provider.closed = True
    service, request = service_for(packet, blocked=blocked,
                                   persistence=ControlledPaperPersistenceService(runtime))
    service.invocation = CapturedInvocation()
    result = await service.run(request)
    return packet, service.market, getattr(service.invocation, "result", None), result, clock, provider


@pytest_asyncio.fixture(scope="module")
async def source_case(tmp_path_factory):
    path = tmp_path_factory.mktemp("a1-source-audit") / "source.db"
    runtime = DatabaseRuntime(Settings(_env_file=None, app_env="test",
                                       database_url=f"sqlite+aiosqlite:///{path}"))
    await runtime.start()
    from backend.core.models import Base
    async with runtime.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        case = await complete_case(runtime)
        assert case[3].outcome.value == "CYCLE_COMPLETED"
        return case
    finally:
        await runtime.dispose()


@pytest_asyncio.fixture
async def completed_case(sqlite_runtime, source_case):
    lifecycle = source_case[2].osc02_result.rti16_result.lifecycle_result
    await ControlledPaperPersistenceService(sqlite_runtime).persist(lifecycle)
    return source_case


@contextmanager
def substituted(owner, name, value):
    original = getattr(owner, name)
    object.__setattr__(owner, name, value)
    try:
        yield
    finally:
        object.__setattr__(owner, name, original)


async def counts(runtime):
    async with runtime.session_scope() as session:
        return tuple([await session.scalar(select(func.count()).select_from(model))
                      for model in (PaperLifecycleRun, PaperLifecycleArtifact, A1CollectionAudit)])


def forbidden(*args, **kwargs):
    raise AssertionError("audit must not rerun owners or access providers/clocks")


@pytest.mark.asyncio
async def test_capture_is_lossless_immutable_and_has_zero_owner_service_or_post_T_IO(completed_case):
    packet, replay, invocation, _, clock, provider = completed_case
    with (patch.object(replay, "compose", forbidden), patch.object(replay.binding, "discover", forbidden),
          patch.object(replay.safety, "evidence_once", forbidden), patch.object(replay.pools, "select", forbidden),
          patch("os.getenv", forbidden)):
        first = capture_collection_audit(packet, replay, invocation)
        second = capture_collection_audit(packet, replay, invocation)
    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.audit_digest = "0" * 64
    bodies = dict(first.raw_bodies)
    assert all(hashlib.sha256(body).hexdigest() == digest for digest, body in bodies.items())
    assert all(e.body == bodies[hashlib.sha256(e.body).hexdigest()] for e in (
        *packet.a1.verification_envelopes, *packet.a1.discovery_envelopes,
        *(e for _, values in packet.a1.reserve_envelopes for e in values),
        *(e for raw in packet.safety for e in raw.physical_envelopes)))
    assert all(d.response.body == bodies[hashlib.sha256(d.response.body).hexdigest()] for d in packet.diagnostics)
    doc = json.loads(first.canonical_payload)
    assert doc["packet"]["a1"]["context"]["reference_time"] == packet.context.reference_time.isoformat()
    assert [r["reused_a1"] for r in doc["replays"]] == [True, False]
    assert len(doc["packet"]["a1"]["context"]["requests"]) == 21
    assert len(provider.calls) == 21 and clock.closed and provider.closed


@pytest.mark.asyncio
async def test_attachment_persist_readback_and_exact_duplicate_preserve_RTI03(sqlite_runtime, completed_case):
    packet, replay, invocation, result, _, provider = completed_case
    service = A1CollectionAuditService(sqlite_runtime)
    snapshot = capture_collection_audit(packet, replay, invocation)
    assert await counts(sqlite_runtime) == (1, 13, 0)
    first = await service.persist(packet, replay, invocation)
    duplicate = await service.persist(packet, replay, invocation)
    read = await service.read(result.lifecycle_digest)
    assert first.outcome is AuditWriteOutcome.STORED and first.audit_digest == snapshot.audit_digest
    assert duplicate.outcome is AuditWriteOutcome.ALREADY_STORED
    assert read.outcome is AuditReadOutcome.FOUND and read.snapshot == snapshot
    assert await counts(sqlite_runtime) == (1, 13, 1)
    legacy = await ControlledPaperPersistenceService(sqlite_runtime).read(result.lifecycle_digest)
    assert legacy.outcome is PaperLifecycleReadOutcome.FOUND and len(legacy.artifacts) == 13
    assert len(provider.calls) == 21


@pytest.mark.asyncio
async def test_audit_is_durable_after_disposal_and_new_runtime(sqlite_runtime, completed_case):
    original = await A1CollectionAuditService(sqlite_runtime).persist(*completed_case[:3])
    url = sqlite_runtime.config.url
    await sqlite_runtime.dispose()
    restarted = DatabaseRuntime(Settings(_env_file=None, app_env="test", database_url=url))
    await restarted.start()
    try:
        read = await A1CollectionAuditService(restarted).read(completed_case[3].lifecycle_digest)
        assert read.outcome is AuditReadOutcome.FOUND
        assert read.snapshot.audit_digest == original.audit_digest
        assert await counts(restarted) == (1, 13, 1)
    finally:
        await restarted.dispose()


@pytest.mark.asyncio
async def test_missing_migration_is_unavailable_without_auto_schema_creation(tmp_path, completed_case):
    runtime = DatabaseRuntime(Settings(_env_file=None, app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'legacy-only.db'}"))
    await runtime.start()
    try:
        async with runtime.engine.begin() as connection:
            await connection.run_sync(PaperLifecycleRun.__table__.create)
            await connection.run_sync(PaperLifecycleArtifact.__table__.create)
        lifecycle = completed_case[2].osc02_result.rti16_result.lifecycle_result
        await ControlledPaperPersistenceService(runtime).persist(lifecycle)
        service = A1CollectionAuditService(runtime)
        assert (await service.persist(*completed_case[:3])).outcome is AuditWriteOutcome.STORAGE_UNAVAILABLE
        assert (await service.read(lifecycle.digest)).outcome is AuditReadOutcome.STORAGE_UNAVAILABLE
        assert (await ControlledPaperPersistenceService(runtime).read(lifecycle.digest)).outcome is PaperLifecycleReadOutcome.FOUND
    finally:
        await runtime.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["foreign_packet", "stopped", "pending", "clock", "body", "pool", "request", "lineage"])
async def test_capture_mismatch_stops_before_any_write(sqlite_runtime, completed_case, mode):
    packet, replay, invocation, _, _, _ = completed_case
    if mode == "foreign_packet":
        packet = replace(packet)
        result = await A1CollectionAuditService(sqlite_runtime).persist(packet, replay, invocation)
    else:
        mutations = {
            "stopped": (replay.binding, "stopped", True),
            "pending": (replay, "_pending", replay.bindings[0]),
            "clock": (packet.context, "planned_cutoff", 0),
            "body": (packet.diagnostics[0].response, "body", b"{}"),
            "pool": (replay.bindings[0].pool_record, "selected", replace(replay.bindings[0].pool_record.selected)),
            "request": (replay.bindings[0], "request", replace(replay.bindings[0].request)),
            "lineage": (replay, "lineage", (replace(replay.lineage[0], request_digest="0" * 64), *replay.lineage[1:])),
        }
        with substituted(*mutations[mode]):
            result = await A1CollectionAuditService(sqlite_runtime).persist(packet, replay, invocation)
    assert result.outcome is AuditWriteOutcome.INVALID_INPUT
    assert await counts(sqlite_runtime) == (1, 13, 0)


@pytest.mark.asyncio
async def test_foreign_equal_owner_graph_cannot_link_same_lifecycle(sqlite_runtime, completed_case):
    other = await complete_case(sqlite_runtime)
    assert other[3].lifecycle_digest == completed_case[3].lifecycle_digest
    result = await A1CollectionAuditService(sqlite_runtime).persist(
        completed_case[0], completed_case[1], other[2])
    assert result.outcome is AuditWriteOutcome.INVALID_INPUT
    assert await counts(sqlite_runtime) == (1, 13, 0)


@pytest.mark.asyncio
async def test_requires_existing_lifecycle_and_restricts_foreign_key(tmp_path, completed_case):
    # Fresh isolated runtime, so the exact canonical lifecycle is not there.
    runtime = DatabaseRuntime(Settings(_env_file=None, app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'empty.db'}"))
    await runtime.start()
    from backend.core.models import Base
    async with runtime.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        result = await A1CollectionAuditService(runtime).persist(*completed_case[:3])
        assert result.outcome is AuditWriteOutcome.LIFECYCLE_NOT_FOUND
        assert await counts(runtime) == (0, 0, 0)
    finally:
        await runtime.dispose()


@pytest.mark.asyncio
async def test_different_valid_collection_for_same_lifecycle_conflicts_without_overwrite(sqlite_runtime, completed_case):
    other = await complete_case(sqlite_runtime, collection_id="audit:other")
    assert other[3].lifecycle_digest == completed_case[3].lifecycle_digest
    service = A1CollectionAuditService(sqlite_runtime)
    original = await service.persist(*completed_case[:3])
    conflict = await service.persist(*other[:3])
    assert original.outcome is AuditWriteOutcome.STORED
    assert conflict.outcome is AuditWriteOutcome.CONFLICT
    read = await service.read(completed_case[3].lifecycle_digest)
    assert read.snapshot.audit_digest == original.audit_digest
    assert await counts(sqlite_runtime) == (1, 13, 1)


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("canonical_payload", "{}"), ("packet_digest", "0" * 64),
    ("collection_digest", "0" * 64), ("selected_rti11_digest", "0" * 64),
    ("payload_digest", "0" * 64), ("audit_digest", "0" * 64),
    ("contract_version", "unsupported"), ("run_id", 999),
])
async def test_corrupt_readback_and_duplicate_fail_closed(sqlite_runtime, completed_case, field, value):
    service = A1CollectionAuditService(sqlite_runtime)
    await service.persist(*completed_case[:3])
    async with sqlite_runtime.session_scope() as session:
        record = await session.scalar(select(A1CollectionAudit))
        setattr(record, field, value)
    read = await service.read(completed_case[3].lifecycle_digest)
    duplicate = await service.persist(*completed_case[:3])
    assert read.outcome is AuditReadOutcome.CORRUPT and read.snapshot is None
    assert duplicate.outcome is AuditWriteOutcome.CONFLICT
    assert await counts(sqlite_runtime) == (1, 13, 1)


@pytest.mark.asyncio
async def test_parent_corruption_rejects_attachment_and_read(sqlite_runtime, completed_case):
    service = A1CollectionAuditService(sqlite_runtime)
    await service.persist(*completed_case[:3])
    async with sqlite_runtime.session_scope() as session:
        artifact = await session.scalar(select(PaperLifecycleArtifact))
        artifact.canonical_payload = "{}"
    assert (await service.read(completed_case[3].lifecycle_digest)).outcome is AuditReadOutcome.CORRUPT
    assert (await service.persist(*completed_case[:3])).outcome is AuditWriteOutcome.CONFLICT


class FailedInsert(A1CollectionAuditRepository):
    async def insert(self, session, **kwargs):
        await super().insert(session, **kwargs)
        raise SQLAlchemyError("synthetic storage failure")


@pytest.mark.asyncio
async def test_failed_insert_rolls_back_only_audit_and_preserves_lifecycle(sqlite_runtime, completed_case):
    result = await A1CollectionAuditService(sqlite_runtime, FailedInsert()).persist(*completed_case[:3])
    assert result.outcome is AuditWriteOutcome.STORAGE_UNAVAILABLE
    assert await counts(sqlite_runtime) == (1, 13, 0)
    assert (await ControlledPaperPersistenceService(sqlite_runtime).read(
        completed_case[3].lifecycle_digest)).outcome is PaperLifecycleReadOutcome.FOUND


@pytest.mark.asyncio
async def test_concurrent_equal_writes_resolve_to_one_attachment(sqlite_runtime, completed_case):
    first, second = await asyncio.gather(*[
        A1CollectionAuditService(sqlite_runtime).persist(*completed_case[:3]) for _ in range(2)])
    assert {first.outcome, second.outcome} == {AuditWriteOutcome.STORED, AuditWriteOutcome.ALREADY_STORED}
    assert first.audit_digest == second.audit_digest
    assert await counts(sqlite_runtime) == (1, 13, 1)


@pytest.mark.asyncio
async def test_unavailable_storage_and_missing_audit_are_truthful(sqlite_runtime, completed_case):
    runtime = DatabaseRuntime(Settings(_env_file=None, database_url=None))
    unavailable = A1CollectionAuditService(runtime)
    assert (await unavailable.persist(*completed_case[:3])).outcome is AuditWriteOutcome.STORAGE_UNAVAILABLE
    assert (await unavailable.read(completed_case[3].lifecycle_digest)).outcome is AuditReadOutcome.STORAGE_UNAVAILABLE
    assert (await A1CollectionAuditService(sqlite_runtime).read(
        completed_case[3].lifecycle_digest)).outcome is AuditReadOutcome.NOT_FOUND
    with pytest.raises(ValueError):
        await unavailable.read("invalid")


@pytest.mark.asyncio
async def test_Risk_veto_produces_no_lifecycle_or_audit(sqlite_runtime):
    case = await complete_case(sqlite_runtime, blocked=True)
    assert case[3].outcome.value == "RISK_OR_CAPITAL_REJECTED" and case[2] is None
    assert (await A1CollectionAuditService(sqlite_runtime).persist(*case[:3])).outcome is AuditWriteOutcome.INVALID_INPUT
    assert await counts(sqlite_runtime) == (0, 0, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["body", "extra_body", "discovery", "pool", "request", "replay", "winner", "bridge", "parent_source_link", "market_body_link"])
async def test_mutated_document_rejected_even_after_recomputed_payload_and_audit_hash(completed_case, mode):
    from backend.application.a1_collection_audit import _hash, _json
    snapshot = capture_collection_audit(*completed_case[:3])
    doc = json.loads(snapshot.canonical_payload)
    if mode == "body":
        blob = next(b for b in doc["blobs"].values() if b["length"])
        blob["base64"] = "e30="
    elif mode == "extra_body":
        doc["blobs"][hashlib.sha256(b"unused").hexdigest()] = {"length": 6, "base64": "dW51c2Vk"}
    elif mode == "discovery":
        doc["discovery"]["material"]["evaluation_id"] = "foreign"
    elif mode == "pool":
        doc["pools"][0]["material"]["selection_policy"] = "foreign"
    elif mode == "request":
        doc["bindings"][0]["request"]["candidate_id"] = "foreign"
    elif mode == "replay":
        doc["replays"][0]["attempt_identity"] = 999
    elif mode == "winner":
        doc["winner"]["rti11_result"]["result_digest"] = "0" * 64
    elif mode == "bridge":
        doc["bridge"]["authorization_digest"] = "0" * 64
    elif mode == "parent_source_link":
        doc["lifecycle"]["source_rti11_digest"] = "0" * 64
    else:
        winner = doc["winner"]["rti11_result"]
        winner["diagnostic"]["diagnostic"]["market"]["observations"][0]["provenance"]["source_metadata"]["response_digest"] = "0" * 64
        winner["result_digest"] = _hash({k: v for k, v in winner.items() if k != "result_digest"})
        doc["identity"]["selected_rti11_digest"] = winner["result_digest"]
        doc["bridge"]["rti11_digest"] = winner["result_digest"]
        doc["lifecycle"]["source_rti11_digest"] = winner["result_digest"]
        for replay in doc["replays"]:
            if replay["binding_digest"] == doc["winner"]["binding_digest"]:
                replay["result_digest"] = winner["result_digest"]
    payload = _json(doc)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    with pytest.raises(ValueError):
        replace(snapshot, canonical_payload=payload, payload_digest=digest,
                audit_digest=_hash({"contract_version": snapshot.contract_version,
                                   **doc["identity"], "payload_digest": digest}))
