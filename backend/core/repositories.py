"""Repository boundaries for infrastructure and append-only paper records."""

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.models import (
    PaperLifecycleArtifact,
    PaperLifecycleRun,
    SystemMetadata,
)


class SystemMetadataRepository:
    """Access system metadata without exposing sessions to business callers."""

    async def get(self, session: AsyncSession, key: str) -> SystemMetadata | None:
        result = await session.execute(select(SystemMetadata).where(SystemMetadata.key == key))
        return result.scalar_one_or_none()

    async def set(self, session: AsyncSession, key: str, value: str) -> SystemMetadata:
        record = await self.get(session, key)
        if record is None:
            record = SystemMetadata(key=key, value=value)
            session.add(record)
        else:
            record.value = value
        return record


class PaperLifecycleRepository:
    """Store and read immutable lifecycle bundles through a supplied session."""

    async def get_run(
        self,
        session: AsyncSession,
        lifecycle_result_digest: str,
    ) -> PaperLifecycleRun | None:
        result = await session.execute(
            select(PaperLifecycleRun).where(
                PaperLifecycleRun.lifecycle_result_digest
                == lifecycle_result_digest
            )
        )
        return result.scalar_one_or_none()

    async def get_artifacts(
        self,
        session: AsyncSession,
        run_id: int,
    ) -> tuple[PaperLifecycleArtifact, ...]:
        result = await session.execute(
            select(PaperLifecycleArtifact)
            .where(PaperLifecycleArtifact.run_id == run_id)
            .order_by(PaperLifecycleArtifact.ordinal)
        )
        return tuple(result.scalars())

    async def insert_bundle(
        self,
        session: AsyncSession,
        *,
        run_values: Mapping[str, Any],
        artifact_values: Sequence[Mapping[str, Any]],
    ) -> PaperLifecycleRun:
        run = PaperLifecycleRun(**dict(run_values))
        session.add(run)
        await session.flush()
        session.add_all(
            PaperLifecycleArtifact(run_id=run.id, **dict(values))
            for values in artifact_values
        )
        await session.flush()
        return run
