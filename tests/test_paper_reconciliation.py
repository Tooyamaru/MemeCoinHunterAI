from dataclasses import FrozenInstanceError
from datetime import timedelta
from decimal import Decimal

import pytest

from core.execution.paper_fill_outcome import FillOutcomeStatus
from core.execution.paper_reconciliation import (
    ObservationAvailability,
    P07_T05_RECONCILIATION_MODEL_VERSION,
    PaperReconciliationExpectation,
    ReconciliationStatus,
    reconcile_paper_ledger,
)
from tests.test_paper_fill_outcome import _evaluate
from tests.test_paper_ledger import STREAM, _bundle
from tests.test_paper_simulation_input import REFERENCE


def _expectation(entry, *, reference=REFERENCE, **fields):
    expected_fields = {
        "entry_id": entry.entry_id,
        "event_identity_digest": entry.event_identity_digest,
        **fields,
    }
    return PaperReconciliationExpectation(
        expectation_id="expectation-1",
        replay_id="replay-1",
        expected_fields=expected_fields,
        comparison_reference_time=reference,
    )


def test_valid_reconciliation_preserves_identity_and_is_immutable():
    entry = _bundle()[3]
    expectation = _expectation(entry)
    result = reconcile_paper_ledger((entry,), expectation)

    assert result.status is ReconciliationStatus.MATCH
    assert result.expectation_identity["expectation_digest"] == expectation.expectation_digest
    assert result.compared_entry_ids == (entry.entry_id,)
    assert result.compared_entry_digests == (entry.entry_digest,)
    assert result.ledger_stream_identity == STREAM
    assert result.p07_t01_input_digest == entry.simulation_identity["p07_t01_input_digest"]
    assert result.replay_identity["replay_id"] == "replay-1"
    assert result.decision_intent_digest == entry.simulation_identity["decision_intent_digest"]
    assert result.outcome_identity == entry.outcome_identity
    assert result.transition_identity == entry.transition_identity
    assert result.prior_state_identity == entry.prior_state_identity
    assert result.resulting_state_identity == entry.resulting_state_identity
    assert result.contract_version == "p07-t05-v1"
    assert result.reconciliation_model_version == P07_T05_RECONCILIATION_MODEL_VERSION

    with pytest.raises(FrozenInstanceError):
        result.status = ReconciliationStatus.INVALID
    with pytest.raises(TypeError):
        result.provenance["changed"] = True


def test_expectation_is_immutable_and_mapping_order_is_canonical():
    entry = _bundle()[3]
    first = _expectation(
        entry,
        status=entry.outcome_identity["status"],
        replay_id=entry.simulation_identity["replay_id"],
    )
    second = PaperReconciliationExpectation(
        expectation_id="expectation-1",
        replay_id="replay-1",
        expected_fields={
            "replay_id": entry.simulation_identity["replay_id"],
            "event_identity_digest": entry.event_identity_digest,
            "status": entry.outcome_identity["status"],
            "entry_id": entry.entry_id,
        },
        comparison_reference_time=REFERENCE,
    )

    assert first.canonical_representation == second.canonical_representation
    assert first.expectation_digest == second.expectation_digest
    with pytest.raises(FrozenInstanceError):
        first.expectation_id = "changed"
    with pytest.raises(TypeError):
        first.expected_fields["changed"] = True


def test_identical_inputs_produce_identical_results_and_digests():
    entry = _bundle()[3]
    expectation = _expectation(entry)

    first = reconcile_paper_ledger((entry,), expectation)
    second = reconcile_paper_ledger((entry,), expectation)

    assert first == second
    assert first.canonical_representation == second.canonical_representation
    assert first.digest == second.digest


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (ObservationAvailability.UNKNOWN, "unknown observation"),
        (ObservationAvailability.UNAVAILABLE, "observation unavailable"),
    ],
)
def test_unknown_and_unavailable_observations_are_preserved(status, reason):
    expectation = PaperReconciliationExpectation(
        expectation_id="expectation-unavailable",
        replay_id="replay-1",
        expected_fields={},
        comparison_reference_time=REFERENCE,
        observation_status=status,
        reason_codes=(reason,),
    )

    result = reconcile_paper_ledger((), expectation)

    assert result.status is ReconciliationStatus.UNAVAILABLE
    assert "OBSERVATION_" + status.value in result.reason_codes


def test_missing_event_is_detected():
    entry = _bundle()[3]

    result = reconcile_paper_ledger((), _expectation(entry))

    assert result.status is ReconciliationStatus.MISSING
    assert "EXPECTED_EVENT_MISSING" in result.reason_codes


def test_duplicate_event_and_malformed_sequence_fail_closed():
    entry = _bundle()[3]
    duplicate = reconcile_paper_ledger((entry, entry), _expectation(entry))
    malformed = reconcile_paper_ledger(
        (_bundle(sequence_number=2, previous_entry_digest="a" * 64)[3],),
        _expectation(entry),
    )

    assert duplicate.status is ReconciliationStatus.INVALID
    assert any("INVALID_LEDGER" in reason for reason in duplicate.reason_codes)
    assert malformed.status is ReconciliationStatus.INVALID
    assert any("INVALID_LEDGER" in reason for reason in malformed.reason_codes)


def test_delayed_event_is_detected():
    entry = _bundle()[3]
    expectation = _expectation(
        entry,
        expected_ledger_reference_time=REFERENCE - timedelta(seconds=1),
    )

    result = reconcile_paper_ledger((entry,), expectation)

    assert result.status is ReconciliationStatus.DELAYED
    assert "EVENT_DELIVERED_AFTER_EXPECTED_TIME" in result.reason_codes


