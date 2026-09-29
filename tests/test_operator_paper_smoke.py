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
DIGEST_E = "e" * 64


def _prepare_payload():
    return {
        "candidate_id": "candidate-1",
        "token_mint": "mint-1",
        "target": {
            "chain_id": "solana",
            "pool_address": "pool-1",
        },
        "paper_intent": {
            "pfx_invocation_id": "pfx-1",
            "cip_invocation_id": "cip-1",
        },
    }


def _config(*, run=False, persist=False, preflight=False):
    return SmokeConfig(
        base_url="https://operator.example",
        token="test-token",
        prepare_payload=_prepare_payload(),
        timeout_seconds=5,
        confirm_run=run,
        confirm_persist=persist,
        preflight_only=preflight,
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


def _prepared(handle="opaque", case_digest=DIGEST_A):
    return 201, {
        "contract_version": "p01-oaf-01-trusted-prepare-v1",
        "handle": handle,
        "case_digest": case_digest,
        "state": "REVIEW_READY",
        "candidate_id": "candidate-1",
        "chain_id": "solana",
        "token_mint": "mint-1",
        "pool_address": "pool-1",
        "cip_digest": DIGEST_E,
        "review_path": f"/api/v1/operator/paper-cases/{handle}",
        "simulation_only": True,
    }


def _review_ready(handle="opaque", case_digest=DIGEST_A):
    return 200, {
        "contract_version": "p01-oaf-01-case-registry-v3",
        "handle": handle,
        "case_digest": case_digest,
        "state": "REVIEW_READY",
        "candidate_id": "candidate-1",
        "chain_id": "solana",
        "token_mint": "mint-1",
        "pool_address": "pool-1",
        "cip_digest": DIGEST_E,
        "simulation_only": True,
        "source_label": "historical_price_proxy_and_explicit_simulation_assumptions",
    }


def test_preflight_only_stops_after_readiness_and_validation_without_prepare():
    calls = []
    responses = [_ready(), _valid()]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    result = run_smoke(_config(preflight=True), request_json=request)

    assert list(result) == ["readiness", "validation"]
    assert [call[0] for call in calls] == ["GET", "POST"]
    assert calls[0][1].endswith("/api/v1/operator/paper-cases/readiness")
    assert calls[1][1].endswith("/api/v1/operator/paper-cases/validate")
    assert len(calls) == 2


def test_preflight_only_rejects_run_or_persist_confirmation():
    with pytest.raises(OperatorSmokeError, match="preflight-only"):
        _config(run=True, preflight=True)

    with pytest.raises(OperatorSmokeError, match="preflight-only"):
        _config(run=True, persist=True, preflight=True)


def test_readiness_contract_mismatch_stops_before_validation():
    calls = []

    bad_ready = _ready()
    bad_ready[1]["provider_connectivity_checked"] = True

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return bad_ready

    with pytest.raises(OperatorSmokeError, match="unexpectedly checked provider connectivity"):
        run_smoke(_config(preflight=True), request_json=request)

    assert len(calls) == 1


def test_validation_identity_mismatch_stops_before_prepare():
    calls = []
    bad_valid = _valid()
    bad_valid[1]["candidate_id"] = "different-candidate"
    responses = [_ready(), bad_valid]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="validation candidate_id mismatch"):
        run_smoke(_config(), request_json=request)

    assert len(calls) == 2


def test_validation_mutation_claim_stops_before_prepare():
    calls = []
    bad_valid = _valid()
    bad_valid[1]["mutates_case"] = True
    responses = [_ready(), bad_valid]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="unexpectedly mutated case state"):
        run_smoke(_config(), request_json=request)

    assert len(calls) == 2


def test_prepare_identity_mismatch_stops_before_review():
    calls = []
    prepared = _prepared()
    prepared[1]["candidate_id"] = "different-candidate"
    responses = [_ready(), _valid(), prepared]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="prepare candidate_id mismatch"):
        run_smoke(_config(), request_json=request)

    assert len(calls) == 3


def test_prepare_review_path_mismatch_stops_before_review():
    calls = []
    prepared = _prepared()
    prepared[1]["review_path"] = "/api/v1/operator/paper-cases/different"
    responses = [_ready(), _valid(), prepared]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="prepare review path mismatch"):
        run_smoke(_config(), request_json=request)

    assert len(calls) == 3


