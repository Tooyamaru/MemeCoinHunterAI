from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import json
from typing import Literal, get_args, get_origin, get_type_hints

import pytest

import core.learning.outcome_readiness as readiness_module
from core.learning import (
    OutcomeEvidenceEvaluationSnapshot,
    OutcomeEvidenceState,
    OutcomeInterpretationStatus,
    OutcomeLearningReadinessReasonCode,
    OutcomeLearningReadinessResult,
    OutcomeLearningReadinessState,
    P08_T04_CONTRACT_VERSION,
    P08_T04_EVALUATOR_VERSION,
    P08_T05_CONTRACT_VERSION,
    P08_T05_EVALUATOR_VERSION,
    P08_T06_CONTRACT_VERSION,
    P08_T06_EVALUATOR_VERSION,
    create_outcome_evidence_evaluation,
    create_outcome_evidence_evaluation_snapshot,
    create_outcome_interpretation_snapshot,
    create_outcome_learning_dataset_snapshot,
    evaluate_outcome_learning_readiness,
)
from tests.test_outcome_learning import _observation
from tests.test_outcome_learning_dataset import _second_observation


def _dataset(observation_count=1):
    observations = [_observation()]
    if observation_count > 1:
        observations.append(_second_observation())
    return create_outcome_learning_dataset_snapshot(
        tuple(observations),
        observations[0].simulation_reference_time + timedelta(hours=1),
    )


def _snapshot(statuses=(OutcomeInterpretationStatus.UNCLASSIFIED,)):
    dataset = _dataset(len(statuses))
    interpretations = create_outcome_interpretation_snapshot(dataset).results
    evaluations = tuple(
        create_outcome_evidence_evaluation(
            replace(interpretation, interpretation_status=status),
            dataset,
        )
        for interpretation, status in zip(interpretations, statuses)
    )
    return create_outcome_evidence_evaluation_snapshot(dataset, evaluations)


def _digest(value):
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


def test_ready_result_preserves_exact_contract_and_provenance():
    snapshot = _snapshot()
    result = evaluate_outcome_learning_readiness(snapshot)

    assert isinstance(result, OutcomeLearningReadinessResult)
    assert result.source_snapshot_digest == snapshot.snapshot_digest
    assert result.source_dataset_digest == snapshot.source_dataset_digest
    assert result.source_dataset_as_of_time == snapshot.source_dataset_as_of_time
    assert (
        result.readiness_state
        is OutcomeLearningReadinessState.READY_FOR_NON_ECONOMIC_ANALYSIS
    )
    assert result.reason_codes == (
        OutcomeLearningReadinessReasonCode.SOURCE_SNAPSHOT_VALID,
        OutcomeLearningReadinessReasonCode.ALL_T04_STATES_UNCLASSIFIED,
        OutcomeLearningReadinessReasonCode.ANALYSIS_READINESS_GRANTED,
    )
    assert result.source_evaluation_contract_version == P08_T04_CONTRACT_VERSION
    assert result.source_evaluation_evaluator_version == P08_T04_EVALUATOR_VERSION
    assert result.source_snapshot_contract_version == P08_T05_CONTRACT_VERSION
    assert result.source_snapshot_evaluator_version == P08_T05_EVALUATOR_VERSION
    assert result.contract_version == P08_T06_CONTRACT_VERSION
    assert result.evaluator_version == P08_T06_EVALUATOR_VERSION
    assert [field.name for field in fields(result)] == [
        "source_snapshot_digest",
        "source_dataset_digest",
        "source_dataset_as_of_time",
        "readiness_state",
        "reason_codes",
        "source_evaluation_contract_version",
        "source_evaluation_evaluator_version",
        "source_snapshot_contract_version",
        "source_snapshot_evaluator_version",
        "contract_version",
        "evaluator_version",
        "result_digest",
    ]


