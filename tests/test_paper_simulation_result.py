from decimal import Decimal

import pytest

from core.execution.paper_fill_outcome import FillOutcomeStatus
from core.execution.paper_simulation_result import (
    P07_T06_CONTRACT_VERSION,
    PaperSimulationResult,
)
from core.execution.paper_reconciliation import reconcile_paper_ledger
from tests.test_paper_fill_outcome import _evaluate
from tests.test_paper_ledger import _bundle
from tests.test_paper_reconciliation import _expectation


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


def test_partial_fill_maps_to_owned_t06_status_without_mutating_t02():
    outcome = _evaluate(executable_liquidity=Decimal("1"))
    simulation_input, outcome, transition, ledger = _bundle(outcome=outcome)
    reconciliation = reconcile_paper_ledger((ledger,), _expectation(ledger))

    result = PaperSimulationResult.from_predecessors(
        simulation_input=simulation_input,
        fill_outcome=outcome,
        transition=transition,
        ledger_entries=(ledger,),
        reconciliation=reconciliation,
    )

    assert outcome.status is FillOutcomeStatus.PARTIALLY_FILLED
    assert result.status == "PARTIAL"
