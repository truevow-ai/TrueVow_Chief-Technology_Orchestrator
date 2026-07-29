"""Async database engine, session factory, and request-scoped session dependency.

Follows the platform pattern: RLS GUCs on Postgres, SQLite fallback for dev/test.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.auth.deps import AuthContext, get_current_context
from app.core.config import settings


def _create_engine(url: str, *, search_path: str = ""):
    if url.startswith("sqlite"):
        return create_async_engine(
            url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            future=True,
        )
    connect_args: dict = {}
    if "pooler.supabase.com" in url:
        connect_args["statement_cache_size"] = 0
    if search_path:
        connect_args["server_settings"] = {"search_path": search_path}
    return create_async_engine(url, pool_pre_ping=True, connect_args=connect_args, future=True)


engine = _create_engine(settings.effective_database_url, search_path="retainer")
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


async def get_db(
    ctx: AuthContext = Depends(get_current_context),  # noqa: B008
) -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        if is_postgres():
            await session.execute(
                text(f"SET LOCAL app.current_tenant_id = '{ctx.firm_id}'")
            )
            await session.execute(
                text(f"SET LOCAL app.current_user_id = '{ctx.user_id}'")
            )
            await session.execute(
                text(f"SET LOCAL app.current_user_role = '{ctx.role or ''}'")
            )
        yield session
