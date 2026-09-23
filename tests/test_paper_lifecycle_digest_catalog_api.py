import ast
from contextlib import asynccontextmanager
from pathlib import Path

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy import event

from backend.api.main import create_app
from backend.api.paper_lifecycle_results import (
    get_paper_lifecycle_digest_catalog,
)
from backend.application import (
    PaperLifecycleDigestCatalogOutcome,
    PaperLifecycleDigestCatalogResult,
)
from backend.core.config import Settings
from backend.core.models import Base, PaperLifecycleRun


@asynccontextmanager
async def _api_context(tmp_path):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'rti-08.db'}",
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


async def _insert_roots(runtime, *digests):
    async with runtime.session_scope() as session:
        session.add_all(
            PaperLifecycleRun(
                lifecycle_result_digest=digest,
                lifecycle_contract_version="catalog-does-not-validate-bundle",
                outcome="ROOT_ONLY",
                reason_codes_json="not-json",
                admission_digest="z" * 64,
                artifact_count=999,
            )
            for digest in digests
        )


def _catalog_result(
    *,
    outcome=PaperLifecycleDigestCatalogOutcome.PAGE,
    reasons=(),
    limit=2,
    after_digest=None,
    digests=(),
    next_after_digest=None,
):
    return PaperLifecycleDigestCatalogResult(
        outcome=outcome,
        reason_codes=reasons,
        limit=limit,
        after_digest=after_digest,
        lifecycle_result_digests=digests,
        next_after_digest=next_after_digest,
    )