def test_review_identity_mismatch_stops_before_run():
    calls = []
    reviewed = _review_ready()
    reviewed[1]["pool_address"] = "different-pool"
    responses = [_ready(), _valid(), _prepared(), reviewed]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="prepare/review pool_address mismatch"):
        run_smoke(_config(run=True), request_json=request)

    assert len(calls) == 4


def test_default_smoke_checks_readiness_and_validation_then_stops_after_prepare_and_review():
    calls = []

    responses = [
        _ready(),
        _valid(),
        _prepared("opaque-handle"),
        _review_ready("opaque-handle"),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    result = run_smoke(_config(), request_json=request)

    assert list(result) == ["readiness", "validation", "prepare", "review_after_prepare"]
    assert [call[0] for call in calls] == ["GET", "POST", "POST", "GET"]
    assert calls[0][1].endswith("/api/v1/operator/paper-cases/readiness")
    assert calls[1][1].endswith("/api/v1/operator/paper-cases/validate")
    assert calls[1][2] == _prepare_payload()


def test_full_smoke_is_one_explicit_request_per_transition_with_no_retry():
    calls = []

    responses = [
        _ready(),
        _valid(),
        _prepared("opaque-handle"),
        _review_ready("opaque-handle"),
        (
            200,
            {
                "handle": "opaque-handle",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-run-once-v1",
                "state": "RUN_TERMINAL",
                "outcome": "RUN_TERMINAL",
                "simulation_only": True,
                "oci_digest": DIGEST_B,
                "osc_digest": DIGEST_C,
                "lifecycle_result_digest": DIGEST_D,
                "persist_eligible": True,
            },
        ),
        (
            200,
            {
                "handle": "opaque-handle",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-case-registry-v3",
                "state": "RUN_TERMINAL",
                "simulation_only": True,
                "source_label": "historical_price_proxy_and_explicit_simulation_assumptions",
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
                "contract_version": "p01-oaf-01-persist-once-v1",
                "state": "PERSIST_TERMINAL",
                "outcome": "PERSIST_TERMINAL",
                "simulation_only": True,
                "persistence_digest": DIGEST_E,
                "artifact_count": 0,
                "persistence_outcome": "STORED",
                "lifecycle_result_digest": DIGEST_D,
                "readback_path": f"/api/v1/paper-lifecycle-results/{DIGEST_D}",
            },
        ),
        (
            200,
            {
                "contract_version": "p01-rti-03-v1",
                "outcome": "FOUND",
                "lifecycle_result_digest": DIGEST_D,
                "result_digest": DIGEST_E,
                "run": {
                    "lifecycle_result_digest": DIGEST_D,
                    "artifact_count": 0,
                },
                "artifacts": [],
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


def test_non_durable_persist_outcome_stops_before_readback():
    calls = []

    responses = [
        _ready(),
        _valid(),
        _prepared(),
        _review_ready(),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-run-once-v1",
                "state": "RUN_TERMINAL",
                "outcome": "RUN_TERMINAL",
                "simulation_only": True,
                "oci_digest": DIGEST_B,
                "osc_digest": DIGEST_C,
                "lifecycle_result_digest": DIGEST_D,
                "persist_eligible": True,
            },
        ),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-case-registry-v3",
                "state": "RUN_TERMINAL",
                "simulation_only": True,
                "source_label": "historical_price_proxy_and_explicit_simulation_assumptions",
                "oci_digest": DIGEST_B,
                "osc_digest": DIGEST_C,
                "lifecycle_result_digest": DIGEST_D,
            },
        ),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-persist-once-v1",
                "state": "PERSIST_TERMINAL",
                "outcome": "PERSIST_TERMINAL",
                "simulation_only": True,
                "persistence_digest": DIGEST_E,
                "artifact_count": 0,
                "persistence_outcome": "STORAGE_UNAVAILABLE",
                "lifecycle_result_digest": DIGEST_D,
                "readback_path": f"/api/v1/paper-lifecycle-results/{DIGEST_D}",
            },
        ),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="durable storage"):
        run_smoke(_config(run=True, persist=True), request_json=request)

    assert len(calls) == 7
    assert all(not call[1].endswith(DIGEST_D) or call[0] != "GET" for call in calls)


