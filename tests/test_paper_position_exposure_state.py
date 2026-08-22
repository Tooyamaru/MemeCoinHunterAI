from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal

import pytest

from core.execution import (
    AccountingContext,
    PaperExposureAsset,
    PaperExposureState,
    PaperPositionExposureState,
    PaperPositionState,
    StateQuality,
    TransitionStatus,
    ValuationContext,
    ValuationObservation,
    ValuationStatus,
    transition_paper_state,
)
from core.execution.paper_fill_outcome import FillOutcomeStatus, TradeSide
from tests.test_paper_fill_outcome import _evaluate
from tests.test_paper_simulation_input import REFERENCE


ASSET = {"chain": "solana", "mint": "mint-1"}
PORTFOLIO = {"portfolio": "paper-1"}


def _position(quantity=Decimal("10"), cost=Decimal("100")):
    return PaperPositionState(
        ASSET, "TOKEN", quantity, "QUOTE",
        cost, None if quantity == 0 else cost / quantity,
        StateQuality.PASS, {"source": "fixture"},
    )


def _valuation(status=ValuationStatus.PASS, price=Decimal("10"), age=Decimal("300")):
    return ValuationObservation(
        ASSET, "valuation-1", REFERENCE - timedelta(seconds=1),
        REFERENCE - timedelta(milliseconds=500), price if status is ValuationStatus.PASS else None,
        "QUOTE_PER_TOKEN", status, "valuation-v1", {"source": "fixture"}, age,
    )


def _exposure(position, valuation):
    asset = PaperExposureAsset(
        ASSET, position.quantity, valuation.price, valuation.price_unit,
        None if valuation.price is None else position.quantity * valuation.price,
        valuation.observed_at, valuation.valuation_status,
        valuation.observation_id, valuation.observation_digest,
    )
    return PaperExposureState(
        PORTFOLIO, (asset,), position.quantity,
        asset.notional, valuation.valuation_status, {"source": "fixture"},
    )


def _state(position=None, valuation=None):
    position = position or _position()
    valuation = valuation or _valuation()
    return PaperPositionExposureState(
        "state-1", "state-v1", PORTFOLIO, (position,),
        _exposure(position, valuation), REFERENCE,
        StateQuality.PASS, {"source": "fixture"},
    )


def _accounting(**overrides):
    values = {
        "fee_amount": Decimal("1"),
        "priority_fee_amount": Decimal("0.25"),
        "fee_unit": "QUOTE",
        "observation_id": "accounting-1",
        "accounting_contract_version": "accounting-v1",
        "provenance": {"source": "fixture"},
        "observed_at": REFERENCE - timedelta(seconds=2),
        "availability_time": REFERENCE - timedelta(seconds=1),
    }
    values.update(overrides)
    return AccountingContext(**values)


def _transition(outcome, state=None, valuation=None, accounting=None):
    return transition_paper_state(
        outcome, state or _state(), target_asset_identity=ASSET,
        valuation_context=ValuationContext((valuation or _valuation(),)),
        accounting_context=accounting or _accounting(),
        transition_reference_time=REFERENCE,
    )


def _non_success(status):
    outcome = _evaluate()
    return replace(
        outcome,
        status=status,
        filled_quantity=Decimal("0"),
        remaining_quantity=outcome.requested_quantity,
        reason_codes=(status.value,),
        outcome_digest=None,
    )


def test_buy_full_fill_updates_quantity_cost_and_exposure():
    outcome = _evaluate(
        side=TradeSide.BUY, requested_quantity=Decimal("2"),
        executable_liquidity=Decimal("2"),
        reference_quote_price=Decimal("99.66"),
    )
    result = _transition(outcome)
    assert result.transition_status is TransitionStatus.APPLIED
    assert result.next_state.positions[0].quantity == Decimal("12")
    assert result.next_state.positions[0].total_cost_basis == Decimal("301.25")
    assert result.next_state.exposure.asset_exposures[0].notional == Decimal("120")
    assert result.outcome_identity["outcome_digest"] == outcome.outcome_digest


def test_sell_partial_fill_removes_only_filled_quantity_and_cost():
    outcome = _evaluate(
        side=TradeSide.SELL, requested_quantity=Decimal("4"),
        executable_liquidity=Decimal("2"), available_inventory=Decimal("10"),
        reference_quote_price=Decimal("10.34"),
    )
    result = _transition(outcome)
    assert result.transition_status is TransitionStatus.APPLIED
    assert result.next_state.positions[0].quantity == Decimal("8")
    assert result.next_state.positions[0].total_cost_basis == Decimal("80")
    assert result.quantity_effect.remaining_quantity == Decimal("2")
    assert result.accounting_effect.proceeds == Decimal("18.75")


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (FillOutcomeStatus.FAILED, TransitionStatus.NO_CHANGE),
        (FillOutcomeStatus.REJECTED, TransitionStatus.NO_CHANGE),
        (FillOutcomeStatus.UNAVAILABLE, TransitionStatus.UNAVAILABLE),
        (FillOutcomeStatus.INVALID, TransitionStatus.INVALID),
    ],
)
def test_non_success_outcomes_do_not_mutate_state(status, expected):
    outcome = _non_success(status)
    result = _transition(outcome)
    assert result.transition_status is expected
    if expected is TransitionStatus.NO_CHANGE:
        assert result.next_state == result.prior_state
    else:
        assert result.next_state is None


def test_insufficient_and_unknown_inventory_fail_closed():
    insufficient = _transition(
        _evaluate(side=TradeSide.SELL, available_inventory=Decimal("10"),
                  requested_quantity=Decimal("11"), executable_liquidity=Decimal("11"))
    )
    assert insufficient.transition_status is TransitionStatus.REJECTED
    assert "INSUFFICIENT_INVENTORY" in insufficient.reason_codes

    unknown_state = _state(_position(), _valuation())
    unknown_position = PaperPositionState(
        ASSET, "TOKEN", Decimal("10"), "QUOTE", Decimal("100"),
        Decimal("10"), StateQuality.UNKNOWN, {"source": "fixture"},
    )
    unknown_state = _state(unknown_position)
    unknown = _transition(_evaluate(side=TradeSide.SELL, available_inventory=Decimal("10")), unknown_state)
    assert unknown.transition_status is TransitionStatus.UNAVAILABLE
    assert "INVENTORY_UNKNOWN" in unknown.reason_codes


def test_unknown_valuation_is_preserved_without_zero_substitution():
    valuation = _valuation(ValuationStatus.UNKNOWN)
    result = _transition(_evaluate(), valuation=valuation)
    assert result.transition_status is TransitionStatus.UNAVAILABLE
    assert result.next_state is None


def test_stale_valuation_and_asset_mismatch_are_rejected():
    stale = _valuation(age=Decimal("1"))
    result = _transition(_evaluate(), valuation=stale)
    assert result.transition_status is TransitionStatus.UNAVAILABLE
    assert "STALE_VALUATION" in result.reason_codes
    with pytest.raises(ValueError, match="target asset identity"):
        transition_paper_state(
            _evaluate(), _state(), target_asset_identity={"chain": "solana", "mint": "other"},
            valuation_context=ValuationContext((_valuation(),)),
            accounting_context=_accounting(),
            transition_reference_time=REFERENCE,
        )


def test_state_and_result_are_immutable_and_replay_stable():
    first = _transition(_evaluate())
    second = _transition(_evaluate())
    assert first.digest == second.digest
    with pytest.raises(FrozenInstanceError):
        first.transition_status = TransitionStatus.INVALID
    with pytest.raises(TypeError):
        first.next_state.positions[0].position_provenance["x"] = "y"