import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.api.main import app, create_app
from backend.core.config import Settings
from backend.core.database import (
    DatabaseRuntime,
    DatabaseState,
    get_database_config,
    redact_database_url,
)
from backend.core.logging import configure_logging
from backend.core.models import Base, SystemMetadata
from backend.core.repositories import SystemMetadataRepository
from backend.core.runtime import SERVICE_NAME

TEST_SETTINGS = Settings(_env_file=None, app_env="test", database_url=None)
foundation_app = create_app(TEST_SETTINGS)


def test_application_imports() -> None:
    assert app.title == "Meme Coin Hunter AI"


def test_health_returns_process_status() -> None:
    with TestClient(foundation_app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == SERVICE_NAME


def test_ready_reports_internal_runtime_readiness() -> None:
    with TestClient(foundation_app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"]["application"] == "ok"
    assert response.json()["checks"]["database"] == "not_configured"


def test_request_id_is_generated_and_preserved() -> None:
    with TestClient(foundation_app) as client:
        generated = client.get("/health")
        supplied = client.get("/health", headers={"X-Request-ID": "request-123"})

    assert generated.headers["X-Request-ID"]
    assert supplied.headers["X-Request-ID"] == "request-123"


def test_configuration_loads_safe_defaults() -> None:
    settings = Settings(_env_file=None, database_url=None)

    assert settings.app_env == "development"
    assert settings.app_port == 8000
    assert settings.database_url is None


def test_configuration_accepts_explicit_overrides() -> None:
    settings = Settings(
        _env_file=None,
        app_env="test",
        app_host="127.0.0.1",
        app_port=9001,
        log_level="DEBUG",
        database_url="postgresql://example",
    )

    assert settings.app_env == "test"
    assert settings.app_host == "127.0.0.1"
    assert settings.app_port == 9001
    assert settings.log_level == "DEBUG"
    assert settings.database_url == "postgresql://example"


def test_logging_and_database_boundaries_initialize() -> None:
    settings = Settings(_env_file=None, database_url=None)

    logger = configure_logging(settings)
    database = get_database_config(settings)

    assert logger.name == "meme_coin_hunter_ai"
    assert database.state is DatabaseState.NOT_CONFIGURED
    assert database.is_connected is False


def test_database_boundary_reports_configured_without_claiming_connection() -> None:
    settings = Settings(_env_file=None, database_url="postgresql://example")

    database = get_database_config(settings)

    assert database.state is DatabaseState.CONFIGURED
    assert database.is_connected is False


def test_database_url_redaction_hides_credentials() -> None:
    redacted = redact_database_url("postgresql+asyncpg://user:secret@db.example/app")

    assert redacted == "postgresql+asyncpg://user:***@db.example/app"
    assert "secret" not in redacted


def test_postgres_url_is_normalized_for_asyncpg() -> None:
    from backend.core.database import async_database_url

    normalized = async_database_url(
        "postgresql://user:secret@db.example/app?sslmode=disable"
    )

    assert normalized == "postgresql+asyncpg://user:secret@db.example/app"


@pytest_asyncio.fixture
async def sqlite_runtime(tmp_path):
    database_file = tmp_path / "test.db"
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite+aiosqlite:///{database_file}",
    )
    runtime = DatabaseRuntime(settings)
    await runtime.start()
    assert runtime.state is DatabaseState.CONNECTED
    assert runtime.engine is not None
    async with runtime.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield runtime
    finally:
        await runtime.dispose()


@pytest.mark.asyncio
async def test_engine_session_repository_commit_and_persistence(sqlite_runtime: DatabaseRuntime) -> None:
    repository = SystemMetadataRepository()

    async with sqlite_runtime.session_scope() as session:
        await repository.set(session, "schema_version", "0001")

    async with sqlite_runtime.session_scope() as session:
        record = await repository.get(session, "schema_version")

    assert record is not None
    assert record.value == "0001"


@pytest.mark.asyncio
async def test_transaction_rolls_back_on_error(sqlite_runtime: DatabaseRuntime) -> None:
    repository = SystemMetadataRepository()

    with pytest.raises(RuntimeError, match="rollback"):
        async with sqlite_runtime.session_scope() as session:
            await repository.set(session, "temporary", "value")
            raise RuntimeError("rollback")

    async with sqlite_runtime.session_scope() as session:
        result = await session.execute(select(SystemMetadata).where(SystemMetadata.key == "temporary"))

    assert result.scalar_one_or_none() is None


def test_migration_metadata_exists() -> None:
    assert "system_metadata" in Base.metadata.tables
    assert "tokens" not in Base.metadata.tables
    assert "trades" not in Base.metadata.tables


def test_configured_unavailable_database_is_not_ready() -> None:
    test_settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+asyncpg://invalid:invalid@127.0.0.1:1/not_available",
    )
    unavailable_app = create_app(test_settings)

    with TestClient(unavailable_app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["database"] == "unavailable"


def test_internal_errors_return_safe_json_without_traceback() -> None:
    error_app = create_app(TEST_SETTINGS)

    @error_app.get("/test-error")
    def raise_error() -> None:
        raise RuntimeError("secret internal detail")

    with TestClient(error_app, raise_server_exceptions=False) as client:
        response = client.get("/test-error")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_server_error"
    assert body["error"]["message"] == "Internal server error"
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text
