import ast
from contextlib import asynccontextmanager
import json
from pathlib import Path

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy import event, func, select

from backend.api.main import create_app
from backend.api.paper_lifecycle_results import get_paper_lifecycle_query
from backend.application import (
    ControlledPaperPersistenceService,
    PaperLifecycleQueryService,
    PaperLifecycleReadOutcome,
    PaperLifecycleReadResult,
)
from backend.core.config import Settings
from backend.core.models import Base, PaperLifecycleArtifact, PaperLifecycleRun
from tests.test_controlled_paper_persistence import _complete_lifecycle


@asynccontextmanager
async def _api_context(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'rti-06.db'}",
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        runtime = application.state.database
        assert runtime.engine is not None
        async with runtime.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        transport = ASGITransport(app=application, raise_app_exceptions=False)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            yield application, client, runtime


@pytest_asyncio.fixture
async def api_context(tmp_path):
    async with _api_context(tmp_path) as context:
        yield context


async def _counts(runtime):
    async with runtime.session_scope() as session:
        return (
            await session.scalar(select(func.count()).select_from(PaperLifecycleRun)),
            await session.scalar(
                select(func.count()).select_from(PaperLifecycleArtifact)
            ),
        )


def _json_value(value):
    return json.loads(json.dumps(value))


@pytest.mark.asyncio
async def test_found_route_preserves_complete_rti_05_result(api_context):
    _application, client, runtime = api_context
    lifecycle = _complete_lifecycle()
    persistence = ControlledPaperPersistenceService(runtime)
    await persistence.persist(lifecycle)
    expected = await PaperLifecycleQueryService(persistence).query(lifecycle.digest)

    first = await client.get(
        f"/api/v1/paper-lifecycle-results/{lifecycle.digest}",
        headers={"X-Request-ID": "rti-06-found"},
    )
    second = await client.get(
        f"/api/v1/paper-lifecycle-results/{lifecycle.digest}"
    )

    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-store"
    assert first.headers["x-request-id"] == "rti-06-found"
    assert first.json() == second.json()
    body = first.json()
    assert body == {
        "contract_version": expected.contract_version,
        "outcome": "FOUND",
        "reason_codes": [],
        "lifecycle_result_digest": lifecycle.digest,
        "result_digest": expected.digest,
        "run": _json_value(expected.run.canonical_representation),
        "artifacts": [
            _json_value(artifact.canonical_representation)
            for artifact in expected.artifacts
        ],
    }
    assert [artifact["ordinal"] for artifact in body["artifacts"]] == list(
        range(1, len(body["artifacts"]) + 1)
    )
    assert all(artifact["canonical_payload"] for artifact in body["artifacts"])
    assert "id" not in body["run"]
    assert all("id" not in artifact for artifact in body["artifacts"])


@pytest.mark.asyncio
async def test_route_delegates_once_with_exact_unmodified_identity(api_context):
    application, client, _runtime = api_context
    digest = "a" * 64
    expected = PaperLifecycleReadResult(
        outcome=PaperLifecycleReadOutcome.NOT_FOUND,
        reason_codes=("LIFECYCLE_NOT_FOUND",),
        lifecycle_result_digest=digest,
    )

    class RecordingQuery:
        def __init__(self):
            self.calls = []

        async def query(self, lifecycle_result_digest):
            self.calls.append(lifecycle_result_digest)
            return expected

    query = RecordingQuery()
    application.dependency_overrides[get_paper_lifecycle_query] = lambda: query
    try:
        response = await client.get(
            f"/api/v1/paper-lifecycle-results/{digest}"
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 404
    assert query.calls == [digest]
    assert response.json()["lifecycle_result_digest"] == digest
    assert response.json()["outcome"] == "NOT_FOUND"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("outcome", "reason", "expected_status"),
    (
        (PaperLifecycleReadOutcome.NOT_FOUND, "LIFECYCLE_NOT_FOUND", 404),
        (PaperLifecycleReadOutcome.CORRUPT, "STORED_BUNDLE_CORRUPT", 409),
        (
            PaperLifecycleReadOutcome.STORAGE_UNAVAILABLE,
            "DATABASE_UNAVAILABLE",
            503,
        ),
    ),
)
async def test_non_found_outcomes_preserve_vocabulary_and_shape(
    api_context,
    outcome,
    reason,
    expected_status,
):
    application, client, _runtime = api_context
    digest = "b" * 64
    expected = PaperLifecycleReadResult(
        outcome=outcome,
        reason_codes=(reason,),
        lifecycle_result_digest=digest,
    )

    class FixedQuery:
        async def query(self, lifecycle_result_digest):
            assert lifecycle_result_digest == digest
            return expected

    application.dependency_overrides[get_paper_lifecycle_query] = FixedQuery
    try:
        response = await client.get(
            f"/api/v1/paper-lifecycle-results/{digest}"
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "contract_version": expected.contract_version,
        "outcome": outcome.value,
        "reason_codes": [reason],
        "lifecycle_result_digest": digest,
        "result_digest": expected.digest,
        "run": None,
        "artifacts": [],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "malformed",
    ("not-a-digest", "A" * 64, "a" * 63, "a" * 65, "g" * 64),
)
async def test_malformed_digest_uses_rti_03_validation_and_safe_422(
    api_context,
    malformed,
):
    _application, client, _runtime = api_context

    response = await client.get(
        f"/api/v1/paper-lifecycle-results/{malformed}",
        headers={"X-Request-ID": "invalid-digest-request"},
    )

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "invalid-digest-request"
    assert response.json() == {
        "error": {
            "code": "invalid_lifecycle_result_digest",
            "message": (
                "lifecycle_result_digest must be a lowercase SHA-256 digest"
            ),
            "request_id": "invalid-digest-request",
        }
    }
    assert malformed not in response.text


