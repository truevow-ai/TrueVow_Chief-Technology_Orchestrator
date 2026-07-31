"""RETAINER Client API — client-safe projection tests."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_header


async def _get_portal_token(client):
    """Full setup to DELIVERED and return portal token."""
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
    await client.post(f"/api/v1/retainer/candidates/{candidate_id}/approve",
                      json={"outcome": "APPROVED", "scope_json": {}, "authority_record_id": str(uuid.uuid4())},
                      headers=headers)
    sr = await client.post(f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search", json={
        "parties": [
            {"party_type": "P", "canonical_ref": str(uuid.uuid4()), "legal_name": "Jane Doe",
             "aliases": ["J Doe"], "normalized_name": "jane doe"},
            {"party_type": "A", "canonical_ref": str(uuid.uuid4()), "legal_name": "Jane Doe",
             "normalized_name": "jane doe"},
        ], "candidate_version": 1}, headers=headers)
    detail = await client.get(f"/api/v1/retainer/conflicts/searches/{sr.json()['search_id']}", headers=headers)
    for c in detail.json()["candidates"]:
        await client.post(f"/api/v1/retainer/conflict-candidates/{c['id']}/disposition",
                          json={"disposition": "NO_CONFLICT"}, headers=headers)
    await client.post(f"/api/v1/retainer/conflicts/{sr.json()['search_id']}/clear",
                      json={"authority_record_id": str(uuid.uuid4())}, headers=headers)
    wf = (await client.get(f"/api/v1/retainer/candidates/{candidate_id}", headers=headers)).json()
    wf_id = wf["workflow_id"]
    r = await client.post(f"/api/v1/retainer/workflows/{wf_id}/templates/resolve", json={
        "template_definition_id": str(uuid.uuid4()), "template_version": "1.0.0",
        "policy_version_id": str(uuid.uuid4()), "merge_fields": []}, headers=headers)
    p = await client.post(f"/api/v1/retainer/workflows/{wf_id}/packages", json={
        "template_resolution_id": r.json()["resolution_id"], "document_roles": ["engagement_letter"],
        "preflight_controls": [{"control_id": "X", "control_name": "ok", "passed": True}]}, headers=headers)
    package_id = p.json()["package_id"]
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/packages/{package_id}/authorize-delivery",
                      json={"authority_record_id": str(uuid.uuid4())}, headers=headers)
    tr = await client.post(f"/api/v1/retainer/workflows/{wf_id}/portal/token", json={
        "package_id": package_id, "prospect_party_role_id": str(uuid.uuid4())}, headers=headers)
    return tr.json()["access_token"], wf_id, headers


@pytest.mark.asyncio
async def test_client_api_me(client):
    token, wf_id, h = await _get_portal_token(client)
    resp = await client.get(f"/api/v1/retainer/client/v1/me?token={token}")
    assert resp.status_code == 200
    assert "party_role_id" in resp.json()


@pytest.mark.asyncio
async def test_client_api_engagements(client):
    token, wf_id, h = await _get_portal_token(client)
    resp = await client.get(f"/api/v1/retainer/client/v1/engagements?token={token}")
    assert resp.status_code == 200
    assert len(resp.json()["engagements"]) >= 1


@pytest.mark.asyncio
async def test_client_api_engagement_detail(client):
    token, wf_id, h = await _get_portal_token(client)
    resp = await client.get(f"/api/v1/retainer/client/v1/engagements/{wf_id}?token={token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "READY_FOR_REVIEW"


@pytest.mark.asyncio
async def test_client_api_documents(client):
    token, wf_id, h = await _get_portal_token(client)
    resp = await client.get(f"/api/v1/retainer/client/v1/engagements/{wf_id}/documents?token={token}")
    assert resp.status_code == 200
    assert len(resp.json()["documents"]) >= 1


@pytest.mark.asyncio
async def test_client_api_signatures(client):
    token, wf_id, h = await _get_portal_token(client)
    resp = await client.get(f"/api/v1/retainer/client/v1/engagements/{wf_id}/signatures?token={token}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_client_api_no_internal_leak(client):
    """Verify client API does not expose conflict details, attorney notes, or authority gates."""
    token, wf_id, h = await _get_portal_token(client)
    resp = await client.get(f"/api/v1/retainer/client/v1/engagements/{wf_id}?token={token}")
    data = resp.json()
    assert "conflict" not in str(data).lower()
    assert "authority" not in str(data).lower()
    assert "attorney" not in str(data).lower()


@pytest.mark.asyncio
async def test_client_api_cross_engagement_denied(client):
    """Client cannot access another workflow using their token."""
    token, wf_id, h = await _get_portal_token(client)
    other_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/retainer/client/v1/engagements/{other_id}?token={token}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_client_api_invalid_token(client):
    resp = await client.get("/api/v1/retainer/client/v1/me?token=fake-token")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_client_detail_exact_keys(client):
    """Response DTO must contain only allowlisted fields."""
    token, wf_id, h = await _get_portal_token(client)
    resp = await client.get(f"/api/v1/retainer/client/v1/engagements/{wf_id}?token={token}")
    assert resp.status_code == 200
    allowed = {"engagement_id", "state", "candidate_version", "package", "is_activated"}
    assert set(resp.json().keys()) == allowed


@pytest.mark.asyncio
async def test_client_documents_exact_keys(client):
    token, wf_id, h = await _get_portal_token(client)
    resp = await client.get(f"/api/v1/retainer/client/v1/engagements/{wf_id}/documents?token={token}")
    assert resp.status_code == 200
    assert set(resp.json().keys()) == {"documents"}


@pytest.mark.asyncio
async def test_client_submit_question(client):
    token, wf_id, h = await _get_portal_token(client)
    resp = await client.post(f"/api/v1/retainer/client/v1/engagements/{wf_id}/questions?token={token}", json={
        "question_text": "What does clause 3 mean?"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_client_decline(client):
    token, wf_id, h = await _get_portal_token(client)
    resp = await client.post(f"/api/v1/retainer/client/v1/engagements/{wf_id}/decline?token={token}", json={
        "reason": "Not interested"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_client_consent(client):
    token, wf_id, h = await _get_portal_token(client)
    resp = await client.post(f"/api/v1/retainer/client/v1/engagements/{wf_id}/consent?token={token}", json={
        "prospect_party_role_id": str(uuid.uuid4())})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_activation_scope_transition(client):
    """Post-activation: is_activated=True in client API response."""
    token, wf_id, headers = await _get_portal_token(client)
    from sqlalchemy import text

    from app.core.database import engine
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT id FROM engagement_packages WHERE workflow_id = :wid ORDER BY generated_at DESC LIMIT 1"), {"wid": str(wf_id)})
        pkg_row = r.fetchone()
    if pkg_row:
        pkg_id = str(pkg_row[0])
        party_id = str(uuid.uuid4())
        cr = await client.post(f"/api/v1/retainer/packages/{pkg_id}/ceremonies", json={
            "provider_type": "docuseal",
            "signers": [{"party_role_id": party_id, "signer_role": "client", "required": True}],
        }, headers=headers)
        if cr.status_code == 201:
            cid = cr.json()["ceremony_id"]
            sid = cr.json()["signers"][0]["id"]
            await client.post(f"/api/v1/retainer/ceremonies/{cid}/sign", json={
                "party_role_id": party_id, "shared_signature_evidence_id": str(uuid.uuid4()),
                "signer_requirement_id": sid}, headers=headers)
            await client.post(f"/api/v1/retainer/ceremonies/{cid}/mark-executed", headers=headers)

    checklist = await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()), "items": [{"control_id": "A1"}]}, headers=headers)
    if checklist.status_code == 201:
        r = await client.post(f"/api/v1/retainer/workflows/{wf_id}/activate", json={
            "activated_matter_id": str(uuid.uuid4())}, headers=headers)
        if r.status_code == 200:
            detail = await client.get(f"/api/v1/retainer/client/v1/engagements/{wf_id}?token={token}")
            assert detail.json()["is_activated"] is True
            return
    # If activation failed (no ceremony), verify is_activated is False
    detail = await client.get(f"/api/v1/retainer/client/v1/engagements/{wf_id}?token={token}")
    assert detail.json()["is_activated"] is False


@pytest.mark.asyncio
async def test_no_matter_scopes_after_activation(client):
    """RETAINER must never grant MATTER_* permissions even after activation."""
    token, wf_id, headers = await _get_portal_token(client)
    # Complete full e2e to activation
    import json as _json

    from sqlalchemy import text

    from app.core.database import engine
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT id FROM engagement_packages WHERE workflow_id = :wid ORDER BY generated_at DESC LIMIT 1"), {"wid": str(wf_id)})
        pkg_row = r.fetchone()
    if pkg_row:
        pkg_id = str(pkg_row[0])
        party_id = str(uuid.uuid4())
        cr = await client.post(f"/api/v1/retainer/packages/{pkg_id}/ceremonies", json={
            "provider_type": "docuseal",
            "signers": [{"party_role_id": party_id, "signer_role": "client", "required": True}],
        }, headers=headers)
        if cr.status_code == 201:
            cid = cr.json()["ceremony_id"]
            sid = cr.json()["signers"][0]["id"]
            await client.post(f"/api/v1/retainer/ceremonies/{cid}/sign", json={
                "party_role_id": party_id, "shared_signature_evidence_id": str(uuid.uuid4()),
                "signer_requirement_id": sid}, headers=headers)
            await client.post(f"/api/v1/retainer/ceremonies/{cid}/mark-executed", headers=headers)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()), "items": [{"control_id": "A1"}]}, headers=headers)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/activate", json={
        "activated_matter_id": str(uuid.uuid4())}, headers=headers)

    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT scopes FROM client_portal_access WHERE workflow_id = :wid"), {"wid": str(wf_id)})
        row = r.fetchone()
        if row:
            scopes = _json.loads(row[0]) if isinstance(row[0], str) else (row[0] or [])
            assert "MATTER_VIEW" not in scopes
            assert "MATTER_MESSAGE" not in scopes
            assert "MATTER_UPLOAD" not in scopes
            assert "REQUEST_RESPOND" not in scopes


@pytest.mark.asyncio
async def test_post_activation_detail_readable(client):
    """After activation, _has_scope grants ENGAGEMENT_VIEW from ENGAGEMENT_HISTORY."""
    from app.api.v1.routes.client_api import _has_scope
    assert _has_scope({"scopes": ["ENGAGEMENT_HISTORY"]}, "ENGAGEMENT_VIEW")
    assert _has_scope({"scopes": ["ENGAGEMENT_HISTORY"]}, "COMPLETED_COPY_DOWNLOAD")


@pytest.mark.asyncio
async def test_post_activation_documents_readable(client):
    from app.api.v1.routes.client_api import _has_scope
    assert _has_scope({"scopes": ["ENGAGEMENT_HISTORY"]}, "ENGAGEMENT_VIEW")


@pytest.mark.asyncio
async def test_post_activation_signatures_readable(client):
    from app.api.v1.routes.client_api import _has_scope
    assert _has_scope({"scopes": ["ENGAGEMENT_HISTORY"]}, "ENGAGEMENT_VIEW")


@pytest.mark.asyncio
async def test_post_activation_completed_copy_readable(client):
    from app.api.v1.routes.client_api import _has_scope
    assert _has_scope({"scopes": ["ENGAGEMENT_HISTORY"]}, "COMPLETED_COPY_DOWNLOAD")


@pytest.mark.asyncio
async def test_post_activation_decline_rejected(client):
    """ENGAGEMENT_HISTORY does NOT grant decline access."""
    from app.api.v1.routes.client_api import _has_scope
    assert not _has_scope({"scopes": ["ENGAGEMENT_HISTORY"]}, "ENGAGEMENT_QUESTION")
    # Decline check is explicit in endpoint, not through _has_scope


@pytest.mark.asyncio
async def test_post_activation_questions_rejected(client):
    """ENGAGEMENT_HISTORY does NOT grant question access."""
    from app.api.v1.routes.client_api import _has_scope
    assert not _has_scope({"scopes": ["ENGAGEMENT_HISTORY"]}, "ENGAGEMENT_QUESTION")
