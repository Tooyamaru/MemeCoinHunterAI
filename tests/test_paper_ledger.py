from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal

import pytest

from core.execution.paper_fill_outcome import (
    FillOutcomeStatus,
    TradeSide,
)
from core.execution.paper_ledger import (
    LedgerAppendStatus,
    P07_T04_APPEND_POLICY_VERSION,
    P07_T04_CANONICALIZATION_VERSION,
    PaperLedgerEntry,
    append_paper_ledger_entry,
    create_paper_ledger_entry,
)
from core.execution.paper_position_exposure_state import (
    PaperExposureAsset,
    PaperExposureState,
    PaperPositionExposureState,
    PaperPositionState,
    StateQuality,
    TransitionStatus,
    ValuationContext,
    ValuationObservation,
    ValuationStatus,
    AccountingContext,
    transition_paper_state,
)
from tests.test_paper_fill_outcome import _evaluate
from tests.test_paper_simulation_input import REFERENCE, ReplayIdentity, _input


ASSET = {"chain": "solana", "mint": "mint-1"}
PORTFOLIO = {"portfolio": "test"}
STREAM = {"stream": "paper-test"}


def _position(quantity=Decimal("10"), cost=Decimal("100")):
    return PaperPositionState(
        ASSET,
        "TOKEN",
        quantity,
        "QUOTE",
        cost,
        None if quantity == 0 else cost / quantity,
        StateQuality.PASS,
        {"source": "ledger-fixture"},
    )


def _valuation(status=ValuationStatus.PASS):
    price = Decimal("10") if status is ValuationStatus.PASS else None
    return ValuationObservation(
        ASSET,
        "valuation-ledger",
        REFERENCE - timedelta(seconds=2),
        REFERENCE - timedelta(seconds=1),
        price,
        "QUOTE_PER_TOKEN",
        status,
        "valuation-v1",
        {"source": "ledger-fixture"},
        Decimal("300"),
    )


def _state(valuation=None):
    position = _position()
    valuation = valuation or _valuation()
    exposure_asset = PaperExposureAsset(
        ASSET,
        position.quantity,
        valuation.price,
        valuation.price_unit,
        None if valuation.price is None else position.quantity * valuation.price,
        valuation.observed_at,
        valuation.valuation_status,
        valuation.observation_id,
        valuation.observation_digest,
    )
    exposure = PaperExposureState(
        PORTFOLIO,
        (exposure_asset,),
        position.quantity,
        exposure_asset.notional,
        valuation.valuation_status,
        {"source": "ledger-fixture"},
    )
    return PaperPositionExposureState(
        "paper-state-1",
        "paper-state-v1",
        PORTFOLIO,
        (position,),
        exposure,
        REFERENCE - timedelta(seconds=1),
        StateQuality.PASS,
        {"source": "ledger-fixture"},
    )


def _accounting():
    return AccountingContext(
        fee_amount=Decimal("1"),
        priority_fee_amount=Decimal("0.25"),
        fee_unit="QUOTE",
        observation_id="accounting-ledger",
        accounting_contract_version="accounting-v1",
        provenance={"source": "ledger-fixture"},
        observed_at=REFERENCE - timedelta(seconds=3),
        availability_time=REFERENCE - timedelta(seconds=2),
    )


def _bundle(
    *,
    sequence_number=1,
    previous_entry_digest=None,
    reference=REFERENCE,
    valuation=None,
    outcome=None,
):
    simulation_input = _input()
    outcome = outcome or _evaluate(
        simulation_input=simulation_input,
        side=TradeSide.BUY,
        requested_quantity=Decimal("2"),
        executable_liquidity=Decimal("2"),
    )
    state = _state(valuation)
    transition = transition_paper_state(
        outcome,
        state,
        target_asset_identity=ASSET,
        valuation_context=ValuationContext((valuation or _valuation(),)),
        accounting_context=_accounting(),
        transition_reference_time=reference,
    )
    entry = create_paper_ledger_entry(
        simulation_input,
        outcome,
        transition,
        ledger_stream_identity=STREAM,
        sequence_number=sequence_number,
        previous_entry_digest=previous_entry_digest,
        ledger_reference_time=reference,
    )
    return simulation_input, outcome, transition, entry


def test_valid_first_entry_preserves_all_identity_boundaries():
    simulation_input, outcome, transition, entry = _bundle()

    assert isinstance(entry, PaperLedgerEntry)
    assert entry.sequence_number == 1
    assert entry.previous_entry_digest is None
    assert entry.outcome_identity["outcome_digest"] == outcome.outcome_digest
    assert entry.transition_identity["transition_digest"] == transition.digest
    assert entry.prior_state_identity["state_digest"] == transition.prior_state.digest
    assert entry.resulting_state_identity["state_digest"] == transition.next_state.digest
    assert (
        entry.simulation_identity["p07_t01_input_digest"]
        == simulation_input.digest
    )
    assert entry.provenance["append_policy_version"] == P07_T04_APPEND_POLICY_VERSION
    assert entry.provenance["canonicalization_version"] == P07_T04_CANONICALIZATION_VERSION


