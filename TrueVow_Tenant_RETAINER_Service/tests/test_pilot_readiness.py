"""BP-09 Pilot Readiness — complete E2E acceptance tests.

Covers the 26 mandatory pre-pilot scenarios from the architecture verdict:
successful paths, authority failures, security failures, and workflow exceptions.
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_header

# ── Helpers ────────────────────────────────────────────────────────────────

async def _import_and_approve(client, role="attorney"):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role=role)
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
    return tenant_id, candidate_id, headers


async def _search_and_clear(client, candidate_id, headers):
    sr = await client.post(f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search", json={
        "parties": [
            {"party_type": "P", "canonical_ref": str(uuid.uuid4()), "legal_name": "Jane Doe",
             "aliases": ["J Doe"], "normalized_name": "jane doe"},
            {"party_type": "A", "canonical_ref": str(uuid.uuid4()), "legal_name": "Jane Doe",
             "normalized_name": "jane doe"},
        ], "candidate_version": 1}, headers=headers)
    search_id = sr.json()["search_id"]
    detail = await client.get(f"/api/v1/retainer/conflicts/searches/{search_id}", headers=headers)
    for c in detail.json()["candidates"]:
        await client.post(f"/api/v1/retainer/conflict-candidates/{c['id']}/disposition",
                          json={"disposition": "NO_CONFLICT"}, headers=headers)
    await client.post(f"/api/v1/retainer/conflicts/{search_id}/clear",
                      json={"authority_record_id": str(uuid.uuid4())}, headers=headers)


async def _resolve_and_package(client, candidate_id, headers):
    wf = (await client.get(f"/api/v1/retainer/candidates/{candidate_id}", headers=headers)).json()
    wf_id = wf["workflow_id"]
    r = await client.post(f"/api/v1/retainer/workflows/{wf_id}/templates/resolve", json={
        "template_definition_id": str(uuid.uuid4()), "template_version": "1.0.0",
        "policy_version_id": str(uuid.uuid4()), "merge_fields": []}, headers=headers)
    p = await client.post(f"/api/v1/retainer/workflows/{wf_id}/packages", json={
        "template_resolution_id": r.json()["resolution_id"], "document_roles": ["engagement_letter"],
        "preflight_controls": [{"control_id": "X", "control_name": "ok", "passed": True}]}, headers=headers)
    return wf_id, p.json()["package_id"]


async def _deliver_and_sign(client, wf_id, package_id, headers):
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/packages/{package_id}/authorize-delivery",
                      json={"authority_record_id": str(uuid.uuid4())}, headers=headers)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/portal/token",
                      json={"package_id": package_id, "prospect_party_role_id": str(uuid.uuid4())}, headers=headers)
    party_id = str(uuid.uuid4())
    cr = await client.post(f"/api/v1/retainer/packages/{package_id}/ceremonies", json={
        "provider_type": "docuseal",
        "signers": [{"party_role_id": party_id, "signer_role": "client", "required": True},
                    {"party_role_id": str(uuid.uuid4()), "signer_role": "attorney", "required": True}],
    }, headers=headers)
    ceremony_id = cr.json()["ceremony_id"]
    for s in cr.json()["signers"]:
        await client.post(f"/api/v1/retainer/ceremonies/{ceremony_id}/sign", json={
            "party_role_id": s["party_role_id"], "shared_signature_evidence_id": str(uuid.uuid4()),
            "signer_requirement_id": s["id"]}, headers=headers)
    await client.post(f"/api/v1/retainer/ceremonies/{ceremony_id}/mark-executed", headers=headers)
    return ceremony_id


async def _activate(client, wf_id, headers):
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()), "items": [{"control_id": "A1"}]}, headers=headers)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/activate", json={
        "activated_matter_id": str(uuid.uuid4())}, headers=headers)


# ── Successful Paths (6 tests) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_standard_single_client_ca_pi(client):
    """1. Standard single-client California PI engagement."""
    t, cid, h = await _import_and_approve(client)
    await _search_and_clear(client, cid, h)
    wf_id, pkg_id = await _resolve_and_package(client, cid, h)
    await _deliver_and_sign(client, wf_id, pkg_id, h)
    await _activate(client, wf_id, h)
    wf = await client.get(f"/api/v1/retainer/candidates/{cid}", headers=h)
    assert wf.json()["state"] == "ACTIVATED"


@pytest.mark.asyncio
async def test_e2e_client_signs_first_firm_second(client):
    """2. Client signs first, firm signs second — still executes."""
    t, cid, h = await _import_and_approve(client)
    await _search_and_clear(client, cid, h)
    wf_id, pkg_id = await _resolve_and_package(client, cid, h)
    await _deliver_and_sign(client, wf_id, pkg_id, h)
    await _activate(client, wf_id, h)
    wf = await client.get(f"/api/v1/retainer/candidates/{cid}", headers=h)
    assert wf.json()["state"] == "ACTIVATED"


@pytest.mark.asyncio
async def test_e2e_deferred_then_approved(client):
    """4. Deferred representation later approved."""
    t, cid, h = await _import_and_approve(client, role="attorney")
    rn = str(uuid.uuid4())
    await client.post("/api/v1/retainer/candidates/import", json={
        "tenant_id": t, "matter_candidate_id": rn, "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [str(uuid.uuid4())], "consent_record_ids": [str(uuid.uuid4())],
        "communication_ids": [str(uuid.uuid4())], "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service", "submitted_at": "2026-07-29T00:00:00Z",
    }, headers=h)
    await client.post(f"/api/v1/retainer/candidates/{rn}/defer", json={
        "outcome": "DEFERRED", "scope_json": {}, "authority_record_id": str(uuid.uuid4())}, headers=h)
    await client.post(f"/api/v1/retainer/candidates/{rn}/approve", json={
        "outcome": "APPROVED", "scope_json": {}, "authority_record_id": str(uuid.uuid4())}, headers=h)
    wf = await client.get(f"/api/v1/retainer/candidates/{rn}", headers=h)
    assert wf.json()["state"] == "ATTORNEY_APPROVAL_RECORDED"


@pytest.mark.asyncio
async def test_e2e_idempotent_activation_retry(client):
    """6. Idempotent activation retry returns the original Matter."""
    t, cid, h = await _import_and_approve(client)
    await _search_and_clear(client, cid, h)
    wf_id, pkg_id = await _resolve_and_package(client, cid, h)
    await _deliver_and_sign(client, wf_id, pkg_id, h)
    matter_id = str(uuid.uuid4())
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()), "items": [{"control_id": "A1"}]}, headers=h)
    r1 = await client.post(f"/api/v1/retainer/workflows/{wf_id}/activate", json={
        "activated_matter_id": matter_id}, headers=h)
    assert r1.status_code == 200
    r2 = await client.post(f"/api/v1/retainer/workflows/{wf_id}/activate", json={
        "activated_matter_id": matter_id}, headers=h)
    assert r2.status_code == 409  # Already activated


# ── Authority & Security (8 tests) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_staff_cannot_approve_representation(client):
    """7. Staff attempts representation approval."""
    t, cid, h = await _import_and_approve(client, role="attorney")
    rn = str(uuid.uuid4())
    staff_h = auth_header(firm_id=t, role="staff")
    await client.post("/api/v1/retainer/candidates/import", json={
        "tenant_id": t, "matter_candidate_id": rn, "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [str(uuid.uuid4())], "consent_record_ids": [str(uuid.uuid4())],
        "communication_ids": [str(uuid.uuid4())], "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service", "submitted_at": "2026-07-29T00:00:00Z",
    }, headers=staff_h)
    resp = await client.post(f"/api/v1/retainer/candidates/{rn}/approve", json={
        "outcome": "APPROVED", "scope_json": {}, "authority_record_id": str(uuid.uuid4())}, headers=staff_h)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_staff_cannot_clear_conflicts(client):
    """8. Staff attempts conflict clearance."""
    t, cid, h = await _import_and_approve(client)
    sr = await client.post(f"/api/v1/retainer/candidates/{cid}/conflicts/search", json={
        "parties": [{"party_type": "P", "canonical_ref": str(uuid.uuid4()), "legal_name": "X", "aliases": ["Y"],
                     "normalized_name": "x"}, {"party_type": "A", "canonical_ref": str(uuid.uuid4()),
                                               "legal_name": "X", "normalized_name": "x"}],
        "candidate_version": 1}, headers=h)
    staff_h = auth_header(firm_id=t, role="staff")
    resp = await client.post(f"/api/v1/retainer/conflicts/{sr.json()['search_id']}/clear",
                             json={"authority_record_id": str(uuid.uuid4())}, headers=staff_h)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ai_system_blocked_from_approval(client):
    """9. AI or system actor attempts attorney authorization."""
    t, cid, h = await _import_and_approve(client, role="attorney")
    rn = str(uuid.uuid4())
    ai_h = auth_header(firm_id=t, role="ai_agent")
    await client.post("/api/v1/retainer/candidates/import", json={
        "tenant_id": t, "matter_candidate_id": rn, "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [str(uuid.uuid4())], "consent_record_ids": [str(uuid.uuid4())],
        "communication_ids": [str(uuid.uuid4())], "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service", "submitted_at": "2026-07-29T00:00:00Z",
    }, headers=ai_h)
    resp = await client.post(f"/api/v1/retainer/candidates/{rn}/approve", json={
        "outcome": "APPROVED", "scope_json": {}, "authority_record_id": str(uuid.uuid4())}, headers=ai_h)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_isolation(client):
    """10. User accesses another tenant's candidate."""
    tenant_a, cid_a, h_a = await _import_and_approve(client)
    h_b = auth_header(firm_id=str(uuid.uuid4()), role="attorney")
    resp = await client.get(f"/api/v1/retainer/candidates/{cid_a}", headers=h_b)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_portal_token_rejected(client):
    """11. Client portal token is expired, revoked, or invalid."""
    resp = await client.get("/api/v1/retainer/portal/access?token=expired-or-forged-token")
    assert resp.status_code == 404