def test_partial_failed_and_unexpected_events_are_detected():
    partial = _bundle(
        outcome=_evaluate(executable_liquidity=Decimal("1")),
    )[3]
    failed = _bundle(
        outcome=_evaluate(executable_liquidity=Decimal("0")),
    )[3]
    partial_result = reconcile_paper_ledger(
        (partial,),
        _expectation(partial, status=FillOutcomeStatus.FILLED.value),
    )
    failed_result = reconcile_paper_ledger(
        (failed,),
        _expectation(failed, status=FillOutcomeStatus.FILLED.value),
    )
    unexpected = reconcile_paper_ledger(
        (failed,),
        PaperReconciliationExpectation(
            expectation_id="expectation-absent",
            replay_id="replay-1",
            expected_fields={"expected_presence": False},
            comparison_reference_time=REFERENCE,
        ),
    )

    assert partial_result.status is ReconciliationStatus.PARTIAL
    assert failed_result.status is ReconciliationStatus.FAILED
    assert unexpected.status is ReconciliationStatus.UNEXPECTED


def test_identity_digest_replay_sequence_timestamp_and_state_mismatches():
    first = _bundle()[3]
    second = _bundle(
        sequence_number=2,
        previous_entry_digest=first.entry_digest,
        reference=REFERENCE + timedelta(seconds=1),
    )[3]
    identity = reconcile_paper_ledger(
        (first,),
        _expectation(first, entry_id="f" * 64, sequence_number=1),
    )
    digest = reconcile_paper_ledger(
        (first,),
        _expectation(first, entry_digest="e" * 64),
    )
    replay = reconcile_paper_ledger(
        (first,),
        _expectation(first, replay_id="different-replay"),
    )
    timestamp = reconcile_paper_ledger(
        (first,),
        _expectation(
            first,
            timestamps={"ledger_reference_time": REFERENCE - timedelta(seconds=1)},
        ),
    )
    state = reconcile_paper_ledger(
        (first,),
        _expectation(first, prior_state_digest="a" * 64),
    )
    contradictory = reconcile_paper_ledger(
        (first, second),
        _expectation(
            first,
            entry_id=first.entry_id,
            event_identity_digest=second.event_identity_digest,
            reference=REFERENCE + timedelta(seconds=1),
        ),
    )

    assert identity.status is ReconciliationStatus.IDENTITY_MISMATCH
    assert digest.status is ReconciliationStatus.DIGEST_MISMATCH
    assert replay.status is ReconciliationStatus.REPLAY_MISMATCH
    assert timestamp.status is ReconciliationStatus.TIMESTAMP_MISMATCH
    assert state.status is ReconciliationStatus.STATE_MISMATCH
    assert contradictory.status is ReconciliationStatus.CONTRADICTORY


def test_future_timestamp_is_rejected_without_wall_clock():
    entry = _bundle()[3]
    future = reconcile_paper_ledger(
        (entry,),
        _expectation(
            entry,
            reference=REFERENCE - timedelta(seconds=1),
        ),
    )

    assert future.status is ReconciliationStatus.TIMESTAMP_MISMATCH
    assert "FUTURE_DATA_LEAKAGE" in future.reason_codes


def test_invalid_expectation_is_explicit_and_fail_closed():
    result = reconcile_paper_ledger(
        (),
        {
            "expectation_id": "expectation-invalid",
            "replay_id": "replay-1",
            "expected_fields": {"unsupported": True},
            "comparison_reference_time": REFERENCE,
        },
    )

    assert result.status is ReconciliationStatus.INVALID
    assert result.result_digest is not None
    assert any(reason.startswith("INVALID_EXPECTATION:") for reason in result.reason_codes)


def test_unresolved_discrepancy_does_not_append_or_mutate_inputs():
    entry = _bundle()[3]
    original_entry = entry.canonical_representation
    expectation = _expectation(entry, entry_digest="0" * 64)
    original_expectation = expectation.canonical_representation

    result = reconcile_paper_ledger((entry,), expectation)

    assert result.status is ReconciliationStatus.DIGEST_MISMATCH
    assert entry.canonical_representation == original_entry
    assert expectation.canonical_representation == original_expectation
    assert result.resulting_state_identity == entry.resulting_state_identity


def test_reconciliation_has_no_live_authority_or_execution_semantics():
    entry = _bundle()[3]
    result = reconcile_paper_ledger((entry,), _expectation(entry))
    serialized = result.canonical_representation

    for forbidden in (
        "authorization",
        "order",
        "transaction",
        "wallet",
        "signing",
        "broadcast",
        "rpc",
        "dex",
        "provider",
        "on_chain",
        "live",
        "database",
        "filesystem",
        "network",
    ):
        assert forbidden not in serialized
    assert result.provenance["source_contract"] == "P07-T05"
    assert "on-chain" not in str(result.provenance).lower()


def test_provider_neutral_and_no_random_or_clock_dependency():
    entry = _bundle()[3]
    result = reconcile_paper_ledger((entry,), _expectation(entry))

    assert result.timestamps["comparison_reference_time"] == (
        "2026-08-21T12:00:00.000000Z"
    )
    assert result.timestamps["observation_time"] is None
    assert result.reconciliation_model_version == "p07-t05-reconciliation-v1"