def test_identity_digest_and_canonical_representation_are_deterministic():
    first = _bundle()[3]
    second = _bundle()[3]

    assert first.canonical_representation == second.canonical_representation
    assert first.deterministic_representation == first.canonical_representation
    assert first.event_identity_digest == second.event_identity_digest
    assert first.entry_id == second.entry_id
    assert first.entry_digest == second.entry_digest


def test_entry_is_immutable_including_nested_values():
    entry = _bundle()[3]

    with pytest.raises(FrozenInstanceError):
        entry.sequence_number = 2
    with pytest.raises(TypeError):
        entry.ledger_stream_identity["changed"] = True
    with pytest.raises(TypeError):
        entry.provenance["changed"] = True


def test_first_append_returns_new_immutable_sequence():
    entry = _bundle()[3]

    result = append_paper_ledger_entry((), entry)

    assert result.status is LedgerAppendStatus.APPENDED
    assert result.resulting_entries == (entry,)
    assert isinstance(result.resulting_entries, tuple)
    with pytest.raises(FrozenInstanceError):
        result.status = LedgerAppendStatus.INVALID


def test_contiguous_append_and_predecessor_linkage():
    first = _bundle()[3]
    second = _bundle(
        sequence_number=2,
        previous_entry_digest=first.entry_digest,
        reference=REFERENCE + timedelta(seconds=1),
    )[3]

    first_result = append_paper_ledger_entry((), first)
    second_result = append_paper_ledger_entry(
        first_result.resulting_entries,
        second,
    )

    assert second_result.status is LedgerAppendStatus.APPENDED
    assert second_result.resulting_entries == (first, second)
    assert second.previous_entry_digest == first.entry_digest


def test_exact_duplicate_is_idempotent_without_second_record():
    entry = _bundle()[3]
    existing = (entry,)

    result = append_paper_ledger_entry(existing, entry)

    assert result.status is LedgerAppendStatus.DUPLICATE
    assert result.resulting_entries is existing
    assert len(result.resulting_entries) == 1


def test_conflicting_duplicate_and_occupied_location_are_rejected():
    first = _bundle()[3]
    same_event_different_location = _bundle(
        sequence_number=2,
        previous_entry_digest=first.entry_digest,
        reference=REFERENCE,
    )[3]
    occupied = _bundle(
        sequence_number=1,
        reference=REFERENCE + timedelta(seconds=1),
    )[3]

    event_conflict = append_paper_ledger_entry(
        (first,),
        same_event_different_location,
    )
    occupied_conflict = append_paper_ledger_entry((first,), occupied)

    assert event_conflict.status is LedgerAppendStatus.CONFLICT
    assert "EVENT_ALREADY_RECORDED" in event_conflict.reason_codes
    assert occupied_conflict.status is LedgerAppendStatus.CONFLICT
    assert "SEQUENCE_LOCATION_OCCUPIED" in occupied_conflict.reason_codes


@pytest.mark.parametrize(
    ("sequence_number", "previous_entry_digest", "expected_reason"),
    [
        (3, "a" * 64, "SEQUENCE_GAP_OR_ORDERING_VIOLATION"),
        (2, "b" * 64, "PREDECESSOR_MISMATCH"),
    ],
)
def test_gap_and_wrong_predecessor_fail_closed(
    sequence_number,
    previous_entry_digest,
    expected_reason,
):
    first = _bundle()[3]
    candidate = _bundle(
        sequence_number=sequence_number,
        previous_entry_digest=previous_entry_digest,
        reference=REFERENCE + timedelta(seconds=1),
    )[3]

    result = append_paper_ledger_entry((first,), candidate)

    assert result.status in {
        LedgerAppendStatus.REJECTED,
        LedgerAppendStatus.CONFLICT,
    }
    assert expected_reason in result.reason_codes
    assert result.resulting_entries is None


def test_append_does_not_mutate_original_ledger():
    first = _bundle()[3]
    original = (first,)
    second = _bundle(
        sequence_number=2,
        previous_entry_digest=first.entry_digest,
        reference=REFERENCE + timedelta(seconds=1),
    )[3]

    result = append_paper_ledger_entry(original, second)

    assert original == (first,)
    assert result.resulting_entries is not original
    assert result.resulting_entries == (first, second)


def test_mutation_and_replacement_attempts_fail():
    entry = _bundle()[3]

    with pytest.raises(TypeError):
        entry.timestamps["x"] = "y"
    with pytest.raises(ValueError, match="entry_id"):
        replace(entry, entry_id="a" * 64)


