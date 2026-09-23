"""Focused conformance tests for the closed RTI-06/RTI-08 API family."""

from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio

from backend.api.main import create_app
from backend.api.paper_lifecycle_results import (
    get_paper_lifecycle_digest_catalog,
    get_paper_lifecycle_query,
)
from backend.application import (
    PaperLifecycleDigestCatalogOutcome,
    PaperLifecycleDigestCatalogResult,
    PaperLifecycleReadOutcome,
    PaperLifecycleReadResult,
)
from backend.core.config import Settings


COLLECTION_PATH = "/api/v1/paper-lifecycle-results"
DETAIL_TEMPLATE = "/api/v1/paper-lifecycle-results/{lifecycle_result_digest}"
CATALOG_FIELDS = {
    "contract_version",
    "outcome",
    "reason_codes",
    "limit",
    "after_digest",
    "lifecycle_result_digests",
    "next_after_digest",
    "result_digest",
}
READ_FIELDS = {
    "contract_version",
    "outcome",
    "reason_codes",
    "lifecycle_result_digest",
    "result_digest",
    "run",
    "artifacts",
}
RUN_FIELDS = {
    "contract_version",
    "outcome",
    "reason_codes",
    "admission_digest",
    "fill_digest",
    "transition_digest",
    "ledger_digest",
    "reconciliation_digest",
    "paper_result_digest",
    "history_digest",
    "observation_digest",
    "lifecycle_result_digest",
    "decision_intent_digest",
    "simulation_input_digest",
    "artifact_count",
}
ARTIFACT_FIELDS = {
    "artifact_kind",
    "artifact_digest",
    "payload_digest",
    "owner_contract_version",
    "canonical_payload",
    "ordinal",
}


@asynccontextmanager
async def _api_context():
    application = create_app(
        Settings(_env_file=None, app_env="test", database_url=None)
    )
    async with application.router.lifespan_context(application):
        transport = ASGITransport(app=application, raise_app_exceptions=False)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            yield application, client


@pytest_asyncio.fixture
async def api_context():
    async with _api_context() as context:
        yield context


def _response_ref(operation, status_code):
    return operation["responses"][str(status_code)]["content"][
        "application/json"
    ]["schema"]["$ref"]


def _catalog_result(
    outcome=PaperLifecycleDigestCatalogOutcome.PAGE,
    reasons=(),
):
    return PaperLifecycleDigestCatalogResult(
        outcome=outcome,
        reason_codes=reasons,
        limit=50,
        after_digest=None,
    )


def _read_result(outcome, reason):
    return PaperLifecycleReadResult(
        outcome=outcome,
        reason_codes=(reason,),
        lifecycle_result_digest="a" * 64,
    )


def test_openapi_exposes_exact_read_only_lifecycle_resource_family():
    schema = create_app(
        Settings(_env_file=None, app_env="test", database_url=None)
    ).openapi()
    lifecycle_paths = {
        path: path_item
        for path, path_item in schema["paths"].items()
        if path.startswith(COLLECTION_PATH)
    }

    assert set(lifecycle_paths) == {COLLECTION_PATH, DETAIL_TEMPLATE}
    assert set(lifecycle_paths[COLLECTION_PATH]) == {"get"}
    assert set(lifecycle_paths[DETAIL_TEMPLATE]) == {"get"}
    assert not any(
        fragment in path.lower()
        for path in lifecycle_paths
        for fragment in (
            "trigger",
            "command",
            "execute",
            "search",
            "latest",
            "history",
            "delete",
        )
    )


def test_openapi_exposes_exact_parameters_and_requiredness():
    schema = create_app(
        Settings(_env_file=None, app_env="test", database_url=None)
    ).openapi()
    collection = schema["paths"][COLLECTION_PATH]["get"]
    detail = schema["paths"][DETAIL_TEMPLATE]["get"]

    assert [
        (parameter["name"], parameter["in"], parameter["required"])
        for parameter in collection["parameters"]
    ] == [
        ("limit", "query", False),
        ("after_digest", "query", False),
    ]
    assert [
        (parameter["name"], parameter["in"], parameter["required"])
        for parameter in detail["parameters"]
    ] == [("lifecycle_result_digest", "path", True)]


