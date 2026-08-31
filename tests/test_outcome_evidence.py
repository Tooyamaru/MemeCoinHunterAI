from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta
import hashlib
import inspect
import json
from typing import Literal, get_args, get_origin, get_type_hints

import pytest

import core.learning.outcome_evidence as outcome_evidence_module
from core.learning import (
    OutcomeEvidenceEvaluationResult,
    OutcomeEvidenceReasonCode,
    OutcomeEvidenceState,
    OutcomeInterpretationStatus,
    P08_T03_CONTRACT_VERSION,
    P08_T03_EVALUATOR_VERSION,
    P08_T04_CONTRACT_VERSION,
    P08_T04_EVALUATOR_VERSION,
    create_outcome_evidence_evaluation,
    create_outcome_interpretation_snapshot,
    create_outcome_learning_dataset_snapshot,
)
from core.execution import PaperSimulationResultHistory
from tests.test_outcome_learning import _observation
from tests.test_outcome_learning_dataset import _second_observation


def _dataset():
    observation = _observation()
    return create_outcome_learning_dataset_snapshot(
        (observation,),
        observation.simulation_reference_time,
    )


def _interpretation(status=OutcomeInterpretationStatus.UNCLASSIFIED):
    result = create_outcome_interpretation_snapshot(_dataset()).results[0]
    return replace(result, interpretation_status=status)


def test_evaluation_preserves_valid_linkage_and_paper_provenance():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]

    result = create_outcome_evidence_evaluation(interpretation, dataset)

    observation = dataset.observations[0]
    assert isinstance(result, OutcomeEvidenceEvaluationResult)
    assert result.source_interpretation_digest == interpretation.digest
    assert result.source_dataset_digest == dataset.digest
    assert result.source_observation_digest == observation.digest
    assert result.source_paper_outcome_status == observation.outcome_status
    assert result.source_reconciliation_status == observation.reconciliation_status
    assert result.source_interpretation_contract_version == P08_T03_CONTRACT_VERSION
    assert result.source_interpretation_evaluator_version == P08_T03_EVALUATOR_VERSION
    assert result.contract_version == P08_T04_CONTRACT_VERSION
    assert result.evaluator_version == P08_T04_EVALUATOR_VERSION


def test_output_contract_has_exact_public_fields_and_types():
    result = create_outcome_evidence_evaluation(
        create_outcome_interpretation_snapshot(_dataset()).results[0],
        _dataset(),
    )
    expected_fields = [
        "source_interpretation_digest",
        "source_dataset_digest",
        "source_observation_digest",
        "source_paper_outcome_status",
        "source_reconciliation_status",
        "evidence_state",
        "reason_codes",
        "source_candidate_id",
        "source_chain_id",
        "source_token_identity",
        "source_reference_time",
        "source_interpretation_contract_version",
        "source_interpretation_evaluator_version",
        "contract_version",
        "evaluator_version",
        "result_digest",
    ]
    assert [field.name for field in fields(result)] == expected_fields

    hints = get_type_hints(OutcomeEvidenceEvaluationResult)
    assert hints["source_interpretation_digest"] is str
    assert hints["source_dataset_digest"] is str
    assert hints["source_observation_digest"] is str
    assert hints["source_paper_outcome_status"] is str
    assert hints["source_reconciliation_status"] is str
    assert hints["evidence_state"] is OutcomeEvidenceState
    assert hints["reason_codes"] == tuple[OutcomeEvidenceReasonCode, ...]
    assert hints["source_candidate_id"] is str
    assert hints["source_chain_id"] is str
    assert hints["source_token_identity"] is str
    assert hints["source_reference_time"] is datetime
    assert get_origin(hints["source_interpretation_contract_version"]) is Literal
    assert get_args(hints["source_interpretation_contract_version"]) == (
        P08_T03_CONTRACT_VERSION,
    )
    assert hints["source_interpretation_evaluator_version"] is str
    assert get_origin(hints["contract_version"]) is Literal
    assert get_args(hints["contract_version"]) == (P08_T04_CONTRACT_VERSION,)
    assert get_origin(hints["evaluator_version"]) is Literal
    assert get_args(hints["evaluator_version"]) == (P08_T04_EVALUATOR_VERSION,)
    assert hints["result_digest"] is str


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (
            OutcomeInterpretationStatus.UNCLASSIFIED,
            OutcomeEvidenceReasonCode.STATE_UNCLASSIFIED_PRESERVED,
        ),
        (
            OutcomeInterpretationStatus.UNKNOWN,
            OutcomeEvidenceReasonCode.STATE_UNKNOWN_PRESERVED,
        ),
        (
            OutcomeInterpretationStatus.UNAVAILABLE,
            OutcomeEvidenceReasonCode.STATE_UNAVAILABLE_PRESERVED,
        ),
        (
            OutcomeInterpretationStatus.INCOMPLETE,
            OutcomeEvidenceReasonCode.STATE_INCOMPLETE_PRESERVED,
        ),
    ],
)
def test_all_evidence_states_and_reason_order_are_preserved(status, reason):
    dataset = _dataset()
    result = create_outcome_evidence_evaluation(
        _interpretation(status),
        dataset,
    )

    assert result.evidence_state is OutcomeEvidenceState(status.value)
    assert result.reason_codes == (
        OutcomeEvidenceReasonCode.LINKAGE_VALID,
        reason,
    )