@pytest.mark.parametrize(
    "status",
    [
        FillOutcomeStatus.FAILED,
        FillOutcomeStatus.REJECTED,
        FillOutcomeStatus.UNAVAILABLE,
        FillOutcomeStatus.INVALID,
    ],
)
def test_non_success_outcomes_are_recorded_without_success_effect(
    status,
):
    kwargs = {"simulation_input": _input()}
    if status is FillOutcomeStatus.FAILED:
        kwargs["executable_liquidity"] = Decimal("0")
    elif status is FillOutcomeStatus.REJECTED:
        kwargs.update(
            side=TradeSide.SELL,
            available_inventory=Decimal("1"),
            requested_quantity=Decimal("2"),
            executable_liquidity=Decimal("2"),
        )
    elif status is FillOutcomeStatus.UNAVAILABLE:
        kwargs.update(
            side=TradeSide.SELL,
            requested_quantity=Decimal("2"),
            executable_liquidity=Decimal("2"),
        )
    else:
        valid = _evaluate(**kwargs)
        kwargs = {}
        outcome = replace(
            valid,
            status=FillOutcomeStatus.INVALID,
            filled_quantity=Decimal("0"),
            remaining_quantity=valid.requested_quantity,
            reason_codes=("INVALID_INPUT",),
            outcome_digest=None,
        )

    if status is not FillOutcomeStatus.INVALID:
        outcome = _evaluate(**kwargs)
    state = _state()
    transition = transition_paper_state(
        outcome,
        state,
        target_asset_identity=ASSET,
        valuation_context=ValuationContext((_valuation(),)),
        accounting_context=_accounting(),
        transition_reference_time=REFERENCE,
    )
    entry = create_paper_ledger_entry(
        _input(),
        outcome,
        transition,
        ledger_stream_identity=STREAM,
        sequence_number=1,
        previous_entry_digest=None,
        ledger_reference_time=REFERENCE,
    )

    assert entry.outcome_identity["status"] == status.value
    assert entry.effects["effect_status"] == "NOT_APPLIED"
    assert entry.resulting_state_identity is None or (
        transition.transition_status is TransitionStatus.NO_CHANGE
    )
    assert entry.outcome_identity["filled_quantity"] == "0"


def test_unknown_valuation_is_preserved():
    valuation = _valuation(ValuationStatus.UNKNOWN)
    outcome = _evaluate(simulation_input=_input())
    state = _state(valuation)
    transition = transition_paper_state(
        outcome,
        state,
        target_asset_identity=ASSET,
        valuation_context=ValuationContext((valuation,)),
        accounting_context=_accounting(),
        transition_reference_time=REFERENCE,
    )
    entry = create_paper_ledger_entry(
        _input(),
        outcome,
        transition,
        ledger_stream_identity=STREAM,
        sequence_number=1,
        previous_entry_digest=None,
        ledger_reference_time=REFERENCE,
    )

    assert transition.transition_status is TransitionStatus.APPLIED
    assert (
        entry.resulting_state_identity is not None
        and entry.effects["exposure_effect"]["next_exposure"][
            "valuation_status"
        ]
        == "UNKNOWN"
    )


def test_identity_contradictions_and_unsupported_versions_are_rejected():
    simulation_input = _input()
    outcome = _evaluate(simulation_input=simulation_input)
    state = _state()
    transition = transition_paper_state(
        outcome,
        state,
        target_asset_identity=ASSET,
        valuation_context=ValuationContext((_valuation(),)),
        accounting_context=_accounting(),
        transition_reference_time=REFERENCE,
    )

    with pytest.raises(ValueError, match="outcome does not link"):
        create_paper_ledger_entry(
            _input(
                replay_identity=ReplayIdentity(
                    "different-replay",
                    "replay-v1",
                    "seed-1",
                    None,
                    {"scope": "single-input"},
                )
            ),
            outcome,
            transition,
            ledger_stream_identity=STREAM,
            sequence_number=1,
            previous_entry_digest=None,
            ledger_reference_time=REFERENCE,
        )

    unsupported = replace(
        outcome,
        fill_model_version="unsupported-v2",
        outcome_digest=None,
    )
    with pytest.raises(ValueError, match="unsupported T02 fill model"):
        create_paper_ledger_entry(
            simulation_input,
            unsupported,
            transition,
            ledger_stream_identity=STREAM,
            sequence_number=1,
            previous_entry_digest=None,
            ledger_reference_time=REFERENCE,
        )


def test_future_transition_reference_and_invalid_sequence_fail_closed():
    _, outcome, transition, _ = _bundle(reference=REFERENCE + timedelta(seconds=1))
    with pytest.raises(ValueError, match="transition_reference_time"):
        create_paper_ledger_entry(
            _input(),
            outcome,
            transition,
            ledger_stream_identity=STREAM,
            sequence_number=1,
            previous_entry_digest=None,
            ledger_reference_time=REFERENCE,
        )

    entry = _bundle()[3]
    result = append_paper_ledger_entry(
        [entry],
        entry,
    )
    assert result.status is LedgerAppendStatus.INVALID
    assert "LEDGER_SEQUENCE_NOT_IMMUTABLE" in result.reason_codes


def test_no_external_authority_or_persistence_fields_are_created():
    entry = _bundle()[3]
    serialized = entry.canonical_representation

    assert "order" not in serialized
    assert "transaction" not in serialized
    assert "authorization" not in serialized
    assert "wallet" not in serialized
    assert "provider" not in serialized
    assert "database" not in serialized
    assert "reconciliation" not in serialized