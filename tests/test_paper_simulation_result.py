import pytest

from core.execution.paper_simulation_result import (
    P07_T06_CONTRACT_VERSION,
    PaperSimulationResult,
)


def make_result(**overrides):
    values = {
        "input_digest": "i",
        "fill_digest": "f",
        "transition_digest": "t",
        "ledger_digest": "l",
        "reconciliation_digest": "r",
        "status": "FILLED",
        "filled_quantity": "10",
        "unfilled_quantity": "0",
        "position_state_digest": "p",
        "reconciliation_status": "RECONCILED",
    }
    values.update(overrides)
    return PaperSimulationResult(**values)


def test_contract_version():
    assert make_result().contract_version == P07_T06_CONTRACT_VERSION


def test_immutable():
    with pytest.raises(Exception):
        make_result().status = "FAILED"


def test_invalid_status_rejected():
    with pytest.raises(ValueError):
        make_result(status="SUCCESS")


def test_unknown_reconciliation_preserved():
    result = make_result(reconciliation_status="UNKNOWN")
    assert result.reconciliation_status == "UNKNOWN"


def test_digest_is_deterministic():
    assert make_result().digest == make_result().digest