def test_evaluation_is_deterministic_and_digest_covers_canonical_result():
    left_dataset = _dataset()
    right_dataset = _dataset()
    left = create_outcome_evidence_evaluation(
        create_outcome_interpretation_snapshot(left_dataset).results[0],
        left_dataset,
    )
    right = create_outcome_evidence_evaluation(
        create_outcome_interpretation_snapshot(right_dataset).results[0],
        right_dataset,
    )

    assert left.canonical_representation == right.canonical_representation
    assert left.deterministic_representation == left.canonical_representation
    assert left.result_digest == right.result_digest
    assert len(left.result_digest) == 64


def test_result_digest_covers_every_semantic_field():
    dataset = _dataset()
    result = create_outcome_evidence_evaluation(
        create_outcome_interpretation_snapshot(dataset).results[0],
        dataset,
    )
    canonical = dict(result.canonical_representation)
    assert set(canonical) == {
        "source_interpretation_digest",
        "source_dataset_digest",
        "source_observation_digest",
        "source_paper_outcome_status",
        "source_reconciliation_status",
        "evidence_state",
        "reason_codes",
        "source_candidate_id",
        "source_chain_id",
        "source_token_identity",
        "source_reference_time",
        "source_interpretation_contract_version",
        "source_interpretation_evaluator_version",
        "contract_version",
        "evaluator_version",
    }

    def digest(value):
        return hashlib.sha256(
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()

    assert result.result_digest == digest(canonical)
    mutations = {
        "source_interpretation_digest": "0" * 64,
        "source_dataset_digest": "1" * 64,
        "source_observation_digest": "2" * 64,
        "source_paper_outcome_status": "TAMPERED",
        "source_reconciliation_status": "TAMPERED",
        "evidence_state": OutcomeEvidenceState.UNKNOWN.value,
        "reason_codes": (
            OutcomeEvidenceReasonCode.LINKAGE_VALID.value,
            OutcomeEvidenceReasonCode.STATE_UNKNOWN_PRESERVED.value,
        ),
        "source_candidate_id": "TAMPERED",
        "source_chain_id": "TAMPERED",
        "source_token_identity": "TAMPERED",
        "source_reference_time": "2030-01-01T00:00:00+00:00",
        "source_interpretation_contract_version": "p08-t99-v1",
        "source_interpretation_evaluator_version": "p08-t03-tampered-v1",
        "contract_version": "p08-t99-v1",
        "evaluator_version": "p08-t04-tampered-v1",
    }
    for field_name, value in mutations.items():
        tampered = dict(canonical)
        tampered[field_name] = value
        assert digest(tampered) != result.result_digest, field_name


def test_result_is_immutable_and_nested_representation_is_frozen():
    dataset = _dataset()
    result = create_outcome_evidence_evaluation(
        create_outcome_interpretation_snapshot(dataset).results[0],
        dataset,
    )

    with pytest.raises(FrozenInstanceError):
        result.evidence_state = OutcomeEvidenceState.UNKNOWN
    with pytest.raises(TypeError):
        result.canonical_representation["evidence_state"] = "UNKNOWN"
    assert isinstance(result.reason_codes, tuple)


def test_rejects_dataset_linkage_mismatch():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    tampered = replace(
        interpretation,
        source_dataset_digest="0" * 64,
    )

    with pytest.raises(ValueError, match="source dataset digest"):
        create_outcome_evidence_evaluation(tampered, dataset)


def test_rejects_observation_mismatch_and_non_member():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    tampered = replace(
        interpretation,
        source_observation_digest="0" * 64,
    )

    with pytest.raises(ValueError, match="exactly one observation"):
        create_outcome_evidence_evaluation(tampered, dataset)


def test_rejects_provenance_mismatch():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    tampered = replace(interpretation, candidate_id="different-candidate")

    with pytest.raises(ValueError, match="candidate identity"):
        create_outcome_evidence_evaluation(tampered, dataset)


def test_rejects_cutoff_violation():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    tampered = replace(
        interpretation,
        reference_time=dataset.as_of_time + timedelta(seconds=1),
    )

    with pytest.raises(ValueError, match="reference time"):
        create_outcome_evidence_evaluation(tampered, dataset)


def test_rejects_invalid_and_unsupported_predecessors():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]

    with pytest.raises(ValueError, match="OutcomeInterpretationResult"):
        create_outcome_evidence_evaluation(object(), dataset)
    with pytest.raises(ValueError, match="OutcomeLearningDatasetSnapshot"):
        create_outcome_evidence_evaluation(interpretation, object())
    with pytest.raises(ValueError, match="contract version"):
        create_outcome_evidence_evaluation(
            replace(interpretation, contract_version="p08-t99-v1"),
            dataset,
        )

    object.__setattr__(
        interpretation,
        "evaluator_version",
        "p08-t03-unsupported-v1",
    )
    with pytest.raises(ValueError, match="invalid|evaluator"):
        create_outcome_evidence_evaluation(interpretation, dataset)


