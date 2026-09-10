"""Focused contract tests for the G1 implementation surface."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from core.execution import PaperSimulationResult, PaperSimulationResultHistory
from core.execution.paper_ledger import create_paper_ledger_entry
from core.execution.paper_reconciliation import reconcile_paper_ledger
from core.learning import (
    create_outcome_evidence_evaluation,
    create_outcome_evidence_evaluation_snapshot,
    create_outcome_interpretation_snapshot,
    create_outcome_learning_dataset_snapshot,
    create_outcome_learning_observation,
    evaluate_outcome_learning_readiness,
)
from core.learning.g1_simulation_only_economic_authority import (
    G1AuthorityAReference,
    G1FinalityState,
    G1P07HistorySnapshot,
    G1P07Predecessors,
    G1P08Predecessors,
    G1ReasonCode,
    G1RecognitionState,
    G1SimulationOnlyEconomicAuthorityInput,
    evaluate_g1,
    _canonical_json,
    _first,
    _sha256,
)
from tests.test_paper_ledger import _bundle
from tests.test_paper_reconciliation import _expectation


def _real_p06_p07_p08_chain() -> G1SimulationOnlyEconomicAuthorityInput:
    simulation_input, fill_outcome, transition, ledger_entry = _bundle()
    reconciliation = reconcile_paper_ledger(
        (ledger_entry,),
        _expectation(ledger_entry),
    )
    paper_result = PaperSimulationResult(
        input_digest=simulation_input.digest,
        fill_digest=fill_outcome.outcome_digest,
        transition_digest=transition.transition_digest,
        ledger_digest=ledger_entry.entry_digest,
        reconciliation_digest=reconciliation.result_digest,
        status=fill_outcome.status.value,
        filled_quantity=str(fill_outcome.filled_quantity),
        unfilled_quantity=str(fill_outcome.remaining_quantity),
        position_state_digest=transition.next_state.digest,
        reconciliation_status="RECONCILED",
    )
    history = PaperSimulationResultHistory((paper_result,))
    observation = create_outcome_learning_observation(
        simulation_input.decision_intent.intent,
        simulation_input,
        paper_result,
        history,
    )
    dataset = create_outcome_learning_dataset_snapshot(
        (observation,),
        simulation_input.simulation_reference_time,
    )
    interpretation = create_outcome_interpretation_snapshot(dataset).results[0]
    evaluation = create_outcome_evidence_evaluation(interpretation, dataset)
    evaluation_snapshot = create_outcome_evidence_evaluation_snapshot(
        dataset,
        (evaluation,),
    )
    readiness = evaluate_outcome_learning_readiness(evaluation_snapshot)
    return G1SimulationOnlyEconomicAuthorityInput(
        authority_a=G1AuthorityAReference(
            "subject-1",
            "lifecycle-1",
            "authority-a",
            "authority-a-v1",
        ),
        p06=simulation_input.decision_intent.intent,
        p07=G1P07Predecessors(
            simulation_input,
            fill_outcome,
            transition,
            (ledger_entry,),
            reconciliation,
            paper_result,
        ),
        p07_history=G1P07HistorySnapshot.from_results((paper_result,)),
        p08=G1P08Predecessors(
            observation,
            dataset,
            interpretation,
            evaluation,
            evaluation_snapshot,
            readiness,
        ),
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


def test_real_p06_p07_p08_chain_is_recognized() -> None:
    result = evaluate_g1(_real_p06_p07_p08_chain())

    assert result is not None
    assert result.recognition_state is G1RecognitionState.RECOGNIZED
    assert result.finality_state is G1FinalityState.FINAL
    assert result.reason_code is G1ReasonCode.RECOGNIZED_COMPLETE
    assert len(result.provenance) == 15


def test_canonicalization_is_order_and_unicode_stable() -> None:
    left = {
        "b": "e\u0301",
        "a": {"z": 1, "y": True},
    }
    right = {
        "a": {"y": True, "z": 1},
        "b": "é",
    }

    assert _canonical_json(left) == _canonical_json(right)
    assert _sha256(left) == _sha256(right)


def test_equivalent_unicode_authority_references_replay_identically() -> None:
    decomposed = _real_p06_p07_p08_chain()
    composed = _real_p06_p07_p08_chain()
    decomposed = replace(
        decomposed,
        authority_a=G1AuthorityAReference(
            "e\u0301-subject",
            "e\u0301-lifecycle",
            "authority-a",
            "authority-a-v1",
        ),
    )
    composed = replace(
        composed,
        authority_a=G1AuthorityAReference(
            "é-subject",
            "é-lifecycle",
            "authority-a",
            "authority-a-v1",
        ),
    )

    first = evaluate_g1(decomposed)
    second = evaluate_g1(composed)

    assert first is not None
    assert second is not None
    assert first.canonical_representation == second.canonical_representation
    assert first.result_identity == second.result_identity
    assert first.result_digest == second.result_digest


def test_predecessor_digest_tampering_fails_closed() -> None:
    value = _real_p06_p07_p08_chain()
    object.__setattr__(value.p07.p07_t01, "input_digest", "0" * 64)

    result = evaluate_g1(value)

    assert result is not None
    assert result.recognition_state is G1RecognitionState.NOT_RECOGNIZED
    assert result.finality_state is G1FinalityState.NOT_APPLICABLE
    assert result.reason_code is G1ReasonCode.INVALID_CANONICAL_REPRESENTATION


def test_result_identity_and_digest_change_for_semantic_lifecycle_change() -> None:
    original = evaluate_g1(_real_p06_p07_p08_chain())
    changed_input = _real_p06_p07_p08_chain()
    changed_input = replace(
        changed_input,
        authority_a=G1AuthorityAReference(
            "subject-2",
            "lifecycle-2",
            "authority-a",
            "authority-a-v1",
        ),
    )
    changed = evaluate_g1(changed_input)

    assert original is not None
    assert changed is not None
    assert original.recognition_state is G1RecognitionState.RECOGNIZED
    assert changed.recognition_state is G1RecognitionState.RECOGNIZED
    assert original.result_identity != changed.result_identity
    assert original.result_digest != changed.result_digest


def test_result_digest_and_identity_reject_tampering() -> None:
    result = evaluate_g1(_real_p06_p07_p08_chain())

    assert result is not None
    canonical_without_digest = {
        key: value
        for key, value in result.canonical_representation.items()
        if key != "result_digest"
    }
    assert result.result_digest == _sha256(canonical_without_digest)

    with pytest.raises(ValueError, match="result_identity"):
        replace(result, result_identity="0" * 64)
    with pytest.raises(ValueError, match="result_digest"):
        replace(result, result_digest="0" * 64)


def test_provenance_is_complete_and_caller_mutation_cannot_change_result() -> None:
    result = evaluate_g1(_real_p06_p07_p08_chain())

    assert result is not None
    assert tuple(link.stage for link in result.provenance) == (
        "p06_decision_intent",
        "p07_simulation_input",
        "p07_fill_outcome",
        "p07_position_exposure",
        "p07_ledger",
        "p07_reconciliation",
        "p07_simulation_result",
        "p07_history",
        "p08_t01_observation",
        "p08_t02_dataset",
        "p08_t03_interpretation",
        "p08_t04_evaluation",
        "p08_t05_snapshot",
        "p08_t06_readiness",
        "authority_a_identity",
    )
    assert all(len(link.record_digest) == 64 for link in result.provenance)

    original_reason = result.reason_code
    caller_view = result.canonical_representation
    caller_view["reason_code"] = G1ReasonCode.INVALID_TYPE.value
    assert result.reason_code is original_reason

    with pytest.raises(FrozenInstanceError):
        result.reason_code = G1ReasonCode.INVALID_TYPE  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.provenance[0].stage = "tampered"  # type: ignore[misc]


def test_equivalent_duplicate_lifecycles_replay_to_identical_results() -> None:
    first = evaluate_g1(_real_p06_p07_p08_chain())
    second = evaluate_g1(_real_p06_p07_p08_chain())

    assert first is not None
    assert second is not None
    assert first.recognition_state is second.recognition_state
    assert first.finality_state is second.finality_state
    assert first.reason_code is second.reason_code
    assert first.canonical_representation == second.canonical_representation
    assert first.result_identity == second.result_identity
    assert first.result_digest == second.result_digest


def test_contradictory_history_digest_fails_closed() -> None:
    value = _real_p06_p07_p08_chain()
    object.__setattr__(value.p07_history, "history_digest", "0" * 64)

    result = evaluate_g1(value)

    assert result is not None
    assert result.recognition_state is G1RecognitionState.NOT_RECOGNIZED
    assert result.finality_state is G1FinalityState.NOT_APPLICABLE
    assert result.reason_code is G1ReasonCode.DIGEST_FAILURE


def test_t02_cutoff_is_preserved_as_the_sole_cutoff() -> None:
    value = _real_p06_p07_p08_chain()
    result = evaluate_g1(value)

    assert result is not None
    assert result.dataset_as_of_time == value.p08.p08_t02.as_of_time
    assert result.dataset_as_of_time.tzinfo is timezone.utc


def test_future_inconsistent_cutoff_material_fails_closed() -> None:
    value = _real_p06_p07_p08_chain()
    cutoff = value.p08.p08_t02.as_of_time
    object.__setattr__(
        value.p08.p08_t02,
        "as_of_time",
        cutoff - timedelta(seconds=1),
    )

    result = evaluate_g1(value)

    assert result is not None
    assert result.recognition_state is G1RecognitionState.NOT_RECOGNIZED
    assert result.finality_state is G1FinalityState.NOT_APPLICABLE
    assert result.reason_code is G1ReasonCode.INVALID_CANONICAL_REPRESENTATION


def test_timezone_invalid_cutoff_fails_closed() -> None:
    value = _real_p06_p07_p08_chain()
    object.__setattr__(
        value.p08.p08_t02,
        "as_of_time",
        datetime(2026, 1, 1),
    )

    result = evaluate_g1(value)

    assert result is None


def test_repeated_evaluation_replays_all_result_semantics() -> None:
    value = _real_p06_p07_p08_chain()
    first = evaluate_g1(value)
    second = evaluate_g1(value)

    assert first is not None
    assert second is not None
    assert (
        first.recognition_state,
        first.finality_state,
        first.reason_code,
        first.canonical_representation,
        first.result_identity,
        first.result_digest,
        first.dataset_as_of_time,
        first.provenance,
    ) == (
        second.recognition_state,
        second.finality_state,
        second.reason_code,
        second.canonical_representation,
        second.result_identity,
        second.result_digest,
        second.dataset_as_of_time,
        second.provenance,
    )


@pytest.mark.parametrize(
    ("earlier", "later"),
    [
        (earlier, later)
        for index, earlier in enumerate(tuple(G1ReasonCode)[1:])
        for later in tuple(G1ReasonCode)[index + 2 :]
    ],
)
def test_complete_reason_precedence_is_deterministic(
    earlier: G1ReasonCode,
    later: G1ReasonCode,
) -> None:
    assert _first({earlier, later}) is earlier


def test_all_reason_precedence_selects_invalid_type_first() -> None:
    assert _first(set(tuple(G1ReasonCode)[1:])) is G1ReasonCode.INVALID_TYPE
