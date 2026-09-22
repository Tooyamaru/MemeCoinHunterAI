"""Bounded read-only catalog of persisted paper lifecycle identities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from backend.application.paper_lifecycle_persistence import (
    validate_lifecycle_result_digest,
)
from backend.core.database import DatabaseRuntime, DatabaseState
from backend.core.repositories import PaperLifecycleRepository


P01_RTI_07_CONTRACT_VERSION = "p01-rti-07-v1"
P01_RTI_07_DEFAULT_LIMIT = 50
P01_RTI_07_MAX_LIMIT = 100


class PaperLifecycleDigestCatalogOutcome(StrEnum):
    PAGE = "PAGE"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"


@dataclass(frozen=True)
class PaperLifecycleDigestCatalogResult:
    outcome: PaperLifecycleDigestCatalogOutcome | str
    reason_codes: tuple[str, ...]
    limit: int
    after_digest: str | None
    lifecycle_result_digests: tuple[str, ...] = ()
    next_after_digest: str | None = None
    contract_version: str = P01_RTI_07_CONTRACT_VERSION
    result_digest: str | None = None

    def __post_init__(self) -> None:
        try:
            outcome = PaperLifecycleDigestCatalogOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ValueError("unsupported digest catalog outcome") from error
        object.__setattr__(self, "outcome", outcome)
        _validate_limit(self.limit)
        if self.contract_version != P01_RTI_07_CONTRACT_VERSION:
            raise ValueError("unsupported digest catalog contract_version")
        if self.after_digest is not None:
            validate_lifecycle_result_digest(self.after_digest)
        reasons = _reason_codes(self.reason_codes)
        object.__setattr__(self, "reason_codes", reasons)
        digests = tuple(self.lifecycle_result_digests)
        object.__setattr__(self, "lifecycle_result_digests", digests)
        for digest in digests:
            validate_lifecycle_result_digest(digest)
        if digests != tuple(sorted(digests)) or len(set(digests)) != len(digests):
            raise ValueError("lifecycle_result_digests must be unique and ordered")
        if len(digests) > self.limit:
            raise ValueError("digest catalog page exceeds limit")
        if self.after_digest is not None and any(
            digest <= self.after_digest for digest in digests
        ):
            raise ValueError("digest catalog page is not after cursor")
        if self.next_after_digest is not None:
            validate_lifecycle_result_digest(self.next_after_digest)
            if not digests or self.next_after_digest != digests[-1]:
                raise ValueError("next_after_digest must equal the final page digest")
        if outcome is PaperLifecycleDigestCatalogOutcome.PAGE:
            if reasons:
                raise ValueError("PAGE cannot contain reason codes")
        elif digests or self.next_after_digest is not None or not reasons:
            raise ValueError("STORAGE_UNAVAILABLE cannot expose catalog entries")
        expected = _digest(self._without_digest())
        if self.result_digest is not None and self.result_digest != expected:
            raise ValueError("result_digest does not match digest catalog result")
        object.__setattr__(self, "result_digest", expected)

    def _without_digest(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "outcome": self.outcome.value,
            "reason_codes": self.reason_codes,
            "limit": self.limit,
            "after_digest": self.after_digest,
            "lifecycle_result_digests": self.lifecycle_result_digests,
            "next_after_digest": self.next_after_digest,
        }

    @property
    def digest(self) -> str:
        return self.result_digest  # type: ignore[return-value]


class PaperLifecycleDigestCatalogService:
    """Read one deterministic page of canonical persisted lifecycle identities."""

    def __init__(
        self,
        database: DatabaseRuntime,
        repository: PaperLifecycleRepository | None = None,
    ) -> None:
        if not isinstance(database, DatabaseRuntime):
            raise ValueError("database must be a DatabaseRuntime")
        self.database = database
        self.repository = repository or PaperLifecycleRepository()

    async def query(
        self,
        *,
        limit: int = P01_RTI_07_DEFAULT_LIMIT,
        after_digest: str | None = None,
    ) -> PaperLifecycleDigestCatalogResult:
        normalized_limit = _validate_limit(limit)
        normalized_after = (
            validate_lifecycle_result_digest(after_digest)
            if after_digest is not None
            else None
        )
        if not self._available:
            return _result(
                PaperLifecycleDigestCatalogOutcome.STORAGE_UNAVAILABLE,
                ("DATABASE_UNAVAILABLE",),
                limit=normalized_limit,
                after_digest=normalized_after,
            )
        try:
            async with self.database.session_scope() as session:
                candidates = await self.repository.list_run_digests(
                    session,
                    limit=normalized_limit + 1,
                    after_digest=normalized_after,
                )
        except (SQLAlchemyError, OSError, RuntimeError):
            return _result(
                PaperLifecycleDigestCatalogOutcome.STORAGE_UNAVAILABLE,
                ("DATABASE_READ_FAILED",),
                limit=normalized_limit,
                after_digest=normalized_after,
            )
        try:
            page = tuple(candidates[:normalized_limit])
            continuation = page[-1] if len(candidates) > normalized_limit else None
            return _result(
                PaperLifecycleDigestCatalogOutcome.PAGE,
                (),
                limit=normalized_limit,
                after_digest=normalized_after,
                digests=page,
                next_after_digest=continuation,
            )
        except (TypeError, ValueError):
            return _result(
                PaperLifecycleDigestCatalogOutcome.STORAGE_UNAVAILABLE,
                ("DATABASE_READ_FAILED",),
                limit=normalized_limit,
                after_digest=normalized_after,
            )

    @property
    def _available(self) -> bool:
        return (
            self.database.state is DatabaseState.CONNECTED
            and self.database.session_factory is not None
        )


def _validate_limit(value: Any) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or value > P01_RTI_07_MAX_LIMIT
    ):
        raise ValueError("limit must be an integer between 1 and 100")
    return value


def _reason_codes(value: Any) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValueError("reason_codes must be an immutable tuple")
    if any(
        not isinstance(item, str) or not item or item != item.strip()
        for item in value
    ):
        raise ValueError("reason_codes must contain canonical non-empty text")
    if len(set(value)) != len(value):
        raise ValueError("reason_codes must not contain duplicates")
    return value


def _result(
    outcome: PaperLifecycleDigestCatalogOutcome,
    reasons: tuple[str, ...],
    *,
    limit: int,
    after_digest: str | None,
    digests: tuple[str, ...] = (),
    next_after_digest: str | None = None,
) -> PaperLifecycleDigestCatalogResult:
    return PaperLifecycleDigestCatalogResult(
        outcome=outcome,
        reason_codes=reasons,
        limit=limit,
        after_digest=after_digest,
        lifecycle_result_digests=digests,
        next_after_digest=next_after_digest,
    )


def _digest(value: Any) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "P01_RTI_07_CONTRACT_VERSION",
    "P01_RTI_07_DEFAULT_LIMIT",
    "P01_RTI_07_MAX_LIMIT",
    "PaperLifecycleDigestCatalogOutcome",
    "PaperLifecycleDigestCatalogResult",
    "PaperLifecycleDigestCatalogService",
]