@pytest.mark.asyncio
async def test_omitted_parameters_return_successful_empty_default_page(api_context):
    _application, client, _runtime = api_context

    response = await client.get(
        "/api/v1/paper-lifecycle-results",
        headers={"X-Request-ID": "rti-08-empty"},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "rti-08-empty"
    assert response.json() == {
        "contract_version": "p01-rti-07-v1",
        "outcome": "PAGE",
        "reason_codes": [],
        "limit": 50,
        "after_digest": None,
        "lifecycle_result_digests": [],
        "next_after_digest": None,
        "result_digest": response.json()["result_digest"],
    }


@pytest.mark.asyncio
async def test_explicit_parameters_delegate_once_and_preserve_exact_result(api_context):
    application, client, _runtime = api_context
    after_digest = "a" * 64
    expected = _catalog_result(
        limit=2,
        after_digest=after_digest,
        digests=("b" * 64, "c" * 64),
        next_after_digest="c" * 64,
    )

    class RecordingCatalog:
        def __init__(self):
            self.calls = []

        async def query(self, **arguments):
            self.calls.append(arguments)
            return expected

    catalog = RecordingCatalog()
    application.dependency_overrides[
        get_paper_lifecycle_digest_catalog
    ] = lambda: catalog
    try:
        response = await client.get(
            "/api/v1/paper-lifecycle-results",
            params={"limit": "2", "after_digest": after_digest},
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert catalog.calls == [{"limit": 2, "after_digest": after_digest}]
    assert response.json() == {
        "contract_version": expected.contract_version,
        "outcome": "PAGE",
        "reason_codes": [],
        "limit": 2,
        "after_digest": after_digest,
        "lifecycle_result_digests": ["b" * 64, "c" * 64],
        "next_after_digest": "c" * 64,
        "result_digest": expected.digest,
    }


@pytest.mark.asyncio
async def test_maximum_limit_is_accepted_and_delegated(api_context):
    application, client, _runtime = api_context
    expected = _catalog_result(limit=100)

    class MaxCatalog:
        async def query(self, **arguments):
            assert arguments == {"limit": 100}
            return expected

    application.dependency_overrides[
        get_paper_lifecycle_digest_catalog
    ] = MaxCatalog
    try:
        response = await client.get(
            "/api/v1/paper-lifecycle-results?limit=100"
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["limit"] == 100


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    (
        "limit=not-an-integer",
        "limit=true",
        "limit=0",
        "limit=-1",
        "limit=101",
        f"after_digest={'A' * 64}",
        f"after_digest={'a' * 63}",
        f"after_digest={'a' * 65}",
        f"after_digest={'g' * 64}",
    ),
)
async def test_invalid_query_uses_fixed_safe_422(api_context, query):
    _application, client, _runtime = api_context

    response = await client.get(
        f"/api/v1/paper-lifecycle-results?{query}",
        headers={"X-Request-ID": "rti-08-invalid"},
    )

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "rti-08-invalid"
    assert response.json() == {
        "error": {
            "code": "invalid_catalog_query",
            "message": "limit or after_digest is invalid",
            "request_id": "rti-08-invalid",
        }
    }
    assert "ValueError" not in response.text
    assert "Traceback" not in response.text


@pytest.mark.asyncio
async def test_storage_unavailable_maps_to_exact_safe_503_result(api_context):
    application, client, _runtime = api_context
    after_digest = "d" * 64
    expected = _catalog_result(
        outcome=PaperLifecycleDigestCatalogOutcome.STORAGE_UNAVAILABLE,
        reasons=("DATABASE_READ_FAILED",),
        limit=7,
        after_digest=after_digest,
    )

    class UnavailableCatalog:
        async def query(self, **arguments):
            assert arguments == {"limit": 7, "after_digest": after_digest}
            return expected

    application.dependency_overrides[
        get_paper_lifecycle_digest_catalog
    ] = UnavailableCatalog
    try:
        response = await client.get(
            "/api/v1/paper-lifecycle-results",
            params={"limit": 7, "after_digest": after_digest},
            headers={"X-Request-ID": "rti-08-unavailable"},
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "rti-08-unavailable"
    assert response.json() == {
        "contract_version": expected.contract_version,
        "outcome": "STORAGE_UNAVAILABLE",
        "reason_codes": ["DATABASE_READ_FAILED"],
        "limit": 7,
        "after_digest": after_digest,
        "lifecycle_result_digests": [],
        "next_after_digest": None,
        "result_digest": expected.digest,
    }


@pytest.mark.asyncio
async def test_unexpected_exception_uses_existing_safe_500(api_context):
    application, client, _runtime = api_context

    class FailingCatalog:
        async def query(self, **arguments):
            raise RuntimeError("secret catalog detail")

    application.dependency_overrides[
        get_paper_lifecycle_digest_catalog
    ] = FailingCatalog
    try:
        response = await client.get(
            "/api/v1/paper-lifecycle-results",
            headers={"X-Request-ID": "rti-08-failure"},
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "rti-08-failure"
    assert response.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "Internal server error",
            "request_id": "rti-08-failure",
        }
    }
    assert "secret catalog detail" not in response.text
    assert "Traceback" not in response.text


@pytest.mark.asyncio
async def test_route_preserves_store_order_cursor_and_performs_only_root_select(
    api_context,
):
    _application, client, runtime = api_context
    await _insert_roots(runtime, "d" * 64, "a" * 64, "c" * 64, "b" * 64)
    statements = []

    def record_statement(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(runtime.engine.sync_engine, "before_cursor_execute", record_statement)
    try:
        first = await client.get(
            "/api/v1/paper-lifecycle-results?limit=2"
        )
        second = await client.get(
            "/api/v1/paper-lifecycle-results",
            params={"limit": 2, "after_digest": "b" * 64},
        )
    finally:
        event.remove(
            runtime.engine.sync_engine,
            "before_cursor_execute",
            record_statement,
        )

    assert first.json()["lifecycle_result_digests"] == ["a" * 64, "b" * 64]
    assert first.json()["next_after_digest"] == "b" * 64
    assert second.json()["lifecycle_result_digests"] == ["c" * 64, "d" * 64]
    assert second.json()["next_after_digest"] is None
    normalized = " ".join(statements).lower()
    assert "paper_lifecycle_artifacts" not in normalized
    assert "lifecycle_contract_version" not in normalized
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)


@pytest.mark.asyncio
async def test_repeated_unchanged_requests_have_equivalent_bodies(api_context):
    _application, client, _runtime = api_context

    first = await client.get("/api/v1/paper-lifecycle-results")
    second = await client.get("/api/v1/paper-lifecycle-results")

    assert first.json() == second.json()


@pytest.mark.asyncio
async def test_mutation_methods_do_not_invoke_catalog(api_context):
    application, client, _runtime = api_context

    class RecordingCatalog:
        def __init__(self):
            self.calls = 0

        async def query(self, **arguments):
            self.calls += 1
            raise AssertionError("catalog must not be invoked")

    catalog = RecordingCatalog()
    application.dependency_overrides[
        get_paper_lifecycle_digest_catalog
    ] = lambda: catalog
    try:
        path = "/api/v1/paper-lifecycle-results"
        responses = [
            await client.post(path),
            await client.put(path),
            await client.patch(path),
            await client.delete(path),
        ]
    finally:
        application.dependency_overrides.clear()

    assert [response.status_code for response in responses] == [405] * 4
    assert catalog.calls == 0


def test_transport_has_no_direct_repository_model_or_forbidden_dependency():
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

    assert "backend.core.repositories" not in imports
    assert "backend.core.models" not in imports
    assert "sqlalchemy" not in source.lower()
    assert "paper_lifecycle_artifact" not in source
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
