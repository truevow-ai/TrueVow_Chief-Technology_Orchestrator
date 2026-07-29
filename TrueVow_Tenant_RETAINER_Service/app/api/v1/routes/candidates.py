"""Candidate and representation review API routes."""

# ruff: noqa: B008 (Depends() in function defaults is standard FastAPI pattern)

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from retainer_contracts.states import EngagementState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthContext, get_current_context
from app.core.database import get_db
from app.domain.candidate import import_candidate
from app.domain.representation import record_representation_decision
from app.models import RepresentationDecision, RetainerOutboxEvent, RetainerWorkflow
from app.schemas import (
    CandidateHandoffRequest,
    CandidateImportResponse,
    RepresentationDecisionRequest,
    RepresentationDecisionResponse,
    ReviewQueueResponse,
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
    correlation_id = uuid.uuid4()
    try:
        workflow_id, _ = await import_candidate(
            db,
            tenant_id=payload.tenant_id,
            matter_candidate_id=payload.matter_candidate_id,
            candidate_version=payload.candidate_version,
            source_event_id=payload.source_event_ids[0],
            submitted_by_actor_id=payload.submitted_by_actor_id,
            source_event_ids=payload.source_event_ids,
            correlation_id=correlation_id,
        )
        await db.commit()
        return CandidateImportResponse(
            workflow_id=workflow_id,
            state=EngagementState.NOT_STARTED,
            candidate_version=payload.candidate_version,
            correlation_id=str(correlation_id),
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post(
    "/candidates/{candidate_id}/decisions",
    status_code=201,
    response_model=RepresentationDecisionResponse,
)
async def record_decision_endpoint(
    candidate_id: uuid.UUID,
    payload: RepresentationDecisionRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    firm_uuid = uuid.UUID(ctx.firm_id)
    result = await db.execute(
        select(RetainerWorkflow).where(
            RetainerWorkflow.tenant_id == firm_uuid,
            RetainerWorkflow.matter_candidate_id == candidate_id,
        ).order_by(RetainerWorkflow.candidate_version.desc())
    )
    workflow = result.scalars().first()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    correlation_id = uuid.uuid4()
    try:
        decision_id = await record_representation_decision(
            db,
            workflow_id=workflow.id,
            tenant_id=uuid.UUID(ctx.firm_id),
            attorney_actor_id=ctx.user_id,
            authority_record_id=payload.authority_record_id,
            outcome=payload.outcome,
            scope_json=payload.scope_json,
            supersedes_id=payload.supersedes_id,
            correlation_id=correlation_id,
        )
        await db.commit()
        decision = await db.get(RepresentationDecision, decision_id)
        return RepresentationDecisionResponse(
            decision_id=decision_id,
            outcome=decision.outcome,
            decided_at=decision.decided_at,
            correlation_id=str(correlation_id),
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


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