def test_persist_digest_mismatch_stops_before_readback():
    calls = []

    responses = [
        _ready(),
        _valid(),
        _prepared(),
        _review_ready(),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-run-once-v1",
                "state": "RUN_TERMINAL",
                "outcome": "RUN_TERMINAL",
                "simulation_only": True,
                "oci_digest": DIGEST_B,
                "osc_digest": DIGEST_C,
                "lifecycle_result_digest": DIGEST_D,
                "persist_eligible": True,
            },
        ),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-case-registry-v3",
                "state": "RUN_TERMINAL",
                "simulation_only": True,
                "source_label": "historical_price_proxy_and_explicit_simulation_assumptions",
                "oci_digest": DIGEST_B,
                "osc_digest": DIGEST_C,
                "lifecycle_result_digest": DIGEST_D,
            },
        ),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-persist-once-v1",
                "state": "PERSIST_TERMINAL",
                "outcome": "PERSIST_TERMINAL",
                "simulation_only": True,
                "persistence_digest": DIGEST_E,
                "artifact_count": 0,
                "persistence_outcome": "STORED",
                "lifecycle_result_digest": DIGEST_C,
                "readback_path": f"/api/v1/paper-lifecycle-results/{DIGEST_C}",
            },
        ),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="persist lifecycle digest mismatch"):
        run_smoke(_config(run=True, persist=True), request_json=request)

    assert len(calls) == 7


def test_readback_digest_mismatch_is_rejected():
    calls = []

    responses = [
        _ready(),
        _valid(),
        _prepared(),
        _review_ready(),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-run-once-v1",
                "state": "RUN_TERMINAL",
                "outcome": "RUN_TERMINAL",
                "simulation_only": True,
                "oci_digest": DIGEST_B,
                "osc_digest": DIGEST_C,
                "lifecycle_result_digest": DIGEST_D,
                "persist_eligible": True,
            },
        ),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-case-registry-v3",
                "state": "RUN_TERMINAL",
                "simulation_only": True,
                "source_label": "historical_price_proxy_and_explicit_simulation_assumptions",
                "oci_digest": DIGEST_B,
                "osc_digest": DIGEST_C,
                "lifecycle_result_digest": DIGEST_D,
            },
        ),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-persist-once-v1",
                "state": "PERSIST_TERMINAL",
                "outcome": "PERSIST_TERMINAL",
                "simulation_only": True,
                "persistence_digest": DIGEST_E,
                "artifact_count": 0,
                "persistence_outcome": "STORED",
                "lifecycle_result_digest": DIGEST_D,
                "readback_path": f"/api/v1/paper-lifecycle-results/{DIGEST_D}",
            },
        ),
        (
            200,
            {
                "contract_version": "p01-rti-03-v1",
                "outcome": "FOUND",
                "lifecycle_result_digest": DIGEST_C,
                "result_digest": DIGEST_E,
                "run": {
                    "lifecycle_result_digest": DIGEST_C,
                    "artifact_count": 0,
                },
                "artifacts": [],
            },
        ),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="readback lifecycle digest mismatch"):
        run_smoke(_config(run=True, persist=True), request_json=request)

    assert len(calls) == 8


def test_run_case_identity_mismatch_stops_before_post_run_review():
    calls = []

    responses = [
        _ready(),
        _valid(),
        _prepared(),
        _review_ready(),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_B,
                "contract_version": "p01-oaf-01-run-once-v1",
                "state": "RUN_TERMINAL",
                "outcome": "RUN_TERMINAL",
                "simulation_only": True,
                "persist_eligible": False,
            },
        ),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="run case digest mismatch"):
        run_smoke(_config(run=True), request_json=request)

    assert len(calls) == 5


