"""BP-06 Communications & BP-07 Activation integration tests."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_header


async def _setup_to_fully_executed(client):
    """Shortcut: import → approve → conflict clear → template → package → delivery → token → ceremony → sign → executed."""
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
                      json={"outcome": "APPROVED", "scope_json": {}, "authority_record_id": str(uuid.uuid4())}, headers=headers)
    sr = await client.post(f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search", json={
        "parties": [
            {"party_type": "PROSPECTIVE_CLIENT", "canonical_ref": str(uuid.uuid4()), "legal_name": "Acme Corp",
             "aliases": ["ACME Corporation"], "normalized_name": "acme corp"},
            {"party_type": "ADVERSE_PARTY", "canonical_ref": str(uuid.uuid4()), "legal_name": "Acme Corp",
             "normalized_name": "acme corp"},
        ], "candidate_version": 1,
    }, headers=headers)
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
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/portal/token",
                      json={"package_id": package_id, "prospect_party_role_id": str(uuid.uuid4())}, headers=headers)
    party_id = str(uuid.uuid4())
    cr = await client.post(f"/api/v1/retainer/packages/{package_id}/ceremonies", json={
        "provider_type": "docuseal", "signers": [{"party_role_id": party_id, "signer_role": "client", "required": True}]},
        headers=headers)
    ceremony_id = cr.json()["ceremony_id"]
    await client.post(f"/api/v1/retainer/ceremonies/{ceremony_id}/sign", json={
        "party_role_id": party_id, "shared_signature_evidence_id": str(uuid.uuid4()),
        "signer_requirement_id": cr.json()["signers"][0]["id"]}, headers=headers)
    await client.post(f"/api/v1/retainer/ceremonies/{ceremony_id}/mark-executed", headers=headers)
    return tenant_id, wf_id, headers


@pytest.mark.asyncio
async def test_create_reminder_schedule(client):
    tenant_id, wf_id, headers = await _setup_to_fully_executed(client)
    resp = await client.post(f"/api/v1/retainer/workflows/{wf_id}/reminders", json={
        "policy_version_id": str(uuid.uuid4()), "max_attempts": 3}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["state"] == "ACTIVE"


@pytest.mark.asyncio
async def test_send_reminder(client):
    tenant_id, wf_id, headers = await _setup_to_fully_executed(client)
    sr = await client.post(f"/api/v1/retainer/workflows/{wf_id}/reminders", json={
        "policy_version_id": str(uuid.uuid4()), "max_attempts": 3}, headers=headers)
    schedule_id = sr.json()["schedule_id"]
    resp = await client.post(f"/api/v1/retainer/reminders/{schedule_id}/send", json={
        "communication_id": str(uuid.uuid4()), "attempt_no": 1, "result": "SENT"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["attempt_no"] == 1


@pytest.mark.asyncio
async def test_suppress_reminders(client):
    tenant_id, wf_id, headers = await _setup_to_fully_executed(client)
    sr = await client.post(f"/api/v1/retainer/workflows/{wf_id}/reminders", json={
        "policy_version_id": str(uuid.uuid4())}, headers=headers)
    schedule_id = sr.json()["schedule_id"]
    resp = await client.post(f"/api/v1/retainer/reminders/{schedule_id}/suppress", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_expire_engagement(client):
    tenant_id, wf_id, headers = await _setup_to_fully_executed(client)
    resp = await client.post(f"/api/v1/retainer/workflows/{wf_id}/expire", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["state"] == "DECLINED_OR_EXPIRED"


@pytest.mark.asyncio
async def test_cannot_expire_activated(client):
    tenant_id, wf_id, headers = await _setup_to_fully_executed(client)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()),
        "items": [{"control_id": "ACT_001", "required": True}]}, headers=headers)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/activate", json={
        "activated_matter_id": str(uuid.uuid4())}, headers=headers)
    resp = await client.post(f"/api/v1/retainer/workflows/{wf_id}/expire", headers=headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_activation_checklist(client):
    tenant_id, wf_id, headers = await _setup_to_fully_executed(client)
    resp = await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()),
        "items": [{"control_id": "ACT_001", "required": True}, {"control_id": "ACT_002", "required": False}]},
        headers=headers)
    assert resp.status_code == 201
    assert len(resp.json()["items"]) == 2


@pytest.mark.asyncio
async def test_evaluate_checklist_item(client):
    tenant_id, wf_id, headers = await _setup_to_fully_executed(client)
    cr = await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()),
        "items": [{"control_id": "ACT_001", "required": True}]}, headers=headers)
    item_id = cr.json()["items"][0]["id"]
    resp = await client.post(f"/api/v1/retainer/checklist-items/{item_id}/evaluate", json={
        "result": "PASSED"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["result"] == "PASSED"


@pytest.mark.asyncio
async def test_authorize_activation(client):
    tenant_id, wf_id, headers = await _setup_to_fully_executed(client)
    cr = await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()),
        "items": [{"control_id": "ACT_001", "required": True}]}, headers=headers)
    item_id = cr.json()["items"][0]["id"]
    await client.post(f"/api/v1/retainer/checklist-items/{item_id}/evaluate", json={"result": "PASSED"}, headers=headers)
    resp = await client.post(f"/api/v1/retainer/checklists/{cr.json()['checklist_id']}/authorize", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_authorize_fails_without_all_required_pass(client):
    tenant_id, wf_id, headers = await _setup_to_fully_executed(client)
    cr = await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()),
        "items": [{"control_id": "ACT_001", "required": True}]}, headers=headers)
    resp = await client.post(f"/api/v1/retainer/checklists/{cr.json()['checklist_id']}/authorize", headers=headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_confirm_matter_activated(client):
    tenant_id, wf_id, headers = await _setup_to_fully_executed(client)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()),
        "items": [{"control_id": "ACT_001", "required": True}]}, headers=headers)
    matter_id = str(uuid.uuid4())
    resp = await client.post(f"/api/v1/retainer/workflows/{wf_id}/activate", json={
        "activated_matter_id": matter_id}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["state"] == "ACTIVATED"
    assert resp.json()["activated_matter_id"] == matter_id


@pytest.mark.asyncio
async def test_trace_manifest(client):
    tenant_id, wf_id, headers = await _setup_to_fully_executed(client)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()), "items": [{"control_id": "A1"}]}, headers=headers)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/activate", json={
        "activated_matter_id": str(uuid.uuid4())}, headers=headers)

    resp = await client.get(f"/api/v1/retainer/workflows/{wf_id}/trace-manifest", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "manifest_id" in data
    assert "representation" in data
    assert "conflict_review" in data
    assert "package" in data
    assert "signatures" in data
    assert "activation" in data


@pytest.mark.asyncio
async def test_trace_manifest_requires_activated(client):
    tenant_id, wf_id, headers = await _setup_to_fully_executed(client)
    resp = await client.get(f"/api/v1/retainer/workflows/{wf_id}/trace-manifest", headers=headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_full_e2e_workflow(client):
    """End-to-end: import → approve → conflict clear → package → delivery → sign → activate."""
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
                      json={"outcome": "APPROVED", "scope_json": {}, "authority_record_id": str(uuid.uuid4())}, headers=headers)

    sr = await client.post(f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search", json={
        "parties": [{"party_type": "P", "canonical_ref": str(uuid.uuid4()), "legal_name": "X", "aliases": ["Y"],
                     "normalized_name": "x"}, {"party_type": "A", "canonical_ref": str(uuid.uuid4()),
                                               "legal_name": "X", "normalized_name": "x"}],
        "candidate_version": 1}, headers=headers)
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
        "template_resolution_id": r.json()["resolution_id"], "document_roles": ["el"],
        "preflight_controls": [{"control_id": "X", "control_name": "ok", "passed": True}]}, headers=headers)
    package_id = p.json()["package_id"]

    await client.post(f"/api/v1/retainer/workflows/{wf_id}/packages/{package_id}/authorize-delivery",
                      json={"authority_record_id": str(uuid.uuid4())}, headers=headers)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/portal/token",
                      json={"package_id": package_id, "prospect_party_role_id": str(uuid.uuid4())}, headers=headers)

    party_id = str(uuid.uuid4())
    cr = await client.post(f"/api/v1/retainer/packages/{package_id}/ceremonies", json={
        "provider_type": "docuseal", "signers": [{"party_role_id": party_id, "signer_role": "c", "required": True}]},
        headers=headers)
    await client.post(f"/api/v1/retainer/ceremonies/{cr.json()['ceremony_id']}/sign", json={
        "party_role_id": party_id, "shared_signature_evidence_id": str(uuid.uuid4()),
        "signer_requirement_id": cr.json()["signers"][0]["id"]}, headers=headers)
    await client.post(f"/api/v1/retainer/ceremonies/{cr.json()['ceremony_id']}/mark-executed", headers=headers)

    await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()), "items": [{"control_id": "A1"}]}, headers=headers)
    resp = await client.post(f"/api/v1/retainer/workflows/{wf_id}/activate", json={
        "activated_matter_id": str(uuid.uuid4())}, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["state"] == "ACTIVATED"
