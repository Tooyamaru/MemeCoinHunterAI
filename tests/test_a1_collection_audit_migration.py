"""Actual Alembic upgrades/downgrade against an isolated temporary database."""
import asyncio
from io import StringIO
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
import pytest

from backend.application.paper_lifecycle_persistence import ControlledPaperPersistenceService
from backend.core.config import Settings, get_settings
from backend.core.database import DatabaseRuntime
from backend.core.models import A1CollectionAudit
from tests.test_controlled_paper_persistence import _complete_lifecycle


def test_additive_upgrade_and_downgrade_preserve_existing_lifecycle(tmp_path, monkeypatch):
    path = tmp_path / "audit-migration.db"
    url = f"sqlite+aiosqlite:///{path}"
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        command.upgrade(config, "0002_paper_lifecycle")

        async def seed():
            runtime = DatabaseRuntime(Settings(_env_file=None, app_env="test", database_url=url))
            await runtime.start()
            try:
                result = await ControlledPaperPersistenceService(runtime).persist(_complete_lifecycle())
                assert result.outcome.value == "STORED"
            finally:
                await runtime.dispose()
        asyncio.run(seed())

        def legacy_snapshot():
            with sqlite3.connect(path) as connection:
                schema = connection.execute(
                    "SELECT type, name, sql FROM sqlite_master WHERE name LIKE 'paper_%' ORDER BY name"
                ).fetchall()
                runs = connection.execute("SELECT * FROM paper_lifecycle_runs").fetchall()
                artifacts = connection.execute("SELECT * FROM paper_lifecycle_artifacts ORDER BY ordinal").fetchall()
                return schema, runs, artifacts
        original = legacy_snapshot()
        assert len(original[1]) == 1 and len(original[2]) == 13
        command.upgrade(config, "head")
        assert legacy_snapshot() == original
        with sqlite3.connect(path) as connection:
            columns = connection.execute("PRAGMA table_info(a1_collection_audits)").fetchall()
            assert {column[1] for column in columns} == set(A1CollectionAudit.__table__.columns.keys())
            foreign_key = connection.execute("PRAGMA foreign_key_list(a1_collection_audits)").fetchone()
            assert foreign_key[2:5] == ("paper_lifecycle_runs", "run_id", "id")
            assert foreign_key[6] == "RESTRICT"
            uniques = {tuple(row[2] for row in connection.execute(f"PRAGMA index_info('{index[1]}')"))
                       for index in connection.execute("PRAGMA index_list(a1_collection_audits)") if index[2]}
            assert uniques == {("run_id",), ("lifecycle_result_digest",), ("audit_digest",)}
            connection.execute("PRAGMA foreign_keys=ON")
            names = ("run_id", "contract_version", "lifecycle_result_digest", "collection_id", "packet_digest",
                     "collection_digest", "selected_rti11_digest", "payload_digest", "audit_digest", "canonical_payload")
            values = (999, "test", "a" * 64, "test", "b" * 64, "c" * 64, "d" * 64, "e" * 64, "f" * 64, "{}")
            with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
                connection.execute(f"INSERT INTO a1_collection_audits ({','.join(names)}) VALUES ({','.join('?' for _ in names)})", values)
        command.downgrade(config, "0002_paper_lifecycle")
        assert legacy_snapshot() == original
        with sqlite3.connect(path) as connection:
            assert connection.execute("SELECT name FROM sqlite_master WHERE name='a1_collection_audits'").fetchone() is None
        command.upgrade(config, "head")
        assert legacy_snapshot() == original
    finally:
        get_settings.cache_clear()


def test_migration_compiles_for_PostgreSQL_without_opening_connection(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    output = StringIO()
    config = Config(str(root / "alembic.ini"), output_buffer=output)
    config.set_main_option("script_location", str(root / "migrations"))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://127.0.0.1/audit_compile_only")
    get_settings.cache_clear()
    try:
        command.upgrade(config, "0002_paper_lifecycle:head", sql=True)
        sql = output.getvalue()
        assert "CREATE TABLE a1_collection_audits" in sql
        assert "REFERENCES paper_lifecycle_runs (id) ON DELETE RESTRICT" in sql
        assert "CREATE TABLE paper_lifecycle_runs" not in sql
        assert "CREATE TABLE paper_lifecycle_artifacts" not in sql
        assert "DROP TABLE" not in sql and "ALTER TABLE" not in sql
    finally:
        get_settings.cache_clear()
