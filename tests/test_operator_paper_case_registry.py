from datetime import datetime, timedelta, timezone

import pytest

from backend.api.operator_access import OperatorAccessDenied, require_operator_bearer
from backend.application.oaf_prepare_case import OafPrepareCaseService
from backend.application.operator_paper_case_registry import (
    OperatorPaperCaseRegistry,
    OperatorPaperCaseState,
)
from tests.test_oaf_prepare_case import _request


NOW = datetime(2026, 9, 25, 8, 0, tzinfo=timezone.utc)


def _prepared():
    return OafPrepareCaseService().prepare(_request())


def test_registry_preserves_exact_prepared_object_and_case_digest():
    prepared = _prepared()
    registry = OperatorPaperCaseRegistry(
        capacity=2,
        ttl=timedelta(minutes=10),
        clock=lambda: NOW,
        handle_factory=lambda: "opaque-handle-12345678901234567890",
    )

    record = registry.put(prepared)

    assert record.prepared is prepared
    assert record.state is OperatorPaperCaseState.REVIEW_READY
    assert len(record.case_digest) == 64
    assert registry.get(record.handle) is record
    assert registry.size() == 1


def test_registry_expires_without_reconstructing_case():
    prepared = _prepared()
    current = [NOW]
    registry = OperatorPaperCaseRegistry(
        capacity=2,
        ttl=timedelta(seconds=5),
        clock=lambda: current[0],
        handle_factory=lambda: "opaque-handle-12345678901234567890",
    )
    record = registry.put(prepared)
    current[0] = NOW + timedelta(seconds=6)

    assert registry.get(record.handle) is None
    assert registry.size() == 0


def test_registry_capacity_fails_closed():
    handles = iter(
        (
            "opaque-handle-11111111111111111111",
            "opaque-handle-22222222222222222222",
        )
    )
    registry = OperatorPaperCaseRegistry(
        capacity=1,
        ttl=timedelta(minutes=10),
        clock=lambda: NOW,
        handle_factory=lambda: next(handles),
    )
    registry.put(_prepared())
    with pytest.raises(RuntimeError, match="CASE_REGISTRY_CAPACITY_EXCEEDED"):
        registry.put(_prepared())


@pytest.mark.parametrize(
    "authorization,configured,reason",
    [
        (None, "x" * 32, "OPERATOR_AUTH_REQUIRED"),
        ("Basic abc", "x" * 32, "OPERATOR_AUTH_REQUIRED"),
        ("Bearer wrong", "x" * 32, "OPERATOR_AUTH_INVALID"),
        ("Bearer " + "x" * 32, None, "OPERATOR_ACCESS_UNAVAILABLE"),
        ("Bearer " + "x" * 32, "short", "OPERATOR_ACCESS_UNAVAILABLE"),
    ],
)
def test_operator_access_fails_closed(authorization, configured, reason):
    with pytest.raises(OperatorAccessDenied, match=reason):
        require_operator_bearer(
            authorization=authorization,
            configured_token=configured,
        )


def test_operator_access_accepts_exact_bearer_only():
    token = "controller-secret-token-1234567890"
    require_operator_bearer(
        authorization=f"Bearer {token}",
        configured_token=token,
    )
