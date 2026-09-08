from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import inspect
import json

import pytest

import core.learning.economic_outcome_interpretation as economic_module
from core.learning.economic_outcome_interpretation import (
    EconomicOutcomeFailureReason,
    EconomicOutcomeInterpretationInput,
    EconomicOutcomeInterpretationResult,
    EconomicOutcomeInterpretationStatus,
    G2RealizationState,
    G3Validity,
    G4Validity,
    P08_T07_CONTRACT_VERSION,
    P08_T07_EVALUATOR_VERSION,
    PerformanceClassification,
    evaluate_economic_outcome_interpretation,
)


def _digest(character: str) -> str:
    return character * 64


def _valid_input(**overrides):
    values = {
        "decision_intent_id": "decision-1",
        "lifecycle_id": "lifecycle-1",
        "observation_id": "observation-1",
        "dataset_snapshot_id": "dataset-1",
        "evidence_evaluation_snapshot_id": "evidence-snapshot-1",
        "readiness_result_id": "readiness-1",
        "g2_result_id": "g2-1",
        "g2_state": G2RealizationState.REALIZED_ELIGIBLE,
        "g2_policy_version": "g2-policy-v1",
        "g2_result_digest": _digest("a"),
        "g2_provenance": {"lifecycle_id": "lifecycle-1"},
        "g3_result_id": "g3-1",
        "g3_validity": G3Validity.VALID_REALIZED_ECONOMIC_RESULT,
        "realized_economic_result": Decimal("12.3400"),
        "canonical_numeraire": "USD",
        "g3_policy_version": "g3-policy-v1",
        "g3_result_digest": _digest("b"),
        "g3_provenance": {"lifecycle_id": "lifecycle-1"},
        "g4_result_id": "g4-1",
        "g4_validity": G4Validity.VALID_CANONICAL_CLASSIFICATION,
        "classification": PerformanceClassification.WIN,
        "g4_policy_version": "g4-policy-v1",
        "g4_result_digest": _digest("c"),
        "g4_provenance": {"lifecycle_id": "lifecycle-1"},
        "evidence_digest": _digest("e"),
        "evidence_references": ("evidence-1",),
        "authority_references": ("authority-1",),
        "source_references": ("source-1",),
        "correction_lineage": (),
        "supersession_lineage": (),
        "canonical_timestamps": {
            "lifecycle": datetime(2026, 1, 1, tzinfo=timezone.utc),
        },
    }
    values.update(overrides)
    return EconomicOutcomeInterpretationInput(**values)


def _valid_result(**overrides):
    return evaluate_economic_outcome_interpretation(
        _valid_input(**overrides)
    )


def test_contract_versions_and_canonical_fields_are_exact():
    result = _valid_result()

    assert isinstance(result, EconomicOutcomeInterpretationResult)
    assert result.contract_version == P08_T07_CONTRACT_VERSION == "p08-t07-v1"
    assert (
        result.evaluator_version
        == P08_T07_EVALUATOR_VERSION
        == "p08-t07-evaluator-v1"
    )
    assert [field.name for field in fields(result)] == [
        "contract_version",
        "evaluator_version",
        "decision_intent_id",
        "lifecycle_id",
        "status",
        "failure_reason",
        "realization_eligibility",
        "realized_economic_result",
        "canonical_numeraire",
        "performance_classification",
        "g2_result_id",
        "g2_policy_version",
        "g2_result_digest",
        "g3_result_id",
        "g3_policy_version",
        "g3_result_digest",
        "g4_result_id",
        "g4_policy_version",
        "g4_result_digest",
        "evidence_digest",
        "provenance",
        "correction_lineage",
        "supersession_lineage",
        "result_digest",
        "classification_digest",
    ]
    assert set(result.canonical_representation) == {
        field.name for field in fields(result)
    }


