"""Process-local opaque registry for prepared OAF paper cases.

This registry preserves exact Python object identity across review requests. It is
bounded operational control state only: not persistence, replay archive, or a
cross-process idempotency mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import hashlib
import json
import secrets
from threading import RLock
from typing import Callable

from backend.application.oaf_prepare_case import OafPrepareCaseResult


P01_OAF_CASE_REGISTRY_VERSION = "p01-oaf-01-case-registry-v1"


class OperatorPaperCaseState(StrEnum):
    REVIEW_READY = "REVIEW_READY"
    PREPARATION_STOPPED = "PREPARATION_STOPPED"
    PREPARATION_UNAVAILABLE = "PREPARATION_UNAVAILABLE"


@dataclass(frozen=True)
class OperatorPaperCaseRecord:
    handle: str
    case_digest: str
    state: OperatorPaperCaseState
    prepared: OafPrepareCaseResult
    created_at: datetime
    expires_at: datetime
    contract_version: str = P01_OAF_CASE_REGISTRY_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != P01_OAF_CASE_REGISTRY_VERSION:
            raise ValueError("unsupported registry contract")
        if not isinstance(self.handle, str) or len(self.handle) < 24:
            raise ValueError("opaque handle is invalid")
        if not isinstance(self.case_digest, str) or len(self.case_digest) != 64:
            raise ValueError("case_digest must be SHA-256")
        if not isinstance(self.state, OperatorPaperCaseState):
            raise ValueError("invalid case state")
        if not isinstance(self.prepared, OafPrepareCaseResult):
            raise ValueError("prepared case result is required")
        for name in ("created_at", "expires_at"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")


class OperatorPaperCaseRegistry:
    """Finite in-memory identity-preserving prepared-case registry."""

    def __init__(
        self,
        *,
        capacity: int = 64,
        ttl: timedelta = timedelta(minutes=30),
        clock: Callable[[], datetime] | None = None,
        handle_factory: Callable[[], str] | None = None,
    ) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0 or capacity > 4096:
            raise ValueError("capacity must be between 1 and 4096")
        if not isinstance(ttl, timedelta) or ttl <= timedelta(0) or ttl > timedelta(days=1):
            raise ValueError("ttl must be positive and at most one day")
        self._capacity = capacity
        self._ttl = ttl
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._handle_factory = handle_factory or (lambda: secrets.token_urlsafe(32))
        self._records: dict[str, OperatorPaperCaseRecord] = {}
        self._lock = RLock()

    def put(self, prepared: OafPrepareCaseResult) -> OperatorPaperCaseRecord:
        if not isinstance(prepared, OafPrepareCaseResult):
            raise ValueError("prepared must be OafPrepareCaseResult")
        with self._lock:
            now = self._utc(self._clock())
            self._purge_expired(now)
            if len(self._records) >= self._capacity:
                raise RuntimeError("CASE_REGISTRY_CAPACITY_EXCEEDED")
            handle = self._new_handle()
            record = OperatorPaperCaseRecord(
                handle=handle,
                case_digest=_case_digest(prepared),
                state=_state_for(prepared),
                prepared=prepared,
                created_at=now,
                expires_at=now + self._ttl,
            )
            self._records[handle] = record
            return record

    def get(self, handle: str) -> OperatorPaperCaseRecord | None:
        if not isinstance(handle, str) or not handle:
            return None
        with self._lock:
            now = self._utc(self._clock())
            record = self._records.get(handle)
            if record is None:
                return None
            if record.expires_at <= now:
                del self._records[handle]
                return None
            return record

    def remove(self, handle: str) -> bool:
        if not isinstance(handle, str) or not handle:
            return False
        with self._lock:
            return self._records.pop(handle, None) is not None

    def size(self) -> int:
        with self._lock:
            self._purge_expired(self._utc(self._clock()))
            return len(self._records)

    def _new_handle(self) -> str:
        for _ in range(4):
            handle = self._handle_factory()
            if not isinstance(handle, str) or len(handle) < 24:
                raise ValueError("handle_factory returned invalid opaque handle")
            if handle not in self._records:
                return handle
        raise RuntimeError("CASE_HANDLE_COLLISION")

    def _purge_expired(self, now: datetime) -> None:
        expired = [key for key, value in self._records.items() if value.expires_at <= now]
        for key in expired:
            del self._records[key]

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("clock must return timezone-aware datetime")
        return value.astimezone(timezone.utc)


def _state_for(prepared: OafPrepareCaseResult) -> OperatorPaperCaseState:
    outcome = prepared.cip_result.outcome.value
    if outcome == "REQUEST_PREPARED":
        return OperatorPaperCaseState.REVIEW_READY
    if outcome in {"PREFIX_NOT_ELIGIBLE", "FACTS_NOT_MATERIALIZED"}:
        return OperatorPaperCaseState.PREPARATION_STOPPED
    return OperatorPaperCaseState.PREPARATION_UNAVAILABLE


def _case_digest(prepared: OafPrepareCaseResult) -> str:
    cip = prepared.cip_result
    pfx = prepared.pfx_result
    pfs = prepared.pfs_result
    material = {
        "registry_contract": P01_OAF_CASE_REGISTRY_VERSION,
        "prepare_contract": prepared.contract_version,
        "cip_contract": cip.contract_version,
        "cip_digest": cip.result_digest,
        "cip_outcome": cip.outcome.value,
        "osc_invocation_id": cip.request.invocation_id,
        "osc_input_digests": (
            dict(cip.osc02_request.input_digests) if cip.osc02_request is not None else None
        ),
        "rti11_digest": pfx.request.rti11_result.result_digest,
        "pfx_digest": pfx.result_digest,
        "pfs_digest": pfs.result_digest,
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


__all__ = [
    "OperatorPaperCaseRecord",
    "OperatorPaperCaseRegistry",
    "OperatorPaperCaseState",
    "P01_OAF_CASE_REGISTRY_VERSION",
]
