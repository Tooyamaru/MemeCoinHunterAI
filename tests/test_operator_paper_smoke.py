from scripts.operator_paper_smoke import (
    OperatorSmokeError,
    SmokeConfig,
    run_smoke,
)

import pytest


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64


def _config(*, run=False, persist=False):
    return SmokeConfig(
        base_url="https://operator.example",
        token="test-token",
        prepare_payload={"explicit": "payload"},
        timeout_seconds=5,
        confirm_run=run,
        confirm_persist=persist,
    )


def _ready():
    return 200, {
        "contract_version": "p01-oaf-01-operator-readiness-v1",
        "status": "READY",
        "checks": {
            "database": "ready",
            "case_registry": "enabled",
            "prepare_service": "configured",
            "run_service": "configured",
            "persist_service": "configured",
        },
        "process_local_registry": True,
        "provider_connectivity_checked": False,
        "simulation_only": True,
    }


def _valid():
    return 200, {
        "contract_version": "p01-oaf-01-prepare-validation-v1",
        "status": "VALID",
        "candidate_id": "candidate-1",
        "token_mint": "mint-1",
        "chain_id": "solana",
        "pool_address": "pool-1",
        "pfx_invocation_id": "pfx-1",
        "cip_invocation_id": "cip-1",
        "selected_observation_time": "2026-09-29T00:00:00+00:00",
        "provider_connectivity_checked": False,
        "mutates_case": False,
        "simulation_only": True,
    }


def test_default_smoke_checks_readiness_and_validation_then_stops_after_prepare_and_review():
    calls = []

    responses = [
        _ready(),
        _valid(),
        (
            201,
            {
                "handle": "opaque-handle",
                "case_digest": DIGEST_A,
                "state": "REVIEW_READY",
            },
        ),
        (
            200,
            {
                "handle": "opaque-handle",
                "case_digest": DIGEST_A,
                "state": "REVIEW_READY",
            },
        ),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    result = run_smoke(_config(), request_json=request)

    assert list(result) == ["readiness", "validation", "prepare", "review_after_prepare"]
    assert [call[0] for call in calls] == ["GET", "POST", "POST", "GET"]
    assert calls[0][1].endswith("/api/v1/operator/paper-cases/readiness")
    assert calls[1][1].endswith("/api/v1/operator/paper-cases/validate")
    assert calls[1][2] == {"explicit": "payload"}


def test_full_smoke_is_one_explicit_request_per_transition_with_no_retry():
    calls = []

    responses = [
        _ready(),
        _valid(),
        (
            201,
            {
                "handle": "opaque-handle",
                "case_digest": DIGEST_A,
                "state": "REVIEW_READY",
            },
        ),
        (
            200,
            {
                "handle": "opaque-handle",
                "case_digest": DIGEST_A,
                "state": "REVIEW_READY",
            },
        ),
        (
            200,
            {
                "handle": "opaque-handle",
                "case_digest": DIGEST_A,
                "state": "RUN_TERMINAL",
                "outcome": "RUN_TERMINAL",
                "persist_eligible": True,
            },
        ),
        (
            200,
            {
                "handle": "opaque-handle",
                "case_digest": DIGEST_A,
                "state": "RUN_TERMINAL",
                "oci_digest": DIGEST_B,
                "osc_digest": DIGEST_C,
                "lifecycle_result_digest": DIGEST_D,
            },
        ),
        (
            200,
            {
                "handle": "opaque-handle",
                "case_digest": DIGEST_A,
                "state": "PERSIST_TERMINAL",
                "readback_path": f"/api/v1/paper-lifecycle-results/{DIGEST_D}",
            },
        ),
        (
            200,
            {
                "outcome": "FOUND",
                "lifecycle_result_digest": DIGEST_D,
            },
        ),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    result = run_smoke(_config(run=True, persist=True), request_json=request)

    assert list(result) == [
        "readiness",
        "validation",
        "prepare",
        "review_after_prepare",
        "run",
        "review_after_run",
        "persist",
        "readback",
    ]
    assert [call[0] for call in calls] == ["GET", "POST", "POST", "GET", "POST", "GET", "POST", "GET"]
    assert calls[4][2] == {"case_digest": DIGEST_A, "confirm_run": True}
    assert calls[6][2] == {
        "case_digest": DIGEST_A,
        "oci_digest": DIGEST_B,
        "osc_digest": DIGEST_C,
        "lifecycle_result_digest": DIGEST_D,
        "confirm_persist": True,
    }


def test_readiness_failure_stops_before_prepare():
    calls = []

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return 503, {
            "status": "NOT_READY",
            "checks": {"prepare_service": "unavailable"},
        }

    with pytest.raises(OperatorSmokeError, match="readiness preflight"):
        run_smoke(_config(run=True, persist=True), request_json=request)

    assert len(calls) == 1
    assert calls[0][0] == "GET"


def test_validation_failure_stops_before_prepare():
    calls = []

    responses = [
        _ready(),
        (422, {"error": {"code": "operator_prepare_invalid"}}),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="validation preflight"):
        run_smoke(_config(run=True, persist=True), request_json=request)

    assert len(calls) == 2
    assert calls[0][0] == "GET"
    assert calls[1][0] == "POST"
    assert calls[1][1].endswith("/api/v1/operator/paper-cases/validate")


def test_persist_requires_explicit_run_confirmation():
    with pytest.raises(OperatorSmokeError, match="requires --confirm-run"):
        _config(persist=True)


def test_non_persistable_run_stops_without_persist_or_readback():
    calls = []

    responses = [
        _ready(),
        _valid(),
        (201, {"handle": "opaque", "case_digest": DIGEST_A, "state": "REVIEW_READY"}),
        (200, {"handle": "opaque", "case_digest": DIGEST_A, "state": "REVIEW_READY"}),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "state": "RUN_TERMINAL",
                "outcome": "RUN_TERMINAL",
                "persist_eligible": False,
            },
        ),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "state": "RUN_TERMINAL",
            },
        ),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    result = run_smoke(_config(run=True, persist=True), request_json=request)

    assert "persist_skipped" in result
    assert "persist" not in result
    assert "readback" not in result
    assert len(calls) == 6


def test_preparation_stop_does_not_review_or_run():
    calls = []

    responses = [
        _ready(),
        _valid(),
        (
            200,
            {
                "state": "PREPARATION_STOPPED",
                "reason_codes": ["ELIGIBILITY_REJECTED"],
                "simulation_only": True,
            },
        ),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    result = run_smoke(_config(run=True, persist=True), request_json=request)

    assert list(result) == ["readiness", "validation", "prepare"]
    assert len(calls) == 3


def test_non_local_plain_http_is_rejected_before_any_request():
    with pytest.raises(OperatorSmokeError, match="requires HTTPS"):
        SmokeConfig(
            base_url="http://operator.example",
            token="test-token",
            prepare_payload={"explicit": "payload"},
            timeout_seconds=5,
        )


def test_local_plain_http_remains_available_for_controlled_development():
    config = SmokeConfig(
        base_url="http://127.0.0.1:8000",
        token="test-token",
        prepare_payload={"explicit": "payload"},
        timeout_seconds=5,
    )
    assert config.base_url == "http://127.0.0.1:8000"
