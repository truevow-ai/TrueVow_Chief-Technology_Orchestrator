import asyncio
import os
import re

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv(".env.local", override=True)


async def main():
    url = os.getenv("RETAINER_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        print("No database URL found")
        return
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(url, pool_pre_ping=True, connect_args={"statement_cache_size": 0})
    async with engine.connect() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS retainer"))
        await conn.commit()
        print("Schema 'retainer' created")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
