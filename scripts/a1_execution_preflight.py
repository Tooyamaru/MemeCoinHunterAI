"""Local manifest-only A1 preparation check. No launch or provider-call path.

Configuration booleans are operator declarations, not runtime evidence. This
script intentionally does not load Settings, environment variables or secrets.
It cannot verify a connected database or confer execution authorization.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path

from core.data.a1_source_verification import MAINNET_GENESIS_HASH, PROGRAM

_BOOL_FIELDS = (
    "database_configured", "operator_configured", "solana_provider_configured",
    "coingecko_provider_configured", "process_local_acknowledged",
    "simulation_only", "offline_preparation_authorized",
)
_FIELDS = {"environment", "expected_environment", "workers", "reload", *_BOOL_FIELDS}
_ENVIRONMENTS = {"development", "test", "staging", "production"}


class A1PreflightError(ValueError):
    pass


@dataclass(frozen=True)
class A1ExecutionPreparation:
    status: str
    environment: str
    expected_genesis_hash: str = MAINNET_GENESIS_HASH
    expected_program: str = PROGRAM
    simulation_only: bool = True
    provider_execution_authorized: bool = False
    provider_contacted: bool = False
    database_connection: str = "PENDING"
    qualifying_runtime: str = "PENDING"
    cluster_verification: str = "PENDING"
    program_verification: str = "PENDING"
    collection_budget: str = "PENDING"
    reference_lifecycle: str = "PENDING"
    persistence_readback: str = "PENDING"
    operational_gate: str = "SEPARATE_CONTROLLER_AUTHORIZATION_REQUIRED"


def check_preparation(manifest):
    """Check exact declarative configuration; zero external or environment I/O."""
    if type(manifest) is not dict or set(manifest) != _FIELDS:
        raise A1PreflightError("EXACT_SAFE_MANIFEST_REQUIRED")
    if any(type(manifest[name]) is not bool for name in (*_BOOL_FIELDS, "reload")):
        raise A1PreflightError("BOOLEAN_CONFIGURATION_REQUIRED")
    environment = manifest["environment"]
    expected = manifest["expected_environment"]
    if type(environment) is not str or type(expected) is not str or environment not in _ENVIRONMENTS or expected not in _ENVIRONMENTS or environment != expected:
        raise A1PreflightError("ENVIRONMENT_IDENTITY_MISMATCH")
    if type(manifest["workers"]) is not int or manifest["workers"] != 1 or manifest["reload"]:
        raise A1PreflightError("SINGLE_PROCESS_CONFIGURATION_REQUIRED")
    if not manifest["simulation_only"] or not manifest["offline_preparation_authorized"]:
        raise A1PreflightError("OFFLINE_PAPER_PREPARATION_AUTHORITY_REQUIRED")
    if environment in {"staging", "production"} and not manifest["process_local_acknowledged"]:
        raise A1PreflightError("PROCESS_LOCAL_ACK_REQUIRED")
    if not all(manifest[name] for name in ("database_configured", "operator_configured", "solana_provider_configured", "coingecko_provider_configured")):
        raise A1PreflightError("CONFIGURATION_INCOMPLETE")
    return A1ExecutionPreparation("OFFLINE_CONFIGURATION_CHECKED", environment)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise A1PreflightError("DUPLICATE_MANIFEST_KEY")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", required=True)
    parser.add_argument("--manifest", type=Path, required=True,
                        help="Safe exact boolean configuration manifest; never credentials.")
    args = parser.parse_args(argv)
    try:
        with args.manifest.open("rb") as handle:
            raw = handle.read(32769)
        if not 0 < len(raw) <= 32768:
            raise A1PreflightError("MANIFEST_BYTE_CAP")
        def bad_number(_):
            raise A1PreflightError("INVALID_MANIFEST_NUMBER")
        manifest = json.loads(raw, object_pairs_hook=_pairs, parse_constant=bad_number)
        print(json.dumps(asdict(check_preparation(manifest)), sort_keys=True))
        return 0
    except (A1PreflightError, OSError, ValueError, TypeError, RecursionError):
        # No input, filenames, credentials or exception bodies enter output.
        print(json.dumps({"status": "NOT_READY", "reason": "INVALID_OR_INCOMPLETE_SAFE_MANIFEST",
                          "provider_contacted": False, "provider_execution_authorized": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
