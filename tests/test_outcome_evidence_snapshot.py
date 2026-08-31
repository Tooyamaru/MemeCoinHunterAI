from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta
import hashlib
import inspect
import json
from typing import Literal, get_args, get_origin, get_type_hints

import pytest

import core.learning.outcome_evidence_snapshot as snapshot_module
from core.learning import (
    OutcomeEvidenceEvaluationResult,
    OutcomeEvidenceEvaluationSnapshot,
    OutcomeEvidenceState,
    OutcomeInterpretationStatus,
    P08_T02_CONTRACT_VERSION,
    P08_T04_CONTRACT_VERSION,
    P08_T04_EVALUATOR_VERSION,
    P08_T05_CONTRACT_VERSION,
    P08_T05_EVALUATOR_VERSION,
    create_outcome_evidence_evaluation,
    create_outcome_evidence_evaluation_snapshot,
    create_outcome_interpretation_snapshot,
    create_outcome_learning_dataset_snapshot,
)
from tests.test_outcome_evidence import _dataset
from tests.test_outcome_learning_dataset import _second_observation
from tests.test_outcome_learning import _observation


def _two_observation_dataset():
    first = _observation()
    second = _second_observation()
    return create_outcome_learning_dataset_snapshot(
        (first, second),
        first.simulation_reference_time + timedelta(hours=1),
    )


def _evaluations(dataset):
    interpretation = create_outcome_interpretation_snapshot(dataset)
    return tuple(
        create_outcome_evidence_evaluation(result, dataset)
        for result in interpretation.results
    )


