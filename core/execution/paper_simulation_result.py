from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from typing import Any

from core.execution.paper_fill_outcome import PaperFillOutcome
from core.execution.paper_ledger import PaperLedgerEntry
from core.execution.paper_position_exposure_state import PaperStateTransitionResult
from core.execution.paper_reconciliation import PaperReconciliationResult
from core.execution.paper_simulation_input import PaperSimulationInput

P07_T06_CONTRACT_VERSION = "p07-t06-v1"
_DIGEST_LENGTH = 64


@dataclass(frozen=True)
class PaperSimulationResult:
    input_digest: str
    fill_digest: str
    transition_digest: str
    ledger_digest: str
    reconciliation_digest: str
    status: str
    filled_quantity: str
    unfilled_quantity: str
    position_state_digest: str
    reconciliation_status: str

    def __post_init__(self) -> None:
        for name in (
            "input_digest",
            "fill_digest",
            "transition_digest",
            "ledger_digest",
            "reconciliation_digest",
            "position_state_digest",
        ):
            _require_digest(getattr(self, name), name)
        for name in (
            "status",
            "filled_quantity",
            "unfilled_quantity",
            "reconciliation_status",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"{name} must be non-empty canonical text")

        allowed = {
            "FILLED",
            "PARTIAL",
            "FAILED",
            "REJECTED",
            "UNAVAILABLE",
            "INVALID",
        }
        if self.status not in allowed:
            raise ValueError("unsupported simulation status")

        if self.reconciliation_status not in {
            "RECONCILED",
            "DISAGREEMENT",
            "UNKNOWN",
        }:
            raise ValueError("unsupported reconciliation status")

    @classmethod
    def from_predecessors(
        cls,
        *,
        simulation_input: PaperSimulationInput,
        fill_outcome: PaperFillOutcome,
        transition: PaperStateTransitionResult,
        ledger_entries: tuple[PaperLedgerEntry, ...] | list[PaperLedgerEntry],
        reconciliation: PaperReconciliationResult,
    ) -> "PaperSimulationResult":
        """Materialize a result only after validating its owned predecessors."""

        ledger_values = tuple(ledger_entries)
        cls._validate_predecessors(
            simulation_input,
            fill_outcome,
            transition,
            ledger_values,
            reconciliation,
        )
        if len(ledger_values) != 1:
            raise ValueError("P07-T06 requires exactly one ledger entry")
        return cls(
            input_digest=simulation_input.digest,
            fill_digest=fill_outcome.outcome_digest,
            transition_digest=transition.transition_digest,
            ledger_digest=ledger_values[0].entry_digest,
            reconciliation_digest=reconciliation.result_digest,
            status=fill_outcome.status.value,
            filled_quantity=str(fill_outcome.filled_quantity),
            unfilled_quantity=str(fill_outcome.remaining_quantity),
            position_state_digest=(
                transition.next_state.digest
                if transition.next_state is not None
                else transition.prior_state.digest
            ),
            reconciliation_status=(
                "RECONCILED"
                if str(reconciliation.status) == "MATCH"
                else str(reconciliation.status)
            ),
        )

    @classmethod
    def validate_predecessors(
        cls,
        result: "PaperSimulationResult",
        *,
        simulation_input: PaperSimulationInput,
        fill_outcome: PaperFillOutcome,
        transition: PaperStateTransitionResult,
        ledger_entries: tuple[PaperLedgerEntry, ...] | list[PaperLedgerEntry],
        reconciliation: PaperReconciliationResult,
    ) -> None:
        """Revalidate owner contracts and every result-to-predecessor link."""

        ledger_values = tuple(ledger_entries)
        cls._validate_predecessors(
            simulation_input,
            fill_outcome,
            transition,
            ledger_values,
            reconciliation,
        )
        expected = cls.from_predecessors(
            simulation_input=simulation_input,
            fill_outcome=fill_outcome,
            transition=transition,
            ledger_entries=ledger_values,
            reconciliation=reconciliation,
        )
        if expected != result:
            raise ValueError("paper simulation result does not match predecessors")

    @staticmethod
    def _validate_predecessors(
        simulation_input: PaperSimulationInput,
        fill_outcome: PaperFillOutcome,
        transition: PaperStateTransitionResult,
        ledger_entries: tuple[PaperLedgerEntry, ...],
        reconciliation: PaperReconciliationResult,
    ) -> None:
        if not isinstance(simulation_input, PaperSimulationInput):
            raise ValueError("simulation_input must be a PaperSimulationInput")
        if not isinstance(fill_outcome, PaperFillOutcome):
            raise ValueError("fill_outcome must be a PaperFillOutcome")
        if not isinstance(transition, PaperStateTransitionResult):
            raise ValueError("transition must be a PaperStateTransitionResult")
        if not ledger_entries or not all(
            isinstance(entry, PaperLedgerEntry) for entry in ledger_entries
        ):
            raise ValueError("ledger_entries must contain PaperLedgerEntry values")
        if not isinstance(reconciliation, PaperReconciliationResult):
            raise ValueError(
                "reconciliation must be a PaperReconciliationResult"
            )

        for predecessor in (
            simulation_input,
            fill_outcome,
            transition,
            *ledger_entries,
            reconciliation,
        ):
            rebuilt = replace(predecessor)
            if rebuilt != predecessor:
                raise ValueError("predecessor is not canonical")

        if fill_outcome.p07_t01_input_digest != simulation_input.digest:
            raise ValueError("fill outcome does not match simulation input")
        if (
            transition.outcome_identity.get("outcome_digest")
            != fill_outcome.outcome_digest
        ):
            raise ValueError("transition does not match fill outcome")
        if len(ledger_entries) != 1:
            raise ValueError("P07-T06 requires exactly one ledger entry")
        ledger = ledger_entries[0]
        if (
            ledger.simulation_identity.get("p07_t01_input_digest")
            != simulation_input.digest
            or ledger.outcome_identity.get("outcome_digest")
            != fill_outcome.outcome_digest
            or ledger.transition_identity.get("transition_digest")
            != transition.transition_digest
        ):
            raise ValueError("ledger does not match P07 predecessors")
        if reconciliation.result_digest != reconciliation.digest:
            raise ValueError("reconciliation digest is not canonical")

    @property
    def contract_version(self) -> str:
        return P07_T06_CONTRACT_VERSION

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "input_digest": self.input_digest,
            "fill_digest": self.fill_digest,
            "transition_digest": self.transition_digest,
            "ledger_digest": self.ledger_digest,
            "reconciliation_digest": self.reconciliation_digest,
            "status": self.status,
            "filled_quantity": self.filled_quantity,
            "unfilled_quantity": self.unfilled_quantity,
            "position_state_digest": self.position_state_digest,
            "reconciliation_status": self.reconciliation_status,
        }

    @property
    def digest(self) -> str:
        payload = json.dumps(
            self.canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(payload).hexdigest()


def _require_digest(value: Any, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != _DIGEST_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