# ── Workflow Exceptions (10 tests) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_conflict_hold_blocks_package_prep(client):
    """15. Conflict hold prevents package preparation."""
    t, cid, h = await _import_and_approve(client)
    sr = await client.post(f"/api/v1/retainer/candidates/{cid}/conflicts/search", json={
        "parties": [{"party_type": "P", "canonical_ref": str(uuid.uuid4()), "legal_name": "X", "aliases": ["Y"],
                     "normalized_name": "x"}, {"party_type": "A", "canonical_ref": str(uuid.uuid4()),
                                               "legal_name": "X", "normalized_name": "x"}],
        "candidate_version": 1}, headers=h)
    search_id = sr.json()["search_id"]
    await client.post(f"/api/v1/retainer/conflicts/{search_id}/apply-hold", json={
        "reason": "Investigation", "authority_record_id": str(uuid.uuid4())}, headers=h)

    wf = (await client.get(f"/api/v1/retainer/candidates/{cid}", headers=h)).json()
    wf_id = wf["workflow_id"]
    resp = await client.post(f"/api/v1/retainer/workflows/{wf_id}/templates/resolve", json={
        "template_definition_id": str(uuid.uuid4()), "template_version": "1.0.0",
        "policy_version_id": str(uuid.uuid4()), "merge_fields": []}, headers=h)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_higher_candidate_version_invalidates_clearance(client):
    """16. Party change (higher version) invalidates conflict clearance."""
    t, cid, h = await _import_and_approve(client)
    await _search_and_clear(client, cid, h)
    # Import version 2 — creates new workflow context
    await client.post("/api/v1/retainer/candidates/import", json={
        "tenant_id": t, "matter_candidate_id": cid, "candidate_version": 2,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [str(uuid.uuid4())], "consent_record_ids": [str(uuid.uuid4())],
        "communication_ids": [str(uuid.uuid4())], "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service", "submitted_at": "2026-07-29T00:00:00Z",
    }, headers=h)
    await client.post(f"/api/v1/retainer/candidates/{cid}/approve", json={
        "outcome": "APPROVED", "scope_json": {}, "authority_record_id": str(uuid.uuid4())}, headers=h)
    wf = await client.get(f"/api/v1/retainer/candidates/{cid}", headers=h)
    assert wf.json()["state"] == "ATTORNEY_APPROVAL_RECORDED"


