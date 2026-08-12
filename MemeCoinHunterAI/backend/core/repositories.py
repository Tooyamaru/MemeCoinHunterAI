"""Repository boundary for infrastructure metadata."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.models import SystemMetadata


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
