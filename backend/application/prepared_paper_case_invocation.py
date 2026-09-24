"""P01-OCI-01: explicitly hand one prepared case to the existing OSC-02 owner."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import hashlib
import json
from typing import Any, Mapping

from backend.application.controlled_paper_experiment_input_preparation import (
    ControlledInputPreparationOutcome,
    P01_CIP_01_CONTRACT_VERSION,
    P01Cip01Result,
)
from backend.application.prevalidated_risk_capital_suffix_caller import (
    P01_OSC_02_CONTRACT_VERSION,
    P01Osc02Result,
    PrevalidatedRiskCapitalSuffixCaller,
)


P01_OCI_01_CONTRACT_VERSION = "p01-oci-01-v1"


class PreparedPaperInvocationOutcome(StrEnum):
    OSC_RESULT_RETURNED = "OSC_RESULT_RETURNED"
    CASE_NOT_PREPARED = "CASE_NOT_PREPARED"
    OSC_UNAVAILABLE = "OSC_UNAVAILABLE"


def _canonical_cip(value: Any) -> bool:
    if type(value) is not P01Cip01Result:
        return False
    try:
        return replace(value) == value
    except (AttributeError, TypeError, ValueError, KeyError, ArithmeticError):
        return False


def _canonical_osc(value: Any, source: P01Cip01Result) -> bool:
    if type(value) is not P01Osc02Result:
        return False
    try:
        return (
            replace(value) == value
            and value.contract_version == P01_OSC_02_CONTRACT_VERSION
            and value.request is source.osc02_request
            and value.request.invocation_id == source.request.invocation_id
            and value.request.input_digests == source.osc02_request.input_digests
        )
    except (AttributeError, TypeError, ValueError, KeyError, ArithmeticError):
        return False


def _digest(material: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=True).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class P01Oci01Request:
    cip_result: P01Cip01Result
    contract_version: str = P01_OCI_01_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_OCI_01_CONTRACT_VERSION:
            raise ValueError("unsupported OCI-01 contract version")
        if not _canonical_cip(self.cip_result):
            raise ValueError("noncanonical CIP-01 result")
        if self.cip_result.contract_version != P01_CIP_01_CONTRACT_VERSION:
            raise ValueError("unsupported CIP-01 contract version")


@dataclass(frozen=True)
class P01Oci01Result:
    request: P01Oci01Request
    outcome: PreparedPaperInvocationOutcome
    reason_codes: tuple[str, ...]
    terminal_stage: str
    osc02_result: P01Osc02Result | None = None
    contract_version: str = P01_OCI_01_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        if type(self.request) is not P01Oci01Request:
            raise ValueError("invalid OCI-01 request")
        self.request.__post_init__()
        if self.contract_version != P01_OCI_01_CONTRACT_VERSION:
            raise ValueError("unsupported OCI-01 result version")
        if type(self.outcome) is not PreparedPaperInvocationOutcome:
            raise ValueError("unsupported OCI-01 outcome")
        expected = {
            PreparedPaperInvocationOutcome.OSC_RESULT_RETURNED: (
                "OSC-02", (), True,
            ),
            PreparedPaperInvocationOutcome.CASE_NOT_PREPARED: (
                "CIP-01", ("CASE_NOT_PREPARED",), False,
            ),
            PreparedPaperInvocationOutcome.OSC_UNAVAILABLE: (
                "OSC-02", ("OSC-02_UNAVAILABLE",), False,
            ),
        }[self.outcome]
        if (
            self.terminal_stage != expected[0]
            or self.reason_codes != expected[1]
            or (self.osc02_result is not None) != expected[2]
        ):
            raise ValueError("invalid OCI-01 result shape")
        cip = self.request.cip_result
        if self.outcome is PreparedPaperInvocationOutcome.CASE_NOT_PREPARED:
            if cip.outcome is ControlledInputPreparationOutcome.REQUEST_PREPARED:
                raise ValueError("prepared case cannot stop before OSC-02")
        else:
            if cip.outcome is not ControlledInputPreparationOutcome.REQUEST_PREPARED:
                raise ValueError("non-ready case cannot reach OSC-02")
        if self.osc02_result is not None and not _canonical_osc(self.osc02_result, cip):
            raise ValueError("invalid exact OSC-02 result")
        expected_digest = _digest(self._material())
        if self.result_digest is not None and self.result_digest != expected_digest:
            raise ValueError("OCI-01 result digest mismatch")
        object.__setattr__(self, "result_digest", expected_digest)

    def _material(self) -> Mapping[str, Any]:
        cip = self.request.cip_result
        prepared = cip.osc02_request
        osc = self.osc02_result
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "terminal_stage": self.terminal_stage,
            "cip_contract_version": cip.contract_version,
            "cip_outcome": cip.outcome.value,
            "invocation_id": cip.request.invocation_id,
            "cip_result_digest": cip.result_digest,
            "prepared_request_present": prepared is not None,
            "prepared_osc_contract": prepared.contract_version if prepared else None,
            "prepared_input_digests": prepared.input_digests if prepared else None,
            "osc_result_present": osc is not None,
            "osc_contract_version": osc.contract_version if osc else None,
            "osc_outcome": osc.outcome.value if osc else None,
            "osc_reason_codes": osc.reason_codes if osc else None,
            "osc_terminal_stage": osc.terminal_stage if osc else None,
            "osc_result_digest": osc.result_digest if osc else None,
            "osc_input_digests": osc.request.input_digests if osc else None,
        }

    @property
    def canonical_representation(self) -> Mapping[str, Any]:
        return {**self._material(), "result_digest": self.result_digest}


class PreparedPaperCaseInvocationService:
    def __init__(self, *, osc02: Any = None) -> None:
        self._osc02 = osc02 if osc02 is not None else PrevalidatedRiskCapitalSuffixCaller()
        if not callable(getattr(self._osc02, "run", None)):
            raise ValueError("invalid OSC-02 owner seam")

    def run(self, request: P01Oci01Request) -> P01Oci01Result:
        if type(request) is not P01Oci01Request:
            raise ValueError("invalid OCI-01 request")
        request.__post_init__()
        cip = request.cip_result
        if cip.outcome is not ControlledInputPreparationOutcome.REQUEST_PREPARED:
            return P01Oci01Result(
                request, PreparedPaperInvocationOutcome.CASE_NOT_PREPARED,
                ("CASE_NOT_PREPARED",), "CIP-01",
            )

        # CIP constructed and validated this exact request; never reconstruct it.
        try:
            osc = self._osc02.run(cip.osc02_request)
        except ValueError:
            raise ValueError("OSC-02 validation failed") from None
        except Exception:
            return P01Oci01Result(
                request, PreparedPaperInvocationOutcome.OSC_UNAVAILABLE,
                ("OSC-02_UNAVAILABLE",), "OSC-02",
            )
        if not _canonical_osc(osc, cip):
            return P01Oci01Result(
                request, PreparedPaperInvocationOutcome.OSC_UNAVAILABLE,
                ("OSC-02_UNAVAILABLE",), "OSC-02",
            )
        return P01Oci01Result(
            request, PreparedPaperInvocationOutcome.OSC_RESULT_RETURNED,
            (), "OSC-02", osc,
        )


__all__ = [
    "P01_OCI_01_CONTRACT_VERSION",
    "PreparedPaperInvocationOutcome",
    "P01Oci01Request",
    "P01Oci01Result",
    "PreparedPaperCaseInvocationService",
]
