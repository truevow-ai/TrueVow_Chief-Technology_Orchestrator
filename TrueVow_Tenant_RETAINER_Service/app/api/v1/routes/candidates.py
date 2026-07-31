"""BP-01 Candidate Review and Representation Decision API routes."""

# ruff: noqa: B008 (Depends() in function defaults is standard FastAPI pattern)

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from retainer_contracts.states import EngagementState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthContext, get_current_context, get_webhook_context
from app.core.database import get_db
from app.domain.candidate import (
    approve_representation,
    assign_responsible_attorney,
    decline_representation,
    defer_representation,
    request_missing_information,
    start_candidate_review,
)
from app.models import (
    AuditEvent,
    CandidateReview,
    RepresentationDecision,
    RetainerOutboxEvent,
    RetainerWorkflow,
)
from app.schemas import (
    AssignAttorneyRequest,
    AssignAttorneyResponse,
    AuditEntry,
    AuditResponse,
    CandidateDetailResponse,
    CandidateHandoffRequest,
    CandidateImportResponse,
    CandidateListResponse,
    CandidateSummary,
    RepresentationDecisionRequest,
    RepresentationDecisionResponse,
    RequestInformationRequest,
    RequestInformationResponse,
    ReviewQueueResponse,
    StartReviewResponse,
    TimelineEvent,
    WorkflowDetail,
    WorkflowSummary,
    WorkflowTimelineResponse,
)

router = APIRouter(tags=["candidates"])