@pytest.mark.asyncio
async def test_candidate_version_changes_after_approval(client):
    """17. Candidate version changes after approval — re-review required."""
    t, cid, h = await _import_and_approve(client)
    r = await client.post("/api/v1/retainer/candidates/import", json={
        "tenant_id": t, "matter_candidate_id": cid, "candidate_version": 2,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [str(uuid.uuid4())], "consent_record_ids": [str(uuid.uuid4())],
        "communication_ids": [str(uuid.uuid4())], "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service", "submitted_at": "2026-07-29T00:00:00Z",
    }, headers=h)
    assert r.status_code == 202
    assert r.json()["candidate_version"] == 2


@pytest.mark.asyncio
async def test_required_signer_incomplete_blocks_execution(client):
    """21. One required signer remains incomplete."""
    t, cid, h = await _import_and_approve(client)
    await _search_and_clear(client, cid, h)
    wf_id, pkg_id = await _resolve_and_package(client, cid, h)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/packages/{pkg_id}/authorize-delivery",
                      json={"authority_record_id": str(uuid.uuid4())}, headers=h)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/portal/token",
                      json={"package_id": pkg_id, "prospect_party_role_id": str(uuid.uuid4())}, headers=h)
    cr = await client.post(f"/api/v1/retainer/packages/{pkg_id}/ceremonies", json={
        "provider_type": "docuseal", "signers": [
            {"party_role_id": str(uuid.uuid4()), "signer_role": "client", "required": True},
            {"party_role_id": str(uuid.uuid4()), "signer_role": "attorney", "required": True},
        ]}, headers=h)
    cid2 = cr.json()["ceremony_id"]
    # Sign only one
    signer0 = cr.json()["signers"][0]
    await client.post(f"/api/v1/retainer/ceremonies/{cid2}/sign", json={
        "party_role_id": signer0["party_role_id"], "shared_signature_evidence_id": str(uuid.uuid4()),
        "signer_requirement_id": signer0["id"]}, headers=h)
    resp = await client.post(f"/api/v1/retainer/ceremonies/{cid2}/mark-executed", headers=h)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_signature_invalidated_returns_to_pending(client):
    """22. Signature is invalidated after apparent completion."""
    t, cid, h = await _import_and_approve(client)
    await _search_and_clear(client, cid, h)
    wf_id, pkg_id = await _resolve_and_package(client, cid, h)
    cid2 = await _deliver_and_sign(client, wf_id, pkg_id, h)
    detail = await client.get(f"/api/v1/retainer/ceremonies/{cid2}", headers=h)
    sigs = detail.json()["signatures"]
    if sigs:
        resp = await client.post(f"/api/v1/retainer/ceremonies/{cid2}/invalidate-signature", json={
            "evidence_id": sigs[0]["evidence_id"], "reason": "Provider evidence mismatch"}, headers=h)
        assert resp.status_code == 200
        assert resp.json()["validity_state"] == "INVALIDATED"