def test_valid_result_preserves_materialized_g2_g3_g4_without_recalculation():
    result = _valid_result(
        realized_economic_result=Decimal("12.3400"),
        classification=PerformanceClassification.WIN,
    )

    assert result.status is EconomicOutcomeInterpretationStatus.VALID
    assert result.failure_reason is None
    assert result.realization_eligibility == "REALIZED_ELIGIBLE"
    assert result.realized_economic_result == "12.3400"
    assert result.performance_classification is PerformanceClassification.WIN
    assert result.g2_result_digest == _digest("a")
    assert result.g3_result_digest == _digest("b")
    assert result.g4_result_digest == _digest("c")
    assert result.evidence_digest == _digest("e")


@pytest.mark.parametrize(
    "classification",
    [
        PerformanceClassification.WIN,
        PerformanceClassification.LOSS,
        PerformanceClassification.BREAKEVEN,
    ],
)
def test_valid_result_preserves_each_canonical_g4_classification(classification):
    result = _valid_result(classification=classification)

    assert result.status is EconomicOutcomeInterpretationStatus.VALID
    assert result.performance_classification is classification


@pytest.mark.parametrize(
    "g2_state",
    [
        G2RealizationState.NON_FINAL,
        G2RealizationState.SETTLEMENT_PENDING,
        G2RealizationState.SETTLED_BUT_NOT_REALIZED_ELIGIBLE,
    ],
)
def test_valid_non_realized_lifecycle_has_no_economic_outcome(g2_state):
    result = _valid_result(
        g2_state=g2_state,
        g3_validity=G3Validity.NOT_REALIZED,
        g4_validity=G4Validity.NOT_REALIZED,
        realized_economic_result=None,
        canonical_numeraire=None,
        classification=None,
    )

    assert result.status is EconomicOutcomeInterpretationStatus.NOT_REALIZED
    assert result.failure_reason is (
        EconomicOutcomeFailureReason.NON_REALIZED_LIFECYCLE
    )
    assert result.realization_eligibility == "NOT_REALIZED_ELIGIBLE"
    assert result.realized_economic_result is None
    assert result.performance_classification is None
    assert result.classification_digest is None


def test_missing_input_returns_explicit_invalid_result():
    result = evaluate_economic_outcome_interpretation(
        EconomicOutcomeInterpretationInput()
    )

    assert result.status is EconomicOutcomeInterpretationStatus.INVALID_INPUT
    assert result.failure_reason is (
        EconomicOutcomeFailureReason.MISSING_REQUIRED_INPUT
    )
    assert result.realization_eligibility is None
    assert result.realized_economic_result is None
    assert result.performance_classification is None
    assert result.result_digest


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        (
            "g2_state",
            "NOT_A_G2_STATE",
            EconomicOutcomeFailureReason.INVALID_G2,
        ),
        (
            "g3_validity",
            "NOT_A_G3_STATE",
            EconomicOutcomeFailureReason.INVALID_G3,
        ),
        (
            "g4_validity",
            "NOT_A_G4_STATE",
            EconomicOutcomeFailureReason.INVALID_G4,
        ),
        (
            "g4_result_digest",
            "not-a-digest",
            EconomicOutcomeFailureReason.DIGEST_FAILURE,
        ),
        (
            "realized_economic_result",
            1.25,
            EconomicOutcomeFailureReason.NUMERIC_INVALID,
        ),
    ],
)
def test_invalid_upstream_or_numeric_input_is_fail_closed(field, value, reason):
    result = _valid_result(**{field: value})

    assert result.status is EconomicOutcomeInterpretationStatus.INVALID_INPUT
    assert result.failure_reason is reason
    assert result.realized_economic_result is None
    assert result.performance_classification is None


