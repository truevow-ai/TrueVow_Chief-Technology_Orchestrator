"""BP-04 Client Engagement Portal integration tests."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_header


async def _setup_to_delivery_ready(client):
    """Setup through approve → conflict clear → template resolve → package generate → delivery auth."""
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")

    await client.post(
        "/api/v1/retainer/candidates/import",
        json={
            "tenant_id": tenant_id, "matter_candidate_id": candidate_id,
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
                {"party_type": "PROSPECTIVE_CLIENT", "canonical_ref": str(uuid.uuid4()),
                 "legal_name": "Acme Corp", "aliases": ["ACME Corporation"], "normalized_name": "acme corp"},
                {"party_type": "ADVERSE_PARTY", "canonical_ref": str(uuid.uuid4()),
                 "legal_name": "Acme Corp", "normalized_name": "acme corp"},
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
            json={"disposition": "NO_CONFLICT"}, headers=headers,
        )
    await client.post(
        f"/api/v1/retainer/conflicts/{search_id}/clear",
        json={"authority_record_id": str(uuid.uuid4())}, headers=headers,
    )
    wf_resp = await client.get(f"/api/v1/retainer/candidates/{candidate_id}", headers=headers)
    wf_id = wf_resp.json()["workflow_id"]

    r = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/templates/resolve",
        json={
            "template_definition_id": str(uuid.uuid4()),
            "template_version": "1.0.0",
            "policy_version_id": str(uuid.uuid4()),
            "merge_fields": [{"field_name": "client_name", "field_value": "John Doe"}],
        },
        headers=headers,
    )
    resolution_id = r.json()["resolution_id"]
    p = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages",
        json={
            "template_resolution_id": resolution_id,
            "document_roles": ["engagement_letter"],
            "preflight_controls": [{"control_id": "CHK", "control_name": "ok", "passed": True}],
        },
        headers=headers,
    )
    return tenant_id, wf_id, p.json(), headers


@pytest.mark.asyncio
async def test_authorize_delivery(client):
    tenant_id, wf_id, package, headers = await _setup_to_delivery_ready(client)
    package_id = package["package_id"]

    resp = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages/{package_id}/authorize-delivery",
        json={"authority_record_id": str(uuid.uuid4()), "channel": "portal"},
        headers=headers,
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_generate_portal_token(client):
    tenant_id, wf_id, package, headers = await _setup_to_delivery_ready(client)
    package_id = package["package_id"]

    await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages/{package_id}/authorize-delivery",
        json={"authority_record_id": str(uuid.uuid4())}, headers=headers,
    )

    resp = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/portal/token",
        json={"package_id": package_id, "prospect_party_role_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    assert len(token) > 30


@pytest.mark.asyncio
async def test_portal_access_with_token(client):
    tenant_id, wf_id, package, headers = await _setup_to_delivery_ready(client)
    package_id = package["package_id"]
    await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages/{package_id}/authorize-delivery",
        json={"authority_record_id": str(uuid.uuid4())}, headers=headers,
    )
    tr = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/portal/token",
        json={"package_id": package_id, "prospect_party_role_id": str(uuid.uuid4())},
        headers=headers,
    )
    token = tr.json()["access_token"]

    resp = await client.get(f"/api/v1/retainer/portal/access?token={token}")
    assert resp.status_code == 200
    assert len(resp.json()["documents"]) >= 1


@pytest.mark.asyncio
async def test_invalid_portal_token(client):
    resp = await client.get("/api/v1/retainer/portal/access?token=invalid-token")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_grant_esign_consent(client):
    tenant_id, wf_id, package, headers = await _setup_to_delivery_ready(client)
    package_id = package["package_id"]
    await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages/{package_id}/authorize-delivery",
        json={"authority_record_id": str(uuid.uuid4())}, headers=headers,
    )
    tr = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/portal/token",
        json={"package_id": package_id, "prospect_party_role_id": str(uuid.uuid4())},
        headers=headers,
    )
    token = tr.json()["access_token"]

    resp = await client.post(
        f"/api/v1/retainer/portal/consent?token={token}",
        json={"prospect_party_role_id": str(uuid.uuid4()), "ip_address": "127.0.0.1"},
    )
    assert resp.status_code == 201
    assert resp.json()["state"] == "GRANTED"


@pytest.mark.asyncio
async def test_submit_client_question(client):
    tenant_id, wf_id, package, headers = await _setup_to_delivery_ready(client)
    package_id = package["package_id"]
    await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages/{package_id}/authorize-delivery",
        json={"authority_record_id": str(uuid.uuid4())}, headers=headers,
    )
    tr = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/portal/token",
        json={"package_id": package_id, "prospect_party_role_id": str(uuid.uuid4())},
        headers=headers,
    )
    token = tr.json()["access_token"]

    resp = await client.post(
        f"/api/v1/retainer/portal/questions?token={token}",
        json={"question_text": "What does clause 4 mean?"},
    )
    assert resp.status_code == 201
    assert resp.json()["state"] == "RECEIVED"


@pytest.mark.asyncio
async def test_client_decline(client):
    tenant_id, wf_id, package, headers = await _setup_to_delivery_ready(client)
    package_id = package["package_id"]
    await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages/{package_id}/authorize-delivery",
        json={"authority_record_id": str(uuid.uuid4())}, headers=headers,
    )
    tr = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/portal/token",
        json={"package_id": package_id, "prospect_party_role_id": str(uuid.uuid4())},
        headers=headers,
    )
    token = tr.json()["access_token"]

    resp = await client.post(
        f"/api/v1/retainer/portal/decline?token={token}",
        json={"reason": "Not interested"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "DECLINED_OR_EXPIRED"


@pytest.mark.asyncio
async def test_cannot_generate_token_before_authorization(client):
    tenant_id, wf_id, package, headers = await _setup_to_delivery_ready(client)
    resp = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/portal/token",
        json={"package_id": package["package_id"], "prospect_party_role_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert resp.status_code == 409
