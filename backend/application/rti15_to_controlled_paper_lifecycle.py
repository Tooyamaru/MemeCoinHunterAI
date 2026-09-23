"""P01-RTI-16: one exact RTI-15 admission through the existing RTI-02 owner."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from enum import StrEnum
import hashlib
import json
from typing import Any, Callable

from backend.application.risk_capital_to_paper_admission_continuation import (
    P01_RTI_15_CONTRACT_VERSION,
    P01Rti15PaperAdmissionContinuationResult,
    RiskCapitalToPaperAdmissionOutcome,
)
from core.runtime.controlled_paper_run_admission import (
    P01_RTI_01_CONTRACT_VERSION,
    ControlledPaperRunAdmissionOutcome,
    ControlledPaperRunAdmissionResult,
)
from core.runtime.controlled_paper_lifecycle import (
    P01_RTI_02_CONTRACT_VERSION,
    ControlledPaperLifecycleResult,
    PaperFillInstruction,
    PaperLifecycleEvidence,
    run_controlled_paper_lifecycle,
)


P01_RTI_16_CONTRACT_VERSION = "p01-rti-16-v1"


class Rti15ToControlledLifecycleOutcome(StrEnum):
    LIFECYCLE_MATERIALIZED = "LIFECYCLE_MATERIALIZED"
    UPSTREAM_NOT_ADMITTED = "UPSTREAM_NOT_ADMITTED"
    LIFECYCLE_UNAVAILABLE = "LIFECYCLE_UNAVAILABLE"


_UNAVAILABLE_REASONS = frozenset({
    "ADMISSION_ENVELOPE_UNAVAILABLE",
    "ADMISSION_ENVELOPE_INVALID_RESULT",
    "LIFECYCLE_UNAVAILABLE",
    "LIFECYCLE_INVALID_RESULT",
})


@dataclass(frozen=True)
class P01Rti16ControlledPaperLifecycleContinuationResult:
    upstream_result: P01Rti15PaperAdmissionContinuationResult
    fill_instruction: PaperFillInstruction
    lifecycle_evidence: PaperLifecycleEvidence
    outcome: Rti15ToControlledLifecycleOutcome | str
    reason_codes: tuple[str, ...]
    compatibility_admission: ControlledPaperRunAdmissionResult | None = None
    lifecycle_result: ControlledPaperLifecycleResult | None = None
    contract_version: str = P01_RTI_16_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        _validate_inputs(self.upstream_result, self.fill_instruction, self.lifecycle_evidence)
        if self.contract_version != P01_RTI_16_CONTRACT_VERSION:
            raise ValueError("unsupported RTI-16 contract version")
        try:
            outcome = Rti15ToControlledLifecycleOutcome(self.outcome)
        except (TypeError, ValueError):
            raise ValueError("unsupported RTI-16 outcome") from None
        object.__setattr__(self, "outcome", outcome)
        if type(self.reason_codes) is not tuple or any(
            type(reason) is not str or not reason for reason in self.reason_codes
        ):
            raise ValueError("invalid RTI-16 reasons")
        if outcome is Rti15ToControlledLifecycleOutcome.UPSTREAM_NOT_ADMITTED:
            if (self.upstream_result.outcome is RiskCapitalToPaperAdmissionOutcome.ADMISSION_MATERIALIZED
                or self.reason_codes != ("UPSTREAM_NOT_ADMITTED",)
                or self.compatibility_admission is not None or self.lifecycle_result is not None):
                raise ValueError("invalid upstream stop result")
        elif outcome is Rti15ToControlledLifecycleOutcome.LIFECYCLE_MATERIALIZED:
            if (self.upstream_result.outcome is not RiskCapitalToPaperAdmissionOutcome.ADMISSION_MATERIALIZED
                or self.reason_codes or not _valid_admission(self.compatibility_admission, self.upstream_result)
                or not _valid_lifecycle(self.lifecycle_result, self.compatibility_admission)):
                raise ValueError("invalid lifecycle materialization")
        else:
            if (self.upstream_result.outcome is not RiskCapitalToPaperAdmissionOutcome.ADMISSION_MATERIALIZED
                or len(self.reason_codes) != 1 or self.reason_codes[0] not in _UNAVAILABLE_REASONS
                or self.lifecycle_result is not None):
                raise ValueError("invalid lifecycle unavailable result")
            if self.reason_codes[0].startswith("ADMISSION_ENVELOPE_"):
                if self.compatibility_admission is not None:
                    raise ValueError("unavailable admission must be absent")
            elif not _valid_admission(self.compatibility_admission, self.upstream_result):
                raise ValueError("unavailable lifecycle requires canonical admission")
        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("RTI-16 result digest mismatch")
        object.__setattr__(self, "result_digest", expected)

    def _without_digest(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "rti15_contract_version": self.upstream_result.contract_version,
            "rti15_outcome": self.upstream_result.outcome.value,
            "rti15_result_digest": self.upstream_result.digest,
            "compatibility_admission_contract_version": self.compatibility_admission.contract_version if self.compatibility_admission else None,
            "compatibility_admission_digest": self.compatibility_admission.digest if self.compatibility_admission else None,
            "fill_instruction_digest": self.fill_instruction.digest,
            "lifecycle_evidence_digest": self.lifecycle_evidence.digest,
            "rti02_contract_version": self.lifecycle_result.contract_version if self.lifecycle_result else None,
            "rti02_outcome": self.lifecycle_result.outcome.value if self.lifecycle_result else None,
            "rti02_result_digest": self.lifecycle_result.digest if self.lifecycle_result else None,
        }

    @property
    def canonical_representation(self) -> dict[str, Any]:
        return {**self._without_digest(), "result_digest": self.result_digest}

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


AdmissionFactory = Callable[..., ControlledPaperRunAdmissionResult]
LifecycleOwner = Callable[..., ControlledPaperLifecycleResult]


class Rti15ToControlledPaperLifecycleContinuationService:
    def __init__(
        self,
        *,
        admission_factory: AdmissionFactory = ControlledPaperRunAdmissionResult,
        lifecycle_owner: LifecycleOwner = run_controlled_paper_lifecycle,
    ) -> None:
        if not callable(admission_factory) or not callable(lifecycle_owner):
            raise ValueError("RTI-16 delegates must be callable")
        self._admission_factory = admission_factory
        self._lifecycle_owner = lifecycle_owner

    def continue_to_controlled_paper_lifecycle(
        self,
        upstream_result: P01Rti15PaperAdmissionContinuationResult,
        fill_instruction: PaperFillInstruction,
        lifecycle_evidence: PaperLifecycleEvidence,
    ) -> P01Rti16ControlledPaperLifecycleContinuationResult:
        _validate_inputs(upstream_result, fill_instruction, lifecycle_evidence)
        common = dict(upstream_result=upstream_result, fill_instruction=fill_instruction,
                      lifecycle_evidence=lifecycle_evidence)
        if upstream_result.outcome is not RiskCapitalToPaperAdmissionOutcome.ADMISSION_MATERIALIZED:
            return P01Rti16ControlledPaperLifecycleContinuationResult(
                **common, outcome=Rti15ToControlledLifecycleOutcome.UPSTREAM_NOT_ADMITTED,
                reason_codes=("UPSTREAM_NOT_ADMITTED",))

        decision = upstream_result.upstream_result.upstream_result.decision_intent
        authorization = upstream_result.upstream_result.authorization_result
        paper_input = upstream_result.paper_simulation_input
        try:
            admission = self._admission_factory(
                outcome=ControlledPaperRunAdmissionOutcome.READY_FOR_PAPER_SIMULATION,
                reason_codes=(), decision_intent=decision,
                risk_capital_authorization=authorization,
                paper_simulation_input=paper_input,
                contract_version=P01_RTI_01_CONTRACT_VERSION,
            )
        except ValueError:
            raise ValueError("RTI-16 admission validation failed") from None
        except Exception:
            return _unavailable(common, "ADMISSION_ENVELOPE_UNAVAILABLE")
        if not _valid_admission(admission, upstream_result):
            return _unavailable(common, "ADMISSION_ENVELOPE_INVALID_RESULT")
        try:
            lifecycle = self._lifecycle_owner(
                admission, fill_instruction=fill_instruction,
                lifecycle_evidence=lifecycle_evidence)
        except ValueError:
            raise ValueError("RTI-16 lifecycle validation failed") from None
        except Exception:
            return _unavailable(common, "LIFECYCLE_UNAVAILABLE", admission)
        if not _valid_lifecycle(lifecycle, admission):
            return _unavailable(common, "LIFECYCLE_INVALID_RESULT", admission)
        return P01Rti16ControlledPaperLifecycleContinuationResult(
            **common, outcome=Rti15ToControlledLifecycleOutcome.LIFECYCLE_MATERIALIZED,
            reason_codes=(), compatibility_admission=admission, lifecycle_result=lifecycle)

    materialize = continue_to_controlled_paper_lifecycle


def _unavailable(common: dict[str, Any], reason: str,
                 admission: ControlledPaperRunAdmissionResult | None = None) -> P01Rti16ControlledPaperLifecycleContinuationResult:
    return P01Rti16ControlledPaperLifecycleContinuationResult(
        **common, outcome=Rti15ToControlledLifecycleOutcome.LIFECYCLE_UNAVAILABLE,
        reason_codes=(reason,), compatibility_admission=admission)


def _canonical(value: Any, expected_type: type) -> bool:
    if type(value) is not expected_type:
        return False
    try:
        # Replay every nested owner's constructor without replacing the linked
        # objects supplied to its parent: several owner contracts require exact
        # predecessor identity, not merely equal canonical values.
        rebuilt = _rebuild_preserving_links(value)
        return type(rebuilt) is expected_type and rebuilt == value
    except (AttributeError, TypeError, ValueError, KeyError, ArithmeticError):
        return False


def _rebuild_preserving_links(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            _rebuild_preserving_links(getattr(value, field.name))
        rebuilt = replace(value)
        if rebuilt != value:
            raise ValueError("nested owner is not canonical")
        return rebuilt
    if isinstance(value, tuple):
        for child in value:
            _rebuild_preserving_links(child)
    return value


def _validate_inputs(upstream: Any, fill: Any, evidence: Any) -> None:
    for value, expected in (
        (upstream, P01Rti15PaperAdmissionContinuationResult),
        (fill, PaperFillInstruction), (evidence, PaperLifecycleEvidence),
    ):
        if not _canonical(value, expected):
            raise ValueError("RTI-16 input is not canonical")
    if upstream.contract_version != P01_RTI_15_CONTRACT_VERSION:
        raise ValueError("unsupported RTI-15 contract version")


def _valid_admission(admission: Any, upstream: P01Rti15PaperAdmissionContinuationResult) -> bool:
    try:
        return (
            _canonical(admission, ControlledPaperRunAdmissionResult)
            and admission.contract_version == P01_RTI_01_CONTRACT_VERSION
            and admission.outcome is ControlledPaperRunAdmissionOutcome.READY_FOR_PAPER_SIMULATION
            and admission.reason_codes == ()
            and admission.decision_intent is upstream.upstream_result.upstream_result.decision_intent
            and admission.risk_capital_authorization is upstream.upstream_result.authorization_result
            and admission.paper_simulation_input is upstream.paper_simulation_input
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _valid_lifecycle(value: Any, admission: ControlledPaperRunAdmissionResult) -> bool:
    try:
        return (
            _canonical(value, ControlledPaperLifecycleResult)
            and value.contract_version == P01_RTI_02_CONTRACT_VERSION
            and value.admission is admission
            and value.admission.digest == admission.digest
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode("utf-8")).hexdigest()


__all__ = ["P01_RTI_16_CONTRACT_VERSION", "Rti15ToControlledLifecycleOutcome",
           "P01Rti16ControlledPaperLifecycleContinuationResult",
           "Rti15ToControlledPaperLifecycleContinuationService"]
