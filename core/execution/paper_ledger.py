"""Deterministic, immutable P07-T04 logical paper-ledger records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.execution.paper_fill_outcome import (
    FillOutcomeStatus,
    P07_T02_CONTRACT_VERSION,
    P07_T02_FILL_MODEL_VERSION,
    P07_T02_FRICTION_MODEL_VERSION,
    PaperFillOutcome,
)
from core.execution.paper_position_exposure_state import (
    PaperPositionExposureState,
    PaperStateTransitionResult,
    P07_T03_CONTRACT_VERSION,
    TransitionStatus,
)
from core.execution.paper_simulation_input import (
    P07_T01_CONTRACT_VERSION,
    PaperSimulationInput,
)


P07_T04_CONTRACT_VERSION = "p07-t04-v1"
P07_T04_LEDGER_MODEL_VERSION = "p07-t04-ledger-v1"
P07_T04_CANONICALIZATION_VERSION = "p07-t04-canonical-v1"
P07_T04_APPEND_POLICY_VERSION = "p07-t04-append-v1"

_DIGEST_LENGTH = 64


class LedgerAppendStatus(StrEnum):
    """Result of validating one candidate against a logical ledger sequence."""

    APPENDED = "APPENDED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    REJECTED = "REJECTED"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


@dataclass(frozen=True)
class PaperLedgerEntry:
    """One immutable logical record of a hypothetical paper event."""

    ledger_stream_identity: Mapping[str, Any]
    sequence_number: int
    previous_entry_digest: str | None
    simulation_identity: Mapping[str, Any]
    outcome_identity: Mapping[str, Any]
    transition_identity: Mapping[str, Any]
    prior_state_identity: Mapping[str, Any]
    resulting_state_identity: Mapping[str, Any] | None
    timestamps: Mapping[str, Any]
    effects: Mapping[str, Any]
    reason_codes: tuple[str, ...]
    provenance: Mapping[str, Any]
    contract_version: str = P07_T04_CONTRACT_VERSION
    ledger_model_version: str = P07_T04_LEDGER_MODEL_VERSION
    event_identity_digest: str | None = None
    entry_id: str | None = None
    entry_digest: str | None = None

    def __post_init__(self) -> None:
        if self.contract_version != P07_T04_CONTRACT_VERSION:
            raise ValueError("unsupported P07-T04 contract_version")
        if self.ledger_model_version != P07_T04_LEDGER_MODEL_VERSION:
            raise ValueError("unsupported P07-T04 ledger_model_version")
        if (
            isinstance(self.sequence_number, bool)
            or not isinstance(self.sequence_number, int)
            or self.sequence_number <= 0
        ):
            raise ValueError("sequence_number must be a positive integer")
        if self.sequence_number == 1 and self.previous_entry_digest is not None:
            raise ValueError("first ledger entry must have null predecessor")
        if self.sequence_number > 1:
            _require_digest(self.previous_entry_digest, "previous_entry_digest")
        elif self.previous_entry_digest is not None:
            _require_digest(self.previous_entry_digest, "previous_entry_digest")

        for value, name in (
            (self.ledger_stream_identity, "ledger_stream_identity"),
            (self.simulation_identity, "simulation_identity"),
            (self.outcome_identity, "outcome_identity"),
            (self.transition_identity, "transition_identity"),
            (self.prior_state_identity, "prior_state_identity"),
            (self.timestamps, "timestamps"),
            (self.effects, "effects"),
            (self.provenance, "provenance"),
        ):
            object.__setattr__(self, name, _canonical_mapping(value, name))
        if self.resulting_state_identity is not None:
            object.__setattr__(
                self,
                "resulting_state_identity",
                _canonical_mapping(
                    self.resulting_state_identity,
                    "resulting_state_identity",
                ),
            )

        object.__setattr__(
            self,
            "reason_codes",
            _canonical_texts(self.reason_codes, "reason_codes"),
        )

        expected_event = _digest(self._event_identity_material())
        if self.event_identity_digest is not None:
            _require_digest(self.event_identity_digest, "event_identity_digest")
            if self.event_identity_digest != expected_event:
                raise ValueError(
                    "event_identity_digest does not match canonical identity"
                )
        object.__setattr__(self, "event_identity_digest", expected_event)

        expected_entry_id = _digest(
            {
                "ledger_stream_identity": self.ledger_stream_identity,
                "sequence_number": self.sequence_number,
                "previous_entry_digest": self.previous_entry_digest,
                "event_identity_digest": expected_event,
            }
        )
        if self.entry_id is not None:
            _require_digest(self.entry_id, "entry_id")
            if self.entry_id != expected_entry_id:
                raise ValueError("entry_id does not match canonical identity")
        object.__setattr__(self, "entry_id", expected_entry_id)

        expected_entry_digest = _digest(self._canonical_without_digest())
        if self.entry_digest is not None:
            _require_digest(self.entry_digest, "entry_digest")
            if self.entry_digest != expected_entry_digest:
                raise ValueError("entry_digest does not match canonical entry")
        object.__setattr__(self, "entry_digest", expected_entry_digest)

    def _event_identity_material(self) -> Mapping[str, Any]:
        return {
            "ledger_model_version": self.ledger_model_version,
            "p07_t01_input_digest": self.simulation_identity[
                "p07_t01_input_digest"
            ],
            "replay_id": self.simulation_identity["replay_id"],
            "outcome_digest": self.outcome_identity["outcome_digest"],
            "transition_digest": self.transition_identity["transition_digest"],
            "prior_state_digest": self.prior_state_identity["state_digest"],
            "resulting_state_digest": (
                self.resulting_state_identity["state_digest"]
                if self.resulting_state_identity is not None
                else None
            ),
            "transition_reference_time": self.timestamps[
                "transition_reference_time"
            ],
            "ledger_reference_time": self.timestamps["ledger_reference_time"],
        }

    def _canonical_without_digest(self) -> Mapping[str, Any]:
        return {
            "contract_version": self.contract_version,
            "ledger_model_version": self.ledger_model_version,
            "ledger_stream_identity": self.ledger_stream_identity,
            "sequence_number": self.sequence_number,
            "previous_entry_digest": self.previous_entry_digest,
            "entry_id": self.entry_id,
            "event_identity_digest": self.event_identity_digest,
            "simulation_identity": self.simulation_identity,
            "outcome_identity": self.outcome_identity,
            "transition_identity": self.transition_identity,
            "prior_state_identity": self.prior_state_identity,
            "resulting_state_identity": self.resulting_state_identity,
            "timestamps": self.timestamps,
            "effects": self.effects,
            "reason_codes": self.reason_codes,
            "provenance": self.provenance,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                **self._canonical_without_digest(),
                "entry_digest": self.entry_digest,
            }
        )

    deterministic_representation = property(
        lambda self: self.canonical_representation
    )


@dataclass(frozen=True)
class PaperLedgerAppendResult:
    """Immutable result of pure append validation."""

    status: LedgerAppendStatus | str
    candidate_entry_id: str | None
    resulting_entries: tuple[PaperLedgerEntry, ...] | None
    reason_codes: tuple[str, ...]
    contract_version: str = P07_T04_CONTRACT_VERSION
    append_policy_version: str = P07_T04_APPEND_POLICY_VERSION

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "status", LedgerAppendStatus(self.status))
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported ledger append status") from error
        if self.contract_version != P07_T04_CONTRACT_VERSION:
            raise ValueError("unsupported P07-T04 contract_version")
        if self.append_policy_version != P07_T04_APPEND_POLICY_VERSION:
            raise ValueError("unsupported append_policy_version")
        if self.candidate_entry_id is not None:
            _require_digest(self.candidate_entry_id, "candidate_entry_id")
        if self.resulting_entries is not None:
            if not isinstance(self.resulting_entries, tuple):
                raise ValueError("resulting_entries must be an immutable tuple")
            if any(
                not isinstance(entry, PaperLedgerEntry)
                for entry in self.resulting_entries
            ):
                raise ValueError(
                    "resulting_entries must contain PaperLedgerEntry values"
                )
        object.__setattr__(
            self,
            "reason_codes",
            _canonical_texts(self.reason_codes, "reason_codes"),
        )

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "contract_version": self.contract_version,
                "append_policy_version": self.append_policy_version,
                "status": self.status,
                "candidate_entry_id": self.candidate_entry_id,
                "resulting_entries": (
                    tuple(entry.canonical_representation for entry in self.resulting_entries)
                    if self.resulting_entries is not None
                    else None
                ),
                "reason_codes": self.reason_codes,
            }
        )

    deterministic_representation = property(
        lambda self: self.canonical_representation
    )


def create_paper_ledger_entry(
    simulation_input: PaperSimulationInput,
    outcome: PaperFillOutcome,
    transition: PaperStateTransitionResult,
    *,
    ledger_stream_identity: Mapping[str, Any],
    sequence_number: int,
    previous_entry_digest: str | None,
    ledger_reference_time: datetime,
) -> PaperLedgerEntry:
    """Create one identity-verified logical paper-ledger record."""

    if not isinstance(simulation_input, PaperSimulationInput):
        raise TypeError("simulation_input must be PaperSimulationInput")
    if not isinstance(outcome, PaperFillOutcome):
        raise TypeError("outcome must be PaperFillOutcome")
    if not isinstance(transition, PaperStateTransitionResult):
        raise TypeError("transition must be PaperStateTransitionResult")

    _verify_simulation_input(simulation_input)
    _verify_outcome(outcome)
    _verify_transition(transition)

    if outcome.p07_t01_input_digest != simulation_input.digest:
        raise ValueError("outcome does not link to the supplied T01 input")
    configuration = simulation_input.simulation_configuration
    if (
        outcome.simulation_configuration_id != configuration.configuration_id
        or outcome.simulation_configuration_digest
        != configuration.configuration_digest
    ):
        raise ValueError("outcome configuration identity mismatch")
    execution = simulation_input.execution_observation
    if (
        outcome.execution_observation_id != execution.observation_id
        or outcome.execution_observation_digest != execution.observation_digest
    ):
        raise ValueError("outcome execution observation identity mismatch")
    if outcome.replay_id != simulation_input.replay_identity.replay_id:
        raise ValueError("outcome replay identity mismatch")

    prior_state = transition.prior_state
    initial_state = simulation_input.initial_paper_state
    if (
        prior_state.state_id != initial_state.state_id
        or prior_state.state_version != initial_state.state_version
        or prior_state.portfolio_scope
        != _canonical_mapping(initial_state.portfolio_scope, "portfolio_scope")
    ):
        raise ValueError("T03 prior state identity mismatch")
    if transition.outcome_identity.get("outcome_digest") != outcome.outcome_digest:
        raise ValueError("T03 outcome identity mismatch")

    reference = _to_utc(ledger_reference_time, "ledger_reference_time")
    transition_reference = _to_utc(
        transition.transition_reference_time,
        "transition_reference_time",
    )
    if transition_reference != reference:
        raise ValueError(
            "transition_reference_time must equal ledger_reference_time"
        )
    _validate_temporal_boundary(simulation_input, outcome, transition, reference)
    _validate_status_linkage(outcome, transition)

    resulting_state = transition.next_state
    if transition.transition_status is TransitionStatus.APPLIED:
        if resulting_state is None:
            raise ValueError("APPLIED transition requires resulting state")
    elif transition.transition_status is TransitionStatus.NO_CHANGE:
        if resulting_state is not prior_state and resulting_state != prior_state:
            raise ValueError("NO_CHANGE transition must preserve prior state")
    elif resulting_state is not None:
        raise ValueError("non-applied transition cannot invent resulting state")

    simulation_identity = _simulation_identity(simulation_input)
    outcome_identity = _outcome_identity(outcome)
    transition_identity = _transition_identity(transition)
    prior_identity = _state_identity(prior_state)
    resulting_identity = (
        _state_identity(resulting_state) if resulting_state is not None else None
    )
    timestamps = _timestamps(simulation_input, outcome, transition, reference)
    effects = _effects(transition)
    reason_codes = tuple(
        sorted(set(outcome.reason_codes) | set(transition.reason_codes))
    )
    provenance = {
        "source_contract": "P07-T04",
        "canonicalization_version": P07_T04_CANONICALIZATION_VERSION,
        "append_policy_version": P07_T04_APPEND_POLICY_VERSION,
        "p07_t01_input_digest": simulation_input.digest,
        "p07_t02_outcome_digest": outcome.outcome_digest,
        "p07_t03_transition_digest": transition.transition_digest,
        "prior_state_digest": prior_state.digest,
        "resulting_state_digest": (
            resulting_state.digest if resulting_state is not None else None
        ),
        "replay_id": simulation_input.replay_identity.replay_id,
    }

    return PaperLedgerEntry(
        ledger_stream_identity=ledger_stream_identity,
        sequence_number=sequence_number,
        previous_entry_digest=previous_entry_digest,
        simulation_identity=simulation_identity,
        outcome_identity=outcome_identity,
        transition_identity=transition_identity,
        prior_state_identity=prior_identity,
        resulting_state_identity=resulting_identity,
        timestamps=timestamps,
        effects=effects,
        reason_codes=reason_codes,
        provenance=provenance,
    )


def append_paper_ledger_entry(
    existing_entries: tuple[PaperLedgerEntry, ...],
    candidate: PaperLedgerEntry,
) -> PaperLedgerAppendResult:
    """Validate and append a candidate without mutating supplied entries."""

    candidate_id = (
        candidate.entry_id if isinstance(candidate, PaperLedgerEntry) else None
    )
    if not isinstance(candidate, PaperLedgerEntry):
        return _append_result(
            LedgerAppendStatus.INVALID,
            candidate_id,
            None,
            ("INVALID_CANDIDATE",),
        )
    if not isinstance(existing_entries, tuple):
        return _append_result(
            LedgerAppendStatus.INVALID,
            candidate.entry_id,
            None,
            ("LEDGER_SEQUENCE_NOT_IMMUTABLE",),
        )
    if any(
        not isinstance(entry, PaperLedgerEntry) for entry in existing_entries
    ):
        return _append_result(
            LedgerAppendStatus.INVALID,
            candidate.entry_id,
            None,
            ("INVALID_EXISTING_ENTRY",),
        )
    if not _valid_existing_sequence(existing_entries):
        return _append_result(
            LedgerAppendStatus.INVALID,
            candidate.entry_id,
            None,
            ("INVALID_EXISTING_SEQUENCE",),
        )

    if not existing_entries:
        if candidate.sequence_number != 1:
            return _append_result(
                LedgerAppendStatus.REJECTED,
                candidate.entry_id,
                None,
                ("SEQUENCE_MUST_START_AT_ONE",),
            )
        if candidate.previous_entry_digest is not None:
            return _append_result(
                LedgerAppendStatus.REJECTED,
                candidate.entry_id,
                None,
                ("FIRST_PREDECESSOR_MUST_BE_NULL",),
            )
        return _append_result(
            LedgerAppendStatus.APPENDED,
            candidate.entry_id,
            (candidate,),
            (),
        )

    first = existing_entries[0]
    if candidate.ledger_stream_identity != first.ledger_stream_identity:
        return _append_result(
            LedgerAppendStatus.CONFLICT,
            candidate.entry_id,
            None,
            ("LEDGER_STREAM_CONFLICT",),
        )
    if _append_policy(first) != P07_T04_APPEND_POLICY_VERSION:
        return _append_result(
            LedgerAppendStatus.INVALID,
            candidate.entry_id,
            None,
            ("UNSUPPORTED_APPEND_POLICY",),
        )
    if _append_policy(candidate) != _append_policy(first):
        return _append_result(
            LedgerAppendStatus.CONFLICT,
            candidate.entry_id,
            None,
            ("APPEND_POLICY_CONFLICT",),
        )

    for entry in existing_entries:
        if entry.entry_id == candidate.entry_id:
            if entry.canonical_representation == candidate.canonical_representation:
                return _append_result(
                    LedgerAppendStatus.DUPLICATE,
                    candidate.entry_id,
                    existing_entries,
                    (),
                )
            return _append_result(
                LedgerAppendStatus.CONFLICT,
                candidate.entry_id,
                None,
                ("ENTRY_ID_CONFLICT",),
            )
        if entry.event_identity_digest == candidate.event_identity_digest:
            return _append_result(
                LedgerAppendStatus.CONFLICT,
                candidate.entry_id,
                None,
                ("EVENT_ALREADY_RECORDED",),
            )
        if entry.sequence_number == candidate.sequence_number:
            return _append_result(
                LedgerAppendStatus.CONFLICT,
                candidate.entry_id,
                None,
                ("SEQUENCE_LOCATION_OCCUPIED",),
            )

    expected_sequence = existing_entries[-1].sequence_number + 1
    if candidate.sequence_number != expected_sequence:
        return _append_result(
            LedgerAppendStatus.REJECTED,
            candidate.entry_id,
            None,
            ("SEQUENCE_GAP_OR_ORDERING_VIOLATION",),
        )
    if candidate.previous_entry_digest != existing_entries[-1].entry_digest:
        return _append_result(
            LedgerAppendStatus.CONFLICT,
            candidate.entry_id,
            None,
            ("PREDECESSOR_MISMATCH",),
        )
    return _append_result(
        LedgerAppendStatus.APPENDED,
        candidate.entry_id,
        existing_entries + (candidate,),
        (),
    )


def _append_result(
    status: LedgerAppendStatus,
    candidate_entry_id: str | None,
    resulting_entries: tuple[PaperLedgerEntry, ...] | None,
    reason_codes: tuple[str, ...],
) -> PaperLedgerAppendResult:
    return PaperLedgerAppendResult(
        status=status,
        candidate_entry_id=candidate_entry_id,
        resulting_entries=resulting_entries,
        reason_codes=reason_codes,
    )


def _verify_simulation_input(value: PaperSimulationInput) -> None:
    if value.contract_version != P07_T01_CONTRACT_VERSION:
        raise ValueError("unsupported P07-T01 contract version")
    _verify_digest(value.canonical_representation, value.digest, "input_digest")
    _verify_digest(
        value.authorization_observation.canonical_representation,
        value.authorization_observation.observation_digest,
        "observation_digest",
    )
    _verify_digest(
        value.execution_observation.canonical_representation,
        value.execution_observation.observation_digest,
        "observation_digest",
    )
    _verify_digest(
        value.simulation_configuration.canonical_representation,
        value.simulation_configuration.configuration_digest,
        "configuration_digest",
    )
    _verify_digest(
        value.initial_paper_state.canonical_representation,
        value.initial_paper_state.state_digest,
        "state_digest",
    )


def _verify_outcome(value: PaperFillOutcome) -> None:
    if value.contract_version != P07_T02_CONTRACT_VERSION:
        raise ValueError("unsupported P07-T02 contract version")
    if value.fill_model_version != P07_T02_FILL_MODEL_VERSION:
        raise ValueError("unsupported T02 fill model version")
    if value.friction_model_version != P07_T02_FRICTION_MODEL_VERSION:
        raise ValueError("unsupported T02 friction model version")
    _verify_digest(
        value.canonical_representation,
        value.outcome_digest,
        "outcome_digest",
    )


def _verify_transition(value: PaperStateTransitionResult) -> None:
    if value.contract_version != P07_T03_CONTRACT_VERSION:
        raise ValueError("unsupported P07-T03 contract version")
    _verify_digest(
        value.canonical_representation,
        value.transition_digest,
        "transition_digest",
    )
    _verify_state(value.prior_state)
    if value.next_state is not None:
        _verify_state(value.next_state)


def _verify_state(value: PaperPositionExposureState) -> None:
    _verify_digest(value.canonical_representation, value.digest, "state_digest")


def _verify_digest(
    representation: Mapping[str, Any],
    supplied: str | None,
    field: str,
) -> None:
    _require_digest(supplied, field)
    source = {
        key: value
        for key, value in representation.items()
        if key != field
    }
    expected = _digest(source)
    if supplied != expected:
        raise ValueError(f"{field} does not match canonical representation")


def _validate_status_linkage(
    outcome: PaperFillOutcome,
    transition: PaperStateTransitionResult,
) -> None:
    allowed = {
        FillOutcomeStatus.FILLED: {TransitionStatus.APPLIED},
        FillOutcomeStatus.PARTIALLY_FILLED: {TransitionStatus.APPLIED},
        FillOutcomeStatus.FAILED: {TransitionStatus.NO_CHANGE},
        FillOutcomeStatus.REJECTED: {
            TransitionStatus.NO_CHANGE,
            TransitionStatus.REJECTED,
        },
        FillOutcomeStatus.UNAVAILABLE: {TransitionStatus.UNAVAILABLE},
        FillOutcomeStatus.INVALID: {TransitionStatus.INVALID},
    }
    if transition.transition_status not in allowed[outcome.status]:
        raise ValueError("T02/T03 status contradiction")


def _validate_temporal_boundary(
    simulation_input: PaperSimulationInput,
    outcome: PaperFillOutcome,
    transition: PaperStateTransitionResult,
    reference: datetime,
) -> None:
    timestamps = [
        simulation_input.decision_intent.decision_time,
        simulation_input.simulation_reference_time,
        simulation_input.execution_observation.observation_time,
        simulation_input.execution_observation.availability_time,
        outcome.quote_observation_time,
        outcome.fill_time,
        transition.prior_state.as_of_time,
        transition.transition_reference_time,
    ]
    if transition.next_state is not None:
        timestamps.append(transition.next_state.as_of_time)
    if any(value is not None and _to_utc(value, "timestamp") > reference for value in timestamps):
        raise ValueError("timestamp is future relative to ledger_reference_time")
    if simulation_input.simulation_reference_time > reference:
        raise ValueError("simulation_reference_time is future")


def _simulation_identity(value: PaperSimulationInput) -> Mapping[str, Any]:
    decision = value.decision_intent.canonical_representation
    authorization = value.authorization_observation.canonical_representation
    execution = value.execution_observation.canonical_representation
    configuration = value.simulation_configuration.canonical_representation
    initial_state = value.initial_paper_state.canonical_representation
    replay = value.replay_identity.canonical_representation
    return {
        "p07_t01_input_digest": value.digest,
        "decision_intent": decision,
        "authorization_observation": authorization,
        "execution_observation": execution,
        "simulation_configuration": configuration,
        "initial_paper_state": initial_state,
        "replay_identity": replay,
        "decision_intent_digest": decision["decision_intent_digest"],
        "context_digest": decision["context_digest"],
        "replay_id": replay["replay_id"],
        "simulation_reference_time": value.simulation_reference_time,
    }


def _outcome_identity(value: PaperFillOutcome) -> Mapping[str, Any]:
    canonical = value.canonical_representation
    return {
        "outcome_digest": value.outcome_digest,
        "contract_version": value.contract_version,
        "fill_model_version": value.fill_model_version,
        "friction_model_version": value.friction_model_version,
        "status": value.status,
        "reason_codes": value.reason_codes,
        "side": value.side,
        "requested_quantity": value.requested_quantity,
        "filled_quantity": value.filled_quantity,
        "remaining_quantity": value.remaining_quantity,
        "quantity_unit": value.quantity_unit,
        "price_unit": value.price_unit,
        "fee_unit": value.fee_unit,
        "execution_observation_id": value.execution_observation_id,
        "execution_observation_digest": value.execution_observation_digest,
        "canonical_representation": canonical,
    }


def _transition_identity(value: PaperStateTransitionResult) -> Mapping[str, Any]:
    return {
        "transition_digest": value.transition_digest,
        "contract_version": value.contract_version,
        "transition_status": value.transition_status,
        "transition_reference_time": value.transition_reference_time,
        "reason_codes": value.reason_codes,
        "outcome_digest": value.outcome_identity.get("outcome_digest"),
        "canonical_representation": value.canonical_representation,
    }


def _state_identity(value: PaperPositionExposureState) -> Mapping[str, Any]:
    return {
        "state_id": value.state_id,
        "state_version": value.state_version,
        "state_digest": value.digest,
        "portfolio_scope": value.portfolio_scope,
        "state_quality": value.state_quality,
        "state_as_of_time": value.as_of_time,
    }


def _timestamps(
    simulation_input: PaperSimulationInput,
    outcome: PaperFillOutcome,
    transition: PaperStateTransitionResult,
    reference: datetime,
) -> Mapping[str, Any]:
    return {
        "decision_time": simulation_input.decision_intent.decision_time,
        "simulation_reference_time": simulation_input.simulation_reference_time,
        "execution_observation_time": (
            simulation_input.execution_observation.observation_time
        ),
        "execution_availability_time": (
            simulation_input.execution_observation.availability_time
        ),
        "quote_observation_time": outcome.quote_observation_time,
        "fill_time": outcome.fill_time,
        "transition_reference_time": transition.transition_reference_time,
        "ledger_reference_time": reference,
    }


def _effects(value: PaperStateTransitionResult) -> Mapping[str, Any]:
    return {
        "quantity_effect": value.quantity_effect.canonical_representation,
        "accounting_effect": value.accounting_effect.canonical_representation,
        "exposure_effect": value.exposure_effect.canonical_representation,
        "effect_status": (
            "APPLIED"
            if value.transition_status is TransitionStatus.APPLIED
            else "NOT_APPLIED"
        ),
        "rounding_mode": value.canonical_representation["rounding_mode"],
        "max_decimal_places": value.canonical_representation[
            "max_decimal_places"
        ],
    }


def _valid_existing_sequence(
    entries: tuple[PaperLedgerEntry, ...],
) -> bool:
    if not entries:
        return True
    first = entries[0]
    if (
        first.sequence_number != 1
        or first.previous_entry_digest is not None
        or _append_policy(first) != P07_T04_APPEND_POLICY_VERSION
    ):
        return False
    seen_ids: set[str] = set()
    seen_events: set[str] = set()
    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.sequence_number != expected_sequence:
            return False
        if entry.ledger_stream_identity != first.ledger_stream_identity:
            return False
        if _append_policy(entry) != _append_policy(first):
            return False
        if entry.entry_id in seen_ids or entry.event_identity_digest in seen_events:
            return False
        seen_ids.add(entry.entry_id)
        seen_events.add(entry.event_identity_digest)
        if expected_sequence > 1 and entry.previous_entry_digest != entries[
            expected_sequence - 2
        ].entry_digest:
            return False
    return True


def _append_policy(entry: PaperLedgerEntry) -> Any:
    return entry.provenance.get("append_policy_version")


def _canonical_mapping(value: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return _freeze(_canonicalize(value))


def _canonical_texts(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{name} must be a tuple or list")
    values = []
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError(f"{name} must contain canonical text")
        values.append(item)
    return tuple(sorted(dict.fromkeys(values)))


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Decimal must be finite")
        normalized = Decimal("0") if value == 0 else value.normalize()
        return format(normalized, "f")
    if isinstance(value, datetime):
        return _timestamp_text(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("mapping keys must be strings")
        return {
            key: _canonicalize(value[key])
            for key in sorted(value)
        }
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float):
        raise ValueError("float values are not canonical; use Decimal")
    raise ValueError(f"{type(value).__name__} is not canonical")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(child) for key, child in value.items()}
        )
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(child) for child in value)
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonicalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _require_digest(value: Any, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != _DIGEST_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _to_utc(value: Any, name: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _timestamp_text(value: datetime) -> str:
    return (
        _to_utc(value, "timestamp")
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


__all__ = [
    "LedgerAppendStatus",
    "P07_T04_APPEND_POLICY_VERSION",
    "P07_T04_CANONICALIZATION_VERSION",
    "P07_T04_CONTRACT_VERSION",
    "P07_T04_LEDGER_MODEL_VERSION",
    "PaperLedgerAppendResult",
    "PaperLedgerEntry",
    "append_paper_ledger_entry",
    "create_paper_ledger_entry",
]