@router.post("/candidates/import", status_code=202, response_model=CandidateImportResponse)
async def import_candidate_endpoint(
    payload: CandidateHandoffRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_current_context),
):
    from app.domain.candidate import import_candidate

    try:
        workflow_id, _ = await import_candidate(
            db,
            tenant_id=payload.tenant_id,
            matter_candidate_id=payload.matter_candidate_id,
            candidate_version=payload.candidate_version,
            source_event_id=payload.source_event_ids[0],
            submitted_by_actor_id=payload.submitted_by_actor_id,
            source_event_ids=payload.source_event_ids,
        )
        await db.commit()
        return CandidateImportResponse(
            workflow_id=workflow_id,
            candidate_id=payload.matter_candidate_id,
            state=EngagementState.NOT_STARTED,
            candidate_version=payload.candidate_version,
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post(
    "/webhooks/candidate-submitted",
    status_code=202,
    response_model=CandidateImportResponse,
    summary="INTAKE → RETAINER webhook for candidate.submitted_for_representation_review",
)
async def candidate_submitted_webhook(
    payload: CandidateHandoffRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_webhook_context),
):
    """Accept a candidate submission from INTAKE via service-to-service webhook.

    Authenticated via API key (X-API-Key or Bearer token).
    Tenant context from X-Tenant-Id header.
    """
    from app.domain.candidate import import_candidate

    try:
        workflow_id, _ = await import_candidate(
            db,
            tenant_id=payload.tenant_id,
            matter_candidate_id=payload.matter_candidate_id,
            candidate_version=payload.candidate_version,
            source_event_id=payload.source_event_ids[0],
            submitted_by_actor_id=payload.submitted_by_actor_id,
            source_event_ids=payload.source_event_ids,
        )
        await db.commit()
        return CandidateImportResponse(
            workflow_id=workflow_id,
            candidate_id=payload.matter_candidate_id,
            state=EngagementState.NOT_STARTED,
            candidate_version=payload.candidate_version,
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.get("/candidates", response_model=CandidateListResponse)
async def list_candidates(
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    firm_uuid = uuid.UUID(ctx.firm_id)
    result = await db.execute(
        select(RetainerWorkflow)
        .where(RetainerWorkflow.tenant_id == firm_uuid)
        .order_by(RetainerWorkflow.created_at.desc())
    )
    workflows = result.scalars().all()
    summaries = []
    for w in workflows:
        review = (
            await db.execute(
                select(CandidateReview).where(
                    CandidateReview.tenant_id == firm_uuid,
                    CandidateReview.workflow_id == w.id,
                )
            )
        ).scalar_one_or_none()
        summaries.append(
            CandidateSummary(
                candidate_id=w.matter_candidate_id,
                workflow_id=w.id,
                state=EngagementState(w.state),
                candidate_version=w.candidate_version,
                review_state=review.review_state if review else "UNREVIEWED",
                responsible_attorney=review.responsible_attorney_actor_id if review else None,
                created_at=w.created_at,
                updated_at=w.updated_at,
            )
        )
    return CandidateListResponse(candidates=summaries)


@router.get("/candidates/{candidate_id}", response_model=CandidateDetailResponse)
async def get_candidate(
    candidate_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    firm_uuid = uuid.UUID(ctx.firm_id)
    result = await db.execute(
        select(RetainerWorkflow)
        .where(
            RetainerWorkflow.tenant_id == firm_uuid,
            RetainerWorkflow.matter_candidate_id == candidate_id,
        )
        .order_by(RetainerWorkflow.candidate_version.desc())
    )
    workflow = result.scalars().first()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    review = (
        await db.execute(
            select(CandidateReview).where(
                CandidateReview.tenant_id == firm_uuid,
                CandidateReview.workflow_id == workflow.id,
            )
        )
    ).scalar_one_or_none()

    decision = None
    if workflow.representation_decision_id:
        decision = await db.get(RepresentationDecision, workflow.representation_decision_id)

    return CandidateDetailResponse(
        candidate_id=workflow.matter_candidate_id,
        workflow_id=workflow.id,
        tenant_id=workflow.tenant_id,
        state=EngagementState(workflow.state),
        candidate_version=workflow.candidate_version,
        version=workflow.version,
        review_state=review.review_state if review else None,
        prepared_by_actor_id=review.prepared_by_actor_id if review else None,
        responsible_attorney_actor_id=review.responsible_attorney_actor_id if review else None,
        representation_decision_id=workflow.representation_decision_id,
        decision_outcome=decision.outcome if decision else None,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


@router.post(
    "/candidates/{candidate_id}/start-review",
    status_code=200,
    response_model=StartReviewResponse,
)
async def start_review_endpoint(
    candidate_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        review_id, state = await start_candidate_review(
            db,
            candidate_id=candidate_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            actor_id=ctx.user_id,
            actor_role=ctx.role,
        )
        await db.commit()
        return StartReviewResponse(review_id=review_id, review_state=state)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(e)) from None


@router.post(
    "/candidates/{candidate_id}/assign-attorney",
    status_code=200,
    response_model=AssignAttorneyResponse,
)
async def assign_attorney_endpoint(
    candidate_id: uuid.UUID,
    payload: AssignAttorneyRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        review_id = await assign_responsible_attorney(
            db,
            candidate_id=candidate_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            attorney_actor_id=payload.attorney_actor_id,
            actor_id=ctx.user_id,
            actor_role=ctx.role,
        )
        await db.commit()
        return AssignAttorneyResponse(
            review_id=review_id,
            responsible_attorney_actor_id=payload.attorney_actor_id,
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(e)) from None


@router.post(
    "/candidates/{candidate_id}/request-information",
    status_code=200,
    response_model=RequestInformationResponse,
)
async def request_information_endpoint(
    candidate_id: uuid.UUID,
    payload: RequestInformationRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        request_id = await request_missing_information(
            db,
            candidate_id=candidate_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            actor_id=ctx.user_id,
            actor_role=ctx.role,
            reason=payload.reason,
            fields_required=payload.fields_required,
        )
        await db.commit()
        return RequestInformationResponse(request_id=request_id, state="OPEN")
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(e)) from None


@router.post(
    "/candidates/{candidate_id}/approve",
    status_code=201,
    response_model=RepresentationDecisionResponse,
)
async def approve_representation_endpoint(
    candidate_id: uuid.UUID,
    payload: RepresentationDecisionRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        decision_id = await approve_representation(
            db,
            candidate_id=candidate_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            attorney_actor_id=ctx.user_id,
            authority_record_id=payload.authority_record_id,
            scope_json=payload.scope_json,
            policy_snapshot_id=payload.policy_snapshot_id,
            actor_role=ctx.role,
        )
        await db.commit()
        decision = await db.get(RepresentationDecision, decision_id)
        return RepresentationDecisionResponse(
            decision_id=decision_id,
            outcome=decision.outcome,
            decided_at=decision.decided_at,
        )
    except ValueError as e:
        await db.rollback()
        msg = str(e)
        if "AUTHORITY_MISSING" in msg or "authority" in msg.lower():
            raise HTTPException(status_code=403, detail=msg) from None
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from None
        raise HTTPException(status_code=409, detail=msg) from None


@router.post(
    "/candidates/{candidate_id}/decline",
    status_code=201,
    response_model=RepresentationDecisionResponse,
)
async def decline_representation_endpoint(
    candidate_id: uuid.UUID,
    payload: RepresentationDecisionRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        decision_id = await decline_representation(
            db,
            candidate_id=candidate_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            attorney_actor_id=ctx.user_id,
            authority_record_id=payload.authority_record_id,
            actor_role=ctx.role,
        )
        await db.commit()
        decision = await db.get(RepresentationDecision, decision_id)
        return RepresentationDecisionResponse(
            decision_id=decision_id,
            outcome=decision.outcome,
            decided_at=decision.decided_at,
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post(
    "/candidates/{candidate_id}/defer",
    status_code=201,
    response_model=RepresentationDecisionResponse,
)
async def defer_representation_endpoint(
    candidate_id: uuid.UUID,
    payload: RepresentationDecisionRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        decision_id = await defer_representation(
            db,
            candidate_id=candidate_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            attorney_actor_id=ctx.user_id,
            authority_record_id=payload.authority_record_id,
            scope_json=payload.scope_json,
            policy_snapshot_id=payload.policy_snapshot_id,
            actor_role=ctx.role,
        )
        await db.commit()
        decision = await db.get(RepresentationDecision, decision_id)
        return RepresentationDecisionResponse(
            decision_id=decision_id,
            outcome=decision.outcome,
            decided_at=decision.decided_at,
        )
    except ValueError as e:
        await db.rollback()
        msg = str(e)
        if "AUTHORITY_MISSING" in msg or "authority" in msg.lower():
            raise HTTPException(status_code=403, detail=msg) from None
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from None
        raise HTTPException(status_code=409, detail=msg) from None


@router.get("/candidates/{candidate_id}/audit", response_model=AuditResponse)
async def get_candidate_audit(
    candidate_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    firm_uuid = uuid.UUID(ctx.firm_id)
    result = await db.execute(
        select(RetainerWorkflow)
        .where(
            RetainerWorkflow.tenant_id == firm_uuid,
            RetainerWorkflow.matter_candidate_id == candidate_id,
        )
        .order_by(RetainerWorkflow.candidate_version.desc())
    )
    workflow = result.scalars().first()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    audit_result = await db.execute(
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == firm_uuid,
            AuditEvent.workflow_id == workflow.id,
        )
        .order_by(AuditEvent.occurred_at.asc())
    )
    entries = [
        AuditEntry(
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
    return AuditResponse(candidate_id=candidate_id, audit_entries=entries)


@router.get("/review-queue", response_model=ReviewQueueResponse)
async def review_queue(
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    firm_uuid = uuid.UUID(ctx.firm_id)
    result = await db.execute(
        select(RetainerWorkflow)
        .where(
            RetainerWorkflow.tenant_id == firm_uuid,
            RetainerWorkflow.state.in_([
                EngagementState.NOT_STARTED,
                EngagementState.ATTORNEY_APPROVAL_RECORDED,
            ]),
        )
        .order_by(RetainerWorkflow.created_at.desc())
    )
    workflows = result.scalars().all()
    summaries = [
        WorkflowSummary(
            workflow_id=w.id,
            matter_candidate_id=w.matter_candidate_id,
            state=EngagementState(w.state),
            version=w.version,
            created_at=w.created_at,
            updated_at=w.updated_at,
        )
        for w in workflows
    ]
    return ReviewQueueResponse(workflows=summaries)


@router.get("/workflows/{workflow_id}", response_model=WorkflowDetail)
async def get_workflow(
    workflow_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    workflow = await db.get(RetainerWorkflow, workflow_id)
    if workflow is None or str(workflow.tenant_id) != ctx.firm_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowDetail(
        workflow_id=workflow.id,
        tenant_id=workflow.tenant_id,
        matter_candidate_id=workflow.matter_candidate_id,
        candidate_version=workflow.candidate_version,
        state=EngagementState(workflow.state),
        version=workflow.version,
        representation_decision_id=workflow.representation_decision_id,
        conflict_review_id=workflow.conflict_review_id,
        engagement_package_id=workflow.engagement_package_id,
        activation_checklist_id=workflow.activation_checklist_id,
        activated_matter_id=workflow.activated_matter_id,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


@router.get("/workflows/{workflow_id}/timeline", response_model=WorkflowTimelineResponse)
async def get_workflow_timeline(
    workflow_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    workflow = await db.get(RetainerWorkflow, workflow_id)
    if workflow is None or str(workflow.tenant_id) != ctx.firm_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    firm_uuid = uuid.UUID(ctx.firm_id)
    result = await db.execute(
        select(RetainerOutboxEvent)
        .where(RetainerOutboxEvent.aggregate_id == workflow_id)
        .where(RetainerOutboxEvent.tenant_id == firm_uuid)
        .order_by(RetainerOutboxEvent.created_at.asc())
    )
    outbox_events = result.scalars().all()

    events = [
        TimelineEvent(
            event_id=e.event_id,
            event_type=e.event_type,
            occurred_at=e.created_at,
            authority_class=e.payload_json.get("authority_class", "SYS_ADMIN"),
            actor_id=e.payload_json.get("actor_id", "system"),
        )
        for e in outbox_events
    ]
    return WorkflowTimelineResponse(workflow_id=workflow_id, events=events)
