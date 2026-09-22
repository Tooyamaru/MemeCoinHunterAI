"""One caller-triggered P01-RTI-01 through P01-RTI-03 composition."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
import hashlib
import json
import re
from typing import Any

from backend.application.paper_lifecycle_persistence import (
    ControlledPaperPersistenceService,
    PaperLifecyclePersistenceOutcome,
    PaperLifecyclePersistenceResult,
)
from backend.application.service import ServiceRequestContext
from core.decision import DecisionEvaluationRuleset
from core.execution import (
    ExecutionObservation,
    InitialPaperStateIdentity,
    ReplayIdentity,
    SimulationConfigurationIdentity,
)
from core.opportunity.opportunity_context import OpportunityContext
from core.risk.paper_risk_capital_authorization import (
    PaperRiskCapitalPolicySnapshot,
)
from core.runtime.controlled_paper_lifecycle import (
    ControlledPaperLifecycleResult,
    PaperFillInstruction,
    PaperLifecycleEvidence,
    run_controlled_paper_lifecycle,
)
from core.runtime.controlled_paper_run_admission import (
    ControlledPaperRunAdmissionResult,
    prepare_controlled_paper_run,
)


P01_RTI_04_CONTRACT_VERSION = "p01-rti-04-v1"

_INVOCATION_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")


class ControlledPaperRunOutcome(StrEnum):
    PERSISTED = "PERSISTED"
    ALREADY_PERSISTED = "ALREADY_PERSISTED"
    PERSISTENCE_CONFLICT = "PERSISTENCE_CONFLICT"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class ControlledPaperRunRequest:
    """All explicit owner inputs for exactly one persisted paper run."""

    invocation_id: str
    opportunity_context: OpportunityContext
    decision_ruleset: DecisionEvaluationRuleset
    policy_snapshot: PaperRiskCapitalPolicySnapshot
    execution_observation: ExecutionObservation
    simulation_configuration: SimulationConfigurationIdentity
    initial_paper_state: InitialPaperStateIdentity
    replay_identity: ReplayIdentity
    fill_instruction: PaperFillInstruction
    lifecycle_evidence: PaperLifecycleEvidence
    decision_time: datetime | None = None
    request_context: ServiceRequestContext | None = field(
        default=None,
        compare=False,
        repr=False,
    )
    contract_version: str = P01_RTI_04_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _invocation_id(self.invocation_id)
        if self.contract_version != P01_RTI_04_CONTRACT_VERSION:
            raise ValueError("unsupported request contract_version")
        expected_types = (
            (self.opportunity_context, OpportunityContext),
            (self.decision_ruleset, DecisionEvaluationRuleset),
            (self.policy_snapshot, PaperRiskCapitalPolicySnapshot),
            (self.execution_observation, ExecutionObservation),
            (self.simulation_configuration, SimulationConfigurationIdentity),
            (self.initial_paper_state, InitialPaperStateIdentity),
            (self.replay_identity, ReplayIdentity),
            (self.fill_instruction, PaperFillInstruction),
            (self.lifecycle_evidence, PaperLifecycleEvidence),
        )
        if any(type(value) is not expected for value, expected in expected_types):
            raise ValueError("request contains an unsupported owner input type")
        if self.decision_time is not None and type(self.decision_time) is not datetime:
            raise ValueError("decision_time must be a datetime or None")
        if (
            self.request_context is not None
            and type(self.request_context) is not ServiceRequestContext
        ):
            raise ValueError("request_context must be ServiceRequestContext or None")


@dataclass(frozen=True)
class ControlledPaperRunResult:
    """Deterministic outer result preserving every reached owner result."""

    outcome: ControlledPaperRunOutcome | str
    reason_codes: tuple[str, ...]
    invocation_id: str | None
    admission: ControlledPaperRunAdmissionResult | None = None
    lifecycle: ControlledPaperLifecycleResult | None = None
    persistence: PaperLifecyclePersistenceResult | None = None
    contract_version: str = P01_RTI_04_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        try:
            outcome = ControlledPaperRunOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported controlled paper run outcome") from error
        object.__setattr__(self, "outcome", outcome)
        if self.contract_version != P01_RTI_04_CONTRACT_VERSION:
            raise ValueError("unsupported result contract_version")
        reasons = _reason_codes(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)
        if self.invocation_id is not None:
            _invocation_id(self.invocation_id)
        self._validate_nested_results()
        self._validate_shape()
        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("result_digest does not match controlled paper run")
        object.__setattr__(self, "result_digest", expected)

    def _validate_nested_results(self) -> None:
        for value, expected, name in (
            (
                self.admission,
                ControlledPaperRunAdmissionResult,
                "admission",
            ),
            (self.lifecycle, ControlledPaperLifecycleResult, "lifecycle"),
            (
                self.persistence,
                PaperLifecyclePersistenceResult,
                "persistence",
            ),
        ):
            if value is None:
                continue
            if type(value) is not expected:
                raise ValueError(f"{name} has an unsupported type")
            try:
                canonical = replace(value)
            except (AttributeError, TypeError, ValueError) as error:
                raise ValueError(f"{name} is invalid or tampered") from error
            if canonical != value:
                raise ValueError(f"{name} is not canonical")

        if self.lifecycle is not None:
            if (
                self.admission is None
                or self.lifecycle.admission.digest != self.admission.digest
            ):
                raise ValueError("lifecycle does not preserve the admission digest")
        if self.persistence is not None:
            if self.lifecycle is None:
                raise ValueError("persistence requires a lifecycle result")
            digest = self.persistence.lifecycle_result_digest
            if digest is not None and digest != self.lifecycle.digest:
                raise ValueError("persistence does not preserve the lifecycle digest")

    def _validate_shape(self) -> None:
        outcome = self.outcome
        if outcome is ControlledPaperRunOutcome.INVALID_INPUT:
            if not self.reason_codes:
                raise ValueError("INVALID_INPUT requires reason codes")
            if self.persistence is not None:
                if (
                    self.persistence.outcome
                    is not PaperLifecyclePersistenceOutcome.INVALID_INPUT
                    or self.reason_codes != self.persistence.reason_codes
                ):
                    raise ValueError(
                        "INVALID_INPUT must preserve invalid persistence reasons"
                    )
            return
        if self.invocation_id is None:
            raise ValueError("non-invalid result requires invocation_id")
        if self.admission is None or self.lifecycle is None or self.persistence is None:
            raise ValueError("reached persistence outcome requires all nested results")

        expected_persistence = {
            ControlledPaperRunOutcome.PERSISTED: (
                PaperLifecyclePersistenceOutcome.STORED,
                False,
            ),
            ControlledPaperRunOutcome.ALREADY_PERSISTED: (
                PaperLifecyclePersistenceOutcome.ALREADY_STORED,
                False,
            ),
            ControlledPaperRunOutcome.PERSISTENCE_CONFLICT: (
                PaperLifecyclePersistenceOutcome.CONFLICT,
                True,
            ),
            ControlledPaperRunOutcome.STORAGE_UNAVAILABLE: (
                PaperLifecyclePersistenceOutcome.STORAGE_UNAVAILABLE,
                True,
            ),
        }[outcome]
        expected_outcome, expects_reasons = expected_persistence
        if self.persistence.outcome is not expected_outcome:
            raise ValueError("outer outcome does not match persistence outcome")
        if expects_reasons:
            if self.reason_codes != self.persistence.reason_codes:
                raise ValueError("outer result must preserve persistence reasons")
        elif self.reason_codes:
            raise ValueError("successful outer result cannot contain reason codes")

    def _without_digest(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "invocation_id": self.invocation_id,
            "admission_digest": self.admission.digest if self.admission else None,
            "lifecycle_digest": self.lifecycle.digest if self.lifecycle else None,
            "persistence_digest": (
                self.persistence.digest if self.persistence else None
            ),
        }

    @property
    def canonical_representation(self) -> dict[str, Any]:
        return {**self._without_digest(), "result_digest": self.result_digest}

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


class ControlledPaperRunService:
    """Coordinate one exact admission, lifecycle, and persistence attempt."""

    def __init__(self, persistence: ControlledPaperPersistenceService) -> None:
        if not isinstance(persistence, ControlledPaperPersistenceService):
            raise ValueError("persistence must be ControlledPaperPersistenceService")
        self.persistence = persistence

    async def run(self, request: object) -> ControlledPaperRunResult:
        if type(request) is not ControlledPaperRunRequest:
            return _invalid(None, "INVALID_REQUEST_TYPE")
        try:
            canonical_request = replace(request)
        except (AttributeError, TypeError, ValueError):
            return _invalid(_safe_invocation_id(request), "INVALID_REQUEST")
        if canonical_request != request:
            return _invalid(request.invocation_id, "NON_CANONICAL_REQUEST")

        admission: ControlledPaperRunAdmissionResult | None = None
        lifecycle: ControlledPaperLifecycleResult | None = None
        try:
            raw_admission = prepare_controlled_paper_run(
                opportunity_context=request.opportunity_context,
                decision_ruleset=request.decision_ruleset,
                policy_snapshot=request.policy_snapshot,
                execution_observation=request.execution_observation,
                simulation_configuration=request.simulation_configuration,
                initial_paper_state=request.initial_paper_state,
                replay_identity=request.replay_identity,
                decision_time=request.decision_time,
            )
            admission = _canonical_owner_result(
                raw_admission,
                ControlledPaperRunAdmissionResult,
                "ADMISSION_RESULT_INVALID",
            )
            raw_lifecycle = run_controlled_paper_lifecycle(
                admission,
                fill_instruction=request.fill_instruction,
                lifecycle_evidence=request.lifecycle_evidence,
            )
            lifecycle = _canonical_owner_result(
                raw_lifecycle,
                ControlledPaperLifecycleResult,
                "LIFECYCLE_RESULT_INVALID",
            )
            if lifecycle.admission.digest != admission.digest:
                return _invalid(
                    request.invocation_id,
                    "ADMISSION_LIFECYCLE_LINK_INVALID",
                    admission=admission,
                )
        except _OwnerResultError as error:
            return _invalid(
                request.invocation_id,
                error.reason,
                admission=admission,
            )
        except (AttributeError, ArithmeticError, KeyError, TypeError, ValueError):
            return _invalid(
                request.invocation_id,
                "OWNER_COMPOSITION_FAILED",
                admission=admission,
            )

        persistence = await self.persistence.persist(lifecycle)
        try:
            persistence = _canonical_owner_result(
                persistence,
                PaperLifecyclePersistenceResult,
                "PERSISTENCE_RESULT_INVALID",
            )
        except _OwnerResultError as error:
            return _invalid(
                request.invocation_id,
                error.reason,
                admission=admission,
                lifecycle=lifecycle,
            )
        if (
            persistence.lifecycle_result_digest is not None
            and persistence.lifecycle_result_digest != lifecycle.digest
        ):
            return _invalid(
                request.invocation_id,
                "LIFECYCLE_PERSISTENCE_LINK_INVALID",
                admission=admission,
                lifecycle=lifecycle,
            )

        outcome = {
            PaperLifecyclePersistenceOutcome.STORED: (
                ControlledPaperRunOutcome.PERSISTED
            ),
            PaperLifecyclePersistenceOutcome.ALREADY_STORED: (
                ControlledPaperRunOutcome.ALREADY_PERSISTED
            ),
            PaperLifecyclePersistenceOutcome.CONFLICT: (
                ControlledPaperRunOutcome.PERSISTENCE_CONFLICT
            ),
            PaperLifecyclePersistenceOutcome.STORAGE_UNAVAILABLE: (
                ControlledPaperRunOutcome.STORAGE_UNAVAILABLE
            ),
            PaperLifecyclePersistenceOutcome.INVALID_INPUT: (
                ControlledPaperRunOutcome.INVALID_INPUT
            ),
        }[persistence.outcome]
        reasons = persistence.reason_codes if outcome not in {
            ControlledPaperRunOutcome.PERSISTED,
            ControlledPaperRunOutcome.ALREADY_PERSISTED,
        } else ()
        return ControlledPaperRunResult(
            outcome=outcome,
            reason_codes=reasons,
            invocation_id=request.invocation_id,
            admission=admission,
            lifecycle=lifecycle,
            persistence=persistence,
        )


class _OwnerResultError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _canonical_owner_result(value: object, expected: type, reason: str):
    if type(value) is not expected:
        raise _OwnerResultError(reason)
    try:
        canonical = replace(value)
    except (AttributeError, TypeError, ValueError) as error:
        raise _OwnerResultError(reason) from error
    if canonical != value:
        raise _OwnerResultError(reason)
    return canonical


def _invalid(
    invocation_id: str | None,
    reason: str,
    *,
    admission: ControlledPaperRunAdmissionResult | None = None,
    lifecycle: ControlledPaperLifecycleResult | None = None,
    persistence: PaperLifecyclePersistenceResult | None = None,
) -> ControlledPaperRunResult:
    return ControlledPaperRunResult(
        outcome=ControlledPaperRunOutcome.INVALID_INPUT,
        reason_codes=(reason,),
        invocation_id=invocation_id,
        admission=admission,
        lifecycle=lifecycle,
        persistence=persistence,
    )


def _safe_invocation_id(request: ControlledPaperRunRequest) -> str | None:
    try:
        return _invocation_id(request.invocation_id)
    except (TypeError, ValueError):
        return None


def _invocation_id(value: object) -> str:
    if not isinstance(value, str) or _INVOCATION_ID.fullmatch(value) is None:
        raise ValueError("invocation_id must use the canonical closed format")
    return value


def _reason_codes(values: object) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ValueError("reason_codes must be a tuple")
    if any(
        not isinstance(value, str) or not value or value != value.strip()
        for value in values
    ):
        raise ValueError("reason_codes must contain canonical non-empty text")
    if len(set(values)) != len(values):
        raise ValueError("reason_codes must not contain duplicates")
    return values


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


__all__ = [
    "P01_RTI_04_CONTRACT_VERSION",
    "ControlledPaperRunOutcome",
    "ControlledPaperRunRequest",
    "ControlledPaperRunResult",
    "ControlledPaperRunService",
]
