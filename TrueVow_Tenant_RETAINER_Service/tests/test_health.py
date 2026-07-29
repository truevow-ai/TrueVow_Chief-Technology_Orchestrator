"""Health endpoint tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "retainer"
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_v1_router_mounted(client):
    response = await client.get("/api/v1/retainer")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "retainer"