def test_openapi_advertises_exact_status_and_schema_mappings():
    schema = create_app(
        Settings(_env_file=None, app_env="test", database_url=None)
    ).openapi()
    collection = schema["paths"][COLLECTION_PATH]["get"]
    detail = schema["paths"][DETAIL_TEMPLATE]["get"]

    assert set(collection["responses"]) == {"200", "422", "500", "503"}
    assert {
        status: _response_ref(collection, status)
        for status in (200, 422, 500, 503)
    } == {
        200: "#/components/schemas/PaperLifecycleDigestCatalogResponse",
        422: "#/components/schemas/TransportErrorResponse",
        500: "#/components/schemas/TransportErrorResponse",
        503: "#/components/schemas/PaperLifecycleDigestCatalogResponse",
    }
    assert set(detail["responses"]) == {
        "200",
        "404",
        "409",
        "422",
        "500",
        "503",
    }
    assert {
        status: _response_ref(detail, status)
        for status in (200, 404, 409, 422, 500, 503)
    } == {
        200: "#/components/schemas/PaperLifecycleReadResponse",
        404: "#/components/schemas/PaperLifecycleReadResponse",
        409: "#/components/schemas/PaperLifecycleReadResponse",
        422: "#/components/schemas/TransportErrorResponse",
        500: "#/components/schemas/TransportErrorResponse",
        503: "#/components/schemas/PaperLifecycleReadResponse",
    }


def test_openapi_component_fields_are_exact_and_required():
    components = create_app(
        Settings(_env_file=None, app_env="test", database_url=None)
    ).openapi()["components"]["schemas"]

    expected_fields = {
        "PaperLifecycleDigestCatalogResponse": CATALOG_FIELDS,
        "PaperLifecycleReadResponse": READ_FIELDS,
        "PaperLifecycleRunResponse": RUN_FIELDS,
        "PaperLifecycleArtifactResponse": ARTIFACT_FIELDS,
        "TransportErrorResponse": {"error"},
        "TransportErrorDetail": {"code", "message", "request_id"},
    }
    for name, fields in expected_fields.items():
        assert set(components[name]["properties"]) == fields
        assert set(components[name]["required"]) == fields


@pytest.mark.asyncio
async def test_collection_and_detail_resolve_to_only_their_authoritative_owner(
    api_context,
):
    application, client = api_context

    class RecordingCatalog:
        def __init__(self):
            self.calls = []

        async def query(self, **arguments):
            self.calls.append(arguments)
            return _catalog_result()

    class RecordingQuery:
        def __init__(self):
            self.calls = []

        async def query(self, lifecycle_result_digest):
            self.calls.append(lifecycle_result_digest)
            return _read_result(
                PaperLifecycleReadOutcome.NOT_FOUND,
                "LIFECYCLE_NOT_FOUND",
            )

    catalog = RecordingCatalog()
    query = RecordingQuery()
    application.dependency_overrides[
        get_paper_lifecycle_digest_catalog
    ] = lambda: catalog
    application.dependency_overrides[get_paper_lifecycle_query] = lambda: query
    try:
        collection = await client.get(
            COLLECTION_PATH,
            headers={"X-Request-ID": "rti-09-collection"},
        )
        detail = await client.get(
            f"{COLLECTION_PATH}/{'a' * 64}",
            headers={"X-Request-ID": "rti-09-detail"},
        )
    finally:
        application.dependency_overrides.clear()

    assert collection.status_code == 200
    assert set(collection.json()) == CATALOG_FIELDS
    assert collection.headers["cache-control"] == "no-store"
    assert collection.headers["x-request-id"] == "rti-09-collection"
    assert detail.status_code == 404
    assert set(detail.json()) == READ_FIELDS
    assert detail.headers["cache-control"] == "no-store"
    assert detail.headers["x-request-id"] == "rti-09-detail"
    assert catalog.calls == [{}]
    assert query.calls == ["a" * 64]


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
async def test_detail_outcome_status_vocabulary_remains_exact(
    api_context,
    outcome,
    reason,
    expected_status,
):
    application, client = api_context

    class FixedQuery:
        async def query(self, lifecycle_result_digest):
            assert lifecycle_result_digest == "a" * 64
            return _read_result(outcome, reason)

    application.dependency_overrides[get_paper_lifecycle_query] = FixedQuery
    try:
        response = await client.get(
            f"{COLLECTION_PATH}/{'a' * 64}",
            headers={"X-Request-ID": "rti-09-detail-outcome"},
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json()["outcome"] == outcome.value
    assert response.json()["reason_codes"] == [reason]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "rti-09-detail-outcome"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("outcome", "reasons", "expected_status"),
    (
        (PaperLifecycleDigestCatalogOutcome.PAGE, (), 200),
        (
            PaperLifecycleDigestCatalogOutcome.STORAGE_UNAVAILABLE,
            ("DATABASE_UNAVAILABLE",),
            503,
        ),
    ),
)
async def test_collection_outcome_status_vocabulary_remains_exact(
    api_context,
    outcome,
    reasons,
    expected_status,
):
    application, client = api_context

    class FixedCatalog:
        async def query(self, **arguments):
            assert arguments == {}
            return _catalog_result(outcome, reasons)

    application.dependency_overrides[
        get_paper_lifecycle_digest_catalog
    ] = FixedCatalog
    try:
        response = await client.get(
            COLLECTION_PATH,
            headers={"X-Request-ID": "rti-09-catalog-outcome"},
        )
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json()["outcome"] == outcome.value
    assert response.json()["reason_codes"] == list(reasons)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "rti-09-catalog-outcome"


