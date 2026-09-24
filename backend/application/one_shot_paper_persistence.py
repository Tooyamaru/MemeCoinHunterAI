"""Explicit one-shot persistence of an existing OSC-01 lifecycle result."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import hashlib
import json
from typing import Any

from backend.application.one_shot_controlled_paper_caller import (
    OneShotPaperOutcome,
    P01Osc01Result,
)
from backend.application.paper_lifecycle_persistence import (
    ControlledPaperPersistenceService,
    PaperLifecyclePersistenceOutcome,
    PaperLifecyclePersistenceResult,
)
from backend.application.rti15_to_controlled_paper_lifecycle import (
    P01Rti16ControlledPaperLifecycleContinuationResult,
    Rti15ToControlledLifecycleOutcome,
)
from core.runtime.controlled_paper_lifecycle import ControlledPaperLifecycleResult


P01_OSP_01_CONTRACT_VERSION = "p01-osp-01-v1"


class OneShotPersistenceOutcome(StrEnum):
    UPSTREAM_NOT_PERSISTABLE = "UPSTREAM_NOT_PERSISTABLE"
    STORED = "STORED"
    ALREADY_STORED = "ALREADY_STORED"
    CONFLICT = "CONFLICT"
    INVALID_INPUT = "INVALID_INPUT"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"
    PERSISTENCE_UNAVAILABLE = "PERSISTENCE_UNAVAILABLE"


_OWNER_OUTCOMES = frozenset(PaperLifecyclePersistenceOutcome)
_UNAVAILABLE_REASONS = frozenset({"RTI_03_UNAVAILABLE", "RTI_03_INVALID_RESULT"})


def _canonical(value: Any, expected: type) -> bool:
    if type(value) is not expected:
        return False
    try:
        reconstructed = replace(value)
        return reconstructed == value and reconstructed.canonical_representation == value.canonical_representation
    except (AttributeError, TypeError, ValueError, KeyError, ArithmeticError):
        return False


def _validate_osc(value: P01Osc01Result) -> None:
    if not _canonical(value, P01Osc01Result):
        raise ValueError("invalid canonical OSC-01 result")
    if value.outcome is OneShotPaperOutcome.LIFECYCLE_RETURNED:
        rti16 = value.rti16_result
        if (not _canonical(rti16, P01Rti16ControlledPaperLifecycleContinuationResult)
            or rti16.outcome is not Rti15ToControlledLifecycleOutcome.LIFECYCLE_MATERIALIZED
            or not _canonical(rti16.lifecycle_result, ControlledPaperLifecycleResult)):
            raise ValueError("invalid canonical OSC-01 lifecycle")


def _valid_owner(value: Any, lifecycle_digest: str) -> bool:
    if type(value) is not PaperLifecyclePersistenceResult:
        return False
    try:
        reconstructed = replace(value)
        if reconstructed != value or reconstructed.digest != value.digest:
            return False
        if value.outcome is not PaperLifecyclePersistenceOutcome.INVALID_INPUT and value.lifecycle_result_digest is None:
            return False
        return value.lifecycle_result_digest in (None, lifecycle_digest) and (
            value.lifecycle_result_digest is not None or value.outcome is PaperLifecyclePersistenceOutcome.INVALID_INPUT
        )
    except (AttributeError, TypeError, ValueError, KeyError, ArithmeticError):
        return False


def _digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


@dataclass(frozen=True)
class P01Osp01Result:
    osc_result: P01Osc01Result
    outcome: OneShotPersistenceOutcome
    reason_codes: tuple[str, ...]
    persistence_result: PaperLifecyclePersistenceResult | None = None
    contract_version: str = P01_OSP_01_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        _validate_osc(self.osc_result)
        if self.contract_version != P01_OSP_01_CONTRACT_VERSION or type(self.outcome) is not OneShotPersistenceOutcome:
            raise ValueError("invalid OSP-01 contract")
        if type(self.reason_codes) is not tuple or any(type(code) is not str or not code for code in self.reason_codes):
            raise ValueError("invalid OSP-01 reasons")
        if self.outcome is OneShotPersistenceOutcome.UPSTREAM_NOT_PERSISTABLE:
            if (self.osc_result.outcome is OneShotPaperOutcome.LIFECYCLE_RETURNED
                or self.persistence_result is not None or self.reason_codes != self.osc_result.reason_codes):
                raise ValueError("invalid upstream persistence stop")
        elif self.outcome is OneShotPersistenceOutcome.PERSISTENCE_UNAVAILABLE:
            if (self.osc_result.outcome is not OneShotPaperOutcome.LIFECYCLE_RETURNED
                or self.persistence_result is not None or self.reason_codes not in tuple((code,) for code in _UNAVAILABLE_REASONS)):
                raise ValueError("invalid persistence unavailable result")
        else:
            lifecycle = self.osc_result.lifecycle_result
            if (self.osc_result.outcome is not OneShotPaperOutcome.LIFECYCLE_RETURNED
                or not _valid_owner(self.persistence_result, lifecycle.digest)
                or self.outcome.value not in _OWNER_OUTCOMES
                or self.outcome.value != self.persistence_result.outcome.value
                or self.reason_codes != self.persistence_result.reason_codes):
                raise ValueError("invalid persistence owner result")
        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("OSP-01 result digest mismatch")
        object.__setattr__(self, "result_digest", expected)

    @property
    def invocation_id(self) -> str:
        return self.osc_result.invocation_id

    def _without_digest(self) -> dict[str, Any]:
        rti16 = self.osc_result.rti16_result
        lifecycle = self.osc_result.lifecycle_result if self.osc_result.outcome is OneShotPaperOutcome.LIFECYCLE_RETURNED else None
        owner = self.persistence_result
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "invocation_id": self.invocation_id,
            "osc_contract_version": self.osc_result.contract_version,
            "osc_outcome": self.osc_result.outcome.value,
            "osc_result_digest": self.osc_result.digest,
            "rti16_contract_version": rti16.contract_version if rti16 else None,
            "rti16_outcome": rti16.outcome.value if rti16 else None,
            "rti16_result_digest": rti16.digest if rti16 else None,
            "rti02_contract_version": lifecycle.contract_version if lifecycle else None,
            "rti02_outcome": lifecycle.outcome.value if lifecycle else None,
            "rti02_lifecycle_digest": lifecycle.digest if lifecycle else None,
            "rti03_contract_version": owner.contract_version if owner else None,
            "rti03_outcome": owner.outcome.value if owner else None,
            "rti03_result_digest": owner.digest if owner else None,
        }

    @property
    def canonical_representation(self) -> dict[str, Any]:
        return {**self._without_digest(), "result_digest": self.result_digest}

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


class OneShotPaperPersistenceService:
    """Persist one already-returned lifecycle; never invoke OSC or lifecycle owners."""

    def __init__(self, persistence: ControlledPaperPersistenceService) -> None:
        if not isinstance(persistence, ControlledPaperPersistenceService):
            raise ValueError("invalid RTI-03 persistence owner")
        self.persistence = persistence

    async def persist(self, osc_result: P01Osc01Result) -> P01Osp01Result:
        _validate_osc(osc_result)
        if osc_result.outcome is not OneShotPaperOutcome.LIFECYCLE_RETURNED:
            return P01Osp01Result(osc_result, OneShotPersistenceOutcome.UPSTREAM_NOT_PERSISTABLE,
                                  osc_result.reason_codes)
        lifecycle = osc_result.rti16_result.lifecycle_result
        try:
            owner_result = await self.persistence.persist(lifecycle)
        except ValueError:
            raise ValueError("RTI-03 validation failed") from None
        except Exception:
            return P01Osp01Result(osc_result, OneShotPersistenceOutcome.PERSISTENCE_UNAVAILABLE,
                                  ("RTI_03_UNAVAILABLE",))
        if not _valid_owner(owner_result, lifecycle.digest):
            return P01Osp01Result(osc_result, OneShotPersistenceOutcome.PERSISTENCE_UNAVAILABLE,
                                  ("RTI_03_INVALID_RESULT",))
        return P01Osp01Result(osc_result, OneShotPersistenceOutcome(owner_result.outcome.value),
                              owner_result.reason_codes, persistence_result=owner_result)
