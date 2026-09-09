"""P08-G1 simulation-only economic authority.

This module is deliberately a validation boundary, not a second simulation
engine.  It accepts one explicitly materialized predecessor chain and emits
only simulation recognition/finality information.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import unicodedata
from typing import Any, Mapping

from core.decision import DecisionIntent, P06_T01_CONTRACT_VERSION
from core.execution.paper_fill_outcome import (
    FillOutcomeStatus,
    P07_T02_CONTRACT_VERSION,
    PaperFillOutcome,
)
from core.execution.paper_ledger import (
    P07_T04_CONTRACT_VERSION,
    PaperLedgerEntry,
)
from core.execution.paper_position_exposure_state import (
    P07_T03_CONTRACT_VERSION,
    PaperStateTransitionResult,
)
from core.execution.paper_reconciliation import (
    LEDGER_STATE_CONSISTENCY_VERIFICATION_CONTRACT_VERSION,
    PaperReconciliationResult,
    ReconciliationStatus,
)
from core.execution.paper_simulation_input import (
    P07_T01_CONTRACT_VERSION,
    PaperSimulationInput,
)
from core.execution.paper_simulation_result import (
    P07_T06_CONTRACT_VERSION,
    PaperSimulationResult,
)
from core.learning.outcome_dataset import (
    P08_T02_CONTRACT_VERSION,
    OutcomeLearningDatasetSnapshot,
)
from core.learning.outcome_evidence import (
    P08_T04_CONTRACT_VERSION,
    OutcomeEvidenceEvaluationResult,
    OutcomeEvidenceState,
)
from core.learning.outcome_evidence_snapshot import (
    P08_T05_CONTRACT_VERSION,
    OutcomeEvidenceEvaluationSnapshot,
)
from core.learning.outcome_interpretation import (
    P08_T03_CONTRACT_VERSION,
    OutcomeInterpretationResult,
)
from core.learning.outcome_observation import (
    P08_T01_CONTRACT_VERSION,
    OutcomeLearningObservation,
)
from core.learning.outcome_readiness import (
    P08_T06_CONTRACT_VERSION,
    OutcomeLearningReadinessResult,
    OutcomeLearningReadinessState,
)


G1_CONTRACT_VERSION = "p08-g1-simulation-only-v1"
G1_EVALUATOR_VERSION = "p08-g1-simulation-only-economic-authority-v1"
P07_T07_CONTRACT_VERSION = "p07-t07-v1"


class G1RecognitionState(StrEnum):
    NOT_RECOGNIZED = "NOT_RECOGNIZED"
    RECOGNIZED = "RECOGNIZED"


class G1FinalityState(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    FINAL = "FINAL"


class G1ReasonCode(StrEnum):
    RECOGNIZED_COMPLETE = "RECOGNIZED_COMPLETE"
    INVALID_TYPE = "INVALID_TYPE"
    MISSING_REQUIRED_INPUT = "MISSING_REQUIRED_INPUT"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    INVALID_CANONICAL_REPRESENTATION = "INVALID_CANONICAL_REPRESENTATION"
    DIGEST_FAILURE = "DIGEST_FAILURE"
    INVALID_IDENTITY_LINK = "INVALID_IDENTITY_LINK"
    INVALID_LIFECYCLE = "INVALID_LIFECYCLE"
    PROVENANCE_FAILURE = "PROVENANCE_FAILURE"
    CONTRADICTORY_INPUT = "CONTRADICTORY_INPUT"
    STALE_INPUT = "STALE_INPUT"
    UNKNOWN_INPUT = "UNKNOWN_INPUT"
    UNAVAILABLE_INPUT = "UNAVAILABLE_INPUT"
    INCOMPLETE_INPUT = "INCOMPLETE_INPUT"
    PARTIAL_INPUT = "PARTIAL_INPUT"
    UNFILLED_INPUT = "UNFILLED_INPUT"
    FAILED_INPUT = "FAILED_INPUT"
    NON_FINAL_INPUT = "NON_FINAL_INPUT"
    UNSUPPORTED_SIMULATION_STATE = "UNSUPPORTED_SIMULATION_STATE"
    UNRESOLVED_CORRECTION = "UNRESOLVED_CORRECTION"
    UNRESOLVED_SUPERSESSION = "UNRESOLVED_SUPERSESSION"
    DETERMINISM_FAILURE = "DETERMINISM_FAILURE"


@dataclass(frozen=True)
class G1AuthorityAReference:
    """Opaque Authority A references consumed without redefining their meaning."""

    canonical_economic_subject_identity: str
    lifecycle_identity: str
    authority_identity: str
    authority_version: str

    def __post_init__(self) -> None:
        for name in (
            "canonical_economic_subject_identity",
            "lifecycle_identity",
            "authority_identity",
            "authority_version",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
            if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
                raise ValueError(f"{name} contains an unpaired surrogate")
        object.__setattr__(
            self,
            "canonical_economic_subject_identity",
            unicodedata.normalize(
                "NFC", self.canonical_economic_subject_identity
            ),
        )
        object.__setattr__(
            self,
            "lifecycle_identity",
            unicodedata.normalize("NFC", self.lifecycle_identity),
        )
        object.__setattr__(
            self,
            "authority_identity",
            unicodedata.normalize("NFC", self.authority_identity),
        )
        object.__setattr__(
            self,
            "authority_version",
            unicodedata.normalize("NFC", self.authority_version),
        )


@dataclass(frozen=True)
class G1P07Predecessors:
    p07_t01: PaperSimulationInput
    p07_t02: PaperFillOutcome
    p07_t03: PaperStateTransitionResult
    p07_t04: tuple[PaperLedgerEntry, ...]
    p07_t05: PaperReconciliationResult
    p07_t06: PaperSimulationResult


@dataclass(frozen=True)
class G1P07HistorySnapshot:
    """Explicit immutable materialization of one P07-T07 history snapshot."""

    results: tuple[PaperSimulationResult, ...]
    history_digest: str
    history_identity: str
    contract_version: str = P07_T07_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "results", tuple(self.results))
        if self.contract_version != P07_T07_CONTRACT_VERSION:
            raise ValueError("unsupported P07-T07 contract version")
        if not self.results:
            raise ValueError("P07-T07 history snapshot must not be empty")
        if not all(isinstance(result, PaperSimulationResult) for result in self.results):
            raise ValueError("history results must be PaperSimulationResult values")
        ordered = tuple(
            sorted(self.results, key=lambda value: _canonical_json(value.canonical_dict()))
        )
        if ordered != self.results:
            raise ValueError("history results are not in canonical order")
        if self.history_digest != _history_digest(self.results):
            raise ValueError("history digest does not match history")
        if self.history_identity != self.history_digest:
            raise ValueError("history identity must equal history digest")

    @classmethod
    def from_results(
        cls,
        results: tuple[PaperSimulationResult, ...],
    ) -> "G1P07HistorySnapshot":
        ordered = tuple(
            sorted(results, key=lambda value: _canonical_json(value.canonical_dict()))
        )
        digest = _sha256(
            {
                "contract_version": P07_T07_CONTRACT_VERSION,
                "results": tuple(value.canonical_dict() for value in ordered),
            }
        )
        return cls(
            results=ordered,
            history_digest=digest,
            history_identity=digest,
        )


@dataclass(frozen=True)
class G1P08Predecessors:
    p08_t01: OutcomeLearningObservation
    p08_t02: OutcomeLearningDatasetSnapshot
    p08_t03: OutcomeInterpretationResult
    p08_t04: OutcomeEvidenceEvaluationResult
    p08_t05: OutcomeEvidenceEvaluationSnapshot
    p08_t06: OutcomeLearningReadinessResult


@dataclass(frozen=True)
class G1SimulationOnlyEconomicAuthorityInput:
    authority_a: G1AuthorityAReference
    p06: DecisionIntent
    p07: G1P07Predecessors
    p07_history: G1P07HistorySnapshot
    p08: G1P08Predecessors
    contract_version: str = G1_CONTRACT_VERSION
    evaluator_version: str = G1_EVALUATOR_VERSION


@dataclass(frozen=True)
class G1ProvenanceLink:
    stage: str
    record_identity: str
    record_digest: str
    authority_identity: str
    contract_version: str
    evaluator_version: str

    @property
    def canonical_representation(self) -> Mapping[str, str]:
        return {
            "stage": self.stage,
            "record_identity": self.record_identity,
            "record_digest": self.record_digest,
            "authority_identity": self.authority_identity,
            "contract_version": self.contract_version,
            "evaluator_version": self.evaluator_version,
        }


@dataclass(frozen=True)
class G1SimulationOnlyEconomicAuthorityResult:
    contract_version: str
    evaluator_version: str
    canonical_economic_subject_identity: str
    lifecycle_identity: str
    decision_intent_identity: str
    paper_simulation_result_identity: str
    history_snapshot_identity: str
    observation_identity: str
    dataset_snapshot_identity: str
    dataset_as_of_time: datetime
    readiness_identity: str
    recognition_state: G1RecognitionState
    finality_state: G1FinalityState
    reason_code: G1ReasonCode
    provenance: tuple[G1ProvenanceLink, ...]
    result_identity: str
    result_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_as_of_time", _utc(self.dataset_as_of_time))
        object.__setattr__(self, "provenance", tuple(self.provenance))
        object.__setattr__(self, "recognition_state", G1RecognitionState(self.recognition_state))
        object.__setattr__(self, "finality_state", G1FinalityState(self.finality_state))
        object.__setattr__(self, "reason_code", G1ReasonCode(self.reason_code))
        expected_identity = _result_identity(self._identity_projection())
        if self.result_identity != expected_identity:
            raise ValueError("result_identity does not match canonical identity projection")
        if self.result_digest != _sha256(self._canonical_without_digest()):
            raise ValueError("result_digest does not match canonical result")

    def _identity_projection(self) -> tuple[str, ...]:
        return (
            self.contract_version,
            self.canonical_economic_subject_identity,
            self.lifecycle_identity,
            self.decision_intent_identity,
            self.paper_simulation_result_identity,
            self.history_snapshot_identity,
            self.observation_identity,
            self.dataset_snapshot_identity,
            self.readiness_identity,
            self.recognition_state.value,
            self.finality_state.value,
        )

    def _canonical_without_digest(self) -> Mapping[str, Any]:
        return {
            "contract_version": self.contract_version,
            "evaluator_version": self.evaluator_version,
            "canonical_economic_subject_identity": self.canonical_economic_subject_identity,
            "lifecycle_identity": self.lifecycle_identity,
            "decision_intent_identity": self.decision_intent_identity,
            "paper_simulation_result_identity": self.paper_simulation_result_identity,
            "history_snapshot_identity": self.history_snapshot_identity,
            "observation_identity": self.observation_identity,
            "dataset_snapshot_identity": self.dataset_snapshot_identity,
            "dataset_as_of_time": self.dataset_as_of_time.isoformat(),
            "readiness_identity": self.readiness_identity,
            "recognition_state": self.recognition_state.value,
            "finality_state": self.finality_state.value,
            "reason_code": self.reason_code.value,
            "provenance": tuple(link.canonical_representation for link in self.provenance),
            "result_identity": self.result_identity,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {**self._canonical_without_digest(), "result_digest": self.result_digest}

    @property
    def digest(self) -> str:
        return self.result_digest


_PRECEDENCE = tuple(G1ReasonCode)[1:]
_STAGES = (
    "p06_decision_intent",
    "p07_simulation_input",
    "p07_fill_outcome",
    "p07_position_exposure",
    "p07_ledger",
    "p07_reconciliation",
    "p07_simulation_result",
    "p07_history",
    "p08_t01_observation",
    "p08_t02_dataset",
    "p08_t03_interpretation",
    "p08_t04_evaluation",
    "p08_t05_snapshot",
    "p08_t06_readiness",
    "authority_a_identity",
)


def evaluate_g1(
    value: G1SimulationOnlyEconomicAuthorityInput,
) -> G1SimulationOnlyEconomicAuthorityResult | None:
    """Evaluate one explicit chain. Missing/invalid outer structure returns None."""

    if not isinstance(value, G1SimulationOnlyEconomicAuthorityInput):
        return None
    try:
        refs = _references(value)
        failure = _classify(value)
        if failure is None:
            recognition = G1RecognitionState.RECOGNIZED
            finality = G1FinalityState.FINAL
            reason = G1ReasonCode.RECOGNIZED_COMPLETE
        else:
            recognition = G1RecognitionState.NOT_RECOGNIZED
            finality = G1FinalityState.NOT_APPLICABLE
            reason = failure
        return _make_result(value, refs, recognition, finality, reason)
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
        return None


evaluate_simulation_only_economic_authority = evaluate_g1
recognize_simulation_lifecycle = evaluate_g1


def _classify(value: G1SimulationOnlyEconomicAuthorityInput) -> G1ReasonCode | None:
    failures: set[G1ReasonCode] = set()
    a, p07, h, p08 = value.authority_a, value.p07, value.p07_history, value.p08
    if not isinstance(a, G1AuthorityAReference) or not _texts(a):
        failures.add(G1ReasonCode.INVALID_TYPE)
    if value.contract_version != G1_CONTRACT_VERSION or value.evaluator_version != G1_EVALUATOR_VERSION:
        failures.add(G1ReasonCode.UNSUPPORTED_VERSION)
    if not isinstance(p07, G1P07Predecessors) or not isinstance(h, G1P07HistorySnapshot):
        failures.add(G1ReasonCode.MISSING_REQUIRED_INPUT)
    if not isinstance(p08, G1P08Predecessors) or not isinstance(value.p06, DecisionIntent):
        failures.add(G1ReasonCode.INVALID_TYPE)
    if failures:
        return _first(failures)

    artifacts = (value.p06, p07.p07_t01, p07.p07_t02, p07.p07_t03,
                 *p07.p07_t04, p07.p07_t05, p07.p07_t06, *h.results,
                 p08.p08_t01, p08.p08_t02, p08.p08_t03, p08.p08_t04,
                 p08.p08_t05, p08.p08_t06)
    for artifact in artifacts:
        try:
            _validate_artifact(artifact)
        except _Validation as error:
            failures.add(error.reason)
    if h.contract_version != P07_T07_CONTRACT_VERSION:
        failures.add(G1ReasonCode.UNSUPPORTED_VERSION)
    if _history_digest(h.results) != h.history_digest or h.history_identity != h.history_digest:
        failures.add(G1ReasonCode.DIGEST_FAILURE)
    if len({r.digest for r in h.results}) != len(h.results):
        failures.add(G1ReasonCode.CONTRADICTORY_INPUT)

    # Exact predecessor linkage.
    if p07.p07_t01.decision_intent.decision_intent_digest != value.p06.digest:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    if p07.p07_t02.p07_t01_input_digest != p07.p07_t01.digest:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    if p07.p07_t03.outcome_identity.get("outcome_digest") != p07.p07_t02.outcome_digest:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    if p07.p07_t05.p07_t01_input_digest != p07.p07_t01.digest:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    if p07.p07_t06.input_digest != p07.p07_t01.digest:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    if p07.p07_t06.fill_digest != p07.p07_t02.outcome_digest:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    if p07.p07_t06.transition_digest != p07.p07_t03.transition_digest:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    if p07.p07_t06.reconciliation_digest != p07.p07_t05.result_digest:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    retained = [r for r in h.results if r.digest == p07.p07_t06.digest]
    if len(retained) != 1:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)

    o = p08.p08_t01
    if (o.decision_intent.digest != value.p06.digest
            or o.simulation_input.digest != p07.p07_t01.digest
            or o.paper_result.digest != p07.p07_t06.digest
            or o.history_digest != h.history_digest):
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    if o.digest not in p08.p08_t02.observation_digests:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    if p08.p08_t03.source_dataset_digest != p08.p08_t02.digest:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    if p08.p08_t04.source_interpretation_digest != p08.p08_t03.digest:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    if p08.p08_t05.source_dataset_digest != p08.p08_t02.digest or p08.p08_t04.result_digest not in p08.p08_t05.evaluation_digests:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)
    if p08.p08_t06.source_snapshot_digest != p08.p08_t05.snapshot_digest:
        failures.add(G1ReasonCode.INVALID_IDENTITY_LINK)

    cutoff = p08.p08_t02.as_of_time
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        failures.add(G1ReasonCode.STALE_INPUT)
    if any(o2.simulation_reference_time > cutoff for o2 in p08.p08_t02.observations):
        failures.add(G1ReasonCode.STALE_INPUT)
    if p08.p08_t03.reference_time > cutoff or p08.p08_t04.source_reference_time > cutoff:
        failures.add(G1ReasonCode.STALE_INPUT)

    # Authority A references are opaque but must agree everywhere lifecycle-bearing.
    if not all(_lifecycle_consistent(a, artifact) for artifact in (p07.p07_t01, p08.p08_t01)):
        failures.add(G1ReasonCode.INVALID_LIFECYCLE)

    # Predecessor-owned state is inspected, never recomputed.
    status = str(p07.p07_t02.status)
    if status == "PARTIALLY_FILLED":
        failures.add(G1ReasonCode.PARTIAL_INPUT)
    elif status == FillOutcomeStatus.FILLED.value and p07.p07_t02.filled_quantity == 0:
        failures.add(G1ReasonCode.UNFILLED_INPUT)
    elif status in {FillOutcomeStatus.FAILED.value, FillOutcomeStatus.REJECTED.value}:
        failures.add(G1ReasonCode.FAILED_INPUT)
    elif status == FillOutcomeStatus.UNAVAILABLE.value:
        failures.add(G1ReasonCode.UNAVAILABLE_INPUT)
    elif status == FillOutcomeStatus.INVALID.value:
        failures.add(G1ReasonCode.UNSUPPORTED_SIMULATION_STATE)
    if p07.p07_t05.status is not ReconciliationStatus.MATCH:
        failures.add(G1ReasonCode.NON_FINAL_INPUT)
    if p08.p08_t06.readiness_state is not OutcomeLearningReadinessState.READY_FOR_NON_ECONOMIC_ANALYSIS:
        failures.add(G1ReasonCode.INCOMPLETE_INPUT)
    if any(e.evidence_state is OutcomeEvidenceState.UNKNOWN for e in p08.p08_t05.evaluations):
        failures.add(G1ReasonCode.UNKNOWN_INPUT)
    if any(e.evidence_state is OutcomeEvidenceState.UNAVAILABLE for e in p08.p08_t05.evaluations):
        failures.add(G1ReasonCode.UNAVAILABLE_INPUT)
    if any(e.evidence_state is OutcomeEvidenceState.INCOMPLETE for e in p08.p08_t05.evaluations):
        failures.add(G1ReasonCode.INCOMPLETE_INPUT)
    if p07.p07_t06.status != "FILLED" or p07.p07_t06.reconciliation_status != "RECONCILED":
        failures.add(G1ReasonCode.NON_FINAL_INPUT)
    return _first(failures) if failures else None


class _Validation(Exception):
    def __init__(self, reason: G1ReasonCode) -> None:
        self.reason = reason


def _validate_artifact(value: Any) -> None:
    if value is None:
        raise _Validation(G1ReasonCode.MISSING_REQUIRED_INPUT)
    if not is_dataclass(value):
        raise _Validation(G1ReasonCode.INVALID_TYPE)
    try:
        cls = type(value)
        kwargs = {
            f.name: getattr(value, f.name)
            for f in fields(value)
            if f.init
        }
        rebuilt = cls(**kwargs)
    except Exception as error:
        raise _Validation(G1ReasonCode.INVALID_CANONICAL_REPRESENTATION) from error
    if rebuilt != value:
        raise _Validation(G1ReasonCode.INVALID_CANONICAL_REPRESENTATION)


def _references(value: G1SimulationOnlyEconomicAuthorityInput) -> tuple[str, ...]:
    p07, h, p08 = value.p07, value.p07_history, value.p08
    authority = value.authority_a.authority_identity
    def link(stage: str, identity: str, digest: str, version: str, evaluator: str) -> G1ProvenanceLink:
        return G1ProvenanceLink(stage, identity, digest, authority, version, evaluator)
    return (
        link("p06_decision_intent", value.p06.digest, value.p06.digest,
             value.p06.contract_version, value.p06.evaluator_version),
        link("p07_simulation_input", p07.p07_t01.digest, p07.p07_t01.digest,
             P07_T01_CONTRACT_VERSION, "NOT_APPLICABLE"),
        link("p07_fill_outcome", p07.p07_t02.fill_id, p07.p07_t02.outcome_digest,
             P07_T02_CONTRACT_VERSION, p07.p07_t02.fill_model_version),
        link("p07_position_exposure", p07.p07_t03.transition_digest, p07.p07_t03.transition_digest,
             P07_T03_CONTRACT_VERSION, "NOT_APPLICABLE"),
        link("p07_ledger", _sha256(tuple(e.canonical_representation for e in p07.p07_t04)),
             _sha256(tuple(e.canonical_representation for e in p07.p07_t04)), P07_T04_CONTRACT_VERSION, "NOT_APPLICABLE"),
        link("p07_reconciliation", p07.p07_t05.result_digest, p07.p07_t05.result_digest,
             LEDGER_STATE_CONSISTENCY_VERIFICATION_CONTRACT_VERSION,
             p07.p07_t05.reconciliation_model_version),
        link("p07_simulation_result", p07.p07_t06.digest, p07.p07_t06.digest,
             P07_T06_CONTRACT_VERSION, "NOT_APPLICABLE"),
        link("p07_history", h.history_identity, h.history_digest, P07_T07_CONTRACT_VERSION, "NOT_APPLICABLE"),
        link("p08_t01_observation", p08.p08_t01.digest, p08.p08_t01.digest, P08_T01_CONTRACT_VERSION, p08.p08_t01.evaluator_version),
        link("p08_t02_dataset", p08.p08_t02.digest, p08.p08_t02.digest, P08_T02_CONTRACT_VERSION, "NOT_APPLICABLE"),
        link("p08_t03_interpretation", p08.p08_t03.digest, p08.p08_t03.digest, P08_T03_CONTRACT_VERSION, p08.p08_t03.evaluator_version),
        link("p08_t04_evaluation", p08.p08_t04.result_digest, p08.p08_t04.result_digest, P08_T04_CONTRACT_VERSION, p08.p08_t04.evaluator_version),
        link("p08_t05_snapshot", p08.p08_t05.snapshot_digest, p08.p08_t05.snapshot_digest, P08_T05_CONTRACT_VERSION, p08.p08_t05.evaluator_version),
        link("p08_t06_readiness", p08.p08_t06.result_digest, p08.p08_t06.result_digest, P08_T06_CONTRACT_VERSION, p08.p08_t06.evaluator_version),
        link("authority_a_identity", a := value.authority_a.authority_identity, _sha256(value.authority_a.__dict__), value.authority_a.authority_version, "NOT_APPLICABLE"),
    )


def _make_result(value: G1SimulationOnlyEconomicAuthorityInput, refs: tuple[str, ...],
                 recognition: G1RecognitionState, finality: G1FinalityState,
                 reason: G1ReasonCode) -> G1SimulationOnlyEconomicAuthorityResult:
    p07, h, p08 = value.p07, value.p07_history, value.p08
    links = refs
    identity_fields = (
        value.contract_version, value.authority_a.canonical_economic_subject_identity,
        value.authority_a.lifecycle_identity, value.p06.digest, p07.p07_t06.digest,
        h.history_identity, p08.p08_t01.digest, p08.p08_t02.digest, p08.p08_t06.result_digest,
        recognition.value, finality.value,
    )
    identity = _result_identity(identity_fields)
    without = {
        "contract_version": value.contract_version, "evaluator_version": value.evaluator_version,
        "canonical_economic_subject_identity": value.authority_a.canonical_economic_subject_identity,
        "lifecycle_identity": value.authority_a.lifecycle_identity,
        "decision_intent_identity": value.p06.digest,
        "paper_simulation_result_identity": p07.p07_t06.digest,
        "history_snapshot_identity": h.history_identity,
        "observation_identity": p08.p08_t01.digest,
        "dataset_snapshot_identity": p08.p08_t02.digest,
        "dataset_as_of_time": _utc(p08.p08_t02.as_of_time).isoformat(),
        "readiness_identity": p08.p08_t06.result_digest,
        "recognition_state": recognition.value, "finality_state": finality.value,
        "reason_code": reason.value,
        "provenance": tuple(link.canonical_representation for link in links),
        "result_identity": identity,
    }
    return G1SimulationOnlyEconomicAuthorityResult(
        **{
            **without,
            "dataset_as_of_time": p08.p08_t02.as_of_time,
            "provenance": links,
            "result_identity": identity,
            "result_digest": _sha256(without),
        }
    )


def _first(reasons: set[G1ReasonCode]) -> G1ReasonCode:
    return next(reason for reason in _PRECEDENCE if reason in reasons)


def _lifecycle_consistent(authority: G1AuthorityAReference, artifact: Any) -> bool:
    # Authority A is intentionally opaque; only explicit matching metadata is accepted.
    for name in ("canonical_economic_subject_identity", "lifecycle_identity"):
        if hasattr(artifact, name) and getattr(artifact, name) not in (
            getattr(authority, name), None
        ):
            return False
    return True


def _texts(value: Any) -> bool:
    return all(isinstance(getattr(value, name), str) and bool(getattr(value, name).strip())
               for name in ("canonical_economic_subject_identity", "lifecycle_identity",
                            "authority_identity", "authority_version"))


def _history_digest(results: tuple[PaperSimulationResult, ...]) -> str:
    return _sha256({"contract_version": P07_T07_CONTRACT_VERSION,
                    "results": tuple(r.canonical_dict() for r in results)})


def _result_identity(projection: tuple[str, ...]) -> str:
    return hashlib.sha256(
        ("p08-g1-simulation-only:result:v1\0" + _canonical_json(projection)).encode()
    ).hexdigest()


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _canonicalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return _utc(value).isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {unicodedata.normalize("NFC", str(k)): _canonicalize(v)
                for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if is_dataclass(value):
        return _canonicalize(value.canonical_representation)
    if isinstance(value, (str, int, bool)) or value is None:
        return unicodedata.normalize("NFC", value) if isinstance(value, str) else value
    return str(value)


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)
