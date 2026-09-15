import pytest

from core.execution import (
    P07_T07_CONTRACT_VERSION,
    PaperSimulationResult,
    PaperSimulationResultHistory,
    PaperSimulationResultHistoryOutcome,
    PaperSimulationResultHistoryResult,
)


def make_result(**overrides):
    values = {
        "input_digest": "1" * 64,
        "fill_digest": "2" * 64,
        "transition_digest": "3" * 64,
        "ledger_digest": "4" * 64,
        "reconciliation_digest": "5" * 64,
        "status": "FILLED",
        "filled_quantity": "10",
        "unfilled_quantity": "0",
        "position_state_digest": "6" * 64,
        "reconciliation_status": "RECONCILED",
    }
    values.update(overrides)
    return PaperSimulationResult(**values)


def test_valid_result_is_stored_and_provenance_is_preserved():
    result = make_result()
    history = PaperSimulationResultHistory()

    stored = history.append(result)

    assert isinstance(stored, PaperSimulationResultHistoryResult)
    assert stored.outcome is PaperSimulationResultHistoryOutcome.STORED
    assert stored.accepted is True
    assert stored.result is result
    assert stored.results == (result,)
    assert history.results == (result,)
    assert history.result_count == 1
    assert history.digest == stored.history_digest
    assert result.status == "FILLED"
    assert result.reconciliation_status == "RECONCILED"
    assert result.input_digest == "1" * 64
    assert result.position_state_digest == "6" * 64


def test_duplicate_does_not_add_or_replace_result():
    result = make_result()
    history = PaperSimulationResultHistory((result,))

    duplicate = history.append(make_result())

    assert duplicate.outcome is PaperSimulationResultHistoryOutcome.INVALID_INPUT
    assert duplicate.accepted is False
    assert duplicate.result is None
    assert duplicate.results == (result,)
    assert duplicate.reason_codes == ("SIMULATION_INPUT_ALREADY_STORED",)
    assert history.result_count == 1


def test_contradictory_result_with_same_simulation_input_is_rejected():
    result = make_result()
    history = PaperSimulationResultHistory((result,))

    contradictory = history.append(
        make_result(
            fill_digest="7" * 64,
            status="FAILED",
            filled_quantity="0",
            unfilled_quantity="10",
        )
    )

    assert contradictory.outcome is PaperSimulationResultHistoryOutcome.INVALID_INPUT
    assert contradictory.accepted is False
    assert contradictory.result is None
    assert contradictory.reason_codes == ("CONTRADICTORY_SIMULATION_INPUT",)
    assert history.results == (result,)


def test_history_order_and_digest_are_deterministic():
    first = make_result(input_digest="a" * 64)
    second = make_result(input_digest="b" * 64)

    left = PaperSimulationResultHistory((first, second))
    right = PaperSimulationResultHistory((second, first))

    assert left.results == right.results
    assert left.digest == right.digest
    assert left.history_digest == right.history_digest


def test_invalid_input_fails_closed_without_mutating_history():
    result = make_result()
    history = PaperSimulationResultHistory((result,))
    original_digest = history.digest

    invalid = history.append(object())

    assert invalid.outcome is PaperSimulationResultHistoryOutcome.INVALID_INPUT
    assert invalid.accepted is False
    assert invalid.result is None
    assert invalid.results == (result,)
    assert history.digest == original_digest
    assert history.results == (result,)


def test_tampered_new_result_is_rejected():
    result = make_result()
    object.__setattr__(result, "status", "NOT_A_RESULT")

    with pytest.raises(ValueError):
        PaperSimulationResultHistory((result,))


def test_tampered_stored_result_fails_closed_on_read():
    result = make_result()
    history = PaperSimulationResultHistory((result,))
    object.__setattr__(result, "status", "FAILED")

    with pytest.raises(ValueError, match="stored result|canonical"):
        history.retrieve()


def test_unsupported_version_is_rejected():
    class UnsupportedResult(PaperSimulationResult):
        @property
        def contract_version(self):
            return "p07-t99-v1"

    result = UnsupportedResult(
        input_digest="1" * 64,
        fill_digest="2" * 64,
        transition_digest="3" * 64,
        ledger_digest="4" * 64,
        reconciliation_digest="5" * 64,
        status="FILLED",
        filled_quantity="10",
        unfilled_quantity="0",
        position_state_digest="6" * 64,
        reconciliation_status="RECONCILED",
    )

    with pytest.raises(ValueError):
        PaperSimulationResultHistory((result,))


def test_history_result_is_immutable_and_has_no_forbidden_semantics():
    result = make_result()
    outcome = PaperSimulationResultHistory().append(result)

    with pytest.raises(Exception):
        outcome.outcome = PaperSimulationResultHistoryOutcome.INVALID_INPUT
    assert not hasattr(outcome, "decision")
    assert not hasattr(outcome, "authorization")
    assert not hasattr(outcome, "execution")
    assert outcome.contract_version == P07_T07_CONTRACT_VERSION