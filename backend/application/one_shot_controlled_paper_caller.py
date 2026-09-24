"""One explicit, in-memory paper invocation through the existing RTI-12–16 owners."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import re
from typing import Any

from backend.application.market_to_opportunity_composition import (
    MarketToOpportunityCompositionOutcome,
    P01Rti11CompositionResult,
)
from backend.application.p05_opportunity_context_continuation import (
    OpportunityContextContinuationOutcome,
    P01Rti12ContinuationResult,
    P05OpportunityContextContinuationService,
)
from backend.application.opportunity_context_to_decision_continuation import (
    OpportunityContextToDecisionOutcome,
    OpportunityContextToDecisionContinuationService,
    P01Rti13DecisionContinuationResult,
)
from backend.application.decision_to_risk_capital_continuation import (
    DecisionToRiskCapitalContinuationService,
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
from core.decision.decision_evaluation import DecisionEvaluationRuleset
from core.execution import (
    ExecutionObservation,
    InitialPaperStateIdentity,
    ReplayIdentity,
    SimulationConfigurationIdentity,
)
from core.risk.paper_risk_capital_authorization import (
    AuthorizationStatus,
    PaperRiskCapitalPolicySnapshot,
)
from core.runtime.controlled_paper_lifecycle import PaperFillInstruction, PaperLifecycleEvidence


P01_OSC_01_CONTRACT_VERSION = "p01-osc-01-v1"
_STAGES = ("RTI-11", "RTI-12", "RTI-13", "RTI-14", "RTI-15", "RTI-16")
_TYPES = (P01Rti11CompositionResult, P01Rti12ContinuationResult,
          P01Rti13DecisionContinuationResult, P01Rti14RiskCapitalContinuationResult,
          P01Rti15PaperAdmissionContinuationResult,
          P01Rti16ControlledPaperLifecycleContinuationResult)


class OneShotPaperOutcome(StrEnum):
    LIFECYCLE_RETURNED = "LIFECYCLE_RETURNED"
    UPSTREAM_STOPPED = "UPSTREAM_STOPPED"
    OWNER_UNAVAILABLE = "OWNER_UNAVAILABLE"


def _canonical(value: Any, expected: type) -> bool:
    if type(value) is not expected:
        return False
    try:
        rebuilt = replace(value)
        return (rebuilt == value and getattr(rebuilt, "canonical_representation", None)
                == getattr(value, "canonical_representation", None))
    except (AttributeError, TypeError, ValueError, KeyError, ArithmeticError):
        return False


def _digest(value: Any) -> str:
    def encode(item: Any) -> Any:
        if isinstance(item, datetime):
            return item.astimezone(timezone.utc).isoformat()
        if isinstance(item, dict):
            return {str(key): encode(child) for key, child in item.items()}
        if hasattr(item, "items"):
            return {str(key): encode(child) for key, child in item.items()}
        if isinstance(item, (tuple, list)):
            return [encode(child) for child in item]
        return item
    return hashlib.sha256(json.dumps(encode(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


@dataclass(frozen=True)
class P01Osc01Request:
    invocation_id: str
    rti11_result: P01Rti11CompositionResult
    decision_ruleset: DecisionEvaluationRuleset
    decision_time: datetime
    policy_snapshot: PaperRiskCapitalPolicySnapshot
    execution_observation: ExecutionObservation
    simulation_configuration: SimulationConfigurationIdentity
    initial_paper_state: InitialPaperStateIdentity
    replay_identity: ReplayIdentity
    fill_instruction: PaperFillInstruction
    lifecycle_evidence: PaperLifecycleEvidence
    contract_version: str = P01_OSC_01_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_OSC_01_CONTRACT_VERSION:
            raise ValueError("unsupported OSC-01 contract version")
        if type(self.invocation_id) is not str or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", self.invocation_id):
            raise ValueError("invalid invocation identity")
        for name, expected in (
            ("rti11_result", P01Rti11CompositionResult),
            ("decision_ruleset", DecisionEvaluationRuleset),
            ("policy_snapshot", PaperRiskCapitalPolicySnapshot),
            ("execution_observation", ExecutionObservation),
            ("simulation_configuration", SimulationConfigurationIdentity),
            ("initial_paper_state", InitialPaperStateIdentity),
            ("replay_identity", ReplayIdentity),
            ("fill_instruction", PaperFillInstruction),
            ("lifecycle_evidence", PaperLifecycleEvidence),
        ):
            if not _canonical(getattr(self, name), expected):
                raise ValueError(f"noncanonical {name}")
        if type(self.decision_time) is not datetime or self.decision_time.tzinfo is None or self.decision_time.utcoffset() is None:
            raise ValueError("decision_time must be timezone-aware")
        if self.rti11_result.outcome is MarketToOpportunityCompositionOutcome.COMPOSED:
            if self.decision_time.astimezone(timezone.utc) < self.rti11_result.request.reference_time:
                raise ValueError("decision_time precedes opportunity reference")
            if (self.policy_snapshot.scope_identity["candidate_id"] != self.rti11_result.request.candidate_id
                or self.policy_snapshot.scope_identity["chain_id"] != self.rti11_result.request.target.chain_id
                or self.policy_snapshot.scope_identity["token_identity"] != self.rti11_result.request.target.token_mint):
                raise ValueError("policy subject does not match RTI-11")

    @property
    def input_digests(self) -> dict[str, str]:
        return {
            "decision_ruleset": self.decision_ruleset.digest,
            "decision_time": _digest(self.decision_time),
            "policy_snapshot": self.policy_snapshot.digest,
            "execution_observation": self.execution_observation.observation_digest,
            "simulation_configuration": self.simulation_configuration.configuration_digest,
            "initial_paper_state": self.initial_paper_state.state_digest,
            "replay_identity": _digest(self.replay_identity.canonical_representation),
            "fill_instruction": self.fill_instruction.digest,
            "lifecycle_evidence": self.lifecycle_evidence.digest,
        }


@dataclass(frozen=True)
class P01Osc01Result:
    request: P01Osc01Request
    outcome: OneShotPaperOutcome
    reason_codes: tuple[str, ...]
    terminal_stage: str
    rti12_result: P01Rti12ContinuationResult | None = None
    rti13_result: P01Rti13DecisionContinuationResult | None = None
    rti14_result: P01Rti14RiskCapitalContinuationResult | None = None
    rti15_result: P01Rti15PaperAdmissionContinuationResult | None = None
    rti16_result: P01Rti16ControlledPaperLifecycleContinuationResult | None = None
    contract_version: str = P01_OSC_01_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        if type(self.request) is not P01Osc01Request:
            raise ValueError("invalid OSC-01 request")
        self.request.__post_init__()
        if self.contract_version != P01_OSC_01_CONTRACT_VERSION or type(self.outcome) is not OneShotPaperOutcome:
            raise ValueError("invalid OSC-01 result contract")
        if type(self.reason_codes) is not tuple or any(type(r) is not str or not r for r in self.reason_codes):
            raise ValueError("invalid OSC-01 reasons")
        values = self.stage_results
        if any(value is not None for value in (
            self.rti12_result, self.rti13_result, self.rti14_result,
            self.rti15_result, self.rti16_result,
        )[len(values) - 1:]):
            raise ValueError("non-prefix stage results")
        if self.terminal_stage not in _STAGES or self.terminal_stage != _STAGES[len(values) - 1]:
            raise ValueError("invalid terminal stage")
        if any(value is None for value in values):
            raise ValueError("non-prefix stage results")
        for index, value in enumerate(values):
            if not _canonical(value, _TYPES[index]):
                raise ValueError("invalid canonical owner result")
            if index and value.upstream_result is not values[index - 1]:
                raise ValueError("owner result lost exact predecessor")
            if index and not _links(value, index, self.request):
                raise ValueError("owner result lost explicit caller input")
        terminal = values[-1]
        if self.outcome is OneShotPaperOutcome.LIFECYCLE_RETURNED:
            if len(values) != 6 or terminal.outcome is not Rti15ToControlledLifecycleOutcome.LIFECYCLE_MATERIALIZED or self.reason_codes:
                raise ValueError("invalid returned lifecycle")
        elif self.outcome is OneShotPaperOutcome.UPSTREAM_STOPPED:
            can_continue = (
                terminal.outcome is MarketToOpportunityCompositionOutcome.COMPOSED if len(values) == 1 else
                terminal.outcome is OpportunityContextContinuationOutcome.CONTEXT_MATERIALIZED if len(values) == 2 else
                terminal.outcome is OpportunityContextToDecisionOutcome.DECISION_MATERIALIZED if len(values) == 3 else
                (terminal.outcome is DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED
                 and terminal.authorization_result.status is AuthorizationStatus.APPROVED) if len(values) == 4 else
                terminal.outcome is RiskCapitalToPaperAdmissionOutcome.ADMISSION_MATERIALIZED if len(values) == 5 else
                terminal.outcome is Rti15ToControlledLifecycleOutcome.LIFECYCLE_MATERIALIZED
            )
            if can_continue or not self.reason_codes:
                raise ValueError("missing upstream reason")
        elif self.reason_codes != (f"{_STAGES[len(values)]}_UNAVAILABLE",) or len(values) == 6:
            raise ValueError("invalid unavailable stage")
        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("OSC-01 result digest mismatch")
        object.__setattr__(self, "result_digest", expected)

    @property
    def invocation_id(self) -> str:
        return self.request.invocation_id

    @property
    def rti11_result(self) -> P01Rti11CompositionResult:
        return self.request.rti11_result

    @property
    def stage_results(self) -> tuple[Any, ...]:
        values = (self.rti11_result, self.rti12_result, self.rti13_result,
                  self.rti14_result, self.rti15_result, self.rti16_result)
        return values[:next((index for index, value in enumerate(values) if value is None), 6)]

    @property
    def lifecycle_result(self) -> Any:
        return self.rti16_result.lifecycle_result if self.rti16_result is not None else None

    def _without_digest(self) -> dict[str, Any]:
        return {"contract_version": self.contract_version, "invocation_id": self.invocation_id,
                "outcome": self.outcome.value, "reason_codes": self.reason_codes,
                "terminal_stage": self.terminal_stage, "input_digests": self.request.input_digests,
                "stage_results": tuple({"stage": _STAGES[i], "contract_version": v.contract_version,
                                        "outcome": v.outcome.value, "digest": v.digest}
                                       for i, v in enumerate(self.stage_results))}

    @property
    def canonical_representation(self) -> dict[str, Any]:
        return {**self._without_digest(), "result_digest": self.result_digest}

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


class OneShotControlledPaperCaller:
    """A stateless invocation coordinator; injected owners are test seams only."""

    def __init__(self, *, rti12: Any = None, rti13: Any = None, rti14: Any = None,
                 rti15: Any = None, rti16: Any = None) -> None:
        self._owners = (rti12 if rti12 is not None else P05OpportunityContextContinuationService(),
                        rti13 if rti13 is not None else OpportunityContextToDecisionContinuationService(),
                        rti14 if rti14 is not None else DecisionToRiskCapitalContinuationService(),
                        rti15 if rti15 is not None else RiskCapitalToPaperAdmissionContinuationService(),
                        rti16 if rti16 is not None else Rti15ToControlledPaperLifecycleContinuationService())
        for owner, method in zip(self._owners, ("continue_to_context", "continue_to_decision",
                                               "continue_to_risk_capital", "continue_to_paper_admission",
                                               "continue_to_controlled_paper_lifecycle")):
            if not callable(getattr(owner, method, None)):
                raise ValueError("invalid OSC-01 owner seam")

    def run(self, request: P01Osc01Request) -> P01Osc01Result:
        if type(request) is not P01Osc01Request:
            raise ValueError("invalid OSC-01 request")
        request.__post_init__()
        values: list[Any] = [request.rti11_result]

        def result(outcome: OneShotPaperOutcome, reasons: tuple[str, ...]) -> P01Osc01Result:
            return P01Osc01Result(request=request, outcome=outcome, reason_codes=reasons,
                                  terminal_stage=_STAGES[len(values) - 1],
                                  **{f"rti{i}_result": values[i - 11] for i in range(12, 11 + len(values))})

        predicates = (
            lambda v: v.outcome is MarketToOpportunityCompositionOutcome.COMPOSED,
            lambda v: v.outcome is OpportunityContextContinuationOutcome.CONTEXT_MATERIALIZED,
            lambda v: v.outcome is OpportunityContextToDecisionOutcome.DECISION_MATERIALIZED,
            lambda v: (v.outcome is DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED
                       and v.authorization_result is not None
                       and v.authorization_result.status is AuthorizationStatus.APPROVED),
            lambda v: v.outcome is RiskCapitalToPaperAdmissionOutcome.ADMISSION_MATERIALIZED,
        )
        calls = (
            ("continue_to_context", (request.rti11_result,), {}),
            ("continue_to_decision", (), {"decision_ruleset": request.decision_ruleset,
                                           "decision_time": request.decision_time}),
            ("continue_to_risk_capital", (), {"policy_snapshot": request.policy_snapshot}),
            ("continue_to_paper_admission", (), {"execution_observation": request.execution_observation,
                "simulation_configuration": request.simulation_configuration,
                "initial_paper_state": request.initial_paper_state, "replay_identity": request.replay_identity}),
            ("continue_to_controlled_paper_lifecycle", (), {"fill_instruction": request.fill_instruction,
                                                               "lifecycle_evidence": request.lifecycle_evidence}),
        )
        for index, (owner, (method, args, kwargs)) in enumerate(zip(self._owners, calls)):
            if not predicates[index](values[-1]):
                authorization = getattr(values[-1], "authorization_result", None)
                reasons = (values[-1].reason_codes or
                           (authorization.reason_codes if authorization is not None else ()) or
                           ("AUTHORIZATION_REJECTED",))
                return result(OneShotPaperOutcome.UPSTREAM_STOPPED, tuple(reasons))
            try:
                value = getattr(owner, method)(*(args if index == 0 else (values[-1],)), **kwargs)
            except ValueError:
                raise ValueError(f"{_STAGES[index + 1]} validation failed") from None
            except Exception:
                return result(OneShotPaperOutcome.OWNER_UNAVAILABLE, (f"{_STAGES[index + 1]}_UNAVAILABLE",))
            if (not _canonical(value, _TYPES[index + 1])
                or value.upstream_result is not values[-1]
                or not _links(value, index + 1, request)):
                return result(OneShotPaperOutcome.OWNER_UNAVAILABLE, (f"{_STAGES[index + 1]}_UNAVAILABLE",))
            values.append(value)
        if values[-1].outcome is not Rti15ToControlledLifecycleOutcome.LIFECYCLE_MATERIALIZED:
            return result(OneShotPaperOutcome.UPSTREAM_STOPPED, values[-1].reason_codes)
        return result(OneShotPaperOutcome.LIFECYCLE_RETURNED, ())


def _links(value: Any, index: int, request: P01Osc01Request) -> bool:
    if index == 1:
        return True
    if index == 2:
        return (value.decision_ruleset is request.decision_ruleset and
                value.decision_time == request.decision_time.astimezone(timezone.utc))
    if index == 3:
        return value.policy_snapshot is request.policy_snapshot
    if index == 4:
        return (value.execution_observation is request.execution_observation and
                value.simulation_configuration is request.simulation_configuration and
                value.initial_paper_state is request.initial_paper_state and
                value.replay_identity is request.replay_identity)
    return value.fill_instruction is request.fill_instruction and value.lifecycle_evidence is request.lifecycle_evidence
