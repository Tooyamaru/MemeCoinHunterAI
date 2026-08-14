"""Deterministic in-memory history for P04-T10 feature snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from typing import Any

from core.features.feature_snapshot import (
    FeatureCalculationSnapshot,
    FeatureCalculationSnapshotResult,
    P04_T10_CONTRACT_VERSION,
)


class FeatureSnapshotHistoryOutcome(StrEnum):
    """Observable result of one local history insertion attempt."""

    STORED = "STORED"
    DUPLICATE = "DUPLICATE"
    INVALID_INPUT = "INVALID_INPUT"

    ACCEPTED = "STORED"
    INVALID = "INVALID_INPUT"


FeatureCalculationSnapshotHistoryOutcome = FeatureSnapshotHistoryOutcome


@dataclass(frozen=True)
class FeatureCalculationSnapshotHistoryResult:
    """Immutable result and read view for one history insertion attempt."""

    outcome: FeatureSnapshotHistoryOutcome
    accepted: bool
    snapshot: FeatureCalculationSnapshot | None
    snapshots: tuple[FeatureCalculationSnapshot, ...]
    reason_codes: tuple[str, ...]
    history_digest: str
    contract_version: str = P04_T10_CONTRACT_VERSION

    def __post_init__(self) -> None:
        try:
            outcome = FeatureSnapshotHistoryOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("outcome must be a FeatureSnapshotHistoryOutcome") from error
        object.__setattr__(self, "outcome", outcome)
        if self.accepted is not (outcome is FeatureSnapshotHistoryOutcome.STORED):
            raise ValueError("accepted must match the STORED outcome")
        snapshots = tuple(self.snapshots)
        if not all(isinstance(value, FeatureCalculationSnapshot) for value in snapshots):
            raise ValueError("snapshots must contain FeatureCalculationSnapshot values")
        object.__setattr__(self, "snapshots", snapshots)
        if outcome is FeatureSnapshotHistoryOutcome.INVALID_INPUT:
            if self.snapshot is not None:
                raise ValueError("invalid history input cannot contain a snapshot")
        elif not isinstance(self.snapshot, FeatureCalculationSnapshot):
            raise ValueError("valid history outcomes require a snapshot")
        reasons = tuple(self.reason_codes)
        if any(not isinstance(value, str) or not value.strip() for value in reasons):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(self, "reason_codes", tuple(sorted(dict.fromkeys(reasons))))
        if not isinstance(self.history_digest, str) or not self.history_digest.strip():
            raise ValueError("history_digest must be a non-empty string")
        if not isinstance(self.contract_version, str) or not self.contract_version.strip():
            raise ValueError("contract_version must be a non-empty string")

    @property
    def status(self) -> FeatureSnapshotHistoryOutcome:
        return self.outcome

    @property
    def valid(self) -> bool:
        return self.outcome is not FeatureSnapshotHistoryOutcome.INVALID_INPUT

    @property
    def stored(self) -> bool:
        return self.outcome is FeatureSnapshotHistoryOutcome.STORED

    @property
    def duplicate(self) -> bool:
        return self.outcome is FeatureSnapshotHistoryOutcome.DUPLICATE

    @property
    def history(self) -> tuple[FeatureCalculationSnapshot, ...]:
        return self.snapshots


FeatureCalculationSnapshotHistoryStatus = FeatureSnapshotHistoryOutcome


class FeatureCalculationSnapshotHistory:
    """Deterministic, in-memory history keyed by snapshot digest."""

    def __init__(
        self,
        snapshots: tuple[FeatureCalculationSnapshot, ...]
        | list[FeatureCalculationSnapshot]
        | None = None,
    ) -> None:
        self._snapshots_by_digest: dict[str, FeatureCalculationSnapshot] = {}
        if snapshots is not None:
            if not isinstance(snapshots, (tuple, list)):
                raise ValueError("snapshots must be a tuple or list")
            for snapshot in snapshots:
                result = self.append(snapshot)
                if not result.valid:
                    reason = ", ".join(result.reason_codes) or "INVALID_SNAPSHOT"
                    raise ValueError(
                        f"cannot create snapshot history: "
                        f"{result.outcome.value} ({reason})"
                    )

    @classmethod
    def from_snapshots(
        cls,
        snapshots: tuple[FeatureCalculationSnapshot, ...]
        | list[FeatureCalculationSnapshot],
    ) -> FeatureCalculationSnapshotHistory:
        return cls(snapshots)

    def append(
        self,
        snapshot: FeatureCalculationSnapshot | object,
    ) -> FeatureCalculationSnapshotHistoryResult:
        current = self._ordered_snapshots()
        if not isinstance(snapshot, FeatureCalculationSnapshot):
            return self._result(
                outcome=FeatureSnapshotHistoryOutcome.INVALID_INPUT,
                snapshot=None,
                snapshots=current,
                reason_codes=("INVALID_SNAPSHOT",),
            )
        try:
            _validate_snapshot(snapshot)
            digest = snapshot.digest
        except (AttributeError, TypeError, ValueError):
            return self._result(
                outcome=FeatureSnapshotHistoryOutcome.INVALID_INPUT,
                snapshot=None,
                snapshots=current,
                reason_codes=("INVALID_SNAPSHOT",),
            )
        existing = self._snapshots_by_digest.get(digest)
        if existing is not None:
            return self._result(
                outcome=FeatureSnapshotHistoryOutcome.DUPLICATE,
                snapshot=existing,
                snapshots=current,
                reason_codes=("SNAPSHOT_ALREADY_STORED",),
            )
        self._snapshots_by_digest[digest] = snapshot
        return self._result(
            outcome=FeatureSnapshotHistoryOutcome.STORED,
            snapshot=snapshot,
            snapshots=self._ordered_snapshots(),
            reason_codes=(),
        )

    add = append
    record = append
    store = append

    def retrieve(self) -> tuple[FeatureCalculationSnapshot, ...]:
        return self._ordered_snapshots()

    def get_history(self) -> tuple[FeatureCalculationSnapshot, ...]:
        return self.retrieve()

    def snapshot(self) -> tuple[FeatureCalculationSnapshot, ...]:
        return self.retrieve()

    @property
    def snapshots(self) -> tuple[FeatureCalculationSnapshot, ...]:
        return self.retrieve()

    @property
    def history(self) -> tuple[FeatureCalculationSnapshot, ...]:
        return self.retrieve()

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots_by_digest)

    @property
    def representation_digest(self) -> str:
        from core.features.feature_snapshot import _digest

        return _digest(
            {
                "snapshots": tuple(
                    value.canonical_representation for value in self._ordered_snapshots()
                ),
                "contract_version": P04_T10_CONTRACT_VERSION,
            }
        )

    @property
    def digest(self) -> str:
        return self.representation_digest

    @property
    def history_digest(self) -> str:
        return self.representation_digest

    def _ordered_snapshots(self) -> tuple[FeatureCalculationSnapshot, ...]:
        return tuple(
            sorted(
                self._snapshots_by_digest.values(),
                key=lambda value: _canonical_json(value.canonical_representation),
            )
        )

    def _result(
        self,
        *,
        outcome: FeatureSnapshotHistoryOutcome,
        snapshot: FeatureCalculationSnapshot | None,
        snapshots: tuple[FeatureCalculationSnapshot, ...],
        reason_codes: tuple[str, ...],
    ) -> FeatureCalculationSnapshotHistoryResult:
        return FeatureCalculationSnapshotHistoryResult(
            outcome=outcome,
            accepted=outcome is FeatureSnapshotHistoryOutcome.STORED,
            snapshot=snapshot,
            snapshots=snapshots,
            reason_codes=reason_codes,
            history_digest=self._history_digest(snapshots),
        )

    @staticmethod
    def _history_digest(
        snapshots: tuple[FeatureCalculationSnapshot, ...],
    ) -> str:
        from core.features.feature_snapshot import _digest

        return _digest(
            {
                "snapshots": tuple(
                    value.canonical_representation for value in snapshots
                ),
                "contract_version": P04_T10_CONTRACT_VERSION,
            }
        )


def _validate_snapshot(snapshot: FeatureCalculationSnapshot) -> None:
    validated = FeatureCalculationSnapshot(
        calculation_result_id=snapshot.calculation_result_id,
        status=snapshot.status,
        reason_codes=snapshot.reason_codes,
        feature_id=snapshot.feature_id,
        feature_version=snapshot.feature_version,
        calculation_contract_version=snapshot.calculation_contract_version,
        value=snapshot.value,
        value_unit=snapshot.value_unit,
        price_unit=snapshot.price_unit,
        quote_asset=snapshot.quote_asset,
        source_id=snapshot.source_id,
        chain_id=snapshot.chain_id,
        token_identity=snapshot.token_identity,
        market_subject_id=snapshot.market_subject_id,
        reference_time=snapshot.reference_time,
        freshness_policy=snapshot.freshness_policy,
        evaluation_id=snapshot.evaluation_id,
        inputs=snapshot.inputs,
        upstream_references=snapshot.upstream_references,
        input_set_digest=snapshot.input_set_digest,
        snapshot_linkage=snapshot.snapshot_linkage,
        result_representation_digest=snapshot.result_representation_digest,
        contract_version=snapshot.contract_version,
    )
    if validated != snapshot or validated.digest != snapshot.digest:
        raise ValueError("snapshot is not a normalized T10 snapshot")


def _canonical_json(value: Any) -> str:
    from core.features.feature_snapshot import _canonicalize

    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


FeatureSnapshotHistory = FeatureCalculationSnapshotHistory
SnapshotHistoryResult = FeatureCalculationSnapshotHistoryResult
FeatureSnapshotHistoryResult = FeatureCalculationSnapshotHistoryResult


__all__ = [
    "FeatureCalculationSnapshotHistory",
    "FeatureCalculationSnapshotHistoryOutcome",
    "FeatureCalculationSnapshotHistoryResult",
    "FeatureCalculationSnapshotHistoryStatus",
    "FeatureSnapshotHistory",
    "FeatureSnapshotHistoryOutcome",
    "FeatureSnapshotHistoryResult",
    "P04_T10_CONTRACT_VERSION",
    "SnapshotHistoryResult",
]