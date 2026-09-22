import ast
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import event, func, select
from sqlalchemy.exc import SQLAlchemyError

from backend.application import (
    P01_RTI_07_CONTRACT_VERSION,
    PaperLifecycleDigestCatalogOutcome,
    PaperLifecycleDigestCatalogResult,
    PaperLifecycleDigestCatalogService,
)
from backend.core.config import Settings
from backend.core.database import DatabaseRuntime, DatabaseState
from backend.core.models import Base, PaperLifecycleArtifact, PaperLifecycleRun
from backend.core.repositories import PaperLifecycleRepository


@pytest_asyncio.fixture
async def sqlite_runtime(tmp_path):
    runtime = DatabaseRuntime(
        Settings(
            _env_file=None,
            app_env="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'catalog.db'}",
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


async def _insert_roots(runtime, *digests):
    async with runtime.session_scope() as session:
        session.add_all(
            PaperLifecycleRun(
                lifecycle_result_digest=digest,
                lifecycle_contract_version="deliberately-not-validated-by-catalog",
                outcome="CORRUPT_ROOT_IS_STILL_AN_IDENTITY",
                reason_codes_json="not-json",
                admission_digest="z" * 64,
                artifact_count=999,
            )
            for digest in digests
        )


async def _counts(runtime):
    async with runtime.session_scope() as session:
        return (
            await session.scalar(select(func.count()).select_from(PaperLifecycleRun)),
            await session.scalar(
                select(func.count()).select_from(PaperLifecycleArtifact)
            ),
        )


@pytest.mark.asyncio
async def test_empty_catalog_is_successful_deterministic_default_page(sqlite_runtime):
    service = PaperLifecycleDigestCatalogService(sqlite_runtime)

    first = await service.query()
    second = await service.query()

    assert first == second
    assert first.outcome is PaperLifecycleDigestCatalogOutcome.PAGE
    assert first.reason_codes == ()
    assert first.limit == 50
    assert first.after_digest is None
    assert first.lifecycle_result_digests == ()
    assert first.next_after_digest is None
    assert first.contract_version == P01_RTI_07_CONTRACT_VERSION
    assert first.digest == second.digest
    assert len(first.digest) == 64


@pytest.mark.asyncio
async def test_catalog_orders_lexicographically_and_uses_exclusive_keyset_cursor(
    sqlite_runtime,
):
    digests = ("d" * 64, "a" * 64, "c" * 64, "b" * 64)
    await _insert_roots(sqlite_runtime, *digests)
    service = PaperLifecycleDigestCatalogService(sqlite_runtime)

    first = await service.query(limit=2)
    second = await service.query(limit=2, after_digest=first.next_after_digest)

    assert first.lifecycle_result_digests == ("a" * 64, "b" * 64)
    assert first.next_after_digest == "b" * 64
    assert second.after_digest == "b" * 64
    assert second.lifecycle_result_digests == ("c" * 64, "d" * 64)
    assert second.next_after_digest is None
    assert first.lifecycle_result_digests[-1] not in second.lifecycle_result_digests


@pytest.mark.asyncio
async def test_valid_nonexistent_cursor_selects_only_later_digests(sqlite_runtime):
    await _insert_roots(sqlite_runtime, "a" * 64, "d" * 64)

    result = await PaperLifecycleDigestCatalogService(sqlite_runtime).query(
        after_digest="c" * 64
    )

    assert result.outcome is PaperLifecycleDigestCatalogOutcome.PAGE
    assert result.lifecycle_result_digests == ("d" * 64,)


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", (True, 0, -1, 101, 1.5, "50"))
async def test_invalid_limit_is_application_validation_failure(sqlite_runtime, limit):
    with pytest.raises(ValueError, match="limit must be an integer between 1 and 100"):
        await PaperLifecycleDigestCatalogService(sqlite_runtime).query(limit=limit)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "after_digest",
    ("not-a-digest", "A" * 64, "a" * 63, "a" * 65, "g" * 64),
)
async def test_malformed_cursor_reuses_rti_03_validation(sqlite_runtime, after_digest):
    with pytest.raises(
        ValueError,
        match="lifecycle_result_digest must be a lowercase SHA-256 digest",
    ):
        await PaperLifecycleDigestCatalogService(sqlite_runtime).query(
            after_digest=after_digest
        )


@pytest.mark.asyncio
async def test_hard_max_is_allowed_and_repository_probe_is_bounded(sqlite_runtime):
    class RecordingRepository(PaperLifecycleRepository):
        def __init__(self):
            self.calls = []

        async def list_run_digests(self, session, *, limit, after_digest):
            self.calls.append((limit, after_digest))
            return ()

    repository = RecordingRepository()

    result = await PaperLifecycleDigestCatalogService(
        sqlite_runtime, repository=repository
    ).query(limit=100)

    assert result.limit == 100
    assert repository.calls == [(101, None)]


@pytest.mark.asyncio
async def test_catalog_does_not_read_artifacts_or_validate_complete_bundle(
    sqlite_runtime,
):
    await _insert_roots(sqlite_runtime, "a" * 64)
    statements = []

    def record_statement(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(sqlite_runtime.engine.sync_engine, "before_cursor_execute", record_statement)
    try:
        result = await PaperLifecycleDigestCatalogService(sqlite_runtime).query()
    finally:
        event.remove(
            sqlite_runtime.engine.sync_engine,
            "before_cursor_execute",
            record_statement,
        )

    normalized = " ".join(statements).lower()
    assert result.lifecycle_result_digests == ("a" * 64,)
    assert "paper_lifecycle_runs.lifecycle_result_digest" in normalized
    assert "paper_lifecycle_artifacts" not in normalized
    assert "lifecycle_contract_version" not in normalized


@pytest.mark.asyncio
async def test_catalog_is_select_only_and_never_mutates_storage(sqlite_runtime):
    await _insert_roots(sqlite_runtime, "b" * 64, "a" * 64)
    before = await _counts(sqlite_runtime)
    verbs = []

    def record_statement(_conn, _cursor, statement, _parameters, _context, _many):
        verbs.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(sqlite_runtime.engine.sync_engine, "before_cursor_execute", record_statement)
    try:
        await PaperLifecycleDigestCatalogService(sqlite_runtime).query()
    finally:
        event.remove(
            sqlite_runtime.engine.sync_engine,
            "before_cursor_execute",
            record_statement,
        )

    assert verbs and set(verbs) == {"SELECT"}
    assert await _counts(sqlite_runtime) == before


@pytest.mark.asyncio
async def test_storage_unavailable_is_bounded_and_does_not_leak(sqlite_runtime):
    class FailingRepository(PaperLifecycleRepository):
        async def list_run_digests(self, session, *, limit, after_digest):
            raise SQLAlchemyError("secret database detail")

    failure = await PaperLifecycleDigestCatalogService(
        sqlite_runtime,
        repository=FailingRepository(),
    ).query(limit=7, after_digest="a" * 64)
    unavailable_runtime = DatabaseRuntime(
        Settings(_env_file=None, app_env="test", database_url=None)
    )
    unavailable = await PaperLifecycleDigestCatalogService(
        unavailable_runtime
    ).query()

    assert failure.outcome is PaperLifecycleDigestCatalogOutcome.STORAGE_UNAVAILABLE
    assert failure.reason_codes == ("DATABASE_READ_FAILED",)
    assert failure.limit == 7
    assert failure.after_digest == "a" * 64
    assert failure.lifecycle_result_digests == ()
    assert failure.next_after_digest is None
    assert "secret" not in repr(failure)
    assert unavailable.outcome is PaperLifecycleDigestCatalogOutcome.STORAGE_UNAVAILABLE
    assert unavailable.reason_codes == ("DATABASE_UNAVAILABLE",)


@pytest.mark.asyncio
async def test_invalid_repository_identity_fails_closed_as_storage_unavailable(
    sqlite_runtime,
):
    class InvalidIdentityRepository(PaperLifecycleRepository):
        async def list_run_digests(self, session, *, limit, after_digest):
            return ("NOT-CANONICAL",)

    result = await PaperLifecycleDigestCatalogService(
        sqlite_runtime,
        repository=InvalidIdentityRepository(),
    ).query()

    assert result.outcome is PaperLifecycleDigestCatalogOutcome.STORAGE_UNAVAILABLE
    assert result.reason_codes == ("DATABASE_READ_FAILED",)
    assert result.lifecycle_result_digests == ()


def test_result_is_immutable_and_result_digest_covers_contract_fields():
    result = PaperLifecycleDigestCatalogResult(
        outcome=PaperLifecycleDigestCatalogOutcome.PAGE,
        reason_codes=(),
        limit=1,
        after_digest=None,
        lifecycle_result_digests=("a" * 64,),
    )

    with pytest.raises(FrozenInstanceError):
        result.limit = 2
    with pytest.raises(ValueError, match="result_digest does not match"):
        replace(result, limit=2)


def test_catalog_module_has_no_transport_execution_or_provider_dependencies():
    module_path = (
        Path(__file__).parents[1]
        / "backend/application/paper_lifecycle_digest_catalog.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert imports == {
        "__future__",
        "dataclasses",
        "enum",
        "typing",
        "sqlalchemy.exc",
        "backend.application.paper_lifecycle_persistence",
        "backend.core.database",
        "backend.core.repositories",
    }
