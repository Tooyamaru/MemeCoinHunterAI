"""Portable one-process launcher for the controlled-paper smoke environment.

This helper validates only local configuration and then launches exactly one
Uvicorn worker. It performs no provider connectivity probe and does not execute
an operator smoke by itself.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from typing import Callable, Mapping

import uvicorn

from backend.core.config import Settings


class SingleProcessRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class SingleProcessRuntimeReadiness:
    status: str
    app_env: str
    workers: int
    reload: bool
    database_configured: bool
    operator_bearer_configured: bool
    process_local_ack_required: bool
    process_local_acknowledged: bool
    solana_rpc_configured: bool
    coingecko_demo_key_configured: bool
    provider_connectivity_checked: bool = False
    simulation_only: bool = True


def validate_single_process_runtime(
    *,
    settings: Settings,
    environment: Mapping[str, str],
    expected_environment: str,
) -> SingleProcessRuntimeReadiness:
    """Validate configuration required before a one-process smoke host starts."""

    if not isinstance(settings, Settings):
        raise SingleProcessRuntimeError("settings are required")
    if not isinstance(environment, Mapping):
        raise SingleProcessRuntimeError("environment mapping is required")
    if expected_environment not in {"development", "test", "staging", "production"}:
        raise SingleProcessRuntimeError("expected_environment is invalid")
    if settings.app_env != expected_environment:
        raise SingleProcessRuntimeError(
            "single-process runtime environment mismatch: "
            f"expected {expected_environment}, got {settings.app_env}"
        )

    database_configured = bool(settings.database_url)
    operator_bearer_configured = bool(settings.operator_bearer_token)
    solana_rpc_configured = bool(settings.solana_rpc_url)
    coingecko_demo_key_configured = bool(environment.get("COINGECKO_DEMO_API_KEY"))
    ack_required = settings.app_env in {"staging", "production"}
    ack = bool(settings.operator_process_local_registry_ack)

    missing: list[str] = []
    if not database_configured:
        missing.append("DATABASE_URL")
    if not operator_bearer_configured:
        missing.append("OPERATOR_BEARER_TOKEN")
    if not solana_rpc_configured:
        missing.append("SOLANA_RPC_URL")
    if not coingecko_demo_key_configured:
        missing.append("COINGECKO_DEMO_API_KEY")
    if ack_required and not ack:
        missing.append("OPERATOR_PROCESS_LOCAL_REGISTRY_ACK=true")

    if missing:
        raise SingleProcessRuntimeError(
            "single-process smoke runtime configuration incomplete: "
            + ", ".join(missing)
        )

    return SingleProcessRuntimeReadiness(
        status="READY_FOR_SINGLE_PROCESS_LAUNCH",
        app_env=settings.app_env,
        workers=1,
        reload=False,
        database_configured=database_configured,
        operator_bearer_configured=operator_bearer_configured,
        process_local_ack_required=ack_required,
        process_local_acknowledged=ack,
        solana_rpc_configured=solana_rpc_configured,
        coingecko_demo_key_configured=coingecko_demo_key_configured,
    )


ServerRunner = Callable[..., None]


def launch_single_process_server(
    *,
    readiness: SingleProcessRuntimeReadiness,
    host: str,
    port: int,
    runner: ServerRunner = uvicorn.run,
) -> None:
    """Launch the existing FastAPI app with exactly one worker and no reload."""

    if readiness.status != "READY_FOR_SINGLE_PROCESS_LAUNCH":
        raise SingleProcessRuntimeError("runtime readiness did not pass")
    if readiness.workers != 1 or readiness.reload:
        raise SingleProcessRuntimeError("single-process invariant violated")
    if not isinstance(host, str) or not host:
        raise SingleProcessRuntimeError("host is required")
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise SingleProcessRuntimeError("port is invalid")

    runner(
        "backend.api.main:app",
        host=host,
        port=port,
        workers=1,
        reload=False,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and launch one stable application process for the "
            "controlled-paper provider-backed smoke gate."
        )
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--expected-environment",
        required=True,
        choices=("development", "test", "staging", "production"),
        help="Require APP_ENV to match before readiness passes or Uvicorn starts.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate local runtime configuration without starting Uvicorn.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        readiness = validate_single_process_runtime(
            settings=Settings(),
            environment=os.environ,
            expected_environment=args.expected_environment,
        )
        print(json.dumps(asdict(readiness), sort_keys=True))
        if args.check_only:
            return 0
        launch_single_process_server(
            readiness=readiness,
            host=args.host,
            port=args.port,
        )
        return 0
    except SingleProcessRuntimeError as exc:
        print(json.dumps({"status": "NOT_READY", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