def test_output_contract_has_exact_public_field_types():
    hints = get_type_hints(OutcomeLearningReadinessResult)

    assert hints["source_snapshot_digest"] is str
    assert hints["source_dataset_digest"] is str
    assert hints["source_dataset_as_of_time"] is datetime
    assert hints["readiness_state"] is OutcomeLearningReadinessState
    assert hints["reason_codes"] == tuple[
        OutcomeLearningReadinessReasonCode,
        ...,
    ]
    assert get_origin(hints["source_evaluation_contract_version"]) is Literal
    assert get_args(hints["source_evaluation_contract_version"]) == (
        P08_T04_CONTRACT_VERSION,
    )
    assert get_origin(hints["source_evaluation_evaluator_version"]) is Literal
    assert get_args(hints["source_evaluation_evaluator_version"]) == (
        P08_T04_EVALUATOR_VERSION,
    )
    assert get_origin(hints["source_snapshot_contract_version"]) is Literal
    assert get_args(hints["source_snapshot_contract_version"]) == (
        P08_T05_CONTRACT_VERSION,
    )
    assert get_origin(hints["source_snapshot_evaluator_version"]) is Literal
    assert get_args(hints["source_snapshot_evaluator_version"]) == (
        P08_T05_EVALUATOR_VERSION,
    )
    assert get_origin(hints["contract_version"]) is Literal
    assert get_args(hints["contract_version"]) == (P08_T06_CONTRACT_VERSION,)
    assert get_origin(hints["evaluator_version"]) is Literal
    assert get_args(hints["evaluator_version"]) == (P08_T06_EVALUATOR_VERSION,)
    assert hints["result_digest"] is str


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (
            OutcomeInterpretationStatus.UNKNOWN,
            OutcomeLearningReadinessReasonCode.T04_UNKNOWN_PRESENT,
        ),
        (
            OutcomeInterpretationStatus.UNAVAILABLE,
            OutcomeLearningReadinessReasonCode.T04_UNAVAILABLE_PRESENT,
        ),
        (
            OutcomeInterpretationStatus.INCOMPLETE,
            OutcomeLearningReadinessReasonCode.T04_INCOMPLETE_PRESENT,
        ),
    ],
)
def test_each_blocking_state_blocks_non_economic_analysis(status, reason):
    result = evaluate_outcome_learning_readiness(_snapshot((status,)))

    assert (
        result.readiness_state
        is OutcomeLearningReadinessState.NOT_READY_FOR_NON_ECONOMIC_ANALYSIS
    )
    assert result.reason_codes == (
        OutcomeLearningReadinessReasonCode.SOURCE_SNAPSHOT_VALID,
        reason,
        OutcomeLearningReadinessReasonCode.ANALYSIS_READINESS_BLOCKED,
    )


def test_multiple_blocking_states_use_fixed_reason_order():
    result = evaluate_outcome_learning_readiness(
        _snapshot(
            (
                OutcomeInterpretationStatus.INCOMPLETE,
                OutcomeInterpretationStatus.UNKNOWN,
            )
        )
    )

    assert result.reason_codes == (
        OutcomeLearningReadinessReasonCode.SOURCE_SNAPSHOT_VALID,
        OutcomeLearningReadinessReasonCode.T04_UNKNOWN_PRESENT,
        OutcomeLearningReadinessReasonCode.T04_INCOMPLETE_PRESENT,
        OutcomeLearningReadinessReasonCode.ANALYSIS_READINESS_BLOCKED,
    )


