"""BP-05 Signature Ceremony integration tests."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_header


async def _setup_to_delivered(client):
    """Full setup through approval → conflict clear → template → package → delivery → portal token."""
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
        json={"template_definition_id": str(uuid.uuid4()), "template_version": "1.0.0",
              "policy_version_id": str(uuid.uuid4()), "merge_fields": []},
        headers=headers,
    )
    p = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages",
        json={"template_resolution_id": r.json()["resolution_id"],
              "document_roles": ["engagement_letter"],
              "preflight_controls": [{"control_id": "X", "control_name": "ok", "passed": True}]},
        headers=headers,
    )
    package_id = p.json()["package_id"]
    await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/packages/{package_id}/authorize-delivery",
        json={"authority_record_id": str(uuid.uuid4())}, headers=headers,
    )
    tr = await client.post(
        f"/api/v1/retainer/workflows/{wf_id}/portal/token",
        json={"package_id": package_id, "prospect_party_role_id": str(uuid.uuid4())},
        headers=headers,
    )
    return tenant_id, wf_id, package_id, headers


@pytest.mark.asyncio
async def test_create_ceremony(client):
    tenant_id, wf_id, package_id, headers = await _setup_to_delivered(client)
    resp = await client.post(
        f"/api/v1/retainer/packages/{package_id}/ceremonies",
        json={
            "provider_type": "docuseal",
            "signers": [
                {"party_role_id": str(uuid.uuid4()), "signer_role": "client", "required": True},
                {"party_role_id": str(uuid.uuid4()), "signer_role": "attorney", "required": True},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["state"] == "CREATED"
    assert len(resp.json()["signers"]) == 2


@pytest.mark.asyncio
async def test_get_ceremony_detail(client):
    tenant_id, wf_id, package_id, headers = await _setup_to_delivered(client)
    cr = await client.post(
        f"/api/v1/retainer/packages/{package_id}/ceremonies",
        json={"provider_type": "docuseal", "signers": [
            {"party_role_id": str(uuid.uuid4()), "signer_role": "client", "required": True}
        ]},
        headers=headers,
    )
    ceremony_id = cr.json()["ceremony_id"]
    resp = await client.get(f"/api/v1/retainer/ceremonies/{ceremony_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["state"] == "CREATED"


@pytest.mark.asyncio
async def test_apply_signature(client):
    tenant_id, wf_id, package_id, headers = await _setup_to_delivered(client)
    party_id = str(uuid.uuid4())
    cr = await client.post(
        f"/api/v1/retainer/packages/{package_id}/ceremonies",
        json={"provider_type": "docuseal", "signers": [
            {"party_role_id": party_id, "signer_role": "client", "required": True}
        ]},
        headers=headers,
    )
    ceremony_id = cr.json()["ceremony_id"]
    signer_req_id = cr.json()["signers"][0]["id"]

    resp = await client.post(
        f"/api/v1/retainer/ceremonies/{ceremony_id}/sign",
        json={
            "party_role_id": party_id,
            "shared_signature_evidence_id": str(uuid.uuid4()),
            "signer_requirement_id": signer_req_id,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["validity_state"] == "VALID"


@pytest.mark.asyncio
async def test_invalidate_signature(client):
    tenant_id, wf_id, package_id, headers = await _setup_to_delivered(client)
    cr = await client.post(
        f"/api/v1/retainer/packages/{package_id}/ceremonies",
        json={"provider_type": "docuseal", "signers": [
            {"party_role_id": str(uuid.uuid4()), "signer_role": "client", "required": True}
        ]},
        headers=headers,
    )
    ceremony_id = cr.json()["ceremony_id"]
    signer_req_id = cr.json()["signers"][0]["id"]

    sr = await client.post(
        f"/api/v1/retainer/ceremonies/{ceremony_id}/sign",
        json={"party_role_id": str(uuid.uuid4()), "shared_signature_evidence_id": str(uuid.uuid4()),
              "signer_requirement_id": signer_req_id},
        headers=headers,
    )
    evidence_id = sr.json()["evidence_id"]

    resp = await client.post(
        f"/api/v1/retainer/ceremonies/{ceremony_id}/invalidate-signature",
        json={"evidence_id": evidence_id, "reason": "Mismatched document hash"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["validity_state"] == "INVALIDATED"


@pytest.mark.asyncio
async def test_mark_fully_executed(client):
    tenant_id, wf_id, package_id, headers = await _setup_to_delivered(client)
    party_id = str(uuid.uuid4())
    cr = await client.post(
        f"/api/v1/retainer/packages/{package_id}/ceremonies",
        json={"provider_type": "docuseal", "signers": [
            {"party_role_id": party_id, "signer_role": "client", "required": True}
        ]},
        headers=headers,
    )
    ceremony_id = cr.json()["ceremony_id"]
    signer_req_id = cr.json()["signers"][0]["id"]

    await client.post(
        f"/api/v1/retainer/ceremonies/{ceremony_id}/sign",
        json={"party_role_id": party_id, "shared_signature_evidence_id": str(uuid.uuid4()),
              "signer_requirement_id": signer_req_id},
        headers=headers,
    )

    resp = await client.post(
        f"/api/v1/retainer/ceremonies/{ceremony_id}/mark-executed",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "FULLY_EXECUTED"


@pytest.mark.asyncio
async def test_mark_executed_fails_without_signatures(client):
    tenant_id, wf_id, package_id, headers = await _setup_to_delivered(client)
    cr = await client.post(
        f"/api/v1/retainer/packages/{package_id}/ceremonies",
        json={"provider_type": "docuseal", "signers": [
            {"party_role_id": str(uuid.uuid4()), "signer_role": "client", "required": True}
        ]},
        headers=headers,
    )
    ceremony_id = cr.json()["ceremony_id"]

    resp = await client.post(
        f"/api/v1/retainer/ceremonies/{ceremony_id}/mark-executed",
        headers=headers,
    )
    assert resp.status_code == 409
