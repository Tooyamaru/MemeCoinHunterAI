from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from core.execution.paper_fill_outcome import (
    FillOutcomeStatus,
    FrictionComponents,
    PaperFillOutcome,
    TradeSide,
    evaluate_paper_fill,
)
from tests.test_paper_simulation_input import (
    REFERENCE,
    _input,
)


def _friction(**overrides):
    values = {
        "fees": Decimal("0.10"),
        "spread": Decimal("0.20"),
        "slippage": Decimal("0.05"),
        "price_impact": Decimal("0.03"),
        "quote_drift": Decimal("0.02"),
        "priority_fees": Decimal("0.01"),
        "mev_adverse_ordering": Decimal("0.04"),
        "evidence": {"source": "fixture"},
    }
    values.update(overrides)
    return FrictionComponents(**values)


def _evaluate(**overrides):
    values = {
        "simulation_input": _input(),
        "side": TradeSide.BUY,
        "requested_quantity": Decimal("10"),
        "quantity_unit": "TOKEN",
        "price_unit": "QUOTE_PER_TOKEN",
        "fee_unit": "QUOTE",
        "executable_liquidity": Decimal("10"),
        "reference_quote_price": Decimal("100"),
        "quote_observation_time": REFERENCE - timedelta(seconds=2),
        "fill_time": REFERENCE - timedelta(seconds=1),
        "friction": _friction(),
    }
    values.update(overrides)
    return evaluate_paper_fill(**values)


def test_valid_buy_full_fill_preserves_provenance_and_precedence():
    outcome = _evaluate()

    assert outcome.status is FillOutcomeStatus.FILLED
    assert outcome.side is TradeSide.BUY
    assert outcome.filled_quantity == Decimal("10")
    assert outcome.remaining_quantity == Decimal("0")
    assert outcome.effective_price == Decimal("100.34")
    assert outcome.latency_seconds == Decimal("1.0")
    assert outcome.p07_t01_input_digest == outcome.p07_t01_input_digest
    assert len(outcome.outcome_digest) == 64


def test_valid_sell_full_fill_uses_opposite_price_direction():
    outcome = _evaluate(
        side=TradeSide.SELL,
        available_inventory=Decimal("20"),
    )

    assert outcome.status is FillOutcomeStatus.FILLED
    assert outcome.effective_price == Decimal("99.66")


def test_partial_fill_conserves_quantity_and_respects_liquidity():
    outcome = _evaluate(executable_liquidity=Decimal("3.5"))

    assert outcome.status is FillOutcomeStatus.PARTIALLY_FILLED
    assert outcome.filled_quantity == Decimal("3.5")
    assert outcome.remaining_quantity == Decimal("6.5")
    assert outcome.filled_quantity + outcome.remaining_quantity == outcome.requested_quantity


@pytest.mark.parametrize(
    ("liquidity", "status"),
    [(Decimal("0"), FillOutcomeStatus.FAILED)],
)
def test_no_liquidity_is_non_success_without_positive_fill(liquidity, status):
    outcome = _evaluate(executable_liquidity=liquidity)

    assert outcome.status is status
    assert outcome.filled_quantity == Decimal("0")
    assert outcome.remaining_quantity == outcome.requested_quantity


def test_sell_inventory_and_sellability_fail_closed():
    insufficient = _evaluate(side=TradeSide.SELL, available_inventory=Decimal("9"))
    unknown = _evaluate(side=TradeSide.SELL)

    assert insufficient.status is FillOutcomeStatus.REJECTED
    assert unknown.status is FillOutcomeStatus.UNAVAILABLE


def test_unknown_friction_is_unavailable_not_zero():
    outcome = _evaluate(friction=_friction(slippage=None))

    assert outcome.status is FillOutcomeStatus.UNAVAILABLE
    assert "UNKNOWN_FRICTION:slippage" in outcome.reason_codes
    assert outcome.filled_quantity == Decimal("0")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"requested_quantity": Decimal("0")},
        {"requested_quantity": Decimal("-1")},
        {"executable_liquidity": Decimal("-1")},
        {"reference_quote_price": Decimal("NaN")},
    ],
)
def test_invalid_inputs_are_rejected_before_evaluation(kwargs):
    with pytest.raises(ValueError):
        _evaluate(**kwargs)


def test_future_and_negative_latency_are_rejected():
    future = _evaluate(fill_time=REFERENCE + timedelta(seconds=1))
    negative = _evaluate(
        quote_observation_time=REFERENCE - timedelta(seconds=1),
        fill_time=REFERENCE - timedelta(seconds=2),
    )

    assert future.status is FillOutcomeStatus.REJECTED
    assert negative.status is FillOutcomeStatus.INVALID


