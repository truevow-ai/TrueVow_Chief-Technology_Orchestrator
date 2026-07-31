"""BP-02 Conflict Search and Attorney Clearance API routes."""

# ruff: noqa: B008

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthContext, get_current_context
from app.core.database import get_db
from app.domain.conflict import (
    apply_conflict_hold,
    clear_conflict_review,
    disposition_candidate,
    release_conflict_hold,
    rerun_conflict_search,
    start_conflict_search,
)
from app.models import (
    AuditEvent,
    ConflictCandidate,
    ConflictHold,
    ConflictReview,
    ConflictSearch,
    ConflictSearchParty,
)
from app.schemas import (
    ApplyHoldRequest,
    ApplyHoldResponse,
    ClearConflictRequest,
    ClearConflictResponse,
    ConflictAuditEntry,
    ConflictAuditResponse,
    ConflictCandidateResponse,
    ConflictListResponse,
    ConflictSearchDetailResponse,
    ConflictSearchPartyResponse,
    DispositionRequest,
    DispositionResponse,
    ReleaseHoldRequest,
    ReleaseHoldResponse,
    RerunSearchRequest,
    RerunSearchResponse,
    StartConflictSearchRequest,
    StartConflictSearchResponse,
)

router = APIRouter(tags=["conflicts"])


