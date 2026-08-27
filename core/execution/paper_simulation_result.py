from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

P07_T06_CONTRACT_VERSION = "p07-t06-v1"


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
        for name, value in self.__dict__.items():
            if not isinstance(value, str) or not value.strip():
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
