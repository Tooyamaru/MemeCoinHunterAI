"""Focused contract tests for the G1 implementation surface."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

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