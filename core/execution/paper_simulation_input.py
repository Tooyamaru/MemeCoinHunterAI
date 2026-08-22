"""Immutable P07-T01 paper-simulation input and provenance contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.decision import (
    DecisionAction,
    DecisionIntent,
    EntryPosture,
    P06_T01_CONTRACT_VERSION,
    P06_T01_EVALUATOR_VERSION,
    P06_T01_RULESET_VERSION,
    P06_T02_EVALUATOR_VERSION,
    P06_T02_RULESET_VERSION,
)


P07_T01_CONTRACT_VERSION = "p07-t01-v1"
NOT_APPLICABLE = "NOT_APPLICABLE"
_DIGEST_LENGTH = 64


class ObservationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_REQUIRED = "NOT_REQUIRED"


class ObservationQuality(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    INVALID = "INVALID"


@dataclass(frozen=True)
class P06DecisionIntentIdentity:
    """Verified identity/provenance envelope for one immutable P06 intent."""

    intent: DecisionIntent
    decision_intent_digest: str | None = None
    context_digest: str | None = None
    candidate_id: str | None = None
    chain_id: str | None = None
    token_identity: str | None = None
    action: DecisionAction | str | None = None
    entry_posture: EntryPosture | str | None = None
    decision_time: datetime | None = None
    p06_t01_contract_version: str | None = None
    p06_t01_ruleset_version: str | None = None
    p06_t01_evaluator_version: str | None = None
    p06_t02_ruleset_version: str | None = None
    p06_t02_evaluator_version: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.intent, DecisionIntent):
            raise ValueError("intent must be a DecisionIntent")
        intent = self.intent
        values = {
            "decision_intent_digest": intent.digest,
            "context_digest": intent.context_digest,
            "candidate_id": intent.candidate_id,
            "chain_id": intent.chain_id,
            "token_identity": intent.token_identity,
            "action": intent.action,
            "entry_posture": intent.entry_posture,
            "decision_time": _to_utc(intent.decision_time, "decision_time"),
            "p06_t01_contract_version": intent.contract_version,
            "p06_t01_ruleset_version": P06_T01_RULESET_VERSION,
            "p06_t01_evaluator_version": P06_T01_EVALUATOR_VERSION,
            "p06_t02_ruleset_version": (
                intent.ruleset_version
                if intent.ruleset_version == P06_T02_RULESET_VERSION
                else NOT_APPLICABLE
            ),
            "p06_t02_evaluator_version": (
                intent.evaluator_version
                if intent.evaluator_version == P06_T02_EVALUATOR_VERSION
                else NOT_APPLICABLE
            ),
        }
        for name, expected in values.items():
            supplied = getattr(self, name)
            if supplied is not None and _canonicalize(supplied) != _canonicalize(expected):
                raise ValueError(f"{name} does not match DecisionIntent")
            object.__setattr__(self, name, expected)
        object.__setattr__(self, "decision_time", values["decision_time"])

    @classmethod
    def from_intent(cls, intent: DecisionIntent) -> "P06DecisionIntentIdentity":
        return cls(intent)

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "decision_intent_digest": self.decision_intent_digest,
                "context_digest": self.context_digest,
                "candidate_id": self.candidate_id,
                "chain_id": self.chain_id,
                "token_identity": self.token_identity,
                "action": self.action.value,
                "entry_posture": self.entry_posture.value,
                "decision_time": _timestamp_text(self.decision_time),
                "p06_t01_contract_version": self.p06_t01_contract_version,
                "p06_t01_ruleset_version": self.p06_t01_ruleset_version,
                "p06_t01_evaluator_version": self.p06_t01_evaluator_version,
                "p06_t02_ruleset_version": self.p06_t02_ruleset_version,
                "p06_t02_evaluator_version": self.p06_t02_evaluator_version,
            }
        )

    deterministic_representation = property(lambda self: self.canonical_representation)


@dataclass(frozen=True)
class AuthorizationObservation:
    observation_id: str
    status: ObservationStatus | str
    scope_identity: Mapping[str, Any]
    observed_at: datetime
    valid_from: datetime
    valid_until: datetime | None
    contract_version: str
    risk_governor_version: str
    capital_authorization_version: str
    reason_codes: tuple[str, ...] = ()
    unknown_reasons: tuple[str, ...] = ()
    observation_digest: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.observation_id, "observation_id")
        _require_enum(self.status, ObservationStatus, "status")
        object.__setattr__(self, "status", ObservationStatus(self.status))
        object.__setattr__(self, "scope_identity", _freeze_mapping(self.scope_identity, "scope_identity"))
        object.__setattr__(self, "observed_at", _to_utc(self.observed_at, "observed_at"))
        object.__setattr__(self, "valid_from", _to_utc(self.valid_from, "valid_from"))
        if self.valid_until is not None:
            object.__setattr__(self, "valid_until", _to_utc(self.valid_until, "valid_until"))
        if self.status is ObservationStatus.PASS and self.valid_until is None:
            raise ValueError("PASS authorization requires valid_until")
        if self.valid_until is not None and self.valid_until < self.valid_from:
            raise ValueError("valid_until cannot precede valid_from")
        _require_text(self.contract_version, "contract_version")
        _require_text(self.risk_governor_version, "risk_governor_version")
        _require_text(self.capital_authorization_version, "capital_authorization_version")
        object.__setattr__(self, "reason_codes", _texts(self.reason_codes, "reason_codes"))
        object.__setattr__(self, "unknown_reasons", _texts(self.unknown_reasons, "unknown_reasons"))
        if self.status is ObservationStatus.UNKNOWN and not self.unknown_reasons:
            raise ValueError("UNKNOWN authorization requires unknown_reasons")
        _set_or_verify_digest(self, "observation_digest", self._canonical_without_digest())

    def _canonical_without_digest(self) -> Mapping[str, Any]:
        return {
            "observation_id": self.observation_id,
            "status": self.status.value,
            "scope_identity": self.scope_identity,
            "observed_at": self.observed_at,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "contract_version": self.contract_version,
            "risk_governor_version": self.risk_governor_version,
            "capital_authorization_version": self.capital_authorization_version,
            "reason_codes": self.reason_codes,
            "unknown_reasons": self.unknown_reasons,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._canonical_without_digest(), "observation_digest": self.observation_digest})

    deterministic_representation = property(lambda self: self.canonical_representation)


@dataclass(frozen=True)
class ExecutionObservation:
    observation_id: str
    subject_identity: Mapping[str, Any]
    observation_time: datetime
    availability_time: datetime
    quality: ObservationQuality | str
    market_context_digest: str | None
    quote_context_digest: str | None
    liquidity_context_digest: str | None
    sellability_status: ObservationStatus | str
    source_contract_version: str
    source_provenance: Mapping[str, Any]
    observation_replay_key: str
    observation_digest: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.observation_id, "observation_id")
        object.__setattr__(self, "subject_identity", _freeze_mapping(self.subject_identity, "subject_identity"))
        object.__setattr__(self, "observation_time", _to_utc(self.observation_time, "observation_time"))
        object.__setattr__(self, "availability_time", _to_utc(self.availability_time, "availability_time"))
        if self.observation_time > self.availability_time:
            raise ValueError(
                "execution observation is future: "
                "observation_time cannot follow availability_time"
            )
        _require_enum(self.quality, ObservationQuality, "quality")
        object.__setattr__(self, "quality", ObservationQuality(self.quality))
        object.__setattr__(
            self,
            "sellability_status",
            _require_status_or_not_applicable(self.sellability_status, "sellability_status"),
        )
        for value, name in (
            (self.market_context_digest, "market_context_digest"),
            (self.quote_context_digest, "quote_context_digest"),
            (self.liquidity_context_digest, "liquidity_context_digest"),
        ):
            if value is not None:
                _require_digest(value, name)
        _require_text(self.source_contract_version, "source_contract_version")
        object.__setattr__(self, "source_provenance", _freeze_mapping(self.source_provenance, "source_provenance"))
        _require_text(self.observation_replay_key, "observation_replay_key")
        _set_or_verify_digest(self, "observation_digest", self._canonical_without_digest())

    def _canonical_without_digest(self) -> Mapping[str, Any]:
        return {
            "observation_id": self.observation_id,
            "subject_identity": self.subject_identity,
            "observation_time": self.observation_time,
            "availability_time": self.availability_time,
            "quality": self.quality.value,
            "market_context_digest": self.market_context_digest,
            "quote_context_digest": self.quote_context_digest,
            "liquidity_context_digest": self.liquidity_context_digest,
            "sellability_status": self.sellability_status.value,
            "source_contract_version": self.source_contract_version,
            "source_provenance": self.source_provenance,
            "observation_replay_key": self.observation_replay_key,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._canonical_without_digest(), "observation_digest": self.observation_digest})

    deterministic_representation = property(lambda self: self.canonical_representation)


@dataclass(frozen=True)
class SimulationConfigurationIdentity:
    configuration_id: str
    contract_version: str
    simulation_version: str
    fill_model_version: str
    friction_model_version: str
    failure_policy_version: str
    seed_policy_version: str
    configuration_provenance: Mapping[str, Any]
    configuration_digest: str | None = None

    def __post_init__(self) -> None:
        for value, name in (
            (self.configuration_id, "configuration_id"),
            (self.contract_version, "contract_version"),
            (self.simulation_version, "simulation_version"),
            (self.fill_model_version, "fill_model_version"),
            (self.friction_model_version, "friction_model_version"),
            (self.failure_policy_version, "failure_policy_version"),
            (self.seed_policy_version, "seed_policy_version"),
        ):
            _require_text(value, name)
        object.__setattr__(
            self,
            "configuration_provenance",
            _freeze_mapping(self.configuration_provenance, "configuration_provenance"),
        )
        _set_or_verify_digest(self, "configuration_digest", self._canonical_without_digest())

    def _canonical_without_digest(self) -> Mapping[str, Any]:
        return {
            "configuration_id": self.configuration_id,
            "contract_version": self.contract_version,
            "simulation_version": self.simulation_version,
            "fill_model_version": self.fill_model_version,
            "friction_model_version": self.friction_model_version,
            "failure_policy_version": self.failure_policy_version,
            "seed_policy_version": self.seed_policy_version,
            "configuration_provenance": self.configuration_provenance,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._canonical_without_digest(), "configuration_digest": self.configuration_digest})

    deterministic_representation = property(lambda self: self.canonical_representation)


@dataclass(frozen=True)
class InitialPaperStateIdentity:
    state_id: str
    state_version: str
    portfolio_scope: Mapping[str, Any]
    position_state_digest: str
    exposure_state_digest: str
    as_of_time: datetime
    state_quality: ObservationQuality | str
    state_provenance: Mapping[str, Any]
    state_digest: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.state_id, "state_id")
        _require_text(self.state_version, "state_version")
        object.__setattr__(self, "portfolio_scope", _freeze_mapping(self.portfolio_scope, "portfolio_scope"))
        _require_digest(self.position_state_digest, "position_state_digest")
        _require_digest(self.exposure_state_digest, "exposure_state_digest")
        object.__setattr__(self, "as_of_time", _to_utc(self.as_of_time, "as_of_time"))
        _require_enum(self.state_quality, ObservationQuality, "state_quality")
        object.__setattr__(self, "state_quality", ObservationQuality(self.state_quality))
        object.__setattr__(self, "state_provenance", _freeze_mapping(self.state_provenance, "state_provenance"))
        _set_or_verify_digest(self, "state_digest", self._canonical_without_digest())

    def _canonical_without_digest(self) -> Mapping[str, Any]:
        return {
            "state_id": self.state_id,
            "state_version": self.state_version,
            "portfolio_scope": self.portfolio_scope,
            "position_state_digest": self.position_state_digest,
            "exposure_state_digest": self.exposure_state_digest,
            "as_of_time": self.as_of_time,
            "state_quality": self.state_quality.value,
            "state_provenance": self.state_provenance,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._canonical_without_digest(), "state_digest": self.state_digest})

    deterministic_representation = property(lambda self: self.canonical_representation)


@dataclass(frozen=True)
class ReplayIdentity:
    replay_id: str
    replay_schema_version: str
    replay_seed_identity: str
    parent_replay_id: str | None
    replay_scope: Mapping[str, Any]

    def __post_init__(self) -> None:
        for value, name in (
            (self.replay_id, "replay_id"),
            (self.replay_schema_version, "replay_schema_version"),
            (self.replay_seed_identity, "replay_seed_identity"),
        ):
            _require_text(value, name)
        if self.parent_replay_id is not None:
            _require_text(self.parent_replay_id, "parent_replay_id")
        object.__setattr__(self, "replay_scope", _freeze_mapping(self.replay_scope, "replay_scope"))

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "replay_id": self.replay_id,
                "replay_schema_version": self.replay_schema_version,
                "replay_seed_identity": self.replay_seed_identity,
                "parent_replay_id": self.parent_replay_id,
                "replay_scope": self.replay_scope,
            }
        )

    deterministic_representation = property(lambda self: self.canonical_representation)


@dataclass(frozen=True)
class PaperSimulationInput:
    decision_intent: P06DecisionIntentIdentity | DecisionIntent
    authorization_observation: AuthorizationObservation
    execution_observation: ExecutionObservation
    simulation_configuration: SimulationConfigurationIdentity
    initial_paper_state: InitialPaperStateIdentity
    simulation_reference_time: datetime
    replay_identity: ReplayIdentity
    contract_version: str = P07_T01_CONTRACT_VERSION
    input_digest: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.decision_intent, DecisionIntent):
            identity = P06DecisionIntentIdentity.from_intent(self.decision_intent)
        elif isinstance(self.decision_intent, P06DecisionIntentIdentity):
            identity = self.decision_intent
        else:
            raise ValueError("decision_intent must be a DecisionIntent or identity envelope")
        object.__setattr__(self, "decision_intent", identity)
        if not isinstance(self.authorization_observation, AuthorizationObservation):
            raise ValueError("authorization_observation must be an AuthorizationObservation")
        if not isinstance(self.execution_observation, ExecutionObservation):
            raise ValueError("execution_observation must be an ExecutionObservation")
        if not isinstance(self.simulation_configuration, SimulationConfigurationIdentity):
            raise ValueError("simulation_configuration must be a SimulationConfigurationIdentity")
        if not isinstance(self.initial_paper_state, InitialPaperStateIdentity):
            raise ValueError("initial_paper_state must be an InitialPaperStateIdentity")
        if not isinstance(self.replay_identity, ReplayIdentity):
            raise ValueError("replay_identity must be a ReplayIdentity")
        if self.contract_version != P07_T01_CONTRACT_VERSION:
            raise ValueError("unsupported P07-T01 contract_version")
        object.__setattr__(self, "simulation_reference_time", _to_utc(
            self.simulation_reference_time, "simulation_reference_time"
        ))
        self._validate_temporal_boundary()
        self._validate_status_boundary()
        _set_or_verify_digest(self, "input_digest", self._canonical_without_digest())

    def _validate_temporal_boundary(self) -> None:
        reference = self.simulation_reference_time
        if self.decision_intent.decision_time > reference:
            raise ValueError("decision_time cannot be future relative to simulation_reference_time")
        context_time = _to_utc(self.decision_intent.intent.context.reference_time, "context.reference_time")
        if context_time > self.decision_intent.decision_time:
            raise ValueError("DecisionIntent decision_time precedes context.reference_time")
        authorization = self.authorization_observation
        if authorization.valid_from > reference:
            raise ValueError("authorization valid_from is future relative to simulation_reference_time")
        if authorization.valid_until is not None and authorization.valid_until < reference:
            raise ValueError("authorization is stale at simulation_reference_time")
        execution = self.execution_observation
        if execution.observation_time > reference:
            raise ValueError(
                "execution observation is future relative to simulation_reference_time"
            )
        if execution.availability_time > reference:
            raise ValueError(
                "execution observation is future relative to simulation_reference_time"
            )
        if self.initial_paper_state.as_of_time > reference:
            raise ValueError("initial paper state is future relative to simulation_reference_time")

    def _validate_status_boundary(self) -> None:
        auth = self.authorization_observation

        if auth.status is ObservationStatus.PASS:
            if auth.valid_until is None:
                raise ValueError("PASS authorization requires valid_until")
        elif auth.status in {
            ObservationStatus.FAIL,
            ObservationStatus.UNKNOWN,
        }:
            raise ValueError(
                "authorization observation is not simulatable"
            )

        if auth.status is ObservationStatus.UNKNOWN and not auth.unknown_reasons:
            raise ValueError("UNKNOWN authorization requires unknown_reasons")

        if self.execution_observation.quality is ObservationQuality.UNKNOWN:
            return
        if self.execution_observation.quality in {
            ObservationQuality.FAIL,
            ObservationQuality.INVALID,
        }:
            raise ValueError("execution observation is not simulatable")
        if self.initial_paper_state.state_quality in {
            ObservationQuality.FAIL,
            ObservationQuality.INVALID,
        }:
            raise ValueError("initial paper state is not simulatable")

    def _canonical_without_digest(self) -> Mapping[str, Any]:
        return {
            "contract_version": self.contract_version,
            "decision_intent": self.decision_intent.canonical_representation,
            "authorization_observation": self.authorization_observation.canonical_representation,
            "execution_observation": self.execution_observation.canonical_representation,
            "simulation_configuration": self.simulation_configuration.canonical_representation,
            "initial_paper_state": self.initial_paper_state.canonical_representation,
            "simulation_reference_time": self.simulation_reference_time,
            "replay_identity": self.replay_identity.canonical_representation,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._canonical_without_digest(), "input_digest": self.input_digest})

    deterministic_representation = property(lambda self: self.canonical_representation)

    @property
    def digest(self) -> str:
        return self.input_digest  # type: ignore[return-value]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PaperSimulationInput":
        allowed = {
            "contract_version",
            "decision_intent",
            "authorization_observation",
            "execution_observation",
            "simulation_configuration",
            "initial_paper_state",
            "simulation_reference_time",
            "replay_identity",
            "input_digest",
        }
        _reject_unknown(value, allowed, "PaperSimulationInput")
        required = allowed - {"contract_version", "input_digest"}
        missing = sorted(name for name in required if name not in value)
        if missing:
            raise ValueError(f"missing PaperSimulationInput fields: {', '.join(missing)}")
        return cls(**dict(value))


DecisionIntentIdentity = P06DecisionIntentIdentity
PaperPositionExposureStateIdentity = InitialPaperStateIdentity


def _set_or_verify_digest(instance: Any, field: str, value: Any) -> None:
    expected = _digest(value)
    supplied = getattr(instance, field)
    if supplied is not None:
        _require_digest(supplied, field)
        if supplied != expected:
            raise ValueError(f"{field} does not match canonical representation")
    else:
        object.__setattr__(instance, field, expected)


def _freeze_mapping(value: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return _freeze(_canonicalize(value))


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    if isinstance(value, tuple):
        return tuple(_freeze(child) for child in value)
    return value


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Decimal must be finite")
        return _decimal_text(value)
    if isinstance(value, datetime):
        return _timestamp_text(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("mapping keys must be strings")
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float):
        raise ValueError("float values are not canonical; use Decimal")
    raise ValueError(f"{type(value).__name__} cannot be deterministically serialized")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonicalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _timestamp_text(value: datetime) -> str:
    return _to_utc(value, "timestamp").isoformat(timespec="microseconds").replace("+00:00", "Z")


def _to_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _decimal_text(value: Decimal) -> str:
    normalized = Decimal("0") if value == 0 else value.normalize()
    return format(normalized, "f")


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be canonical non-empty text")


def _texts(values: Any, name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{name} must be a tuple or list")
    normalized = tuple(values)
    for value in normalized:
        _require_text(value, name)
    return tuple(sorted(dict.fromkeys(normalized)))


def _require_enum(value: Any, enum_type: type[StrEnum], name: str) -> None:
    try:
        enum_type(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"unsupported {name}") from error


def _require_status_or_not_applicable(value: Any, name: str) -> ObservationStatus | str:
    if value == NOT_APPLICABLE:
        return NOT_APPLICABLE
    _require_enum(value, ObservationStatus, name)
    return ObservationStatus(value)


def _require_digest(value: Any, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != _DIGEST_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _reject_unknown(value: Mapping[str, Any], allowed: set[str], name: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"unsupported {name} fields: {', '.join(unknown)}")


__all__ = [
    "AuthorizationObservation",
    "DecisionIntentIdentity",
    "ExecutionObservation",
    "InitialPaperStateIdentity",
    "NOT_APPLICABLE",
    "ObservationQuality",
    "ObservationStatus",
    "P06DecisionIntentIdentity",
    "P07_T01_CONTRACT_VERSION",
    "PaperPositionExposureStateIdentity",
    "PaperSimulationInput",
    "ReplayIdentity",
    "SimulationConfigurationIdentity",
]