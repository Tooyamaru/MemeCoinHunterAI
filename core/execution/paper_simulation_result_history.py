"""Deterministic in-memory history for P07-T06 simulation results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Any

from core.execution.paper_simulation_result import (
    P07_T06_CONTRACT_VERSION,
    PaperSimulationResult,
)


P07_T07_CONTRACT_VERSION = "p07-t07-v1"


class PaperSimulationResultHistoryOutcome(StrEnum):
    """Observable result of one local history insertion attempt."""

    STORED = "STORED"
    DUPLICATE = "DUPLICATE"
    INVALID_INPUT = "INVALID_INPUT"

    ACCEPTED = "STORED"
    INVALID = "INVALID_INPUT"


@dataclass(frozen=True)
class PaperSimulationResultHistoryResult:
    """Immutable result and read view for one history insertion attempt."""

    outcome: PaperSimulationResultHistoryOutcome
    accepted: bool
    result: PaperSimulationResult | None
    results: tuple[PaperSimulationResult, ...]
    reason_codes: tuple[str, ...]
    history_digest: str
    contract_version: str = P07_T07_CONTRACT_VERSION

    def __post_init__(self) -> None:
        try:
            outcome = PaperSimulationResultHistoryOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "outcome must be a PaperSimulationResultHistoryOutcome"
            ) from error
        object.__setattr__(self, "outcome", outcome)
        if self.accepted is not (outcome is PaperSimulationResultHistoryOutcome.STORED):
            raise ValueError("accepted must match the STORED outcome")
        values = tuple(self.results)
        if not all(isinstance(value, PaperSimulationResult) for value in values):
            raise ValueError(
                "results must contain PaperSimulationResult values"
            )
        object.__setattr__(self, "results", values)
        if outcome is PaperSimulationResultHistoryOutcome.INVALID_INPUT:
            if self.result is not None:
                raise ValueError("invalid history input cannot contain a result")
        elif not isinstance(self.result, PaperSimulationResult):
            raise ValueError("valid history outcomes require a result")
        reasons = tuple(self.reason_codes)
        if any(not isinstance(value, str) or not value.strip() for value in reasons):
            raise ValueError("reason_codes must contain non-empty strings")
        object.__setattr__(
            self,
            "reason_codes",
            tuple(sorted(dict.fromkeys(reasons))),
        )
        _require_text(self.history_digest, "history_digest")
        if self.contract_version != P07_T07_CONTRACT_VERSION:
            raise ValueError("unsupported P07-T07 contract version")

    @property
    def status(self) -> PaperSimulationResultHistoryOutcome:
        return self.outcome

    @property
    def valid(self) -> bool:
        return self.outcome is not PaperSimulationResultHistoryOutcome.INVALID_INPUT

    @property
    def stored(self) -> bool:
        return self.outcome is PaperSimulationResultHistoryOutcome.STORED

    @property
    def duplicate(self) -> bool:
        return self.outcome is PaperSimulationResultHistoryOutcome.DUPLICATE

    @property
    def history(self) -> tuple[PaperSimulationResult, ...]:
        return self.results


PaperSimulationResultHistoryStatus = PaperSimulationResultHistoryOutcome


class PaperSimulationResultHistory:
    """Deterministic, local history keyed by T06 result digest."""

    def __init__(
        self,
        results: tuple[PaperSimulationResult, ...]
        | list[PaperSimulationResult]
        | None = None,
    ) -> None:
        self._results_by_digest: dict[str, PaperSimulationResult] = {}
        if results is not None:
            if not isinstance(results, (tuple, list)):
                raise ValueError("results must be a tuple or list")
            for result in results:
                insertion = self.append(result)
                if not insertion.valid:
                    reason = ", ".join(insertion.reason_codes) or "INVALID_RESULT"
                    raise ValueError(
                        "cannot create paper simulation result history: "
                        f"{insertion.outcome.value} ({reason})"
                    )

    @classmethod
    def from_results(
        cls,
        results: tuple[PaperSimulationResult, ...]
        | list[PaperSimulationResult],
    ) -> "PaperSimulationResultHistory":
        return cls(results)

    def append(
        self,
        result: PaperSimulationResult | object,
    ) -> PaperSimulationResultHistoryResult:
        """Store one valid T06 result without mutating the supplied object."""

        try:
            current = self._ordered_results()
        except (AttributeError, TypeError, ValueError):
            return self._invalid_result(("INVALID_STORED_HISTORY",))
        if not isinstance(result, PaperSimulationResult):
            return self._result(
                outcome=PaperSimulationResultHistoryOutcome.INVALID_INPUT,
                result=None,
                results=current,
                reason_codes=("INVALID_RESULT",),
            )
        try:
            _validate_result(result)
            digest = result.digest
        except (AttributeError, TypeError, ValueError):
            return self._result(
                outcome=PaperSimulationResultHistoryOutcome.INVALID_INPUT,
                result=None,
                results=current,
                reason_codes=("INVALID_RESULT",),
            )
        existing = self._results_by_digest.get(digest)
        if existing is not None:
            return self._result(
                outcome=PaperSimulationResultHistoryOutcome.DUPLICATE,
                result=existing,
                results=current,
                reason_codes=("RESULT_ALREADY_STORED",),
            )
        self._results_by_digest[digest] = result
        return self._result(
            outcome=PaperSimulationResultHistoryOutcome.STORED,
            result=result,
            results=self._ordered_results(),
            reason_codes=(),
        )

    add = append
    record = append
    store = append

    def retrieve(self) -> tuple[PaperSimulationResult, ...]:
        return self._ordered_results()

    def get_history(self) -> tuple[PaperSimulationResult, ...]:
        return self.retrieve()

    def snapshot(self) -> tuple[PaperSimulationResult, ...]:
        return self.retrieve()

    @property
    def results(self) -> tuple[PaperSimulationResult, ...]:
        return self.retrieve()

    @property
    def history(self) -> tuple[PaperSimulationResult, ...]:
        return self.retrieve()

    @property
    def result_count(self) -> int:
        return len(self._results_by_digest)

    @property
    def snapshot_count(self) -> int:
        return self.result_count

    @property
    def representation_digest(self) -> str:
        return self._history_digest(self._ordered_results())

    @property
    def digest(self) -> str:
        return self.representation_digest

    @property
    def history_digest(self) -> str:
        return self.representation_digest

    def _ordered_results(self) -> tuple[PaperSimulationResult, ...]:
        for stored_digest, result in self._results_by_digest.items():
            _validate_result(result)
            if stored_digest != result.digest:
                raise ValueError("stored result digest no longer matches")
        return tuple(
            sorted(
                self._results_by_digest.values(),
                key=lambda value: _canonical_json(value.canonical_dict()),
            )
        )

    def _invalid_result(
        self,
        reason_codes: tuple[str, ...],
    ) -> PaperSimulationResultHistoryResult:
        return PaperSimulationResultHistoryResult(
            outcome=PaperSimulationResultHistoryOutcome.INVALID_INPUT,
            accepted=False,
            result=None,
            results=(),
            reason_codes=reason_codes,
            history_digest="invalid",
        )

    def _result(
        self,
        *,
        outcome: PaperSimulationResultHistoryOutcome,
        result: PaperSimulationResult | None,
        results: tuple[PaperSimulationResult, ...],
        reason_codes: tuple[str, ...],
    ) -> PaperSimulationResultHistoryResult:
        return PaperSimulationResultHistoryResult(
            outcome=outcome,
            accepted=outcome is PaperSimulationResultHistoryOutcome.STORED,
            result=result,
            results=results,
            reason_codes=reason_codes,
            history_digest=self._history_digest(results),
        )

    @staticmethod
    def _history_digest(results: tuple[PaperSimulationResult, ...]) -> str:
        return _digest(
            {
                "contract_version": P07_T07_CONTRACT_VERSION,
                "results": tuple(result.canonical_dict() for result in results),
            }
        )


def _validate_result(result: PaperSimulationResult) -> None:
    if result.contract_version != P07_T06_CONTRACT_VERSION:
        raise ValueError("unsupported P07-T06 contract version")
    values = result.canonical_dict()
    expected = PaperSimulationResult(
        input_digest=values["input_digest"],
        fill_digest=values["fill_digest"],
        transition_digest=values["transition_digest"],
        ledger_digest=values["ledger_digest"],
        reconciliation_digest=values["reconciliation_digest"],
        status=values["status"],
        filled_quantity=values["filled_quantity"],
        unfilled_quantity=values["unfilled_quantity"],
        position_state_digest=values["position_state_digest"],
        reconciliation_status=values["reconciliation_status"],
    )
    if expected != result or expected.digest != result.digest:
        raise ValueError("paper simulation result is not canonical")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


PaperSimulationHistory = PaperSimulationResultHistory
PaperResultHistory = PaperSimulationResultHistory
PaperSimulationResultHistoryResultAlias = PaperSimulationResultHistoryResult


__all__ = [
    "P07_T07_CONTRACT_VERSION",
    "PaperResultHistory",
    "PaperSimulationHistory",
    "PaperSimulationResultHistory",
    "PaperSimulationResultHistoryOutcome",
    "PaperSimulationResultHistoryResult",
    "PaperSimulationResultHistoryResultAlias",
    "PaperSimulationResultHistoryStatus",
]