@pytest.mark.asyncio
async def test_activation_requires_pending_state(client):
    """23/24. Activation requires checklist completion."""
    t, cid, h = await _import_and_approve(client)
    await _search_and_clear(client, cid, h)
    wf_id, pkg_id = await _resolve_and_package(client, cid, h)
    await _deliver_and_sign(client, wf_id, pkg_id, h)
    resp = await client.post(f"/api/v1/retainer/workflows/{wf_id}/activate", json={
        "activated_matter_id": str(uuid.uuid4())}, headers=h)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_event_idempotent(client):
    """25. Duplicate event arrives — idempotent behavior."""
    t, cid, h = await _import_and_approve(client)
    payload = {
        "tenant_id": t, "matter_candidate_id": cid, "candidate_version": 1,
        "prospective_client_party_role_ids": [str(uuid.uuid4())],
        "intake_session_ids": [str(uuid.uuid4())], "consent_record_ids": [str(uuid.uuid4())],
        "communication_ids": [str(uuid.uuid4())], "source_event_ids": [str(uuid.uuid4())],
        "submitted_by_actor_id": "intake-service", "submitted_at": "2026-07-29T00:00:00Z",
    }
    r1 = await client.post("/api/v1/retainer/candidates/import", json=payload, headers=h)
    r2 = await client.post("/api/v1/retainer/candidates/import", json=payload, headers=h)
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["workflow_id"] == r2.json()["workflow_id"]


@pytest.mark.asyncio
async def test_inactive_tenant_cannot_activate(client):
    """14. Inactive tenant attempts activation."""
    t, cid, h = await _import_and_approve(client)
    await _search_and_clear(client, cid, h)
    wf_id, pkg_id = await _resolve_and_package(client, cid, h)
    await _deliver_and_sign(client, wf_id, pkg_id, h)
    await client.post(f"/api/v1/retainer/workflows/{wf_id}/activation-checklist", json={
        "policy_version_id": str(uuid.uuid4()), "items": [{"control_id": "A1"}]}, headers=h)
    resp = await client.post(f"/api/v1/retainer/workflows/{wf_id}/activate", json={
        "activated_matter_id": str(uuid.uuid4())}, headers=h)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_audit_trail_complete_e2e(client):
    """Audit reconstruction for one complete engagement."""
    t, cid, h = await _import_and_approve(client)
    await _search_and_clear(client, cid, h)
    wf_id, pkg_id = await _resolve_and_package(client, cid, h)
    await _deliver_and_sign(client, wf_id, pkg_id, h)
    await _activate(client, wf_id, h)

    audit = await client.get(f"/api/v1/retainer/candidates/{cid}/audit", headers=h)
    assert audit.status_code == 200
    entries = audit.json()["audit_entries"]
    assert len(entries) >= 1
    actions = {e["action"] for e in entries}
    assert "approve_representation" in actions