def test_outcome_is_immutable_including_nested_friction_evidence():
    outcome = _evaluate()

    with pytest.raises(FrozenInstanceError):
        outcome.status = FillOutcomeStatus.FAILED
    with pytest.raises(TypeError):
        outcome.friction.evidence["changed"] = True


def test_canonical_digest_and_replay_are_stable():
    first = _evaluate()
    second = _evaluate()

    assert first.canonical_representation == second.canonical_representation
    assert first.deterministic_representation == first.canonical_representation
    assert first.outcome_digest == second.outcome_digest


def test_unknown_fields_and_non_decimal_values_are_rejected():
    with pytest.raises(TypeError):
        FrictionComponents(unknown_field=Decimal("1"))
    with pytest.raises(TypeError):
        _evaluate(requested_quantity=1.0)


def test_outcome_constructor_rejects_non_success_positive_fill():
    with pytest.raises(ValueError, match="non-success"):
        PaperFillOutcome(
            status=FillOutcomeStatus.FAILED,
            side=TradeSide.BUY,
            requested_quantity=Decimal("1"),
            filled_quantity=Decimal("1"),
            remaining_quantity=Decimal("0"),
            quantity_unit="TOKEN",
            price_unit="QUOTE_PER_TOKEN",
            fee_unit="QUOTE",
            reference_quote_price=None,
            effective_price=None,
            executable_liquidity=None,
            friction=None,
            quote_observation_time=None,
            fill_time=None,
            latency_seconds=None,
            reason_codes=("failed",),
            p07_t01_input_digest="a" * 64,
            simulation_configuration_id="config",
            simulation_configuration_digest="b" * 64,
            replay_id="replay",
            execution_observation_id="obs",
            execution_observation_digest="c" * 64,
        )

def test_constructor_rejects_filled_quantity_above_liquidity():
    with pytest.raises(ValueError, match="cannot exceed executable_liquidity"):
        PaperFillOutcome(
            status=FillOutcomeStatus.FILLED,
            side=TradeSide.BUY,
            requested_quantity=Decimal("10"),
            filled_quantity=Decimal("10"),
            remaining_quantity=Decimal("0"),
            quantity_unit="TOKEN",
            price_unit="QUOTE_PER_TOKEN",
            fee_unit="QUOTE",
            reference_quote_price=Decimal("100"),
            effective_price=Decimal("100"),
            executable_liquidity=Decimal("5"),
            friction=_friction(),
            quote_observation_time=REFERENCE - timedelta(seconds=2),
            fill_time=REFERENCE - timedelta(seconds=1),
            latency_seconds=Decimal("1"),
            reason_codes=(),
            p07_t01_input_digest="a" * 64,
            simulation_configuration_id="config",
            simulation_configuration_digest="b" * 64,
            replay_id="replay",
            execution_observation_id="obs",
            execution_observation_digest="c" * 64,
        )


def test_friction_requires_provenance_evidence():
    with pytest.raises(ValueError, match="requires supplied evidence"):
        FrictionComponents(
            fees=Decimal("0.10"),
            spread=Decimal("0.20"),
            slippage=Decimal("0.05"),
            price_impact=Decimal("0.03"),
            quote_drift=Decimal("0.02"),
            priority_fees=Decimal("0.01"),
            mev_adverse_ordering=Decimal("0.04"),
            evidence={},
        )


def test_constructor_derives_latency_from_timestamps():
    outcome = PaperFillOutcome(
        status=FillOutcomeStatus.FILLED,
        side=TradeSide.BUY,
        requested_quantity=Decimal("1"),
        filled_quantity=Decimal("1"),
        remaining_quantity=Decimal("0"),
        quantity_unit="TOKEN",
        price_unit="QUOTE_PER_TOKEN",
        fee_unit="QUOTE",
        reference_quote_price=Decimal("100"),
        effective_price=Decimal("100"),
        executable_liquidity=Decimal("1"),
        friction=_friction(),
        quote_observation_time=REFERENCE - timedelta(seconds=60),
        fill_time=REFERENCE,
        latency_seconds=None,
        reason_codes=(),
        p07_t01_input_digest="a" * 64,
        simulation_configuration_id="config",
        simulation_configuration_digest="b" * 64,
        replay_id="replay",
        execution_observation_id="obs",
        execution_observation_digest="c" * 64,
    )

    assert outcome.latency_seconds == Decimal("60.0")


def test_rounding_policy_is_explicit_and_deterministic():
    outcome = _evaluate(
        reference_quote_price=Decimal(
            "100.12345678901234567895"
        ),
    )

    assert outcome.effective_price == Decimal(
        "100.463456789012345679"
    )
    assert (
        outcome.canonical_representation["rounding_mode"]
        == "ROUND_HALF_EVEN"
    )
    assert (
        outcome.canonical_representation["max_decimal_places"]
        == 18
    )
