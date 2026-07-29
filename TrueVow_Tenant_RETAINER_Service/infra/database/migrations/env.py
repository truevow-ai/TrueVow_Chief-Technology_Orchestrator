"""Alembic migration environment (async).

Resolves the database URL from RETAINER_DATABASE_URL / DATABASE_URL and
runs migrations against Supabase Postgres. Not exercised by the test suite
(tests build schema from SQLAlchemy metadata on SQLite).

Uses retainer.alembic_version as the version table to avoid conflicts with
other services sharing the same database instance.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

from app.models import Base

load_dotenv(".env.local", override=True)

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _db_url() -> str:
    url = os.getenv("RETAINER_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Set RETAINER_DATABASE_URL or DATABASE_URL to run migrations.")
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _configure_context(connection=None):
    kwargs = {
        "target_metadata": target_metadata,
        "version_table": "alembic_version",
        "version_table_schema": "retainer",
    }
    if connection is not None:
        kwargs["connection"] = connection
    else:
        kwargs.update(
            url=_db_url(),
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
    context.configure(**kwargs)


def run_migrations_offline() -> None:
    _configure_context()
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    _configure_context(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(
        _db_url(), pool_pre_ping=True, connect_args={"statement_cache_size": 0}
    )
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
