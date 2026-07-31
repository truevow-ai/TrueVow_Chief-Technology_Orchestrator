"""BP-02 Conflict Search and Attorney Clearance integration tests."""

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


def _search_payload(candidate_version: int = 1):
    return {
        "parties": [
            {
                "party_type": "PROSPECTIVE_CLIENT",
                "canonical_ref": str(uuid.uuid4()),
                "legal_name": "John Doe",
                "aliases": ["Johnny Doe"],
                "normalized_name": "john doe",
                "relationship_to_candidate": "self",
            },
            {
                "party_type": "ADVERSE_PARTY",
                "canonical_ref": str(uuid.uuid4()),
                "legal_name": "Jane Smith",
                "normalized_name": "jane smith",
                "relationship_to_candidate": "adverse",
            },
        ],
        "candidate_version": candidate_version,
    }


async def _setup_approved_candidate(client, role="attorney"):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role=role)
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
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
    return tenant_id, candidate_id, headers


@pytest.mark.asyncio
async def test_conflict_search_happy_path(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)

    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "search_id" in data
    assert data["party_count"] == 2


@pytest.mark.asyncio
async def test_conflict_search_requires_approved_state(client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    headers = auth_header(firm_id=tenant_id, role="attorney")
    await client.post(
        "/api/v1/retainer/candidates/import",
        json=_import_payload(tenant_id, candidate_id),
        headers=headers,
    )
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_conflicts(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=headers,
    )
    resp = await client.get(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts",
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["searches"]) >= 1


@pytest.mark.asyncio
async def test_get_search_detail(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=headers,
    )
    search_id = search_resp.json()["search_id"]
    resp = await client.get(
        f"/api/v1/retainer/conflicts/searches/{search_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["search_id"] == search_id
    assert len(data["parties"]) == 2


@pytest.mark.asyncio
async def test_disposition_candidate(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=headers,
    )
    search_id = search_resp.json()["search_id"]

    detail = await client.get(
        f"/api/v1/retainer/conflicts/searches/{search_id}", headers=headers
    )
    candidates = detail.json()["candidates"]
    if candidates:
        candidate_match_id = candidates[0]["id"]
        resp = await client.post(
            f"/api/v1/retainer/conflict-candidates/{candidate_match_id}/disposition",
            json={"disposition": "NO_CONFLICT", "rationale": "Different person"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["disposition"] == "NO_CONFLICT"


@pytest.mark.asyncio
async def test_apply_hold_and_release(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=headers,
    )
    search_id = search_resp.json()["search_id"]

    hold_resp = await client.post(
        f"/api/v1/retainer/conflicts/{search_id}/apply-hold",
        json={
            "reason": "Need to investigate potential adverse party connection",
            "authority_record_id": str(uuid.uuid4()),
            "supporting_evidence": {"case_ref": "CASE-123"},
        },
        headers=headers,
    )
    assert hold_resp.status_code == 201
    hold_id = hold_resp.json()["hold_id"]

    detail = await client.get(
        f"/api/v1/retainer/conflicts/searches/{search_id}", headers=headers
    )
    assert detail.json()["current_hold"] is not None

    release_resp = await client.post(
        f"/api/v1/retainer/conflicts/{search_id}/release-hold",
        json={
            "authority_record_id": str(uuid.uuid4()),
            "reason": "Investigation complete — no conflict",
        },
        headers=headers,
    )
    assert release_resp.status_code == 200, release_resp.text
    assert release_resp.json()["hold_id"] == hold_id


@pytest.mark.asyncio
async def test_staff_cannot_approve_clear(client):
    tenant_id, candidate_id, att_hdrs = await _setup_approved_candidate(client, role="attorney")
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=att_hdrs,
    )
    search_id = search_resp.json()["search_id"]

    staff_h = auth_header(firm_id=tenant_id, role="staff")
    resp = await client.post(
        f"/api/v1/retainer/conflicts/{search_id}/clear",
        json={"authority_record_id": str(uuid.uuid4())},
        headers=staff_h,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_staff_cannot_apply_hold(client):
    tenant_id, candidate_id, att_headers = await _setup_approved_candidate(client)
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=att_headers,
    )
    search_id = search_resp.json()["search_id"]

    staff_h = auth_header(firm_id=tenant_id, role="staff")
    resp = await client.post(
        f"/api/v1/retainer/conflicts/{search_id}/apply-hold",
        json={
            "reason": "Test",
            "authority_record_id": str(uuid.uuid4()),
        },
        headers=staff_h,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ai_system_cannot_clear(client):
    tenant_id, candidate_id, att_headers = await _setup_approved_candidate(client)
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=att_headers,
    )
    search_id = search_resp.json()["search_id"]

    ai_h = auth_header(firm_id=tenant_id, role="ai_agent")
    resp = await client.post(
        f"/api/v1/retainer/conflicts/{search_id}/clear",
        json={"authority_record_id": str(uuid.uuid4())},
        headers=ai_h,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_clear_conflict_happy_path(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=headers,
    )
    search_id = search_resp.json()["search_id"]

    detail = await client.get(
        f"/api/v1/retainer/conflicts/searches/{search_id}", headers=headers
    )
    for c in detail.json()["candidates"]:
        await client.post(
            f"/api/v1/retainer/conflict-candidates/{c['id']}/disposition",
            json={"disposition": "NO_CONFLICT"},
            headers=headers,
        )

    resp = await client.post(
        f"/api/v1/retainer/conflicts/{search_id}/clear",
        json={"authority_record_id": str(uuid.uuid4()), "rationale": "All matches reviewed"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["outcome"] == "CLEARED"


@pytest.mark.asyncio
async def test_unresolved_candidate_blocks_clear(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    payload = {
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
    }
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=payload,
        headers=headers,
    )
    search_id = search_resp.json()["search_id"]

    resp = await client.post(
        f"/api/v1/retainer/conflicts/{search_id}/clear",
        json={"authority_record_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cross_tenant_isolation_conflict(client):
    tenant_a, candidate_a, headers_a = await _setup_approved_candidate(client)
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_a}/conflicts/search",
        json=_search_payload(),
        headers=headers_a,
    )
    search_id = search_resp.json()["search_id"]

    tenant_b = str(uuid.uuid4())
    headers_b = auth_header(firm_id=tenant_b, role="attorney")
    resp = await client.get(
        f"/api/v1/retainer/conflicts/searches/{search_id}", headers=headers_b
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_idempotent(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    payload = _search_payload()
    r1 = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=payload,
        headers=headers,
    )
    assert r1.status_code == 201
    s1 = r1.json()["search_id"]

    r2 = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=payload,
        headers=headers,
    )
    assert r2.status_code == 201
    assert r2.json()["search_id"] != s1


@pytest.mark.asyncio
async def test_hold_then_clear_transitions_to_package_prep(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    payload = {
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
    }
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=payload,
        headers=headers,
    )
    search_id = search_resp.json()["search_id"]

    await client.post(
        f"/api/v1/retainer/conflicts/{search_id}/apply-hold",
        json={"reason": "Investigation needed", "authority_record_id": str(uuid.uuid4())},
        headers=headers,
    )
    await client.post(
        f"/api/v1/retainer/conflicts/{search_id}/release-hold",
        json={"authority_record_id": str(uuid.uuid4()), "reason": "Resolved"},
        headers=headers,
    )

    detail = await client.get(
        f"/api/v1/retainer/conflicts/searches/{search_id}", headers=headers
    )
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

    resp = await client.get(
        f"/api/v1/retainer/candidates/{candidate_id}", headers=headers
    )
    assert resp.json()["state"] == "PACKAGE_PREPARATION"


@pytest.mark.asyncio
async def test_version_mismatch_blocks_search(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    payload = _search_payload(candidate_version=99)
    resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_higher_candidate_version_triggers_rerun(client):
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
        json={"outcome": "APPROVED", "scope_json": {}, "authority_record_id": str(uuid.uuid4())},
        headers=headers,
    )
    sr1 = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(1),
        headers=headers,
    )
    assert sr1.status_code == 201
    old_search = sr1.json()["search_id"]

    await client.post(
        "/api/v1/retainer/candidates/import",
        json={**_import_payload(tenant_id, candidate_id), "candidate_version": 2},
        headers=headers,
    )
    await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/approve",
        json={"outcome": "APPROVED", "scope_json": {}, "authority_record_id": str(uuid.uuid4())},
        headers=headers,
    )
    sr2 = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(2),
        headers=headers,
    )
    assert sr2.status_code == 201
    assert sr2.json()["search_id"] != old_search


@pytest.mark.asyncio
async def test_conflict_audit_trail(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=headers,
    )
    search_id = search_resp.json()["search_id"]

    detail = await client.get(
        f"/api/v1/retainer/conflicts/searches/{search_id}", headers=headers
    )
    for c in detail.json()["candidates"]:
        await client.post(
            f"/api/v1/retainer/conflict-candidates/{c['id']}/disposition",
            json={"disposition": "NO_CONFLICT"},
            headers=headers,
        )
    await client.post(
        f"/api/v1/retainer/conflicts/{search_id}/clear",
        json={"authority_record_id": str(uuid.uuid4()), "rationale": "All clear"},
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/retainer/conflicts/{search_id}/audit", headers=headers
    )
    assert resp.status_code == 200
    assert len(resp.json()["audit_entries"]) >= 1


@pytest.mark.asyncio
async def test_search_preserves_candidates(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=headers,
    )
    search_id = search_resp.json()["search_id"]
    detail = await client.get(
        f"/api/v1/retainer/conflicts/searches/{search_id}", headers=headers
    )
    assert detail.status_code == 200
    assert "candidates" in detail.json()


@pytest.mark.asyncio
async def test_clear_conflict_moves_to_package_preparation(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    search_resp = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=headers,
    )
    search_id = search_resp.json()["search_id"]

    detail = await client.get(
        f"/api/v1/retainer/conflicts/searches/{search_id}", headers=headers
    )
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

    resp = await client.get(
        f"/api/v1/retainer/candidates/{candidate_id}", headers=headers
    )
    assert resp.json()["state"] == "PACKAGE_PREPARATION"


@pytest.mark.asyncio
async def test_rerun_search_marks_old_stale(client):
    tenant_id, candidate_id, headers = await _setup_approved_candidate(client)
    sr1 = await client.post(
        f"/api/v1/retainer/candidates/{candidate_id}/conflicts/search",
        json=_search_payload(),
        headers=headers,
    )
    old_id = sr1.json()["search_id"]

    sr2 = await client.post(
        f"/api/v1/retainer/conflicts/{old_id}/rerun",
        json={
            "reason": "Party information updated",
            "candidate_version": 1,
            "parties": _search_payload()["parties"],
        },
        headers=headers,
    )
    assert sr2.status_code == 201
    new_id = sr2.json()["search_id"]
    assert new_id != old_id
    assert sr2.json()["supersedes_search_id"] == old_id