def test_run_and_post_run_review_digest_mismatch_stops_before_persist():
    calls = []

    responses = [
        _ready(),
        _valid(),
        _prepared(),
        _review_ready(),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-run-once-v1",
                "state": "RUN_TERMINAL",
                "outcome": "RUN_TERMINAL",
                "simulation_only": True,
                "oci_digest": DIGEST_B,
                "osc_digest": DIGEST_C,
                "lifecycle_result_digest": DIGEST_D,
                "persist_eligible": True,
            },
        ),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-case-registry-v3",
                "state": "RUN_TERMINAL",
                "simulation_only": True,
                "source_label": "historical_price_proxy_and_explicit_simulation_assumptions",
                "oci_digest": DIGEST_B,
                "osc_digest": DIGEST_C,
                "lifecycle_result_digest": DIGEST_A,
            },
        ),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(
        OperatorSmokeError,
        match="run/post-run review lifecycle_result_digest mismatch",
    ):
        run_smoke(_config(run=True, persist=True), request_json=request)

    assert len(calls) == 6


def test_persist_case_identity_mismatch_stops_before_readback():
    calls = []

    responses = [
        _ready(),
        _valid(),
        _prepared(),
        _review_ready(),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-run-once-v1",
                "state": "RUN_TERMINAL",
                "outcome": "RUN_TERMINAL",
                "simulation_only": True,
                "oci_digest": DIGEST_B,
                "osc_digest": DIGEST_C,
                "lifecycle_result_digest": DIGEST_D,
                "persist_eligible": True,
            },
        ),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-case-registry-v3",
                "state": "RUN_TERMINAL",
                "simulation_only": True,
                "source_label": "historical_price_proxy_and_explicit_simulation_assumptions",
                "oci_digest": DIGEST_B,
                "osc_digest": DIGEST_C,
                "lifecycle_result_digest": DIGEST_D,
            },
        ),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_B,
                "contract_version": "p01-oaf-01-persist-once-v1",
                "state": "PERSIST_TERMINAL",
                "outcome": "PERSIST_TERMINAL",
                "simulation_only": True,
                "persistence_digest": DIGEST_E,
                "artifact_count": 0,
                "persistence_outcome": "STORED",
                "lifecycle_result_digest": DIGEST_D,
                "readback_path": f"/api/v1/paper-lifecycle-results/{DIGEST_D}",
            },
        ),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="persist case digest mismatch"):
        run_smoke(_config(run=True, persist=True), request_json=request)

    assert len(calls) == 7


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


def test_run_contract_mismatch_stops_before_post_run_review():
    calls = []
    run = {
        "contract_version": "wrong-run-contract",
        "handle": "opaque",
        "case_digest": DIGEST_A,
        "state": "RUN_TERMINAL",
        "outcome": "RUN_TERMINAL",
        "simulation_only": True,
        "persist_eligible": False,
    }
    responses = [_ready(), _valid(), _prepared(), _review_ready(), (200, run)]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="run contract mismatch"):
        run_smoke(_config(run=True), request_json=request)

    assert len(calls) == 5


def test_post_run_review_contract_mismatch_stops_before_persist():
    calls = []
    run = {
        "contract_version": "p01-oaf-01-run-once-v1",
        "handle": "opaque",
        "case_digest": DIGEST_A,
        "state": "RUN_TERMINAL",
        "outcome": "RUN_TERMINAL",
        "simulation_only": True,
        "persist_eligible": False,
    }
    review = {
        "contract_version": "wrong-review-contract",
        "handle": "opaque",
        "case_digest": DIGEST_A,
        "state": "RUN_TERMINAL",
        "simulation_only": True,
        "source_label": "historical_price_proxy_and_explicit_simulation_assumptions",
    }
    responses = [_ready(), _valid(), _prepared(), _review_ready(), (200, run), (200, review)]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="post-run review contract mismatch"):
        run_smoke(_config(run=True, persist=True), request_json=request)

    assert len(calls) == 6


