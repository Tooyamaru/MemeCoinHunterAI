"""Deterministic in-memory history for P05-T06 opportunity records."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Any

from core.opportunity.opportunity_record import (
    OpportunityRecord,
    P05_T06_CONTRACT_VERSION,
)


P05_T07_CONTRACT_VERSION = "p05-t07-v1"


class OpportunityRecordHistoryOutcome(StrEnum):
    """Observable result of one local history insertion attempt."""

    STORED = "STORED"
    DUPLICATE = "DUPLICATE"
    INVALID_INPUT = "INVALID_INPUT"

    ACCEPTED = "STORED"
    INVALID = "INVALID_INPUT"


@dataclass(frozen=True)
class OpportunityRecordHistoryResult:
    """Immutable result and read view for one history insertion attempt."""

    outcome: OpportunityRecordHistoryOutcome
    accepted: bool
    record: OpportunityRecord | None
    records: tuple[OpportunityRecord, ...]
    reason_codes: tuple[str, ...]
    history_digest: str
    contract_version: str = P05_T07_CONTRACT_VERSION

    def __post_init__(self) -> None:
        try:
            outcome = OpportunityRecordHistoryOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "outcome must be an OpportunityRecordHistoryOutcome"
            ) from error
        object.__setattr__(self, "outcome", outcome)
        if self.accepted is not (outcome is OpportunityRecordHistoryOutcome.STORED):
            raise ValueError("accepted must match the STORED outcome")
        records = tuple(self.records)
        if not all(isinstance(value, OpportunityRecord) for value in records):
            raise ValueError("records must contain OpportunityRecord values")
        object.__setattr__(self, "records", records)
        if outcome is OpportunityRecordHistoryOutcome.INVALID_INPUT:
            if self.record is not None:
                raise ValueError("invalid history input cannot contain a record")
        elif not isinstance(self.record, OpportunityRecord):
            raise ValueError("valid history outcomes require a record")
        reasons = tuple(self.reason_codes)
        if any(not isinstance(value, str) or not value.strip() for value in reasons):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(self, "reason_codes", tuple(sorted(dict.fromkeys(reasons))))
        _require_text(self.history_digest, "history_digest")
        _require_text(self.contract_version, "contract_version")
        if self.contract_version != P05_T07_CONTRACT_VERSION:
            raise ValueError("unsupported P05-T07 contract version")

    @property
    def status(self) -> OpportunityRecordHistoryOutcome:
        return self.outcome

    @property
    def valid(self) -> bool:
        return self.outcome is not OpportunityRecordHistoryOutcome.INVALID_INPUT

    @property
    def stored(self) -> bool:
        return self.outcome is OpportunityRecordHistoryOutcome.STORED

    @property
    def duplicate(self) -> bool:
        return self.outcome is OpportunityRecordHistoryOutcome.DUPLICATE

    @property
    def history(self) -> tuple[OpportunityRecord, ...]:
        return self.records


OpportunityRecordHistoryStatus = OpportunityRecordHistoryOutcome


class OpportunityRecordHistory:
    """Deterministic, local history keyed by immutable record digest."""

    def __init__(
        self,
        records: tuple[OpportunityRecord, ...]
        | list[OpportunityRecord]
        | None = None,
    ) -> None:
        self._records_by_digest: dict[str, OpportunityRecord] = {}
        if records is not None:
            if not isinstance(records, (tuple, list)):
                raise ValueError("records must be a tuple or list")
            for record in records:
                result = self.append(record)
                if not result.valid:
                    reason = ", ".join(result.reason_codes) or "INVALID_RECORD"
                    raise ValueError(
                        f"cannot create opportunity record history: "
                        f"{result.outcome.value} ({reason})"
                    )

    @classmethod
    def from_records(
        cls,
        records: tuple[OpportunityRecord, ...] | list[OpportunityRecord],
    ) -> OpportunityRecordHistory:
        return cls(records)

    def append(
        self,
        record: OpportunityRecord | object,
    ) -> OpportunityRecordHistoryResult:
        current = self._ordered_records()
        if not isinstance(record, OpportunityRecord):
            return self._result(
                outcome=OpportunityRecordHistoryOutcome.INVALID_INPUT,
                record=None,
                records=current,
                reason_codes=("INVALID_RECORD",),
            )
        try:
            _validate_record(record)
            digest = record.digest
        except (AttributeError, TypeError, ValueError):
            return self._result(
                outcome=OpportunityRecordHistoryOutcome.INVALID_INPUT,
                record=None,
                records=current,
                reason_codes=("INVALID_RECORD",),
            )
        existing = self._records_by_digest.get(digest)
        if existing is not None:
            return self._result(
                outcome=OpportunityRecordHistoryOutcome.DUPLICATE,
                record=existing,
                records=current,
                reason_codes=("RECORD_ALREADY_STORED",),
            )
        self._records_by_digest[digest] = record
        return self._result(
            outcome=OpportunityRecordHistoryOutcome.STORED,
            record=record,
            records=self._ordered_records(),
            reason_codes=(),
        )

    add = append
    record = append
    store = append

    def retrieve(self) -> tuple[OpportunityRecord, ...]:
        return self._ordered_records()

    def get_history(self) -> tuple[OpportunityRecord, ...]:
        return self.retrieve()

    def snapshot(self) -> tuple[OpportunityRecord, ...]:
        return self.retrieve()

    @property
    def records(self) -> tuple[OpportunityRecord, ...]:
        return self.retrieve()

    @property
    def history(self) -> tuple[OpportunityRecord, ...]:
        return self.retrieve()

    @property
    def record_count(self) -> int:
        return len(self._records_by_digest)

    @property
    def snapshot_count(self) -> int:
        return self.record_count

    @property
    def representation_digest(self) -> str:
        return self._history_digest(self._ordered_records())

    @property
    def digest(self) -> str:
        return self.representation_digest

    @property
    def history_digest(self) -> str:
        return self.representation_digest

    def _ordered_records(self) -> tuple[OpportunityRecord, ...]:
        return tuple(
            sorted(
                self._records_by_digest.values(),
                key=lambda value: _canonical_json(value.canonical_representation),
            )
        )

    def _result(
        self,
        *,
        outcome: OpportunityRecordHistoryOutcome,
        record: OpportunityRecord | None,
        records: tuple[OpportunityRecord, ...],
        reason_codes: tuple[str, ...],
    ) -> OpportunityRecordHistoryResult:
        return OpportunityRecordHistoryResult(
            outcome=outcome,
            accepted=outcome is OpportunityRecordHistoryOutcome.STORED,
            record=record,
            records=records,
            reason_codes=reason_codes,
            history_digest=self._history_digest(records),
        )

    @staticmethod
    def _history_digest(records: tuple[OpportunityRecord, ...]) -> str:
        return _digest(
            {
                "records": tuple(
                    value.canonical_representation for value in records
                ),
                "contract_version": P05_T07_CONTRACT_VERSION,
            }
        )


def _validate_record(record: OpportunityRecord) -> None:
    if record.contract_version != P05_T06_CONTRACT_VERSION:
        raise ValueError("unsupported P05-T06 contract version")
    validated = OpportunityRecord(
        candidate_id=record.candidate_id,
        chain_id=record.chain_id,
        token_identity=record.token_identity,
        reference_time=record.reference_time,
        input_score_digest=record.input_score_digest,
        opportunity_score=record.opportunity_score,
        feature_evaluation=record.feature_evaluation,
        risk_evaluation=record.risk_evaluation,
        signal_snapshot=record.signal_snapshot,
        evaluator_version=record.evaluator_version,
        contract_version=record.contract_version,
    )
    if validated != record or validated.digest != record.digest:
        raise ValueError("opportunity record is not canonical")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonicalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _canonicalize(value[key]) for key in sorted(value, key=str)
        }
    if hasattr(value, "items"):
        return {
            str(key): _canonicalize(value[key]) for key in sorted(value, key=str)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ValueError(f"{type(value).__name__} cannot be deterministically serialized")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


OpportunityRecordHistoryResultAlias = OpportunityRecordHistoryResult
OpportunityHistory = OpportunityRecordHistory


__all__ = [
    "OpportunityHistory",
    "OpportunityRecordHistory",
    "OpportunityRecordHistoryOutcome",
    "OpportunityRecordHistoryResult",
    "OpportunityRecordHistoryResultAlias",
    "OpportunityRecordHistoryStatus",
    "P05_T07_CONTRACT_VERSION",
]