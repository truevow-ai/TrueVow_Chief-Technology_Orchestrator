"""BP-03 Template Resolution and Package Generation integration tests."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_header


async def _setup_at_package_prep(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")

    await client.post(
        "/api/v1/retainer/candidates/import",
        json={
            "tenant_id": tenant_id,
            "matter_candidate_id": candidate_id,
            "candidate_version": 1,
            "prospective_client_party_role_ids": [str(uuid.uuid4())],
            "intake_session_ids": [str(uuid.uuid4())],
            "consent_record_ids": [str(uuid.uuid4())],
            "communication_ids": [str(uuid.uuid4())],
            "source_event_ids": [str(uuid.uuid4())],
            "submitted_by_actor_id": "intake-service",
            "submitted_at": "2026-07-29T00:00:00Z",
        },
        headers=headers,
    )
    await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={"outcome": "APPROVED", "scope_json": {}, "authority_record_id": str(uuid.uuid4())},
        headers=headers,
    )
    sr = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json={
            "parties": [
                {
                    "party_type": "PROSPECTIVE_CLIENT",
                    "canonical_ref": str(uuid.uuid4()),
                    "legal_name": "Acme Corp",
                    "aliases": ["ACME Corporation"],
                    "normalized_name": "acme corp",
                },
                {
                    "party_type": "ADVERSE_PARTY",
                    "canonical_ref": str(uuid.uuid4()),
                    "legal_name": "Acme Corp",
                    "normalized_name": "acme corp",
                },
            ],
            "candidate_version": 1,
        },
        headers=headers,
    )
    search_id = sr.json()["search_id"]
    detail = await client.get(f"/api/v1/retainer/conflicts/searches/{search_id}", headers=headers)
    for c in detail.json()["candidates"]:
        await client.post(
            f"/api/v1/retainer/conflict-candidates/{c['id']}/disposition",
            json={"disposition": "NO_CONFLICT"},
            headers=headers,
        )
    await client.post(
        f"/api/v1/retainer/conflicts/{search_id}/clear",
        json={"authority_record_id": str(uuid.uuid4())},
        headers=headers,
    )
    wf_resp = await client.get(f"/api/v1/retainer/candidates/{candidate_id}", headers=headers)
    return tenant_id, wf_resp.json()["workflow_id"], headers


@pytest.mark.asyncio
async def test_resolve_template_happy_path(client):
    tenant_id, wf_id, headers = await _setup_at_package_prep(client)
    resp = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/templates/resolve",
        json={
            "template_definition_id": str(uuid.uuid4()),
            "template_version": "1.0.0",
            "policy_version_id": str(uuid.uuid4()),
            "merge_fields": [
                {"field_name": "client_name", "field_value": "John Doe"},
                {"field_name": "practice_area", "field_value": "personal_injury"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["merge_fields"]) == 2
    assert data["template_hash"]


@pytest.mark.asyncio
async def test_resolve_template_requires_package_prep(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json={
            "tenant_id": tenant_id,
            "matter_candidate_id": candidate_id,
            "candidate_version": 1,
            "prospective_client_party_role_ids": [str(uuid.uuid4())],
            "intake_session_ids": [str(uuid.uuid4())],
            "consent_record_ids": [str(uuid.uuid4())],
            "communication_ids": [str(uuid.uuid4())],
            "source_event_ids": [str(uuid.uuid4())],
            "submitted_by_actor_id": "intake-service",
            "submitted_at": "2026-07-29T00:00:00Z",
        },
        headers=headers,
    )
    wf_resp = await client.get(f"/api/v1/retainer/candidates/{candidate_id}", headers=headers)
    wf_id = wf_resp.json()["workflow_id"]
    resp = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/templates/resolve",
        json={
            "template_definition_id": str(uuid.uuid4()),
            "template_version": "1.0.0",
            "policy_version_id": str(uuid.uuid4()),
            "merge_fields": [],
        },
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_generate_package_happy_path(client):
    tenant_id, wf_id, headers = await _setup_at_package_prep(client)
    r = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/templates/resolve",
        json={
            "template_definition_id": str(uuid.uuid4()),
            "template_version": "1.0.0",
            "policy_version_id": str(uuid.uuid4()),
            "merge_fields": [
                {"field_name": "client_name", "field_value": "John Doe"},
            ],
        },
        headers=headers,
    )
    resolution_id = r.json()["resolution_id"]

    resp = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages",
        json={
            "template_resolution_id": resolution_id,
            "document_roles": ["engagement_letter", "fee_agreement"],
            "preflight_controls": [
                {"control_id": "REQ_001", "control_name": "Merge fields valid", "passed": True},
                {"control_id": "REQ_002", "control_name": "Disclosures present", "passed": True},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["package_hash"]
    assert len(data["documents"]) == 2
    assert len(data["preflight_results"]) == 2


@pytest.mark.asyncio
async def test_generate_package_fails_preflight(client):
    tenant_id, wf_id, headers = await _setup_at_package_prep(client)
    r = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/templates/resolve",
        json={
            "template_definition_id": str(uuid.uuid4()),
            "template_version": "1.0.0",
            "policy_version_id": str(uuid.uuid4()),
            "merge_fields": [],
        },
        headers=headers,
    )
    resolution_id = r.json()["resolution_id"]

    resp = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages",
        json={
            "template_resolution_id": resolution_id,
            "document_roles": ["engagement_letter"],
            "preflight_controls": [
                {"control_id": "CHK_001", "control_name": "Check", "passed": False},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_package_detail(client):
    tenant_id, wf_id, headers = await _setup_at_package_prep(client)
    r = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/templates/resolve",
        json={
            "template_definition_id": str(uuid.uuid4()),
            "template_version": "1.0.0",
            "policy_version_id": str(uuid.uuid4()),
            "merge_fields": [],
        },
        headers=headers,
    )
    resolution_id = r.json()["resolution_id"]
    p = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages",
        json={"template_resolution_id": resolution_id, "document_roles": ["engagement_letter"]},
        headers=headers,
    )
    package_id = p.json()["package_id"]

    resp = await client.get(f"/api/v1/retainer/packages/{package_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["package_hash"]
    assert len(data["documents"]) == 1


@pytest.mark.asyncio
async def test_cross_tenant_package_isolation(client):
    tenant_id, wf_id, headers = await _setup_at_package_prep(client)
    r = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/templates/resolve",
        json={
            "template_definition_id": str(uuid.uuid4()),
            "template_version": "1.0.0",
            "policy_version_id": str(uuid.uuid4()),
            "merge_fields": [],
        },
        headers=headers,
    )
    resolution_id = r.json()["resolution_id"]
    p = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages",
        json={"template_resolution_id": resolution_id, "document_roles": ["engagement_letter"]},
        headers=headers,
    )
    package_id = p.json()["package_id"]

    other_headers = auth_header(firm_id=str(uuid.uuid4()), role="attorney")
    resp = await client.get(f"/api/v1/retainer/packages/{package_id}", headers=other_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_template_resolution_is_idempotent_per_version(client):
    tenant_id, wf_id, headers = await _setup_at_package_prep(client)
    payload = {
        "template_definition_id": str(uuid.uuid4()),
        "template_version": "1.0.0",
        "policy_version_id": str(uuid.uuid4()),
        "merge_fields": [],
    }
    r1 = await client.post(f"/api/v1/retainer/workflows/{wf_id}/templates/resolve", json=payload, headers=headers)
    assert r1.status_code == 201
    rid1 = r1.json()["resolution_id"]

    r2 = await client.post(f"/api/v1/retainer/workflows/{wf_id}/templates/resolve", json=payload, headers=headers)
    assert r2.status_code == 201
    assert r2.json()["resolution_id"] == rid1


@pytest.mark.asyncio
async def test_package_has_immutable_hashes(client):
    tenant_id, wf_id, headers = await _setup_at_package_prep(client)
    r = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/templates/resolve",
        json={
            "template_definition_id": str(uuid.uuid4()),
            "template_version": "1.0.0",
            "policy_version_id": str(uuid.uuid4()),
            "merge_fields": [],
        },
        headers=headers,
    )
    resolution_id = r.json()["resolution_id"]

    p1 = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages",
        json={"template_resolution_id": resolution_id, "document_roles": ["engagement_letter"]},
        headers=headers,
    )
    assert p1.status_code == 201
    hash1 = p1.json()["package_hash"]
    assert len(hash1) == 64
    for doc in p1.json()["documents"]:
        assert len(doc["document_hash"]) == 64
