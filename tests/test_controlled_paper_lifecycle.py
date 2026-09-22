from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal

import pytest

from core.decision import DecisionEvaluationRuleset
from core.execution.paper_fill_outcome import (
    FillOutcomeStatus,
    TradeSide,
    evaluate_paper_fill,
)
from core.execution.paper_ledger import create_paper_ledger_entry
from core.execution.paper_position_exposure_state import (
    TransitionStatus,
    ValuationContext,
    transition_paper_state,
)
from core.execution.paper_reconciliation import ReconciliationStatus
from core.runtime import (
    ControlledPaperLifecycleOutcome,
    PaperFillInstruction,
    PaperLifecycleEvidence,
    prepare_controlled_paper_run,
    run_controlled_paper_lifecycle,
)
from tests.test_controlled_paper_run_admission import _facts
from tests.test_g1_simulation_only_economic_authority import _paper_state
from tests.test_paper_fill_outcome import _friction
from tests.test_paper_ledger import ASSET, STREAM, _accounting, _valuation
from tests.test_paper_reconciliation import _expectation


def _ready_admission():
    facts, _ = _facts()
    return prepare_controlled_paper_run(**facts)


def _instruction(admission, **overrides):
    reference = admission.paper_simulation_input.simulation_reference_time
    values = {
        "side": TradeSide.BUY,
        "requested_quantity": Decimal("2"),
        "quantity_unit": "TOKEN",
        "price_unit": "QUOTE_PER_TOKEN",
        "fee_unit": "QUOTE",
        "quote_currency": "QUOTE",
        "executable_liquidity": Decimal("2"),
        "reference_quote_price": Decimal("100"),
        "quote_observation_time": reference - timedelta(seconds=2),
        "fill_time": reference - timedelta(seconds=1),
        "friction": _friction(),
    }
    values.update(overrides)
    return PaperFillInstruction(**values)


def _evidence(admission, instruction, *, expectation_fields=None):
    simulation_input = admission.paper_simulation_input
    reference = simulation_input.simulation_reference_time
    valuation = replace(
        _valuation(),
        observed_at=reference - timedelta(seconds=2),
        availability_time=reference - timedelta(seconds=1),
        observation_digest=None,
    )
    accounting = replace(
        _accounting(),
        observed_at=reference - timedelta(seconds=3),
        availability_time=reference - timedelta(seconds=2),
        context_digest=None,
    )
    prior_state = _paper_state(reference)
    fill = evaluate_paper_fill(
        simulation_input,
        side=instruction.side,
        requested_quantity=instruction.requested_quantity,
        quantity_unit=instruction.quantity_unit,
        price_unit=instruction.price_unit,
        fee_unit=instruction.fee_unit,
        quote_currency=instruction.quote_currency,
        executable_liquidity=instruction.executable_liquidity,
        reference_quote_price=instruction.reference_quote_price,
        quote_observation_time=instruction.quote_observation_time,
        fill_time=instruction.fill_time,
        friction=instruction.friction,
        available_inventory=instruction.available_inventory,
    )
    transition = transition_paper_state(
        fill,
        prior_state,
        target_asset_identity=ASSET,
        valuation_context=ValuationContext((valuation,)),
        accounting_context=accounting,
        transition_reference_time=reference,
    )
    ledger = create_paper_ledger_entry(
        simulation_input,
        fill,
        transition,
        ledger_stream_identity=STREAM,
        sequence_number=1,
        previous_entry_digest=None,
        ledger_reference_time=reference,
    )
    expectation = _expectation(ledger, **(expectation_fields or {}))
    return PaperLifecycleEvidence(
        prior_state=prior_state,
        target_asset_identity=ASSET,
        valuation_context=ValuationContext((valuation,)),
        accounting_context=accounting,
        lifecycle_reference_time=reference,
        ledger_stream_identity=STREAM,
        sequence_number=1,
        previous_entry_digest=None,
        reconciliation_expectation=expectation,
    )


def test_ready_admission_reaches_one_linked_p08_observation():
    admission = _ready_admission()
    instruction = _instruction(admission)
    evidence = _evidence(admission, instruction)

    result = run_controlled_paper_lifecycle(
        admission,
        fill_instruction=instruction,
        lifecycle_evidence=evidence,
    )

    assert result.outcome is ControlledPaperLifecycleOutcome.OBSERVATION_PRODUCED
    assert result.reason_codes == ()
    assert result.fill_outcome.status is FillOutcomeStatus.FILLED
    assert (
        result.transition.outcome_identity["outcome_digest"]
        == result.fill_outcome.outcome_digest
    )
    assert result.ledger_entry.transition_identity["transition_digest"] == result.transition.digest
    assert result.reconciliation.status is ReconciliationStatus.MATCH
    assert result.paper_result.ledger_digest == result.ledger_entry.entry_digest
    assert result.history_result.results == (result.paper_result,)
    assert result.observation.paper_result_digest == result.paper_result.digest


def test_partial_fill_maps_only_t06_status_and_still_produces_observation():
    admission = _ready_admission()
    instruction = _instruction(admission, executable_liquidity=Decimal("1"))
    evidence = _evidence(admission, instruction)

    result = run_controlled_paper_lifecycle(
        admission,
        fill_instruction=instruction,
        lifecycle_evidence=evidence,
    )

    assert result.outcome is ControlledPaperLifecycleOutcome.OBSERVATION_PRODUCED
    assert result.fill_outcome.status is FillOutcomeStatus.PARTIALLY_FILLED
    assert result.paper_result.status == "PARTIAL"
    assert result.observation.outcome_status == "PARTIAL"


