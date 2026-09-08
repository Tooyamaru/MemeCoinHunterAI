"""Immutable, deterministic P08-T07 economic outcome assembly boundary.

This module consumes materialized G2, G3, and G4 decisions.  It does not
collect evidence, calculate accounting, classify performance, or perform any
external operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Literal, Mapping


P08_T07_CONTRACT_VERSION = "p08-t07-v1"
P08_T07_EVALUATOR_VERSION = "p08-t07-evaluator-v1"
_DIGEST_LENGTH = 64


class EconomicOutcomeInterpretationStatus(str, Enum):
    """The bounded primary T07 interpretation status."""

    VALID = "VALID"
    NOT_REALIZED = "NOT_REALIZED"
    INVALID_INPUT = "INVALID_INPUT"


class EconomicOutcomeFailureReason(str, Enum):
    """The bounded machine-readable T07 failure vocabulary."""

    MISSING_REQUIRED_INPUT = "MISSING_REQUIRED_INPUT"
    NON_REALIZED_LIFECYCLE = "NON_REALIZED_LIFECYCLE"
    INVALID_G2 = "INVALID_G2"
    INVALID_G3 = "INVALID_G3"
    INVALID_G4 = "INVALID_G4"
    PROVENANCE_LINKAGE_FAILURE = "PROVENANCE_LINKAGE_FAILURE"
    DIGEST_FAILURE = "DIGEST_FAILURE"
    CONFLICTING_INPUT = "CONFLICTING_INPUT"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    UNRESOLVED_CORRECTION = "UNRESOLVED_CORRECTION"
    UNRESOLVED_SUPERSESSION = "UNRESOLVED_SUPERSESSION"
    UNRESOLVED_RESIDUAL = "UNRESOLVED_RESIDUAL"
    NUMERIC_INVALID = "NUMERIC_INVALID"


class G2RealizationState(str, Enum):
    """Materialized G2 realization/settlement eligibility states."""

    REALIZED_ELIGIBLE = "REALIZED_ELIGIBLE"
    NON_FINAL = "NON_FINAL"
    SETTLEMENT_PENDING = "SETTLEMENT_PENDING"
    SETTLED_BUT_NOT_REALIZED_ELIGIBLE = (
        "SETTLED_BUT_NOT_REALIZED_ELIGIBLE"
    )
    SETTLED_NOT_REALIZED_ELIGIBLE = "SETTLED_NOT_REALIZED_ELIGIBLE"
    INVALID = "INVALID"
    UNRESOLVED = "UNRESOLVED"


class G3Validity(str, Enum):
    """Materialized G3 validity states accepted by the assembly boundary."""

    VALID_REALIZED_ECONOMIC_RESULT = "VALID_REALIZED_ECONOMIC_RESULT"
    VALID = "VALID"
    NOT_REALIZED = "NOT_REALIZED"
    INVALID = "INVALID"


class G4Validity(str, Enum):
    """Materialized G4 validity states accepted by the assembly boundary."""

    VALID_CANONICAL_CLASSIFICATION = "VALID_CANONICAL_CLASSIFICATION"
    VALID = "VALID"
    NOT_REALIZED = "NOT_REALIZED"
    INVALID = "INVALID"


class PerformanceClassification(str, Enum):
    """The only canonical performance classifications."""

    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"


_NON_REALIZED_G2_STATES = {
    G2RealizationState.NON_FINAL,
    G2RealizationState.SETTLEMENT_PENDING,
    G2RealizationState.SETTLED_BUT_NOT_REALIZED_ELIGIBLE,
    G2RealizationState.SETTLED_NOT_REALIZED_ELIGIBLE,
}
_VALID_G3_STATES = {
    G3Validity.VALID_REALIZED_ECONOMIC_RESULT,
    G3Validity.VALID,
}
_VALID_G4_STATES = {
    G4Validity.VALID_CANONICAL_CLASSIFICATION,
    G4Validity.VALID,
}


@dataclass(frozen=True)
class EconomicOutcomeInterpretationInput:
    """The smallest immutable input envelope needed to assemble one result.

    Fields default to ``None`` so a syntactically valid invocation can return
    an explicit ``INVALID_INPUT`` result for missing required material.
    """

    decision_intent_id: str | None = None
    lifecycle_id: str | None = None
    observation_id: str | None = None
    dataset_snapshot_id: str | None = None
    evidence_evaluation_snapshot_id: str | None = None
    readiness_result_id: str | None = None
    g2_result_id: str | None = None
    g2_state: G2RealizationState | str | None = None
    g2_policy_version: str | None = None
    g2_result_digest: str | None = None
    g2_provenance: Mapping[str, Any] | tuple[Any, ...] | None = None
    g3_result_id: str | None = None
    g3_validity: G3Validity | str | None = None
    realized_economic_result: Any = None
    canonical_numeraire: str | None = None
    g3_policy_version: str | None = None
    g3_result_digest: str | None = None
    g3_provenance: Mapping[str, Any] | tuple[Any, ...] | None = None
    g4_result_id: str | None = None
    g4_validity: G4Validity | str | None = None
    classification: PerformanceClassification | str | None = None
    g4_policy_version: str | None = None
    g4_result_digest: str | None = None
    g4_provenance: Mapping[str, Any] | tuple[Any, ...] | None = None
    evidence_digest: str | None = None
    evidence_references: tuple[str, ...] = ()
    authority_references: tuple[str, ...] = ()
    source_references: tuple[str, ...] = ()
    correction_lineage: tuple[str, ...] = ()
    supersession_lineage: tuple[str, ...] = ()
    canonical_timestamps: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        for name in (
            "g2_provenance",
            "g3_provenance",
            "g4_provenance",
            "canonical_timestamps",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _freeze(value))

        for name in (
            "evidence_references",
            "authority_references",
            "source_references",
            "correction_lineage",
            "supersession_lineage",
        ):
            value = getattr(self, name)
            if isinstance(value, (list, tuple)):
                object.__setattr__(self, name, tuple(_freeze(item) for item in value))


@dataclass(frozen=True)
class EconomicOutcomeInterpretationResult:
    """One immutable canonical interpretation assembled from G2/G3/G4."""

    contract_version: Literal["p08-t07-v1"]
    evaluator_version: Literal["p08-t07-evaluator-v1"]
    decision_intent_id: str | None
    lifecycle_id: str | None
    status: EconomicOutcomeInterpretationStatus
    failure_reason: EconomicOutcomeFailureReason | None
    realization_eligibility: Literal[
        "REALIZED_ELIGIBLE",
        "NOT_REALIZED_ELIGIBLE",
    ] | None
    realized_economic_result: str | None
    canonical_numeraire: str | None
    performance_classification: PerformanceClassification | None
    g2_result_id: str | None
    g2_policy_version: str | None
    g2_result_digest: str | None
    g3_result_id: str | None
    g3_policy_version: str | None
    g3_result_digest: str | None
    g4_result_id: str | None
    g4_policy_version: str | None
    g4_result_digest: str | None
    evidence_digest: str | None
    provenance: Mapping[str, Any] | None
    correction_lineage: tuple[str, ...] | None
    supersession_lineage: tuple[str, ...] | None
    result_digest: str
    classification_digest: str | None

    def __post_init__(self) -> None:
        if self.contract_version != P08_T07_CONTRACT_VERSION:
            raise ValueError("unsupported P08-T07 contract version")
        if self.evaluator_version != P08_T07_EVALUATOR_VERSION:
            raise ValueError("unsupported P08-T07 evaluator version")

        status = _coerce_enum(
            self.status,
            EconomicOutcomeInterpretationStatus,
            "status",
        )
        object.__setattr__(self, "status", status)

        if self.failure_reason is not None:
            failure_reason = _coerce_enum(
                self.failure_reason,
                EconomicOutcomeFailureReason,
                "failure_reason",
            )
            object.__setattr__(self, "failure_reason", failure_reason)

        if self.performance_classification is not None:
            classification = _coerce_enum(
                self.performance_classification,
                PerformanceClassification,
                "performance_classification",
            )
            object.__setattr__(self, "performance_classification", classification)

        if self.realization_eligibility is not None:
            if self.realization_eligibility not in {
                "REALIZED_ELIGIBLE",
                "NOT_REALIZED_ELIGIBLE",
            }:
                raise ValueError("unsupported realization eligibility")

        for name in (
            "decision_intent_id",
            "lifecycle_id",
            "g2_result_id",
            "g2_policy_version",
            "g3_result_id",
            "g3_policy_version",
            "g4_result_id",
            "g4_policy_version",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_text(value, name)

        for name in (
            "g2_result_digest",
            "g3_result_digest",
            "g4_result_digest",
            "evidence_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_digest(value, name)

        if self.realized_economic_result is not None:
            object.__setattr__(
                self,
                "realized_economic_result",
                _canonical_decimal(self.realized_economic_result),
            )

        if self.canonical_numeraire is not None:
            _require_text(self.canonical_numeraire, "canonical_numeraire")

        if self.provenance is not None:
            object.__setattr__(self, "provenance", _freeze(self.provenance))

        for name in ("correction_lineage", "supersession_lineage"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, tuple(value))

        _validate_result_semantics(self)
        _require_digest(self.result_digest, "result_digest")
        if self.result_digest != _digest(self.digest_representation):
            raise ValueError("result digest does not match canonical result")

        if self.classification_digest is not None:
            _require_digest(self.classification_digest, "classification_digest")
            if self.classification_digest != _digest(
                _classification_payload(self)
            ):
                raise ValueError(
                    "classification digest does not match canonical classification"
                )

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        """Return the complete public representation, including both digests."""

        return _freeze(
            {
                "contract_version": self.contract_version,
                "evaluator_version": self.evaluator_version,
                "decision_intent_id": self.decision_intent_id,
                "lifecycle_id": self.lifecycle_id,
                "status": self.status.value,
                "failure_reason": (
                    self.failure_reason.value
                    if self.failure_reason is not None
                    else None
                ),
                "realization_eligibility": self.realization_eligibility,
                "realized_economic_result": self.realized_economic_result,
                "canonical_numeraire": self.canonical_numeraire,
                "performance_classification": (
                    self.performance_classification.value
                    if self.performance_classification is not None
                    else None
                ),
                "g2_result_id": self.g2_result_id,
                "g2_policy_version": self.g2_policy_version,
                "g2_result_digest": self.g2_result_digest,
                "g3_result_id": self.g3_result_id,
                "g3_policy_version": self.g3_policy_version,
                "g3_result_digest": self.g3_result_digest,
                "g4_result_id": self.g4_result_id,
                "g4_policy_version": self.g4_policy_version,
                "g4_result_digest": self.g4_result_digest,
                "evidence_digest": self.evidence_digest,
                "provenance": (
                    _canonicalize(self.provenance)
                    if self.provenance is not None
                    else None
                ),
                "correction_lineage": self.correction_lineage,
                "supersession_lineage": self.supersession_lineage,
                "result_digest": self.result_digest,
                "classification_digest": self.classification_digest,
            }
        )

    @property
    def digest_representation(self) -> Mapping[str, Any]:
        """Return canonical result material with result_digest excluded."""

        representation = dict(self.canonical_representation)
        representation.pop("result_digest")
        return _freeze(representation)

    @property
    def deterministic_representation(self) -> Mapping[str, Any]:
        return self.canonical_representation


class EconomicOutcomeInterpretationEvaluator:
    """Callable façade for the pure T07 assembly operation."""

    @staticmethod
    def evaluate(
        input_value: EconomicOutcomeInterpretationInput | Mapping[str, Any],
    ) -> EconomicOutcomeInterpretationResult:
        return evaluate_economic_outcome_interpretation(input_value)

    def __call__(
        self,
        input_value: EconomicOutcomeInterpretationInput | Mapping[str, Any],
    ) -> EconomicOutcomeInterpretationResult:
        return self.evaluate(input_value)


def evaluate_economic_outcome_interpretation(
    input_value: EconomicOutcomeInterpretationInput | Mapping[str, Any],
) -> EconomicOutcomeInterpretationResult:
    """Assemble one T07 result without deriving any upstream economic fact."""

    try:
        value = _coerce_input(input_value)
    except _InputIssue as issue:
        return _invalid_result(None, issue.reason)

    issue = _validate_input(value)
    if issue is not None:
        return _invalid_result(value, issue.reason)

    g2_state = _coerce_enum(value.g2_state, G2RealizationState, "g2_state")
    g3_validity = _coerce_enum(value.g3_validity, G3Validity, "g3_validity")
    g4_validity = _coerce_enum(value.g4_validity, G4Validity, "g4_validity")

    if g2_state in _NON_REALIZED_G2_STATES:
        if (
            g3_validity is not G3Validity.NOT_REALIZED
            or g4_validity is not G4Validity.NOT_REALIZED
            or value.realized_economic_result is not None
            or value.classification is not None
        ):
            return _invalid_result(value, EconomicOutcomeFailureReason.CONFLICTING_INPUT)
        return _build_result(
            value,
            status=EconomicOutcomeInterpretationStatus.NOT_REALIZED,
            failure_reason=EconomicOutcomeFailureReason.NON_REALIZED_LIFECYCLE,
            realization_eligibility="NOT_REALIZED_ELIGIBLE",
            realized_economic_result=None,
            classification=None,
        )

    if g2_state is not G2RealizationState.REALIZED_ELIGIBLE:
        return _invalid_result(value, EconomicOutcomeFailureReason.INVALID_G2)
    if g3_validity not in _VALID_G3_STATES:
        return _invalid_result(value, EconomicOutcomeFailureReason.INVALID_G3)
    if g4_validity not in _VALID_G4_STATES:
        return _invalid_result(value, EconomicOutcomeFailureReason.INVALID_G4)

    try:
        economic_result = _canonical_decimal(value.realized_economic_result)
    except ValueError:
        return _invalid_result(value, EconomicOutcomeFailureReason.NUMERIC_INVALID)

    if economic_result is None:
        return _invalid_result(value, EconomicOutcomeFailureReason.NUMERIC_INVALID)
    if value.classification is None:
        return _invalid_result(value, EconomicOutcomeFailureReason.INVALID_G4)

    try:
        classification = _coerce_enum(
            value.classification,
            PerformanceClassification,
            "classification",
        )
    except ValueError:
        return _invalid_result(value, EconomicOutcomeFailureReason.INVALID_G4)

    return _build_result(
        value,
        status=EconomicOutcomeInterpretationStatus.VALID,
        failure_reason=None,
        realization_eligibility="REALIZED_ELIGIBLE",
        realized_economic_result=economic_result,
        classification=classification,
    )


create_economic_outcome_interpretation = (
    evaluate_economic_outcome_interpretation
)
interpret_economic_outcome = evaluate_economic_outcome_interpretation
EconomicOutcomeInterpretation = EconomicOutcomeInterpretationResult


class _InputIssue(Exception):
    def __init__(self, reason: EconomicOutcomeFailureReason):
        self.reason = reason


def _coerce_input(
    value: EconomicOutcomeInterpretationInput | Mapping[str, Any],
) -> EconomicOutcomeInterpretationInput:
    if type(value) is EconomicOutcomeInterpretationInput:
        return value

    if not isinstance(value, Mapping):
        raise _InputIssue(EconomicOutcomeFailureReason.MISSING_REQUIRED_INPUT)

    field_names = {
        field
        for field in EconomicOutcomeInterpretationInput.__dataclass_fields__
    }
    if any(key not in field_names for key in value):
        raise _InputIssue(EconomicOutcomeFailureReason.CONFLICTING_INPUT)

    try:
        return EconomicOutcomeInterpretationInput(**dict(value))
    except (TypeError, ValueError):
        raise _InputIssue(EconomicOutcomeFailureReason.CONFLICTING_INPUT)


def _validate_input(
    value: EconomicOutcomeInterpretationInput,
) -> _InputIssue | None:
    required_text_fields = (
        "decision_intent_id",
        "lifecycle_id",
        "observation_id",
        "dataset_snapshot_id",
        "evidence_evaluation_snapshot_id",
        "readiness_result_id",
        "g2_result_id",
        "g2_policy_version",
        "g3_result_id",
        "g3_policy_version",
        "g4_result_id",
        "g4_policy_version",
    )
    for name in required_text_fields:
        if not _is_text(getattr(value, name)):
            return _InputIssue(EconomicOutcomeFailureReason.MISSING_REQUIRED_INPUT)

    for name in (
        "g2_result_digest",
        "g3_result_digest",
        "g4_result_digest",
        "evidence_digest",
    ):
        if not _is_digest(getattr(value, name)):
            return _InputIssue(EconomicOutcomeFailureReason.DIGEST_FAILURE)

    for name in (
        "evidence_references",
        "authority_references",
        "source_references",
    ):
        if not _valid_reference_tuple(getattr(value, name)):
            return _InputIssue(EconomicOutcomeFailureReason.MISSING_REQUIRED_INPUT)

    for name in ("g2_provenance", "g3_provenance", "g4_provenance"):
        provenance = getattr(value, name)
        if not _valid_provenance(provenance):
            return _InputIssue(EconomicOutcomeFailureReason.PROVENANCE_LINKAGE_FAILURE)
        if _provenance_conflicts(
            provenance,
            value.decision_intent_id,
            value.lifecycle_id,
        ):
            return _InputIssue(EconomicOutcomeFailureReason.PROVENANCE_LINKAGE_FAILURE)

    timestamps = value.canonical_timestamps
    if not isinstance(timestamps, Mapping) or not timestamps:
        return _InputIssue(EconomicOutcomeFailureReason.MISSING_REQUIRED_INPUT)
    for timestamp in timestamps.values():
        if not _valid_timestamp(timestamp):
            return _InputIssue(EconomicOutcomeFailureReason.PROVENANCE_LINKAGE_FAILURE)

    for name, lineage in (
        ("correction_lineage", value.correction_lineage),
        ("supersession_lineage", value.supersession_lineage),
    ):
        if not isinstance(lineage, tuple):
            return _InputIssue(EconomicOutcomeFailureReason.PROVENANCE_LINKAGE_FAILURE)
        if any(not _is_text(item) for item in lineage):
            return _InputIssue(EconomicOutcomeFailureReason.PROVENANCE_LINKAGE_FAILURE)
        if any(item.upper() == "UNRESOLVED" for item in lineage):
            reason = (
                EconomicOutcomeFailureReason.UNRESOLVED_CORRECTION
                if name == "correction_lineage"
                else EconomicOutcomeFailureReason.UNRESOLVED_SUPERSESSION
            )
            return _InputIssue(reason)

    try:
        _coerce_enum(value.g2_state, G2RealizationState, "g2_state")
    except ValueError:
        return _InputIssue(EconomicOutcomeFailureReason.INVALID_G2)
    try:
        _coerce_enum(value.g3_validity, G3Validity, "g3_validity")
    except ValueError:
        return _InputIssue(EconomicOutcomeFailureReason.INVALID_G3)
    try:
        _coerce_enum(value.g4_validity, G4Validity, "g4_validity")
    except ValueError:
        return _InputIssue(EconomicOutcomeFailureReason.INVALID_G4)

    try:
        _canonical_decimal(value.realized_economic_result)
    except ValueError:
        return _InputIssue(EconomicOutcomeFailureReason.NUMERIC_INVALID)

    if value.canonical_numeraire is not None and not _is_text(
        value.canonical_numeraire
    ):
        return _InputIssue(EconomicOutcomeFailureReason.NUMERIC_INVALID)

    for provenance in (
        value.g2_provenance,
        value.g3_provenance,
        value.g4_provenance,
    ):
        if isinstance(provenance, Mapping):
            state = provenance.get("status")
            if state in {"CONFLICTING", "CONTRADICTORY"}:
                return _InputIssue(EconomicOutcomeFailureReason.CONFLICTING_INPUT)
            if provenance.get("unresolved_residual") is True:
                return _InputIssue(EconomicOutcomeFailureReason.UNRESOLVED_RESIDUAL)

    return None


def _build_result(
    value: EconomicOutcomeInterpretationInput,
    *,
    status: EconomicOutcomeInterpretationStatus,
    failure_reason: EconomicOutcomeFailureReason | None,
    realization_eligibility: str | None,
    realized_economic_result: str | None,
    classification: PerformanceClassification | None,
) -> EconomicOutcomeInterpretationResult:
    fields = {
        "contract_version": P08_T07_CONTRACT_VERSION,
        "evaluator_version": P08_T07_EVALUATOR_VERSION,
        "decision_intent_id": value.decision_intent_id,
        "lifecycle_id": value.lifecycle_id,
        "status": status,
        "failure_reason": failure_reason,
        "realization_eligibility": realization_eligibility,
        "realized_economic_result": realized_economic_result,
        "canonical_numeraire": value.canonical_numeraire
        if status is EconomicOutcomeInterpretationStatus.VALID
        else None,
        "performance_classification": classification,
        "g2_result_id": value.g2_result_id,
        "g2_policy_version": value.g2_policy_version,
        "g2_result_digest": value.g2_result_digest,
        "g3_result_id": value.g3_result_id,
        "g3_policy_version": value.g3_policy_version,
        "g3_result_digest": value.g3_result_digest,
        "g4_result_id": value.g4_result_id,
        "g4_policy_version": value.g4_policy_version,
        "g4_result_digest": value.g4_result_digest,
        "evidence_digest": value.evidence_digest,
        "provenance": _assemble_provenance(value),
        "correction_lineage": value.correction_lineage,
        "supersession_lineage": value.supersession_lineage,
        "result_digest": None,
        "classification_digest": None,
    }
    if classification is not None:
        fields["classification_digest"] = _digest(
            _classification_payload_from_fields(fields)
        )
    fields["result_digest"] = _digest(
        _canonical_result_fields(fields, include_result_digest=False)
    )
    return EconomicOutcomeInterpretationResult(
        **fields,
    )


def _invalid_result(
    value: EconomicOutcomeInterpretationInput | None,
    reason: EconomicOutcomeFailureReason,
) -> EconomicOutcomeInterpretationResult:
    if value is None:
        value = EconomicOutcomeInterpretationInput()

    return _build_result(
        _safe_input(value),
        status=EconomicOutcomeInterpretationStatus.INVALID_INPUT,
        failure_reason=reason,
        realization_eligibility=None,
        realized_economic_result=None,
        classification=None,
    )


def _safe_input(
    value: EconomicOutcomeInterpretationInput,
) -> EconomicOutcomeInterpretationInput:
    def text_or_none(item: Any) -> str | None:
        return item if _is_text(item) else None

    def digest_or_none(item: Any) -> str | None:
        return item if _is_digest(item) else None

    def lineage_or_none(item: Any) -> tuple[str, ...] | None:
        if not isinstance(item, tuple):
            return None
        if any(not _is_text(child) for child in item):
            return None
        return item

    return EconomicOutcomeInterpretationInput(
        decision_intent_id=text_or_none(value.decision_intent_id),
        lifecycle_id=text_or_none(value.lifecycle_id),
        observation_id=text_or_none(value.observation_id),
        dataset_snapshot_id=text_or_none(value.dataset_snapshot_id),
        evidence_evaluation_snapshot_id=text_or_none(
            value.evidence_evaluation_snapshot_id
        ),
        readiness_result_id=text_or_none(value.readiness_result_id),
        g2_result_id=text_or_none(value.g2_result_id),
        g2_policy_version=text_or_none(value.g2_policy_version),
        g2_result_digest=digest_or_none(value.g2_result_digest),
        g2_provenance=_safe_provenance(value.g2_provenance),
        g3_result_id=text_or_none(value.g3_result_id),
        g3_policy_version=text_or_none(value.g3_policy_version),
        g3_result_digest=digest_or_none(value.g3_result_digest),
        g3_provenance=_safe_provenance(value.g3_provenance),
        canonical_numeraire=text_or_none(value.canonical_numeraire),
        g4_result_id=text_or_none(value.g4_result_id),
        g4_policy_version=text_or_none(value.g4_policy_version),
        g4_result_digest=digest_or_none(value.g4_result_digest),
        g4_provenance=_safe_provenance(value.g4_provenance),
        evidence_digest=digest_or_none(value.evidence_digest),
        evidence_references=_safe_strings(value.evidence_references),
        authority_references=_safe_strings(value.authority_references),
        source_references=_safe_strings(value.source_references),
        correction_lineage=lineage_or_none(value.correction_lineage) or (),
        supersession_lineage=lineage_or_none(value.supersession_lineage) or (),
        canonical_timestamps=_safe_timestamps(value.canonical_timestamps),
    )


def _result_kwargs(
    result: EconomicOutcomeInterpretationResult,
) -> dict[str, Any]:
    return {
        field: getattr(result, field)
        for field in EconomicOutcomeInterpretationResult.__dataclass_fields__
    }


def _classification_payload_from_fields(
    fields: Mapping[str, Any],
) -> Mapping[str, Any]:
    classification = fields["performance_classification"]
    return _freeze(
        {
            "lifecycle_id": fields["lifecycle_id"],
            "g4_result_id": fields["g4_result_id"],
            "g4_policy_version": fields["g4_policy_version"],
            "g4_result_digest": fields["g4_result_digest"],
            "classification": (
                classification.value
                if isinstance(classification, PerformanceClassification)
                else classification
            ),
        }
    )


def _canonical_result_fields(
    fields: Mapping[str, Any],
    *,
    include_result_digest: bool,
) -> Mapping[str, Any]:
    canonical = {
        "contract_version": fields["contract_version"],
        "evaluator_version": fields["evaluator_version"],
        "decision_intent_id": fields["decision_intent_id"],
        "lifecycle_id": fields["lifecycle_id"],
        "status": (
            fields["status"].value
            if isinstance(fields["status"], EconomicOutcomeInterpretationStatus)
            else fields["status"]
        ),
        "failure_reason": (
            fields["failure_reason"].value
            if isinstance(fields["failure_reason"], EconomicOutcomeFailureReason)
            else fields["failure_reason"]
        ),
        "realization_eligibility": fields["realization_eligibility"],
        "realized_economic_result": fields["realized_economic_result"],
        "canonical_numeraire": fields["canonical_numeraire"],
        "performance_classification": (
            fields["performance_classification"].value
            if isinstance(fields["performance_classification"], PerformanceClassification)
            else fields["performance_classification"]
        ),
        "g2_result_id": fields["g2_result_id"],
        "g2_policy_version": fields["g2_policy_version"],
        "g2_result_digest": fields["g2_result_digest"],
        "g3_result_id": fields["g3_result_id"],
        "g3_policy_version": fields["g3_policy_version"],
        "g3_result_digest": fields["g3_result_digest"],
        "g4_result_id": fields["g4_result_id"],
        "g4_policy_version": fields["g4_policy_version"],
        "g4_result_digest": fields["g4_result_digest"],
        "evidence_digest": fields["evidence_digest"],
        "provenance": (
            _canonicalize(fields["provenance"])
            if fields["provenance"] is not None
            else None
        ),
        "correction_lineage": fields["correction_lineage"],
        "supersession_lineage": fields["supersession_lineage"],
        "classification_digest": fields["classification_digest"],
    }
    if include_result_digest:
        canonical["result_digest"] = fields["result_digest"]
    return _freeze(canonical)


def _assemble_provenance(
    value: EconomicOutcomeInterpretationInput,
) -> Mapping[str, Any] | None:
    if not (
        _valid_provenance(value.g2_provenance)
        and _valid_provenance(value.g3_provenance)
        and _valid_provenance(value.g4_provenance)
        and isinstance(value.canonical_timestamps, Mapping)
    ):
        return None

    return _freeze(
        {
            "decision_intent_id": value.decision_intent_id,
            "lifecycle_id": value.lifecycle_id,
            "observation_id": value.observation_id,
            "dataset_snapshot_id": value.dataset_snapshot_id,
            "evidence_evaluation_snapshot_id": (
                value.evidence_evaluation_snapshot_id
            ),
            "readiness_result_id": value.readiness_result_id,
            "g2": value.g2_provenance,
            "g3": value.g3_provenance,
            "g4": value.g4_provenance,
            "evidence_references": value.evidence_references,
            "authority_references": value.authority_references,
            "source_references": value.source_references,
            "canonical_timestamps": value.canonical_timestamps,
        }
    )


def _validate_result_semantics(
    result: EconomicOutcomeInterpretationResult,
) -> None:
    if result.status is EconomicOutcomeInterpretationStatus.VALID:
        if result.failure_reason is not None:
            raise ValueError("VALID result cannot have a failure reason")
        if result.realization_eligibility != "REALIZED_ELIGIBLE":
            raise ValueError("VALID result must be realization eligible")
        if result.realized_economic_result is None:
            raise ValueError("VALID result requires an economic result")
        if result.performance_classification is None:
            raise ValueError("VALID result requires a classification")
        if result.classification_digest is None:
            raise ValueError("VALID result requires a classification digest")
    elif result.status is EconomicOutcomeInterpretationStatus.NOT_REALIZED:
        if result.failure_reason is not EconomicOutcomeFailureReason.NON_REALIZED_LIFECYCLE:
            raise ValueError("NOT_REALIZED result has an invalid failure reason")
        if result.realization_eligibility != "NOT_REALIZED_ELIGIBLE":
            raise ValueError("NOT_REALIZED result must not be eligible")
        if result.realized_economic_result is not None:
            raise ValueError("NOT_REALIZED result cannot have an economic result")
        if result.performance_classification is not None:
            raise ValueError("NOT_REALIZED result cannot have a classification")
        if result.classification_digest is not None:
            raise ValueError("NOT_REALIZED result cannot have a classification digest")
    else:
        if result.failure_reason is None:
            raise ValueError("INVALID_INPUT result requires a failure reason")
        if result.realized_economic_result is not None:
            raise ValueError("INVALID_INPUT result cannot have an economic result")
        if result.performance_classification is not None:
            raise ValueError("INVALID_INPUT result cannot have a classification")
        if result.classification_digest is not None:
            raise ValueError("INVALID_INPUT result cannot have a classification digest")


def _classification_payload(
    result: EconomicOutcomeInterpretationResult,
) -> Mapping[str, Any]:
    return _freeze(
        {
            "lifecycle_id": result.lifecycle_id,
            "g4_result_id": result.g4_result_id,
            "g4_policy_version": result.g4_policy_version,
            "g4_result_digest": result.g4_result_digest,
            "classification": (
                result.performance_classification.value
                if result.performance_classification is not None
                else None
            ),
        }
    )


def _canonical_decimal(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("economic values must not use binary floating point")
    if isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, str):
        if not value or value.strip() != value:
            raise ValueError("economic value is not canonical text")
        try:
            decimal_value = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("economic value is not a decimal") from error
    else:
        raise ValueError("unsupported economic numeric representation")

    if not decimal_value.is_finite():
        raise ValueError("economic value must be finite")
    if decimal_value == 0:
        return "0"
    canonical = format(decimal_value, "f")
    if canonical.startswith("+"):
        canonical = canonical[1:]
    return canonical


def _coerce_enum(value: Any, enum_type: type[Enum], name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"unsupported {name}") from error


def _valid_provenance(value: Any) -> bool:
    if isinstance(value, Mapping):
        if not value:
            return False
        try:
            _canonicalize(value)
        except ValueError:
            return False
        return True
    if isinstance(value, tuple):
        return bool(value) and all(_is_text(item) for item in value)
    return False


def _provenance_conflicts(
    value: Any,
    decision_intent_id: str | None,
    lifecycle_id: str | None,
) -> bool:
    if not isinstance(value, Mapping):
        return False
    return (
        (
            "decision_intent_id" in value
            and value["decision_intent_id"] != decision_intent_id
        )
        or ("lifecycle_id" in value and value["lifecycle_id"] != lifecycle_id)
    )


def _valid_reference_tuple(value: Any) -> bool:
    return (
        isinstance(value, tuple)
        and bool(value)
        and all(_is_text(item) for item in value)
    )


def _valid_timestamp(value: Any) -> bool:
    if isinstance(value, datetime):
        return value.tzinfo is not None and value.utcoffset() is not None
    return isinstance(value, str) and bool(value.strip())


def _safe_provenance(value: Any) -> Mapping[str, Any] | tuple[Any, ...] | None:
    if not _valid_provenance(value):
        return None
    return value


def _safe_timestamps(value: Any) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    if not all(_valid_timestamp(item) for item in value.values()):
        return None
    return value


def _safe_strings(value: Any) -> tuple[str, ...]:
    return value if _valid_reference_tuple(value) else ()


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_text(value: Any, name: str) -> None:
    if not _is_text(value):
        raise ValueError(f"{name} must be non-empty text")


def _is_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _DIGEST_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _require_digest(value: Any, name: str) -> None:
    if not _is_digest(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return _canonical_decimal(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value, key=str)
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    raise ValueError(f"{type(value).__name__} cannot be serialized canonically")


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
            {str(key): _freeze(child) for key, child in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


__all__ = [
    "EconomicOutcomeFailureReason",
    "EconomicOutcomeInterpretation",
    "EconomicOutcomeInterpretationEvaluator",
    "EconomicOutcomeInterpretationInput",
    "EconomicOutcomeInterpretationResult",
    "EconomicOutcomeInterpretationStatus",
    "G2RealizationState",
    "G3Validity",
    "G4Validity",
    "P08_T07_CONTRACT_VERSION",
    "P08_T07_EVALUATOR_VERSION",
    "PerformanceClassification",
    "create_economic_outcome_interpretation",
    "evaluate_economic_outcome_interpretation",
    "interpret_economic_outcome",
]