@router.post(
    "/candidates/{candidate_id}/conflicts/search",
    status_code=201,
    response_model=StartConflictSearchResponse,
)
async def start_search_endpoint(
    candidate_id: uuid.UUID,
    payload: StartConflictSearchRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        parties_dicts = [p.model_dump() for p in payload.parties]
        search_id = await start_conflict_search(
            db,
            candidate_id=candidate_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            actor_id=ctx.user_id,
            actor_role=ctx.role,
            parties=parties_dicts,
            candidate_version=payload.candidate_version,
            scope_json=payload.scope_json,
        )
        await db.commit()
        search = await db.get(ConflictSearch, search_id)
        party_count_result = await db.execute(
            select(ConflictSearchParty).where(
                ConflictSearchParty.search_id == search_id
            )
        )
        party_count = len(party_count_result.scalars().all())
        return StartConflictSearchResponse(
            search_id=search_id,
            status=search.status if search else "COMPLETED",
            started_at=search.started_at if search else None,
            party_count=party_count,
        )
    except ValueError as e:
        await db.rollback()
        msg = str(e)
        if "AUTHORITY_MISSING" in msg or "authority" in msg.lower():
            raise HTTPException(status_code=403, detail=msg) from None
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from None
        raise HTTPException(status_code=409, detail=msg) from None


@router.get(
    "/candidates/{candidate_id}/conflicts",
    response_model=ConflictListResponse,
)
async def list_candidate_searches(
    candidate_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    firm_uuid = uuid.UUID(ctx.firm_id)
    from app.models import RetainerWorkflow

    candidate_workflow_result = await db.execute(
        select(RetainerWorkflow).where(
            RetainerWorkflow.tenant_id == firm_uuid,
            RetainerWorkflow.matter_candidate_id == candidate_id,
        ).order_by(RetainerWorkflow.candidate_version.desc())
    )
    candidate_workflow = candidate_workflow_result.scalars().first()
    if candidate_workflow is None:
        return ConflictListResponse(searches=[])

    searches_result = await db.execute(
        select(ConflictSearch)
        .where(
            ConflictSearch.tenant_id == firm_uuid,
            ConflictSearch.workflow_id == candidate_workflow.id,
        )
        .order_by(ConflictSearch.started_at.desc())
    )
    searches = searches_result.scalars().all()

    detail_list = []
    for s in searches:
        parties_result = await db.execute(
            select(ConflictSearchParty).where(
                ConflictSearchParty.search_id == s.id
            )
        )
        parties = parties_result.scalars().all()
        candidates_result = await db.execute(
            select(ConflictCandidate).where(
                ConflictCandidate.search_id == s.id
            )
        )
        candidates = candidates_result.scalars().all()
        hold_result = await db.execute(
            select(ConflictHold)
            .where(
                ConflictHold.search_id == s.id,
                ConflictHold.released_at.is_(None),
            )
        )
        hold = hold_result.scalars().first()
        review_result = await db.execute(
            select(ConflictReview).where(
                ConflictReview.search_id == s.id
            )
        )
        review = review_result.scalars().first()

        detail_list.append(
            ConflictSearchDetailResponse(
                search_id=s.id,
                workflow_id=s.workflow_id,
                tenant_id=s.tenant_id,
                status=s.status,
                party_set_version=s.party_set_version,
                algorithm_version=s.algorithm_version,
                started_at=s.started_at,
                completed_at=s.completed_at,
                parties=[
                    ConflictSearchPartyResponse(
                        id=p.id,
                        party_type=p.party_type,
                        canonical_ref=p.canonical_ref,
                        legal_name=p.legal_name,
                        prior_names=p.prior_names,
                        aliases=p.aliases,
                        normalized_name=p.normalized_name,
                        relationship_to_candidate=p.relationship_to_candidate,
                    )
                    for p in parties
                ],
                candidates=[
                    ConflictCandidateResponse(
                        id=c.id,
                        matched_party_ref=c.matched_party_ref,
                        match_basis_json=c.match_basis_json,
                        rule_or_score=c.rule_or_score,
                        disposition=c.disposition,
                    )
                    for c in candidates
                ],
                current_hold={
                    "hold_id": str(hold.id),
                    "reason": hold.reason,
                    "held_at": str(hold.held_at),
                } if hold else None,
                review_outcome=review.outcome if review else None,
            )
        )
    return ConflictListResponse(searches=detail_list)


@router.get(
    "/conflicts/searches/{search_id}",
    response_model=ConflictSearchDetailResponse,
)
async def get_search_detail(
    search_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    s = await db.get(ConflictSearch, search_id)
    if s is None or str(s.tenant_id) != ctx.firm_id:
        raise HTTPException(status_code=404, detail="Search not found")

    parties_result = await db.execute(
        select(ConflictSearchParty).where(
            ConflictSearchParty.search_id == search_id
        )
    )
    parties = parties_result.scalars().all()
    candidates_result = await db.execute(
        select(ConflictCandidate).where(
            ConflictCandidate.search_id == search_id
        )
    )
    candidates = candidates_result.scalars().all()
    hold_result = await db.execute(
        select(ConflictHold)
        .where(
            ConflictHold.search_id == search_id,
            ConflictHold.released_at.is_(None),
        )
    )
    hold = hold_result.scalars().first()
    review_result = await db.execute(
        select(ConflictReview).where(
            ConflictReview.search_id == search_id
        )
    )
    review = review_result.scalars().first()

    return ConflictSearchDetailResponse(
        search_id=s.id,
        workflow_id=s.workflow_id,
        tenant_id=s.tenant_id,
        status=s.status,
        party_set_version=s.party_set_version,
        algorithm_version=s.algorithm_version,
        started_at=s.started_at,
        completed_at=s.completed_at,
        parties=[ConflictSearchPartyResponse(**p.__dict__) for p in parties],
        candidates=[ConflictCandidateResponse(**c.__dict__) for c in candidates],
        current_hold={
            "hold_id": str(hold.id),
            "reason": hold.reason,
            "held_at": str(hold.held_at),
        } if hold else None,
        review_outcome=review.outcome if review else None,
    )


@router.post(
    "/conflicts/{search_id}/rerun",
    status_code=201,
    response_model=RerunSearchResponse,
)
async def rerun_search_endpoint(
    search_id: uuid.UUID,
    payload: RerunSearchRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        parties_dicts = (
            [p.model_dump() for p in payload.parties] if payload.parties else []
        )
        new_id = await rerun_conflict_search(
            db,
            search_id=search_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            actor_id=ctx.user_id,
            actor_role=ctx.role,
            reason=payload.reason,
            parties=parties_dicts,
            candidate_version=payload.candidate_version,
        )
        await db.commit()
        search = await db.get(ConflictSearch, new_id)
        return RerunSearchResponse(
            search_id=new_id,
            status=search.status if search else "COMPLETED",
            started_at=search.started_at if search else None,
            supersedes_search_id=search_id,
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post(
    "/conflict-candidates/{conflict_candidate_id}/disposition",
    status_code=200,
    response_model=DispositionResponse,
)
async def disposition_candidate_endpoint(
    conflict_candidate_id: uuid.UUID,
    payload: DispositionRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        disp_id = await disposition_candidate(
            db,
            conflict_candidate_id=conflict_candidate_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            actor_id=ctx.user_id,
            actor_role=ctx.role,
            disposition=payload.disposition,
            rationale=payload.rationale,
        )
        await db.commit()
        return DispositionResponse(
            candidate_id=disp_id, disposition=payload.disposition
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.post(
    "/conflicts/{search_id}/apply-hold",
    status_code=201,
    response_model=ApplyHoldResponse,
)
async def apply_hold_endpoint(
    search_id: uuid.UUID,
    payload: ApplyHoldRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        hold_id = await apply_conflict_hold(
            db,
            search_id=search_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            attorney_actor_id=ctx.user_id,
            authority_record_id=payload.authority_record_id,
            reason=payload.reason,
            actor_role=ctx.role,
            affected_candidate_id=payload.affected_candidate_id,
            supporting_evidence=payload.supporting_evidence,
            required_followup=payload.required_followup,
            policy_snapshot_id=payload.policy_snapshot_id,
        )
        await db.commit()
        hold = await db.get(ConflictHold, hold_id)
        return ApplyHoldResponse(
            hold_id=hold_id, held_at=hold.held_at if hold else None
        )
    except ValueError as e:
        await db.rollback()
        msg = str(e)
        if "AUTHORITY_MISSING" in msg:
            raise HTTPException(status_code=403, detail=msg) from None
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from None
        raise HTTPException(status_code=409, detail=msg) from None


@router.post(
    "/conflicts/{search_id}/release-hold",
    status_code=200,
    response_model=ReleaseHoldResponse,
)
async def release_hold_endpoint(
    search_id: uuid.UUID,
    payload: ReleaseHoldRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        hold_id = await release_conflict_hold(
            db,
            search_id=search_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            actor_id=ctx.user_id,
            authority_record_id=payload.authority_record_id,
            reason=payload.reason,
            actor_role=ctx.role,
        )
        await db.commit()
        hold = await db.get(ConflictHold, hold_id)
        return ReleaseHoldResponse(
            hold_id=hold_id,
            released_at=hold.released_at if hold else None,
        )
    except ValueError as e:
        await db.rollback()
        msg = str(e)
        if "AUTHORITY_MISSING" in msg:
            raise HTTPException(status_code=403, detail=msg) from None
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from None
        raise HTTPException(status_code=409, detail=msg) from None


@router.post(
    "/conflicts/{search_id}/clear",
    status_code=201,
    response_model=ClearConflictResponse,
)
async def clear_conflict_endpoint(
    search_id: uuid.UUID,
    payload: ClearConflictRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        review_id = await clear_conflict_review(
            db,
            search_id=search_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            attorney_actor_id=ctx.user_id,
            authority_record_id=payload.authority_record_id,
            actor_role=ctx.role,
            rationale=payload.rationale,
            policy_snapshot_id=payload.policy_snapshot_id,
        )
        await db.commit()
        review = await db.get(ConflictReview, review_id)
        return ClearConflictResponse(
            review_id=review_id,
            outcome=review.outcome if review else "CLEARED",
            decided_at=review.decided_at if review else None,
        )
    except ValueError as e:
        await db.rollback()
        msg = str(e)
        if "AUTHORITY_MISSING" in msg:
            raise HTTPException(status_code=403, detail=msg) from None
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from None
        if "Unresolved" in msg:
            raise HTTPException(status_code=409, detail=msg) from None
        raise HTTPException(status_code=409, detail=msg) from None


@router.get(
    "/conflicts/{search_id}/audit",
    response_model=ConflictAuditResponse,
)
async def get_conflict_audit(
    search_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    search = await db.get(ConflictSearch, search_id)
    if search is None or str(search.tenant_id) != ctx.firm_id:
        raise HTTPException(status_code=404, detail="Search not found")

    audit_result = await db.execute(
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == uuid.UUID(ctx.firm_id),
            AuditEvent.workflow_id == search_id,
        )
        .order_by(AuditEvent.occurred_at.asc())
    )
    entries = [
        ConflictAuditEntry(
            event_id=e.id,
            event_type=e.event_type,
            actor_id=e.actor_id,
            actor_role=e.actor_role,
            authority_class=e.authority_class,
            action=e.action,
            result=e.result,
            occurred_at=e.occurred_at,
        )
        for e in audit_result.scalars().all()
    ]
    return ConflictAuditResponse(search_id=search_id, audit_entries=entries)