def test_result_is_deterministic_and_digest_covers_every_semantic_field():
    left = evaluate_outcome_learning_readiness(_snapshot())
    right = evaluate_outcome_learning_readiness(_snapshot())

    assert left.canonical_representation == right.canonical_representation
    assert left.deterministic_representation == left.canonical_representation
    assert left.result_digest == right.result_digest
    assert left.result_digest == _digest(left.canonical_representation)

    canonical = dict(left.canonical_representation)
    assert set(canonical) == {
        "source_snapshot_digest",
        "source_dataset_digest",
        "source_dataset_as_of_time",
        "readiness_state",
        "reason_codes",
        "source_evaluation_contract_version",
        "source_evaluation_evaluator_version",
        "source_snapshot_contract_version",
        "source_snapshot_evaluator_version",
        "contract_version",
        "evaluator_version",
    }
    mutations = {
        "source_snapshot_digest": "0" * 64,
        "source_dataset_digest": "1" * 64,
        "source_dataset_as_of_time": "2030-01-01T00:00:00+00:00",
        "readiness_state": (
            OutcomeLearningReadinessState.NOT_READY_FOR_NON_ECONOMIC_ANALYSIS.value
        ),
        "reason_codes": (
            OutcomeLearningReadinessReasonCode.SOURCE_SNAPSHOT_VALID.value,
            OutcomeLearningReadinessReasonCode.T04_UNKNOWN_PRESENT.value,
            OutcomeLearningReadinessReasonCode.ANALYSIS_READINESS_BLOCKED.value,
        ),
        "source_evaluation_contract_version": "p08-t99-v1",
        "source_evaluation_evaluator_version": "p08-t04-tampered-v1",
        "source_snapshot_contract_version": "p08-t99-v1",
        "source_snapshot_evaluator_version": "p08-t05-tampered-v1",
        "contract_version": "p08-t99-v1",
        "evaluator_version": "p08-t06-tampered-v1",
    }
    for field_name, value in mutations.items():
        tampered = dict(canonical)
        tampered[field_name] = value
        assert _digest(tampered) != left.result_digest, field_name


def test_result_and_canonical_values_are_immutable():
    result = evaluate_outcome_learning_readiness(_snapshot())

    with pytest.raises(FrozenInstanceError):
        result.readiness_state = (
            OutcomeLearningReadinessState.NOT_READY_FOR_NON_ECONOMIC_ANALYSIS
        )
    with pytest.raises(TypeError):
        result.canonical_representation["readiness_state"] = "tampered"
    with pytest.raises(TypeError):
        result.canonical_representation["reason_codes"] = ()
    assert type(result.reason_codes) is tuple


def test_rejects_invalid_snapshot_types_and_versions():
    with pytest.raises(ValueError, match="OutcomeEvidenceEvaluationSnapshot"):
        evaluate_outcome_learning_readiness(object())

    snapshot = _snapshot()
    class SnapshotSubclass(OutcomeEvidenceEvaluationSnapshot):
        pass

    subclass_snapshot = SnapshotSubclass(
        source_dataset_digest=snapshot.source_dataset_digest,
        source_dataset_as_of_time=snapshot.source_dataset_as_of_time,
        evaluations=snapshot.evaluations,
        evaluation_digests=snapshot.evaluation_digests,
        source_evaluation_contract_version=(
            snapshot.source_evaluation_contract_version
        ),
        source_evaluation_evaluator_version=(
            snapshot.source_evaluation_evaluator_version
        ),
        contract_version=snapshot.contract_version,
        evaluator_version=snapshot.evaluator_version,
        snapshot_digest=snapshot.snapshot_digest,
    )
    with pytest.raises(ValueError, match="OutcomeEvidenceEvaluationSnapshot"):
        evaluate_outcome_learning_readiness(subclass_snapshot)

    object.__setattr__(snapshot, "contract_version", "p08-t99-v1")
    with pytest.raises(ValueError, match="snapshot|contract|invalid"):
        evaluate_outcome_learning_readiness(snapshot)

    snapshot = _snapshot()
    object.__setattr__(snapshot, "evaluator_version", "p08-t05-tampered-v1")
    with pytest.raises(ValueError, match="snapshot|evaluator|invalid"):
        evaluate_outcome_learning_readiness(snapshot)


