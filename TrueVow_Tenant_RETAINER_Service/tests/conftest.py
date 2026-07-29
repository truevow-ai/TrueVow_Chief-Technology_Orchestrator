"""Test configuration.

Runs the suite against in-memory SQLite (the platform's conftest pattern).
Environment is set BEFORE importing the app so settings pick it up.
"""

from __future__ import annotations

import os
import uuid

os.environ["ENVIRONMENT"] = "development"
os.environ["AUTH_MODE"] = "local"
os.environ["LOCAL_JWT_SECRET"] = "test-secret-at-least-32-bytes-long-000"
os.environ["RETAINER_DATABASE_URL"] = ""
os.environ.pop("DATABASE_URL", None)

import jwt
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import engine
from app.main import app
from app.models import Base


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


def make_token(
    firm_id: str | None = None, user_id: str | None = None, role: str = "attorney"
) -> str:
    payload = {
        "sub": user_id or str(uuid.uuid4()),
        "firm_id": firm_id or str(uuid.uuid4()),
        "role": role,
        "mfa": True,
    }
    return jwt.encode(payload, settings.local_jwt_secret, algorithm="HS256")


def auth_header(
    firm_id: str | None = None, user_id: str | None = None, role: str = "attorney"
) -> dict:
    return {"Authorization": f"Bearer {make_token(firm_id=firm_id, user_id=user_id, role=role)}"}
