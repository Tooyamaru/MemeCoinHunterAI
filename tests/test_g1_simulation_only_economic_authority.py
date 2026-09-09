"""Focused contract tests for the G1 implementation surface."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from core.learning.g1_simulation_only_economic_authority import (
    G1AuthorityAReference,
    G1FinalityState,
    G1P07HistorySnapshot,
    G1ReasonCode,
    G1RecognitionState,
    G1SimulationOnlyEconomicAuthorityInput,
    evaluate_g1,
)


def test_outer_input_is_explicit_and_fail_closed() -> None:
    assert evaluate_g1(object()) is None
    assert evaluate_g1(None) is None


def test_authority_reference_is_immutable() -> None:
    value = G1AuthorityAReference("subject", "lifecycle", "authority", "v1")
    with pytest.raises(FrozenInstanceError):
        value.lifecycle_identity = "other"  # type: ignore[misc]


def test_reason_vocabulary_and_precedence_are_closed() -> None:
    assert G1ReasonCode.RECOGNIZED_COMPLETE.value == "RECOGNIZED_COMPLETE"
    assert G1ReasonCode.INVALID_TYPE.value == "INVALID_TYPE"
    assert G1ReasonCode.DETERMINISM_FAILURE.value == "DETERMINISM_FAILURE"
    assert G1RecognitionState.RECOGNIZED.value == "RECOGNIZED"
    assert G1FinalityState.FINAL.value == "FINAL"


def test_history_snapshot_is_reordered_deterministically() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        G1P07HistorySnapshot(
            results=(),
            history_digest="0" * 64,
            history_identity="0" * 64,
        )


def test_cutoff_value_is_not_generated_by_wall_clock() -> None:
    cutoff = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert cutoff.isoformat() == "2026-01-01T00:00:00+00:00"