def test_invalid_classification_is_not_recalculated():
    result = _valid_result(classification="NOT_A_CLASSIFICATION")

    assert result.status is EconomicOutcomeInterpretationStatus.INVALID_INPUT
    assert result.failure_reason is EconomicOutcomeFailureReason.INVALID_G4
    assert result.performance_classification is None


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        (
            "correction_lineage",
            EconomicOutcomeFailureReason.UNRESOLVED_CORRECTION,
        ),
        (
            "supersession_lineage",
            EconomicOutcomeFailureReason.UNRESOLVED_SUPERSESSION,
        ),
    ],
)
def test_unresolved_lineage_is_invalid(field, reason):
    result = _valid_result(**{field: ("UNRESOLVED",)})

    assert result.status is EconomicOutcomeInterpretationStatus.INVALID_INPUT
    assert result.failure_reason is reason


def test_provenance_conflict_is_invalid():
    result = _valid_result(
        g3_provenance={
            "lifecycle_id": "different-lifecycle",
        }
    )

    assert result.status is EconomicOutcomeInterpretationStatus.INVALID_INPUT
    assert result.failure_reason is (
        EconomicOutcomeFailureReason.PROVENANCE_LINKAGE_FAILURE
    )


def test_unresolved_residual_and_conflicting_input_are_invalid():
    residual = _valid_result(
        g2_provenance={
            "lifecycle_id": "lifecycle-1",
            "unresolved_residual": True,
        }
    )
    conflict = _valid_result(
        g4_provenance={
            "lifecycle_id": "lifecycle-1",
            "status": "CONTRADICTORY",
        }
    )

    assert residual.failure_reason is EconomicOutcomeFailureReason.UNRESOLVED_RESIDUAL
    assert conflict.failure_reason is EconomicOutcomeFailureReason.CONFLICTING_INPUT


def test_negative_zero_normalizes_without_reclassification():
    result = _valid_result(
        realized_economic_result=Decimal("-0.00"),
        classification=PerformanceClassification.BREAKEVEN,
    )

    assert result.status is EconomicOutcomeInterpretationStatus.VALID
    assert result.realized_economic_result == "0"
    assert result.performance_classification is PerformanceClassification.BREAKEVEN


def test_timezone_aware_timestamp_normalizes_to_utc():
    result = _valid_result(
        canonical_timestamps={
            "lifecycle": datetime(
                2026,
                1,
                1,
                1,
                tzinfo=timezone(timedelta(hours=1)),
            )
        }
    )

    assert result.status is EconomicOutcomeInterpretationStatus.VALID
    assert result.provenance["canonical_timestamps"] == {
        "lifecycle": "2026-01-01T00:00:00+00:00"
    }


def test_utc_timestamp_string_is_valid():
    result = _valid_result(
        canonical_timestamps={"lifecycle": "2026-01-01T00:00:00Z"}
    )

    assert result.status is EconomicOutcomeInterpretationStatus.VALID
    assert result.provenance["canonical_timestamps"] == {
        "lifecycle": "2026-01-01T00:00:00+00:00"
    }


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-01-01T00:00:00",
        "not-a-timestamp",
    ],
)
def test_naive_or_malformed_timestamp_is_invalid(timestamp):
    result = _valid_result(canonical_timestamps={"lifecycle": timestamp})

    assert result.status is EconomicOutcomeInterpretationStatus.INVALID_INPUT
    assert result.failure_reason is (
        EconomicOutcomeFailureReason.PROVENANCE_LINKAGE_FAILURE
    )


def test_equivalent_timestamps_have_deterministic_utc_representation():
    offset_result = _valid_result(
        canonical_timestamps={"lifecycle": "2026-01-01T01:00:00+01:00"}
    )
    utc_result = _valid_result(
        canonical_timestamps={"lifecycle": "2026-01-01T00:00:00Z"}
    )

    assert (
        offset_result.canonical_representation
        == utc_result.canonical_representation
    )
    assert offset_result.result_digest == utc_result.result_digest


