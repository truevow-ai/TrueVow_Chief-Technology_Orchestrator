"""v1.1 Capability Addendum — API routes."""

# ruff: noqa: B008

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthContext, get_current_context
from app.core.database import get_db
from app.domain.v11_addendum import (
    build_client_experience_projection,
    create_request_items,
    pause_work_item,
    reassign_work_item,
    record_engagement_outcome,
    resume_work_item,
    submit_information,
    verify_submission,
)

router = APIRouter(tags=["v11"])


@router.post("/information-requests/{request_id}/items", status_code=201)
async def create_request_items_endpoint(
    request_id: uuid.UUID,
    payload: dict,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        ids = await create_request_items(
            db, request_id=request_id, tenant_id=uuid.UUID(ctx.firm_id),
            items=payload.get("items", []),
        )
        await db.commit()
        return {"item_ids": [str(i) for i in ids]}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/information-request-items/{item_id}/submit", status_code=201)
async def submit_information_endpoint(
    item_id: uuid.UUID,
    payload: dict,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        sub_id = await submit_information(
            db, request_item_id=item_id, tenant_id=uuid.UUID(ctx.firm_id),
            submitted_by_actor_id=payload.get("submitted_by_actor_id", ctx.user_id),
            content=payload["content"], content_type=payload.get("content_type", "TEXT"),
        )
        await db.commit()
        return {"submission_id": str(sub_id), "status": "FULFILLED"}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/information-submissions/{submission_id}/verify", status_code=200)
async def verify_submission_endpoint(
    submission_id: uuid.UUID,
    payload: dict,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        sid = await verify_submission(
            db, submission_id=submission_id, tenant_id=uuid.UUID(ctx.firm_id),
            verified_by_actor_id=ctx.user_id,
            status=payload.get("status", "VERIFIED"),
        )
        await db.commit()
        return {"submission_id": str(sid), "status": payload.get("status", "VERIFIED")}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/workflows/{workflow_id}/outcome", status_code=201)
async def record_outcome_endpoint(
    workflow_id: uuid.UUID,
    payload: dict,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        oid = await record_engagement_outcome(
            db, workflow_id=workflow_id, tenant_id=uuid.UUID(ctx.firm_id),
            outcome_class=payload["outcome_class"],
            friction_reason=payload.get("friction_reason"),
            evidence_classification=payload.get("evidence_classification", "SYSTEM_OBSERVED"),
            stated_by_actor_id=payload.get("stated_by_actor_id"),
            recorded_by_actor_id=ctx.user_id,
            notes=payload.get("notes"),
        )
        await db.commit()
        return {"outcome_id": str(oid), "outcome_class": payload["outcome_class"]}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/workflows/{workflow_id}/client-experience", status_code=201)
async def build_experience_endpoint(
    workflow_id: uuid.UUID,
    payload: dict,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        pid = await build_client_experience_projection(
            db, workflow_id=workflow_id, tenant_id=uuid.UUID(ctx.firm_id),
            recipient_party_role_id=payload["recipient_party_role_id"],
        )
        await db.commit()
        return {"projection_id": str(pid)}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/work-items/{item_id}/pause", status_code=200)
async def pause_work_item_endpoint(
    item_id: uuid.UUID,
    payload: dict,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        iid = await pause_work_item(
            db, item_id=item_id, tenant_id=uuid.UUID(ctx.firm_id),
            reason=payload.get("reason", "Unspecified"),
        )
        await db.commit()
        return {"item_id": str(iid), "state": "PAUSED"}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/work-items/{item_id}/resume", status_code=200)
async def resume_work_item_endpoint(
    item_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        iid = await resume_work_item(db, item_id=item_id, tenant_id=uuid.UUID(ctx.firm_id))
        await db.commit()
        return {"item_id": str(iid), "state": "PENDING"}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/work-items/{item_id}/reassign", status_code=200)
async def reassign_work_item_endpoint(
    item_id: uuid.UUID,
    payload: dict,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        iid = await reassign_work_item(
            db, item_id=item_id, tenant_id=uuid.UUID(ctx.firm_id),
            new_actor_id=payload["new_actor_id"],
        )
        await db.commit()
        return {"item_id": str(iid), "assigned_to": payload["new_actor_id"]}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None
