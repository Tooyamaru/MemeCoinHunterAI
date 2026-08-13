"""Provider-neutral in-memory history for P04-T07 signal snapshots.

This boundary stores only already-created, valid
``SignalEvidenceSnapshot`` values.  It deliberately has no clock, persistence,
provider, network, market, decision, or execution behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from core.signals.signal_snapshot import (
    SignalEvidenceSnapshot,
    SignalEvidenceSnapshotCollection,
)


P04_T07_CONTRACT_VERSION = "p04-t07-v1"


class SignalSnapshotHistoryOutcome(StrEnum):
    """Observable result of one local history insertion attempt."""

    STORED = "STORED"
    DUPLICATE = "DUPLICATE"
    INVALID_INPUT = "INVALID_INPUT"

    ACCEPTED = "STORED"
    INVALID = "INVALID_INPUT"


@dataclass(frozen=True)
class SignalEvidenceSnapshotHistoryResult:
    """Immutable result and read view for one history insertion attempt."""

    outcome: SignalSnapshotHistoryOutcome
    accepted: bool
    snapshot: SignalEvidenceSnapshot | None
    snapshots: tuple[SignalEvidenceSnapshot, ...]
    reason_codes: tuple[str, ...]
    history_digest: str
    contract_version: str = P04_T07_CONTRACT_VERSION

    def __post_init__(self) -> None:
        try:
            outcome = SignalSnapshotHistoryOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "outcome must be a SignalSnapshotHistoryOutcome"
            ) from error
        object.__setattr__(self, "outcome", outcome)

        if self.accepted is not (outcome is SignalSnapshotHistoryOutcome.STORED):
            raise ValueError("accepted must match the STORED outcome")

        values = tuple(self.snapshots)
        if not all(isinstance(item, SignalEvidenceSnapshot) for item in values):
            raise ValueError(
                "snapshots must contain SignalEvidenceSnapshot values"
            )
        object.__setattr__(self, "snapshots", values)

        if outcome is SignalSnapshotHistoryOutcome.INVALID_INPUT:
            if self.snapshot is not None:
                raise ValueError("invalid history input cannot contain a snapshot")
        elif not isinstance(self.snapshot, SignalEvidenceSnapshot):
            raise ValueError("valid history outcomes require a snapshot")

        reasons = tuple(self.reason_codes)
        if any(not isinstance(value, str) or not value.strip() for value in reasons):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(
            self,
            "reason_codes",
            tuple(sorted(dict.fromkeys(reasons))),
        )

        if not isinstance(self.history_digest, str) or not self.history_digest.strip():
            raise ValueError("history_digest must be a non-empty string")
        if (
            not isinstance(self.contract_version, str)
            or not self.contract_version.strip()
        ):
            raise ValueError("contract_version must be a non-empty string")

    @property
    def status(self) -> SignalSnapshotHistoryOutcome:
        return self.outcome

    @property
    def valid(self) -> bool:
        return self.outcome is not SignalSnapshotHistoryOutcome.INVALID_INPUT

    @property
    def stored(self) -> bool:
        return self.outcome is SignalSnapshotHistoryOutcome.STORED

    @property
    def duplicate(self) -> bool:
        return self.outcome is SignalSnapshotHistoryOutcome.DUPLICATE

    @property
    def history(self) -> tuple[SignalEvidenceSnapshot, ...]:
        return self.snapshots


SignalEvidenceSnapshotHistoryStatus = SignalSnapshotHistoryOutcome


class SignalEvidenceSnapshotHistory:
    """Deterministic, in-memory history keyed by snapshot digest."""

    def __init__(
        self,
        snapshots: tuple[SignalEvidenceSnapshot, ...]
        | list[SignalEvidenceSnapshot]
        | None = None,
    ) -> None:
        self._snapshots_by_digest: dict[str, SignalEvidenceSnapshot] = {}
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
        snapshots: tuple[SignalEvidenceSnapshot, ...]
        | list[SignalEvidenceSnapshot],
    ) -> SignalEvidenceSnapshotHistory:
        return cls(snapshots)

    def append(
        self,
        snapshot: SignalEvidenceSnapshot | object,
    ) -> SignalEvidenceSnapshotHistoryResult:
        """Store one valid snapshot without mutating the supplied object."""

        current = self._ordered_snapshots()
        if not isinstance(snapshot, SignalEvidenceSnapshot):
            return self._result(
                outcome=SignalSnapshotHistoryOutcome.INVALID_INPUT,
                snapshot=None,
                snapshots=current,
                reason_codes=("INVALID_SNAPSHOT",),
            )

        try:
            # Reuse the completed T06 validation boundary rather than
            # reconstructing or normalizing the supplied snapshot.
            _validate_snapshot(snapshot)
            SignalEvidenceSnapshotCollection.from_snapshots((snapshot,))
            digest = snapshot.digest
        except (AttributeError, TypeError, ValueError):
            return self._result(
                outcome=SignalSnapshotHistoryOutcome.INVALID_INPUT,
                snapshot=None,
                snapshots=current,
                reason_codes=("INVALID_SNAPSHOT",),
            )

        existing = self._snapshots_by_digest.get(digest)
        if existing is not None:
            return self._result(
                outcome=SignalSnapshotHistoryOutcome.DUPLICATE,
                snapshot=existing,
                snapshots=current,
                reason_codes=("SNAPSHOT_ALREADY_STORED",),
            )

        self._snapshots_by_digest[digest] = snapshot
        return self._result(
            outcome=SignalSnapshotHistoryOutcome.STORED,
            snapshot=snapshot,
            snapshots=self._ordered_snapshots(),
            reason_codes=(),
        )

    add = append
    record = append
    store = append

    def retrieve(self) -> tuple[SignalEvidenceSnapshot, ...]:
        """Return all stored snapshots in deterministic canonical order."""

        return self._ordered_snapshots()

    def get_history(self) -> tuple[SignalEvidenceSnapshot, ...]:
        return self.retrieve()

    def snapshot(self) -> tuple[SignalEvidenceSnapshot, ...]:
        return self.retrieve()

    @property
    def snapshots(self) -> tuple[SignalEvidenceSnapshot, ...]:
        return self.retrieve()

    @property
    def history(self) -> tuple[SignalEvidenceSnapshot, ...]:
        return self.retrieve()

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots_by_digest)

    @property
    def representation_digest(self) -> str:
        return SignalEvidenceSnapshotCollection.from_snapshots(
            self._ordered_snapshots()
        ).representation_digest

    @property
    def digest(self) -> str:
        return self.representation_digest

    @property
    def history_digest(self) -> str:
        return self.representation_digest

    def _ordered_snapshots(self) -> tuple[SignalEvidenceSnapshot, ...]:
        return SignalEvidenceSnapshotCollection.from_snapshots(
            tuple(self._snapshots_by_digest.values())
        ).snapshots

    def _result(
        self,
        *,
        outcome: SignalSnapshotHistoryOutcome,
        snapshot: SignalEvidenceSnapshot | None,
        snapshots: tuple[SignalEvidenceSnapshot, ...],
        reason_codes: tuple[str, ...],
    ) -> SignalEvidenceSnapshotHistoryResult:
        return SignalEvidenceSnapshotHistoryResult(
            outcome=outcome,
            accepted=outcome is SignalSnapshotHistoryOutcome.STORED,
            snapshot=snapshot,
            snapshots=snapshots,
            reason_codes=reason_codes,
            history_digest=SignalEvidenceSnapshotCollection.from_snapshots(
                snapshots
            ).representation_digest,
        )


def _validate_snapshot(snapshot: SignalEvidenceSnapshot) -> None:
    """Confirm the supplied instance still satisfies the T06 value contract."""

    validated = SignalEvidenceSnapshot(
        chain_id=snapshot.chain_id,
        token_identity=snapshot.token_identity,
        aggregation_status=snapshot.aggregation_status,
        aggregated=snapshot.aggregated,
        evaluation_status=snapshot.evaluation_status,
        quality_status=snapshot.quality_status,
        signal_statuses=snapshot.signal_statuses,
        reason_codes=snapshot.reason_codes,
        evidence_references=snapshot.evidence_references,
        provenance=snapshot.provenance,
        observation_timestamps=snapshot.observation_timestamps,
        normalized_evidence_digest=snapshot.normalized_evidence_digest,
        evaluation_digest=snapshot.evaluation_digest,
        aggregation_digest=snapshot.aggregation_digest,
        aggregation_contract_version=snapshot.aggregation_contract_version,
        contract_version=snapshot.contract_version,
    )
    if validated != snapshot:
        raise ValueError("snapshot is not a normalized T06 snapshot")


SignalSnapshotHistory = SignalEvidenceSnapshotHistory
SnapshotHistoryResult = SignalEvidenceSnapshotHistoryResult


__all__ = [
    "P04_T07_CONTRACT_VERSION",
    "SignalEvidenceSnapshotHistory",
    "SignalEvidenceSnapshotHistoryResult",
    "SignalEvidenceSnapshotHistoryStatus",
    "SignalSnapshotHistory",
    "SignalSnapshotHistoryOutcome",
    "SnapshotHistoryResult",
]