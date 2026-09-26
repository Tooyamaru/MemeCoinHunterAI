"""One-shot operator run orchestration over an exact prepared OAF case."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from backend.application.operator_paper_case_registry import (
    OperatorPaperCaseRecord,
    OperatorPaperCaseRegistry,
    OperatorPaperCaseRegistryError,
    OperatorPaperCaseState,
)
from backend.application.prepared_paper_case_invocation import (
    P01Oci01Request,
    P01Oci01Result,
    PreparedPaperCaseInvocationService,
)


P01_OAF_RUN_ONCE_VERSION = "p01-oaf-01-run-once-v1"


class OperatorPaperRunOutcome(StrEnum):
    RUN_TERMINAL = "RUN_TERMINAL"
    CASE_NOT_FOUND = "CASE_NOT_FOUND"
    CASE_DIGEST_MISMATCH = "CASE_DIGEST_MISMATCH"
    CASE_NOT_RUNNABLE = "CASE_NOT_RUNNABLE"
    RUN_OUTCOME_UNKNOWN = "RUN_OUTCOME_UNKNOWN"


@dataclass(frozen=True)
class OperatorPaperRunResult:
    outcome: OperatorPaperRunOutcome
    record: OperatorPaperCaseRecord | None
    reason_codes: tuple[str, ...]
    contract_version: str = P01_OAF_RUN_ONCE_VERSION


class OperatorPaperCaseRunService:
    """Atomically claim, invoke OCI once, then retain exact terminal result."""

    def __init__(
        self,
        *,
        registry: OperatorPaperCaseRegistry,
        oci: Any = None,
    ) -> None:
        self._registry = registry
        self._oci = oci if oci is not None else PreparedPaperCaseInvocationService()
        if not callable(getattr(self._oci, "run", None)):
            raise ValueError("invalid OCI-01 owner seam")

    def run_once(self, *, handle: str, case_digest: str) -> OperatorPaperRunResult:
        try:
            claimed = self._registry.claim_run(handle, case_digest=case_digest)
        except OperatorPaperCaseRegistryError as exc:
            mapping = {
                "CASE_NOT_FOUND": OperatorPaperRunOutcome.CASE_NOT_FOUND,
                "CASE_DIGEST_MISMATCH": OperatorPaperRunOutcome.CASE_DIGEST_MISMATCH,
                "CASE_NOT_RUNNABLE": OperatorPaperRunOutcome.CASE_NOT_RUNNABLE,
            }
            outcome = mapping.get(exc.code, OperatorPaperRunOutcome.CASE_NOT_RUNNABLE)
            return OperatorPaperRunResult(outcome, None, (exc.code,))

        request = P01Oci01Request(claimed.prepared.cip_result)
        try:
            result = self._oci.run(request)
        except Exception:
            unknown = self._registry.mark_run_unknown(handle)
            return OperatorPaperRunResult(
                OperatorPaperRunOutcome.RUN_OUTCOME_UNKNOWN,
                unknown,
                ("RUN_OUTCOME_UNKNOWN",),
            )

        if not isinstance(result, P01Oci01Result) or result.request is not request:
            unknown = self._registry.mark_run_unknown(handle)
            return OperatorPaperRunResult(
                OperatorPaperRunOutcome.RUN_OUTCOME_UNKNOWN,
                unknown,
                ("RUN_RESULT_INVALID",),
            )

        terminal = self._registry.complete_run(handle, oci_result=result)
        if terminal.state is not OperatorPaperCaseState.RUN_TERMINAL:
            raise RuntimeError("RUN_TERMINAL state was not retained")
        return OperatorPaperRunResult(
            OperatorPaperRunOutcome.RUN_TERMINAL,
            terminal,
            (),
        )


__all__ = [
    "OperatorPaperCaseRunService",
    "OperatorPaperRunOutcome",
    "OperatorPaperRunResult",
    "P01_OAF_RUN_ONCE_VERSION",
]
