"""Deterministic, immutable P07-T05 paper reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.execution.paper_ledger import PaperLedgerEntry


P07_T05_CONTRACT_VERSION = "p07-t05-v1"
P07_T05_RECONCILIATION_MODEL_VERSION = "p07-t05-reconciliation-v1"
P07_T05_DISCREPANCY_TAXONOMY_VERSION = "p07-t05-taxonomy-v1"
P07_T05_CANONICALIZATION_VERSION = "p07-t05-canonical-v1"
P07_T05_COMPARISON_POLICY_VERSION = "p07-t05-comparison-v1"

_DIGEST_LENGTH = 64
_ALLOWED_EXPECTATION_KEYS = frozenset(
    {
        "ledger_stream_identity",
        "sequence_number",
        "entry_id",
        "event_identity_digest",
        "entry_digest",
        "p07_t01_input_digest",
        "replay_id",
        "decision_intent_digest",
        "outcome_digest",
        "transition_digest",
        "prior_state_digest",
        "resulting_state_digest",
        "status",
        "transition_status",
        "prior_state_identity",
        "resulting_state_identity",
        "outcome_identity",
        "transition_identity",
        "reason_codes",
        "timestamps",
        "expected_ledger_reference_time",
        "expected_presence",
        "expected_canonical",
    }
)
_IDENTITY_KEYS = frozenset(
    {
        "ledger_stream_identity",
        "entry_id",
        "event_identity_digest",
        "p07_t01_input_digest",
        "decision_intent_digest",
        "outcome_digest",
        "transition_digest",
        "prior_state_digest",
        "resulting_state_digest",
    }
)
_DIGEST_KEYS = frozenset(
    {
        "entry_id",
        "event_identity_digest",
        "entry_digest",
        "p07_t01_input_digest",
        "decision_intent_digest",
        "outcome_digest",
        "transition_digest",
        "prior_state_digest",
        "resulting_state_digest",
    }
)
_TIMESTAMP_ORDER = (
    "decision_time",
    "execution_observation_time",
    "execution_availability_time",
    "quote_observation_time",
    "fill_time",
    "simulation_reference_time",
    "transition_reference_time",
    "ledger_reference_time",
)


class ReconciliationStatus(StrEnum):
    """Closed status taxonomy for one reconciliation evaluation."""

    MATCH = "MATCH"
    MISSING = "MISSING"
    DUPLICATE = "DUPLICATE"
    DELAYED = "DELAYED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    UNEXPECTED = "UNEXPECTED"
    CONTRADICTORY = "CONTRADICTORY"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    DIGEST_MISMATCH = "DIGEST_MISMATCH"
    SEQUENCE_MISMATCH = "SEQUENCE_MISMATCH"
    TIMESTAMP_MISMATCH = "TIMESTAMP_MISMATCH"
    STATE_MISMATCH = "STATE_MISMATCH"
    REPLAY_MISMATCH = "REPLAY_MISMATCH"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


class ObservationAvailability(StrEnum):
    """Availability of the explicitly supplied comparison observation."""

    AVAILABLE = "AVAILABLE"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"


DiscrepancyStatus = ReconciliationStatus
ReconciliationObservationStatus = ObservationAvailability


@dataclass(frozen=True)
class PaperReconciliationExpectation:
    """Immutable, caller-supplied expectation or replay observation."""

    expectation_id: str
    replay_id: str
    expected_fields: Mapping[str, Any]
    comparison_reference_time: datetime
    observation_status: ObservationAvailability | str = (
        ObservationAvailability.AVAILABLE
    )
    observed_at: datetime | None = None
    available_at: datetime | None = None
    reason_codes: tuple[str, ...] = ()
    contract_version: str = P07_T05_CONTRACT_VERSION
    reconciliation_model_version: str = P07_T05_RECONCILIATION_MODEL_VERSION
    expectation_digest: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.expectation_id, "expectation_id")
        _require_text(self.replay_id, "replay_id")
        try:
            object.__setattr__(
                self,
                "observation_status",
                ObservationAvailability(self.observation_status),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported observation_status") from error
        if self.contract_version != P07_T05_CONTRACT_VERSION:
            raise ValueError("unsupported P07-T05 contract_version")
        if (
            self.reconciliation_model_version
            != P07_T05_RECONCILIATION_MODEL_VERSION
        ):
            raise ValueError(
                "unsupported P07-T05 reconciliation_model_version"
            )
        object.__setattr__(
            self,
            "expected_fields",
            _freeze_mapping(self.expected_fields, "expected_fields"),
        )
        object.__setattr__(
            self,
            "comparison_reference_time",
            _to_utc(
                self.comparison_reference_time,
                "comparison_reference_time",
            ),
        )
        if self.observed_at is not None:
            object.__setattr__(
                self,
                "observed_at",
                _to_utc(self.observed_at, "observed_at"),
            )
        if self.available_at is not None:
            object.__setattr__(
                self,
                "available_at",
                _to_utc(self.available_at, "available_at"),
            )
        if (
            self.observed_at is not None
            and self.available_at is not None
            and self.observed_at > self.available_at
        ):
            raise ValueError("observed_at cannot follow available_at")
        object.__setattr__(
            self,
            "reason_codes",
            _canonical_texts(self.reason_codes, "reason_codes"),
        )
        if self.observation_status in {
            ObservationAvailability.UNKNOWN,
            ObservationAvailability.UNAVAILABLE,
        } and not self.reason_codes:
            raise ValueError(
                "unknown or unavailable observation requires reason_codes"
            )
        expected = _digest(self._canonical_without_digest())
        if self.expectation_digest is not None:
            _require_digest(self.expectation_digest, "expectation_digest")
            if self.expectation_digest != expected:
                raise ValueError(
                    "expectation_digest does not match canonical expectation"
                )
        object.__setattr__(self, "expectation_digest", expected)

    def _canonical_without_digest(self) -> Mapping[str, Any]:
        return {
            "contract_version": self.contract_version,
            "reconciliation_model_version": self.reconciliation_model_version,
            "expectation_id": self.expectation_id,
            "replay_id": self.replay_id,
            "expected_fields": self.expected_fields,
            "comparison_reference_time": self.comparison_reference_time,
            "observation_status": self.observation_status,
            "observed_at": self.observed_at,
            "available_at": self.available_at,
            "reason_codes": self.reason_codes,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                **self._canonical_without_digest(),
                "expectation_digest": self.expectation_digest,
            }
        )

    deterministic_representation = property(
        lambda self: self.canonical_representation
    )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "PaperReconciliationExpectation":
        allowed = {
            "expectation_id",
            "replay_id",
            "expected_fields",
            "expected",
            "comparison_reference_time",
            "observation_status",
            "observed_at",
            "available_at",
            "reason_codes",
            "contract_version",
            "reconciliation_model_version",
            "expectation_digest",
        }
        if not isinstance(value, Mapping):
            raise ValueError("PaperReconciliationExpectation must be a mapping")
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unsupported PaperReconciliationExpectation fields: "
                + ", ".join(unknown)
            )
        fields = value.get("expected_fields", value.get("expected"))
        if fields is None:
            raise ValueError("missing expected_fields")
        values = dict(value)
        values["expected_fields"] = fields
        values.pop("expected", None)
        return cls(**values)


@dataclass(frozen=True)
class PaperReconciliationResult:
    """Immutable result of comparing supplied paper records and expectations."""

    status: ReconciliationStatus | str
    reason_codes: tuple[str, ...]
    expectation_identity: Mapping[str, Any] | None
    compared_entry_ids: tuple[str, ...]
    compared_entry_digests: tuple[str, ...]
    ledger_stream_identity: Mapping[str, Any] | None
    p07_t01_input_digest: str | None
    replay_identity: Mapping[str, Any] | None
    decision_intent_digest: str | None
    outcome_identity: Mapping[str, Any] | None
    transition_identity: Mapping[str, Any] | None
    prior_state_identity: Mapping[str, Any] | None
    resulting_state_identity: Mapping[str, Any] | None
    timestamps: Mapping[str, Any]
    provenance: Mapping[str, Any]
    contract_version: str = P07_T05_CONTRACT_VERSION
    reconciliation_model_version: str = P07_T05_RECONCILIATION_MODEL_VERSION
    discrepancy_taxonomy_version: str = (
        P07_T05_DISCREPANCY_TAXONOMY_VERSION
    )
    canonicalization_version: str = P07_T05_CANONICALIZATION_VERSION
    comparison_policy_version: str = P07_T05_COMPARISON_POLICY_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "status", ReconciliationStatus(self.status))
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported reconciliation status") from error
        versions = (
            (self.contract_version, P07_T05_CONTRACT_VERSION, "contract_version"),
            (
                self.reconciliation_model_version,
                P07_T05_RECONCILIATION_MODEL_VERSION,
                "reconciliation_model_version",
            ),
            (
                self.discrepancy_taxonomy_version,
                P07_T05_DISCREPANCY_TAXONOMY_VERSION,
                "discrepancy_taxonomy_version",
            ),
            (
                self.canonicalization_version,
                P07_T05_CANONICALIZATION_VERSION,
                "canonicalization_version",
            ),
            (
                self.comparison_policy_version,
                P07_T05_COMPARISON_POLICY_VERSION,
                "comparison_policy_version",
            ),
        )
        for supplied, expected, name in versions:
            if supplied != expected:
                raise ValueError(f"unsupported P07-T05 {name}")
        for value, name in (
            (self.expectation_identity, "expectation_identity"),
            (self.ledger_stream_identity, "ledger_stream_identity"),
            (self.replay_identity, "replay_identity"),
            (self.outcome_identity, "outcome_identity"),
            (self.transition_identity, "transition_identity"),
            (self.prior_state_identity, "prior_state_identity"),
            (self.resulting_state_identity, "resulting_state_identity"),
            (self.timestamps, "timestamps"),
            (self.provenance, "provenance"),
        ):
            if value is not None:
                object.__setattr__(self, name, _freeze_mapping(value, name))
        object.__setattr__(
            self,
            "reason_codes",
            _canonical_texts(self.reason_codes, "reason_codes"),
        )
        object.__setattr__(
            self,
            "compared_entry_ids",
            _canonical_digests(self.compared_entry_ids, "compared_entry_ids"),
        )
        object.__setattr__(
            self,
            "compared_entry_digests",
            _canonical_digests(
                self.compared_entry_digests,
                "compared_entry_digests",
            ),
        )
        expected = _digest(self._canonical_without_digest())
        if self.result_digest is not None:
            _require_digest(self.result_digest, "result_digest")
            if self.result_digest != expected:
                raise ValueError(
                    "result_digest does not match canonical result"
                )
        object.__setattr__(self, "result_digest", expected)

    def _canonical_without_digest(self) -> Mapping[str, Any]:
        return {
            "contract_version": self.contract_version,
            "reconciliation_model_version": self.reconciliation_model_version,
            "discrepancy_taxonomy_version": self.discrepancy_taxonomy_version,
            "canonicalization_version": self.canonicalization_version,
            "comparison_policy_version": self.comparison_policy_version,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "expectation_identity": self.expectation_identity,
            "compared_entry_ids": self.compared_entry_ids,
            "compared_entry_digests": self.compared_entry_digests,
            "ledger_stream_identity": self.ledger_stream_identity,
            "p07_t01_input_digest": self.p07_t01_input_digest,
            "replay_identity": self.replay_identity,
            "decision_intent_digest": self.decision_intent_digest,
            "outcome_identity": self.outcome_identity,
            "transition_identity": self.transition_identity,
            "prior_state_identity": self.prior_state_identity,
            "resulting_state_identity": self.resulting_state_identity,
            "timestamps": self.timestamps,
            "provenance": self.provenance,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                **self._canonical_without_digest(),
                "result_digest": self.result_digest,
            }
        )

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]

    deterministic_representation = property(
        lambda self: self.canonical_representation
    )


def reconcile_paper_ledger(
    ledger_entries: tuple[PaperLedgerEntry, ...],
    expectation: PaperReconciliationExpectation | Mapping[str, Any],
) -> PaperReconciliationResult:
    """Compare supplied immutable ledger state to one supplied expectation."""

    expected: PaperReconciliationExpectation | None = None
    try:
        expected = _coerce_expectation(expectation)
    except (TypeError, ValueError) as error:
        return _make_result(
            ReconciliationStatus.INVALID,
            ("INVALID_EXPECTATION:" + type(error).__name__,),
            None,
            (),
            (),
            (),
            None,
        )

    try:
        entries = _validate_entries(ledger_entries)
    except (TypeError, ValueError) as error:
        return _make_result(
            ReconciliationStatus.INVALID,
            ("INVALID_LEDGER:" + type(error).__name__,),
            expected,
            (),
            (),
            (),
            None,
        )

    try:
        _validate_expectation(expected)
    except (TypeError, ValueError) as error:
        return _make_result(
            ReconciliationStatus.INVALID,
            ("INVALID_EXPECTATION:" + type(error).__name__,),
            expected,
            entries,
            (),
            (),
            None,
        )

    if expected.observation_status is not ObservationAvailability.AVAILABLE:
        status = ReconciliationStatus.UNAVAILABLE
        reason = (
            "OBSERVATION_UNKNOWN"
            if expected.observation_status is ObservationAvailability.UNKNOWN
            else "OBSERVATION_UNAVAILABLE"
        )
        return _make_result(
            status,
            tuple(sorted(set(expected.reason_codes) | {reason})),
            expected,
            entries,
            (),
            (),
            None,
        )

    timestamp_status = _validate_future_data(entries, expected)
    if timestamp_status is not None:
        status, reasons = timestamp_status
        return _make_result(
            status,
            reasons,
            expected,
            entries,
            entries,
            (),
            None,
        )

    expected_fields = expected.expected_fields
    if expected_fields.get("expected_presence", True) is False:
        if entries:
            return _make_result(
                ReconciliationStatus.UNEXPECTED,
                ("UNEXPECTED_EVENT",),
                expected,
                entries,
                entries,
                (),
                None,
            )
        return _make_result(
            ReconciliationStatus.MATCH,
            (),
            expected,
            entries,
            (),
            (),
            None,
        )

    candidates = _select_candidates(entries, expected_fields)
    if candidates is None:
        return _make_result(
            ReconciliationStatus.CONTRADICTORY,
            ("EXPECTATION_IDENTITIES_CONFLICT",),
            expected,
            entries,
            entries,
            (),
            None,
        )
    if not candidates:
        if not entries:
            return _make_result(
                ReconciliationStatus.MISSING,
                ("EXPECTED_EVENT_MISSING",),
                expected,
                entries,
                (),
                (),
                None,
            )
        if _sequence_is_present(entries, expected_fields):
            return _make_result(
                ReconciliationStatus.IDENTITY_MISMATCH,
                ("EXPECTED_IDENTITY_NOT_FOUND",),
                expected,
                entries,
                entries,
                (),
                None,
            )
        return _make_result(
            ReconciliationStatus.MISSING,
            ("EXPECTED_EVENT_MISSING",),
            expected,
            entries,
            (),
            (),
            None,
        )
    if len(candidates) > 1:
        return _make_result(
            ReconciliationStatus.DUPLICATE,
            ("DUPLICATE_EVENT_IDENTITY",),
            expected,
            entries,
            candidates,
            (),
            None,
        )

    candidate = candidates[0]
    status, reasons = _compare_candidate(candidate, expected)
    delayed_reference = expected_fields.get("expected_ledger_reference_time")
    if (
        status is ReconciliationStatus.MATCH
        and delayed_reference is not None
        and _timestamp(candidate.timestamps["ledger_reference_time"])
        > _timestamp(delayed_reference)
    ):
        status = ReconciliationStatus.DELAYED
        reasons = ("EVENT_DELIVERED_AFTER_EXPECTED_TIME",)
    return _make_result(
        status,
        reasons,
        expected,
        entries,
        (candidate,),
        (),
        candidate,
    )


reconcile_paper_ledger_entries = reconcile_paper_ledger
reconcile_paper_ledger_state = reconcile_paper_ledger


def _make_result(
    status: ReconciliationStatus,
    reasons: tuple[str, ...],
    expectation: PaperReconciliationExpectation | None,
    entries: tuple[PaperLedgerEntry, ...],
    compared: tuple[PaperLedgerEntry, ...],
    extra_digests: tuple[str, ...],
    candidate: PaperLedgerEntry | None,
) -> PaperReconciliationResult:
    source = candidate or (compared[0] if compared else None)
    entry_ids = tuple(entry.entry_id for entry in compared)
    entry_digests = tuple(entry.entry_digest for entry in compared)
    if extra_digests:
        entry_digests = tuple(entry_digests) + tuple(extra_digests)
    expectation_identity = (
        expectation.canonical_representation if expectation else None
    )
    timestamps: Mapping[str, Any] = {
        "comparison_reference_time": (
            expectation.comparison_reference_time if expectation else None
        ),
        "observation_time": expectation.observed_at if expectation else None,
        "availability_time": expectation.available_at if expectation else None,
        "ledger_reference_times": tuple(
            entry.timestamps["ledger_reference_time"] for entry in compared
        ),
    }
    provenance: Mapping[str, Any] = {
        "source_contract": "P07-T05",
        "comparison_input": "supplied-paper-ledger-and-expectation",
        "expectation_id": expectation.expectation_id if expectation else None,
        "expectation_digest": (
            expectation.expectation_digest if expectation else None
        ),
        "compared_entry_ids": entry_ids,
        "compared_entry_digests": entry_digests,
    }
    if expectation is not None:
        provenance = {
            **provenance,
            "observation_status": expectation.observation_status,
            "observation_reason_codes": expectation.reason_codes,
        }
    if source is not None:
        provenance = {
            **provenance,
            "ledger_contract_version": source.contract_version,
            "ledger_model_version": source.ledger_model_version,
        }
    return PaperReconciliationResult(
        status=status,
        reason_codes=reasons,
        expectation_identity=expectation_identity,
        compared_entry_ids=entry_ids,
        compared_entry_digests=entry_digests,
        ledger_stream_identity=(
            source.ledger_stream_identity if source is not None else None
        ),
        p07_t01_input_digest=(
            source.simulation_identity["p07_t01_input_digest"]
            if source is not None
            else None
        ),
        replay_identity=(
            source.simulation_identity["replay_identity"]
            if source is not None
            else None
        ),
        decision_intent_digest=(
            source.simulation_identity["decision_intent_digest"]
            if source is not None
            else None
        ),
        outcome_identity=(
            source.outcome_identity if source is not None else None
        ),
        transition_identity=(
            source.transition_identity if source is not None else None
        ),
        prior_state_identity=(
            source.prior_state_identity if source is not None else None
        ),
        resulting_state_identity=(
            source.resulting_state_identity if source is not None else None
        ),
        timestamps=timestamps,
        provenance=provenance,
    )


def _coerce_expectation(
    value: PaperReconciliationExpectation | Mapping[str, Any],
) -> PaperReconciliationExpectation:
    if isinstance(value, PaperReconciliationExpectation):
        return value
    if isinstance(value, Mapping):
        return PaperReconciliationExpectation.from_mapping(value)
    raise TypeError("expectation must be PaperReconciliationExpectation")


def _validate_entries(
    entries: tuple[PaperLedgerEntry, ...],
) -> tuple[PaperLedgerEntry, ...]:
    if not isinstance(entries, tuple):
        raise TypeError("ledger_entries must be an immutable tuple")
    if any(not isinstance(entry, PaperLedgerEntry) for entry in entries):
        raise TypeError("ledger_entries must contain PaperLedgerEntry values")
    if not entries:
        return entries
    first = entries[0]
    seen_entry_ids: set[str] = set()
    seen_events: dict[str, PaperLedgerEntry] = {}
    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.sequence_number != expected_sequence:
            raise ValueError("sequence mismatch")
        if entry.ledger_stream_identity != first.ledger_stream_identity:
            raise ValueError("ledger stream mismatch")
        if _entry_event_digest(entry) != entry.event_identity_digest:
            raise ValueError("event identity digest mismatch")
        if _entry_id(entry) != entry.entry_id:
            raise ValueError("entry identity digest mismatch")
        if _entry_digest(entry) != entry.entry_digest:
            raise ValueError("entry digest mismatch")
        if entry.entry_id in seen_entry_ids:
            raise ValueError("duplicate entry identity")
        if entry.event_identity_digest in seen_events:
            previous = seen_events[entry.event_identity_digest]
            if previous.canonical_representation != entry.canonical_representation:
                raise ValueError("conflicting duplicate event identity")
            raise ValueError("duplicate event identity")
        seen_entry_ids.add(entry.entry_id)
        seen_events[entry.event_identity_digest] = entry
        if expected_sequence == 1:
            if entry.previous_entry_digest is not None:
                raise ValueError("first predecessor mismatch")
        elif entry.previous_entry_digest != entries[expected_sequence - 2].entry_digest:
            raise ValueError("predecessor mismatch")
    return entries


def _validate_expectation(
    expectation: PaperReconciliationExpectation,
) -> None:
    fields = expectation.expected_fields
    unknown = sorted(set(fields) - _ALLOWED_EXPECTATION_KEYS)
    if unknown:
        raise ValueError("unsupported expectation fields: " + ", ".join(unknown))
    if not isinstance(fields.get("expected_presence", True), bool):
        raise ValueError("expected_presence must be boolean")
    if expectation.observation_status is not ObservationAvailability.AVAILABLE:
        return
    if fields.get("expected_presence", True) is False:
        return
    if not any(key in fields for key in ("entry_id", "event_identity_digest", "sequence_number")):
        raise ValueError("available expectation is missing event identity")
    for key in _DIGEST_KEYS:
        if key in fields:
            _require_digest(fields[key], key)
    if "sequence_number" in fields:
        sequence = fields["sequence_number"]
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= 0:
            raise ValueError("sequence_number must be a positive integer")
    if "timestamps" in fields:
        if not isinstance(fields["timestamps"], Mapping):
            raise ValueError("expected timestamps must be a mapping")
        for name, value in fields["timestamps"].items():
            if name not in _TIMESTAMP_ORDER:
                raise ValueError("unsupported expected timestamp")
            _timestamp(value)
    if "expected_ledger_reference_time" in fields:
        _timestamp(fields["expected_ledger_reference_time"])
    _validate_expected_canonical(fields)


def _validate_expected_canonical(fields: Mapping[str, Any]) -> None:
    canonical = fields.get("expected_canonical")
    if canonical is None:
        return
    if not isinstance(canonical, Mapping):
        raise ValueError("expected_canonical must be a mapping")
    if "entry_digest" not in canonical:
        raise ValueError("expected_canonical requires entry_digest")
    _require_digest(canonical["entry_digest"], "expected_canonical.entry_digest")
    without_digest = {
        key: value for key, value in canonical.items() if key != "entry_digest"
    }
    if _digest(without_digest) != canonical["entry_digest"]:
        raise ValueError("expected canonical entry digest mismatch")


def _validate_future_data(
    entries: tuple[PaperLedgerEntry, ...],
    expectation: PaperReconciliationExpectation,
) -> tuple[ReconciliationStatus, tuple[str, ...]] | None:
    reference = expectation.comparison_reference_time
    supplied_times = (
        expectation.observed_at,
        expectation.available_at,
        reference,
    )
    if any(value is not None and value > reference for value in supplied_times[:2]):
        return (
            ReconciliationStatus.TIMESTAMP_MISMATCH,
            ("FUTURE_DATA_LEAKAGE",),
        )
    for entry in entries:
        for value in entry.timestamps.values():
            if value is None:
                continue
            try:
                if _timestamp_as_datetime(value) > reference:
                    return (
                        ReconciliationStatus.TIMESTAMP_MISMATCH,
                        ("FUTURE_DATA_LEAKAGE",),
                    )
            except (TypeError, ValueError):
                return (
                    ReconciliationStatus.INVALID,
                    ("UNSUPPORTED_TIMESTAMP_REPRESENTATION",),
                )
    return None


def _select_candidates(
    entries: tuple[PaperLedgerEntry, ...],
    fields: Mapping[str, Any],
) -> tuple[PaperLedgerEntry, ...] | None:
    selectors = {
        key: fields[key]
        for key in (
            "entry_id",
            "event_identity_digest",
            "sequence_number",
        )
        if key in fields
    }
    if not selectors:
        return ()
    matches = []
    for entry in entries:
        view = _entry_view(entry)
        matched = [view[key] == value for key, value in selectors.items()]
        if all(matched):
            matches.append(entry)
    if matches:
        return tuple(matches)
    independent_matches = [
        {
            entry.entry_id
            for entry in entries
            if _entry_view(entry)[key] == value
        }
        for key, value in selectors.items()
    ]
    non_empty = [values for values in independent_matches if values]
    if len(non_empty) > 1 and len(set.intersection(*non_empty)) == 0:
        return None
    return ()


def _sequence_is_present(
    entries: tuple[PaperLedgerEntry, ...],
    fields: Mapping[str, Any],
) -> bool:
    sequence = fields.get("sequence_number")
    return sequence is not None and any(
        entry.sequence_number == sequence for entry in entries
    )


def _compare_candidate(
    entry: PaperLedgerEntry,
    expectation: PaperReconciliationExpectation,
) -> tuple[ReconciliationStatus, tuple[str, ...]]:
    fields = expectation.expected_fields
    view = _entry_view(entry)
    mismatches: list[tuple[ReconciliationStatus, str]] = []

    for key, expected_value in fields.items():
        if key in {"expected_presence", "expected_ledger_reference_time"}:
            continue
        if key == "timestamps":
            actual = view["timestamps"]
            for timestamp_key, value in expected_value.items():
                if actual.get(timestamp_key) != _canonicalize(value):
                    mismatches.append(
                        (ReconciliationStatus.TIMESTAMP_MISMATCH, timestamp_key)
                    )
            continue
        if key == "expected_canonical":
            if _canonicalize(expected_value) != _canonicalize(
                entry.canonical_representation
            ):
                mismatches.append(
                    (ReconciliationStatus.DIGEST_MISMATCH, "expected_canonical")
                )
            continue
        actual_value = view.get(key)
        expected_canonical = _canonicalize(expected_value)
        if actual_value == expected_canonical:
            continue
        if key == "replay_id":
            mismatch_status = ReconciliationStatus.REPLAY_MISMATCH
        elif key == "sequence_number":
            mismatch_status = ReconciliationStatus.SEQUENCE_MISMATCH
        elif key in {"prior_state_digest", "resulting_state_digest", "prior_state_identity", "resulting_state_identity"}:
            mismatch_status = ReconciliationStatus.STATE_MISMATCH
        elif key in _DIGEST_KEYS:
            mismatch_status = ReconciliationStatus.DIGEST_MISMATCH
        elif key in _IDENTITY_KEYS or key in {"outcome_identity", "transition_identity"}:
            mismatch_status = ReconciliationStatus.IDENTITY_MISMATCH
        elif key == "status":
            if actual_value == "PARTIALLY_FILLED":
                mismatch_status = ReconciliationStatus.PARTIAL
            elif actual_value in {"FAILED", "REJECTED"}:
                mismatch_status = ReconciliationStatus.FAILED
            else:
                mismatch_status = ReconciliationStatus.CONTRADICTORY
        elif key == "transition_status":
            mismatch_status = ReconciliationStatus.CONTRADICTORY
        elif key == "reason_codes":
            mismatch_status = ReconciliationStatus.CONTRADICTORY
        else:
            mismatch_status = ReconciliationStatus.IDENTITY_MISMATCH
        mismatches.append((mismatch_status, key))

    if not mismatches:
        return ReconciliationStatus.MATCH, ()
    priorities = {
        ReconciliationStatus.CONTRADICTORY: 0,
        ReconciliationStatus.DIGEST_MISMATCH: 1,
        ReconciliationStatus.IDENTITY_MISMATCH: 2,
        ReconciliationStatus.REPLAY_MISMATCH: 3,
        ReconciliationStatus.SEQUENCE_MISMATCH: 4,
        ReconciliationStatus.TIMESTAMP_MISMATCH: 5,
        ReconciliationStatus.STATE_MISMATCH: 6,
        ReconciliationStatus.FAILED: 7,
        ReconciliationStatus.PARTIAL: 8,
    }
    status = min(mismatches, key=lambda item: priorities[item[0]])[0]
    return status, tuple(sorted({f"{status.value}:{key}" for status, key in mismatches}))


def _entry_view(entry: PaperLedgerEntry) -> Mapping[str, Any]:
    simulation = entry.simulation_identity
    outcome = entry.outcome_identity
    transition = entry.transition_identity
    return {
        "ledger_stream_identity": entry.ledger_stream_identity,
        "sequence_number": entry.sequence_number,
        "entry_id": entry.entry_id,
        "event_identity_digest": entry.event_identity_digest,
        "entry_digest": entry.entry_digest,
        "p07_t01_input_digest": simulation["p07_t01_input_digest"],
        "replay_id": simulation["replay_id"],
        "decision_intent_digest": simulation["decision_intent_digest"],
        "outcome_digest": outcome["outcome_digest"],
        "transition_digest": transition["transition_digest"],
        "prior_state_digest": entry.prior_state_identity["state_digest"],
        "resulting_state_digest": (
            entry.resulting_state_identity["state_digest"]
            if entry.resulting_state_identity is not None
            else None
        ),
        "status": outcome["status"],
        "transition_status": transition["transition_status"],
        "prior_state_identity": entry.prior_state_identity,
        "resulting_state_identity": entry.resulting_state_identity,
        "outcome_identity": outcome,
        "transition_identity": transition,
        "reason_codes": entry.reason_codes,
        "timestamps": entry.timestamps,
    }


def _entry_event_digest(entry: PaperLedgerEntry) -> str:
    return _digest(
        {
            "ledger_model_version": entry.ledger_model_version,
            "p07_t01_input_digest": entry.simulation_identity[
                "p07_t01_input_digest"
            ],
            "replay_id": entry.simulation_identity["replay_id"],
            "outcome_digest": entry.outcome_identity["outcome_digest"],
            "transition_digest": entry.transition_identity["transition_digest"],
            "prior_state_digest": entry.prior_state_identity["state_digest"],
            "resulting_state_digest": (
                entry.resulting_state_identity["state_digest"]
                if entry.resulting_state_identity is not None
                else None
            ),
            "transition_reference_time": entry.timestamps[
                "transition_reference_time"
            ],
            "ledger_reference_time": entry.timestamps["ledger_reference_time"],
        }
    )


def _entry_id(entry: PaperLedgerEntry) -> str:
    return _digest(
        {
            "ledger_stream_identity": entry.ledger_stream_identity,
            "sequence_number": entry.sequence_number,
            "previous_entry_digest": entry.previous_entry_digest,
            "event_identity_digest": entry.event_identity_digest,
        }
    )


def _entry_digest(entry: PaperLedgerEntry) -> str:
    value = dict(entry.canonical_representation)
    value.pop("entry_digest", None)
    return _digest(value)


def _freeze_mapping(value: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return _freeze(_canonicalize(value))


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(child) for key, child in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, datetime):
        return _timestamp(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("mapping keys must be strings")
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    raise ValueError(f"{type(value).__name__} is not canonical")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonicalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be canonical non-empty text")


def _canonical_texts(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{name} must be a tuple or list")
    for item in value:
        _require_text(item, name)
    return tuple(sorted(dict.fromkeys(value)))


def _canonical_digests(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{name} must be a tuple or list")
    for item in value:
        _require_digest(item, name)
    return tuple(value)


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


def _timestamp(value: Any) -> datetime | str:
    if isinstance(value, datetime):
        return _to_utc(value, "timestamp").isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z")
    if isinstance(value, str):
        if not value.endswith("Z"):
            raise ValueError("timestamp must be canonical UTC text")
        try:
            parsed = datetime.fromisoformat(value[:-1] + "+00:00")
        except ValueError as error:
            raise ValueError("unsupported timestamp representation") from error
        if _timestamp(parsed) != value:
            raise ValueError("timestamp must use canonical microseconds")
        return value
    raise ValueError("timestamp must be datetime or canonical UTC text")


def _timestamp_as_datetime(value: Any) -> datetime:
    canonical = _timestamp(value)
    if isinstance(canonical, datetime):
        return canonical
    return datetime.fromisoformat(canonical[:-1] + "+00:00")


__all__ = [
    "DiscrepancyStatus",
    "ObservationAvailability",
    "P07_T05_CANONICALIZATION_VERSION",
    "P07_T05_COMPARISON_POLICY_VERSION",
    "P07_T05_CONTRACT_VERSION",
    "P07_T05_DISCREPANCY_TAXONOMY_VERSION",
    "P07_T05_RECONCILIATION_MODEL_VERSION",
    "PaperReconciliationExpectation",
    "PaperReconciliationResult",
    "ReconciliationObservationStatus",
    "ReconciliationStatus",
    "reconcile_paper_ledger",
    "reconcile_paper_ledger_entries",
    "reconcile_paper_ledger_state",
]