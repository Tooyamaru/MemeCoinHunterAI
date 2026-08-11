"""Deterministic provider-neutral market-state materialization for P02-T08.

This module projects already accepted P02-T07 evidence into a local,
read-oriented current-state view. It does not collect market data, interpret
measurements, reconcile sources, or mutate upstream contexts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Iterable, Mapping, TypeAlias

from core.data.contracts import DataQuality, OrderingStatus, SequenceValue
from core.data.market_observations import (
    AcceptedMarketObservationEvidence,
    MarketObservationKind,
)


P02_T08_CONTRACT_VERSION = "p02-t08-v1"
MAX_METADATA_DEPTH = 8
MAX_METADATA_ITEMS = 64
MAX_METADATA_BYTES = 8192

MarketStateKey: TypeAlias = tuple[str, str, str, str]


class MarketStateOutcome(StrEnum):
    MATERIALIZED = "MATERIALIZED"
    UPDATED = "UPDATED"
    DUPLICATE = "DUPLICATE"
    CONTRADICTORY = "CONTRADICTORY"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    INVALID = "INVALID"
    INCOMPLETE = "INCOMPLETE"
    STALE = "STALE"
    REJECTED = "REJECTED"


class MarketStateReason(StrEnum):
    INVALID_EVIDENCE = "INVALID_EVIDENCE"
    INCOMPLETE_EVIDENCE = "INCOMPLETE_EVIDENCE"
    INVALID_IDENTITY = "INVALID_IDENTITY"
    EVIDENCE_IDENTITY_MISMATCH = "EVIDENCE_IDENTITY_MISMATCH"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"
    INVALID_DATA_AGE = "INVALID_DATA_AGE"
    EVIDENCE_NOT_ACCEPTED = "EVIDENCE_NOT_ACCEPTED"
    EVIDENCE_QUALITY_NOT_VALID = "EVIDENCE_QUALITY_NOT_VALID"
    UNSUPPORTED_OBSERVATION_KIND = "UNSUPPORTED_OBSERVATION_KIND"
    UNSUPPORTED_METADATA = "UNSUPPORTED_METADATA"
    METADATA_BOUNDS_EXCEEDED = "METADATA_BOUNDS_EXCEEDED"
    DUPLICATE_OBSERVATION = "DUPLICATE_OBSERVATION"
    CONTRADICTORY_OBSERVATION = "CONTRADICTORY_OBSERVATION"
    OUT_OF_ORDER_SEQUENCE = "OUT_OF_ORDER_SEQUENCE"
    UPDATE_REQUIRES_PRIOR_STATE = "UPDATE_REQUIRES_PRIOR_STATE"


@dataclass(frozen=True)
class MarketStateEntry:
    """One immutable current state projection."""

    key: MarketStateKey
    evidence: AcceptedMarketObservationEvidence
    entry_fingerprint: str
    contract_version: str = P02_T08_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not _valid_key(self.key):
            raise ValueError("key must contain four non-empty strings")
        if not isinstance(self.evidence, AcceptedMarketObservationEvidence):
            raise ValueError("evidence must be accepted P02-T07 evidence")
        if not _non_empty(self.entry_fingerprint):
            raise ValueError("entry_fingerprint is required")
        if not _non_empty(self.contract_version):
            raise ValueError("contract_version is required")

    @property
    def source_id(self) -> str:
        return self.key[0]

    @property
    def chain_id(self) -> str:
        return self.key[1]

    @property
    def token_identity(self) -> str:
        return self.key[2]

    @property
    def market_subject_id(self) -> str:
        return self.key[3]


CurrentMarketState = MarketStateEntry


@dataclass
class MarketStateContext:
    """Explicit mutable state owned by one P02-T08 materializer."""

    contract_version: str = P02_T08_CONTRACT_VERSION
    evaluation_id: str | None = None
    current_state: dict[MarketStateKey, MarketStateEntry] = field(default_factory=dict)
    accepted_evidence_fingerprints: dict[str, str] = field(default_factory=dict)
    latest_sequence_by_key: dict[MarketStateKey, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _non_empty(self.contract_version):
            raise ValueError("contract_version is required")
        if self.evaluation_id is not None and not _non_empty(self.evaluation_id):
            raise ValueError("evaluation_id must be non-empty when provided")
        if not isinstance(self.current_state, dict):
            raise ValueError("current_state must be a dictionary")
        if not isinstance(self.accepted_evidence_fingerprints, dict):
            raise ValueError("accepted_evidence_fingerprints must be a dictionary")
        if not isinstance(self.latest_sequence_by_key, dict):
            raise ValueError("latest_sequence_by_key must be a dictionary")
        for key, entry in self.current_state.items():
            if not _valid_key(key) or not isinstance(entry, MarketStateEntry):
                raise ValueError("current_state contains an invalid entry")
            if entry.key != key:
                raise ValueError("entry key does not match current_state key")
            sequence = entry.evidence.sequence
            if _integer_sequence(sequence):
                self.latest_sequence_by_key.setdefault(key, sequence)
            self.accepted_evidence_fingerprints.setdefault(
                entry.evidence.observation_id,
                _content_fingerprint(entry.evidence),
            )
        for key, sequence in self.latest_sequence_by_key.items():
            if not _valid_key(key) or not _integer_sequence(sequence):
                raise ValueError("latest sequence state is invalid")

    @property
    def state_version(self) -> str:
        return self.state_digest()

    def state_digest(self) -> str:
        material = {
            "contract_version": self.contract_version,
            "evaluation_id": self.evaluation_id,
            "current_state": [
                {
                    "key": list(key),
                    "entry": _entry_material(entry),
                }
                for key, entry in sorted(self.current_state.items())
            ],
            "accepted_evidence_fingerprints": dict(
                sorted(self.accepted_evidence_fingerprints.items())
            ),
            "latest_sequence_by_key": [
                {"key": list(key), "sequence": sequence}
                for key, sequence in sorted(self.latest_sequence_by_key.items())
            ],
        }
        return _digest(material)

    def snapshot(self) -> tuple[MarketStateEntry, ...]:
        """Return the current state in canonical key order."""

        return tuple(self.current_state[key] for key in sorted(self.current_state))


@dataclass(frozen=True)
class MarketStateResult:
    """Observable immutable result for accepted and rejected evidence."""

    result_id: str
    key: MarketStateKey | None
    outcome: MarketStateOutcome
    quality: DataQuality
    reason_codes: tuple[str, ...]
    predecessor_state_version: str
    predecessor_state_digest: str
    local_state_version: str
    local_state_digest: str
    entry: MarketStateEntry | None
    accepted: bool
    state_changed: bool

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.reason_codes

    @property
    def state(self) -> MarketStateEntry | None:
        return self.entry


class MarketStateMaterializer:
    """Materialize accepted P02-T07 evidence deterministically."""

    def __init__(
        self,
        *,
        context: MarketStateContext | None = None,
        contract_version: str = P02_T08_CONTRACT_VERSION,
        evaluation_id: str | None = None,
    ) -> None:
        if context is not None and not isinstance(context, MarketStateContext):
            raise ValueError("context must be a MarketStateContext")
        if not _non_empty(contract_version):
            raise ValueError("contract_version is required")
        if evaluation_id is not None and not _non_empty(evaluation_id):
            raise ValueError("evaluation_id must be non-empty when provided")
        self.context = context or MarketStateContext(
            contract_version=contract_version,
            evaluation_id=evaluation_id,
        )

    def process(self, evidence: object) -> MarketStateResult:
        """Materialize one already accepted P02-T07 evidence value."""

        before = self.context.state_digest()
        validation = _validate_evidence(evidence)
        if validation is not None:
            outcome, quality, reason, key = validation
            return self._rejected(
                evidence,
                key=key,
                outcome=outcome,
                quality=quality,
                reason=reason,
                before=before,
            )

        assert isinstance(evidence, AcceptedMarketObservationEvidence)
        key = _state_key(evidence)
        fingerprint = _content_fingerprint(evidence)
        prior_fingerprint = self.context.accepted_evidence_fingerprints.get(
            evidence.observation_id
        )
        if prior_fingerprint is not None:
            if prior_fingerprint == fingerprint:
                return self._rejected(
                    evidence,
                    key=key,
                    outcome=MarketStateOutcome.DUPLICATE,
                    quality=DataQuality.DUPLICATE,
                    reason=MarketStateReason.DUPLICATE_OBSERVATION.value,
                    before=before,
                )
            return self._rejected(
                evidence,
                key=key,
                outcome=MarketStateOutcome.CONTRADICTORY,
                quality=DataQuality.CONTRADICTORY,
                reason=MarketStateReason.CONTRADICTORY_OBSERVATION.value,
                before=before,
            )

        current = self.context.current_state.get(key)
        if current is not None:
            if evidence.observation_kind is MarketObservationKind.OBSERVED:
                if _subject_content_fingerprint(current.evidence) == _subject_content_fingerprint(
                    evidence
                ):
                    outcome = MarketStateOutcome.DUPLICATE
                    quality = DataQuality.DUPLICATE
                else:
                    outcome = MarketStateOutcome.CONTRADICTORY
                    quality = DataQuality.CONTRADICTORY
                return self._rejected(
                    evidence,
                    key=key,
                    outcome=outcome,
                    quality=quality,
                    reason=(
                        MarketStateReason.DUPLICATE_OBSERVATION.value
                        if outcome is MarketStateOutcome.DUPLICATE
                        else MarketStateReason.CONTRADICTORY_OBSERVATION.value
                    ),
                    before=before,
                )
            sequence_error = self._sequence_error(key, evidence.sequence)
            if sequence_error is MarketStateOutcome.CONTRADICTORY:
                return self._rejected(
                    evidence,
                    key=key,
                    outcome=MarketStateOutcome.CONTRADICTORY,
                    quality=DataQuality.CONTRADICTORY,
                    reason=MarketStateReason.CONTRADICTORY_OBSERVATION.value,
                    before=before,
                )
            if sequence_error is MarketStateOutcome.OUT_OF_ORDER:
                return self._rejected(
                    evidence,
                    key=key,
                    outcome=MarketStateOutcome.OUT_OF_ORDER,
                    quality=DataQuality.OUT_OF_ORDER,
                    reason=MarketStateReason.OUT_OF_ORDER_SEQUENCE.value,
                    before=before,
                )
        elif evidence.observation_kind is MarketObservationKind.UPDATED:
            return self._rejected(
                evidence,
                key=key,
                outcome=MarketStateOutcome.REJECTED,
                quality=DataQuality.INCOMPLETE,
                reason=MarketStateReason.UPDATE_REQUIRES_PRIOR_STATE.value,
                before=before,
            )

        entry = MarketStateEntry(
            key=key,
            evidence=evidence,
            entry_fingerprint=_entry_fingerprint(evidence),
            contract_version=self.context.contract_version,
        )
        self.context.current_state[key] = entry
        self.context.accepted_evidence_fingerprints[evidence.observation_id] = fingerprint
        if _integer_sequence(evidence.sequence):
            self.context.latest_sequence_by_key[key] = evidence.sequence
        after = self.context.state_digest()
        outcome = (
            MarketStateOutcome.MATERIALIZED
            if current is None
            else MarketStateOutcome.UPDATED
        )
        return MarketStateResult(
            result_id=_result_id(self.context.evaluation_id, evidence, outcome, before, after),
            key=key,
            outcome=outcome,
            quality=DataQuality.VALID,
            reason_codes=(),
            predecessor_state_version=before,
            predecessor_state_digest=before,
            local_state_version=after,
            local_state_digest=after,
            entry=entry,
            accepted=True,
            state_changed=True,
        )

    def process_batch(self, evidence: Iterable[object]) -> tuple[MarketStateResult, ...]:
        if not isinstance(evidence, (tuple, list)):
            raise ValueError("evidence must be a tuple or list")
        return tuple(self.process(item) for item in evidence)

    def materialize(self, evidence: Iterable[object]) -> tuple[MarketStateResult, ...]:
        return self.process_batch(evidence)

    def snapshot(self) -> tuple[MarketStateEntry, ...]:
        return self.context.snapshot()

    def _sequence_error(
        self, key: MarketStateKey, sequence: SequenceValue
    ) -> MarketStateOutcome | None:
        if not _integer_sequence(sequence):
            return None
        previous = self.context.latest_sequence_by_key.get(key)
        if previous is None:
            return None
        if sequence == previous:
            return MarketStateOutcome.CONTRADICTORY
        if sequence < previous:
            return MarketStateOutcome.OUT_OF_ORDER
        return None

    def _rejected(
        self,
        evidence: object,
        *,
        key: MarketStateKey | None,
        outcome: MarketStateOutcome,
        quality: DataQuality,
        reason: str,
        before: str,
    ) -> MarketStateResult:
        observation_id = (
            evidence.observation_id
            if isinstance(evidence, AcceptedMarketObservationEvidence)
            else None
        )
        return MarketStateResult(
            result_id=_digest(
                {
                    "evaluation_id": self.context.evaluation_id,
                    "observation_id": observation_id,
                    "key": list(key) if key is not None else None,
                    "outcome": outcome.value,
                    "before": before,
                }
            ),
            key=key,
            outcome=outcome,
            quality=quality,
            reason_codes=(reason,),
            predecessor_state_version=before,
            predecessor_state_digest=before,
            local_state_version=before,
            local_state_digest=before,
            entry=None,
            accepted=False,
            state_changed=False,
        )


MarketStateProcessor = MarketStateMaterializer
MarketStateProcessingContext = MarketStateContext
MarketState = MarketStateEntry


def materialize_market_state(
    evidence: Iterable[object],
    *,
    context: MarketStateContext | None = None,
    evaluation_id: str | None = None,
) -> tuple[MarketStateResult, ...]:
    return MarketStateMaterializer(
        context=context,
        evaluation_id=evaluation_id,
    ).process_batch(evidence)


def _validate_evidence(
    evidence: object,
) -> tuple[MarketStateOutcome, DataQuality, str, MarketStateKey | None] | None:
    if not isinstance(evidence, AcceptedMarketObservationEvidence):
        return (
            MarketStateOutcome.INVALID,
            DataQuality.INVALID,
            MarketStateReason.INVALID_EVIDENCE.value,
            None,
        )
    key = _state_key_if_valid(evidence)
    if not evidence.accepted:
        return (
            MarketStateOutcome.REJECTED,
            DataQuality.INVALID,
            MarketStateReason.EVIDENCE_NOT_ACCEPTED.value,
            key,
        )
    if evidence.quality is not DataQuality.VALID or evidence.quality_status is not DataQuality.VALID:
        quality = (
            evidence.quality
            if isinstance(evidence.quality, DataQuality)
            else DataQuality.INVALID
        )
        outcome = MarketStateOutcome.STALE if quality is DataQuality.STALE else MarketStateOutcome.REJECTED
        reason = (
            MarketStateReason.EVIDENCE_QUALITY_NOT_VALID.value
            if quality is not DataQuality.STALE
            else MarketStateReason.EVIDENCE_QUALITY_NOT_VALID.value
        )
        return outcome, quality, reason, key
    if key is None:
        return (
            MarketStateOutcome.INCOMPLETE,
            DataQuality.INCOMPLETE,
            MarketStateReason.INCOMPLETE_EVIDENCE.value,
            None,
        )
    if not isinstance(evidence.observation_kind, MarketObservationKind):
        return (
            MarketStateOutcome.INVALID,
            DataQuality.INVALID,
            MarketStateReason.UNSUPPORTED_OBSERVATION_KIND.value,
            key,
        )
    if not _aware(evidence.observation_time) or not _aware(evidence.received_time):
        return (
            MarketStateOutcome.INVALID,
            DataQuality.INVALID,
            MarketStateReason.INVALID_TIMESTAMP.value,
            key,
        )
    if not _aware(evidence.processing_time) or not _aware(evidence.reference_time):
        return (
            MarketStateOutcome.INVALID,
            DataQuality.INVALID,
            MarketStateReason.INVALID_TIMESTAMP.value,
            key,
        )
    if not isinstance(evidence.data_age, timedelta) or evidence.data_age < timedelta(0):
        return (
            MarketStateOutcome.INVALID,
            DataQuality.INVALID,
            MarketStateReason.INVALID_DATA_AGE.value,
            key,
        )
    if evidence.reference_time - evidence.observation_time != evidence.data_age:
        return (
            MarketStateOutcome.INVALID,
            DataQuality.INVALID,
            MarketStateReason.INVALID_DATA_AGE.value,
            key,
        )
    if evidence.observation_time > evidence.received_time or evidence.observation_time > evidence.reference_time:
        return (
            MarketStateOutcome.INVALID,
            DataQuality.INVALID,
            MarketStateReason.INVALID_TIMESTAMP.value,
            key,
        )
    if not _valid_sequence(evidence.sequence):
        return (
            MarketStateOutcome.INVALID,
            DataQuality.INVALID,
            MarketStateReason.INVALID_EVIDENCE.value,
            key,
        )
    if not _provenance_matches(evidence):
        return (
            MarketStateOutcome.INVALID,
            DataQuality.INVALID,
            MarketStateReason.EVIDENCE_IDENTITY_MISMATCH.value,
            key,
        )
    try:
        _canonical_metadata(evidence.observation_metadata)
        _canonical_metadata(evidence.source_metadata)
        _canonical_metadata(evidence.provenance.observation_metadata)
        _canonical_metadata(evidence.provenance.source_metadata)
        _reject_measurements(evidence.observation_metadata)
        _reject_measurements(evidence.source_metadata)
        _reject_measurements(evidence.provenance.observation_metadata)
        _reject_measurements(evidence.provenance.source_metadata)
        _content_fingerprint(evidence)
    except ValueError as exc:
        reason = (
            MarketStateReason.METADATA_BOUNDS_EXCEEDED.value
            if "bound" in str(exc)
            else MarketStateReason.UNSUPPORTED_METADATA.value
        )
        return MarketStateOutcome.INVALID, DataQuality.INVALID, reason, key
    return None


def _provenance_matches(evidence: AcceptedMarketObservationEvidence) -> bool:
    provenance = evidence.provenance
    pairs = (
        (provenance.source_id, evidence.source_id),
        (provenance.observation_id, evidence.observation_id),
        (provenance.chain_id, evidence.chain_id),
        (provenance.token_identity, evidence.token_identity),
        (provenance.market_subject_id, evidence.market_subject_id),
        (provenance.observation_kind, evidence.observation_kind),
        (provenance.observation_time, evidence.observation_time),
        (provenance.received_time, evidence.received_time),
        (provenance.sequence, evidence.sequence),
    )
    return all(left == right for left, right in pairs)


def _state_key(evidence: AcceptedMarketObservationEvidence) -> MarketStateKey:
    return (
        evidence.source_id,
        evidence.chain_id,
        evidence.token_identity,
        evidence.market_subject_id,
    )


def _state_key_if_valid(evidence: AcceptedMarketObservationEvidence) -> MarketStateKey | None:
    key = _state_key(evidence)
    return key if _valid_key(key) else None


def _entry_material(entry: MarketStateEntry) -> dict[str, Any]:
    return {
        "key": list(entry.key),
        "evidence": _canonical_evidence(entry.evidence),
        "entry_fingerprint": entry.entry_fingerprint,
        "contract_version": entry.contract_version,
    }


def _canonical_evidence(evidence: AcceptedMarketObservationEvidence) -> dict[str, Any]:
    return {
        "observation_result_id": evidence.observation_result_id,
        "observation_id": evidence.observation_id,
        "source_id": evidence.source_id,
        "chain_id": evidence.chain_id,
        "token_identity": evidence.token_identity,
        "market_subject_id": evidence.market_subject_id,
        "observation_kind": evidence.observation_kind.value,
        "quality": evidence.quality.value,
        "quality_status": evidence.quality_status.value,
        "sequence": evidence.sequence,
        "ordering_status": evidence.ordering_status.value,
        "observation_time": _timestamp(evidence.observation_time),
        "received_time": _timestamp(evidence.received_time),
        "processing_time": _timestamp(evidence.processing_time),
        "reference_time": _timestamp(evidence.reference_time),
        "data_age": evidence.data_age.total_seconds(),
        "observation_metadata": _canonical_metadata(evidence.observation_metadata),
        "source_metadata": _canonical_metadata(evidence.source_metadata),
        "provenance": {
            "source_id": evidence.provenance.source_id,
            "source_event_id": evidence.provenance.source_event_id,
            "observation_id": evidence.provenance.observation_id,
            "chain_id": evidence.provenance.chain_id,
            "token_identity": evidence.provenance.token_identity,
            "market_subject_id": evidence.provenance.market_subject_id,
            "observation_kind": evidence.provenance.observation_kind.value,
            "observation_time": _timestamp(evidence.provenance.observation_time),
            "received_time": _timestamp(evidence.provenance.received_time),
            "sequence": evidence.provenance.sequence,
            "observation_metadata": _canonical_metadata(
                evidence.provenance.observation_metadata
            ),
            "source_metadata": _canonical_metadata(evidence.provenance.source_metadata),
        },
        "candidate_contract_version": evidence.candidate_contract_version,
        "materializer_contract_version": evidence.materializer_contract_version,
        "predecessor_state_version": evidence.predecessor_state_version,
        "predecessor_state_digest": evidence.predecessor_state_digest,
        "accepted": evidence.accepted,
    }


def _content_fingerprint(evidence: AcceptedMarketObservationEvidence) -> str:
    material = _canonical_evidence(evidence)
    material.pop("observation_result_id", None)
    material.pop("observation_id", None)
    return _digest(material)


def _subject_content_fingerprint(evidence: AcceptedMarketObservationEvidence) -> str:
    material = _canonical_evidence(evidence)
    for field_name in ("observation_result_id", "observation_id", "observation_kind", "sequence"):
        material.pop(field_name, None)
    material["provenance"].pop("observation_id", None)
    material["provenance"].pop("observation_kind", None)
    material["provenance"].pop("sequence", None)
    return _digest(material)


def _entry_fingerprint(evidence: AcceptedMarketObservationEvidence) -> str:
    return _digest(_canonical_evidence(evidence))


def _result_id(
    evaluation_id: str | None,
    evidence: AcceptedMarketObservationEvidence,
    outcome: MarketStateOutcome,
    before: str,
    after: str,
) -> str:
    return _digest(
        {
            "evaluation_id": evaluation_id,
            "observation_id": evidence.observation_id,
            "key": list(_state_key(evidence)),
            "outcome": outcome.value,
            "before": before,
            "after": after,
        }
    )


def _canonical_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("metadata must be a mapping")
    counter = [0]
    result = _canonicalize(value, depth=0, counter=counter)
    if not isinstance(result, dict):
        raise ValueError("metadata must be a mapping")
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > MAX_METADATA_BYTES:
        raise ValueError("metadata bound exceeded")
    return result


def _canonicalize(value: Any, *, depth: int, counter: list[int]) -> Any:
    if depth > MAX_METADATA_DEPTH:
        raise ValueError("metadata bound exceeded")
    counter[0] += 1
    if counter[0] > MAX_METADATA_ITEMS:
        raise ValueError("metadata bound exceeded")
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("unsupported metadata")
        if any(_sensitive_key(key) for key in value):
            raise ValueError("unsupported metadata")
        return {
            key: _canonicalize(value[key], depth=depth + 1, counter=counter)
            for key in sorted(value)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item, depth=depth + 1, counter=counter) for item in value]
    raise ValueError("unsupported metadata")


def _sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(
        term in normalized
        for term in (
            "secret",
            "password",
            "credential",
            "api_key",
            "access_token",
            "private_key",
            "seed_phrase",
            "signing",
        )
    )


def _reject_measurements(value: Any) -> None:
    unsupported = {
        "price",
        "volume",
        "liquidity",
        "reserve",
        "reserves",
        "transaction_count",
        "swap_amount",
        "buy_sell_pressure",
        "buy_pressure",
        "sell_pressure",
        "order_book",
        "pool_state",
        "transaction_flow",
    }
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower().replace("-", "_") in unsupported:
                raise ValueError("unsupported market measurement")
            _reject_measurements(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_measurements(child)


def _digest(value: Any) -> str:
    encoded = json.dumps(
        _general_canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _general_canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _general_canonical(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_general_canonical(item) for item in value]
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, datetime):
        return _timestamp(value)
    if isinstance(value, timedelta):
        return value.total_seconds()
    return value


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _aware(value: Any) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_key(key: Any) -> bool:
    return isinstance(key, tuple) and len(key) == 4 and all(_non_empty(item) for item in key)


def _integer_sequence(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_sequence(value: Any) -> bool:
    return value is None or _integer_sequence(value) or isinstance(value, str)


__all__ = [
    "CurrentMarketState",
    "MarketState",
    "MarketStateContext",
    "MarketStateEntry",
    "MarketStateKey",
    "MarketStateMaterializer",
    "MarketStateOutcome",
    "MarketStateProcessingContext",
    "MarketStateProcessor",
    "MarketStateReason",
    "MarketStateResult",
    "P02_T08_CONTRACT_VERSION",
    "materialize_market_state",
]