def test_rejects_tampered_snapshot_digest_canonical_material_and_cutoff():
    snapshot = _snapshot()
    object.__setattr__(snapshot, "snapshot_digest", "0" * 64)
    with pytest.raises(ValueError, match="snapshot|digest|invalid"):
        evaluate_outcome_learning_readiness(snapshot)

    snapshot = _snapshot()
    object.__setattr__(
        snapshot,
        "source_dataset_as_of_time",
        snapshot.source_dataset_as_of_time.replace(tzinfo=timezone(timedelta(hours=1))),
    )
    with pytest.raises(ValueError, match="UTC|canonical|Snapshot"):
        evaluate_outcome_learning_readiness(snapshot)

    snapshot = _snapshot()
    evaluation = snapshot.evaluations[0]
    object.__setattr__(evaluation, "evidence_state", "NOT_A_STATE")
    with pytest.raises(ValueError, match="invalid|state|evaluation"):
        evaluate_outcome_learning_readiness(snapshot)


def test_rejects_invalid_reason_codes_and_source_digest():
    snapshot = _snapshot()
    evaluation = snapshot.evaluations[0]
    object.__setattr__(evaluation, "reason_codes", ())
    with pytest.raises(ValueError, match="invalid|reason|evaluation"):
        evaluate_outcome_learning_readiness(snapshot)

    snapshot = _snapshot()
    object.__setattr__(snapshot, "source_dataset_digest", "not-a-digest")
    with pytest.raises(ValueError, match="invalid|digest|snapshot"):
        evaluate_outcome_learning_readiness(snapshot)


def test_does_not_read_wall_clock_or_external_state():
    class ClockGuardMeta(type):
        def __instancecheck__(cls, value):
            return isinstance(value, datetime)

    class ClockGuard(metaclass=ClockGuardMeta):
        @classmethod
        def now(cls, *args, **kwargs):
            raise AssertionError("T06 must not read datetime.now")

        @classmethod
        def utcnow(cls, *args, **kwargs):
            raise AssertionError("T06 must not read datetime.utcnow")

        @classmethod
        def today(cls, *args, **kwargs):
            raise AssertionError("T06 must not read datetime.today")

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(readiness_module, "datetime", ClockGuard)
        result = evaluate_outcome_learning_readiness(_snapshot())
    finally:
        monkeypatch.undo()
    assert (
        result.readiness_state
        is OutcomeLearningReadinessState.READY_FOR_NON_ECONOMIC_ANALYSIS
    )

    forbidden = (
        "win",
        "loss",
        "profit",
        "return",
        "expectancy",
        "drawdown",
        "edge",
        "ranking",
        "model",
        "strategy",
        "execution",
        "wallet",
        "rpc",
        "provider",
        "network",
    )
    for name in forbidden:
        assert not hasattr(result, name)
    assert "socket" not in readiness_module.__dict__
    assert "requests" not in readiness_module.__dict__
    assert "sqlite3" not in readiness_module.__dict__


def test_public_boundary_is_one_pure_snapshot_operation():
    signature = inspect.signature(
        readiness_module.evaluate_outcome_learning_readiness,
    )
    assert tuple(signature.parameters) == ("snapshot",)
    assert set(readiness_module.__all__) == {
        "OutcomeLearningReadinessReasonCode",
        "OutcomeLearningReadinessResult",
        "OutcomeLearningReadinessState",
        "P08_T06_CONTRACT_VERSION",
        "P08_T06_EVALUATOR_VERSION",
        "evaluate_outcome_learning_readiness",
    }
    assert isinstance(_snapshot(), OutcomeEvidenceEvaluationSnapshot)


def test_readiness_does_not_mutate_t05_predecessor_or_add_authority():
    snapshot = _snapshot()
    before = snapshot.canonical_representation

    evaluate_outcome_learning_readiness(snapshot)

    assert snapshot.canonical_representation == before
    assert not hasattr(
        OutcomeLearningReadinessResult,
        "source_snapshot",
    )