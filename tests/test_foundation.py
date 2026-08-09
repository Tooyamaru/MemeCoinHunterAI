from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.config import Settings
from backend.core.database import get_database_config
from backend.core.logging import configure_logging


def test_application_imports() -> None:
    assert app.title == "Meme Coin Hunter AI"


def test_health_returns_process_status() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "meme-coin-hunter-ai"


def test_configuration_loads_safe_defaults() -> None:
    settings = Settings(_env_file=None, database_url=None)

    assert settings.app_env == "development"
    assert settings.app_port == 8000
    assert settings.database_url is None


def test_logging_and_database_boundaries_initialize() -> None:
    settings = Settings(_env_file=None, database_url=None)

    logger = configure_logging(settings)
    database = get_database_config(settings)

    assert logger.name == "meme_coin_hunter_ai"
    assert database.is_configured is False
