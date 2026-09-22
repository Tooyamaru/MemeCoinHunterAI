"""Compose one deterministic, paper-only run admission attempt.

This boundary delegates decisions to P06, authorization to the independent
Risk/Capital Authority, and admission validation to P07-T01. It performs no
fill, position, ledger, persistence, provider, wallet, or execution behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import hashlib
import json
from typing import Any

from core.decision import (
    DecisionEvaluationRuleset,
    DecisionIntent,
    evaluate_decision_intent,
)
from core.execution import (
    AuthorizationObservation,
    ExecutionObservation,
    InitialPaperStateIdentity,
    PaperSimulationInput,
    ReplayIdentity,
    SimulationConfigurationIdentity,
)
from core.opportunity.opportunity_context import OpportunityContext
from core.risk.paper_risk_capital_authorization import (
    AuthorizationStatus,
    PaperRiskCapitalAuthorizationResult,
    PaperRiskCapitalPolicySnapshot,
    evaluate_paper_risk_capital_authorization,
)


P01_RTI_01_CONTRACT_VERSION = "p01-rti-01-v1"


class ControlledPaperRunAdmissionOutcome(StrEnum):
    READY_FOR_PAPER_SIMULATION = "READY_FOR_PAPER_SIMULATION"
    AUTHORIZATION_REJECTED = "AUTHORIZATION_REJECTED"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class ControlledPaperRunAdmissionResult:
    """Immutable result of one controlled P05→P06→Risk→P07 admission."""

    outcome: ControlledPaperRunAdmissionOutcome | str
    reason_codes: tuple[str, ...]
    decision_intent: DecisionIntent | None = None
    risk_capital_authorization: PaperRiskCapitalAuthorizationResult | None = None
    paper_simulation_input: PaperSimulationInput | None = None
    contract_version: str = P01_RTI_01_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        try:
            outcome = ControlledPaperRunAdmissionOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported controlled admission outcome") from error
        object.__setattr__(self, "outcome", outcome)
        if self.contract_version != P01_RTI_01_CONTRACT_VERSION:
            raise ValueError("unsupported controlled admission contract_version")
        if (
            not isinstance(self.reason_codes, tuple)
            or any(
                not isinstance(reason, str)
                or not reason
                or reason != reason.strip()
                for reason in self.reason_codes
            )
        ):
            raise ValueError("reason_codes must be canonical non-empty text")
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("reason_codes must not contain duplicates")
        self._validate_shape()
        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("result_digest does not match canonical result")
        object.__setattr__(self, "result_digest", expected)

    def _validate_shape(self) -> None:
        outcome = self.outcome
        if outcome is ControlledPaperRunAdmissionOutcome.READY_FOR_PAPER_SIMULATION:
            if self.reason_codes:
                raise ValueError("ready result cannot contain reason codes")
            if not isinstance(self.decision_intent, DecisionIntent):
                raise ValueError("ready result requires DecisionIntent")
            authorization = self.risk_capital_authorization
            if (
                not isinstance(authorization, PaperRiskCapitalAuthorizationResult)
                or authorization.status is not AuthorizationStatus.APPROVED
            ):
                raise ValueError("ready result requires approved Risk/Capital result")
            if not isinstance(self.paper_simulation_input, PaperSimulationInput):
                raise ValueError("ready result requires P07-T01 input")
            if (
                authorization.decision_intent_digest != self.decision_intent.digest
                or self.paper_simulation_input.decision_intent.decision_intent_digest
                != self.decision_intent.digest
            ):
                raise ValueError("ready result identity linkage is invalid")
            return
        if outcome is ControlledPaperRunAdmissionOutcome.AUTHORIZATION_REJECTED:
            authorization = self.risk_capital_authorization
            if not isinstance(self.decision_intent, DecisionIntent):
                raise ValueError("rejected result requires DecisionIntent")
            if (
                not isinstance(authorization, PaperRiskCapitalAuthorizationResult)
                or authorization.status is not AuthorizationStatus.REJECTED
            ):
                raise ValueError("rejected result requires canonical rejection")
            if self.paper_simulation_input is not None:
                raise ValueError("rejected result cannot contain P07-T01 input")
            if not self.reason_codes or self.reason_codes != authorization.reason_codes:
                raise ValueError("rejected result must preserve authority reasons")
            return
        if not self.reason_codes:
            raise ValueError("invalid result requires a reason code")
        if self.paper_simulation_input is not None:
            raise ValueError("invalid result cannot contain P07-T01 input")

    def _without_digest(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "decision_intent_digest": (
                self.decision_intent.digest if self.decision_intent is not None else None
            ),
            "risk_capital_authorization_digest": (
                self.risk_capital_authorization.digest
                if self.risk_capital_authorization is not None
                else None
            ),
            "paper_simulation_input_digest": (
                self.paper_simulation_input.input_digest
                if self.paper_simulation_input is not None
                else None
            ),
        }

    @property
    def canonical_representation(self) -> dict[str, Any]:
        return {**self._without_digest(), "result_digest": self.result_digest}

    deterministic_representation = property(lambda self: self.canonical_representation)

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


def prepare_controlled_paper_run(
    *,
    opportunity_context: OpportunityContext,
    decision_ruleset: DecisionEvaluationRuleset,
    policy_snapshot: PaperRiskCapitalPolicySnapshot,
    execution_observation: ExecutionObservation,
    simulation_configuration: SimulationConfigurationIdentity,
    initial_paper_state: InitialPaperStateIdentity,
    replay_identity: ReplayIdentity,
    decision_time: datetime | None = None,
) -> ControlledPaperRunAdmissionResult:
    """Prepare exactly one validated P07-T01 input, or fail closed."""

    inputs = (
        (opportunity_context, OpportunityContext),
        (decision_ruleset, DecisionEvaluationRuleset),
        (policy_snapshot, PaperRiskCapitalPolicySnapshot),
        (execution_observation, ExecutionObservation),
        (simulation_configuration, SimulationConfigurationIdentity),
        (initial_paper_state, InitialPaperStateIdentity),
        (replay_identity, ReplayIdentity),
    )
    if any(type(value) is not expected for value, expected in inputs):
        return _invalid("UNSUPPORTED_INPUT_TYPE")
    if decision_time is not None and type(decision_time) is not datetime:
        return _invalid("INVALID_DECISION_TIME")

    try:
        decision = evaluate_decision_intent(
            opportunity_context,
            ruleset=decision_ruleset,
            decision_time=decision_time,
        )
    except (AttributeError, TypeError, ValueError):
        return _invalid("P06_INVALID_INPUT")

    try:
        authorization = evaluate_paper_risk_capital_authorization(
            decision,
            policy_snapshot,
        )
    except (AttributeError, TypeError, ValueError):
        return _invalid("RISK_CAPITAL_INVALID_INPUT", decision=decision)

    if authorization.status is AuthorizationStatus.REJECTED:
        return ControlledPaperRunAdmissionResult(
            outcome=ControlledPaperRunAdmissionOutcome.AUTHORIZATION_REJECTED,
            reason_codes=authorization.reason_codes,
            decision_intent=decision,
            risk_capital_authorization=authorization,
        )

    try:
        simulation_input = PaperSimulationInput(
            decision_intent=decision,
            authorization_observation=(
                AuthorizationObservation.from_risk_capital_result(authorization)
            ),
            execution_observation=execution_observation,
            simulation_configuration=simulation_configuration,
            initial_paper_state=initial_paper_state,
            simulation_reference_time=authorization.simulation_reference_time,
            replay_identity=replay_identity,
        )
    except (AttributeError, TypeError, ValueError):
        return _invalid(
            "P07_ADMISSION_INVALID_INPUT",
            decision=decision,
            authorization=authorization,
        )

    return ControlledPaperRunAdmissionResult(
        outcome=ControlledPaperRunAdmissionOutcome.READY_FOR_PAPER_SIMULATION,
        reason_codes=(),
        decision_intent=decision,
        risk_capital_authorization=authorization,
        paper_simulation_input=simulation_input,
    )


def _invalid(
    reason: str,
    *,
    decision: DecisionIntent | None = None,
    authorization: PaperRiskCapitalAuthorizationResult | None = None,
) -> ControlledPaperRunAdmissionResult:
    return ControlledPaperRunAdmissionResult(
        outcome=ControlledPaperRunAdmissionOutcome.INVALID_INPUT,
        reason_codes=(reason,),
        decision_intent=decision,
        risk_capital_authorization=authorization,
    )


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
    "P01_RTI_01_CONTRACT_VERSION",
    "ControlledPaperRunAdmissionOutcome",
    "ControlledPaperRunAdmissionResult",
    "prepare_controlled_paper_run",
]