def test_valid_realized_result_requires_canonical_numeraire():
    result = _valid_result(canonical_numeraire=None)

    assert result.status is EconomicOutcomeInterpretationStatus.INVALID_INPUT
    assert result.failure_reason is (
        EconomicOutcomeFailureReason.MISSING_REQUIRED_INPUT
    )
    assert result.realized_economic_result is None
    assert result.canonical_numeraire is None


@pytest.mark.parametrize("numeraire", ["", "   ", 42])
def test_invalid_realized_numeraire_is_fail_closed(numeraire):
    result = _valid_result(canonical_numeraire=numeraire)

    assert result.status is EconomicOutcomeInterpretationStatus.INVALID_INPUT
    assert result.failure_reason is EconomicOutcomeFailureReason.NUMERIC_INVALID


def test_realized_numeraire_is_assembled_without_conversion():
    result = _valid_result(
        canonical_numeraire="EUR",
        realized_economic_result=Decimal("12.3400"),
    )

    assert result.status is EconomicOutcomeInterpretationStatus.VALID
    assert result.canonical_numeraire == "EUR"
    assert result.realized_economic_result == "12.3400"


def test_result_and_nested_canonical_values_are_immutable():
    result = _valid_result()

    with pytest.raises(FrozenInstanceError):
        result.status = EconomicOutcomeInterpretationStatus.INVALID_INPUT
    with pytest.raises(TypeError):
        result.canonical_representation["status"] = "INVALID_INPUT"
    with pytest.raises(TypeError):
        result.provenance["lifecycle_id"] = "tampered"
    assert type(result.correction_lineage) is tuple


def test_digests_are_deterministic_and_non_circular():
    left = _valid_result()
    right = _valid_result()

    assert left.canonical_representation == right.canonical_representation
    assert left.result_digest == right.result_digest
    assert left.classification_digest == right.classification_digest
    assert left.result_digest == _sha256(left.digest_representation)
    assert left.result_digest not in left.digest_representation.values()
    assert left.classification_digest == _sha256(
        {
            "classification": "WIN",
            "g4_policy_version": "g4-policy-v1",
            "g4_result_digest": _digest("c"),
            "g4_result_id": "g4-1",
            "lifecycle_id": "lifecycle-1",
        }
    )


def test_mapping_input_is_supported_but_unknown_fields_fail_closed():
    valid = _valid_input()
    mapping = {
        field.name: getattr(valid, field.name)
        for field in fields(valid)
    }
    assert (
        evaluate_economic_outcome_interpretation(mapping).status
        is EconomicOutcomeInterpretationStatus.VALID
    )

    invalid = dict(mapping, unexpected="value")
    result = evaluate_economic_outcome_interpretation(invalid)
    assert result.status is EconomicOutcomeInterpretationStatus.INVALID_INPUT
    assert result.failure_reason is EconomicOutcomeFailureReason.CONFLICTING_INPUT


def test_public_boundary_has_no_external_authority_operations():
    signature = inspect.signature(
        economic_module.evaluate_economic_outcome_interpretation
    )
    assert tuple(signature.parameters) == ("input_value",)
    assert "socket" not in economic_module.__dict__
    assert "requests" not in economic_module.__dict__
    assert "sqlite3" not in economic_module.__dict__
    assert "EconomicEvidencePacket" not in economic_module.__dict__


def test_only_assembly_semantics_are_exposed():
    forbidden = (
        "calculate_profit",
        "calculate_pnl",
        "classify_performance",
        "fetch_provider",
        "execute_trade",
        "sign_transaction",
        "wallet",
        "rpc",
        "persist",
    )
    for name in forbidden:
        assert not hasattr(economic_module, name)


def _sha256(value):
    def plain(item):
        if isinstance(item, dict):
            return {key: plain(child) for key, child in item.items()}
        if hasattr(item, "items"):
            return {key: plain(child) for key, child in item.items()}
        if isinstance(item, tuple):
            return [plain(child) for child in item]
        return item

    return hashlib.sha256(
        json.dumps(
            plain(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()