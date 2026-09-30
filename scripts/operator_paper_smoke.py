"""Explicit, no-retry controlled-paper Operator Facade smoke harness.

This tool is intentionally operator-driven. It accepts one explicit prepare JSON
payload, performs at most one request per requested transition, and never polls
or retries. By default it performs readiness + no-I/O validation, then stops
after prepare+review. Run and persistence each require their own command-line
confirmation flag.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class OperatorSmokeError(RuntimeError):
    pass


JsonObject = Mapping[str, Any]
RequestJson = Callable[[str, str, str, JsonObject | None, float], tuple[int, dict[str, Any]]]


@dataclass(frozen=True)
class SmokeConfig:
    base_url: str
    token: str
    prepare_payload: dict[str, Any]
    timeout_seconds: float
    confirm_provider_prepare: bool = False
    confirm_run: bool = False
    confirm_persist: bool = False
    preflight_only: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.base_url, str):
            raise OperatorSmokeError("base_url must be HTTP(S)")
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise OperatorSmokeError("base_url must be HTTP(S)")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise OperatorSmokeError("non-local operator smoke requires HTTPS")
        if not isinstance(self.token, str) or not self.token:
            raise OperatorSmokeError("operator token is required")
        if not isinstance(self.prepare_payload, dict) or not self.prepare_payload:
            raise OperatorSmokeError("prepare payload must be a non-empty JSON object")
        if self.timeout_seconds <= 0:
            raise OperatorSmokeError("timeout must be positive")
        if self.preflight_only and (
            self.confirm_provider_prepare or self.confirm_run or self.confirm_persist
        ):
            raise OperatorSmokeError(
                "--preflight-only cannot be combined with provider/run/persist confirmation"
            )
        if self.confirm_persist and not self.confirm_run:
            raise OperatorSmokeError("--confirm-persist requires --confirm-run")
        if (self.confirm_run or self.confirm_persist) and not self.confirm_provider_prepare:
            raise OperatorSmokeError(
                "run/persist confirmation requires --confirm-provider-prepare"
            )


def _request_json(
    method: str,
    url: str,
    token: str,
    payload: JsonObject | None,
    timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
    body = None
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=headers, method=method)

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = build_opener(NoRedirect())
    try:
        with opener.open(req, timeout=timeout_seconds) as response:
            status = int(response.status)
            raw = response.read()
    except HTTPError as exc:
        raw = exc.read()
        detail = raw.decode("utf-8", errors="replace")[:4096]
        raise OperatorSmokeError(f"HTTP {exc.code}: {detail}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise OperatorSmokeError(f"transport unavailable: {type(exc).__name__}") from None

    try:
        decoded = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        raise OperatorSmokeError("response was not valid JSON") from None
    if not isinstance(decoded, dict):
        raise OperatorSmokeError("response JSON must be an object")
    return status, decoded


def run_smoke(
    config: SmokeConfig,
    *,
    request_json: RequestJson = _request_json,
) -> dict[str, Any]:
    """Run one bounded smoke sequence and return the collected safe projections."""

    config.__post_init__()
    base = config.base_url.rstrip("/")
    result: dict[str, Any] = {}

    readiness_status, readiness = request_json(
        "GET",
        f"{base}/api/v1/operator/paper-cases/readiness",
        config.token,
        None,
        config.timeout_seconds,
    )
    result["readiness"] = {"status": readiness_status, "body": readiness}
    if readiness_status != 200 or readiness.get("status") != "READY":
        raise OperatorSmokeError("operator readiness preflight did not pass")
    if readiness.get("contract_version") != "p01-oaf-01-operator-readiness-v1":
        raise OperatorSmokeError("operator readiness contract mismatch")
    if readiness.get("process_local_registry") is not True:
        raise OperatorSmokeError("operator readiness process-local registry mismatch")
    if readiness.get("provider_connectivity_checked") is not False:
        raise OperatorSmokeError("operator readiness unexpectedly checked provider connectivity")
    if readiness.get("simulation_only") is not True:
        raise OperatorSmokeError("operator readiness lost simulation-only boundary")

    validation_status, validation = request_json(
        "POST",
        f"{base}/api/v1/operator/paper-cases/validate",
        config.token,
        config.prepare_payload,
        config.timeout_seconds,
    )
    result["validation"] = {"status": validation_status, "body": validation}
    if validation_status != 200 or validation.get("status") != "VALID":
        raise OperatorSmokeError("operator prepare validation preflight did not pass")
    if validation.get("contract_version") != "p01-oaf-01-prepare-validation-v1":
        raise OperatorSmokeError("operator prepare validation contract mismatch")
    if validation.get("provider_connectivity_checked") is not False:
        raise OperatorSmokeError("operator validation unexpectedly checked provider connectivity")
    if validation.get("mutates_case") is not False:
        raise OperatorSmokeError("operator validation unexpectedly mutated case state")
    if validation.get("simulation_only") is not True:
        raise OperatorSmokeError("operator validation lost simulation-only boundary")

    target = config.prepare_payload.get("target")
    paper_intent = config.prepare_payload.get("paper_intent")
    if not isinstance(target, dict) or not isinstance(paper_intent, dict):
        raise OperatorSmokeError("prepare payload identity projection is unavailable")
    expected_identity = {
        "candidate_id": config.prepare_payload.get("candidate_id"),
        "token_mint": config.prepare_payload.get("token_mint"),
        "chain_id": target.get("chain_id"),
        "pool_address": target.get("pool_address"),
        "pfx_invocation_id": paper_intent.get("pfx_invocation_id"),
        "cip_invocation_id": paper_intent.get("cip_invocation_id"),
    }
    for name, expected in expected_identity.items():
        if not isinstance(expected, str) or not expected:
            raise OperatorSmokeError(f"prepare payload missing explicit {name}")
        if validation.get(name) != expected:
            raise OperatorSmokeError(f"operator validation {name} mismatch")

    if config.preflight_only:
        return result
    if not config.confirm_provider_prepare:
        raise OperatorSmokeError(
            "--confirm-provider-prepare is required before trusted prepare/provider access"
        )

    prepare_status, prepare = request_json(
        "POST",
        f"{base}/api/v1/operator/paper-cases",
        config.token,
        config.prepare_payload,
        config.timeout_seconds,
    )
    result["prepare"] = {"status": prepare_status, "body": prepare}

    if prepare_status == 200 and prepare.get("state") == "PREPARATION_STOPPED":
        if prepare.get("contract_version") != "p01-oaf-01-post-prepare-v1":
            raise OperatorSmokeError("preparation stop contract mismatch")
        if prepare.get("simulation_only") is not True:
            raise OperatorSmokeError("preparation stop lost simulation-only boundary")
        reason_codes = prepare.get("reason_codes")
        if (
            not isinstance(reason_codes, list)
            or not reason_codes
            or any(not isinstance(code, str) or not code for code in reason_codes)
        ):
            raise OperatorSmokeError("preparation stop reason codes are invalid")
        return result
    if prepare_status != 201:
        raise OperatorSmokeError(f"unexpected prepare status: {prepare_status}")
    if prepare.get("contract_version") != "p01-oaf-01-trusted-prepare-v1":
        raise OperatorSmokeError("operator prepare contract mismatch")
    if prepare.get("state") != "REVIEW_READY":
        raise OperatorSmokeError("operator prepare did not reach review-ready state")
    if prepare.get("simulation_only") is not True:
        raise OperatorSmokeError("operator prepare lost simulation-only boundary")
    for name in ("candidate_id", "token_mint", "chain_id", "pool_address"):
        if prepare.get(name) != expected_identity[name]:
            raise OperatorSmokeError(f"operator prepare {name} mismatch")

    handle = prepare.get("handle")
    case_digest = prepare.get("case_digest")
    if not isinstance(handle, str) or not handle:
        raise OperatorSmokeError("prepare response missing handle")
    if not isinstance(case_digest, str) or len(case_digest) != 64:
        raise OperatorSmokeError("prepare response missing canonical case digest")
    cip_digest = prepare.get("cip_digest")
    if not isinstance(cip_digest, str) or len(cip_digest) != 64:
        raise OperatorSmokeError("prepare response missing canonical cip digest")
    expected_review_path = f"/api/v1/operator/paper-cases/{handle}"
    if prepare.get("review_path") != expected_review_path:
        raise OperatorSmokeError("prepare review path mismatch")

    review_status, review = request_json(
        "GET",
        f"{base}/api/v1/operator/paper-cases/{handle}",
        config.token,
        None,
        config.timeout_seconds,
    )
    if review_status != 200:
        raise OperatorSmokeError(f"unexpected review status: {review_status}")
    if review.get("contract_version") != "p01-oaf-01-case-registry-v3":
        raise OperatorSmokeError("review contract mismatch")
    if review.get("handle") != handle:
        raise OperatorSmokeError("review handle mismatch")
    if review.get("case_digest") != case_digest:
        raise OperatorSmokeError("review case digest mismatch")
    if review.get("state") != "REVIEW_READY":
        raise OperatorSmokeError("review did not retain review-ready state")
    if review.get("simulation_only") is not True:
        raise OperatorSmokeError("review lost simulation-only boundary")
    if review.get("source_label") != "historical_price_proxy_and_explicit_simulation_assumptions":
        raise OperatorSmokeError("review source label mismatch")
    for name in ("candidate_id", "token_mint", "chain_id", "pool_address"):
        if review.get(name) != prepare.get(name):
            raise OperatorSmokeError(f"prepare/review {name} mismatch")
    if review.get("cip_digest") != cip_digest:
        raise OperatorSmokeError("prepare/review cip_digest mismatch")
    result["review_after_prepare"] = {"status": review_status, "body": review}

    if not config.confirm_run:
        return result

    run_status, run = request_json(
        "POST",
        f"{base}/api/v1/operator/paper-cases/{handle}/run",
        config.token,
        {"case_digest": case_digest, "confirm_run": True},
        config.timeout_seconds,
    )
    if run_status != 200:
        raise OperatorSmokeError(f"unexpected run status: {run_status}")
    if run.get("contract_version") != "p01-oaf-01-run-once-v1":
        raise OperatorSmokeError("run contract mismatch")
    if run.get("handle") != handle:
        raise OperatorSmokeError("run handle mismatch")
    if run.get("case_digest") != case_digest:
        raise OperatorSmokeError("run case digest mismatch")
    if run.get("state") != "RUN_TERMINAL" or run.get("outcome") != "RUN_TERMINAL":
        raise OperatorSmokeError("run did not reach terminal controlled-paper outcome")
    if run.get("simulation_only") is not True:
        raise OperatorSmokeError("run lost simulation-only boundary")
    result["run"] = {"status": run_status, "body": run}

    review2_status, review2 = request_json(
        "GET",
        f"{base}/api/v1/operator/paper-cases/{handle}",
        config.token,
        None,
        config.timeout_seconds,
    )
    if review2_status != 200:
        raise OperatorSmokeError(f"unexpected post-run review status: {review2_status}")
    if review2.get("contract_version") != "p01-oaf-01-case-registry-v3":
        raise OperatorSmokeError("post-run review contract mismatch")
    if review2.get("handle") != handle:
        raise OperatorSmokeError("post-run review handle mismatch")
    if review2.get("case_digest") != case_digest:
        raise OperatorSmokeError("post-run review case digest mismatch")
    if review2.get("state") != "RUN_TERMINAL":
        raise OperatorSmokeError("post-run review did not retain terminal run state")
    if review2.get("simulation_only") is not True:
        raise OperatorSmokeError("post-run review lost simulation-only boundary")
    if review2.get("source_label") != "historical_price_proxy_and_explicit_simulation_assumptions":
        raise OperatorSmokeError("post-run review source label mismatch")
    result["review_after_run"] = {"status": review2_status, "body": review2}

    if not config.confirm_persist:
        return result

    if run.get("persist_eligible") is not True:
        result["persist_skipped"] = {
            "reason": "run result is not persist eligible",
            "state": run.get("state"),
            "outcome": run.get("outcome"),
        }
        return result

    oci_digest = review2.get("oci_digest")
    osc_digest = review2.get("osc_digest")
    lifecycle_digest = review2.get("lifecycle_result_digest")
    for value, name in (
        (oci_digest, "oci_digest"),
        (osc_digest, "osc_digest"),
        (lifecycle_digest, "lifecycle_result_digest"),
    ):
        if not isinstance(value, str) or len(value) != 64:
            raise OperatorSmokeError(f"post-run review missing canonical {name}")
        if run.get(name) != value:
            raise OperatorSmokeError(f"run/post-run review {name} mismatch")

    persist_status, persist = request_json(
        "POST",
        f"{base}/api/v1/operator/paper-cases/{handle}/persist",
        config.token,
        {
            "case_digest": case_digest,
            "oci_digest": oci_digest,
            "osc_digest": osc_digest,
            "lifecycle_result_digest": lifecycle_digest,
            "confirm_persist": True,
        },
        config.timeout_seconds,
    )
    if persist_status != 200:
        raise OperatorSmokeError(f"unexpected persist status: {persist_status}")
    if persist.get("contract_version") != "p01-oaf-01-persist-once-v1":
        raise OperatorSmokeError("persist contract mismatch")
    if persist.get("handle") != handle:
        raise OperatorSmokeError("persist handle mismatch")
    if persist.get("case_digest") != case_digest:
        raise OperatorSmokeError("persist case digest mismatch")
    if persist.get("state") != "PERSIST_TERMINAL" or persist.get("outcome") != "PERSIST_TERMINAL":
        raise OperatorSmokeError("persist did not reach terminal state")
    if persist.get("simulation_only") is not True:
        raise OperatorSmokeError("persist lost simulation-only boundary")
    persistence_digest = persist.get("persistence_digest")
    if not isinstance(persistence_digest, str) or len(persistence_digest) != 64:
        raise OperatorSmokeError("persist response missing canonical persistence digest")
    artifact_count = persist.get("artifact_count")
    if isinstance(artifact_count, bool) or not isinstance(artifact_count, int) or artifact_count < 0:
        raise OperatorSmokeError("persist response has invalid artifact count")
    result["persist"] = {"status": persist_status, "body": persist}

    persistence_outcome = persist.get("persistence_outcome")
    if persistence_outcome not in {"STORED", "ALREADY_STORED"}:
        raise OperatorSmokeError("persistence did not confirm durable storage")
    if persist.get("lifecycle_result_digest") != lifecycle_digest:
        raise OperatorSmokeError("persist lifecycle digest mismatch")

    readback_path = persist.get("readback_path")
    expected_readback_path = f"/api/v1/paper-lifecycle-results/{lifecycle_digest}"
    if readback_path != expected_readback_path:
        raise OperatorSmokeError("persist response readback path mismatch")

    read_status, readback = request_json(
        "GET",
        f"{base}{readback_path}",
        config.token,
        None,
        config.timeout_seconds,
    )
    if read_status != 200:
        raise OperatorSmokeError(f"unexpected readback status: {read_status}")
    if readback.get("contract_version") != "p01-rti-03-v1":
        raise OperatorSmokeError("readback contract mismatch")
    if readback.get("outcome") != "FOUND":
        raise OperatorSmokeError("readback did not confirm persisted lifecycle")
    if readback.get("lifecycle_result_digest") != lifecycle_digest:
        raise OperatorSmokeError("readback lifecycle digest mismatch")
    result_digest = readback.get("result_digest")
    if not isinstance(result_digest, str) or len(result_digest) != 64:
        raise OperatorSmokeError("readback response missing canonical result digest")
    read_run = readback.get("run")
    artifacts = readback.get("artifacts")
    if not isinstance(read_run, dict) or read_run.get("lifecycle_result_digest") != lifecycle_digest:
        raise OperatorSmokeError("readback run lifecycle identity mismatch")
    if not isinstance(artifacts, list):
        raise OperatorSmokeError("readback artifacts projection is invalid")
    read_artifact_count = read_run.get("artifact_count")
    if (
        isinstance(read_artifact_count, bool)
        or not isinstance(read_artifact_count, int)
        or read_artifact_count != len(artifacts)
        or read_artifact_count != artifact_count
    ):
        raise OperatorSmokeError("readback artifact count mismatch")
    result["readback"] = {"status": read_status, "body": readback}
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one explicit controlled-paper Operator Facade smoke sequence."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--prepare-payload", required=True, type=Path)
    parser.add_argument("--token-env", default="OPERATOR_BEARER_TOKEN")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help=(
            "Stop after readiness + no-I/O payload validation without calling "
            "the trusted prepare/provider path."
        ),
    )
    parser.add_argument(
        "--confirm-provider-prepare",
        action="store_true",
        help=(
            "Explicitly authorize the one bounded trusted prepare/provider call "
            "after readiness + no-I/O validation."
        ),
    )
    parser.add_argument(
        "--confirm-run",
        action="store_true",
        help="Explicitly authorize the one-shot controlled-paper run transition.",
    )
    parser.add_argument(
        "--confirm-persist",
        action="store_true",
        help="Explicitly authorize one RTI-03 persistence transition after an eligible run.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    token = os.environ.get(args.token_env, "")
    try:
        payload = json.loads(args.prepare_payload.read_text(encoding="utf-8"))
        config = SmokeConfig(
            base_url=args.base_url,
            token=token,
            prepare_payload=payload,
            timeout_seconds=args.timeout_seconds,
            confirm_provider_prepare=args.confirm_provider_prepare,
            confirm_run=args.confirm_run,
            confirm_persist=args.confirm_persist,
            preflight_only=args.preflight_only,
        )
        output = run_smoke(config)
    except (OSError, json.JSONDecodeError, OperatorSmokeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    print(json.dumps({"ok": True, "result": output}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
