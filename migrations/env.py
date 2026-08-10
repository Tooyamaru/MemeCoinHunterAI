"""Alembic environment using the application metadata and DATABASE_URL."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from backend.core.config import get_settings
from backend.core.database import async_database_url
from backend.core.models import Base

config = context.config
if config.config_file_name is not None and config.get_section("loggers"):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating an engine."""

    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is required to run migrations")
    context.configure(
        url=async_database_url(database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is required to run migrations")
    connectable = async_engine_from_config(
        {"sqlalchemy.url": async_database_url(database_url)},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
