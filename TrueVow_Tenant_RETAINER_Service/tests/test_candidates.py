"""Candidate and representation decision integration tests."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_candidate_import_happy_path(client):
    payload = {
        "tenant_id": str(uuid.uuid4()),
        "matter_candidate_id": str(uuid.uuid4()),
        "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [str(uuid.uuid4())],
        "consent_record_ids": [str(uuid.uuid4())],
        "communication_ids": [str(uuid.uuid4())],
        "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service",
        "submitted_at": "2026-07-29T00:00:00Z",
    }
    response = await client.post(
        "/api/v1/retainer/candidates/import",
        json=payload,
        headers=auth_header(firm_id=payload["tenant_id"]),
    )
    assert response.status_code == 202
    data = response.json()
    assert "workflow_id" in data
    assert data["state"] == "NOT_STARTED"


@pytest.mark.asyncio
async def test_candidate_import_idempotent(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    payload = {
        "tenant_id": tenant_id,
        "matter_candidate_id": candidate_id,
        "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [],
        "consent_record_ids": [],
        "communication_ids": [],
        "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service",
        "submitted_at": "2026-07-29T00:00:00Z",
    }
    headers = auth_header(firm_id=tenant_id)

    r1 = await client.post(
        "/api/v1/retainer/candidates/import", json=payload, headers=headers
    )
    assert r1.status_code == 202
    wf_id_1 = r1.json()["workflow_id"]

    r2 = await client.post(
        "/api/v1/retainer/candidates/import", json=payload, headers=headers
    )
    assert r2.status_code == 202
    assert r2.json()["workflow_id"] == wf_id_1


@pytest.mark.asyncio
async def test_candidate_import_version_conflict(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    base_payload = {
        "tenant_id": tenant_id,
        "matter_candidate_id": candidate_id,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [],
        "consent_record_ids": [],
        "communication_ids": [],
        "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service",
        "submitted_at": "2026-07-29T00:00:00Z",
    }
    headers = auth_header(firm_id=tenant_id)

    r1 = await client.post(
        "/api/v1/retainer/candidates/import",
        json={**base_payload, "candidate_version": 3},
        headers=headers,
    )
    assert r1.status_code == 202

    r2 = await client.post(
        "/api/v1/retainer/candidates/import",
        json={**base_payload, "candidate_version": 1},
        headers=headers,
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_representation_approve_happy_path(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    import_payload = {
        "tenant_id": tenant_id,
        "matter_candidate_id": candidate_id,
        "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [],
        "consent_record_ids": [],
        "communication_ids": [],
        "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service",
        "submitted_at": "2026-07-29T00:00:00Z",
    }
    headers = auth_header(firm_id=tenant_id)

    import_resp = await client.post(
        "/api/v1/retainer/candidates/import", json=import_payload, headers=headers
    )
    assert import_resp.status_code == 202

    decision_payload = {
        "outcome": "APPROVED",
        "scope_json": {"practice_area": "personal_injury"},
        "authority_record_id": str(uuid.uuid4()),
    }
    dec_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/decisions",
        json=decision_payload,
        headers=headers,
    )
    assert dec_resp.status_code == 201
    data = dec_resp.json()
    assert data["outcome"] == "APPROVED"


@pytest.mark.asyncio
async def test_representation_decline(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    import_payload = {
        "tenant_id": tenant_id,
        "matter_candidate_id": candidate_id,
        "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [],
        "consent_record_ids": [],
        "communication_ids": [],
        "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service",
        "submitted_at": "2026-07-29T00:00:00Z",
    }
    headers = auth_header(firm_id=tenant_id)
    await client.post(
        "/api/v1/retainer/candidates/import", json=import_payload, headers=headers
    )
    dec_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/decisions",
        json={
            "outcome": "DECLINED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert dec_resp.status_code == 201
    assert dec_resp.json()["outcome"] == "DECLINED"


@pytest.mark.asyncio
async def test_representation_unauthenticated(client):
    resp = await client.post(
        f"/api/v1/retainer/candidates/{uuid.uuid4()}/decisions",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_representation_nonexistent_candidate(client):
    headers = auth_header()
    resp = await client.post(
        f"/api/v1/retainer/candidates/{uuid.uuid4()}/decisions",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_review_queue_returns_workflows(client):
    tenant_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id)

    base = {
        "tenant_id": tenant_id,
        "matter_candidate_id": str(uuid.uuid4()),
        "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [],
        "consent_record_ids": [],
        "communication_ids": [],
        "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service",
        "submitted_at": "2026-07-29T00:00:00Z",
    }
    await client.post(
        "/api/v1/retainer/candidates/import", json=base, headers=headers
    )

    resp = await client.get("/api/v1/retainer/review-queue", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["workflows"]) >= 1


@pytest.mark.asyncio
async def test_get_workflow_detail(client):
    tenant_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id)
    candidate_id = str(uuid.uuid4())

    import_payload = {
        "tenant_id": tenant_id,
        "matter_candidate_id": candidate_id,
        "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [],
        "consent_record_ids": [],
        "communication_ids": [],
        "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service",
        "submitted_at": "2026-07-29T00:00:00Z",
    }
    import_resp = await client.post(
        "/api/v1/retainer/candidates/import", json=import_payload, headers=headers
    )
    wf_id = import_resp.json()["workflow_id"]

    resp = await client.get(f"/api/v1/retainer/workflows/{wf_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "NOT_STARTED"


@pytest.mark.asyncio
async def test_get_workflow_timeline(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id)

    import_payload = {
        "tenant_id": tenant_id,
        "matter_candidate_id": candidate_id,
        "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [],
        "consent_record_ids": [],
        "communication_ids": [],
        "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service",
        "submitted_at": "2026-07-29T00:00:00Z",
    }
    import_resp = await client.post(
        "/api/v1/retainer/candidates/import", json=import_payload, headers=headers
    )
    wf_id = import_resp.json()["workflow_id"]

    resp = await client.get(
        f"/api/v1/retainer/workflows/{wf_id}/timeline", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) >= 1
