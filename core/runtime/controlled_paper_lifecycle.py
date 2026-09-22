"""Compose one approved paper admission through one P08-T01 observation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from core.execution.paper_fill_outcome import (
    FrictionComponents,
    PaperFillOutcome,
    TradeSide,
    evaluate_paper_fill,
)
from core.execution.paper_ledger import (
    PaperLedgerEntry,
    create_paper_ledger_entry,
)
from core.execution.paper_position_exposure_state import (
    AccountingContext,
    PaperPositionExposureState,
    PaperStateTransitionResult,
    ValuationContext,
    transition_paper_state,
)
from core.execution.paper_reconciliation import (
    PaperReconciliationExpectation,
    PaperReconciliationResult,
    ReconciliationStatus,
    reconcile_paper_ledger,
)
from core.execution.paper_simulation_result import PaperSimulationResult
from core.execution.paper_simulation_result_history import (
    PaperSimulationResultHistory,
    PaperSimulationResultHistoryOutcome,
    PaperSimulationResultHistoryResult,
)
from core.learning.outcome_observation import (
    OutcomeLearningObservation,
    create_outcome_learning_observation,
)
from core.runtime.controlled_paper_run_admission import (
    ControlledPaperRunAdmissionOutcome,
    ControlledPaperRunAdmissionResult,
)


P01_RTI_02_CONTRACT_VERSION = "p01-rti-02-v1"


class ControlledPaperLifecycleOutcome(StrEnum):
    OBSERVATION_PRODUCED = "OBSERVATION_PRODUCED"
    ADMISSION_NOT_READY = "ADMISSION_NOT_READY"
    RECONCILIATION_NOT_MATCHED = "RECONCILIATION_NOT_MATCHED"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class PaperFillInstruction:
    """Explicit caller-owned facts for one P07-T02 evaluation."""

    side: TradeSide | str
    requested_quantity: Decimal
    quantity_unit: str
    price_unit: str
    fee_unit: str
    quote_currency: str
    executable_liquidity: Decimal
    reference_quote_price: Decimal
    quote_observation_time: datetime
    fill_time: datetime | None
    friction: FrictionComponents
    available_inventory: Decimal | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "side", TradeSide(self.side))
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported paper fill side") from error
        for value, name in (
            (self.requested_quantity, "requested_quantity"),
            (self.executable_liquidity, "executable_liquidity"),
            (self.reference_quote_price, "reference_quote_price"),
        ):
            _decimal(value, name)
        if self.available_inventory is not None:
            _decimal(self.available_inventory, "available_inventory")
        for value, name in (
            (self.quantity_unit, "quantity_unit"),
            (self.price_unit, "price_unit"),
            (self.fee_unit, "fee_unit"),
            (self.quote_currency, "quote_currency"),
        ):
            _text(value, name)
        object.__setattr__(
            self,
            "quote_observation_time",
            _utc(self.quote_observation_time, "quote_observation_time"),
        )
        if self.fill_time is not None:
            object.__setattr__(self, "fill_time", _utc(self.fill_time, "fill_time"))
        if type(self.friction) is not FrictionComponents:
            raise ValueError("friction must be FrictionComponents")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "side": self.side.value,
                "requested_quantity": _decimal_text(self.requested_quantity),
                "quantity_unit": self.quantity_unit,
                "price_unit": self.price_unit,
                "fee_unit": self.fee_unit,
                "quote_currency": self.quote_currency,
                "executable_liquidity": _decimal_text(self.executable_liquidity),
                "reference_quote_price": _decimal_text(self.reference_quote_price),
                "quote_observation_time": self.quote_observation_time,
                "fill_time": self.fill_time,
                "friction": self.friction.canonical_representation,
                "available_inventory": (
                    _decimal_text(self.available_inventory)
                    if self.available_inventory is not None
                    else None
                ),
            }
        )

    @property
    def digest(self) -> str:
        return _digest(self.canonical_representation)


@dataclass(frozen=True)
class PaperLifecycleEvidence:
    """Explicit state, accounting, ledger, and reconciliation evidence."""

    prior_state: PaperPositionExposureState
    target_asset_identity: Mapping[str, Any]
    valuation_context: ValuationContext
    accounting_context: AccountingContext
    lifecycle_reference_time: datetime
    ledger_stream_identity: Mapping[str, Any]
    sequence_number: int
    previous_entry_digest: str | None
    reconciliation_expectation: PaperReconciliationExpectation

    def __post_init__(self) -> None:
        if type(self.prior_state) is not PaperPositionExposureState:
            raise ValueError("prior_state must be PaperPositionExposureState")
        if type(self.valuation_context) is not ValuationContext:
            raise ValueError("valuation_context must be ValuationContext")
        if type(self.accounting_context) is not AccountingContext:
            raise ValueError("accounting_context must be AccountingContext")
        if type(self.reconciliation_expectation) is not PaperReconciliationExpectation:
            raise ValueError(
                "reconciliation_expectation must be PaperReconciliationExpectation"
            )
        object.__setattr__(
            self,
            "target_asset_identity",
            _freeze_mapping(self.target_asset_identity, "target_asset_identity"),
        )
        object.__setattr__(
            self,
            "ledger_stream_identity",
            _freeze_mapping(self.ledger_stream_identity, "ledger_stream_identity"),
        )
        object.__setattr__(
            self,
            "lifecycle_reference_time",
            _utc(self.lifecycle_reference_time, "lifecycle_reference_time"),
        )
        if (
            isinstance(self.sequence_number, bool)
            or not isinstance(self.sequence_number, int)
            or self.sequence_number <= 0
        ):
            raise ValueError("sequence_number must be a positive integer")
        if self.previous_entry_digest is not None:
            _digest_text(self.previous_entry_digest, "previous_entry_digest")

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze(
            {
                "prior_state_digest": self.prior_state.digest,
                "target_asset_identity": self.target_asset_identity,
                "valuation_observation_digests": tuple(
                    value.observation_digest
                    for value in self.valuation_context.observations
                ),
                "accounting_context_digest": self.accounting_context.context_digest,
                "lifecycle_reference_time": self.lifecycle_reference_time,
                "ledger_stream_identity": self.ledger_stream_identity,
                "sequence_number": self.sequence_number,
                "previous_entry_digest": self.previous_entry_digest,
                "reconciliation_expectation_digest": (
                    self.reconciliation_expectation.expectation_digest
                ),
            }
        )

    @property
    def digest(self) -> str:
        return _digest(self.canonical_representation)


@dataclass(frozen=True)
class ControlledPaperLifecycleResult:
    """Immutable result of one P07-T02–T07 and P08-T01 composition."""

    outcome: ControlledPaperLifecycleOutcome | str
    reason_codes: tuple[str, ...]
    admission: ControlledPaperRunAdmissionResult
    fill_outcome: PaperFillOutcome | None = None
    transition: PaperStateTransitionResult | None = None
    ledger_entry: PaperLedgerEntry | None = None
    reconciliation: PaperReconciliationResult | None = None
    paper_result: PaperSimulationResult | None = None
    history_result: PaperSimulationResultHistoryResult | None = None
    observation: OutcomeLearningObservation | None = None
    contract_version: str = P01_RTI_02_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        try:
            outcome = ControlledPaperLifecycleOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported paper lifecycle outcome") from error
        object.__setattr__(self, "outcome", outcome)
        if type(self.admission) is not ControlledPaperRunAdmissionResult:
            raise ValueError("admission must be ControlledPaperRunAdmissionResult")
        if self.contract_version != P01_RTI_02_CONTRACT_VERSION:
            raise ValueError("unsupported P01-RTI-02 contract_version")
        reasons = _reason_codes(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)
        self._validate_shape()
        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("result_digest does not match canonical lifecycle result")
        object.__setattr__(self, "result_digest", expected)

    def _validate_shape(self) -> None:
        if self.outcome is ControlledPaperLifecycleOutcome.OBSERVATION_PRODUCED:
            required = (
                self.fill_outcome,
                self.transition,
                self.ledger_entry,
                self.reconciliation,
                self.paper_result,
                self.history_result,
                self.observation,
            )
            if any(value is None for value in required) or self.reason_codes:
                raise ValueError("completed lifecycle requires every artifact")
            if self.reconciliation.status is not ReconciliationStatus.MATCH:
                raise ValueError("completed lifecycle requires MATCH reconciliation")
            if (
                self.history_result.outcome
                is not PaperSimulationResultHistoryOutcome.STORED
            ):
                raise ValueError("completed lifecycle requires stored history result")
            if self.observation.paper_result_digest != self.paper_result.digest:
                raise ValueError("observation does not link to paper result")
            return
        if self.outcome is ControlledPaperLifecycleOutcome.ADMISSION_NOT_READY:
            if any(
                value is not None
                for value in (
                    self.fill_outcome,
                    self.transition,
                    self.ledger_entry,
                    self.reconciliation,
                    self.paper_result,
                    self.history_result,
                    self.observation,
                )
            ):
                raise ValueError("unready admission cannot contain lifecycle artifacts")
            if not self.reason_codes:
                raise ValueError("unready admission requires reason codes")
            return
        if self.outcome is ControlledPaperLifecycleOutcome.RECONCILIATION_NOT_MATCHED:
            if any(
                value is None
                for value in (
                    self.fill_outcome,
                    self.transition,
                    self.ledger_entry,
                    self.reconciliation,
                )
            ):
                raise ValueError("reconciliation outcome requires P07-T02–T05 artifacts")
            if self.reconciliation.status is ReconciliationStatus.MATCH:
                raise ValueError("reconciliation outcome cannot contain MATCH")
            if any(
                value is not None
                for value in (
                    self.paper_result,
                    self.history_result,
                    self.observation,
                )
            ):
                raise ValueError("non-match cannot contain P07-T06/T07 or P08-T01")
            if not self.reason_codes:
                raise ValueError("non-match requires reason codes")
            return
        if self.observation is not None:
            raise ValueError("invalid lifecycle cannot contain P08-T01 observation")
        if not self.reason_codes:
            raise ValueError("invalid lifecycle requires reason codes")

    def _without_digest(self) -> Mapping[str, Any]:
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "admission_digest": self.admission.digest,
            "fill_digest": _artifact_digest(self.fill_outcome, "outcome_digest"),
            "transition_digest": _artifact_digest(self.transition, "transition_digest"),
            "ledger_digest": _artifact_digest(self.ledger_entry, "entry_digest"),
            "reconciliation_digest": _artifact_digest(
                self.reconciliation, "result_digest"
            ),
            "paper_result_digest": (
                self.paper_result.digest if self.paper_result is not None else None
            ),
            "history_digest": (
                self.history_result.history_digest
                if self.history_result is not None
                else None
            ),
            "observation_digest": (
                self.observation.digest if self.observation is not None else None
            ),
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return _freeze({**self._without_digest(), "result_digest": self.result_digest})

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


def run_controlled_paper_lifecycle(
    admission: ControlledPaperRunAdmissionResult,
    *,
    fill_instruction: PaperFillInstruction,
    lifecycle_evidence: PaperLifecycleEvidence,
) -> ControlledPaperLifecycleResult:
    """Run one explicit paper lifecycle without external I/O or persistence."""

    if type(admission) is not ControlledPaperRunAdmissionResult:
        raise ValueError("admission must be ControlledPaperRunAdmissionResult")
    try:
        canonical_admission = replace(admission)
    except (AttributeError, TypeError, ValueError):
        return _invalid(admission, "ADMISSION_INVALID_OR_TAMPERED")
    if canonical_admission != admission:
        return _invalid(admission, "ADMISSION_NON_CANONICAL")
    if (
        admission.outcome
        is not ControlledPaperRunAdmissionOutcome.READY_FOR_PAPER_SIMULATION
        or admission.paper_simulation_input is None
        or admission.decision_intent is None
    ):
        reasons = admission.reason_codes or (admission.outcome.value,)
        return ControlledPaperLifecycleResult(
            outcome=ControlledPaperLifecycleOutcome.ADMISSION_NOT_READY,
            reason_codes=reasons,
            admission=admission,
        )
    if type(fill_instruction) is not PaperFillInstruction:
        return _invalid(admission, "FILL_INSTRUCTION_REQUIRED")
    if type(lifecycle_evidence) is not PaperLifecycleEvidence:
        return _invalid(admission, "LIFECYCLE_EVIDENCE_REQUIRED")

    simulation_input = admission.paper_simulation_input
    fill: PaperFillOutcome | None = None
    transition: PaperStateTransitionResult | None = None
    ledger: PaperLedgerEntry | None = None
    reconciliation: PaperReconciliationResult | None = None
    paper_result: PaperSimulationResult | None = None
    history_result: PaperSimulationResultHistoryResult | None = None

    try:
        fill = evaluate_paper_fill(
            simulation_input,
            side=fill_instruction.side,
            requested_quantity=fill_instruction.requested_quantity,
            quantity_unit=fill_instruction.quantity_unit,
            price_unit=fill_instruction.price_unit,
            fee_unit=fill_instruction.fee_unit,
            quote_currency=fill_instruction.quote_currency,
            executable_liquidity=fill_instruction.executable_liquidity,
            reference_quote_price=fill_instruction.reference_quote_price,
            quote_observation_time=fill_instruction.quote_observation_time,
            fill_time=fill_instruction.fill_time,
            friction=fill_instruction.friction,
            available_inventory=fill_instruction.available_inventory,
        )
        transition = transition_paper_state(
            fill,
            lifecycle_evidence.prior_state,
            target_asset_identity=lifecycle_evidence.target_asset_identity,
            valuation_context=lifecycle_evidence.valuation_context,
            accounting_context=lifecycle_evidence.accounting_context,
            transition_reference_time=lifecycle_evidence.lifecycle_reference_time,
        )
        ledger = create_paper_ledger_entry(
            simulation_input,
            fill,
            transition,
            ledger_stream_identity=lifecycle_evidence.ledger_stream_identity,
            sequence_number=lifecycle_evidence.sequence_number,
            previous_entry_digest=lifecycle_evidence.previous_entry_digest,
            ledger_reference_time=lifecycle_evidence.lifecycle_reference_time,
        )
        reconciliation = reconcile_paper_ledger(
            (ledger,),
            lifecycle_evidence.reconciliation_expectation,
        )
    except (AttributeError, ArithmeticError, KeyError, TypeError, ValueError):
        return _invalid(
            admission,
            "P07_LIFECYCLE_INVALID_INPUT",
            fill=fill,
            transition=transition,
            ledger=ledger,
            reconciliation=reconciliation,
        )

    if reconciliation.status is not ReconciliationStatus.MATCH:
        reasons = reconciliation.reason_codes or (reconciliation.status.value,)
        return ControlledPaperLifecycleResult(
            outcome=ControlledPaperLifecycleOutcome.RECONCILIATION_NOT_MATCHED,
            reason_codes=reasons,
            admission=admission,
            fill_outcome=fill,
            transition=transition,
            ledger_entry=ledger,
            reconciliation=reconciliation,
        )

    try:
        paper_result = PaperSimulationResult.from_predecessors(
            simulation_input=simulation_input,
            fill_outcome=fill,
            transition=transition,
            ledger_entries=(ledger,),
            reconciliation=reconciliation,
        )
        history = PaperSimulationResultHistory()
        history_result = history.append(paper_result)
        if history_result.outcome is not PaperSimulationResultHistoryOutcome.STORED:
            return _invalid(
                admission,
                "P07_HISTORY_REJECTED",
                fill=fill,
                transition=transition,
                ledger=ledger,
                reconciliation=reconciliation,
                paper_result=paper_result,
                history_result=history_result,
            )
        observation = create_outcome_learning_observation(
            admission.decision_intent,
            simulation_input,
            paper_result,
            history,
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        return _invalid(
            admission,
            "P07_P08_ASSEMBLY_INVALID_INPUT",
            fill=fill,
            transition=transition,
            ledger=ledger,
            reconciliation=reconciliation,
            paper_result=paper_result,
            history_result=history_result,
        )

    return ControlledPaperLifecycleResult(
        outcome=ControlledPaperLifecycleOutcome.OBSERVATION_PRODUCED,
        reason_codes=(),
        admission=admission,
        fill_outcome=fill,
        transition=transition,
        ledger_entry=ledger,
        reconciliation=reconciliation,
        paper_result=paper_result,
        history_result=history_result,
        observation=observation,
    )


def _invalid(
    admission: ControlledPaperRunAdmissionResult,
    reason: str,
    *,
    fill: PaperFillOutcome | None = None,
    transition: PaperStateTransitionResult | None = None,
    ledger: PaperLedgerEntry | None = None,
    reconciliation: PaperReconciliationResult | None = None,
    paper_result: PaperSimulationResult | None = None,
    history_result: PaperSimulationResultHistoryResult | None = None,
) -> ControlledPaperLifecycleResult:
    return ControlledPaperLifecycleResult(
        outcome=ControlledPaperLifecycleOutcome.INVALID_INPUT,
        reason_codes=(reason,),
        admission=admission,
        fill_outcome=fill,
        transition=transition,
        ledger_entry=ledger,
        reconciliation=reconciliation,
        paper_result=paper_result,
        history_result=history_result,
    )


def _artifact_digest(value: Any, name: str) -> str | None:
    return getattr(value, name) if value is not None else None


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be canonical non-empty text")
    return value


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{name} must be a finite Decimal")
    return value


def _decimal_text(value: Decimal) -> str:
    return format(Decimal("0") if value == 0 else value.normalize(), "f")


def _utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _digest_text(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _reason_codes(value: Any) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValueError("reason_codes must be an immutable tuple")
    if any(not isinstance(item, str) or not item or item != item.strip() for item in value):
        raise ValueError("reason_codes must contain canonical non-empty text")
    if len(set(value)) != len(value):
        raise ValueError("reason_codes must not contain duplicates")
    return value


def _freeze_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{name} must be a non-empty mapping")
    if any(not isinstance(key, str) or not key for key in value):
        raise ValueError(f"{name} keys must be non-empty strings")
    return _freeze(value)


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(child) for child in value)
    return value


def _canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return _utc(value, "timestamp").isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(child) for child in value]
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


__all__ = [
    "P01_RTI_02_CONTRACT_VERSION",
    "ControlledPaperLifecycleOutcome",
    "ControlledPaperLifecycleResult",
    "PaperFillInstruction",
    "PaperLifecycleEvidence",
    "run_controlled_paper_lifecycle",
]
