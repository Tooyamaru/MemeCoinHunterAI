"""Immutable, deterministic P08-T06 outcome-analysis readiness boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Literal, Mapping

from core.learning.outcome_evidence import (
    OutcomeEvidenceState,
    P08_T04_CONTRACT_VERSION,
    P08_T04_EVALUATOR_VERSION,
)
from core.learning.outcome_evidence_snapshot import (
    OutcomeEvidenceEvaluationSnapshot,
    P08_T05_CONTRACT_VERSION,
    P08_T05_EVALUATOR_VERSION,
)


P08_T06_CONTRACT_VERSION = "p08-t06-v1"
P08_T06_EVALUATOR_VERSION = "p08-t06-evidence-analysis-readiness-v1"
_DIGEST_LENGTH = 64


class OutcomeLearningReadinessState(str, Enum):
    """Structural readiness for non-economic analysis only."""

    READY_FOR_NON_ECONOMIC_ANALYSIS = "READY_FOR_NON_ECONOMIC_ANALYSIS"
    NOT_READY_FOR_NON_ECONOMIC_ANALYSIS = "NOT_READY_FOR_NON_ECONOMIC_ANALYSIS"


class OutcomeLearningReadinessReasonCode(str, Enum):
    """The fixed, deterministic T06 reason-code vocabulary."""

    SOURCE_SNAPSHOT_VALID = "SOURCE_SNAPSHOT_VALID"
    ALL_T04_STATES_UNCLASSIFIED = "ALL_T04_STATES_UNCLASSIFIED"
    T04_UNKNOWN_PRESENT = "T04_UNKNOWN_PRESENT"
    T04_UNAVAILABLE_PRESENT = "T04_UNAVAILABLE_PRESENT"
    T04_INCOMPLETE_PRESENT = "T04_INCOMPLETE_PRESENT"
    ANALYSIS_READINESS_GRANTED = "ANALYSIS_READINESS_GRANTED"
    ANALYSIS_READINESS_BLOCKED = "ANALYSIS_READINESS_BLOCKED"


@dataclass(frozen=True)
class OutcomeLearningReadinessResult:
    """One immutable structural readiness result for a validated T05 snapshot."""

    source_snapshot_digest: str
    source_dataset_digest: str
    source_dataset_as_of_time: datetime
    readiness_state: OutcomeLearningReadinessState
    reason_codes: tuple[OutcomeLearningReadinessReasonCode, ...]
    source_evaluation_contract_version: Literal["p08-t04-v1"]
    source_evaluation_evaluator_version: Literal[
        "p08-t04-outcome-evidence-v1"
    ]
    source_snapshot_contract_version: Literal["p08-t05-v1"]
    source_snapshot_evaluator_version: Literal[
        "p08-t05-outcome-evidence-snapshot-v1"
    ]
    contract_version: Literal["p08-t06-v1"] = P08_T06_CONTRACT_VERSION
    evaluator_version: Literal[
        "p08-t06-evidence-analysis-readiness-v1"
    ] = P08_T06_EVALUATOR_VERSION
    result_digest: str = ""

    def __post_init__(self) -> None:
        _require_digest(self.source_snapshot_digest, "source_snapshot_digest")
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
            self.source_snapshot_contract_version,
            P08_T05_CONTRACT_VERSION,
            "unsupported P08-T05 source contract version",
        )
        _require_exact_version(
            self.source_snapshot_evaluator_version,
            P08_T05_EVALUATOR_VERSION,
            "unsupported P08-T05 source evaluator version",
        )
        _require_exact_version(
            self.contract_version,
            P08_T06_CONTRACT_VERSION,
            "unsupported P08-T06 contract version",
        )
        _require_exact_version(
            self.evaluator_version,
            P08_T06_EVALUATOR_VERSION,
            "unsupported P08-T06 evaluator version",
        )

        try:
            readiness_state = OutcomeLearningReadinessState(
                self.readiness_state
            )
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported readiness state") from error
        object.__setattr__(self, "readiness_state", readiness_state)

        if type(self.reason_codes) is not tuple:
            raise ValueError("reason_codes must be an exact tuple")
        try:
            reason_codes = tuple(
                OutcomeLearningReadinessReasonCode(code)
                for code in self.reason_codes
            )
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported readiness reason code") from error
        if not _reason_codes_are_valid(readiness_state, reason_codes):
            raise ValueError("reason codes are not deterministic for readiness state")
        object.__setattr__(self, "reason_codes", reason_codes)

        _require_digest(self.result_digest, "result_digest")
        if self.result_digest != _digest(self.canonical_representation):
            raise ValueError("result digest does not match canonical result")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "source_snapshot_digest": self.source_snapshot_digest,
                "source_dataset_digest": self.source_dataset_digest,
                "source_dataset_as_of_time": (
                    self.source_dataset_as_of_time.isoformat()
                ),
                "readiness_state": self.readiness_state.value,
                "reason_codes": tuple(code.value for code in self.reason_codes),
                "source_evaluation_contract_version": (
                    self.source_evaluation_contract_version
                ),
                "source_evaluation_evaluator_version": (
                    self.source_evaluation_evaluator_version
                ),
                "source_snapshot_contract_version": (
                    self.source_snapshot_contract_version
                ),
                "source_snapshot_evaluator_version": (
                    self.source_snapshot_evaluator_version
                ),
                "contract_version": self.contract_version,
                "evaluator_version": self.evaluator_version,
            }
        )

    @property
    def deterministic_representation(self) -> Mapping[str, Any]:
        return self.canonical_representation


def evaluate_outcome_learning_readiness(
    snapshot: OutcomeEvidenceEvaluationSnapshot,
) -> OutcomeLearningReadinessResult:
    """Evaluate structural readiness from exactly one validated T05 snapshot."""

    _validate_snapshot(snapshot)

    states = {evaluation.evidence_state for evaluation in snapshot.evaluations}
    blocking_states = {
        OutcomeEvidenceState.UNKNOWN,
        OutcomeEvidenceState.UNAVAILABLE,
        OutcomeEvidenceState.INCOMPLETE,
    }

    if not states - {OutcomeEvidenceState.UNCLASSIFIED}:
        readiness_state = (
            OutcomeLearningReadinessState.READY_FOR_NON_ECONOMIC_ANALYSIS
        )
        reason_codes = (
            OutcomeLearningReadinessReasonCode.SOURCE_SNAPSHOT_VALID,
            OutcomeLearningReadinessReasonCode.ALL_T04_STATES_UNCLASSIFIED,
            OutcomeLearningReadinessReasonCode.ANALYSIS_READINESS_GRANTED,
        )
    else:
        readiness_state = (
            OutcomeLearningReadinessState.NOT_READY_FOR_NON_ECONOMIC_ANALYSIS
        )
        state_reason_codes = {
            OutcomeEvidenceState.UNKNOWN: (
                OutcomeLearningReadinessReasonCode.T04_UNKNOWN_PRESENT
            ),
            OutcomeEvidenceState.UNAVAILABLE: (
                OutcomeLearningReadinessReasonCode.T04_UNAVAILABLE_PRESENT
            ),
            OutcomeEvidenceState.INCOMPLETE: (
                OutcomeLearningReadinessReasonCode.T04_INCOMPLETE_PRESENT
            ),
        }
        reason_codes = (
            OutcomeLearningReadinessReasonCode.SOURCE_SNAPSHOT_VALID,
            *tuple(
                state_reason_codes[state]
                for state in (
                    OutcomeEvidenceState.UNKNOWN,
                    OutcomeEvidenceState.UNAVAILABLE,
                    OutcomeEvidenceState.INCOMPLETE,
                )
                if state in states
            ),
            OutcomeLearningReadinessReasonCode.ANALYSIS_READINESS_BLOCKED,
        )

    fields = {
        "source_snapshot_digest": snapshot.snapshot_digest,
        "source_dataset_digest": snapshot.source_dataset_digest,
        "source_dataset_as_of_time": snapshot.source_dataset_as_of_time,
        "readiness_state": readiness_state,
        "reason_codes": reason_codes,
        "source_evaluation_contract_version": (
            snapshot.source_evaluation_contract_version
        ),
        "source_evaluation_evaluator_version": (
            snapshot.source_evaluation_evaluator_version
        ),
        "source_snapshot_contract_version": snapshot.contract_version,
        "source_snapshot_evaluator_version": snapshot.evaluator_version,
        "contract_version": P08_T06_CONTRACT_VERSION,
        "evaluator_version": P08_T06_EVALUATOR_VERSION,
    }
    return OutcomeLearningReadinessResult(
        **fields,
        result_digest=_digest(_canonical_result_fields(**fields)),
    )


def _reason_codes_for(
    state: OutcomeLearningReadinessState,
) -> tuple[
    OutcomeLearningReadinessReasonCode,
    ...,
]:
    if state is OutcomeLearningReadinessState.READY_FOR_NON_ECONOMIC_ANALYSIS:
        return (
            OutcomeLearningReadinessReasonCode.SOURCE_SNAPSHOT_VALID,
            OutcomeLearningReadinessReasonCode.ALL_T04_STATES_UNCLASSIFIED,
            OutcomeLearningReadinessReasonCode.ANALYSIS_READINESS_GRANTED,
        )
    return (
        OutcomeLearningReadinessReasonCode.SOURCE_SNAPSHOT_VALID,
        OutcomeLearningReadinessReasonCode.ANALYSIS_READINESS_BLOCKED,
    )


def _validate_snapshot(value: Any) -> None:
    if not isinstance(value, OutcomeEvidenceEvaluationSnapshot):
        raise ValueError(
            "snapshot must be an OutcomeEvidenceEvaluationSnapshot"
        )

    if (
        not isinstance(value.source_dataset_as_of_time, datetime)
        or value.source_dataset_as_of_time.tzinfo is not timezone.utc
    ):
        raise ValueError(
            "OutcomeEvidenceEvaluationSnapshot cutoff is not canonical UTC"
        )

    try:
        validated = OutcomeEvidenceEvaluationSnapshot(
            source_dataset_digest=value.source_dataset_digest,
            source_dataset_as_of_time=value.source_dataset_as_of_time,
            evaluations=value.evaluations,
            evaluation_digests=value.evaluation_digests,
            source_evaluation_contract_version=(
                value.source_evaluation_contract_version
            ),
            source_evaluation_evaluator_version=(
                value.source_evaluation_evaluator_version
            ),
            contract_version=value.contract_version,
            evaluator_version=value.evaluator_version,
            snapshot_digest=value.snapshot_digest,
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "OutcomeEvidenceEvaluationSnapshot is invalid"
        ) from error

    if (
        validated != value
        or validated.canonical_representation
        != value.deterministic_representation
        or validated.snapshot_digest != value.snapshot_digest
    ):
        raise ValueError(
            "OutcomeEvidenceEvaluationSnapshot is tampered or non-canonical"
        )


def _canonical_result_fields(
    *,
    source_snapshot_digest: str,
    source_dataset_digest: str,
    source_dataset_as_of_time: datetime,
    readiness_state: OutcomeLearningReadinessState,
    reason_codes: tuple[OutcomeLearningReadinessReasonCode, ...],
    source_evaluation_contract_version: str,
    source_evaluation_evaluator_version: str,
    source_snapshot_contract_version: str,
    source_snapshot_evaluator_version: str,
    contract_version: str,
    evaluator_version: str,
) -> Mapping[str, Any]:
    return {
        "source_snapshot_digest": source_snapshot_digest,
        "source_dataset_digest": source_dataset_digest,
        "source_dataset_as_of_time": _to_utc(
            source_dataset_as_of_time,
            "source_dataset_as_of_time",
        ).isoformat(),
        "readiness_state": readiness_state.value,
        "reason_codes": tuple(code.value for code in reason_codes),
        "source_evaluation_contract_version": source_evaluation_contract_version,
        "source_evaluation_evaluator_version": source_evaluation_evaluator_version,
        "source_snapshot_contract_version": source_snapshot_contract_version,
        "source_snapshot_evaluator_version": source_snapshot_evaluator_version,
        "contract_version": contract_version,
        "evaluator_version": evaluator_version,
    }


def _reason_codes_are_valid(
    state: OutcomeLearningReadinessState,
    reason_codes: tuple[OutcomeLearningReadinessReasonCode, ...],
) -> bool:
    if state is OutcomeLearningReadinessState.READY_FOR_NON_ECONOMIC_ANALYSIS:
        return reason_codes == _reason_codes_for(state)

    if (
        len(reason_codes) < 3
        or reason_codes[0]
        is not OutcomeLearningReadinessReasonCode.SOURCE_SNAPSHOT_VALID
        or reason_codes[-1]
        is not OutcomeLearningReadinessReasonCode.ANALYSIS_READINESS_BLOCKED
    ):
        return False

    blocking_codes = (
        OutcomeLearningReadinessReasonCode.T04_UNKNOWN_PRESENT,
        OutcomeLearningReadinessReasonCode.T04_UNAVAILABLE_PRESENT,
        OutcomeLearningReadinessReasonCode.T04_INCOMPLETE_PRESENT,
    )
    middle = reason_codes[1:-1]
    return bool(middle) and middle == tuple(
        code for code in blocking_codes if code in middle
    )


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
    "OutcomeLearningReadinessReasonCode",
    "OutcomeLearningReadinessResult",
    "OutcomeLearningReadinessState",
    "P08_T06_CONTRACT_VERSION",
    "P08_T06_EVALUATOR_VERSION",
    "evaluate_outcome_learning_readiness",
]