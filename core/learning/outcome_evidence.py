"""Immutable, deterministic P08-T04 outcome-evidence evaluation boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, Literal

from core.learning.outcome_dataset import (
    P08_T02_CONTRACT_VERSION,
    OutcomeLearningDatasetSnapshot,
)
from core.learning.outcome_interpretation import (
    P08_T03_CONTRACT_VERSION,
    P08_T03_EVALUATOR_VERSION,
    OutcomeInterpretationResult,
    OutcomeInterpretationStatus,
)


P08_T04_CONTRACT_VERSION = "p08-t04-v1"
P08_T04_EVALUATOR_VERSION = "p08-t04-outcome-evidence-v1"
_DIGEST_LENGTH = 64


class OutcomeEvidenceState(str, Enum):
    """Evidence sufficiency state, never an economic outcome."""

    UNCLASSIFIED = "UNCLASSIFIED"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"
    INCOMPLETE = "INCOMPLETE"


class OutcomeEvidenceReasonCode(str, Enum):
    """The fixed, deterministic T04 reason-code vocabulary."""

    LINKAGE_VALID = "LINKAGE_VALID"
    STATE_UNCLASSIFIED_PRESERVED = "STATE_UNCLASSIFIED_PRESERVED"
    STATE_UNKNOWN_PRESERVED = "STATE_UNKNOWN_PRESERVED"
    STATE_UNAVAILABLE_PRESERVED = "STATE_UNAVAILABLE_PRESERVED"
    STATE_INCOMPLETE_PRESERVED = "STATE_INCOMPLETE_PRESERVED"


@dataclass(frozen=True)
class OutcomeEvidenceEvaluationResult:
    """One immutable evaluation of one validated T03 interpretation."""

    source_interpretation_digest: str
    source_dataset_digest: str
    source_observation_digest: str
    source_paper_outcome_status: str
    source_reconciliation_status: str
    evidence_state: OutcomeEvidenceState
    reason_codes: tuple[OutcomeEvidenceReasonCode, ...]
    source_candidate_id: str
    source_chain_id: str
    source_token_identity: str
    source_reference_time: datetime
    source_interpretation_contract_version: Literal["p08-t03-v1"]
    source_interpretation_evaluator_version: str
    contract_version: Literal["p08-t04-v1"] = P08_T04_CONTRACT_VERSION
    evaluator_version: Literal[
        "p08-t04-outcome-evidence-v1"
    ] = P08_T04_EVALUATOR_VERSION
    result_digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "source_interpretation_digest",
            "source_dataset_digest",
            "source_observation_digest",
        ):
            _require_digest(getattr(self, name), name)

        for name in (
            "source_paper_outcome_status",
            "source_reconciliation_status",
            "source_candidate_id",
            "source_chain_id",
            "source_token_identity",
            "source_interpretation_evaluator_version",
        ):
            _require_text(getattr(self, name), name)

        reference_time = _to_utc(
            self.source_reference_time,
            "source_reference_time",
        )
        object.__setattr__(self, "source_reference_time", reference_time)

        if self.source_interpretation_contract_version != P08_T03_CONTRACT_VERSION:
            raise ValueError("unsupported P08-T03 source contract version")
        if self.source_interpretation_evaluator_version != P08_T03_EVALUATOR_VERSION:
            raise ValueError("unsupported P08-T03 source evaluator version")
        if self.contract_version != P08_T04_CONTRACT_VERSION:
            raise ValueError("unsupported P08-T04 contract version")
        if self.evaluator_version != P08_T04_EVALUATOR_VERSION:
            raise ValueError("unsupported P08-T04 evaluator version")

        try:
            evidence_state = OutcomeEvidenceState(self.evidence_state)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported evidence state") from error
        object.__setattr__(self, "evidence_state", evidence_state)

        try:
            reason_codes = tuple(
                OutcomeEvidenceReasonCode(code) for code in self.reason_codes
            )
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported reason code") from error
        expected_reason_codes = _reason_codes_for(evidence_state)
        if reason_codes != expected_reason_codes:
            raise ValueError("reason codes are not deterministic for evidence state")
        object.__setattr__(self, "reason_codes", reason_codes)

        _require_digest(self.result_digest, "result_digest")
        if self.result_digest != _digest(self.canonical_representation):
            raise ValueError("result digest does not match canonical result")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "source_interpretation_digest": self.source_interpretation_digest,
                "source_dataset_digest": self.source_dataset_digest,
                "source_observation_digest": self.source_observation_digest,
                "source_paper_outcome_status": self.source_paper_outcome_status,
                "source_reconciliation_status": self.source_reconciliation_status,
                "evidence_state": self.evidence_state.value,
                "reason_codes": tuple(code.value for code in self.reason_codes),
                "source_candidate_id": self.source_candidate_id,
                "source_chain_id": self.source_chain_id,
                "source_token_identity": self.source_token_identity,
                "source_reference_time": self.source_reference_time.isoformat(),
                "source_interpretation_contract_version": (
                    self.source_interpretation_contract_version
                ),
                "source_interpretation_evaluator_version": (
                    self.source_interpretation_evaluator_version
                ),
                "contract_version": self.contract_version,
                "evaluator_version": self.evaluator_version,
            }
        )

    @property
    def deterministic_representation(self) -> Mapping[str, Any]:
        return self.canonical_representation


def evaluate_outcome_evidence(
    interpretation: OutcomeInterpretationResult,
    dataset: OutcomeLearningDatasetSnapshot,
) -> OutcomeEvidenceEvaluationResult:
    """Evaluate one T03 result against its linked T02 snapshot."""

    _validate_dataset(dataset)
    _validate_interpretation(interpretation)

    if interpretation.source_dataset_digest != dataset.digest:
        raise ValueError("source dataset digest does not match dataset")

    matches = tuple(
        observation
        for observation in dataset.observations
        if observation.digest == interpretation.source_observation_digest
    )
    if len(matches) != 1:
        raise ValueError("source observation must resolve to exactly one observation")
    observation = matches[0]

    if observation.digest != interpretation.source_observation_digest:
        raise ValueError("source observation digest mismatch")
    if observation.digest not in dataset.observation_digests:
        raise ValueError("source observation is not a member of dataset")
    if observation.simulation_reference_time > dataset.as_of_time:
        raise ValueError("source observation is after dataset cutoff")

    _require_equal(
        interpretation.candidate_id,
        observation.candidate_id,
        "candidate identity provenance mismatch",
    )
    _require_equal(
        interpretation.chain_id,
        observation.chain_id,
        "chain identity provenance mismatch",
    )
    _require_equal(
        interpretation.token_identity,
        observation.token_identity,
        "token identity provenance mismatch",
    )
    _require_equal(
        interpretation.reference_time,
        observation.simulation_reference_time,
        "reference time provenance mismatch",
    )
    _require_equal(
        interpretation.source_outcome_status,
        observation.outcome_status,
        "paper outcome provenance mismatch",
    )
    _require_equal(
        interpretation.source_reconciliation_status,
        observation.reconciliation_status,
        "reconciliation provenance mismatch",
    )

    evidence_state = OutcomeEvidenceState(
        interpretation.interpretation_status.value
    )
    fields = {
        "source_interpretation_digest": interpretation.digest,
        "source_dataset_digest": dataset.digest,
        "source_observation_digest": observation.digest,
        "source_paper_outcome_status": observation.outcome_status,
        "source_reconciliation_status": observation.reconciliation_status,
        "evidence_state": evidence_state,
        "reason_codes": _reason_codes_for(evidence_state),
        "source_candidate_id": observation.candidate_id,
        "source_chain_id": observation.chain_id,
        "source_token_identity": observation.token_identity,
        "source_reference_time": observation.simulation_reference_time,
        "source_interpretation_contract_version": (
            interpretation.contract_version
        ),
        "source_interpretation_evaluator_version": (
            interpretation.evaluator_version
        ),
        "contract_version": P08_T04_CONTRACT_VERSION,
        "evaluator_version": P08_T04_EVALUATOR_VERSION,
    }
    canonical_fields = {
        **fields,
        "source_reference_time": _to_utc(
            fields["source_reference_time"],
            "source_reference_time",
        ).isoformat(),
    }
    canonical_fields["evidence_state"] = evidence_state.value
    canonical_fields["reason_codes"] = tuple(
        code.value for code in fields["reason_codes"]
    )
    return OutcomeEvidenceEvaluationResult(
        **fields,
        result_digest=_digest(canonical_fields),
    )


create_outcome_evidence_evaluation = evaluate_outcome_evidence
evaluate_outcome_interpretation_evidence = evaluate_outcome_evidence


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


def _validate_interpretation(value: OutcomeInterpretationResult) -> None:
    if not isinstance(value, OutcomeInterpretationResult):
        raise ValueError("interpretation must be an OutcomeInterpretationResult")
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
        raise ValueError("OutcomeInterpretationResult is invalid") from error
    if (
        validated != value
        or validated.canonical_representation
        != value.deterministic_representation
        or validated.digest != value.digest
    ):
        raise ValueError("OutcomeInterpretationResult is tampered or non-canonical")


def _reason_codes_for(
    state: OutcomeEvidenceState,
) -> tuple[OutcomeEvidenceReasonCode, OutcomeEvidenceReasonCode]:
    state_code = {
        OutcomeEvidenceState.UNCLASSIFIED:
            OutcomeEvidenceReasonCode.STATE_UNCLASSIFIED_PRESERVED,
        OutcomeEvidenceState.UNKNOWN:
            OutcomeEvidenceReasonCode.STATE_UNKNOWN_PRESERVED,
        OutcomeEvidenceState.UNAVAILABLE:
            OutcomeEvidenceReasonCode.STATE_UNAVAILABLE_PRESERVED,
        OutcomeEvidenceState.INCOMPLETE:
            OutcomeEvidenceReasonCode.STATE_INCOMPLETE_PRESERVED,
    }[state]
    return (OutcomeEvidenceReasonCode.LINKAGE_VALID, state_code)


def _require_equal(left: Any, right: Any, message: str) -> None:
    if left != right:
        raise ValueError(message)


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
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(child) for key, child in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


__all__ = [
    "OutcomeEvidenceEvaluationResult",
    "OutcomeEvidenceReasonCode",
    "OutcomeEvidenceState",
    "P08_T04_CONTRACT_VERSION",
    "P08_T04_EVALUATOR_VERSION",
    "create_outcome_evidence_evaluation",
    "evaluate_outcome_evidence",
    "evaluate_outcome_interpretation_evidence",
]