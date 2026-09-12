"""Deterministic, paper-only P08 Safe V1 Risk/Capital Authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Mapping

from core.decision import DecisionAction, DecisionIntent, EntryPosture
from core.opportunity.opportunity_risk import CandidateViabilityStatus


P08_POLICY_CONTRACT_VERSION = "p08-risk-capital-policy-v1"
P08_AUTHORITY_CONTRACT_VERSION = "p08-risk-capital-authority-v1"
P08_AUTHORITY_EVALUATOR_VERSION = "p08-risk-capital-authority-evaluator-v1"
PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY = "PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY"


class AuthorizationStatus(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RiskStateStatus(StrEnum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    UNKNOWN = "UNKNOWN"


REASON_PRECEDENCE: tuple[tuple[str, ...], ...] = (
    ("MISSING_REQUIRED_INPUT", "INVALID_INPUT"),
    ("UNSUPPORTED_VERSION", "NON_CANONICAL_INPUT"),
    ("DIGEST_MISMATCH", "PROVENANCE_LINKAGE_FAILURE"),
    ("CONTRADICTORY_INPUT", "SCOPE_MISMATCH"),
    ("DUPLICATE_LIFECYCLE_CONFLICT", "REPLAY_IDENTITY_CONFLICT"),
    (
        "REFERENCE_TIME_INVALID",
        "POLICY_NOT_YET_VALID",
        "POLICY_EXPIRED",
        "POLICY_STATE_STALE",
        "POLICY_STATE_FUTURE_DATED",
    ),
    (
        "P05_HARD_RISK_NOT_ELIGIBLE",
        "P06_NO_TRADE",
        "P06_UNCERTAIN",
        "P06_INVALIDATED",
        "P06_ACTION_NOT_ALLOWED",
        "P06_ENTRY_POSTURE_NOT_ALLOWED",
    ),
    (
        "RISK_STATE_BLOCKED",
        "RISK_STATE_UNKNOWN",
        "PAPER_CAPITAL_STATE_UNKNOWN",
        "PAPER_EXPOSURE_STATE_UNKNOWN",
        "PAPER_OBSERVATION_UNAVAILABLE",
    ),
    (
        "PAPER_UNIT_INVALID",
        "PAPER_ENTRY_AMOUNT_INVALID",
        "PAPER_ENTRY_LIMIT_EXCEEDED",
        "PAPER_BUDGET_EXCEEDED",
        "PAPER_EXPOSURE_LIMIT_EXCEEDED",
    ),
)

REASON_ORDER = {
    reason: (group_index, item_index)
    for group_index, group in enumerate(REASON_PRECEDENCE)
    for item_index, reason in enumerate(group)
}
KNOWN_REASONS = frozenset(REASON_ORDER)


def _utc(value: Any, name: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _timestamp_text(value: datetime) -> str:
    return _utc(value, "timestamp").isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
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


def _decimal(value: Any, name: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int)):
        raise ValueError(f"{name} must be a finite Decimal")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError(f"{name} must be a finite Decimal")
    if positive and result <= 0:
        raise ValueError(f"{name} must be positive")
    if not positive and result < 0:
        raise ValueError(f"{name} must be non-negative")
    return Decimal("0") if result == 0 else result.normalize()


def _decimal_text(value: Decimal) -> str:
    return format(Decimal("0") if value == 0 else value.normalize(), "f")


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("float must be finite")
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
    raise ValueError(f"{type(value).__name__} is not canonical")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(child) for key, child in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonicalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return _freeze(_canonicalize(value))


def _texts(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{name} must be a tuple or list")
    normalized = tuple(_text(item, name) for item in value)
    return tuple(sorted(dict.fromkeys(normalized)))


def _scope(value: Any) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("scope_identity must be a mapping")
    expected = {
        "paper_lifecycle_id",
        "paper_portfolio_id",
        "candidate_id",
        "chain_id",
        "token_identity",
    }
    if set(value) != expected:
        raise ValueError("scope_identity must contain exactly the Safe V1 fields")
    return _freeze({key: _text(value[key], f"scope_identity.{key}") for key in expected})


def _set_or_verify_digest(instance: Any, field: str, source: Any) -> None:
    expected = _digest(source)
    supplied = getattr(instance, field)
    if supplied is not None:
        _digest_text(supplied, field)
        if supplied != expected:
            raise ValueError(f"{field} does not match canonical representation")
    object.__setattr__(instance, field, expected)


def _verify_digest(instance: Any, field: str, source: Any) -> None:
    supplied = getattr(instance, field)
    _digest_text(supplied, field)
    if supplied != _digest(source):
        raise ValueError(f"{field} does not match canonical representation")


@dataclass(frozen=True)
class RiskState:
    status: RiskStateStatus | str
    emergency_stop: bool
    risk_flags: tuple[str, ...]
    as_of_time: datetime
    available_at: datetime
    state_digest: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "status", RiskStateStatus(self.status))
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported risk_state.status") from error
        if not isinstance(self.emergency_stop, bool):
            raise ValueError("risk_state.emergency_stop must be boolean")
        object.__setattr__(self, "risk_flags", _texts(self.risk_flags, "risk_flags"))
        as_of = _utc(self.as_of_time, "risk_state.as_of_time")
        available = _utc(self.available_at, "risk_state.available_at")
        if as_of > available:
            raise ValueError("risk_state.as_of_time cannot follow available_at")
        object.__setattr__(self, "as_of_time", as_of)
        object.__setattr__(self, "available_at", available)
        _set_or_verify_digest(self, "state_digest", self._without_digest())

    def _without_digest(self) -> Mapping[str, Any]:
        return {
            "status": self.status,
            "emergency_stop": self.emergency_stop,
            "risk_flags": self.risk_flags,
            "as_of_time": self.as_of_time,
            "available_at": self.available_at,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._without_digest(), "state_digest": self.state_digest})

    deterministic_representation = property(lambda self: self.canonical_representation)


@dataclass(frozen=True)
class PaperCapitalState:
    unit: str
    budget_total: Decimal
    committed_before: Decimal
    requested_entry: Decimal
    max_single_entry: Decimal
    as_of_time: datetime
    available_at: datetime
    state_digest: str | None = None

    def __post_init__(self) -> None:
        _text(self.unit, "paper_capital_state.unit")
        for field in (
            "budget_total",
            "committed_before",
            "requested_entry",
            "max_single_entry",
        ):
            object.__setattr__(
                self,
                field,
                _decimal(getattr(self, field), f"paper_capital_state.{field}"),
            )
        if self.requested_entry <= 0:
            raise ValueError("paper_capital_state.requested_entry must be positive")
        as_of = _utc(self.as_of_time, "paper_capital_state.as_of_time")
        available = _utc(self.available_at, "paper_capital_state.available_at")
        if as_of > available:
            raise ValueError("paper_capital_state.as_of_time cannot follow available_at")
        object.__setattr__(self, "as_of_time", as_of)
        object.__setattr__(self, "available_at", available)
        _set_or_verify_digest(self, "state_digest", self._without_digest())

    def _without_digest(self) -> Mapping[str, Any]:
        return {
            "unit": self.unit,
            "budget_total": self.budget_total,
            "committed_before": self.committed_before,
            "requested_entry": self.requested_entry,
            "max_single_entry": self.max_single_entry,
            "as_of_time": self.as_of_time,
            "available_at": self.available_at,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._without_digest(), "state_digest": self.state_digest})

    deterministic_representation = property(lambda self: self.canonical_representation)


@dataclass(frozen=True)
class PaperExposureState:
    unit: str
    exposure_before: Decimal
    max_total_exposure: Decimal
    as_of_time: datetime
    available_at: datetime
    state_digest: str | None = None

    def __post_init__(self) -> None:
        _text(self.unit, "paper_exposure_state.unit")
        for field in ("exposure_before", "max_total_exposure"):
            object.__setattr__(
                self,
                field,
                _decimal(getattr(self, field), f"paper_exposure_state.{field}"),
            )
        as_of = _utc(self.as_of_time, "paper_exposure_state.as_of_time")
        available = _utc(self.available_at, "paper_exposure_state.available_at")
        if as_of > available:
            raise ValueError("paper_exposure_state.as_of_time cannot follow available_at")
        object.__setattr__(self, "as_of_time", as_of)
        object.__setattr__(self, "available_at", available)
        _set_or_verify_digest(self, "state_digest", self._without_digest())

    def _without_digest(self) -> Mapping[str, Any]:
        return {
            "unit": self.unit,
            "exposure_before": self.exposure_before,
            "max_total_exposure": self.max_total_exposure,
            "as_of_time": self.as_of_time,
            "available_at": self.available_at,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._without_digest(), "state_digest": self.state_digest})

    deterministic_representation = property(lambda self: self.canonical_representation)


@dataclass(frozen=True)
class PaperRiskCapitalPolicySnapshot:
    policy_snapshot_id: str
    risk_governor_version: str
    capital_authorization_version: str
    evaluator_version: str
    scope_identity: Mapping[str, str]
    decision_intent_digest: str
    context_digest: str
    simulation_reference_time: datetime
    policy_cutoff_time: datetime
    risk_state_max_age_seconds: Decimal | int
    paper_capital_state_max_age_seconds: Decimal | int
    paper_exposure_state_max_age_seconds: Decimal | int
    valid_from: datetime
    valid_until: datetime
    risk_state: RiskState
    paper_capital_state: PaperCapitalState
    paper_exposure_state: PaperExposureState
    provenance: Mapping[str, Any]
    contract_version: str = P08_POLICY_CONTRACT_VERSION
    policy_snapshot_digest: str | None = None

    def __post_init__(self) -> None:
        _text(self.policy_snapshot_id, "policy_snapshot_id")
        for value, name in (
            (self.risk_governor_version, "risk_governor_version"),
            (self.capital_authorization_version, "capital_authorization_version"),
            (self.evaluator_version, "evaluator_version"),
        ):
            _text(value, name)
        if self.contract_version != P08_POLICY_CONTRACT_VERSION:
            raise ValueError("unsupported P08 policy contract_version")
        object.__setattr__(self, "scope_identity", _scope(self.scope_identity))
        _digest_text(self.decision_intent_digest, "decision_intent_digest")
        _digest_text(self.context_digest, "context_digest")
        object.__setattr__(
            self,
            "simulation_reference_time",
            _utc(self.simulation_reference_time, "simulation_reference_time"),
        )
        object.__setattr__(
            self,
            "policy_cutoff_time",
            _utc(self.policy_cutoff_time, "policy_cutoff_time"),
        )
        for field in (
            "risk_state_max_age_seconds",
            "paper_capital_state_max_age_seconds",
            "paper_exposure_state_max_age_seconds",
        ):
            object.__setattr__(
                self,
                field,
                _decimal(
                    getattr(self, field),
                    field,
                    positive=True,
                ),
            )
        valid_from = _utc(self.valid_from, "valid_from")
        valid_until = _utc(self.valid_until, "valid_until")
        if valid_until < valid_from:
            raise ValueError("valid_until cannot precede valid_from")
        object.__setattr__(self, "valid_from", valid_from)
        object.__setattr__(self, "valid_until", valid_until)
        for value, name, expected in (
            (self.risk_state, "risk_state", RiskState),
            (self.paper_capital_state, "paper_capital_state", PaperCapitalState),
            (self.paper_exposure_state, "paper_exposure_state", PaperExposureState),
        ):
            if not isinstance(value, expected):
                raise ValueError(f"{name} must be a {expected.__name__}")
        object.__setattr__(self, "provenance", _mapping(self.provenance, "provenance"))
        _set_or_verify_digest(
            self,
            "policy_snapshot_digest",
            self._without_digest(),
        )

    def _without_digest(self) -> Mapping[str, Any]:
        return {
            "contract_version": self.contract_version,
            "policy_snapshot_id": self.policy_snapshot_id,
            "risk_governor_version": self.risk_governor_version,
            "capital_authorization_version": self.capital_authorization_version,
            "evaluator_version": self.evaluator_version,
            "scope_identity": self.scope_identity,
            "decision_intent_digest": self.decision_intent_digest,
            "context_digest": self.context_digest,
            "simulation_reference_time": self.simulation_reference_time,
            "policy_cutoff_time": self.policy_cutoff_time,
            "risk_state_max_age_seconds": self.risk_state_max_age_seconds,
            "paper_capital_state_max_age_seconds": self.paper_capital_state_max_age_seconds,
            "paper_exposure_state_max_age_seconds": self.paper_exposure_state_max_age_seconds,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "risk_state": self.risk_state.canonical_representation,
            "paper_capital_state": self.paper_capital_state.canonical_representation,
            "paper_exposure_state": self.paper_exposure_state.canonical_representation,
            "provenance": self.provenance,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {**self._without_digest(), "policy_snapshot_digest": self.policy_snapshot_digest}
        )

    deterministic_representation = property(lambda self: self.canonical_representation)

    @property
    def digest(self) -> str:
        return self.policy_snapshot_digest  # type: ignore[return-value]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PaperRiskCapitalPolicySnapshot":
        if not isinstance(value, Mapping):
            raise ValueError("PaperRiskCapitalPolicySnapshot must be a mapping")
        allowed = {
            "contract_version",
            "policy_snapshot_id",
            "policy_snapshot_digest",
            "risk_governor_version",
            "capital_authorization_version",
            "evaluator_version",
            "scope_identity",
            "decision_intent_digest",
            "context_digest",
            "simulation_reference_time",
            "policy_cutoff_time",
            "risk_state_max_age_seconds",
            "paper_capital_state_max_age_seconds",
            "paper_exposure_state_max_age_seconds",
            "valid_from",
            "valid_until",
            "risk_state",
            "paper_capital_state",
            "paper_exposure_state",
            "provenance",
        }
        _reject_unknown(value, allowed, "PaperRiskCapitalPolicySnapshot")
        required = allowed - {"contract_version", "policy_snapshot_digest"}
        missing = sorted(field for field in required if field not in value)
        if missing:
            raise ValueError(
                "missing PaperRiskCapitalPolicySnapshot fields: "
                + ", ".join(missing)
            )
        converted = dict(value)
        if isinstance(converted["risk_state"], Mapping):
            converted["risk_state"] = RiskState(**converted["risk_state"])
        if isinstance(converted["paper_capital_state"], Mapping):
            converted["paper_capital_state"] = PaperCapitalState(
                **converted["paper_capital_state"]
            )
        if isinstance(converted["paper_exposure_state"], Mapping):
            converted["paper_exposure_state"] = PaperExposureState(
                **converted["paper_exposure_state"]
            )
        return cls(**converted)


@dataclass(frozen=True)
class PaperRiskCapitalAuthorizationResult:
    status: AuthorizationStatus | str
    paper_lifecycle_id: str
    scope_identity: Mapping[str, str]
    decision_intent_digest: str
    context_digest: str
    policy_snapshot_id: str
    policy_snapshot_digest: str
    simulation_reference_time: datetime
    valid_from: datetime
    valid_until: datetime
    primary_reason_code: str | None
    reason_codes: tuple[str, ...]
    provenance: Mapping[str, Any]
    contract_version: str = P08_AUTHORITY_CONTRACT_VERSION
    evaluator_version: str = P08_AUTHORITY_EVALUATOR_VERSION
    authorization_effect: str = PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY
    authorization_id: str | None = None
    result_digest: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "status", AuthorizationStatus(self.status))
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported authorization status") from error
        _text(self.paper_lifecycle_id, "paper_lifecycle_id")
        object.__setattr__(self, "scope_identity", _scope(self.scope_identity))
        _digest_text(self.decision_intent_digest, "decision_intent_digest")
        _digest_text(self.context_digest, "context_digest")
        _text(self.policy_snapshot_id, "policy_snapshot_id")
        _digest_text(self.policy_snapshot_digest, "policy_snapshot_digest")
        object.__setattr__(
            self,
            "simulation_reference_time",
            _utc(self.simulation_reference_time, "simulation_reference_time"),
        )
        valid_from = _utc(self.valid_from, "valid_from")
        valid_until = _utc(self.valid_until, "valid_until")
        if valid_until < valid_from:
            raise ValueError("valid_until cannot precede valid_from")
        object.__setattr__(self, "valid_from", valid_from)
        object.__setattr__(self, "valid_until", valid_until)
        _text(self.contract_version, "contract_version")
        _text(self.evaluator_version, "evaluator_version")
        if self.contract_version != P08_AUTHORITY_CONTRACT_VERSION:
            raise ValueError("unsupported P08 authority contract_version")
        if self.evaluator_version != P08_AUTHORITY_EVALUATOR_VERSION:
            raise ValueError("unsupported P08 authority evaluator_version")
        if self.authorization_effect != PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY:
            raise ValueError("unsupported authorization_effect")
        reasons = _ordered_reasons(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)
        if self.status is AuthorizationStatus.APPROVED:
            if self.primary_reason_code is not None or reasons:
                raise ValueError("approved result cannot contain rejection reasons")
        else:
            if not reasons:
                raise ValueError("rejected result requires a reason code")
            if self.primary_reason_code != reasons[0]:
                raise ValueError("primary_reason_code must be first by precedence")
        object.__setattr__(self, "provenance", _mapping(self.provenance, "provenance"))
        expected_authorization_id = _digest(
            {
                "contract_version": self.contract_version,
                "paper_lifecycle_id": self.paper_lifecycle_id,
                "decision_intent_digest": self.decision_intent_digest,
                "policy_snapshot_digest": self.policy_snapshot_digest,
                "simulation_reference_time": self.simulation_reference_time,
            }
        )
        if self.authorization_id is not None:
            _digest_text(self.authorization_id, "authorization_id")
            if self.authorization_id != expected_authorization_id:
                raise ValueError("authorization_id does not match canonical identity")
        object.__setattr__(self, "authorization_id", expected_authorization_id)
        _set_or_verify_digest(self, "result_digest", self._without_digest())

    def _without_digest(self) -> Mapping[str, Any]:
        return {
            "contract_version": self.contract_version,
            "evaluator_version": self.evaluator_version,
            "status": self.status,
            "authorization_effect": self.authorization_effect,
            "authorization_id": self.authorization_id,
            "paper_lifecycle_id": self.paper_lifecycle_id,
            "scope_identity": self.scope_identity,
            "decision_intent_digest": self.decision_intent_digest,
            "context_digest": self.context_digest,
            "policy_snapshot_id": self.policy_snapshot_id,
            "policy_snapshot_digest": self.policy_snapshot_digest,
            "simulation_reference_time": self.simulation_reference_time,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "primary_reason_code": self.primary_reason_code,
            "reason_codes": self.reason_codes,
            "provenance": self.provenance,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._without_digest(), "result_digest": self.result_digest})

    deterministic_representation = property(lambda self: self.canonical_representation)

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]

    @property
    def is_authorization(self) -> bool:
        return True

    @property
    def is_order(self) -> bool:
        return False

    def to_authorization_observation(self):
        from core.execution.paper_simulation_input import (
            AuthorizationObservation,
            ObservationStatus,
        )

        unknown_reasons = tuple(
            reason
            for reason in self.reason_codes
            if reason
            in {
                "RISK_STATE_UNKNOWN",
                "PAPER_CAPITAL_STATE_UNKNOWN",
                "PAPER_EXPOSURE_STATE_UNKNOWN",
                "PAPER_OBSERVATION_UNAVAILABLE",
            }
        )
        return AuthorizationObservation(
            observation_id=self.authorization_id,
            observation_digest=None,
            status=(
                ObservationStatus.PASS
                if self.status is AuthorizationStatus.APPROVED
                else ObservationStatus.FAIL
            ),
            scope_identity=self.scope_identity,
            observed_at=self.simulation_reference_time,
            valid_from=self.valid_from,
            valid_until=self.valid_until,
            contract_version=self.contract_version,
            risk_governor_version=str(self.provenance["risk_governor_version"]),
            capital_authorization_version=str(
                self.provenance["capital_authorization_version"]
            ),
            reason_codes=self.reason_codes,
            unknown_reasons=unknown_reasons,
        )


def _ordered_reasons(reasons: Any) -> tuple[str, ...]:
    if not isinstance(reasons, (tuple, list)):
        raise ValueError("reason_codes must be a tuple or list")
    normalized = tuple(reasons)
    if any(reason not in KNOWN_REASONS for reason in normalized):
        raise ValueError("reason_codes contains an unsupported reason")
    return tuple(sorted(set(normalized), key=lambda reason: REASON_ORDER[reason]))


def _reject_unknown(value: Mapping[str, Any], allowed: set[str], name: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"unsupported {name} fields: {', '.join(unknown)}")


def _validate_intent(intent: Any) -> None:
    if not isinstance(intent, DecisionIntent):
        raise ValueError("decision_intent must be a DecisionIntent")
    if (
        intent.canonical_representation != intent.deterministic_representation
        or intent.digest != _digest(intent.canonical_representation)
    ):
        raise ValueError("DecisionIntent is not canonical")
    if not isinstance(intent.action, DecisionAction) or not isinstance(
        intent.entry_posture, EntryPosture
    ):
        raise ValueError("DecisionIntent contains unsupported enums")
    if intent.context_digest != intent.context.digest:
        raise ValueError("DecisionIntent context digest is invalid")
    if intent.risk_evaluation.viability_status is not CandidateViabilityStatus.ELIGIBLE:
        return
    if intent.context.canonical_representation != intent.context.deterministic_representation:
        raise ValueError("DecisionIntent context is not canonical")


def _validate_policy_integrity(policy: PaperRiskCapitalPolicySnapshot) -> None:
    for state, field in (
        (policy.risk_state, "state_digest"),
        (policy.paper_capital_state, "state_digest"),
        (policy.paper_exposure_state, "state_digest"),
    ):
        _verify_digest(state, field, state._without_digest())
    _verify_digest(policy, "policy_snapshot_digest", policy._without_digest())


def _freshness_reasons(policy: PaperRiskCapitalPolicySnapshot) -> list[str]:
    reasons: list[str] = []
    values = (
        (
            policy.risk_state,
            policy.risk_state_max_age_seconds,
        ),
        (
            policy.paper_capital_state,
            policy.paper_capital_state_max_age_seconds,
        ),
        (
            policy.paper_exposure_state,
            policy.paper_exposure_state_max_age_seconds,
        ),
    )
    for state, maximum_age in values:
        age = (policy.policy_cutoff_time - state.as_of_time).total_seconds()
        if state.as_of_time > policy.policy_cutoff_time or age < 0:
            reasons.append("POLICY_STATE_FUTURE_DATED")
        elif Decimal(str(age)) > maximum_age:
            reasons.append("POLICY_STATE_STALE")
        if state.available_at > policy.simulation_reference_time:
            reasons.append("PAPER_OBSERVATION_UNAVAILABLE")
    return reasons


def _evaluate_reasons(
    intent: DecisionIntent,
    policy: PaperRiskCapitalPolicySnapshot,
) -> tuple[str, ...]:
    reasons: list[str] = []
    scope = policy.scope_identity
    if policy.decision_intent_digest != intent.digest or policy.context_digest != intent.context_digest:
        reasons.append("PROVENANCE_LINKAGE_FAILURE")
    if (
        scope["candidate_id"] != intent.candidate_id
        or scope["chain_id"] != intent.chain_id
        or scope["token_identity"] != intent.token_identity
    ):
        reasons.append("SCOPE_MISMATCH")
    if intent.action is not DecisionAction.BUY:
        reasons.append("P06_NO_TRADE" if intent.action is DecisionAction.NO_TRADE else "P06_ACTION_NOT_ALLOWED")
    if intent.entry_posture is not EntryPosture.WAIT:
        reasons.append("P06_ENTRY_POSTURE_NOT_ALLOWED")
    if intent.uncertainty:
        reasons.append("P06_UNCERTAIN")
    if intent.invalidation_conditions:
        reasons.append("P06_INVALIDATED")
    if intent.risk_evaluation.viability_status is not CandidateViabilityStatus.ELIGIBLE:
        reasons.append("P05_HARD_RISK_NOT_ELIGIBLE")
    if intent.context.reference_time > intent.decision_time or intent.decision_time > policy.simulation_reference_time:
        reasons.append("REFERENCE_TIME_INVALID")
    if policy.valid_from > policy.simulation_reference_time:
        reasons.append("POLICY_NOT_YET_VALID")
    if policy.valid_until < policy.simulation_reference_time:
        reasons.append("POLICY_EXPIRED")
    reasons.extend(_freshness_reasons(policy))
    risk = policy.risk_state
    if risk.status is RiskStateStatus.BLOCK or risk.emergency_stop:
        reasons.append("RISK_STATE_BLOCKED")
    elif risk.status is RiskStateStatus.UNKNOWN:
        reasons.append("RISK_STATE_UNKNOWN")
    capital = policy.paper_capital_state
    exposure = policy.paper_exposure_state
    if capital.unit != exposure.unit:
        reasons.append("PAPER_UNIT_INVALID")
    if capital.requested_entry <= 0:
        reasons.append("PAPER_ENTRY_AMOUNT_INVALID")
    if capital.requested_entry > capital.max_single_entry:
        reasons.append("PAPER_ENTRY_LIMIT_EXCEEDED")
    if capital.committed_before + capital.requested_entry > capital.budget_total:
        reasons.append("PAPER_BUDGET_EXCEEDED")
    if exposure.exposure_before + capital.requested_entry > exposure.max_total_exposure:
        reasons.append("PAPER_EXPOSURE_LIMIT_EXCEEDED")
    return _ordered_reasons(reasons)


def evaluate_paper_risk_capital_authorization(
    decision_intent: DecisionIntent,
    policy_snapshot: PaperRiskCapitalPolicySnapshot,
) -> PaperRiskCapitalAuthorizationResult:
    """Evaluate one immutable P06 intent against one immutable paper policy."""

    _validate_intent(decision_intent)
    if not isinstance(policy_snapshot, PaperRiskCapitalPolicySnapshot):
        raise ValueError("policy_snapshot must be a PaperRiskCapitalPolicySnapshot")
    _validate_policy_integrity(policy_snapshot)
    reasons = _evaluate_reasons(decision_intent, policy_snapshot)
    status = (
        AuthorizationStatus.APPROVED
        if not reasons
        else AuthorizationStatus.REJECTED
    )
    return PaperRiskCapitalAuthorizationResult(
        status=status,
        paper_lifecycle_id=policy_snapshot.scope_identity["paper_lifecycle_id"],
        scope_identity=policy_snapshot.scope_identity,
        decision_intent_digest=decision_intent.digest,
        context_digest=decision_intent.context_digest,
        policy_snapshot_id=policy_snapshot.policy_snapshot_id,
        policy_snapshot_digest=policy_snapshot.digest,
        simulation_reference_time=policy_snapshot.simulation_reference_time,
        valid_from=policy_snapshot.valid_from,
        valid_until=policy_snapshot.valid_until,
        primary_reason_code=reasons[0] if reasons else None,
        reason_codes=reasons,
        provenance={
            "risk_governor_version": policy_snapshot.risk_governor_version,
            "capital_authorization_version": policy_snapshot.capital_authorization_version,
            "policy_snapshot_id": policy_snapshot.policy_snapshot_id,
            "policy_snapshot_digest": policy_snapshot.policy_snapshot_digest,
        },
    )


evaluate_risk_capital_authority = evaluate_paper_risk_capital_authorization
authorize_paper_lifecycle = evaluate_paper_risk_capital_authorization
evaluate = evaluate_paper_risk_capital_authorization

PaperRiskState = RiskState
PaperRiskCapitalPolicy = PaperRiskCapitalPolicySnapshot
PaperRiskCapitalAuthorization = PaperRiskCapitalAuthorizationResult


__all__ = [
    "AuthorizationStatus",
    "KNOWN_REASONS",
    "P08_AUTHORITY_CONTRACT_VERSION",
    "P08_AUTHORITY_EVALUATOR_VERSION",
    "P08_POLICY_CONTRACT_VERSION",
    "PAPER_SIMULATION_LIFECYCLE_ENTRY_ONLY",
    "PaperCapitalState",
    "PaperExposureState",
    "PaperRiskCapitalAuthorization",
    "PaperRiskCapitalAuthorizationResult",
    "PaperRiskCapitalPolicy",
    "PaperRiskCapitalPolicySnapshot",
    "PaperRiskState",
    "REASON_PRECEDENCE",
    "RiskState",
    "RiskStateStatus",
    "authorize_paper_lifecycle",
    "evaluate",
    "evaluate_paper_risk_capital_authorization",
    "evaluate_risk_capital_authority",
]