from dataclasses import FrozenInstanceError, replace

import pytest

from core.learning import (
    OutcomeLearningObservation,
    P08_T01_CONTRACT_VERSION,
    P08_T01_EVALUATOR_VERSION,
    create_outcome_learning_observation,
)
from core.execution import PaperSimulationResult, PaperSimulationResultHistory
from tests.test_paper_simulation_input import _input


def _observation() -> OutcomeLearningObservation:
    simulation_input = _input()
    result = PaperSimulationResult(
        input_digest=simulation_input.digest,
        fill_digest="f",
        transition_digest="t",
        ledger_digest="l",
        reconciliation_digest="r",
        status="FILLED",
        filled_quantity="10",
        unfilled_quantity="0",
        position_state_digest="p",
        reconciliation_status="RECONCILED",
    )
    history = PaperSimulationResultHistory((result,))
    return create_outcome_learning_observation(
        simulation_input.decision_intent.intent,
        simulation_input,
        result,
        history,
    )


def test_observation_preserves_one_linked_decision_and_paper_outcome():
    observation = _observation()

    assert isinstance(observation, OutcomeLearningObservation)
    assert observation.decision_intent_digest == observation.decision_intent.digest
    assert observation.simulation_input_digest == observation.simulation_input.digest
    assert observation.paper_result_digest == observation.paper_result.digest
    assert observation.outcome_status == "FILLED"
    assert observation.reconciliation_status == "RECONCILED"
    assert observation.contract_version == P08_T01_CONTRACT_VERSION
    assert observation.evaluator_version == P08_T01_EVALUATOR_VERSION


def test_observation_is_deterministic_and_provenance_is_canonical():
    first = _observation()
    second = _observation()

    assert first.canonical_representation == second.canonical_representation
    assert first.deterministic_representation == first.canonical_representation
    assert first.digest == second.digest
    assert len(first.digest) == 64


def test_observation_rejects_broken_provenance_links():
    observation = _observation()

    with pytest.raises(ValueError, match="not retained"):
        create_outcome_learning_observation(
            observation.decision_intent,
            observation.simulation_input,
            replace(
                observation.paper_result,
                input_digest="0" * 64,
            ),
            PaperSimulationResultHistory((observation.paper_result,)),
        )


def test_observation_rejects_tampered_upstream_records():
    observation = _observation()
    object.__setattr__(observation.decision_intent.context, "candidate_id", "tampered")

    with pytest.raises(ValueError, match="DecisionIntent"):
        create_outcome_learning_observation(
            observation.decision_intent,
            observation.simulation_input,
            observation.paper_result,
            PaperSimulationResultHistory((observation.paper_result,)),
        )


def test_observation_rejects_unsupported_versions():
    with pytest.raises(ValueError, match="contract version"):
        OutcomeLearningObservation(
            decision_intent=_observation().decision_intent,
            simulation_input=_observation().simulation_input,
            paper_result=_observation().paper_result,
            history_results=_observation().history_results,
            history_digest=_observation().history_digest,
            contract_version="p08-t99-v1",
        )


def test_observation_is_immutable_and_has_no_learning_authority():
    observation = _observation()

    with pytest.raises(FrozenInstanceError):
        observation.paper_result = observation.paper_result
    assert not hasattr(observation, "ranking")
    assert not hasattr(observation, "decision")
    assert not hasattr(observation, "authorization")
    assert not hasattr(observation, "execution")
    assert not hasattr(observation, "model_update")
    assert not hasattr(observation, "promotion")