def test_rejects_tampered_dataset_and_duplicate_resolution():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]

    object.__setattr__(dataset, "observations", (dataset.observations[0],) * 2)
    object.__setattr__(
        dataset,
        "observation_digests",
        (dataset.observations[0].digest,) * 2,
    )

    with pytest.raises(ValueError, match="invalid|duplicate"):
        create_outcome_evidence_evaluation(interpretation, dataset)


def test_rejects_tampered_source_observation_digest():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    object.__setattr__(
        dataset.observations[0].decision_intent.context,
        "candidate_id",
        "tampered-source-observation",
    )

    with pytest.raises(ValueError, match="invalid|tampered|canonical"):
        create_outcome_evidence_evaluation(interpretation, dataset)


def test_rejects_missing_and_extra_observation_membership():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    object.__setattr__(dataset, "observations", ())
    with pytest.raises(ValueError, match="invalid|observations"):
        create_outcome_evidence_evaluation(interpretation, dataset)

    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    object.__setattr__(
        dataset,
        "observations",
        (dataset.observations[0], _second_observation()),
    )
    with pytest.raises(ValueError, match="invalid|digest|canonical"):
        create_outcome_evidence_evaluation(interpretation, dataset)

    dataset = _dataset()
    interpretation = replace(
        create_outcome_interpretation_snapshot(dataset).results[0],
        source_observation_digest="f" * 64,
    )
    with pytest.raises(ValueError, match="exactly one observation"):
        create_outcome_evidence_evaluation(interpretation, dataset)


