import json
from dataclasses import asdict

import pytest

from backend.core.config import Settings
from scripts.operator_single_process_runtime import (
    SingleProcessRuntimeError,
    launch_single_process_server,
    validate_single_process_runtime,
)


def _settings(**overrides):
    values = {
        "app_env": "development",
        "database_url": "postgresql://user:secret@db.example/mch",
        "operator_bearer_token": "operator-secret",
        "operator_process_local_registry_ack": False,
        "solana_rpc_url": "https://rpc.example/credential",
    }
    values.update(overrides)
    return Settings(**values)


def _environment():
    return {"COINGECKO_DEMO_API_KEY": "coingecko-secret"}


def test_single_process_runtime_readiness_is_safe_and_bounded():
    readiness = validate_single_process_runtime(
        settings=_settings(),
        environment=_environment(),
        expected_environment="development",
    )

    assert readiness.status == "READY_FOR_SINGLE_PROCESS_LAUNCH"
    assert readiness.workers == 1
    assert readiness.reload is False
    assert readiness.provider_connectivity_checked is False
    assert readiness.simulation_only is True
    assert readiness.process_local_ack_required is False

    projection = json.dumps(asdict(readiness), sort_keys=True)
    assert "operator-secret" not in projection
    assert "coingecko-secret" not in projection
    assert "credential" not in projection


@pytest.mark.parametrize(
    ("overrides", "environment", "missing"),
    [
        ({"database_url": None}, _environment(), "DATABASE_URL"),
        ({"operator_bearer_token": None}, _environment(), "OPERATOR_BEARER_TOKEN"),
        ({"solana_rpc_url": None}, _environment(), "SOLANA_RPC_URL"),
        ({}, {}, "COINGECKO_DEMO_API_KEY"),
    ],
)
def test_single_process_runtime_rejects_missing_required_configuration(
    overrides,
    environment,
    missing,
):
    with pytest.raises(SingleProcessRuntimeError, match=missing):
        validate_single_process_runtime(
            settings=_settings(**overrides),
            environment=environment,
            expected_environment="development",
        )


def test_single_process_runtime_rejects_unknown_expected_environment():
    with pytest.raises(SingleProcessRuntimeError, match="expected_environment is invalid"):
        validate_single_process_runtime(
            settings=_settings(),
            environment=_environment(),
            expected_environment="unknown",
        )


def test_single_process_runtime_rejects_environment_mismatch_before_launch_readiness():
    with pytest.raises(SingleProcessRuntimeError, match="runtime environment mismatch"):
        validate_single_process_runtime(
            settings=_settings(app_env="production", operator_process_local_registry_ack=True),
            environment=_environment(),
            expected_environment="staging",
        )


def test_staging_requires_explicit_process_local_acknowledgement():
    with pytest.raises(
        SingleProcessRuntimeError,
        match="OPERATOR_PROCESS_LOCAL_REGISTRY_ACK=true",
    ):
        validate_single_process_runtime(
            settings=_settings(app_env="staging"),
            environment=_environment(),
        )

    readiness = validate_single_process_runtime(
        settings=_settings(
            app_env="staging",
            operator_process_local_registry_ack=True,
        ),
        environment=_environment(),
        expected_environment="staging",
    )
    assert readiness.process_local_ack_required is True
    assert readiness.process_local_acknowledged is True


def test_launcher_hardcodes_one_worker_and_disables_reload():
    readiness = validate_single_process_runtime(
        settings=_settings(),
        environment=_environment(),
        expected_environment="development",
    )
    calls = []

    def runner(app, **kwargs):
        calls.append((app, kwargs))

    launch_single_process_server(
        readiness=readiness,
        host="127.0.0.1",
        port=8000,
        runner=runner,
    )

    assert calls == [
        (
            "backend.api.main:app",
            {
                "host": "127.0.0.1",
                "port": 8000,
                "workers": 1,
                "reload": False,
            },
        )
    ]
