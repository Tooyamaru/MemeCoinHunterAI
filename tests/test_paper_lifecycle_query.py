import ast
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import event, func, select
from sqlalchemy.exc import SQLAlchemyError

from backend.application import (
    ControlledPaperPersistenceService,
    PaperLifecycleQueryService,
    PaperLifecycleReadOutcome,
    PaperLifecycleReadResult,
)
from backend.core.config import Settings
from backend.core.database import DatabaseRuntime, DatabaseState
from backend.core.models import Base, PaperLifecycleArtifact, PaperLifecycleRun
from backend.core.repositories import PaperLifecycleRepository
from tests.test_controlled_paper_persistence import _complete_lifecycle


@pytest_asyncio.fixture
async def sqlite_runtime(tmp_path):
    runtime = DatabaseRuntime(
        Settings(
            _env_file=None,
            app_env="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'query.db'}",
        )
    )
    await runtime.start()
    assert runtime.state is DatabaseState.CONNECTED
    assert runtime.engine is not None
    async with runtime.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield runtime
    finally:
        await runtime.dispose()


async def _counts(runtime):
    async with runtime.session_scope() as session:
        return (
            await session.scalar(select(func.count()).select_from(PaperLifecycleRun)),
            await session.scalar(
                select(func.count()).select_from(PaperLifecycleArtifact)
            ),
        )


@pytest.mark.asyncio
async def test_query_delegates_exact_identity_and_returns_same_result_object():
    digest = "a" * 64
    expected = PaperLifecycleReadResult(
        outcome=PaperLifecycleReadOutcome.NOT_FOUND,
        reason_codes=("LIFECYCLE_NOT_FOUND",),
        lifecycle_result_digest=digest,
    )

    class RecordingPersistence:
        def __init__(self):
            self.calls = []

        async def read(self, lifecycle_result_digest):
            self.calls.append(lifecycle_result_digest)
            return expected

    persistence = RecordingPersistence()
    result = await PaperLifecycleQueryService(persistence).query(digest)

    assert persistence.calls == [digest]
    assert result is expected
    assert result.outcome is PaperLifecycleReadOutcome.NOT_FOUND
    assert result.lifecycle_result_digest == digest


@pytest.mark.asyncio
async def test_found_query_preserves_identity_provenance_order_and_is_repeatable(
    sqlite_runtime,
):
    lifecycle = _complete_lifecycle()
    persistence = ControlledPaperPersistenceService(sqlite_runtime)
    await persistence.persist(lifecycle)
    query = PaperLifecycleQueryService(persistence)

    first = await query.query(lifecycle.digest)
    second = await query.query(lifecycle.digest)

    assert first.outcome is PaperLifecycleReadOutcome.FOUND
    assert first == second
    assert first.digest == second.digest
    assert first.lifecycle_result_digest == lifecycle.digest
    assert first.run is not None
    assert first.run.lifecycle_result_digest == lifecycle.digest
    assert first.run.lifecycle_contract_version == lifecycle.contract_version
    assert tuple(artifact.ordinal for artifact in first.artifacts) == tuple(
        range(1, len(first.artifacts) + 1)
    )
    assert all(artifact.owner_contract_version for artifact in first.artifacts)
    assert all(artifact.canonical_payload for artifact in first.artifacts)


@pytest.mark.asyncio
async def test_unknown_valid_identity_is_not_found(sqlite_runtime):
    digest = "f" * 64

    result = await PaperLifecycleQueryService(
        ControlledPaperPersistenceService(sqlite_runtime)
    ).query(digest)

    assert result.outcome is PaperLifecycleReadOutcome.NOT_FOUND
    assert result.reason_codes == ("LIFECYCLE_NOT_FOUND",)
    assert result.lifecycle_result_digest == digest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "malformed",
    ("not-a-digest", "A" * 64, "a" * 63, "a" * 65, "g" * 64),
)
async def test_malformed_identity_preserves_rti_03_value_error(
    sqlite_runtime,
    malformed,
):
    query = PaperLifecycleQueryService(
        ControlledPaperPersistenceService(sqlite_runtime)
    )

    with pytest.raises(ValueError, match="lifecycle_result_digest must be a digest"):
        await query.query(malformed)


@pytest.mark.asyncio
async def test_corrupt_and_storage_unavailable_outcomes_propagate_unchanged(
    sqlite_runtime,
):
    lifecycle = _complete_lifecycle()
    persistence = ControlledPaperPersistenceService(sqlite_runtime)
    await persistence.persist(lifecycle)
    async with sqlite_runtime.session_scope() as session:
        artifact = await session.scalar(select(PaperLifecycleArtifact))
        assert artifact is not None
        artifact.canonical_payload = "{}"

    corrupt = await PaperLifecycleQueryService(persistence).query(lifecycle.digest)

    unavailable_runtime = DatabaseRuntime(
        Settings(_env_file=None, app_env="test", database_url=None)
    )
    unavailable = await PaperLifecycleQueryService(
        ControlledPaperPersistenceService(unavailable_runtime)
    ).query(lifecycle.digest)

    assert corrupt.outcome is PaperLifecycleReadOutcome.CORRUPT
    assert corrupt.reason_codes == ("STORED_BUNDLE_CORRUPT",)
    assert unavailable.outcome is PaperLifecycleReadOutcome.STORAGE_UNAVAILABLE
    assert unavailable.reason_codes == ("DATABASE_UNAVAILABLE",)


@pytest.mark.asyncio
async def test_bounded_rti_03_read_failure_does_not_leak(sqlite_runtime):
    class FailingReadRepository(PaperLifecycleRepository):
        async def get_run(self, session, lifecycle_result_digest):
            raise SQLAlchemyError("forced read failure")

    persistence = ControlledPaperPersistenceService(
        sqlite_runtime,
        repository=FailingReadRepository(),
    )

    result = await PaperLifecycleQueryService(persistence).query("e" * 64)

    assert result.outcome is PaperLifecycleReadOutcome.STORAGE_UNAVAILABLE
    assert result.reason_codes == ("DATABASE_READ_FAILED",)
    assert result.lifecycle_result_digest == "e" * 64


@pytest.mark.asyncio
async def test_query_executes_only_selects_and_never_repairs_corrupt_data(
    sqlite_runtime,
):
    lifecycle = _complete_lifecycle()
    persistence = ControlledPaperPersistenceService(sqlite_runtime)
    await persistence.persist(lifecycle)
    async with sqlite_runtime.session_scope() as session:
        artifact = await session.scalar(select(PaperLifecycleArtifact))
        assert artifact is not None
        artifact.canonical_payload = "{}"
    before = await _counts(sqlite_runtime)
    statements = []

    def record_statement(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(sqlite_runtime.engine.sync_engine, "before_cursor_execute", record_statement)
    try:
        result = await PaperLifecycleQueryService(persistence).query(lifecycle.digest)
    finally:
        event.remove(
            sqlite_runtime.engine.sync_engine,
            "before_cursor_execute",
            record_statement,
        )

    assert result.outcome is PaperLifecycleReadOutcome.CORRUPT
    assert statements and set(statements) == {"SELECT"}
    assert await _counts(sqlite_runtime) == before
    async with sqlite_runtime.session_scope() as session:
        artifact = await session.scalar(select(PaperLifecycleArtifact))
        assert artifact is not None
        assert artifact.canonical_payload == "{}"


def test_query_module_has_only_the_rti_03_application_dependency():
    module_path = Path(__file__).parents[1] / "backend/application/paper_lifecycle_query.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert imports == {
        "__future__",
        "backend.application.paper_lifecycle_persistence",
    }