def test_rejects_tampered_predecessor_canonical_material():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    object.__setattr__(dataset, "as_of_time", dataset.as_of_time + timedelta(seconds=1))
    with pytest.raises(ValueError, match="invalid|tampered|canonical|dataset digest"):
        create_outcome_evidence_evaluation(interpretation, dataset)

    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    object.__setattr__(interpretation, "candidate_id", "tampered")
    with pytest.raises(ValueError, match="invalid|tampered|canonical|provenance"):
        create_outcome_evidence_evaluation(interpretation, dataset)


def test_cutoff_is_validated_from_the_supplied_t02_snapshot():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    object.__setattr__(
        dataset,
        "as_of_time",
        dataset.as_of_time - timedelta(seconds=1),
    )

    with pytest.raises(ValueError, match="invalid|cutoff|after"):
        create_outcome_evidence_evaluation(interpretation, dataset)


def test_evaluation_does_not_read_the_wall_clock(monkeypatch):
    class ClockGuardMeta(type):
        def __instancecheck__(cls, value):
            return isinstance(value, datetime)

    class ClockGuard(metaclass=ClockGuardMeta):
        @classmethod
        def now(cls, *args, **kwargs):
            raise AssertionError("T04 must not read datetime.now")

        @classmethod
        def utcnow(cls, *args, **kwargs):
            raise AssertionError("T04 must not read datetime.utcnow")

        @classmethod
        def today(cls, *args, **kwargs):
            raise AssertionError("T04 must not read datetime.today")

    monkeypatch.setattr(outcome_evidence_module, "datetime", ClockGuard)
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    result = create_outcome_evidence_evaluation(interpretation, dataset)
    assert result.source_reference_time == dataset.observations[0].simulation_reference_time


def test_public_boundary_has_no_external_or_authority_operations():
    signature = inspect.signature(outcome_evidence_module.evaluate_outcome_evidence)
    assert tuple(signature.parameters) == ("interpretation", "dataset")
    assert not any(
        name.casefold().startswith(
            (
                "aggregate",
                "calculate",
                "classify",
                "fetch",
                "repair",
                "rank",
                "reconcile",
                "update",
            )
        )
        for name in outcome_evidence_module.__all__
    )
    assert "PaperSimulationResult" not in outcome_evidence_module.__dict__
    assert "socket" not in outcome_evidence_module.__dict__
    assert "requests" not in outcome_evidence_module.__dict__
    assert "sqlite3" not in outcome_evidence_module.__dict__


def test_evaluation_preserves_p07_statuses_without_recalculation_or_mutation():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    observation = dataset.observations[0]
    before_dataset = dataset.canonical_representation
    before_interpretation = interpretation.canonical_representation
    result = create_outcome_evidence_evaluation(interpretation, dataset)

    assert result.source_paper_outcome_status == observation.outcome_status
    assert result.source_reconciliation_status == observation.reconciliation_status
    assert result.source_paper_outcome_status != "WIN"
    assert result.source_paper_outcome_status != "LOSS"
    assert dataset.canonical_representation == before_dataset
    assert interpretation.canonical_representation == before_interpretation


def test_rejects_tampered_output_digest_and_forbidden_authority():
    dataset = _dataset()
    result = create_outcome_evidence_evaluation(
        create_outcome_interpretation_snapshot(dataset).results[0],
        dataset,
    )
    with pytest.raises(ValueError, match="result digest"):
        replace(result, result_digest="0" * 64)

    forbidden = (
        "win",
        "loss",
        "profit",
        "profitability",
        "return",
        "expectancy",
        "drawdown",
        "ranking",
        "aggregation",
        "strategy",
        "model_update",
        "decision_override",
        "risk_override",
        "execution",
        "wallet",
        "rpc",
        "provider",
        "reconciliation",
    )
    for name in forbidden:
        assert not hasattr(result, name)


def test_evaluation_does_not_mutate_predecessors():
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    dataset_before = dataset.canonical_representation
    interpretation_before = interpretation.canonical_representation

    create_outcome_evidence_evaluation(interpretation, dataset)

    assert dataset.canonical_representation == dataset_before
    assert interpretation.canonical_representation == interpretation_before