"""P01-OSC-02: prevalidated RTI-14 suffix through RTI-15 and RTI-16 only."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import re
from typing import Any, Mapping

from backend.application.decision_to_risk_capital_continuation import (
    P01_RTI_14_CONTRACT_VERSION,
    DecisionToRiskCapitalOutcome,
    P01Rti14RiskCapitalContinuationResult,
)
from backend.application.risk_capital_to_paper_admission_continuation import (
    P01Rti15PaperAdmissionContinuationResult,
    RiskCapitalToPaperAdmissionContinuationService,
    RiskCapitalToPaperAdmissionOutcome,
)
from backend.application.rti15_to_controlled_paper_lifecycle import (
    P01Rti16ControlledPaperLifecycleContinuationResult,
    Rti15ToControlledLifecycleOutcome,
    Rti15ToControlledPaperLifecycleContinuationService,
)
from core.execution import (
    ExecutionObservation,
    InitialPaperStateIdentity,
    ReplayIdentity,
    SimulationConfigurationIdentity,
)
from core.risk.paper_risk_capital_authorization import (
    AuthorizationStatus,
    PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY,
)
from core.runtime.controlled_paper_lifecycle import (
    PaperFillInstruction,
    PaperLifecycleEvidence,
)


P01_OSC_02_CONTRACT_VERSION = "p01-osc-02-v1"


class PrevalidatedSuffixOutcome(StrEnum):
    LIFECYCLE_RETURNED = "LIFECYCLE_RETURNED"
    UPSTREAM_STOPPED = "UPSTREAM_STOPPED"
    OWNER_UNAVAILABLE = "OWNER_UNAVAILABLE"


def _canonical(value: Any, expected_type: type) -> bool:
    if type(value) is not expected_type:
        return False
    try:
        rebuilt = _rebuild_preserving_links(value)
        return type(rebuilt) is expected_type and rebuilt == value
    except (AttributeError, TypeError, ValueError, KeyError, ArithmeticError):
        return False


def _rebuild_preserving_links(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            _rebuild_preserving_links(getattr(value, field.name))
        rebuilt = replace(value)
        if rebuilt != value:
            raise ValueError("nested owner is not canonical")
        return rebuilt
    if isinstance(value, tuple):
        for child in value:
            _rebuild_preserving_links(child)
    return value


def _digest(value: Any) -> str:
    def encode(item: Any) -> Any:
        if isinstance(item, datetime):
            return item.astimezone(timezone.utc).isoformat()
        if isinstance(item, StrEnum):
            return item.value
        if isinstance(item, Mapping):
            return {str(key): encode(item[key]) for key in sorted(item)}
        if isinstance(item, (tuple, list)):
            return [encode(child) for child in item]
        return item

    return hashlib.sha256(
        json.dumps(
            encode(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class P01Osc02Request:
    invocation_id: str
    rti14_result: P01Rti14RiskCapitalContinuationResult
    execution_observation: ExecutionObservation
    simulation_configuration: SimulationConfigurationIdentity
    initial_paper_state: InitialPaperStateIdentity
    replay_identity: ReplayIdentity
    fill_instruction: PaperFillInstruction
    lifecycle_evidence: PaperLifecycleEvidence
    contract_version: str = P01_OSC_02_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_OSC_02_CONTRACT_VERSION:
            raise ValueError("unsupported OSC-02 contract version")
        if (
            type(self.invocation_id) is not str
            or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", self.invocation_id)
        ):
            raise ValueError("invalid invocation identity")
        for name, expected in (
            ("rti14_result", P01Rti14RiskCapitalContinuationResult),
            ("execution_observation", ExecutionObservation),
            ("simulation_configuration", SimulationConfigurationIdentity),
            ("initial_paper_state", InitialPaperStateIdentity),
            ("replay_identity", ReplayIdentity),
            ("fill_instruction", PaperFillInstruction),
            ("lifecycle_evidence", PaperLifecycleEvidence),
        ):
            if not _canonical(getattr(self, name), expected):
                raise ValueError(f"noncanonical {name}")

        if self.rti14_result.contract_version != P01_RTI_14_CONTRACT_VERSION:
            raise ValueError("unsupported RTI-14 contract version")

        authorization = self.rti14_result.authorization_result
        if authorization is not None:
            if (
                authorization.authorization_effect
                != PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
            ):
                raise ValueError("unsupported Risk/Capital authorization effect")
            decision = self.rti14_result.upstream_result.decision_intent
            if decision is None:
                raise ValueError("authorization is missing exact DecisionIntent")
            if (
                authorization.decision_intent_digest != decision.digest
                or authorization.context_digest != decision.context_digest
            ):
                raise ValueError("authorization does not match exact DecisionIntent")

    @property
    def input_digests(self) -> Mapping[str, str]:
        return {
            "rti14_result": self.rti14_result.digest,
            "execution_observation": self.execution_observation.observation_digest,
            "simulation_configuration": self.simulation_configuration.configuration_digest,
            "initial_paper_state": self.initial_paper_state.state_digest,
            "replay_identity": _digest(self.replay_identity.canonical_representation),
            "fill_instruction": self.fill_instruction.digest,
            "lifecycle_evidence": self.lifecycle_evidence.digest,
        }


@dataclass(frozen=True)
class P01Osc02Result:
    request: P01Osc02Request
    outcome: PrevalidatedSuffixOutcome | str
    reason_codes: tuple[str, ...]
    terminal_stage: str
    rti15_result: P01Rti15PaperAdmissionContinuationResult | None = None
    rti16_result: P01Rti16ControlledPaperLifecycleContinuationResult | None = None
    contract_version: str = P01_OSC_02_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        if type(self.request) is not P01Osc02Request:
            raise ValueError("invalid OSC-02 request")
        self.request.__post_init__()
        if self.contract_version != P01_OSC_02_CONTRACT_VERSION:
            raise ValueError("unsupported OSC-02 result contract")
        try:
            outcome = PrevalidatedSuffixOutcome(self.outcome)
        except (TypeError, ValueError):
            raise ValueError("unsupported OSC-02 outcome") from None
        object.__setattr__(self, "outcome", outcome)
        if (
            type(self.reason_codes) is not tuple
            or any(type(reason) is not str or not reason for reason in self.reason_codes)
        ):
            raise ValueError("invalid OSC-02 reasons")
        if self.terminal_stage not in ("RTI-14", "RTI-15", "RTI-16"):
            raise ValueError("invalid OSC-02 terminal stage")

        if self.rti15_result is not None:
            if (
                not _canonical(
                    self.rti15_result,
                    P01Rti15PaperAdmissionContinuationResult,
                )
                or self.rti15_result.upstream_result is not self.request.rti14_result
                or self.rti15_result.execution_observation
                is not self.request.execution_observation
                or self.rti15_result.simulation_configuration
                is not self.request.simulation_configuration
                or self.rti15_result.initial_paper_state
                is not self.request.initial_paper_state
                or self.rti15_result.replay_identity is not self.request.replay_identity
            ):
                raise ValueError("invalid exact RTI-15 result")
        if self.rti16_result is not None:
            if (
                self.rti15_result is None
                or not _canonical(
                    self.rti16_result,
                    P01Rti16ControlledPaperLifecycleContinuationResult,
                )
                or self.rti16_result.upstream_result is not self.rti15_result
                or self.rti16_result.fill_instruction is not self.request.fill_instruction
                or self.rti16_result.lifecycle_evidence
                is not self.request.lifecycle_evidence
            ):
                raise ValueError("invalid exact RTI-16 result")

        if outcome is PrevalidatedSuffixOutcome.LIFECYCLE_RETURNED:
            if (
                self.terminal_stage != "RTI-16"
                or self.reason_codes
                or self.rti15_result is None
                or self.rti16_result is None
                or self.rti16_result.outcome
                is not Rti15ToControlledLifecycleOutcome.LIFECYCLE_MATERIALIZED
            ):
                raise ValueError("invalid OSC-02 lifecycle result")
        elif outcome is PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE:
            expected = {
                "RTI-14": ("RTI-15_UNAVAILABLE",),
                "RTI-15": ("RTI-16_UNAVAILABLE",),
            }.get(self.terminal_stage)
            if (
                expected is None
                or self.reason_codes != expected
                or self.rti16_result is not None
            ):
                raise ValueError("invalid OSC-02 unavailable result")
        else:
            if not self.reason_codes:
                raise ValueError("OSC-02 upstream stop requires reasons")
            if self.terminal_stage == "RTI-14":
                if self.rti15_result is not None or self.rti16_result is not None:
                    raise ValueError("RTI-14 stop cannot contain suffix results")
                if _approved(self.request.rti14_result):
                    raise ValueError("RTI-14 stop cannot contain approved authorization")
            elif self.terminal_stage == "RTI-15":
                if (
                    self.rti15_result is None
                    or self.rti16_result is not None
                    or self.rti15_result.outcome
                    is RiskCapitalToPaperAdmissionOutcome.ADMISSION_MATERIALIZED
                ):
                    raise ValueError("invalid RTI-15 stop")
            else:
                if (
                    self.rti15_result is None
                    or self.rti16_result is None
                    or self.rti16_result.outcome
                    is Rti15ToControlledLifecycleOutcome.LIFECYCLE_MATERIALIZED
                ):
                    raise ValueError("invalid RTI-16 stop")

        expected_digest = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected_digest:
            raise ValueError("OSC-02 result digest mismatch")
        object.__setattr__(self, "result_digest", expected_digest)

    def _without_digest(self) -> Mapping[str, Any]:
        authorization = self.request.rti14_result.authorization_result
        return {
            "contract_version": self.contract_version,
            "invocation_id": self.request.invocation_id,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "terminal_stage": self.terminal_stage,
            "input_digests": self.request.input_digests,
            "rti14_contract_version": self.request.rti14_result.contract_version,
            "rti14_outcome": self.request.rti14_result.outcome.value,
            "rti14_result_digest": self.request.rti14_result.digest,
            "authorization_status": (
                authorization.status.value if authorization is not None else None
            ),
            "authorization_result_digest": (
                authorization.digest if authorization is not None else None
            ),
            "rti15_contract_version": (
                self.rti15_result.contract_version
                if self.rti15_result is not None
                else None
            ),
            "rti15_outcome": (
                self.rti15_result.outcome.value
                if self.rti15_result is not None
                else None
            ),
            "rti15_result_digest": (
                self.rti15_result.digest if self.rti15_result is not None else None
            ),
            "rti16_contract_version": (
                self.rti16_result.contract_version
                if self.rti16_result is not None
                else None
            ),
            "rti16_outcome": (
                self.rti16_result.outcome.value
                if self.rti16_result is not None
                else None
            ),
            "rti16_result_digest": (
                self.rti16_result.digest if self.rti16_result is not None else None
            ),
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {**self._without_digest(), "result_digest": self.result_digest}

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]

    @property
    def lifecycle_result(self) -> Any:
        return (
            self.rti16_result.lifecycle_result
            if self.rti16_result is not None
            else None
        )


class PrevalidatedRiskCapitalSuffixCaller:
    def __init__(self, *, rti15: Any = None, rti16: Any = None) -> None:
        self._rti15 = (
            rti15
            if rti15 is not None
            else RiskCapitalToPaperAdmissionContinuationService()
        )
        self._rti16 = (
            rti16
            if rti16 is not None
            else Rti15ToControlledPaperLifecycleContinuationService()
        )
        if not callable(getattr(self._rti15, "continue_to_paper_admission", None)):
            raise ValueError("invalid OSC-02 RTI-15 owner seam")
        if not callable(
            getattr(self._rti16, "continue_to_controlled_paper_lifecycle", None)
        ):
            raise ValueError("invalid OSC-02 RTI-16 owner seam")

    def run(self, request: P01Osc02Request) -> P01Osc02Result:
        if type(request) is not P01Osc02Request:
            raise ValueError("invalid OSC-02 request")
        request.__post_init__()

        if not _approved(request.rti14_result):
            return P01Osc02Result(
                request=request,
                outcome=PrevalidatedSuffixOutcome.UPSTREAM_STOPPED,
                reason_codes=_rti14_stop_reasons(request.rti14_result),
                terminal_stage="RTI-14",
            )

        try:
            rti15 = self._rti15.continue_to_paper_admission(
                request.rti14_result,
                execution_observation=request.execution_observation,
                simulation_configuration=request.simulation_configuration,
                initial_paper_state=request.initial_paper_state,
                replay_identity=request.replay_identity,
            )
        except ValueError:
            raise ValueError("RTI-15 validation failed") from None
        except Exception:
            return P01Osc02Result(
                request=request,
                outcome=PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE,
                reason_codes=("RTI-15_UNAVAILABLE",),
                terminal_stage="RTI-14",
            )

        if not _valid_rti15(rti15, request):
            return P01Osc02Result(
                request=request,
                outcome=PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE,
                reason_codes=("RTI-15_UNAVAILABLE",),
                terminal_stage="RTI-14",
            )
        if rti15.outcome is not RiskCapitalToPaperAdmissionOutcome.ADMISSION_MATERIALIZED:
            return P01Osc02Result(
                request=request,
                outcome=PrevalidatedSuffixOutcome.UPSTREAM_STOPPED,
                reason_codes=rti15.reason_codes or ("RTI-15_STOPPED",),
                terminal_stage="RTI-15",
                rti15_result=rti15,
            )

        try:
            rti16 = self._rti16.continue_to_controlled_paper_lifecycle(
                rti15,
                fill_instruction=request.fill_instruction,
                lifecycle_evidence=request.lifecycle_evidence,
            )
        except ValueError:
            raise ValueError("RTI-16 validation failed") from None
        except Exception:
            return P01Osc02Result(
                request=request,
                outcome=PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE,
                reason_codes=("RTI-16_UNAVAILABLE",),
                terminal_stage="RTI-15",
                rti15_result=rti15,
            )

        if not _valid_rti16(rti16, rti15, request):
            return P01Osc02Result(
                request=request,
                outcome=PrevalidatedSuffixOutcome.OWNER_UNAVAILABLE,
                reason_codes=("RTI-16_UNAVAILABLE",),
                terminal_stage="RTI-15",
                rti15_result=rti15,
            )
        if rti16.outcome is not Rti15ToControlledLifecycleOutcome.LIFECYCLE_MATERIALIZED:
            return P01Osc02Result(
                request=request,
                outcome=PrevalidatedSuffixOutcome.UPSTREAM_STOPPED,
                reason_codes=rti16.reason_codes or ("RTI-16_STOPPED",),
                terminal_stage="RTI-16",
                rti15_result=rti15,
                rti16_result=rti16,
            )
        return P01Osc02Result(
            request=request,
            outcome=PrevalidatedSuffixOutcome.LIFECYCLE_RETURNED,
            reason_codes=(),
            terminal_stage="RTI-16",
            rti15_result=rti15,
            rti16_result=rti16,
        )


def _approved(value: P01Rti14RiskCapitalContinuationResult) -> bool:
    authorization = value.authorization_result
    return (
        value.outcome is DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED
        and authorization is not None
        and authorization.status is AuthorizationStatus.APPROVED
        and authorization.authorization_effect
        == PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
    )


def _rti14_stop_reasons(
    value: P01Rti14RiskCapitalContinuationResult,
) -> tuple[str, ...]:
    if value.reason_codes:
        return value.reason_codes
    authorization = value.authorization_result
    if authorization is not None and authorization.reason_codes:
        return authorization.reason_codes
    return ("AUTHORIZATION_REJECTED",)


def _valid_rti15(value: Any, request: P01Osc02Request) -> bool:
    return (
        _canonical(value, P01Rti15PaperAdmissionContinuationResult)
        and value.upstream_result is request.rti14_result
        and value.execution_observation is request.execution_observation
        and value.simulation_configuration is request.simulation_configuration
        and value.initial_paper_state is request.initial_paper_state
        and value.replay_identity is request.replay_identity
    )


def _valid_rti16(
    value: Any,
    rti15: P01Rti15PaperAdmissionContinuationResult,
    request: P01Osc02Request,
) -> bool:
    return (
        _canonical(value, P01Rti16ControlledPaperLifecycleContinuationResult)
        and value.upstream_result is rti15
        and value.fill_instruction is request.fill_instruction
        and value.lifecycle_evidence is request.lifecycle_evidence
    )


__all__ = [
    "P01_OSC_02_CONTRACT_VERSION",
    "PrevalidatedSuffixOutcome",
    "P01Osc02Request",
    "P01Osc02Result",
    "PrevalidatedRiskCapitalSuffixCaller",
]
