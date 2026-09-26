"""Explicit one-shot OAF persistence over one exact lifecycle-bearing run."""

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
from backend.application.paper_lifecycle_persistence import (
    PaperLifecyclePersistenceResult,
)


P01_OAF_PERSIST_ONCE_VERSION = "p01-oaf-01-persist-once-v1"


class OperatorPaperPersistOutcome(StrEnum):
    PERSIST_TERMINAL = "PERSIST_TERMINAL"
    CASE_NOT_FOUND = "CASE_NOT_FOUND"
    CASE_DIGEST_MISMATCH = "CASE_DIGEST_MISMATCH"
    OCI_DIGEST_MISMATCH = "OCI_DIGEST_MISMATCH"
    OSC_DIGEST_MISMATCH = "OSC_DIGEST_MISMATCH"
    LIFECYCLE_DIGEST_MISMATCH = "LIFECYCLE_DIGEST_MISMATCH"
    CASE_NOT_PERSISTABLE = "CASE_NOT_PERSISTABLE"
    PERSIST_OUTCOME_UNKNOWN = "PERSIST_OUTCOME_UNKNOWN"


@dataclass(frozen=True)
class OperatorPaperPersistResult:
    outcome: OperatorPaperPersistOutcome
    record: OperatorPaperCaseRecord | None
    reason_codes: tuple[str, ...]
    contract_version: str = P01_OAF_PERSIST_ONCE_VERSION


class OperatorPaperCasePersistService:
    """Claim once, persist the exact lifecycle through RTI-03, then stop."""

    def __init__(
        self,
        *,
        registry: OperatorPaperCaseRegistry,
        persistence: Any,
    ) -> None:
        self._registry = registry
        self._persistence = persistence
        if not callable(getattr(self._persistence, "persist", None)):
            raise ValueError("invalid RTI-03 persistence seam")

    async def persist_once(
        self,
        *,
        handle: str,
        case_digest: str,
        oci_digest: str,
        osc_digest: str,
        lifecycle_result_digest: str,
    ) -> OperatorPaperPersistResult:
        try:
            claimed = self._registry.claim_persist(
                handle,
                case_digest=case_digest,
                oci_digest=oci_digest,
                osc_digest=osc_digest,
                lifecycle_result_digest=lifecycle_result_digest,
            )
        except OperatorPaperCaseRegistryError as exc:
            mapping = {
                "CASE_NOT_FOUND": OperatorPaperPersistOutcome.CASE_NOT_FOUND,
                "CASE_DIGEST_MISMATCH": OperatorPaperPersistOutcome.CASE_DIGEST_MISMATCH,
                "OCI_DIGEST_MISMATCH": OperatorPaperPersistOutcome.OCI_DIGEST_MISMATCH,
                "OSC_DIGEST_MISMATCH": OperatorPaperPersistOutcome.OSC_DIGEST_MISMATCH,
                "LIFECYCLE_DIGEST_MISMATCH": OperatorPaperPersistOutcome.LIFECYCLE_DIGEST_MISMATCH,
                "CASE_NOT_PERSISTABLE": OperatorPaperPersistOutcome.CASE_NOT_PERSISTABLE,
            }
            outcome = mapping.get(
                exc.code,
                OperatorPaperPersistOutcome.CASE_NOT_PERSISTABLE,
            )
            return OperatorPaperPersistResult(outcome, None, (exc.code,))

        oci = claimed.oci_result
        osc = oci.osc02_result if oci is not None else None
        lifecycle = osc.lifecycle_result if osc is not None else None
        if lifecycle is None:
            unknown = self._registry.mark_persist_unknown(handle)
            return OperatorPaperPersistResult(
                OperatorPaperPersistOutcome.PERSIST_OUTCOME_UNKNOWN,
                unknown,
                ("LIFECYCLE_RESULT_UNAVAILABLE",),
            )

        try:
            owner_result = await self._persistence.persist(lifecycle)
        except Exception:
            unknown = self._registry.mark_persist_unknown(handle)
            return OperatorPaperPersistResult(
                OperatorPaperPersistOutcome.PERSIST_OUTCOME_UNKNOWN,
                unknown,
                ("PERSIST_OUTCOME_UNKNOWN",),
            )

        if not isinstance(owner_result, PaperLifecyclePersistenceResult):
            unknown = self._registry.mark_persist_unknown(handle)
            return OperatorPaperPersistResult(
                OperatorPaperPersistOutcome.PERSIST_OUTCOME_UNKNOWN,
                unknown,
                ("PERSIST_RESULT_INVALID",),
            )
        if owner_result.lifecycle_result_digest not in (None, lifecycle.digest):
            unknown = self._registry.mark_persist_unknown(handle)
            return OperatorPaperPersistResult(
                OperatorPaperPersistOutcome.PERSIST_OUTCOME_UNKNOWN,
                unknown,
                ("PERSIST_RESULT_IDENTITY_MISMATCH",),
            )

        terminal = self._registry.complete_persist(
            handle,
            persistence_result=owner_result,
        )
        if terminal.state is not OperatorPaperCaseState.PERSIST_TERMINAL:
            raise RuntimeError("PERSIST_TERMINAL state was not retained")
        return OperatorPaperPersistResult(
            OperatorPaperPersistOutcome.PERSIST_TERMINAL,
            terminal,
            (),
        )


__all__ = [
    "OperatorPaperCasePersistService",
    "OperatorPaperPersistOutcome",
    "OperatorPaperPersistResult",
    "P01_OAF_PERSIST_ONCE_VERSION",
]
