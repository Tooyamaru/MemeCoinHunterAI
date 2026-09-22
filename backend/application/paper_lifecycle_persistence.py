"""Atomic append-only persistence for one canonical P01-RTI-02 result."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
import math
from typing import Any, Mapping

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.core.database import DatabaseRuntime, DatabaseState
from backend.core.models import PaperLifecycleArtifact, PaperLifecycleRun
from backend.core.repositories import PaperLifecycleRepository
from core.execution.paper_simulation_result import PaperSimulationResult
from core.execution.paper_simulation_result_history import (
    PaperSimulationResultHistory,
)
from core.runtime.controlled_paper_lifecycle import (
    P01_RTI_02_CONTRACT_VERSION,
    ControlledPaperLifecycleOutcome,
    ControlledPaperLifecycleResult,
)


P01_RTI_03_CONTRACT_VERSION = "p01-rti-03-v1"


class PaperLifecycleArtifactKind(StrEnum):
    ADMISSION_RESULT = "ADMISSION_RESULT"
    DECISION_INTENT = "DECISION_INTENT"
    RISK_CAPITAL_AUTHORIZATION = "RISK_CAPITAL_AUTHORIZATION"
    SIMULATION_INPUT = "SIMULATION_INPUT"
    FILL_OUTCOME = "FILL_OUTCOME"
    PRIOR_PAPER_STATE = "PRIOR_PAPER_STATE"
    STATE_TRANSITION = "STATE_TRANSITION"
    RESULTING_PAPER_STATE = "RESULTING_PAPER_STATE"
    LEDGER_ENTRY = "LEDGER_ENTRY"
    RECONCILIATION_RESULT = "RECONCILIATION_RESULT"
    PAPER_SIMULATION_RESULT = "PAPER_SIMULATION_RESULT"
    HISTORY_RESULT = "HISTORY_RESULT"
    OUTCOME_OBSERVATION = "OUTCOME_OBSERVATION"


class PaperLifecyclePersistenceOutcome(StrEnum):
    STORED = "STORED"
    ALREADY_STORED = "ALREADY_STORED"
    CONFLICT = "CONFLICT"
    INVALID_INPUT = "INVALID_INPUT"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"


class PaperLifecycleReadOutcome(StrEnum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    CORRUPT = "CORRUPT"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"


@dataclass(frozen=True)
class PaperLifecycleArtifactSnapshot:
    artifact_kind: PaperLifecycleArtifactKind | str
    artifact_digest: str
    payload_digest: str
    owner_contract_version: str
    canonical_payload: str
    ordinal: int

    def __post_init__(self) -> None:
        try:
            kind = PaperLifecycleArtifactKind(self.artifact_kind)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported artifact_kind") from error
        object.__setattr__(self, "artifact_kind", kind)
        _digest_text(self.artifact_digest, "artifact_digest")
        _digest_text(self.payload_digest, "payload_digest")
        _text(self.owner_contract_version, "owner_contract_version")
        if (
            isinstance(self.ordinal, bool)
            or not isinstance(self.ordinal, int)
            or self.ordinal <= 0
        ):
            raise ValueError("ordinal must be a positive integer")
        _text(self.canonical_payload, "canonical_payload")
        if _sha256_text(self.canonical_payload) != self.payload_digest:
            raise ValueError("payload_digest does not match canonical_payload")
        try:
            parsed = json.loads(self.canonical_payload)
        except (TypeError, ValueError) as error:
            raise ValueError("canonical_payload must be valid JSON") from error
        if _canonical_json(parsed) != self.canonical_payload:
            raise ValueError("canonical_payload is not canonical JSON")
        if isinstance(parsed, dict):
            payload_version = parsed.get("contract_version")
            if (
                payload_version is not None
                and payload_version != self.owner_contract_version
            ):
                raise ValueError("payload contract version does not match owner")

    @property
    def canonical_representation(self) -> dict[str, Any]:
        return {
            "artifact_kind": self.artifact_kind.value,
            "artifact_digest": self.artifact_digest,
            "payload_digest": self.payload_digest,
            "owner_contract_version": self.owner_contract_version,
            "canonical_payload": self.canonical_payload,
            "ordinal": self.ordinal,
        }


@dataclass(frozen=True)
class PaperLifecycleRunSnapshot:
    lifecycle_result_digest: str
    lifecycle_contract_version: str
    outcome: ControlledPaperLifecycleOutcome | str
    reason_codes: tuple[str, ...]
    admission_digest: str
    decision_intent_digest: str | None
    simulation_input_digest: str | None
    fill_digest: str | None
    transition_digest: str | None
    ledger_digest: str | None
    reconciliation_digest: str | None
    paper_result_digest: str | None
    history_digest: str | None
    observation_digest: str | None
    artifact_count: int

    def __post_init__(self) -> None:
        _digest_text(self.lifecycle_result_digest, "lifecycle_result_digest")
        if self.lifecycle_contract_version != P01_RTI_02_CONTRACT_VERSION:
            raise ValueError("unsupported lifecycle_contract_version")
        try:
            outcome = ControlledPaperLifecycleOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported lifecycle outcome") from error
        object.__setattr__(self, "outcome", outcome)
        reasons = _reason_codes(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)
        _digest_text(self.admission_digest, "admission_digest")
        for name in (
            "decision_intent_digest",
            "simulation_input_digest",
            "fill_digest",
            "transition_digest",
            "ledger_digest",
            "reconciliation_digest",
            "paper_result_digest",
            "history_digest",
            "observation_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                _digest_text(value, name)
        if (
            isinstance(self.artifact_count, bool)
            or not isinstance(self.artifact_count, int)
            or self.artifact_count < 0
        ):
            raise ValueError("artifact_count must be a non-negative integer")
        if _digest(self._owner_result_fields()) != self.lifecycle_result_digest:
            raise ValueError("stored lifecycle root does not match owner digest")

    def _owner_result_fields(self) -> dict[str, Any]:
        return {
            "contract_version": self.lifecycle_contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "admission_digest": self.admission_digest,
            "fill_digest": self.fill_digest,
            "transition_digest": self.transition_digest,
            "ledger_digest": self.ledger_digest,
            "reconciliation_digest": self.reconciliation_digest,
            "paper_result_digest": self.paper_result_digest,
            "history_digest": self.history_digest,
            "observation_digest": self.observation_digest,
        }

    @property
    def canonical_representation(self) -> dict[str, Any]:
        return {
            **self._owner_result_fields(),
            "lifecycle_result_digest": self.lifecycle_result_digest,
            "decision_intent_digest": self.decision_intent_digest,
            "simulation_input_digest": self.simulation_input_digest,
            "artifact_count": self.artifact_count,
        }


@dataclass(frozen=True)
class PaperLifecyclePersistenceResult:
    outcome: PaperLifecyclePersistenceOutcome | str
    reason_codes: tuple[str, ...]
    lifecycle_result_digest: str | None
    artifact_count: int
    contract_version: str = P01_RTI_03_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        try:
            outcome = PaperLifecyclePersistenceOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported persistence outcome") from error
        object.__setattr__(self, "outcome", outcome)
        if self.contract_version != P01_RTI_03_CONTRACT_VERSION:
            raise ValueError("unsupported persistence contract_version")
        reasons = _reason_codes(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)
        if self.lifecycle_result_digest is not None:
            _digest_text(self.lifecycle_result_digest, "lifecycle_result_digest")
        if (
            isinstance(self.artifact_count, bool)
            or not isinstance(self.artifact_count, int)
            or self.artifact_count < 0
        ):
            raise ValueError("artifact_count must be a non-negative integer")
        if outcome in {
            PaperLifecyclePersistenceOutcome.STORED,
            PaperLifecyclePersistenceOutcome.ALREADY_STORED,
        }:
            if self.lifecycle_result_digest is None or reasons:
                raise ValueError("successful persistence requires digest and no reasons")
        elif not reasons:
            raise ValueError("non-success persistence requires reason codes")
        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("result_digest does not match persistence result")
        object.__setattr__(self, "result_digest", expected)

    def _without_digest(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "lifecycle_result_digest": self.lifecycle_result_digest,
            "artifact_count": self.artifact_count,
        }

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


@dataclass(frozen=True)
class PaperLifecycleReadResult:
    outcome: PaperLifecycleReadOutcome | str
    reason_codes: tuple[str, ...]
    lifecycle_result_digest: str
    run: PaperLifecycleRunSnapshot | None = None
    artifacts: tuple[PaperLifecycleArtifactSnapshot, ...] = ()
    contract_version: str = P01_RTI_03_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        try:
            outcome = PaperLifecycleReadOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported read outcome") from error
        object.__setattr__(self, "outcome", outcome)
        _digest_text(self.lifecycle_result_digest, "lifecycle_result_digest")
        if self.contract_version != P01_RTI_03_CONTRACT_VERSION:
            raise ValueError("unsupported read contract_version")
        reasons = _reason_codes(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)
        artifacts = tuple(self.artifacts)
        object.__setattr__(self, "artifacts", artifacts)
        if outcome is PaperLifecycleReadOutcome.FOUND:
            if not isinstance(self.run, PaperLifecycleRunSnapshot) or reasons:
                raise ValueError("FOUND requires a valid run and no reasons")
            if self.run.lifecycle_result_digest != self.lifecycle_result_digest:
                raise ValueError("read run digest does not match requested digest")
            if self.run.artifact_count != len(artifacts):
                raise ValueError("read artifact count does not match run")
        else:
            if self.run is not None or artifacts or not reasons:
                raise ValueError("non-FOUND read cannot expose snapshots")
        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("result_digest does not match read result")
        object.__setattr__(self, "result_digest", expected)

    def _without_digest(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "lifecycle_result_digest": self.lifecycle_result_digest,
            "run": self.run.canonical_representation if self.run else None,
            "artifacts": tuple(
                value.canonical_representation for value in self.artifacts
            ),
        }

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


@dataclass(frozen=True)
class _PersistenceBundle:
    run: PaperLifecycleRunSnapshot
    artifacts: tuple[PaperLifecycleArtifactSnapshot, ...]


class ControlledPaperPersistenceService:
    """Coordinate validation and one atomic write through P01-T03 sessions."""

    def __init__(
        self,
        database: DatabaseRuntime,
        repository: PaperLifecycleRepository | None = None,
    ) -> None:
        if not isinstance(database, DatabaseRuntime):
            raise ValueError("database must be a DatabaseRuntime")
        self.database = database
        self.repository = repository or PaperLifecycleRepository()

    async def persist(
        self,
        lifecycle_result: ControlledPaperLifecycleResult,
    ) -> PaperLifecyclePersistenceResult:
        try:
            bundle = _build_bundle(lifecycle_result)
        except (AttributeError, TypeError, ValueError):
            return _write_result(
                PaperLifecyclePersistenceOutcome.INVALID_INPUT,
                ("INVALID_LIFECYCLE_RESULT",),
            )
        if not self._available:
            return _write_result(
                PaperLifecyclePersistenceOutcome.STORAGE_UNAVAILABLE,
                ("DATABASE_UNAVAILABLE",),
                digest=bundle.run.lifecycle_result_digest,
            )
        try:
            async with self.database.session_scope() as session:
                existing = await self.repository.get_run(
                    session,
                    bundle.run.lifecycle_result_digest,
                )
                if existing is not None:
                    artifacts = await self.repository.get_artifacts(
                        session,
                        existing.id,
                    )
                    return _compare_existing(existing, artifacts, bundle)
                await self.repository.insert_bundle(
                    session,
                    run_values=_run_values(bundle.run),
                    artifact_values=tuple(
                        _artifact_values(value) for value in bundle.artifacts
                    ),
                )
        except IntegrityError:
            return await self._resolve_concurrent_write(bundle)
        except (SQLAlchemyError, OSError, RuntimeError, TypeError, ValueError):
            return _write_result(
                PaperLifecyclePersistenceOutcome.STORAGE_UNAVAILABLE,
                ("DATABASE_WRITE_FAILED",),
                digest=bundle.run.lifecycle_result_digest,
            )
        return _write_result(
            PaperLifecyclePersistenceOutcome.STORED,
            (),
            digest=bundle.run.lifecycle_result_digest,
            count=len(bundle.artifacts),
        )

    async def read(self, lifecycle_result_digest: str) -> PaperLifecycleReadResult:
        try:
            digest = _digest_text(
                lifecycle_result_digest,
                "lifecycle_result_digest",
            )
        except ValueError:
            raise ValueError("lifecycle_result_digest must be a digest") from None
        if not self._available:
            return _read_result(
                PaperLifecycleReadOutcome.STORAGE_UNAVAILABLE,
                ("DATABASE_UNAVAILABLE",),
                digest,
            )
        try:
            async with self.database.session_scope() as session:
                run = await self.repository.get_run(session, digest)
                if run is None:
                    return _read_result(
                        PaperLifecycleReadOutcome.NOT_FOUND,
                        ("LIFECYCLE_NOT_FOUND",),
                        digest,
                    )
                artifacts = await self.repository.get_artifacts(session, run.id)
                snapshot = _snapshot_bundle(run, artifacts)
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return _read_result(
                PaperLifecycleReadOutcome.CORRUPT,
                ("STORED_BUNDLE_CORRUPT",),
                digest,
            )
        except (SQLAlchemyError, OSError, RuntimeError):
            return _read_result(
                PaperLifecycleReadOutcome.STORAGE_UNAVAILABLE,
                ("DATABASE_READ_FAILED",),
                digest,
            )
        return _read_result(
            PaperLifecycleReadOutcome.FOUND,
            (),
            digest,
            run=snapshot.run,
            artifacts=snapshot.artifacts,
        )

    @property
    def _available(self) -> bool:
        return (
            self.database.state is DatabaseState.CONNECTED
            and self.database.session_factory is not None
        )

    async def _resolve_concurrent_write(
        self,
        bundle: _PersistenceBundle,
    ) -> PaperLifecyclePersistenceResult:
        try:
            async with self.database.session_scope() as session:
                run = await self.repository.get_run(
                    session,
                    bundle.run.lifecycle_result_digest,
                )
                if run is None:
                    return _write_result(
                        PaperLifecyclePersistenceOutcome.STORAGE_UNAVAILABLE,
                        ("CONCURRENT_WRITE_NOT_VISIBLE",),
                        digest=bundle.run.lifecycle_result_digest,
                    )
                artifacts = await self.repository.get_artifacts(session, run.id)
                return _compare_existing(run, artifacts, bundle)
        except (SQLAlchemyError, OSError, RuntimeError, TypeError, ValueError):
            return _write_result(
                PaperLifecyclePersistenceOutcome.STORAGE_UNAVAILABLE,
                ("CONCURRENT_WRITE_READ_FAILED",),
                digest=bundle.run.lifecycle_result_digest,
            )


def _build_bundle(
    lifecycle_result: ControlledPaperLifecycleResult,
) -> _PersistenceBundle:
    if type(lifecycle_result) is not ControlledPaperLifecycleResult:
        raise ValueError("lifecycle_result must be ControlledPaperLifecycleResult")
    if replace(lifecycle_result) != lifecycle_result:
        raise ValueError("lifecycle_result is not canonical")

    admission = lifecycle_result.admission
    _validate_owner(admission)
    artifacts: list[PaperLifecycleArtifactSnapshot] = []

    def add(kind: PaperLifecycleArtifactKind, owner: Any, digest: str, payload: Any) -> None:
        _validate_owner(owner)
        canonical_payload = _canonical_json(payload)
        artifacts.append(
            PaperLifecycleArtifactSnapshot(
                artifact_kind=kind,
                artifact_digest=digest,
                payload_digest=_sha256_text(canonical_payload),
                owner_contract_version=_owner_version(owner),
                canonical_payload=canonical_payload,
                ordinal=len(artifacts) + 1,
            )
        )

    add(
        PaperLifecycleArtifactKind.ADMISSION_RESULT,
        admission,
        admission.digest,
        admission.canonical_representation,
    )
    if admission.decision_intent is not None:
        add(
            PaperLifecycleArtifactKind.DECISION_INTENT,
            admission.decision_intent,
            admission.decision_intent.digest,
            admission.decision_intent.canonical_representation,
        )
    if admission.risk_capital_authorization is not None:
        add(
            PaperLifecycleArtifactKind.RISK_CAPITAL_AUTHORIZATION,
            admission.risk_capital_authorization,
            admission.risk_capital_authorization.digest,
            admission.risk_capital_authorization.canonical_representation,
        )
    if admission.paper_simulation_input is not None:
        add(
            PaperLifecycleArtifactKind.SIMULATION_INPUT,
            admission.paper_simulation_input,
            admission.paper_simulation_input.digest,
            admission.paper_simulation_input.canonical_representation,
        )

    transition = lifecycle_result.transition
    if lifecycle_result.fill_outcome is not None:
        add(
            PaperLifecycleArtifactKind.FILL_OUTCOME,
            lifecycle_result.fill_outcome,
            lifecycle_result.fill_outcome.outcome_digest,
            lifecycle_result.fill_outcome.canonical_representation,
        )
    if transition is not None:
        add(
            PaperLifecycleArtifactKind.PRIOR_PAPER_STATE,
            transition.prior_state,
            transition.prior_state.digest,
            transition.prior_state.canonical_representation,
        )
        add(
            PaperLifecycleArtifactKind.STATE_TRANSITION,
            transition,
            transition.digest,
            transition.canonical_representation,
        )
        if transition.next_state is not None:
            add(
                PaperLifecycleArtifactKind.RESULTING_PAPER_STATE,
                transition.next_state,
                transition.next_state.digest,
                transition.next_state.canonical_representation,
            )
    if lifecycle_result.ledger_entry is not None:
        add(
            PaperLifecycleArtifactKind.LEDGER_ENTRY,
            lifecycle_result.ledger_entry,
            lifecycle_result.ledger_entry.entry_digest,
            lifecycle_result.ledger_entry.canonical_representation,
        )
    if lifecycle_result.reconciliation is not None:
        add(
            PaperLifecycleArtifactKind.RECONCILIATION_RESULT,
            lifecycle_result.reconciliation,
            lifecycle_result.reconciliation.digest,
            lifecycle_result.reconciliation.canonical_representation,
        )
    if lifecycle_result.paper_result is not None:
        add(
            PaperLifecycleArtifactKind.PAPER_SIMULATION_RESULT,
            lifecycle_result.paper_result,
            lifecycle_result.paper_result.digest,
            lifecycle_result.paper_result.canonical_dict(),
        )
    if lifecycle_result.history_result is not None:
        history = PaperSimulationResultHistory(lifecycle_result.history_result.results)
        if history.digest != lifecycle_result.history_result.history_digest:
            raise ValueError("history result digest is invalid")
        add(
            PaperLifecycleArtifactKind.HISTORY_RESULT,
            lifecycle_result.history_result,
            lifecycle_result.history_result.history_digest,
            _history_payload(lifecycle_result.history_result),
        )
    if lifecycle_result.observation is not None:
        add(
            PaperLifecycleArtifactKind.OUTCOME_OBSERVATION,
            lifecycle_result.observation,
            lifecycle_result.observation.digest,
            lifecycle_result.observation.canonical_representation,
        )

    if lifecycle_result.paper_result is not None:
        if not all(
            value is not None
            for value in (
                admission.paper_simulation_input,
                lifecycle_result.fill_outcome,
                transition,
                lifecycle_result.ledger_entry,
                lifecycle_result.reconciliation,
            )
        ):
            raise ValueError("paper result predecessors are incomplete")
        PaperSimulationResult.validate_predecessors(
            lifecycle_result.paper_result,
            simulation_input=admission.paper_simulation_input,
            fill_outcome=lifecycle_result.fill_outcome,
            transition=transition,
            ledger_entries=(lifecycle_result.ledger_entry,),
            reconciliation=lifecycle_result.reconciliation,
        )

    run = PaperLifecycleRunSnapshot(
        lifecycle_result_digest=lifecycle_result.digest,
        lifecycle_contract_version=lifecycle_result.contract_version,
        outcome=lifecycle_result.outcome,
        reason_codes=lifecycle_result.reason_codes,
        admission_digest=admission.digest,
        decision_intent_digest=(
            admission.decision_intent.digest
            if admission.decision_intent is not None
            else None
        ),
        simulation_input_digest=(
            admission.paper_simulation_input.digest
            if admission.paper_simulation_input is not None
            else None
        ),
        fill_digest=_artifact_digest(lifecycle_result.fill_outcome, "outcome_digest"),
        transition_digest=_artifact_digest(transition, "transition_digest"),
        ledger_digest=_artifact_digest(lifecycle_result.ledger_entry, "entry_digest"),
        reconciliation_digest=_artifact_digest(
            lifecycle_result.reconciliation,
            "result_digest",
        ),
        paper_result_digest=(
            lifecycle_result.paper_result.digest
            if lifecycle_result.paper_result is not None
            else None
        ),
        history_digest=(
            lifecycle_result.history_result.history_digest
            if lifecycle_result.history_result is not None
            else None
        ),
        observation_digest=(
            lifecycle_result.observation.digest
            if lifecycle_result.observation is not None
            else None
        ),
        artifact_count=len(artifacts),
    )
    _validate_artifact_linkage(run, tuple(artifacts))
    return _PersistenceBundle(run=run, artifacts=tuple(artifacts))


def _snapshot_bundle(
    run: PaperLifecycleRun,
    artifacts: tuple[PaperLifecycleArtifact, ...],
) -> _PersistenceBundle:
    try:
        reason_values = json.loads(run.reason_codes_json)
    except (TypeError, ValueError) as error:
        raise ValueError("stored reason codes are invalid") from error
    if (
        not isinstance(reason_values, list)
        or _canonical_json(reason_values) != run.reason_codes_json
    ):
        raise ValueError("stored reason codes are not canonical")
    snapshot = PaperLifecycleRunSnapshot(
        lifecycle_result_digest=run.lifecycle_result_digest,
        lifecycle_contract_version=run.lifecycle_contract_version,
        outcome=run.outcome,
        reason_codes=tuple(reason_values),
        admission_digest=run.admission_digest,
        decision_intent_digest=run.decision_intent_digest,
        simulation_input_digest=run.simulation_input_digest,
        fill_digest=run.fill_digest,
        transition_digest=run.transition_digest,
        ledger_digest=run.ledger_digest,
        reconciliation_digest=run.reconciliation_digest,
        paper_result_digest=run.paper_result_digest,
        history_digest=run.history_digest,
        observation_digest=run.observation_digest,
        artifact_count=run.artifact_count,
    )
    artifact_snapshots = tuple(
        PaperLifecycleArtifactSnapshot(
            artifact_kind=value.artifact_kind,
            artifact_digest=value.artifact_digest,
            payload_digest=value.payload_digest,
            owner_contract_version=value.owner_contract_version,
            canonical_payload=value.canonical_payload,
            ordinal=value.ordinal,
        )
        for value in artifacts
    )
    _validate_artifact_linkage(snapshot, artifact_snapshots)
    return _PersistenceBundle(run=snapshot, artifacts=artifact_snapshots)


def _validate_artifact_linkage(
    run: PaperLifecycleRunSnapshot,
    artifacts: tuple[PaperLifecycleArtifactSnapshot, ...],
) -> None:
    if run.artifact_count != len(artifacts):
        raise ValueError("artifact_count does not match stored artifacts")
    if tuple(value.ordinal for value in artifacts) != tuple(
        range(1, len(artifacts) + 1)
    ):
        raise ValueError("artifact ordinals must be contiguous")
    kinds = tuple(value.artifact_kind for value in artifacts)
    if len(set(kinds)) != len(kinds):
        raise ValueError("artifact kinds must be unique")
    canonical_order = tuple(PaperLifecycleArtifactKind)
    if kinds != tuple(kind for kind in canonical_order if kind in kinds):
        raise ValueError("artifact kinds are not in canonical order")
    by_kind = {value.artifact_kind: value for value in artifacts}
    expected = {
        PaperLifecycleArtifactKind.ADMISSION_RESULT: run.admission_digest,
        PaperLifecycleArtifactKind.DECISION_INTENT: run.decision_intent_digest,
        PaperLifecycleArtifactKind.SIMULATION_INPUT: run.simulation_input_digest,
        PaperLifecycleArtifactKind.FILL_OUTCOME: run.fill_digest,
        PaperLifecycleArtifactKind.STATE_TRANSITION: run.transition_digest,
        PaperLifecycleArtifactKind.LEDGER_ENTRY: run.ledger_digest,
        PaperLifecycleArtifactKind.RECONCILIATION_RESULT: run.reconciliation_digest,
        PaperLifecycleArtifactKind.PAPER_SIMULATION_RESULT: run.paper_result_digest,
        PaperLifecycleArtifactKind.HISTORY_RESULT: run.history_digest,
        PaperLifecycleArtifactKind.OUTCOME_OBSERVATION: run.observation_digest,
    }
    for kind, digest in expected.items():
        artifact = by_kind.get(kind)
        if (digest is None) is not (artifact is None):
            raise ValueError(f"{kind.value} presence does not match root")
        if artifact is not None and artifact.artifact_digest != digest:
            raise ValueError(f"{kind.value} digest does not match root")

    admission_payload = _payload_mapping(
        by_kind[PaperLifecycleArtifactKind.ADMISSION_RESULT]
    )
    if admission_payload.get("result_digest") != run.admission_digest:
        raise ValueError("admission payload digest does not match root")
    admission_links = {
        PaperLifecycleArtifactKind.DECISION_INTENT: (
            "decision_intent_digest",
            run.decision_intent_digest,
        ),
        PaperLifecycleArtifactKind.RISK_CAPITAL_AUTHORIZATION: (
            "risk_capital_authorization_digest",
            None,
        ),
        PaperLifecycleArtifactKind.SIMULATION_INPUT: (
            "paper_simulation_input_digest",
            run.simulation_input_digest,
        ),
    }
    for kind, (payload_field, root_digest) in admission_links.items():
        linked_digest = admission_payload.get(payload_field)
        artifact = by_kind.get(kind)
        if root_digest is not None and linked_digest != root_digest:
            raise ValueError(f"{kind.value} admission link does not match root")
        if (linked_digest is None) is not (artifact is None):
            raise ValueError(f"{kind.value} presence does not match admission")
        if artifact is not None and artifact.artifact_digest != linked_digest:
            raise ValueError(f"{kind.value} digest does not match admission")

    transition_artifact = by_kind.get(PaperLifecycleArtifactKind.STATE_TRANSITION)
    prior_artifact = by_kind.get(PaperLifecycleArtifactKind.PRIOR_PAPER_STATE)
    next_artifact = by_kind.get(PaperLifecycleArtifactKind.RESULTING_PAPER_STATE)
    if transition_artifact is None:
        if prior_artifact is not None or next_artifact is not None:
            raise ValueError("paper states require a transition")
    else:
        transition_payload = _payload_mapping(transition_artifact)
        prior_payload = transition_payload.get("prior_state")
        next_payload = transition_payload.get("next_state")
        if not isinstance(prior_payload, dict) or prior_artifact is None:
            raise ValueError("transition requires its prior state artifact")
        if prior_payload.get("state_digest") != prior_artifact.artifact_digest:
            raise ValueError("prior state digest does not match transition")
        if (next_payload is None) is not (next_artifact is None):
            raise ValueError("resulting state presence does not match transition")
        if next_artifact is not None and (
            not isinstance(next_payload, dict)
            or next_payload.get("state_digest") != next_artifact.artifact_digest
        ):
            raise ValueError("resulting state digest does not match transition")

    if run.outcome is ControlledPaperLifecycleOutcome.OBSERVATION_PRODUCED:
        if kinds != canonical_order:
            raise ValueError("completed lifecycle requires every artifact")
    elif run.outcome is ControlledPaperLifecycleOutcome.ADMISSION_NOT_READY:
        forbidden = set(canonical_order[4:])
        if forbidden.intersection(kinds):
            raise ValueError("unready admission contains lifecycle artifacts")
    elif run.outcome is ControlledPaperLifecycleOutcome.RECONCILIATION_NOT_MATCHED:
        forbidden = {
            PaperLifecycleArtifactKind.PAPER_SIMULATION_RESULT,
            PaperLifecycleArtifactKind.HISTORY_RESULT,
            PaperLifecycleArtifactKind.OUTCOME_OBSERVATION,
        }
        if forbidden.intersection(kinds):
            raise ValueError("reconciliation non-match contains later artifacts")

    paper_artifact = by_kind.get(PaperLifecycleArtifactKind.PAPER_SIMULATION_RESULT)
    if paper_artifact is not None:
        paper_payload = _payload_mapping(paper_artifact)
        paper_links = {
            "input_digest": run.simulation_input_digest,
            "fill_digest": run.fill_digest,
            "transition_digest": run.transition_digest,
            "ledger_digest": run.ledger_digest,
            "reconciliation_digest": run.reconciliation_digest,
        }
        if any(paper_payload.get(key) != value for key, value in paper_links.items()):
            raise ValueError("paper result payload linkage is invalid")

    history_artifact = by_kind.get(PaperLifecycleArtifactKind.HISTORY_RESULT)
    if history_artifact is not None:
        history_payload = _payload_mapping(history_artifact)
        if history_payload.get("history_digest") != run.history_digest:
            raise ValueError("history payload digest does not match root")

    observation_artifact = by_kind.get(PaperLifecycleArtifactKind.OUTCOME_OBSERVATION)
    if observation_artifact is not None:
        observation_payload = _payload_mapping(observation_artifact)
        if observation_payload.get("history_digest") != run.history_digest:
            raise ValueError("observation history link does not match root")


def _payload_mapping(value: PaperLifecycleArtifactSnapshot) -> dict[str, Any]:
    parsed = json.loads(value.canonical_payload)
    if not isinstance(parsed, dict):
        raise ValueError(f"{value.artifact_kind.value} payload must be an object")
    return parsed


def _compare_existing(
    run: PaperLifecycleRun,
    artifacts: tuple[PaperLifecycleArtifact, ...],
    candidate: _PersistenceBundle,
) -> PaperLifecyclePersistenceResult:
    try:
        stored = _snapshot_bundle(run, artifacts)
    except (AttributeError, KeyError, TypeError, ValueError):
        return _write_result(
            PaperLifecyclePersistenceOutcome.CONFLICT,
            ("PERSISTED_BUNDLE_CORRUPT",),
            digest=candidate.run.lifecycle_result_digest,
        )
    if stored == candidate:
        return _write_result(
            PaperLifecyclePersistenceOutcome.ALREADY_STORED,
            (),
            digest=candidate.run.lifecycle_result_digest,
            count=len(candidate.artifacts),
        )
    return _write_result(
        PaperLifecyclePersistenceOutcome.CONFLICT,
        ("PERSISTED_BUNDLE_MISMATCH",),
        digest=candidate.run.lifecycle_result_digest,
    )


def _run_values(run: PaperLifecycleRunSnapshot) -> dict[str, Any]:
    return {
        "lifecycle_result_digest": run.lifecycle_result_digest,
        "lifecycle_contract_version": run.lifecycle_contract_version,
        "outcome": run.outcome.value,
        "reason_codes_json": _canonical_json(run.reason_codes),
        "admission_digest": run.admission_digest,
        "decision_intent_digest": run.decision_intent_digest,
        "simulation_input_digest": run.simulation_input_digest,
        "fill_digest": run.fill_digest,
        "transition_digest": run.transition_digest,
        "ledger_digest": run.ledger_digest,
        "reconciliation_digest": run.reconciliation_digest,
        "paper_result_digest": run.paper_result_digest,
        "history_digest": run.history_digest,
        "observation_digest": run.observation_digest,
        "artifact_count": run.artifact_count,
    }


def _artifact_values(value: PaperLifecycleArtifactSnapshot) -> dict[str, Any]:
    return {
        "artifact_kind": value.artifact_kind.value,
        "artifact_digest": value.artifact_digest,
        "payload_digest": value.payload_digest,
        "owner_contract_version": value.owner_contract_version,
        "canonical_payload": value.canonical_payload,
        "ordinal": value.ordinal,
    }


def _history_payload(value: Any) -> dict[str, Any]:
    return {
        "outcome": value.outcome.value,
        "accepted": value.accepted,
        "result": value.result.canonical_dict() if value.result is not None else None,
        "results": tuple(result.canonical_dict() for result in value.results),
        "reason_codes": value.reason_codes,
        "history_digest": value.history_digest,
        "contract_version": value.contract_version,
    }


def _validate_owner(value: Any) -> None:
    try:
        rebuilt = replace(value)
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("owner artifact is invalid or tampered") from error
    if rebuilt != value:
        raise ValueError("owner artifact is non-canonical")


def _owner_version(value: Any) -> str:
    version = getattr(value, "contract_version", None)
    if version is None:
        version = getattr(value, "state_version", None)
    return _text(version, "owner_contract_version")


def _artifact_digest(value: Any, name: str) -> str | None:
    return getattr(value, name) if value is not None else None


def _write_result(
    outcome: PaperLifecyclePersistenceOutcome,
    reasons: tuple[str, ...],
    *,
    digest: str | None = None,
    count: int = 0,
) -> PaperLifecyclePersistenceResult:
    return PaperLifecyclePersistenceResult(
        outcome=outcome,
        reason_codes=reasons,
        lifecycle_result_digest=digest,
        artifact_count=count,
    )


def _read_result(
    outcome: PaperLifecycleReadOutcome,
    reasons: tuple[str, ...],
    digest: str,
    *,
    run: PaperLifecycleRunSnapshot | None = None,
    artifacts: tuple[PaperLifecycleArtifactSnapshot, ...] = (),
) -> PaperLifecycleReadResult:
    return PaperLifecycleReadResult(
        outcome=outcome,
        reason_codes=reasons,
        lifecycle_result_digest=digest,
        run=run,
        artifacts=artifacts,
    )


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be canonical non-empty text")
    return value


def _digest_text(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _reason_codes(value: Any) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValueError("reason_codes must be an immutable tuple")
    if any(not isinstance(item, str) or not item or item != item.strip() for item in value):
        raise ValueError("reason_codes must contain canonical non-empty text")
    if len(set(value)) != len(value):
        raise ValueError("reason_codes must not contain duplicates")
    return value


def _decimal_text(value: Decimal) -> str:
    return format(Decimal("0") if value == 0 else value.normalize(), "f")


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("float values must be finite")
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("decimal values must be finite")
        return _decimal_text(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("canonical mapping keys must be strings")
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(child) for child in value]
    raise ValueError(f"{type(value).__name__} cannot be canonically serialized")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "P01_RTI_03_CONTRACT_VERSION",
    "ControlledPaperPersistenceService",
    "PaperLifecycleArtifactKind",
    "PaperLifecycleArtifactSnapshot",
    "PaperLifecyclePersistenceOutcome",
    "PaperLifecyclePersistenceResult",
    "PaperLifecycleReadOutcome",
    "PaperLifecycleReadResult",
    "PaperLifecycleRunSnapshot",
]
