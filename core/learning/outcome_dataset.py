"""Immutable, deterministic P08-T02 outcome-learning dataset snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from core.learning.outcome_observation import (
    P08_T01_CONTRACT_VERSION,
    P08_T01_EVALUATOR_VERSION,
    OutcomeLearningObservation,
)


P08_T02_CONTRACT_VERSION = "p08-t02-v1"
_DIGEST_LENGTH = 64


@dataclass(frozen=True)
class OutcomeLearningDatasetSnapshot:
    """A point-in-time, provenance-preserving collection of T01 observations."""

    observations: tuple[OutcomeLearningObservation, ...]
    as_of_time: datetime
    observation_digests: tuple[str, ...]
    observation_contract_version: str = P08_T01_CONTRACT_VERSION
    observation_evaluator_version: str = P08_T01_EVALUATOR_VERSION
    contract_version: str = P08_T02_CONTRACT_VERSION

    def __post_init__(self) -> None:
        _require_text(self.observation_contract_version, "observation_contract_version")
        _require_text(self.observation_evaluator_version, "observation_evaluator_version")
        _require_text(self.contract_version, "contract_version")
        if self.observation_contract_version != P08_T01_CONTRACT_VERSION:
            raise ValueError("unsupported P08-T01 contract version")
        if self.observation_evaluator_version != P08_T01_EVALUATOR_VERSION:
            raise ValueError("unsupported P08-T01 evaluator version")
        if self.contract_version != P08_T02_CONTRACT_VERSION:
            raise ValueError("unsupported P08-T02 contract version")

        as_of_time = _to_utc(self.as_of_time, "as_of_time")
        object.__setattr__(self, "as_of_time", as_of_time)

        observations = _validated_observations(self.observations, as_of_time)
        if not observations:
            raise ValueError("observations must contain at least one observation")
        ordered = tuple(
            sorted(observations, key=lambda value: _canonical_json(value.canonical_representation))
        )
        digests = tuple(value.digest for value in ordered)
        supplied_digests = tuple(self.observation_digests)
        if supplied_digests != digests:
            raise ValueError("observation digests do not match canonical ordering")
        _validate_unique_digests(digests)
        object.__setattr__(self, "observations", ordered)
        object.__setattr__(self, "observation_digests", digests)

    @property
    def source_observation_digests(self) -> tuple[str, ...]:
        return self.observation_digests

    @property
    def p08_t01_contract_version(self) -> str:
        return self.observation_contract_version

    @property
    def p08_t01_evaluator_version(self) -> str:
        return self.observation_evaluator_version

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "observations": tuple(
                    observation.canonical_representation
                    for observation in self.observations
                ),
                "as_of_time": self.as_of_time.isoformat(),
                "observation_digests": self.observation_digests,
                "observation_contract_version": self.observation_contract_version,
                "observation_evaluator_version": self.observation_evaluator_version,
                "contract_version": self.contract_version,
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

    @property
    def dataset_digest(self) -> str:
        return self.representation_digest


def create_outcome_learning_dataset_snapshot(
    observations: Iterable[OutcomeLearningObservation],
    as_of_time: datetime,
) -> OutcomeLearningDatasetSnapshot:
    """Create one deterministic snapshot from validated T01 observations."""

    if isinstance(observations, (str, bytes)) or not isinstance(observations, Iterable):
        raise ValueError("observations must be an iterable of OutcomeLearningObservation values")
    values = tuple(observations)
    _validated_observations(values, _to_utc(as_of_time, "as_of_time"))
    ordered = tuple(
        sorted(values, key=lambda value: _canonical_json(value.canonical_representation))
    )
    return OutcomeLearningDatasetSnapshot(
        observations=ordered,
        as_of_time=as_of_time,
        observation_digests=tuple(value.digest for value in ordered),
    )


build_outcome_learning_dataset_snapshot = create_outcome_learning_dataset_snapshot
snapshot_outcome_learning_dataset = create_outcome_learning_dataset_snapshot


def _validated_observations(
    observations: Iterable[OutcomeLearningObservation],
    as_of_time: datetime,
) -> tuple[OutcomeLearningObservation, ...]:
    try:
        values = tuple(observations)
    except (TypeError, ValueError) as error:
        raise ValueError("observations must be iterable") from error
    if not values:
        return ()
    digests: list[str] = []
    for observation in values:
        _validate_observation(observation)
        if observation.simulation_reference_time > as_of_time:
            raise ValueError("observation is after as_of_time")
        digests.append(observation.digest)
    _validate_unique_digests(tuple(digests))
    return values


def _validate_observation(value: OutcomeLearningObservation) -> None:
    if not isinstance(value, OutcomeLearningObservation):
        raise ValueError("observations must contain OutcomeLearningObservation values")
    if value.contract_version != P08_T01_CONTRACT_VERSION:
        raise ValueError("unsupported P08-T01 contract version")
    if value.evaluator_version != P08_T01_EVALUATOR_VERSION:
        raise ValueError("unsupported P08-T01 evaluator version")
    try:
        validated = OutcomeLearningObservation(
            decision_intent=value.decision_intent,
            simulation_input=value.simulation_input,
            paper_result=value.paper_result,
            history_results=value.history_results,
            history_digest=value.history_digest,
            contract_version=value.contract_version,
            evaluator_version=value.evaluator_version,
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError("OutcomeLearningObservation is invalid") from error
    if (
        validated != value
        or validated.canonical_representation != value.deterministic_representation
        or validated.digest != value.digest
    ):
        raise ValueError("OutcomeLearningObservation is tampered or non-canonical")


def _validate_unique_digests(digests: tuple[str, ...]) -> None:
    for digest in digests:
        if (
            not isinstance(digest, str)
            or len(digest) != _DIGEST_LENGTH
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError("observation digest must be a lowercase SHA-256 digest")
    if len(set(digests)) != len(digests):
        raise ValueError("duplicate observation digest")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return _to_utc(value, "timestamp").isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value, key=str)
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


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")


def _to_utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


__all__ = [
    "OutcomeLearningDatasetSnapshot",
    "P08_T02_CONTRACT_VERSION",
    "build_outcome_learning_dataset_snapshot",
    "create_outcome_learning_dataset_snapshot",
    "snapshot_outcome_learning_dataset",
]