@pytest.mark.asyncio
async def test_route_specific_safe_422_contracts_remain_distinct(api_context):
    application, client = api_context

    class InvalidDigestQuery:
        async def query(self, lifecycle_result_digest):
            raise ValueError("lifecycle_result_digest must be a digest")

    application.dependency_overrides[
        get_paper_lifecycle_query
    ] = InvalidDigestQuery
    try:
        collection = await client.get(
            f"{COLLECTION_PATH}?limit=not-an-integer",
            headers={"X-Request-ID": "rti-09-invalid-collection"},
        )
        detail = await client.get(
            f"{COLLECTION_PATH}/not-a-digest",
            headers={"X-Request-ID": "rti-09-invalid-detail"},
        )
    finally:
        application.dependency_overrides.clear()

    assert collection.status_code == 422
    assert collection.json() == {
        "error": {
            "code": "invalid_catalog_query",
            "message": "limit or after_digest is invalid",
            "request_id": "rti-09-invalid-collection",
        }
    }
    assert detail.status_code == 422
    assert detail.json() == {
        "error": {
            "code": "invalid_lifecycle_result_digest",
            "message": (
                "lifecycle_result_digest must be a lowercase SHA-256 digest"
            ),
            "request_id": "rti-09-invalid-detail",
        }
    }
    for response in (collection, detail):
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-request-id"]
        assert "ValueError" not in response.text
        assert "Traceback" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ("collection", "detail"))
async def test_unexpected_exceptions_keep_existing_safe_500_contract(
    api_context,
    target,
):
    application, client = api_context

    class FailingOwner:
        async def query(self, *args, **kwargs):
            raise RuntimeError("secret RTI-09 internal detail")

    dependency = (
        get_paper_lifecycle_digest_catalog
        if target == "collection"
        else get_paper_lifecycle_query
    )
    application.dependency_overrides[dependency] = FailingOwner
    path = (
        COLLECTION_PATH
        if target == "collection"
        else f"{COLLECTION_PATH}/{'a' * 64}"
    )
    request_id = f"rti-09-{target}-failure"
    try:
        response = await client.get(path, headers={"X-Request-ID": request_id})
    finally:
        application.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "Internal server error",
            "request_id": request_id,
        }
    }
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == request_id
    assert "secret RTI-09 internal detail" not in response.text
    assert "Traceback" not in response.text


@pytest.mark.asyncio
async def test_mutation_methods_on_both_routes_invoke_no_owner(api_context):
    application, client = api_context

    class ForbiddenOwner:
        async def query(self, *args, **kwargs):
            raise AssertionError("read owner must not be invoked")

    application.dependency_overrides[
        get_paper_lifecycle_digest_catalog
    ] = ForbiddenOwner
    application.dependency_overrides[get_paper_lifecycle_query] = ForbiddenOwner
    try:
        responses = []
        for path in (COLLECTION_PATH, f"{COLLECTION_PATH}/{'a' * 64}"):
            for method in ("post", "put", "patch", "delete"):
                responses.append(await getattr(client, method)(path))
    finally:
        application.dependency_overrides.clear()

    assert [response.status_code for response in responses] == [405] * 8


@pytest.mark.asyncio
async def test_forbidden_nested_paths_are_unexposed_and_invoke_no_owner(
    api_context,
):
    application, client = api_context

    class ForbiddenOwner:
        async def query(self, *args, **kwargs):
            raise AssertionError("read owner must not be invoked")

    application.dependency_overrides[
        get_paper_lifecycle_digest_catalog
    ] = ForbiddenOwner
    application.dependency_overrides[get_paper_lifecycle_query] = ForbiddenOwner
    forbidden_paths = (
        f"{COLLECTION_PATH}/trigger/run",
        f"{COLLECTION_PATH}/search/by-token",
        f"{COLLECTION_PATH}/latest/history",
        f"{COLLECTION_PATH}/{'a' * 64}/execute",
    )
    try:
        responses = [await client.get(path) for path in forbidden_paths]
    finally:
        application.dependency_overrides.clear()

    assert [response.status_code for response in responses] == [404] * 4
