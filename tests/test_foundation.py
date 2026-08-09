from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.main import app, create_app
from backend.core.config import Settings
from backend.core.database import DatabaseState, get_database_config
from backend.core.logging import configure_logging
from backend.core.runtime import SERVICE_NAME


def test_application_imports() -> None:
    assert app.title == "Meme Coin Hunter AI"


def test_health_returns_process_status() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == SERVICE_NAME


def test_ready_reports_internal_runtime_readiness() -> None:
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"]["application"] == "ok"


def test_request_id_is_generated_and_preserved() -> None:
    with TestClient(app) as client:
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


def test_internal_errors_return_safe_json_without_traceback() -> None:
    test_app = create_app()

    @test_app.get("/test-error")
    def raise_error() -> None:
        raise RuntimeError("secret internal detail")

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get("/test-error")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_server_error"
    assert body["error"]["message"] == "Internal server error"
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text
