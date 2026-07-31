"""BP-01 Candidate Review and Representation Decision integration tests."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_header


def _import_payload(tenant_id: str, candidate_id: str | None = None):
    return {
        "tenant_id": tenant_id,
        "matter_candidate_id": candidate_id or str(uuid.uuid4()),
        "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [str(uuid.uuid4())],
        "consent_record_ids": [str(uuid.uuid4())],
        "communication_ids": [str(uuid.uuid4())],
        "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service",
        "submitted_at": "2026-07-29T00:00:00Z",
    }


@pytest.mark.asyncio
async def test_candidate_import_happy_path(client):
    tenant_id = str(uuid.uuid4())
    payload = _import_payload(tenant_id)
    response = await client.post(
        "/api/v1/retainer/candidates/import",
        json=payload,
        headers=auth_header(firm_id=tenant_id),
    )
    assert response.status_code == 202
    data = response.json()
    assert "workflow_id" in data
    assert data["state"] == "NOT_STARTED"


@pytest.mark.asyncio
async def test_candidate_import_idempotent(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    payload = _import_payload(tenant_id, candidate_id)
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
    headers = auth_header(firm_id=tenant_id)

    r1 = await client.post(
        "/api/v1/retainer/candidates/import",
        json={**_import_payload(tenant_id, candidate_id), "candidate_version": 3},
        headers=headers,
    )
    assert r1.status_code == 202

    r2 = await client.post(
        "/api/v1/retainer/candidates/import",
        json={**_import_payload(tenant_id, candidate_id), "candidate_version": 1},
        headers=headers,
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_candidates(client):
    tenant_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id)
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id),
        headers=headers,
    )
    resp = await client.get("/api/v1/retainer/candidates", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["candidates"]) >= 1


@pytest.mark.asyncio
async def test_get_candidate_detail(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id)
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    resp = await client.get(
        f"/api/v1/retainer/candidates/{candidate_id}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "NOT_STARTED"


@pytest.mark.asyncio
async def test_start_review(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="staff")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/start-review",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["review_state"] == "IN_REVIEW"


@pytest.mark.asyncio
async def test_assign_attorney(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    attorney_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="staff")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/start-review",
        headers=headers,
    )
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/assign-attorney",
        json={"attorney_actor_id": attorney_id},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["responsible_attorney_actor_id"] == attorney_id


@pytest.mark.asyncio
async def test_request_information(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="staff")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/request-information",
        json={"reason": "Missing medical records", "fields_required": ["incident_date"]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "OPEN"


@pytest.mark.asyncio
async def test_approve_representation(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {"practice_area": "personal_injury"},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["outcome"] == "APPROVED"


@pytest.mark.asyncio
async def test_decline_representation(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/decline",
        json={
            "outcome": "DECLINED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["outcome"] == "DECLINED"


@pytest.mark.asyncio
async def test_staff_cannot_approve(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    staff_headers = auth_header(firm_id=tenant_id, role="staff")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=staff_headers,
    )
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=staff_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated(client):
    candidate_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 401

    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/decline",
        json={
            "outcome": "DECLINED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_nonexistent_candidate(client):
    headers = auth_header(role="attorney")
    resp = await client.post(
        f"/api/v1/retainer/candidates/{uuid.uuid4()}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cross_tenant_isolation(client):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers_a = auth_header(firm_id=tenant_a)
    headers_b = auth_header(firm_id=tenant_b)

    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_a, candidate_id),
        headers=headers_a,
    )
    resp = await client.get(
        f"/api/v1/retainer/candidates/{candidate_id}", headers=headers_b
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_audit_trail(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")

    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/retainer/candidates/{candidate_id}/audit", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["audit_entries"]) >= 1


@pytest.mark.asyncio
async def test_approve_then_workflow_state_is_attorney_approval_recorded(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")

    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {"practice_area": "personal_injury"},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    resp = await client.get(
        f"/api/v1/retainer/candidates/{candidate_id}", headers=headers
    )
    assert resp.json()["state"] == "ATTORNEY_APPROVAL_RECORDED"


@pytest.mark.asyncio
async def test_decline_preserves_candidate_visibility(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")

    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/decline",
        json={
            "outcome": "DECLINED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    resp = await client.get(
        f"/api/v1/retainer/candidates/{candidate_id}", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "DECLINED_OR_EXPIRED"


@pytest.mark.asyncio
async def test_review_queue(client):
    tenant_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id)

    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id),
        headers=headers,
    )
    resp = await client.get("/api/v1/retainer/review-queue", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["workflows"]) >= 1


@pytest.mark.asyncio
async def test_get_workflow_detail(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id)
    import_resp = await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    wf_id = import_resp.json()["workflow_id"]
    resp = await client.get(f"/api/v1/retainer/workflows/{wf_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["state"] == "NOT_STARTED"


@pytest.mark.asyncio
async def test_get_workflow_timeline(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id)
    import_resp = await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    wf_id = import_resp.json()["workflow_id"]
    resp = await client.get(
        f"/api/v1/retainer/workflows/{wf_id}/timeline", headers=headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["events"]) >= 1


@pytest.mark.asyncio
async def test_defer_representation(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/defer",
        json={
            "outcome": "DEFERRED",
            "scope_json": {"practice_area": "personal_injury"},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["outcome"] == "DEFERRED"


@pytest.mark.asyncio
async def test_staff_cannot_defer(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    staff_headers = auth_header(firm_id=tenant_id, role="staff")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=staff_headers,
    )
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/defer",
        json={
            "outcome": "DEFERRED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=staff_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ai_system_cannot_approve(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    system_headers = auth_header(firm_id=tenant_id, role="system")
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=system_headers,
    )
    assert resp.status_code == 403

    ai_headers = auth_header(firm_id=tenant_id, role="ai_agent")
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=ai_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_approve_then_second_approve_rejected(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    r1 = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert r1.status_code == 201

    r2 = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_decline_then_approve_rejected(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    r1 = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/decline",
        json={
            "outcome": "DECLINED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert r1.status_code == 201

    r2 = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_approve_then_defer_rejected(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/defer",
        json={
            "outcome": "DEFERRED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_defer_then_approve_succeeds(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    r1 = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/defer",
        json={
            "outcome": "DEFERRED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert r1.status_code == 201

    r2 = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_import_higher_version_allows_re_review(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json={**_import_payload(tenant_id, candidate_id), "candidate_version": 1},
        headers=headers,
    )
    await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )
    r2 = await client.post(
        "/api/v1/retainer/candidates/import",
        json={**_import_payload(tenant_id, candidate_id), "candidate_version": 2},
        headers=headers,
    )
    assert r2.status_code == 202
    assert r2.json()["candidate_version"] == 2

    resp = await client.get(
        f"/api/v1/retainer/candidates/{candidate_id}", headers=headers
    )
    assert resp.json()["state"] == "NOT_STARTED"


@pytest.mark.asyncio
async def test_golden_fixture_schema_integrity(client):
    from sqlalchemy import text

    from app.core.database import engine

    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        )
        tables = [row[0] for row in result.fetchall()]
        required = [
            "retainer_workflows",
            "representation_decisions",
            "candidate_reviews",
            "review_work_items",
            "missing_information_requests",
            "authority_evaluations",
            "configuration_resolution_snapshots",
            "retainer_audit_events",
            "retainer_inbox_events",
            "retainer_outbox_events",
            "retainer_idempotency_keys",
            "retainer_projection_checkpoints",
        ]
        missing = [t for t in required if t not in tables]
        if missing:
            available = sorted(tables)
            missing_str = ", ".join(missing)
            raise AssertionError(
                f"Missing tables: {missing_str}. Available: {', '.join(available)}"
            )
        for table in required:
            assert table in tables, f"Missing table: {table}"


@pytest.mark.asyncio
async def test_golden_fixture_audit_data(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")

    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/start-review",
        headers=headers,
    )
    await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={
            "outcome": "APPROVED",
            "scope_json": {"practice_area": "pi"},
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/retainer/candidates/{candidate_id}/audit", headers=headers
    )
    assert resp.status_code == 200
    entries = resp.json()["audit_entries"]
    assert len(entries) >= 1
    actions = [e["action"] for e in entries]
    assert "approve_representation" in actions