@pytest.mark.asyncio
async def test_unexpected_exception_uses_existing_safe_500(api_context):
    application, client, _runtime = api_context

    class FailingQuery:
        async def query(self, lifecycle_result_digest):
            raise RuntimeError("secret internal query detail")

    application.dependency_overrides[get_paper_lifecycle_query] = FailingQuery
    try:
        response = await client.get(
            f"/api/v1/paper-lifecycle-results/{'c' * 64}",
            headers={"X-Request-ID": "failed-query-request"},
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "failed-query-request"
    assert response.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "Internal server error",
            "request_id": "failed-query-request",
        }
    }
    assert "secret internal query detail" not in response.text
    assert "Traceback" not in response.text


@pytest.mark.asyncio
async def test_corrupt_read_executes_only_selects_and_never_repairs(api_context):
    _application, client, runtime = api_context
    lifecycle = _complete_lifecycle()
    persistence = ControlledPaperPersistenceService(runtime)
    await persistence.persist(lifecycle)
    async with runtime.session_scope() as session:
        artifact = await session.scalar(select(PaperLifecycleArtifact))
        assert artifact is not None
        artifact.canonical_payload = "{}"
    before = await _counts(runtime)
    statements = []

    def record_statement(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(runtime.engine.sync_engine, "before_cursor_execute", record_statement)
    try:
        response = await client.get(
            f"/api/v1/paper-lifecycle-results/{lifecycle.digest}"
        )
    finally:
        event.remove(
            runtime.engine.sync_engine,
            "before_cursor_execute",
            record_statement,
        )

    assert response.status_code == 409
    assert response.json()["outcome"] == "CORRUPT"
    assert statements and set(statements) == {"SELECT"}
    assert await _counts(runtime) == before
    async with runtime.session_scope() as session:
        artifact = await session.scalar(select(PaperLifecycleArtifact))
        assert artifact is not None
        assert artifact.canonical_payload == "{}"


@pytest.mark.asyncio
async def test_mutation_methods_do_not_invoke_query(api_context):
    application, client, _runtime = api_context

    class RecordingQuery:
        def __init__(self):
            self.calls = 0

        async def query(self, lifecycle_result_digest):
            self.calls += 1
            raise AssertionError("query must not be invoked")

    query = RecordingQuery()
    application.dependency_overrides[get_paper_lifecycle_query] = lambda: query
    try:
        path = f"/api/v1/paper-lifecycle-results/{'d' * 64}"
        responses = [
            await client.post(path),
            await client.put(path),
            await client.patch(path),
            await client.delete(path),
        ]
    finally:
        application.dependency_overrides.clear()

    assert [response.status_code for response in responses] == [405] * 4
    assert query.calls == 0


def test_transport_has_no_independent_validator_or_forbidden_dependencies():
    module_path = (
        Path(__file__).parents[1]
        / "backend/api/paper_lifecycle_results.py"
    )
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "re" not in imports
    assert "hashlib" not in imports
    assert "lower(" not in source
    assert not any(
        fragment in imported
        for imported in imports
        for fragment in (
            "controlled_paper_run_service",
            "controlled_paper_lifecycle",
            "provider",
            "worker",
            "scheduler",
            "wallet",
            "execution",
            "outcome_learning",
        )
    )
