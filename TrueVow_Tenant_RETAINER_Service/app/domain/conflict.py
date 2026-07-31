"""BP-02 Conflict Search and Attorney Clearance domain services.

All decisions are authority-gated and fail closed. Zero-match search results
do NOT constitute clearance — only an attributable attorney decision clears.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from retainer_contracts.authority import (
    ACTION_AUTHORITY,
    AuthorityAction,
    AuthorityClass,
)
from retainer_contracts.errors import ErrorCode
from retainer_contracts.events import EventType
from retainer_contracts.states import EngagementState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditEvent,
    AuthorityEvaluation,
    ConflictCandidate,
    ConflictEvidenceSnapshot,
    ConflictHold,
    ConflictReview,
    ConflictSearch,
    ConflictSearchParty,
    ConflictSearchSource,
    RetainerOutboxEvent,
    RetainerWorkflow,
)


def _hash_set(items: list[str]) -> str:
    raw = json.dumps(sorted(items), sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _match_parties(
    parties: list[dict], source_data: list[str], algorithm_version: str
) -> list[dict]:
    candidates: list[dict] = []
    party_set = [
        (p.get("legal_name", ""), p.get("normalized_name", ""), p.get("aliases", []))
        for p in parties
    ]
    for i, (legal, norm, aliases) in enumerate(party_set):
        legal_lower = legal.lower()
        norm_lower = (norm or "").lower()
        for j, (legal2, norm2, _aliases2) in enumerate(party_set):
            if i >= j:
                continue
            score = 0
            basis: dict[str, list[str]] = {}
            if legal_lower and legal_lower == legal2.lower():
                score += 100
                basis["exact_name_match"] = [legal2]
            if norm_lower and norm_lower == norm2.lower():
                score += 90
                basis.setdefault("normalized_name_match", []).append(norm2)
            for alias in aliases:
                alias_lower = alias.lower()
                if alias_lower == legal2.lower() or alias_lower == norm2.lower():
                    score += 80
                    basis.setdefault("alias_match", []).append(alias)
            if score > 0:
                candidates.append({
                    "matched_party_ref": f"party_{j}",
                    "match_basis_json": basis,
                    "rule_or_score": str(score),
                    "disposition": "UNREVIEWED",
                })
    return candidates


def _check_authority(action: AuthorityAction, role: str | None) -> bool:
    required = ACTION_AUTHORITY.get(action, AuthorityClass.PROHIBITED)
    if required == AuthorityClass.PROHIBITED:
        return False
    if required == AuthorityClass.SYS_ADMIN:
        return role == "admin" or role == "service"
    if required == AuthorityClass.ATTY_AUTH:
        return role == "attorney"
    if required == AuthorityClass.STAFF_AUTH:
        return role in ("staff", "attorney", "admin")
    if required == AuthorityClass.FIRM_POLICY:
        return role in ("staff", "attorney", "admin")
    return False


async def _record_conflict_audit(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    search_id: uuid.UUID,
    event_type: str,
    actor_id: str,
    actor_role: str | None,
    authority_class: str,
    action: str,
    result: str,
    details: dict | None = None,
) -> None:
    entry = AuditEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workflow_id=search_id,
        event_type=event_type,
        actor_id=actor_id,
        actor_role=actor_role,
        authority_class=authority_class,
        action=action,
        result=result,
        details=details or {},
    )
    db.add(entry)


async def _get_workflow_state(db: AsyncSession, workflow_id: uuid.UUID) -> str:
    wf_result = await db.execute(
        select(RetainerWorkflow).where(RetainerWorkflow.id == workflow_id)
    )
    workflow = wf_result.scalars().first()
    if workflow is None:
        raise ValueError("Workflow not found")
    return workflow.state


async def _update_workflow_state(db: AsyncSession, workflow_id: uuid.UUID, new_state: str) -> None:
    wf_result = await db.execute(
        select(RetainerWorkflow).where(RetainerWorkflow.id == workflow_id)
    )
    workflow = wf_result.scalars().first()
    if workflow is None:
        raise ValueError("Workflow not found")
    workflow.state = new_state
    workflow.version = workflow.version + 1


async def start_conflict_search(
    db: AsyncSession,
    *,
    candidate_id: uuid.UUID,
    tenant_id: uuid.UUID,
    actor_id: str,
    actor_role: str | None,
    parties: list[dict],
    candidate_version: int,
    scope_json: dict | None = None,
) -> uuid.UUID:
    if not _check_authority(AuthorityAction.CONFLICT_SEARCH, actor_role):
        raise ValueError(ErrorCode.RET_AUTHORITY_MISSING)

    result = await db.execute(
        select(RetainerWorkflow)
        .where(
            RetainerWorkflow.tenant_id == tenant_id,
            RetainerWorkflow.matter_candidate_id == candidate_id,
        )
        .order_by(RetainerWorkflow.candidate_version.desc())
        .with_for_update(),
    )
    workflow = result.scalars().first()
    if workflow is None:
        raise ValueError("Candidate not found")
    if workflow.candidate_version != candidate_version:
        raise ValueError(
            f"Version mismatch: expected v{workflow.candidate_version}, got v{candidate_version}"
        )
    if workflow.state not in (
        EngagementState.ATTORNEY_APPROVAL_RECORDED,
        EngagementState.CONFLICT_REVIEW_PENDING,
    ):
        raise ValueError(
            f"Conflict search requires ATTORNEY_APPROVAL_RECORDED or "
            f"CONFLICT_REVIEW_PENDING state, not {workflow.state}"
        )

    now = datetime.now(UTC)
    search_id = uuid.uuid4()
    algorithm_version = "deterministic-v1.0.0"
    search = ConflictSearch(
        id=search_id,
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        party_set_version=candidate_version,
        algorithm_version=algorithm_version,
        scope_json=scope_json or {},
        status="COMPLETED",
        started_at=now,
        completed_at=now,
    )
    db.add(search)

    party_hashes: list[str] = []
    source_covered: list[str] = []
    for p in parties:
        party = ConflictSearchParty(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            search_id=search_id,
            party_type=p.get("party_type", "UNKNOWN"),
            canonical_ref=p["canonical_ref"],
            legal_name=p["legal_name"],
            prior_names=p.get("prior_names", []),
            aliases=p.get("aliases", []),
            normalized_name=p.get("normalized_name"),
            date_of_birth=p.get("date_of_birth"),
            organization_identifiers=p.get("organization_identifiers", []),
            relationship_to_candidate=p.get("relationship_to_candidate"),
            source=p.get("source"),
            confidence=p.get("confidence"),
            candidate_version=candidate_version,
        )
        db.add(party)
        party_hashes.append(p["legal_name"])
        source_covered.append(f"{p.get('party_type', '')}:{p['legal_name']}")

    source = ConflictSearchSource(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        search_id=search_id,
        source_type="internal_party_records",
        source_identifier="retainer.party_set",
        algorithm_version=algorithm_version,
        coverage_data={
            "parties": len(parties),
            "types": list({p.get("party_type", "") for p in parties}),
        },
    )
    db.add(source)

    matches = _match_parties(parties, source_covered, algorithm_version)
    for m in matches:
        candidate = ConflictCandidate(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            search_id=search_id,
            matched_party_ref=m["matched_party_ref"],
            match_basis_json=m["match_basis_json"],
            rule_or_score=m["rule_or_score"],
            disposition=m["disposition"],
        )
        db.add(candidate)

    snapshot = ConflictEvidenceSnapshot(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        search_id=search_id,
        snapshot_type="search_inputs",
        party_set_hash=_hash_set([p["legal_name"] for p in parties]),
        source_set_hash=_hash_set(source_covered),
        candidate_version=candidate_version,
        snapshot_data={"party_count": len(parties), "match_count": len(matches)},
    )
    db.add(snapshot)

    if workflow.state == EngagementState.ATTORNEY_APPROVAL_RECORDED:
        workflow.state = EngagementState.CONFLICT_REVIEW_PENDING
        workflow.version = workflow.version + 1

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow.id,
        event_type=EventType.CONFLICT_SEARCH_STARTED,
        schema_version="1.0.1",
        payload_json={
            "search_id": str(search_id),
            "workflow_id": str(workflow.id),
            "party_count": len(parties),
            "match_count": len(matches),
            "algorithm_version": algorithm_version,
        },
    )
    db.add(outbox)

    return search_id


async def disposition_candidate(
    db: AsyncSession,
    *,
    conflict_candidate_id: uuid.UUID,
    tenant_id: uuid.UUID,
    actor_id: str,
    actor_role: str | None,
    disposition: str,
    rationale: str | None = None,
) -> uuid.UUID:
    cand_result = await db.execute(
        select(ConflictCandidate).where(
            ConflictCandidate.id == conflict_candidate_id,
            ConflictCandidate.tenant_id == tenant_id,
        )
    )
    candidate = cand_result.scalars().first()
    if candidate is None:
        raise ValueError("Conflict candidate not found")
    candidate.disposition = disposition

    search_result = await db.execute(
        select(ConflictSearch).where(ConflictSearch.id == candidate.search_id)
    )
    search = search_result.scalars().first()
    if search is None:
        raise ValueError("Parent search not found")

    authority_class = (
        AuthorityClass.ATTY_AUTH.value
        if disposition in ("MATERIAL_CONFLICT", "NO_CONFLICT")
        else AuthorityClass.FIRM_POLICY.value
    )

    await _record_conflict_audit(
        db,
        tenant_id=tenant_id,
        search_id=candidate.search_id,
        event_type="conflict.candidate_dispositioned",
        actor_id=actor_id,
        actor_role=actor_role,
        authority_class=authority_class,
        action="disposition_candidate",
        result=disposition,
        details={"rationale": rationale} if rationale else {},
    )

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=candidate.search_id,
        event_type=EventType.CONFLICT_CANDIDATE_DETECTED,
        schema_version="1.0.1",
        payload_json={
            "candidate_id": str(conflict_candidate_id),
            "disposition": disposition,
            "search_id": str(candidate.search_id),
        },
    )
    db.add(outbox)

    return conflict_candidate_id


async def apply_conflict_hold(
    db: AsyncSession,
    *,
    search_id: uuid.UUID,
    tenant_id: uuid.UUID,
    attorney_actor_id: str,
    authority_record_id: uuid.UUID,
    reason: str,
    actor_role: str | None = None,
    affected_candidate_id: uuid.UUID | None = None,
    supporting_evidence: dict | None = None,
    required_followup: str | None = None,
    policy_snapshot_id: uuid.UUID | None = None,
) -> uuid.UUID:
    authority = AuthorityClass.ATTY_AUTH
    if not _check_authority(AuthorityAction.CONFLICT_CLEAR_OR_HOLD, actor_role):
        raise ValueError(ErrorCode.RET_AUTHORITY_MISSING)

    search_result = await db.execute(
        select(ConflictSearch).where(
            ConflictSearch.id == search_id,
            ConflictSearch.tenant_id == tenant_id,
        ).with_for_update(),
    )
    search = search_result.scalars().first()
    if search is None:
        raise ValueError("Search not found")

    current_state = await _get_workflow_state(db, search.workflow_id)
    if current_state not in (
        EngagementState.CONFLICT_REVIEW_PENDING,
        EngagementState.PACKAGE_PREPARATION,
    ):
        raise ValueError(f"Cannot apply hold from state {current_state}")

    hold_id = uuid.uuid4()
    hold = ConflictHold(
        id=hold_id,
        tenant_id=tenant_id,
        search_id=search_id,
        attorney_actor_id=attorney_actor_id,
        authority_record_id=authority_record_id,
        reason=reason,
        affected_candidate_id=affected_candidate_id,
        supporting_evidence=supporting_evidence or {},
        required_followup=required_followup,
        review_owner=attorney_actor_id,
        policy_snapshot_id=policy_snapshot_id,
    )
    db.add(hold)

    await _update_workflow_state(db, search.workflow_id, EngagementState.CONFLICT_HOLD)

    auth_eval = AuthorityEvaluation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workflow_id=search.workflow_id,
        action="apply_conflict_hold",
        actor_id=attorney_actor_id,
        authority_class=authority.value,
        result="HELD",
        policy_snapshot_id=policy_snapshot_id,
    )
    db.add(auth_eval)

    await _record_conflict_audit(
        db,
        tenant_id=tenant_id,
        search_id=search_id,
        event_type="conflict.hold_applied",
        actor_id=attorney_actor_id,
        actor_role=actor_role,
        authority_class=authority.value,
        action="apply_conflict_hold",
        result="HELD",
    )

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=search.workflow_id,
        event_type=EventType.CONFLICT_HOLD_APPLIED,
        schema_version="1.0.1",
        payload_json={
            "search_id": str(search_id),
            "hold_id": str(hold_id),
            "reason": reason,
            "attorney_actor_id": attorney_actor_id,
        },
    )
    db.add(outbox)

    return hold_id


async def release_conflict_hold(
    db: AsyncSession,
    *,
    search_id: uuid.UUID,
    tenant_id: uuid.UUID,
    actor_id: str,
    authority_record_id: uuid.UUID,
    reason: str,
    actor_role: str | None = None,
) -> uuid.UUID:
    authority = AuthorityClass.ATTY_AUTH
    if not _check_authority(AuthorityAction.CONFLICT_CLEAR_OR_HOLD, actor_role):
        raise ValueError(ErrorCode.RET_AUTHORITY_MISSING)

    result = await db.execute(
        select(ConflictHold)
        .where(
            ConflictHold.search_id == search_id,
            ConflictHold.tenant_id == tenant_id,
            ConflictHold.released_at.is_(None),
        )
        .order_by(ConflictHold.held_at.desc()),
    )
    hold = result.scalars().first()
    if hold is None:
        raise ValueError("No active hold found for this search")

    hold.released_at = datetime.now(UTC)

    search_result = await db.execute(
        select(ConflictSearch).where(ConflictSearch.id == search_id)
    )
    s = search_result.scalars().first()
    if s is None:
        raise ValueError("Search not found")
    await _update_workflow_state(db, s.workflow_id, EngagementState.CONFLICT_REVIEW_PENDING)

    auth_eval = AuthorityEvaluation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workflow_id=s.workflow_id,
        action="release_conflict_hold",
        actor_id=actor_id,
        authority_class=authority.value,
        result="RELEASED",
    )
    db.add(auth_eval)

    await _record_conflict_audit(
        db,
        tenant_id=tenant_id,
        search_id=search_id,
        event_type="hold_released",
        actor_id=actor_id,
        actor_role=actor_role,
        authority_class=authority.value,
        action="release_conflict_hold",
        result="RELEASED",
        details={"reason": reason},
    )

    return hold.id


async def clear_conflict_review(
    db: AsyncSession,
    *,
    search_id: uuid.UUID,
    tenant_id: uuid.UUID,
    attorney_actor_id: str,
    authority_record_id: uuid.UUID,
    actor_role: str | None = None,
    rationale: str | None = None,
    policy_snapshot_id: uuid.UUID | None = None,
) -> uuid.UUID:
    authority = AuthorityClass.ATTY_AUTH
    if not _check_authority(AuthorityAction.CONFLICT_CLEAR_OR_HOLD, actor_role):
        raise ValueError(ErrorCode.RET_AUTHORITY_MISSING)

    search_result = await db.execute(
        select(ConflictSearch).where(
            ConflictSearch.id == search_id,
            ConflictSearch.tenant_id == tenant_id,
        ).with_for_update(),
    )
    search = search_result.scalars().first()
    if search is None:
        raise ValueError("Search not found")

    current_state = await _get_workflow_state(db, search.workflow_id)
    valid_states = (EngagementState.CONFLICT_REVIEW_PENDING, EngagementState.CONFLICT_HOLD)
    if current_state not in valid_states:
        raise ValueError(f"Cannot clear from state {current_state}")

    unresolved = (
        await db.execute(
            select(ConflictCandidate).where(
                ConflictCandidate.search_id == search_id,
                ConflictCandidate.tenant_id == tenant_id,
                ConflictCandidate.disposition == "UNREVIEWED",
            ).with_for_update(),
        )
    ).scalars().first()
    if unresolved is not None:
        raise ValueError("Unresolved conflict candidates remain — cannot clear")

    now = datetime.now(UTC)
    review_id = uuid.uuid4()
    review = ConflictReview(
        id=review_id,
        tenant_id=tenant_id,
        search_id=search_id,
        outcome="CLEARED",
        attorney_actor_id=attorney_actor_id,
        authority_record_id=authority_record_id,
        rationale_ref=rationale,
        decided_at=now,
    )
    db.add(review)

    await _update_workflow_state(db, search.workflow_id, EngagementState.PACKAGE_PREPARATION)

    wf_result = await db.execute(
        select(RetainerWorkflow).where(RetainerWorkflow.id == search.workflow_id)
    )
    workflow = wf_result.scalars().first()
    if workflow:
        workflow.conflict_review_id = review_id

    auth_eval = AuthorityEvaluation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workflow_id=search.workflow_id,
        action="clear_conflict_review",
        actor_id=attorney_actor_id,
        authority_class=authority.value,
        result="CLEARED",
        policy_snapshot_id=policy_snapshot_id,
    )
    db.add(auth_eval)

    await _record_conflict_audit(
        db,
        tenant_id=tenant_id,
        search_id=search_id,
        event_type="conflict.cleared_by_attorney",
        actor_id=attorney_actor_id,
        actor_role=actor_role,
        authority_class=authority.value,
        action="clear_conflict_review",
        result="CLEARED",
        details={"rationale": rationale} if rationale else {},
    )

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=search.workflow_id,
        event_type=EventType.CONFLICT_CLEARED_BY_ATTORNEY,
        schema_version="1.0.1",
        payload_json={
            "search_id": str(search_id),
            "review_id": str(review_id),
            "outcome": "CLEARED",
            "attorney_actor_id": attorney_actor_id,
        },
    )
    db.add(outbox)

    return review_id


async def rerun_conflict_search(
    db: AsyncSession,
    *,
    search_id: uuid.UUID,
    tenant_id: uuid.UUID,
    actor_id: str,
    actor_role: str | None,
    reason: str,
    parties: list[dict],
    candidate_version: int,
) -> uuid.UUID:
    if not _check_authority(AuthorityAction.CONFLICT_SEARCH, actor_role):
        raise ValueError(ErrorCode.RET_AUTHORITY_MISSING)

    existing_result = await db.execute(
        select(ConflictSearch).where(
            ConflictSearch.id == search_id,
            ConflictSearch.tenant_id == tenant_id,
        ).with_for_update(),
    )
    existing = existing_result.scalars().first()
    if existing is None:
        raise ValueError("Search not found")

    existing.status = "STALE"
    db.add(existing)

    new_search_id = uuid.uuid4()
    now = datetime.now(UTC)
    algorithm_version = existing.algorithm_version
    new_search = ConflictSearch(
        id=new_search_id,
        tenant_id=tenant_id,
        workflow_id=existing.workflow_id,
        party_set_version=candidate_version,
        algorithm_version=algorithm_version,
        scope_json=existing.scope_json,
        status="COMPLETED",
        started_at=now,
        completed_at=now,
    )
    db.add(new_search)

    for p in parties:
        party = ConflictSearchParty(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            search_id=new_search_id,
            party_type=p.get("party_type", "UNKNOWN"),
            canonical_ref=p["canonical_ref"],
            legal_name=p["legal_name"],
            prior_names=p.get("prior_names", []),
            aliases=p.get("aliases", []),
            normalized_name=p.get("normalized_name"),
            date_of_birth=p.get("date_of_birth"),
            organization_identifiers=p.get("organization_identifiers", []),
            relationship_to_candidate=p.get("relationship_to_candidate"),
            source=p.get("source"),
            confidence=p.get("confidence"),
            candidate_version=candidate_version,
        )
        db.add(party)

    source_covered = [f"{p.get('party_type', '')}:{p['legal_name']}" for p in parties]
    matches = _match_parties(parties, source_covered, existing.algorithm_version)
    for m in matches:
        candidate = ConflictCandidate(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            search_id=new_search_id,
            matched_party_ref=m["matched_party_ref"],
            match_basis_json=m["match_basis_json"],
            rule_or_score=m["rule_or_score"],
            disposition=m["disposition"],
        )
        db.add(candidate)

    snapshot = ConflictEvidenceSnapshot(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        search_id=new_search_id,
        snapshot_type="search_inputs",
        party_set_hash=_hash_set([p["legal_name"] for p in parties]),
        source_set_hash=_hash_set(source_covered),
        candidate_version=candidate_version,
        snapshot_data={
            "party_count": len(parties),
            "match_count": len(matches),
            "rerun_reason": reason,
        },
    )
    db.add(snapshot)

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=existing.workflow_id,
        event_type=EventType.CONFLICT_SEARCH_STARTED,
        schema_version="1.0.1",
        payload_json={
            "search_id": str(new_search_id),
            "supersedes_search_id": str(search_id),
            "party_count": len(parties),
            "match_count": len(matches),
            "reason": reason,
        },
    )
    db.add(outbox)

    return new_search_id
