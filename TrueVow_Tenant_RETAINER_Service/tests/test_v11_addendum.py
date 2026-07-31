"""v1.1 Capability Addendum — integration tests."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_header


async def _setup_candidate_imported(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")
    await client.post("/api/v1/retainer/candidates/import", json={
        "tenant_id": tenant_id, "matter_candidate_id": candidate_id, "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [str(uuid.uuid4())], "consent_record_ids": [str(uuid.uuid4())],
        "communication_ids": [str(uuid.uuid4())], "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service", "submitted_at": "2026-07-29T00:00:00Z",
    }, headers=headers)
    await client.post(f"/api/v1/retainer/candidates/{candidate_id}/start-review", headers=headers)
    info_resp = await client.post(f"/api/v1/retainer/candidates/{candidate_id}/request-information", json={
        "reason": "Missing documents", "fields_required": ["id_proof", "incident_report"]}, headers=headers)
    return tenant_id, candidate_id, info_resp.json()["request_id"], headers


@pytest.mark.asyncio
async def test_create_request_items(client):
    t, cid, rid, h = await _setup_candidate_imported(client)
    resp = await client.post(f"/api/v1/retainer/information-requests/{rid}/items", json={
        "items": [
            {"item_key": "id_proof", "description": "Government ID", "category": "IDENTITY", "required": True},
            {"item_key": "incident_report", "description": "Police report", "category": "INCIDENT", "required": False},
        ]}, headers=h)
    assert resp.status_code == 201
    assert len(resp.json()["item_ids"]) == 2


@pytest.mark.asyncio
async def test_submit_information(client):
    t, cid, rid, h = await _setup_candidate_imported(client)
    cr = await client.post(f"/api/v1/retainer/information-requests/{rid}/items", json={
        "items": [{"item_key": "id_proof", "description": "ID", "category": "IDENTITY"}]}, headers=h)
    item_id = cr.json()["item_ids"][0]
    resp = await client.post(f"/api/v1/retainer/information-request-items/{item_id}/submit", json={
        "content": "DL-123456", "content_type": "TEXT"}, headers=h)
    assert resp.status_code == 201
    assert resp.json()["status"] == "FULFILLED"


@pytest.mark.asyncio
async def test_verify_submission(client):
    t, cid, rid, h = await _setup_candidate_imported(client)
    cr = await client.post(f"/api/v1/retainer/information-requests/{rid}/items", json={
        "items": [{"item_key": "id_proof", "description": "ID", "category": "IDENTITY"}]}, headers=h)
    item_id = cr.json()["item_ids"][0]
    sr = await client.post(f"/api/v1/retainer/information-request-items/{item_id}/submit", json={
        "content": "DL-123456"}, headers=h)
    resp = await client.post(f"/api/v1/retainer/information-submissions/{sr.json()['submission_id']}/verify",
                             json={"status": "VERIFIED"}, headers=h)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_record_engagement_outcome(client):
    t, cid, rid, h = await _setup_candidate_imported(client)
    wf = (await client.get(f"/api/v1/retainer/candidates/{cid}", headers=h)).json()
    resp = await client.post(f"/api/v1/retainer/workflows/{wf['workflow_id']}/outcome", json={
        "outcome_class": "CLIENT_DECLINED", "friction_reason": "FEE_OR_COST_CONCERN",
        "evidence_classification": "CLIENT_STATED", "stated_by_actor_id": str(uuid.uuid4()),
    }, headers=h)
    assert resp.status_code == 201
    assert resp.json()["outcome_class"] == "CLIENT_DECLINED"


@pytest.mark.asyncio
async def test_build_client_experience_projection(client):
    t, cid, rid, h = await _setup_candidate_imported(client)
    wf = (await client.get(f"/api/v1/retainer/candidates/{cid}", headers=h)).json()
    resp = await client.post(f"/api/v1/retainer/workflows/{wf['workflow_id']}/client-experience", json={
        "recipient_party_role_id": str(uuid.uuid4())}, headers=h)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_pause_and_resume_work_item(client):
    t, cid, rid, h = await _setup_candidate_imported(client)
    from sqlalchemy import text

    from app.core.database import engine
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT id FROM review_work_items LIMIT 1"))
        item_id = str(r.scalar_one())
    pause = await client.post(f"/api/v1/retainer/work-items/{item_id}/pause", json={"reason": "On leave"}, headers=h)
    assert pause.status_code == 200
    resume = await client.post(f"/api/v1/retainer/work-items/{item_id}/resume", headers=h)
    assert resume.status_code == 200


@pytest.mark.asyncio
async def test_reassign_work_item(client):
    t, cid, rid, h = await _setup_candidate_imported(client)
    from sqlalchemy import text

    from app.core.database import engine
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT id FROM review_work_items LIMIT 1"))
        item_id = str(r.scalar_one())
    new_actor = str(uuid.uuid4())
    resp = await client.post(f"/api/v1/retainer/work-items/{item_id}/reassign", json={
        "new_actor_id": new_actor}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["assigned_to"] == new_actor
