"""Read-only application query for one persisted paper lifecycle result."""

from __future__ import annotations

from backend.application.paper_lifecycle_persistence import (
    ControlledPaperPersistenceService,
    PaperLifecycleReadResult,
)


class PaperLifecycleQueryService:
    """Delegate one canonical digest lookup to the P01-RTI-03 read owner."""

    def __init__(self, persistence: ControlledPaperPersistenceService) -> None:
        self.persistence = persistence

    async def query(
        self,
        lifecycle_result_digest: str,
    ) -> PaperLifecycleReadResult:
        return await self.persistence.read(lifecycle_result_digest)