def test_persist_contract_mismatch_stops_before_readback():
    calls = []
    run = {
        "contract_version": "p01-oaf-01-run-once-v1",
        "handle": "opaque",
        "case_digest": DIGEST_A,
        "state": "RUN_TERMINAL",
        "outcome": "RUN_TERMINAL",
        "simulation_only": True,
        "oci_digest": DIGEST_B,
        "osc_digest": DIGEST_C,
        "lifecycle_result_digest": DIGEST_D,
        "persist_eligible": True,
    }
    review = {
        "contract_version": "p01-oaf-01-case-registry-v3",
        "handle": "opaque",
        "case_digest": DIGEST_A,
        "state": "RUN_TERMINAL",
        "simulation_only": True,
        "source_label": "historical_price_proxy_and_explicit_simulation_assumptions",
        "oci_digest": DIGEST_B,
        "osc_digest": DIGEST_C,
        "lifecycle_result_digest": DIGEST_D,
    }
    persist = {
        "contract_version": "wrong-persist-contract",
        "handle": "opaque",
        "case_digest": DIGEST_A,
        "state": "PERSIST_TERMINAL",
        "outcome": "PERSIST_TERMINAL",
        "simulation_only": True,
        "persistence_digest": DIGEST_E,
        "artifact_count": 0,
        "persistence_outcome": "STORED",
        "lifecycle_result_digest": DIGEST_D,
        "readback_path": f"/api/v1/paper-lifecycle-results/{DIGEST_D}",
    }
    responses = [
        _ready(),
        _valid(),
        _prepared(),
        _review_ready(),
        (200, run),
        (200, review),
        (200, persist),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="persist contract mismatch"):
        run_smoke(_config(run=True, persist=True), request_json=request)

    assert len(calls) == 7


def test_readback_contract_mismatch_is_rejected():
    calls = []
    run = {
        "contract_version": "p01-oaf-01-run-once-v1",
        "handle": "opaque",
        "case_digest": DIGEST_A,
        "state": "RUN_TERMINAL",
        "outcome": "RUN_TERMINAL",
        "simulation_only": True,
        "oci_digest": DIGEST_B,
        "osc_digest": DIGEST_C,
        "lifecycle_result_digest": DIGEST_D,
        "persist_eligible": True,
    }
    review = {
        "contract_version": "p01-oaf-01-case-registry-v3",
        "handle": "opaque",
        "case_digest": DIGEST_A,
        "state": "RUN_TERMINAL",
        "simulation_only": True,
        "source_label": "historical_price_proxy_and_explicit_simulation_assumptions",
        "oci_digest": DIGEST_B,
        "osc_digest": DIGEST_C,
        "lifecycle_result_digest": DIGEST_D,
    }
    persist = {
        "contract_version": "p01-oaf-01-persist-once-v1",
        "handle": "opaque",
        "case_digest": DIGEST_A,
        "state": "PERSIST_TERMINAL",
        "outcome": "PERSIST_TERMINAL",
        "simulation_only": True,
        "persistence_digest": DIGEST_E,
        "artifact_count": 0,
        "persistence_outcome": "STORED",
        "lifecycle_result_digest": DIGEST_D,
        "readback_path": f"/api/v1/paper-lifecycle-results/{DIGEST_D}",
    }
    readback = {
        "contract_version": "wrong-readback-contract",
        "outcome": "FOUND",
        "lifecycle_result_digest": DIGEST_D,
    }
    responses = [
        _ready(),
        _valid(),
        _prepared(),
        _review_ready(),
        (200, run),
        (200, review),
        (200, persist),
        (200, readback),
    ]

    def request(method, url, token, payload, timeout):
        calls.append((method, url, payload))
        return responses[len(calls) - 1]

    with pytest.raises(OperatorSmokeError, match="readback contract mismatch"):
        run_smoke(_config(run=True, persist=True), request_json=request)

    assert len(calls) == 8


def test_non_persistable_run_stops_without_persist_or_readback():
    calls = []

    responses = [
        _ready(),
        _valid(),
        _prepared(),
        _review_ready(),
        (
            200,
            {
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "contract_version": "p01-oaf-01-run-once-v1",
                "state": "RUN_TERMINAL",
                "outcome": "RUN_TERMINAL",
                "simulation_only": True,
                "persist_eligible": False,
            },
        ),
        (
            200,
            {
                "contract_version": "p01-oaf-01-case-registry-v3",
                "handle": "opaque",
                "case_digest": DIGEST_A,
                "state": "RUN_TERMINAL",
                "simulation_only": True,
                "source_label": "historical_price_proxy_and_explicit_simulation_assumptions",
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
