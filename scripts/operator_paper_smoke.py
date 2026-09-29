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
    confirm_run: bool = False
    confirm_persist: bool = False

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
        if self.confirm_persist and not self.confirm_run:
            raise OperatorSmokeError("--confirm-persist requires --confirm-run")


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

    prepare_status, prepare = request_json(
        "POST",
        f"{base}/api/v1/operator/paper-cases",
        config.token,
        config.prepare_payload,
        config.timeout_seconds,
    )
    result["prepare"] = {"status": prepare_status, "body": prepare}

    if prepare_status == 200 and prepare.get("state") == "PREPARATION_STOPPED":
        return result
    if prepare_status != 201:
        raise OperatorSmokeError(f"unexpected prepare status: {prepare_status}")

    handle = prepare.get("handle")
    case_digest = prepare.get("case_digest")
    if not isinstance(handle, str) or not handle:
        raise OperatorSmokeError("prepare response missing handle")
    if not isinstance(case_digest, str) or len(case_digest) != 64:
        raise OperatorSmokeError("prepare response missing canonical case digest")

    review_status, review = request_json(
        "GET",
        f"{base}/api/v1/operator/paper-cases/{handle}",
        config.token,
        None,
        config.timeout_seconds,
    )
    if review_status != 200:
        raise OperatorSmokeError(f"unexpected review status: {review_status}")
    if review.get("case_digest") != case_digest:
        raise OperatorSmokeError("review case digest mismatch")
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
    if readback.get("outcome") != "FOUND":
        raise OperatorSmokeError("readback did not confirm persisted lifecycle")
    if readback.get("lifecycle_result_digest") != lifecycle_digest:
        raise OperatorSmokeError("readback lifecycle digest mismatch")
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
            confirm_run=args.confirm_run,
            confirm_persist=args.confirm_persist,
        )
        output = run_smoke(config)
    except (OSError, json.JSONDecodeError, OperatorSmokeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    print(json.dumps({"ok": True, "result": output}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
