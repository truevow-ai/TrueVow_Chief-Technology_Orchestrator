import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv(".env.local", override=True)


async def main():
    url = os.getenv("RETAINER_DATABASE_URL")
    if not url:
        print("No DATABASE_URL set")
        return
    if "pooler.supabase" in url:
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(
        url, pool_pre_ping=True, connect_args={"statement_cache_size": 0}
    )
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT tablename FROM pg_catalog.pg_tables "
                "WHERE schemaname = 'retainer' ORDER BY tablename"
            )
        )
        rows = [r[0] for r in result]
        print(f"Tables in retainer schema: {len(rows)}")
        for name in rows:
            print(f"  {name}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