def test_failed_fill_remains_non_economic_observation_without_state_change():
    admission = _ready_admission()
    instruction = _instruction(admission, executable_liquidity=Decimal("0"))
    evidence = _evidence(admission, instruction)

    result = run_controlled_paper_lifecycle(
        admission,
        fill_instruction=instruction,
        lifecycle_evidence=evidence,
    )

    assert result.outcome is ControlledPaperLifecycleOutcome.OBSERVATION_PRODUCED
    assert result.fill_outcome.status is FillOutcomeStatus.FAILED
    assert result.transition.transition_status is TransitionStatus.NO_CHANGE
    assert result.paper_result.status == "FAILED"
    assert result.observation.outcome_status == "FAILED"


def test_unavailable_fill_remains_non_economic_observation():
    admission = _ready_admission()
    instruction = _instruction(admission, friction=_friction(slippage=None))
    evidence = _evidence(admission, instruction)

    result = run_controlled_paper_lifecycle(
        admission,
        fill_instruction=instruction,
        lifecycle_evidence=evidence,
    )

    assert result.outcome is ControlledPaperLifecycleOutcome.OBSERVATION_PRODUCED
    assert result.fill_outcome.status is FillOutcomeStatus.UNAVAILABLE
    assert result.paper_result.status == "UNAVAILABLE"
    assert result.observation.outcome_status == "UNAVAILABLE"


def test_reconciliation_non_match_stops_before_result_history_and_observation():
    admission = _ready_admission()
    instruction = _instruction(admission)
    evidence = _evidence(
        admission,
        instruction,
        expectation_fields={"entry_digest": "e" * 64},
    )

    result = run_controlled_paper_lifecycle(
        admission,
        fill_instruction=instruction,
        lifecycle_evidence=evidence,
    )

    assert result.outcome is ControlledPaperLifecycleOutcome.RECONCILIATION_NOT_MATCHED
    assert result.reconciliation.status is ReconciliationStatus.DIGEST_MISMATCH
    assert result.paper_result is None
    assert result.history_result is None
    assert result.observation is None


def test_rejected_admission_stops_before_all_p07_lifecycle_artifacts():
    ruleset = DecisionEvaluationRuleset(
        buy_score_threshold=Decimal("90"),
        watch_score_threshold=Decimal("50"),
    )
    facts, _ = _facts(ruleset=ruleset)
    rejected = prepare_controlled_paper_run(**facts)
    ready = _ready_admission()
    instruction = _instruction(ready)
    evidence = _evidence(ready, instruction)

    result = run_controlled_paper_lifecycle(
        rejected,
        fill_instruction=instruction,
        lifecycle_evidence=evidence,
    )

    assert result.outcome is ControlledPaperLifecycleOutcome.ADMISSION_NOT_READY
    assert result.reason_codes == rejected.reason_codes
    assert result.fill_outcome is None
    assert result.observation is None


def test_invalid_transition_evidence_fails_closed_without_observation():
    admission = _ready_admission()
    instruction = _instruction(admission)
    evidence = _evidence(admission, instruction)
    invalid_evidence = replace(
        evidence,
        target_asset_identity={"chain": "solana", "mint": "missing"},
    )

    result = run_controlled_paper_lifecycle(
        admission,
        fill_instruction=instruction,
        lifecycle_evidence=invalid_evidence,
    )

    assert result.outcome is ControlledPaperLifecycleOutcome.INVALID_INPUT
    assert result.reason_codes == ("P07_LIFECYCLE_INVALID_INPUT",)
    assert result.fill_outcome is not None
    assert result.transition is None
    assert result.observation is None


def test_tampered_admission_returns_invalid_input_without_lifecycle_artifacts():
    admission = _ready_admission()
    instruction = _instruction(admission)
    evidence = _evidence(admission, instruction)
    object.__setattr__(admission, "result_digest", "0" * 64)

    result = run_controlled_paper_lifecycle(
        admission,
        fill_instruction=instruction,
        lifecycle_evidence=evidence,
    )

    assert result.outcome is ControlledPaperLifecycleOutcome.INVALID_INPUT
    assert result.reason_codes == ("ADMISSION_INVALID_OR_TAMPERED",)
    assert result.fill_outcome is None
    assert result.observation is None


def test_identical_explicit_inputs_are_deterministic():
    admission = _ready_admission()
    instruction = _instruction(admission)
    evidence = _evidence(admission, instruction)

    first = run_controlled_paper_lifecycle(
        admission,
        fill_instruction=instruction,
        lifecycle_evidence=evidence,
    )
    second = run_controlled_paper_lifecycle(
        admission,
        fill_instruction=instruction,
        lifecycle_evidence=evidence,
    )

    assert first == second
    assert first.digest == second.digest
    assert first.canonical_representation == second.canonical_representation


def test_result_is_immutable_and_digest_tampering_is_rejected():
    admission = _ready_admission()
    instruction = _instruction(admission)
    result = run_controlled_paper_lifecycle(
        admission,
        fill_instruction=instruction,
        lifecycle_evidence=_evidence(admission, instruction),
    )

    with pytest.raises(FrozenInstanceError):
        result.reason_codes = ("changed",)
    with pytest.raises(ValueError, match="result_digest"):
        replace(result, result_digest="0" * 64)
