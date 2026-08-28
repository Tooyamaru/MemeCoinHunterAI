"""Immutable, deterministic P08-T03 outcome interpretation boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.learning.outcome_dataset import (
    P08_T02_CONTRACT_VERSION,
    OutcomeLearningDatasetSnapshot,
)


P08_T03_CONTRACT_VERSION = "p08-t03-v1"
P08_T03_EVALUATOR_VERSION = "p08-t03-evidence-state-v1"
_DIGEST_LENGTH = 64


class OutcomeInterpretationStatus(str, Enum):
    """Evidence-state interpretation only; never an economic result."""

    UNCLASSIFIED = "UNCLASSIFIED"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class OutcomeInterpretationResult:
    """One immutable interpretation linked to exactly one T02 observation."""

    source_dataset_digest: str
    source_observation_digest: str
    candidate_id: str
    chain_id: str
    token_identity: str
    reference_time: datetime
    interpretation_status: OutcomeInterpretationStatus
    source_outcome_status: str
    source_reconciliation_status: str
    contract_version: str = P08_T03_CONTRACT_VERSION
    evaluator_version: str = P08_T03_EVALUATOR_VERSION

    def __post_init__(self) -> None:
        _require_digest(self.source_dataset_digest, "source_dataset_digest")
        _require_digest(self.source_observation_digest, "source_observation_digest")

        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.chain_id, "chain_id")
        _require_text(self.token_identity, "token_identity")
        _require_text(self.source_outcome_status, "source_outcome_status")
        _require_text(
            self.source_reconciliation_status,
            "source_reconciliation_status",
        )

        reference_time = _to_utc(self.reference_time, "reference_time")
        object.__setattr__(self, "reference_time", reference_time)

        if not isinstance(
            self.interpretation_status,
            OutcomeInterpretationStatus,
        ):
            try:
                status = OutcomeInterpretationStatus(self.interpretation_status)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "unsupported interpretation status"
                ) from error
            object.__setattr__(self, "interpretation_status", status)

        _require_text(self.contract_version, "contract_version")
        _require_text(self.evaluator_version, "evaluator_version")

        if self.contract_version != P08_T03_CONTRACT_VERSION:
            raise ValueError("unsupported P08-T03 contract version")

        if self.evaluator_version != P08_T03_EVALUATOR_VERSION:
            raise ValueError("unsupported P08-T03 evaluator version")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "source_dataset_digest": self.source_dataset_digest,
                "source_observation_digest": self.source_observation_digest,
                "candidate_id": self.candidate_id,
                "chain_id": self.chain_id,
                "token_identity": self.token_identity,
                "reference_time": self.reference_time.isoformat(),
                "interpretation_status": self.interpretation_status.value,
                "source_outcome_status": self.source_outcome_status,
                "source_reconciliation_status": self.source_reconciliation_status,
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


@dataclass(frozen=True)
class OutcomeInterpretationSnapshot:
    """Immutable deterministic collection of P08-T03 interpretation results."""

    source_dataset_digest: str
    source_dataset_as_of_time: datetime
    results: tuple[OutcomeInterpretationResult, ...]
    result_digests: tuple[str, ...]
    source_dataset_contract_version: str = P08_T02_CONTRACT_VERSION
    contract_version: str = P08_T03_CONTRACT_VERSION
    evaluator_version: str = P08_T03_EVALUATOR_VERSION

    def __post_init__(self) -> None:
        _require_digest(self.source_dataset_digest, "source_dataset_digest")
        _require_text(
            self.source_dataset_contract_version,
            "source_dataset_contract_version",
        )
        _require_text(self.contract_version, "contract_version")
        _require_text(self.evaluator_version, "evaluator_version")

        if self.source_dataset_contract_version != P08_T02_CONTRACT_VERSION:
            raise ValueError("unsupported P08-T02 source contract version")

        if self.contract_version != P08_T03_CONTRACT_VERSION:
            raise ValueError("unsupported P08-T03 contract version")

        if self.evaluator_version != P08_T03_EVALUATOR_VERSION:
            raise ValueError("unsupported P08-T03 evaluator version")

        as_of_time = _to_utc(
            self.source_dataset_as_of_time,
            "source_dataset_as_of_time",
        )
        object.__setattr__(self, "source_dataset_as_of_time", as_of_time)

        results = tuple(self.results)

        if not results:
            raise ValueError("results must contain at least one result")

        source_observation_digests = set()

        for result in results:
            _validate_result(result)

            if result.source_dataset_digest != self.source_dataset_digest:
                raise ValueError(
                    "result source dataset digest does not match snapshot"
                )

            if result.source_observation_digest in source_observation_digests:
                raise ValueError(
                    "duplicate source observation digest"
                )
            source_observation_digests.add(result.source_observation_digest)

            if result.reference_time > as_of_time:
                raise ValueError(
                    "result reference_time is after source dataset cutoff"
                )

        ordered = tuple(
            sorted(
                results,
                key=lambda value: _canonical_json(
                    value.canonical_representation
                ),
            )
        )

        digests = tuple(result.digest for result in ordered)

        supplied_digests = tuple(self.result_digests)

        if supplied_digests != digests:
            raise ValueError(
                "result digests do not match canonical ordering"
            )

        _validate_unique_digests(digests)

        object.__setattr__(self, "results", ordered)
        object.__setattr__(self, "result_digests", digests)

    @property
    def result_count(self) -> int:
        return len(self.results)

    @property
    def interpretation_results(self) -> tuple[OutcomeInterpretationResult, ...]:
        return self.results

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "source_dataset_digest": self.source_dataset_digest,
                "source_dataset_as_of_time": self.source_dataset_as_of_time.isoformat(),
                "results": tuple(
                    result.canonical_representation
                    for result in self.results
                ),
                "result_digests": self.result_digests,
                "source_dataset_contract_version": self.source_dataset_contract_version,
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

    @property
    def snapshot_digest(self) -> str:
        return self.representation_digest


def interpret_outcome_learning_dataset(
    dataset: OutcomeLearningDatasetSnapshot,
) -> OutcomeInterpretationSnapshot:
    """Interpret exactly one validated T02 snapshot without economic analysis."""

    _validate_dataset(dataset)

    dataset_digest = dataset.digest

    results = tuple(
        _interpret_observation(
            dataset_digest=dataset_digest,
            observation=observation,
        )
        for observation in dataset.observations
    )

    if len(results) != dataset.observation_count:
        raise ValueError(
            "T03 result cardinality does not match source dataset"
        )

    return OutcomeInterpretationSnapshot(
        source_dataset_digest=dataset_digest,
        source_dataset_as_of_time=dataset.as_of_time,
        results=results,
        result_digests=tuple(result.digest for result in results),
    )


create_outcome_interpretation_snapshot = interpret_outcome_learning_dataset
interpret_outcomes = interpret_outcome_learning_dataset


def _interpret_observation(
    *,
    dataset_digest: str,
    observation: Any,
) -> OutcomeInterpretationResult:
    """Map source evidence state to the approved non-economic taxonomy."""

    source_outcome_status = observation.outcome_status
    source_reconciliation_status = observation.reconciliation_status

    if source_outcome_status == "UNAVAILABLE":
        status = OutcomeInterpretationStatus.UNAVAILABLE
    elif source_reconciliation_status == "UNKNOWN":
        status = OutcomeInterpretationStatus.UNKNOWN
    else:
        status = OutcomeInterpretationStatus.UNCLASSIFIED

    return OutcomeInterpretationResult(
        source_dataset_digest=dataset_digest,
        source_observation_digest=observation.digest,
        candidate_id=observation.candidate_id,
        chain_id=observation.chain_id,
        token_identity=observation.token_identity,
        reference_time=observation.simulation_reference_time,
        interpretation_status=status,
        source_outcome_status=source_outcome_status,
        source_reconciliation_status=source_reconciliation_status,
    )


def _validate_dataset(
    dataset: OutcomeLearningDatasetSnapshot,
) -> None:
    if not isinstance(dataset, OutcomeLearningDatasetSnapshot):
        raise ValueError(
            "dataset must be an OutcomeLearningDatasetSnapshot"
        )

    try:
        validated = OutcomeLearningDatasetSnapshot(
            observations=dataset.observations,
            as_of_time=dataset.as_of_time,
            observation_digests=dataset.observation_digests,
            observation_contract_version=dataset.observation_contract_version,
            observation_evaluator_version=dataset.observation_evaluator_version,
            contract_version=dataset.contract_version,
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError("OutcomeLearningDatasetSnapshot is invalid") from error

    if (
        validated != dataset
        or validated.canonical_representation
        != dataset.deterministic_representation
        or validated.digest != dataset.digest
    ):
        raise ValueError(
            "OutcomeLearningDatasetSnapshot is tampered or non-canonical"
        )


def _validate_result(value: Any) -> None:
    if not isinstance(value, OutcomeInterpretationResult):
        raise ValueError(
            "results must contain OutcomeInterpretationResult values"
        )

    try:
        validated = OutcomeInterpretationResult(
            source_dataset_digest=value.source_dataset_digest,
            source_observation_digest=value.source_observation_digest,
            candidate_id=value.candidate_id,
            chain_id=value.chain_id,
            token_identity=value.token_identity,
            reference_time=value.reference_time,
            interpretation_status=value.interpretation_status,
            source_outcome_status=value.source_outcome_status,
            source_reconciliation_status=value.source_reconciliation_status,
            contract_version=value.contract_version,
            evaluator_version=value.evaluator_version,
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "OutcomeInterpretationResult is invalid"
        ) from error

    if (
        validated != value
        or validated.canonical_representation
        != value.deterministic_representation
        or validated.digest != value.digest
    ):
        raise ValueError(
            "OutcomeInterpretationResult is tampered or non-canonical"
        )


def _validate_unique_digests(digests: tuple[str, ...]) -> None:
    for digest in digests:
        _require_digest(digest, "result digest")

    if len(set(digests)) != len(digests):
        raise ValueError("duplicate result digest")


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")


def _require_digest(value: Any, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != _DIGEST_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(
            f"{name} must be a lowercase SHA-256 digest"
        )


def _to_utc(value: Any, name: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{name} must be timezone-aware")

    return value.astimezone(timezone.utc)


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, datetime):
        return _to_utc(value, "timestamp").isoformat()

    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value, key=str)
        }

    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]

    raise ValueError(
        f"{type(value).__name__} cannot be deterministically serialized"
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                key: _freeze(child)
                for key, child in value.items()
            }
        )

    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)

    return value


__all__ = [
    "OutcomeInterpretationResult",
    "OutcomeInterpretationSnapshot",
    "OutcomeInterpretationStatus",
    "P08_T03_CONTRACT_VERSION",
    "P08_T03_EVALUATOR_VERSION",
    "create_outcome_interpretation_snapshot",
    "interpret_outcome_learning_dataset",
    "interpret_outcomes",
]
