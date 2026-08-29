"""Immutable, deterministic P08-T05 outcome-evidence snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Literal, Mapping

from core.learning.outcome_dataset import (
    P08_T02_CONTRACT_VERSION,
    OutcomeLearningDatasetSnapshot,
)
from core.learning.outcome_evidence import (
    P08_T04_CONTRACT_VERSION,
    P08_T04_EVALUATOR_VERSION,
    OutcomeEvidenceEvaluationResult,
)


P08_T05_CONTRACT_VERSION = "p08-t05-v1"
P08_T05_EVALUATOR_VERSION = "p08-t05-outcome-evidence-snapshot-v1"
_DIGEST_LENGTH = 64


@dataclass(frozen=True)
class OutcomeEvidenceEvaluationSnapshot:
    """A complete immutable collection of linked T04 evaluations."""

    source_dataset_digest: str
    source_dataset_as_of_time: datetime
    evaluations: tuple[OutcomeEvidenceEvaluationResult, ...]
    evaluation_digests: tuple[str, ...]
    source_evaluation_contract_version: Literal["p08-t04-v1"] = (
        P08_T04_CONTRACT_VERSION
    )
    source_evaluation_evaluator_version: Literal[
        "p08-t04-outcome-evidence-v1"
    ] = P08_T04_EVALUATOR_VERSION
    contract_version: Literal["p08-t05-v1"] = P08_T05_CONTRACT_VERSION
    evaluator_version: Literal[
        "p08-t05-outcome-evidence-snapshot-v1"
    ] = P08_T05_EVALUATOR_VERSION
    snapshot_digest: str = ""

    def __post_init__(self) -> None:
        _require_digest(self.source_dataset_digest, "source_dataset_digest")

        source_cutoff = _to_utc(
            self.source_dataset_as_of_time,
            "source_dataset_as_of_time",
        )
        object.__setattr__(self, "source_dataset_as_of_time", source_cutoff)

        _require_exact_version(
            self.source_evaluation_contract_version,
            P08_T04_CONTRACT_VERSION,
            "unsupported P08-T04 source contract version",
        )
        _require_exact_version(
            self.source_evaluation_evaluator_version,
            P08_T04_EVALUATOR_VERSION,
            "unsupported P08-T04 source evaluator version",
        )
        _require_exact_version(
            self.contract_version,
            P08_T05_CONTRACT_VERSION,
            "unsupported P08-T05 contract version",
        )
        _require_exact_version(
            self.evaluator_version,
            P08_T05_EVALUATOR_VERSION,
            "unsupported P08-T05 evaluator version",
        )

        if type(self.evaluations) is not tuple:
            raise ValueError("evaluations must be an exact tuple")
        if not self.evaluations:
            raise ValueError("evaluations must contain at least one evaluation")
        if type(self.evaluation_digests) is not tuple:
            raise ValueError("evaluation_digests must be an exact tuple")

        observation_digests: list[str] = []
        result_digests: list[str] = []
        for evaluation in self.evaluations:
            _validate_evaluation(evaluation)
            if evaluation.source_dataset_digest != self.source_dataset_digest:
                raise ValueError(
                    "evaluation source dataset digest does not match snapshot"
                )
            if evaluation.source_reference_time > source_cutoff:
                raise ValueError(
                    "evaluation source reference time is after dataset cutoff"
                )
            observation_digests.append(evaluation.source_observation_digest)
            result_digests.append(evaluation.result_digest)

        _validate_unique_digests(
            tuple(observation_digests),
            "source observation digest",
        )
        _validate_unique_digests(tuple(result_digests), "T04 result digest")

        ordered = tuple(
            sorted(
                self.evaluations,
                key=lambda value: value.source_observation_digest,
            )
        )
        if ordered != self.evaluations:
            raise ValueError(
                "evaluations do not match source_observation_digest ordering"
            )

        expected_digests = tuple(
            evaluation.result_digest for evaluation in self.evaluations
        )
        if self.evaluation_digests != expected_digests:
            raise ValueError(
                "evaluation digests do not match canonical ordering"
            )

        _require_digest(self.snapshot_digest, "snapshot_digest")
        if self.snapshot_digest != _digest(self.canonical_representation):
            raise ValueError("snapshot digest does not match canonical snapshot")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _canonical_snapshot_fields(
            source_dataset_digest=self.source_dataset_digest,
            source_dataset_as_of_time=self.source_dataset_as_of_time,
            evaluations=self.evaluations,
            evaluation_digests=self.evaluation_digests,
            source_evaluation_contract_version=(
                self.source_evaluation_contract_version
            ),
            source_evaluation_evaluator_version=(
                self.source_evaluation_evaluator_version
            ),
            contract_version=self.contract_version,
            evaluator_version=self.evaluator_version,
        )

    @property
    def deterministic_representation(self) -> Mapping[str, Any]:
        return self.canonical_representation


def create_outcome_evidence_evaluation_snapshot(
    dataset: OutcomeLearningDatasetSnapshot,
    evaluations: tuple[OutcomeEvidenceEvaluationResult, ...],
) -> OutcomeEvidenceEvaluationSnapshot:
    """Create one complete deterministic snapshot from T02 and T04 inputs."""

    _validate_dataset(dataset)
    if type(evaluations) is not tuple:
        raise ValueError(
            "evaluations must be an exact tuple of OutcomeEvidenceEvaluationResult values"
        )
    if not evaluations:
        raise ValueError("evaluations must contain at least one evaluation")

    for evaluation in evaluations:
        _validate_evaluation(evaluation)

    _validate_collection_linkage(dataset, evaluations)

    ordered = tuple(
        sorted(
            evaluations,
            key=lambda value: value.source_observation_digest,
        )
    )
    evaluation_digests = tuple(
        evaluation.result_digest for evaluation in ordered
    )
    fields = {
        "source_dataset_digest": dataset.digest,
        "source_dataset_as_of_time": dataset.as_of_time,
        "evaluations": ordered,
        "evaluation_digests": evaluation_digests,
        "source_evaluation_contract_version": P08_T04_CONTRACT_VERSION,
        "source_evaluation_evaluator_version": P08_T04_EVALUATOR_VERSION,
        "contract_version": P08_T05_CONTRACT_VERSION,
        "evaluator_version": P08_T05_EVALUATOR_VERSION,
    }
    return OutcomeEvidenceEvaluationSnapshot(
        **fields,
        snapshot_digest=_digest(
            _canonical_snapshot_fields(**fields)
        ),
    )


build_outcome_evidence_evaluation_snapshot = (
    create_outcome_evidence_evaluation_snapshot
)
snapshot_outcome_evidence_evaluations = (
    create_outcome_evidence_evaluation_snapshot
)


def _validate_collection_linkage(
    dataset: OutcomeLearningDatasetSnapshot,
    evaluations: tuple[OutcomeEvidenceEvaluationResult, ...],
) -> None:
    observation_digests = tuple(
        evaluation.source_observation_digest for evaluation in evaluations
    )
    result_digests = tuple(
        evaluation.result_digest for evaluation in evaluations
    )
    _validate_unique_digests(observation_digests, "source observation digest")
    _validate_unique_digests(result_digests, "T04 result digest")

    source_observations = {
        observation.digest: observation for observation in dataset.observations
    }
    expected_observation_digests = set(dataset.observation_digests)
    supplied_observation_digests = set(observation_digests)

    if supplied_observation_digests != expected_observation_digests:
        if supplied_observation_digests - expected_observation_digests:
            raise ValueError("T04 evaluation contains an extra observation")
        raise ValueError("T04 evaluation is missing an observation")

    if len(evaluations) != len(dataset.observations):
        raise ValueError("T02/T04 membership cardinality does not match")

    for evaluation in evaluations:
        observation = source_observations.get(
            evaluation.source_observation_digest
        )
        if observation is None:
            raise ValueError("T04 observation is not a member of T02 dataset")
        if evaluation.source_dataset_digest != dataset.digest:
            raise ValueError("T04 source dataset digest does not match T02 dataset")
        if evaluation.source_candidate_id != observation.candidate_id:
            raise ValueError("candidate identity provenance mismatch")
        if evaluation.source_chain_id != observation.chain_id:
            raise ValueError("chain identity provenance mismatch")
        if evaluation.source_token_identity != observation.token_identity:
            raise ValueError("token identity provenance mismatch")
        if (
            evaluation.source_reference_time
            != observation.simulation_reference_time
        ):
            raise ValueError("reference time provenance mismatch")
        if evaluation.source_paper_outcome_status != observation.outcome_status:
            raise ValueError("paper outcome provenance mismatch")
        if (
            evaluation.source_reconciliation_status
            != observation.reconciliation_status
        ):
            raise ValueError("reconciliation provenance mismatch")
        if evaluation.source_reference_time > dataset.as_of_time:
            raise ValueError("T04 source reference time is after T02 cutoff")


def _validate_dataset(value: OutcomeLearningDatasetSnapshot) -> None:
    if not isinstance(value, OutcomeLearningDatasetSnapshot):
        raise ValueError("dataset must be an OutcomeLearningDatasetSnapshot")
    try:
        validated = OutcomeLearningDatasetSnapshot(
            observations=value.observations,
            as_of_time=value.as_of_time,
            observation_digests=value.observation_digests,
            observation_contract_version=value.observation_contract_version,
            observation_evaluator_version=value.observation_evaluator_version,
            contract_version=value.contract_version,
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError("OutcomeLearningDatasetSnapshot is invalid") from error
    if (
        validated != value
        or validated.canonical_representation
        != value.deterministic_representation
        or validated.digest != value.digest
    ):
        raise ValueError("OutcomeLearningDatasetSnapshot is tampered or non-canonical")


def _validate_evaluation(value: Any) -> None:
    if not isinstance(value, OutcomeEvidenceEvaluationResult):
        raise ValueError(
            "evaluations must contain OutcomeEvidenceEvaluationResult values"
        )
    try:
        validated = OutcomeEvidenceEvaluationResult(
            source_interpretation_digest=value.source_interpretation_digest,
            source_dataset_digest=value.source_dataset_digest,
            source_observation_digest=value.source_observation_digest,
            source_paper_outcome_status=value.source_paper_outcome_status,
            source_reconciliation_status=value.source_reconciliation_status,
            evidence_state=value.evidence_state,
            reason_codes=value.reason_codes,
            source_candidate_id=value.source_candidate_id,
            source_chain_id=value.source_chain_id,
            source_token_identity=value.source_token_identity,
            source_reference_time=value.source_reference_time,
            source_interpretation_contract_version=(
                value.source_interpretation_contract_version
            ),
            source_interpretation_evaluator_version=(
                value.source_interpretation_evaluator_version
            ),
            contract_version=value.contract_version,
            evaluator_version=value.evaluator_version,
            result_digest=value.result_digest,
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError("OutcomeEvidenceEvaluationResult is invalid") from error
    if (
        validated != value
        or validated.canonical_representation
        != value.deterministic_representation
        or validated.result_digest != value.result_digest
    ):
        raise ValueError(
            "OutcomeEvidenceEvaluationResult is tampered or non-canonical"
        )


def _canonical_snapshot_fields(
    *,
    source_dataset_digest: str,
    source_dataset_as_of_time: datetime,
    evaluations: tuple[OutcomeEvidenceEvaluationResult, ...],
    evaluation_digests: tuple[str, ...],
    source_evaluation_contract_version: str,
    source_evaluation_evaluator_version: str,
    contract_version: str,
    evaluator_version: str,
) -> Mapping[str, Any]:
    return _freeze(
        {
            "source_dataset_digest": source_dataset_digest,
            "source_dataset_as_of_time": _to_utc(
                source_dataset_as_of_time,
                "source_dataset_as_of_time",
            ).isoformat(),
            "evaluations": tuple(
                evaluation.canonical_representation
                for evaluation in evaluations
            ),
            "evaluation_digests": evaluation_digests,
            "source_evaluation_contract_version": (
                source_evaluation_contract_version
            ),
            "source_evaluation_evaluator_version": (
                source_evaluation_evaluator_version
            ),
            "contract_version": contract_version,
            "evaluator_version": evaluator_version,
        }
    )


def _validate_unique_digests(
    digests: tuple[str, ...],
    name: str,
) -> None:
    for digest in digests:
        _require_digest(digest, name)
    if len(set(digests)) != len(digests):
        raise ValueError(f"duplicate {name}")


def _require_exact_version(value: Any, expected: str, message: str) -> None:
    if value != expected:
        raise ValueError(message)


def _require_digest(value: Any, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != _DIGEST_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


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
    raise ValueError(f"{type(value).__name__} cannot be deterministically serialized")


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
            {key: _freeze(child) for key, child in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


__all__ = [
    "OutcomeEvidenceEvaluationSnapshot",
    "P08_T05_CONTRACT_VERSION",
    "P08_T05_EVALUATOR_VERSION",
    "build_outcome_evidence_evaluation_snapshot",
    "create_outcome_evidence_evaluation_snapshot",
    "snapshot_outcome_evidence_evaluations",
]