def _evaluation_digest(value):
    canonical = {
        key: item for key, item in value.canonical_representation.items()
    }
    return hashlib.sha256(
        json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def test_snapshot_preserves_complete_membership_and_exact_contract():
    dataset = _two_observation_dataset()
    evaluations = _evaluations(dataset)

    snapshot = create_outcome_evidence_evaluation_snapshot(
        dataset,
        tuple(reversed(evaluations)),
    )

    assert isinstance(snapshot, OutcomeEvidenceEvaluationSnapshot)
    assert snapshot.source_dataset_digest == dataset.digest
    assert snapshot.source_dataset_as_of_time == dataset.as_of_time
    assert snapshot.evaluations == tuple(
        sorted(evaluations, key=lambda value: value.source_observation_digest)
    )
    assert snapshot.evaluation_digests == tuple(
        value.result_digest for value in snapshot.evaluations
    )
    assert snapshot.source_evaluation_contract_version == P08_T04_CONTRACT_VERSION
    assert snapshot.source_evaluation_evaluator_version == P08_T04_EVALUATOR_VERSION
    assert snapshot.contract_version == P08_T05_CONTRACT_VERSION
    assert snapshot.evaluator_version == P08_T05_EVALUATOR_VERSION
    assert [field.name for field in fields(snapshot)] == [
        "source_dataset_digest",
        "source_dataset_as_of_time",
        "evaluations",
        "evaluation_digests",
        "source_evaluation_contract_version",
        "source_evaluation_evaluator_version",
        "contract_version",
        "evaluator_version",
        "snapshot_digest",
    ]


def test_snapshot_output_contract_has_exact_public_field_types():
    dataset = _dataset()
    snapshot = create_outcome_evidence_evaluation_snapshot(
        dataset,
        _evaluations(dataset),
    )
    hints = get_type_hints(OutcomeEvidenceEvaluationSnapshot)

    assert hints["source_dataset_digest"] is str
    assert hints["source_dataset_as_of_time"] is datetime
    assert hints["evaluations"] == tuple[
        OutcomeEvidenceEvaluationResult,
        ...,
    ]
    assert hints["evaluation_digests"] == tuple[str, ...]
    assert get_origin(hints["source_evaluation_contract_version"]) is Literal
    assert get_args(hints["source_evaluation_contract_version"]) == (
        P08_T04_CONTRACT_VERSION,
    )
    assert get_origin(hints["source_evaluation_evaluator_version"]) is Literal
    assert get_args(hints["source_evaluation_evaluator_version"]) == (
        P08_T04_EVALUATOR_VERSION,
    )
    assert get_origin(hints["contract_version"]) is Literal
    assert get_args(hints["contract_version"]) == (P08_T05_CONTRACT_VERSION,)
    assert get_origin(hints["evaluator_version"]) is Literal
    assert get_args(hints["evaluator_version"]) == (P08_T05_EVALUATOR_VERSION,)
    assert hints["snapshot_digest"] is str


def test_snapshot_rejects_empty_and_non_tuple_inputs():
    dataset = _dataset()
    evaluation = _evaluations(dataset)[0]

    with pytest.raises(ValueError, match="at least one"):
        create_outcome_evidence_evaluation_snapshot(dataset, ())
    with pytest.raises(ValueError, match="exact tuple"):
        create_outcome_evidence_evaluation_snapshot(dataset, [evaluation])
    with pytest.raises(ValueError, match="exact tuple"):
        create_outcome_evidence_evaluation_snapshot(dataset, {evaluation})
    with pytest.raises(ValueError, match="exact tuple"):
        create_outcome_evidence_evaluation_snapshot(
            dataset,
            (item for item in (evaluation,)),
        )


def test_snapshot_order_and_digest_are_replayable():
    dataset = _two_observation_dataset()
    evaluations = _evaluations(dataset)

    left = create_outcome_evidence_evaluation_snapshot(dataset, evaluations)
    right = create_outcome_evidence_evaluation_snapshot(
        dataset,
        tuple(reversed(evaluations)),
    )

    assert left.evaluations == right.evaluations
    assert left.evaluation_digests == right.evaluation_digests
    assert left.canonical_representation == right.canonical_representation
    assert left.deterministic_representation == left.canonical_representation
    assert left.snapshot_digest == right.snapshot_digest
    assert left.evaluations[0].source_observation_digest < (
        left.evaluations[1].source_observation_digest
    )


def test_snapshot_digest_covers_every_semantic_field():
    dataset = _dataset()
    snapshot = create_outcome_evidence_evaluation_snapshot(
        dataset,
        _evaluations(dataset),
    )

    def plain(value):
        if isinstance(value, dict):
            return {key: plain(item) for key, item in value.items()}
        if hasattr(value, "items"):
            return {key: plain(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return [plain(item) for item in value]
        return value

    def digest(value):
        return hashlib.sha256(
            json.dumps(
                plain(value),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()

    canonical = dict(snapshot.canonical_representation)
    assert set(canonical) == {
        "source_dataset_digest",
        "source_dataset_as_of_time",
        "evaluations",
        "evaluation_digests",
        "source_evaluation_contract_version",
        "source_evaluation_evaluator_version",
        "contract_version",
        "evaluator_version",
    }
    assert snapshot.snapshot_digest == digest(canonical)

    mutations = {
        "source_dataset_digest": "0" * 64,
        "source_dataset_as_of_time": "2030-01-01T00:00:00+00:00",
        "evaluations": (),
        "evaluation_digests": (),
        "source_evaluation_contract_version": "p08-t99-v1",
        "source_evaluation_evaluator_version": "p08-t04-tampered-v1",
        "contract_version": "p08-t99-v1",
        "evaluator_version": "p08-t05-tampered-v1",
    }
    for field_name, value in mutations.items():
        tampered = dict(canonical)
        tampered[field_name] = value
        assert digest(tampered) != snapshot.snapshot_digest, field_name


@pytest.mark.parametrize(
    "status",
    list(OutcomeInterpretationStatus),
)
def test_snapshot_preserves_all_four_evidence_states(status):
    dataset = _dataset()
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    interpretation = replace(
        interpretation,
        interpretation_status=status,
    )
    evaluation = create_outcome_evidence_evaluation(interpretation, dataset)

    snapshot = create_outcome_evidence_evaluation_snapshot(
        dataset,
        (evaluation,),
    )

    assert snapshot.evaluations[0].evidence_state is OutcomeEvidenceState(
        status.value
    )


def test_snapshot_and_nested_values_are_immutable():
    dataset = _dataset()
    snapshot = create_outcome_evidence_evaluation_snapshot(
        dataset,
        _evaluations(dataset),
    )

    with pytest.raises(FrozenInstanceError):
        snapshot.snapshot_digest = "0" * 64
    with pytest.raises(TypeError):
        snapshot.canonical_representation["evaluations"] = ()
    with pytest.raises(TypeError):
        snapshot.canonical_representation["evaluations"][0][
            "evidence_state"
        ] = "UNKNOWN"
    assert type(snapshot.evaluations) is tuple
    assert type(snapshot.evaluation_digests) is tuple


def test_snapshot_rejects_t02_and_t04_version_or_digest_tampering():
    dataset = _dataset()
    evaluation = _evaluations(dataset)[0]

    object.__setattr__(dataset, "contract_version", "p08-t99-v1")
    with pytest.raises(ValueError, match="T02|dataset|invalid"):
        create_outcome_evidence_evaluation_snapshot(dataset, (evaluation,))

    dataset = _dataset()
    evaluation = _evaluations(dataset)[0]
    object.__setattr__(evaluation, "contract_version", "p08-t99-v1")
    with pytest.raises(ValueError, match="T04|evaluation|invalid"):
        create_outcome_evidence_evaluation_snapshot(dataset, (evaluation,))

    dataset = _dataset()
    evaluation = _evaluations(dataset)[0]
    object.__setattr__(evaluation, "evaluator_version", "p08-t99-evaluator-v1")
    with pytest.raises(ValueError, match="T04|evaluation|invalid"):
        create_outcome_evidence_evaluation_snapshot(dataset, (evaluation,))

    dataset = _dataset()
    evaluation = _evaluations(dataset)[0]
    object.__setattr__(evaluation, "result_digest", "0" * 64)
    with pytest.raises(ValueError, match="digest|evaluation|invalid"):
        create_outcome_evidence_evaluation_snapshot(dataset, (evaluation,))


def test_snapshot_rejects_wrong_dataset_and_duplicate_evaluations():
    dataset = _dataset()
    wrong_dataset = _two_observation_dataset()
    wrong_evaluation = _evaluations(wrong_dataset)[0]
    with pytest.raises(ValueError, match="dataset"):
        create_outcome_evidence_evaluation_snapshot(
            dataset,
            (wrong_evaluation,),
        )

    with pytest.raises(ValueError, match="duplicate"):
        create_outcome_evidence_evaluation_snapshot(
            _two_observation_dataset(),
            tuple(
                _evaluations(_two_observation_dataset())[:1]
            )
            * 2,
        )


def test_snapshot_rejects_missing_and_extra_membership():
    dataset = _two_observation_dataset()
    evaluations = _evaluations(dataset)

    with pytest.raises(ValueError, match="missing|membership"):
        create_outcome_evidence_evaluation_snapshot(
            dataset,
            (evaluations[0],),
        )

    extra = evaluations[0]
    object.__setattr__(extra, "source_observation_digest", "f" * 64)
    object.__setattr__(extra, "result_digest", _evaluation_digest(extra))
    with pytest.raises(ValueError, match="extra|member"):
        create_outcome_evidence_evaluation_snapshot(
            dataset,
            (extra, evaluations[1]),
        )


def test_snapshot_rejects_provenance_and_cutoff_violations():
    dataset = _dataset()
    evaluation = _evaluations(dataset)[0]
    object.__setattr__(evaluation, "source_candidate_id", "different")
    object.__setattr__(evaluation, "result_digest", _evaluation_digest(evaluation))
    with pytest.raises(ValueError, match="provenance"):
        create_outcome_evidence_evaluation_snapshot(dataset, (evaluation,))

    dataset = _dataset()
    evaluation = _evaluations(dataset)[0]
    object.__setattr__(
        evaluation,
        "source_reference_time",
        dataset.as_of_time + timedelta(seconds=1),
    )
    object.__setattr__(evaluation, "result_digest", _evaluation_digest(evaluation))
    with pytest.raises(ValueError, match="provenance|cutoff"):
        create_outcome_evidence_evaluation_snapshot(dataset, (evaluation,))


def test_snapshot_rejects_invalid_member_and_tampered_snapshot_digest():
    dataset = _dataset()
    evaluation = _evaluations(dataset)[0]

    with pytest.raises(ValueError, match="OutcomeEvidenceEvaluationResult"):
        create_outcome_evidence_evaluation_snapshot(dataset, (object(),))

    snapshot = create_outcome_evidence_evaluation_snapshot(
        dataset,
        (evaluation,),
    )
    with pytest.raises(ValueError, match="snapshot digest"):
        replace(snapshot, snapshot_digest="0" * 64)


def test_snapshot_rejects_tampered_t04_semantic_predecessor():
    dataset = _dataset()
    evaluation = _evaluations(dataset)[0]
    object.__setattr__(
        evaluation,
        "source_interpretation_digest",
        "0" * 64,
    )

    with pytest.raises(ValueError, match="invalid|tampered|canonical|digest"):
        create_outcome_evidence_evaluation_snapshot(dataset, (evaluation,))


def test_snapshot_does_not_read_the_wall_clock(monkeypatch):
    class ClockGuardMeta(type):
        def __instancecheck__(cls, value):
            return isinstance(value, datetime)

    class ClockGuard(metaclass=ClockGuardMeta):
        @classmethod
        def now(cls, *args, **kwargs):
            raise AssertionError("T05 must not read datetime.now")

        @classmethod
        def utcnow(cls, *args, **kwargs):
            raise AssertionError("T05 must not read datetime.utcnow")

        @classmethod
        def today(cls, *args, **kwargs):
            raise AssertionError("T05 must not read datetime.today")

    dataset = _dataset()
    evaluations = _evaluations(dataset)
    monkeypatch.setattr(snapshot_module, "datetime", ClockGuard)
    snapshot = create_outcome_evidence_evaluation_snapshot(
        dataset,
        evaluations,
    )
    assert snapshot.source_dataset_as_of_time == dataset.as_of_time


def test_snapshot_has_no_economic_or_external_authority():
    dataset = _dataset()
    snapshot = create_outcome_evidence_evaluation_snapshot(
        dataset,
        _evaluations(dataset),
    )

    forbidden = (
        "win",
        "loss",
        "profit",
        "return",
        "expectancy",
        "drawdown",
        "ranking",
        "comparison",
        "selection",
        "model",
        "strategy",
        "execution",
        "reconciliation",
        "ledger",
        "wallet",
        "rpc",
        "provider",
        "database",
        "network",
    )
    for name in forbidden:
        assert not hasattr(snapshot, name)


def test_snapshot_public_boundary_has_no_external_or_authority_operations():
    signature = inspect.signature(
        snapshot_module.create_outcome_evidence_evaluation_snapshot,
    )
    assert tuple(signature.parameters) == ("dataset", "evaluations")
    assert not any(
        name.casefold().startswith(
            (
                "aggregate",
                "calculate",
                "compare",
                "fetch",
                "rank",
                "repair",
                "select",
                "update",
            )
        )
        for name in snapshot_module.__all__
    )
    assert "PaperSimulationResult" not in snapshot_module.__dict__
    assert "socket" not in snapshot_module.__dict__
    assert "requests" not in snapshot_module.__dict__
    assert "sqlite3" not in snapshot_module.__dict__


def test_snapshot_preserves_t04_and_p07_ownership_without_mutation():
    dataset = _dataset()
    evaluations = _evaluations(dataset)
    before_dataset = dataset.canonical_representation
    before_evaluations = tuple(
        evaluation.canonical_representation for evaluation in evaluations
    )

    snapshot = create_outcome_evidence_evaluation_snapshot(
        dataset,
        evaluations,
    )

    assert snapshot.evaluations == evaluations
    assert all(
        evaluation.source_paper_outcome_status
        not in {"WIN", "LOSS", "PROFIT", "LOSS_AMOUNT"}
        for evaluation in snapshot.evaluations
    )
    assert dataset.canonical_representation == before_dataset
    assert tuple(
        evaluation.canonical_representation
        for evaluation in evaluations
    ) == before_evaluations