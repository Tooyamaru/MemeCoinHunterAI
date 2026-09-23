"""Bounded P01-RTI-15 Risk/Capital-to-P07 admission continuation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Any, Callable, Mapping

from backend.application.decision_to_risk_capital_continuation import (
    P01_RTI_14_CONTRACT_VERSION,
    DecisionToRiskCapitalOutcome,
    P01Rti14RiskCapitalContinuationResult,
)
from core.execution import (
    AuthorizationObservation,
    ExecutionObservation,
    InitialPaperStateIdentity,
    P07_T01_CONTRACT_VERSION,
    PaperSimulationInput,
    ReplayIdentity,
    SimulationConfigurationIdentity,
)
from core.risk.paper_risk_capital_authorization import AuthorizationStatus


P01_RTI_15_CONTRACT_VERSION = "p01-rti-15-v1"


class RiskCapitalToPaperAdmissionOutcome(StrEnum):
    ADMISSION_MATERIALIZED = "ADMISSION_MATERIALIZED"
    UPSTREAM_NOT_AUTHORIZED = "UPSTREAM_NOT_AUTHORIZED"
    ADMISSION_UNAVAILABLE = "ADMISSION_UNAVAILABLE"


@dataclass(frozen=True)
class P01Rti15PaperAdmissionContinuationResult:
    upstream_result: P01Rti14RiskCapitalContinuationResult
    execution_observation: ExecutionObservation
    simulation_configuration: SimulationConfigurationIdentity
    initial_paper_state: InitialPaperStateIdentity
    replay_identity: ReplayIdentity
    outcome: RiskCapitalToPaperAdmissionOutcome | str
    reason_codes: tuple[str, ...]
    authorization_observation: AuthorizationObservation | None = None
    paper_simulation_input: PaperSimulationInput | None = None
    contract_version: str = P01_RTI_15_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        _validate_inputs(
            self.upstream_result,
            self.execution_observation,
            self.simulation_configuration,
            self.initial_paper_state,
            self.replay_identity,
        )
        try:
            outcome = RiskCapitalToPaperAdmissionOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported RTI-15 outcome") from error
        object.__setattr__(self, "outcome", outcome)
        if self.contract_version != P01_RTI_15_CONTRACT_VERSION:
            raise ValueError("unsupported RTI-15 contract_version")
        reasons = _reasons(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)
        self._validate_shape()
        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("result_digest does not match RTI-15 result")
        object.__setattr__(self, "result_digest", expected)

    def _validate_shape(self) -> None:
        authorization = self.upstream_result.authorization_result
        if self.outcome is RiskCapitalToPaperAdmissionOutcome.ADMISSION_MATERIALIZED:
            if (
                self.upstream_result.outcome
                is not DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED
                or authorization is None
                or authorization.status is not AuthorizationStatus.APPROVED
                or self.reason_codes
                or not _valid_observation(self.authorization_observation, authorization)
                or not _valid_input(
                    self.paper_simulation_input,
                    self.upstream_result,
                    self.authorization_observation,
                    self.execution_observation,
                    self.simulation_configuration,
                    self.initial_paper_state,
                    self.replay_identity,
                )
            ):
                raise ValueError("ADMISSION_MATERIALIZED result is invalid")
        elif self.outcome is RiskCapitalToPaperAdmissionOutcome.UPSTREAM_NOT_AUTHORIZED:
            if _approved(self.upstream_result):
                raise ValueError("UPSTREAM_NOT_AUTHORIZED cannot contain approval")
            if self.reason_codes != ("UPSTREAM_NOT_AUTHORIZED",):
                raise ValueError("UPSTREAM_NOT_AUTHORIZED reason is required")
            if self.authorization_observation is not None or self.paper_simulation_input is not None:
                raise ValueError("non-authorized result cannot contain P07 material")
        else:
            if not _approved(self.upstream_result):
                raise ValueError("ADMISSION_UNAVAILABLE requires approved upstream")
            if self.reason_codes not in (
                ("AUTHORIZATION_OBSERVATION_UNAVAILABLE",),
                ("AUTHORIZATION_OBSERVATION_INVALID_RESULT",),
                ("P07_ADMISSION_UNAVAILABLE",),
                ("P07_ADMISSION_INVALID_RESULT",),
            ):
                raise ValueError("ADMISSION_UNAVAILABLE reason is invalid")
            if self.paper_simulation_input is not None:
                raise ValueError("unavailable result cannot contain P07 input")

    def _without_digest(self) -> Mapping[str, Any]:
        authorization = self.upstream_result.authorization_result
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "rti14_contract_version": self.upstream_result.contract_version,
            "rti14_outcome": self.upstream_result.outcome.value,
            "rti14_result_digest": self.upstream_result.result_digest,
            "authority_status": authorization.status.value if authorization else None,
            "authority_result_digest": authorization.digest if authorization else None,
            "execution_observation_digest": self.execution_observation.observation_digest,
            "simulation_configuration_digest": self.simulation_configuration.configuration_digest,
            "initial_paper_state_digest": self.initial_paper_state.state_digest,
            "replay_identity_digest": _digest(self.replay_identity.canonical_representation),
            "authorization_observation_digest": (
                self.authorization_observation.observation_digest
                if self.authorization_observation else None
            ),
            "p07_contract_version": (
                self.paper_simulation_input.contract_version
                if self.paper_simulation_input else None
            ),
            "paper_simulation_input_digest": (
                self.paper_simulation_input.digest if self.paper_simulation_input else None
            ),
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {**self._without_digest(), "result_digest": self.result_digest}

    deterministic_representation = property(lambda self: self.canonical_representation)

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


ObservationFactory = Callable[[Any], AuthorizationObservation]
InputFactory = Callable[..., PaperSimulationInput]


class RiskCapitalToPaperAdmissionContinuationService:
    def __init__(
        self,
        *,
        observation_factory: ObservationFactory = AuthorizationObservation.from_risk_capital_result,
        input_factory: InputFactory = PaperSimulationInput,
    ) -> None:
        if not callable(observation_factory) or not callable(input_factory):
            raise ValueError("RTI-15 delegates must be callable")
        self._observation_factory = observation_factory
        self._input_factory = input_factory

    def continue_to_paper_admission(
        self,
        upstream_result: P01Rti14RiskCapitalContinuationResult,
        execution_observation: ExecutionObservation,
        simulation_configuration: SimulationConfigurationIdentity,
        initial_paper_state: InitialPaperStateIdentity,
        replay_identity: ReplayIdentity,
    ) -> P01Rti15PaperAdmissionContinuationResult:
        _validate_inputs(
            upstream_result,
            execution_observation,
            simulation_configuration,
            initial_paper_state,
            replay_identity,
        )
        common = dict(
            upstream_result=upstream_result,
            execution_observation=execution_observation,
            simulation_configuration=simulation_configuration,
            initial_paper_state=initial_paper_state,
            replay_identity=replay_identity,
        )
        if not _approved(upstream_result):
            return P01Rti15PaperAdmissionContinuationResult(
                **common,
                outcome=RiskCapitalToPaperAdmissionOutcome.UPSTREAM_NOT_AUTHORIZED,
                reason_codes=("UPSTREAM_NOT_AUTHORIZED",),
            )
        authorization = upstream_result.authorization_result
        decision = upstream_result.upstream_result.decision_intent
        assert authorization is not None and decision is not None
        try:
            observation = self._observation_factory(authorization)
        except ValueError:
            raise ValueError("Risk/Capital observation validation failed") from None
        except Exception:
            return P01Rti15PaperAdmissionContinuationResult(
                **common,
                outcome=RiskCapitalToPaperAdmissionOutcome.ADMISSION_UNAVAILABLE,
                reason_codes=("AUTHORIZATION_OBSERVATION_UNAVAILABLE",),
            )
        if not _valid_observation(observation, authorization):
            return P01Rti15PaperAdmissionContinuationResult(
                **common,
                outcome=RiskCapitalToPaperAdmissionOutcome.ADMISSION_UNAVAILABLE,
                reason_codes=("AUTHORIZATION_OBSERVATION_INVALID_RESULT",),
            )
        try:
            paper_input = self._input_factory(
                decision_intent=decision,
                authorization_observation=observation,
                execution_observation=execution_observation,
                simulation_configuration=simulation_configuration,
                initial_paper_state=initial_paper_state,
                simulation_reference_time=authorization.simulation_reference_time,
                replay_identity=replay_identity,
                contract_version=P07_T01_CONTRACT_VERSION,
            )
        except ValueError:
            raise ValueError("P07-T01 admission validation failed") from None
        except Exception:
            return P01Rti15PaperAdmissionContinuationResult(
                **common,
                outcome=RiskCapitalToPaperAdmissionOutcome.ADMISSION_UNAVAILABLE,
                reason_codes=("P07_ADMISSION_UNAVAILABLE",),
                authorization_observation=observation,
            )
        if not _valid_input(
            paper_input,
            upstream_result,
            observation,
            execution_observation,
            simulation_configuration,
            initial_paper_state,
            replay_identity,
        ):
            return P01Rti15PaperAdmissionContinuationResult(
                **common,
                outcome=RiskCapitalToPaperAdmissionOutcome.ADMISSION_UNAVAILABLE,
                reason_codes=("P07_ADMISSION_INVALID_RESULT",),
                authorization_observation=observation,
            )
        return P01Rti15PaperAdmissionContinuationResult(
            **common,
            outcome=RiskCapitalToPaperAdmissionOutcome.ADMISSION_MATERIALIZED,
            reason_codes=(),
            authorization_observation=observation,
            paper_simulation_input=paper_input,
        )

    materialize = continue_to_paper_admission


def _validate_inputs(upstream: Any, execution: Any, configuration: Any, state: Any, replay: Any) -> None:
    if not isinstance(upstream, P01Rti14RiskCapitalContinuationResult):
        raise ValueError("upstream_result must be a P01Rti14RiskCapitalContinuationResult")
    if upstream.contract_version != P01_RTI_14_CONTRACT_VERSION:
        raise ValueError("unsupported RTI-14 contract version")
    try:
        rebuilt = P01Rti14RiskCapitalContinuationResult(
            upstream_result=upstream.upstream_result,
            policy_snapshot=upstream.policy_snapshot,
            outcome=upstream.outcome,
            reason_codes=upstream.reason_codes,
            authorization_result=upstream.authorization_result,
            contract_version=upstream.contract_version,
            result_digest=upstream.result_digest,
        )
    except (AttributeError, TypeError, ValueError):
        raise ValueError("upstream_result is not canonical") from None
    if rebuilt != upstream or rebuilt.digest != upstream.digest:
        raise ValueError("upstream_result is not canonical")
    for value, expected, name in (
        (execution, ExecutionObservation, "execution_observation"),
        (configuration, SimulationConfigurationIdentity, "simulation_configuration"),
        (state, InitialPaperStateIdentity, "initial_paper_state"),
        (replay, ReplayIdentity, "replay_identity"),
    ):
        if not isinstance(value, expected):
            raise ValueError(f"{name} must be a {expected.__name__}")
    try:
        rebuilt_execution = ExecutionObservation(
            observation_id=execution.observation_id,
            subject_identity=execution.subject_identity,
            observation_time=execution.observation_time,
            availability_time=execution.availability_time,
            quality=execution.quality,
            market_context_digest=execution.market_context_digest,
            quote_context_digest=execution.quote_context_digest,
            liquidity_context_digest=execution.liquidity_context_digest,
            sellability_status=execution.sellability_status,
            source_contract_version=execution.source_contract_version,
            source_provenance=execution.source_provenance,
            observation_replay_key=execution.observation_replay_key,
            observation_digest=execution.observation_digest,
        )
        rebuilt_configuration = SimulationConfigurationIdentity(
            configuration_id=configuration.configuration_id,
            contract_version=configuration.contract_version,
            simulation_version=configuration.simulation_version,
            fill_model_version=configuration.fill_model_version,
            friction_model_version=configuration.friction_model_version,
            failure_policy_version=configuration.failure_policy_version,
            seed_policy_version=configuration.seed_policy_version,
            configuration_provenance=configuration.configuration_provenance,
            configuration_digest=configuration.configuration_digest,
        )
        rebuilt_state = InitialPaperStateIdentity(
            state_id=state.state_id,
            state_version=state.state_version,
            portfolio_scope=state.portfolio_scope,
            position_state_digest=state.position_state_digest,
            exposure_state_digest=state.exposure_state_digest,
            as_of_time=state.as_of_time,
            state_quality=state.state_quality,
            state_provenance=state.state_provenance,
            state_digest=state.state_digest,
        )
        rebuilt_replay = ReplayIdentity(
            replay_id=replay.replay_id,
            replay_schema_version=replay.replay_schema_version,
            replay_seed_identity=replay.replay_seed_identity,
            parent_replay_id=replay.parent_replay_id,
            replay_scope=replay.replay_scope,
        )
    except (AttributeError, TypeError, ValueError):
        raise ValueError("explicit P07 admission input is not canonical") from None
    if (
        rebuilt_execution != execution
        or rebuilt_configuration != configuration
        or rebuilt_state != state
        or rebuilt_replay != replay
    ):
        raise ValueError("explicit P07 admission input is not canonical")


def _approved(value: P01Rti14RiskCapitalContinuationResult) -> bool:
    return (
        value.outcome is DecisionToRiskCapitalOutcome.AUTHORIZATION_MATERIALIZED
        and value.authorization_result is not None
        and value.authorization_result.status is AuthorizationStatus.APPROVED
    )


def _valid_observation(value: Any, authorization: Any) -> bool:
    try:
        reference = value.authorization_reference
        return (
            isinstance(value, AuthorizationObservation)
            and value.status.value == "PASS"
            and reference is not None
            and reference.authorization_id == authorization.authorization_id
            and reference.authorization_digest == authorization.digest
            and reference.decision_intent_digest == authorization.decision_intent_digest
            and reference.context_digest == authorization.context_digest
            and reference.authorization_effect == authorization.authorization_effect
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _valid_input(value: Any, upstream: Any, observation: Any, execution: Any, configuration: Any, state: Any, replay: Any) -> bool:
    decision = upstream.upstream_result.decision_intent
    authorization = upstream.authorization_result
    try:
        return (
            isinstance(value, PaperSimulationInput)
            and value.contract_version == P07_T01_CONTRACT_VERSION
            and value.decision_intent.intent is decision
            and value.authorization_observation is observation
            and value.execution_observation is execution
            and value.simulation_configuration is configuration
            and value.initial_paper_state is state
            and value.replay_identity is replay
            and value.simulation_reference_time == authorization.simulation_reference_time
            and value.digest == value.input_digest
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _reasons(value: Any) -> tuple[str, ...]:
    if not isinstance(value, tuple) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError("reason_codes must be canonical tuple values")
    if len(value) != len(set(value)):
        raise ValueError("reason_codes must not contain duplicates")
    return value


def _digest(value: Any) -> str:
    encoded = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _canonical(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    raise ValueError(f"unsupported canonical value: {type(value).__name__}")


__all__ = [
    "P01_RTI_15_CONTRACT_VERSION",
    "RiskCapitalToPaperAdmissionOutcome",
    "P01Rti15PaperAdmissionContinuationResult",
    "RiskCapitalToPaperAdmissionContinuationService",
]
