"""Immutable, deterministic P08-T01 outcome-learning observation boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.decision import DecisionIntent
from core.execution import (
    P07_T07_CONTRACT_VERSION,
    PaperSimulationInput,
    PaperSimulationResult,
    PaperSimulationResultHistory,
)


P08_T01_CONTRACT_VERSION = "p08-t01-v1"
P08_T01_EVALUATOR_VERSION = "p08-t01-outcome-observation-v1"
_DIGEST_LENGTH = 64


@dataclass(frozen=True)
class OutcomeLearningObservation:
    """One linked, immutable decision-to-paper-outcome observation."""

    decision_intent: DecisionIntent
    simulation_input: PaperSimulationInput
    paper_result: PaperSimulationResult
    history_results: tuple[PaperSimulationResult, ...]
    history_digest: str
    contract_version: str = P08_T01_CONTRACT_VERSION
    evaluator_version: str = P08_T01_EVALUATOR_VERSION

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_text(self.evaluator_version, "evaluator_version")
        if self.contract_version != P08_T01_CONTRACT_VERSION:
            raise ValueError("unsupported P08-T01 contract version")
        if self.evaluator_version != P08_T01_EVALUATOR_VERSION:
            raise ValueError("unsupported P08-T01 evaluator version")

        _validate_decision_intent(self.decision_intent)
        _validate_simulation_input(self.simulation_input)
        _validate_paper_result(self.paper_result)
        history_results = tuple(self.history_results)
        if not history_results:
            raise ValueError("history_results must contain at least one result")
        for result in history_results:
            _validate_paper_result(result)
        object.__setattr__(self, "history_results", history_results)
        _require_digest(self.history_digest, "history_digest")
        if self.history_digest != _history_digest(history_results):
            raise ValueError("history digest does not match canonical history")
        if self.paper_result.digest not in {result.digest for result in history_results}:
            raise ValueError("paper result is not retained in P07-T07 history")

        if (
            self.simulation_input.decision_intent.decision_intent_digest
            != self.decision_intent.digest
        ):
            raise ValueError("simulation input does not link to DecisionIntent")
        if self.paper_result.input_digest != self.simulation_input.digest:
            raise ValueError("paper result does not link to simulation input")

    @property
    def candidate_id(self) -> str:
        return self.decision_intent.candidate_id

    @property
    def chain_id(self) -> str:
        return self.decision_intent.chain_id

    @property
    def token_identity(self) -> str:
        return self.decision_intent.token_identity

    @property
    def decision_intent_digest(self) -> str:
        return self.decision_intent.digest

    @property
    def simulation_input_digest(self) -> str:
        return self.simulation_input.digest

    @property
    def paper_result_digest(self) -> str:
        return self.paper_result.digest

    @property
    def p07_t07_history_digest(self) -> str:
        return self.history_digest

    @property
    def decision_time(self) -> datetime:
        return self.decision_intent.decision_time

    @property
    def simulation_reference_time(self) -> datetime:
        return self.simulation_input.simulation_reference_time

    @property
    def outcome_status(self) -> str:
        return self.paper_result.status

    @property
    def reconciliation_status(self) -> str:
        return self.paper_result.reconciliation_status

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "decision_intent": self.decision_intent.canonical_representation,
                "simulation_input": self.simulation_input.canonical_representation,
                "paper_result": self.paper_result.canonical_dict(),
                "history_results": tuple(
                    result.canonical_dict() for result in self.history_results
                ),
                "history_digest": self.history_digest,
                "contract_version": self.contract_version,
                "evaluator_version": self.evaluator_version,
            }
        )

    @property
    def deterministic_representation(self) -> Mapping[str, Any]:
        return self.canonical_representation

    @property
    def representation_digest(self) -> str:
        return _digest(self.canonical_representation)

    @property
    def digest(self) -> str:
        return self.representation_digest


def create_outcome_learning_observation(
    decision_intent: DecisionIntent,
    simulation_input: PaperSimulationInput,
    paper_result: PaperSimulationResult,
    history: PaperSimulationResultHistory,
) -> OutcomeLearningObservation:
    """Create one read-only observation without interpreting its outcome."""

    if not isinstance(history, PaperSimulationResultHistory):
        raise ValueError("history must be a PaperSimulationResultHistory")
    return OutcomeLearningObservation(
        decision_intent=decision_intent,
        simulation_input=simulation_input,
        paper_result=paper_result,
        history_results=history.retrieve(),
        history_digest=history.digest,
    )


observe_outcome = create_outcome_learning_observation


def _validate_decision_intent(value: DecisionIntent) -> None:
    if not isinstance(value, DecisionIntent):
        raise ValueError("decision_intent must be a DecisionIntent")
    try:
        validated = DecisionIntent(
            context=value.context,
            action=value.action,
            entry_posture=value.entry_posture,
            expected_edge_assumptions=value.expected_edge_assumptions,
            uncertainty=value.uncertainty,
            invalidation_conditions=value.invalidation_conditions,
            confidence=value.confidence,
            decision_time=value.decision_time,
            ruleset_version=value.ruleset_version,
            evaluator_version=value.evaluator_version,
            contract_version=value.contract_version,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("DecisionIntent is invalid") from error
    if (
        validated != value
        or validated.canonical_representation != value.deterministic_representation
        or validated.digest != value.digest
    ):
        raise ValueError("DecisionIntent is tampered or non-canonical")


def _validate_simulation_input(value: PaperSimulationInput) -> None:
    if not isinstance(value, PaperSimulationInput):
        raise ValueError("simulation_input must be a PaperSimulationInput")
    try:
        validated = PaperSimulationInput(
            decision_intent=value.decision_intent,
            authorization_observation=value.authorization_observation,
            execution_observation=value.execution_observation,
            simulation_configuration=value.simulation_configuration,
            initial_paper_state=value.initial_paper_state,
            simulation_reference_time=value.simulation_reference_time,
            replay_identity=value.replay_identity,
            contract_version=value.contract_version,
            input_digest=value.input_digest,
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("PaperSimulationInput is invalid") from error
    if (
        validated != value
        or validated.canonical_representation != value.deterministic_representation
        or validated.digest != value.digest
    ):
        raise ValueError("PaperSimulationInput is tampered or non-canonical")


def _validate_paper_result(value: PaperSimulationResult) -> None:
    if not isinstance(value, PaperSimulationResult):
        raise ValueError("paper_result must be a PaperSimulationResult")
    try:
        fields = value.canonical_dict()
        validated = PaperSimulationResult(
            input_digest=fields["input_digest"],
            fill_digest=fields["fill_digest"],
            transition_digest=fields["transition_digest"],
            ledger_digest=fields["ledger_digest"],
            reconciliation_digest=fields["reconciliation_digest"],
            status=fields["status"],
            filled_quantity=fields["filled_quantity"],
            unfilled_quantity=fields["unfilled_quantity"],
            position_state_digest=fields["position_state_digest"],
            reconciliation_status=fields["reconciliation_status"],
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError("PaperSimulationResult is invalid") from error
    if validated != value or validated.digest != value.digest:
        raise ValueError("PaperSimulationResult is tampered or non-canonical")


def _history_digest(results: tuple[PaperSimulationResult, ...]) -> str:
    return _digest(
        {
            "contract_version": P07_T07_CONTRACT_VERSION,
            "results": tuple(result.canonical_dict() for result in results),
        }
    )


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")


def _require_digest(value: Any, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != _DIGEST_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


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
    if isinstance(value, datetime):
        return _to_utc(value, "timestamp").isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key]) for key in sorted(value, key=str)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ValueError(f"{type(value).__name__} cannot be deterministically serialized")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


def _to_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = [
    "OutcomeLearningObservation",
    "P08_T01_CONTRACT_VERSION",
    "P08_T01_EVALUATOR_VERSION",
    "create_outcome_learning_observation",
    "observe_outcome",
]