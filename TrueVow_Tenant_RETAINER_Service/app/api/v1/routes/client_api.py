"""RETAINER Client API — client-safe projections for the TrueVow Client Portal.

These endpoints use portal access tokens (not firm auth). They return only
client-permitted information — no conflict details, attorney notes, authority
gates, internal risk flags, or other candidates.
"""

# ruff: noqa: B008

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_public
from app.domain.portal import (
    grant_esign_consent,
    record_client_decline,
    submit_client_question,
    validate_portal_access,
)
from app.models import (
    EngagementPackage,
    PackageDocument,
    RetainerWorkflow,
    SignatureCeremony,
    SignatureEvidenceRef,
)

router = APIRouter(prefix="/client/v1", tags=["client-portal"])


async def _resolve_access(token: str, db: AsyncSession):
    result = await validate_portal_access(db, access_token=token)
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    return result


def _has_scope(access: dict, *required: str) -> bool:
    scopes = set(access.get("scopes", []))
    if "ENGAGEMENT_HISTORY" in scopes:
        scopes.add("ENGAGEMENT_VIEW")
        scopes.add("COMPLETED_COPY_DOWNLOAD")
    return bool(scopes.intersection(required))


@router.get("/me")
async def client_me(token: str, db: AsyncSession = Depends(get_db_public)):
    access = await _resolve_access(token, db)
    await db.commit()
    return {
        "party_role_id": access.get("prospect_party_role_id"),
        "scope": "ENGAGEMENT_ONLY",
        "tenant_id": access.get("tenant_id"),
    }


@router.get("/engagements")
async def client_engagements(token: str, db: AsyncSession = Depends(get_db_public)):
    access = await _resolve_access(token, db)
    await db.commit()
    wf_result = await db.execute(
        select(RetainerWorkflow).where(RetainerWorkflow.id == uuid.UUID(access["workflow_id"]))
    )
    wf = wf_result.scalars().first()
    if wf is None:
        return {"engagements": []}

    pkg = None
    if wf.engagement_package_id:
        pkg = await db.get(EngagementPackage, wf.engagement_package_id)

    return {
        "engagements": [{
            "engagement_id": str(wf.id),
            "state": _client_state(wf.state),
            "candidate_version": wf.candidate_version,
            "package_status": pkg.status if pkg else None,
            "delivered_at": str(pkg.locked_at) if pkg and pkg.locked_at else None,
        }]
    }


@router.get("/engagements/{engagement_id}")
async def client_engagement_detail(
    engagement_id: uuid.UUID,
    token: str,
    db: AsyncSession = Depends(get_db_public),
):
    access = await _resolve_access(token, db)
    if str(access["workflow_id"]) != str(engagement_id):
        raise HTTPException(status_code=403, detail="Access denied")
    await db.commit()

    wf = await db.get(RetainerWorkflow, engagement_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Not found")

    pkg = None
    if wf.engagement_package_id:
        pkg = await db.get(EngagementPackage, wf.engagement_package_id)

    return {
        "engagement_id": str(wf.id),
        "state": _client_state(wf.state),
        "candidate_version": wf.candidate_version,
        "package": {
            "status": pkg.status if pkg else None,
            "hash": pkg.package_hash if pkg else None,
            "delivered_at": str(pkg.locked_at) if pkg and pkg.locked_at else None,
        } if pkg else None,
        "is_activated": wf.activated_matter_id is not None,
    }


@router.get("/engagements/{engagement_id}/documents")
async def client_engagement_documents(
    engagement_id: uuid.UUID,
    token: str,
    db: AsyncSession = Depends(get_db_public),
):
    access = await _resolve_access(token, db)
    if str(access["workflow_id"]) != str(engagement_id):
        raise HTTPException(status_code=403, detail="Access denied")
    await db.commit()

    wf = await db.get(RetainerWorkflow, engagement_id)
    if wf is None or wf.engagement_package_id is None:
        return {"documents": []}

    docs_result = await db.execute(
        select(PackageDocument).where(
            PackageDocument.package_id == wf.engagement_package_id,
            PackageDocument.tenant_id == wf.tenant_id,
        ).order_by(PackageDocument.sequence)
    )
    return {
        "documents": [
            {
                "document_version_id": str(d.document_version_id),
                "role": d.document_role,
                "required": d.required,
                "sequence": d.sequence,
                "hash": d.document_hash,
            }
            for d in docs_result.scalars().all()
        ]
    }


@router.get("/engagements/{engagement_id}/signatures")
async def client_engagement_signatures(
    engagement_id: uuid.UUID,
    token: str,
    db: AsyncSession = Depends(get_db_public),
):
    access = await _resolve_access(token, db)
    if str(access["workflow_id"]) != str(engagement_id):
        raise HTTPException(status_code=403, detail="Access denied")
    await db.commit()

    wf = await db.get(RetainerWorkflow, engagement_id)
    if wf is None or wf.engagement_package_id is None:
        return {"ceremonies": []}

    ceremonies_result = await db.execute(
        select(SignatureCeremony).where(SignatureCeremony.package_id == wf.engagement_package_id)
    )
    ceremonies = ceremonies_result.scalars().all()

    result = []
    for cer in ceremonies:
        ev_result = await db.execute(
            select(SignatureEvidenceRef).where(SignatureEvidenceRef.ceremony_id == cer.id)
        )
        result.append({
            "ceremony_id": str(cer.id),
            "state": cer.state,
            "provider": cer.provider_type,
            "created_at": str(cer.created_at),
            "signatures": [
                {"evidence_id": str(e.id), "state": e.validity_state}
                for e in ev_result.scalars().all()
            ],
        })

    return {"ceremonies": result}


def _client_state(internal_state: str) -> str:
    mapping = {
        "NOT_STARTED": "BEING_PREPARED",
        "ATTORNEY_APPROVAL_RECORDED": "BEING_PREPARED",
        "CONFLICT_REVIEW_PENDING": "BEING_PREPARED",
        "CONFLICT_HOLD": "BEING_PREPARED",
        "PACKAGE_PREPARATION": "BEING_PREPARED",
        "DELIVERY_AUTHORIZED": "READY_FOR_REVIEW",
        "DELIVERED": "READY_FOR_REVIEW",
        "CLIENT_REVIEW": "READY_FOR_REVIEW",
        "SIGNATURE_PENDING": "ACTION_REQUIRED",
        "FULLY_EXECUTED": "COMPLETED",
        "ACTIVATION_PENDING": "COMPLETED",
        "ACTIVATED": "COMPLETED",
        "DECLINED_OR_EXPIRED": "CLOSED",
    }
    return mapping.get(internal_state, "UNKNOWN")


@router.post("/engagements/{engagement_id}/questions", status_code=201)
async def client_submit_question(
    engagement_id: uuid.UUID,
    token: str,
    payload: dict,
    db: AsyncSession = Depends(get_db_public),
):
    access = await _resolve_access(token, db)
    if str(access["workflow_id"]) != str(engagement_id):
        raise HTTPException(status_code=403, detail="Access denied")
    if "ENGAGEMENT_HISTORY" in access.get("scopes", []):
        raise HTTPException(status_code=403, detail="Engagement is historical — cannot submit questions")
    if "ENGAGEMENT_QUESTION" not in access.get("scopes", []):
        raise HTTPException(status_code=403, detail="Permission denied")
    try:
        q_id = await submit_client_question(
            db, access_token=token, question_text=payload["question_text"],
            document_version_id=payload.get("document_version_id"),
            page_or_clause_ref=payload.get("page_or_clause_ref"),
        )
        await db.commit()
        return {"question_id": str(q_id), "state": "RECEIVED"}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/engagements/{engagement_id}/decline", status_code=200)
async def client_decline_engagement(
    engagement_id: uuid.UUID,
    token: str,
    payload: dict,
    db: AsyncSession = Depends(get_db_public),
):
    access = await _resolve_access(token, db)
    if str(access["workflow_id"]) != str(engagement_id):
        raise HTTPException(status_code=403, detail="Access denied")
    if "ENGAGEMENT_HISTORY" in access.get("scopes", []):
        raise HTTPException(status_code=403, detail="Engagement is historical — cannot decline")
    try:
        wf_id = await record_client_decline(db, access_token=token, reason=payload.get("reason"))
        await db.commit()
        return {"workflow_id": str(wf_id), "state": "DECLINED"}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/engagements/{engagement_id}/consent", status_code=201)
async def client_grant_consent(
    engagement_id: uuid.UUID,
    token: str,
    payload: dict,
    db: AsyncSession = Depends(get_db_public),
):
    access = await _resolve_access(token, db)
    if str(access["workflow_id"]) != str(engagement_id):
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        c_id = await grant_esign_consent(
            db, access_token=token,
            prospect_party_role_id=uuid.UUID(payload["prospect_party_role_id"]),
            ip_address=payload.get("ip_address"),
            user_agent=payload.get("user_agent"),
        )
        await db.commit()
        return {"consent_id": str(c_id), "state": "GRANTED"}
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.get("/engagements/{engagement_id}/completed-copy")
async def client_completed_copy(
    engagement_id: uuid.UUID,
    token: str,
    db: AsyncSession = Depends(get_db_public),
):
    access = await _resolve_access(token, db)
    if str(access["workflow_id"]) != str(engagement_id):
        raise HTTPException(status_code=403, detail="Access denied")
    if not _has_scope(access, "COMPLETED_COPY_DOWNLOAD"):
        raise HTTPException(status_code=403, detail="Permission denied")
    await db.commit()

    wf = await db.get(RetainerWorkflow, engagement_id)
    if wf is None or wf.engagement_package_id is None:
        return {"completed_copy_available": False}

    docs_result = await db.execute(
        select(PackageDocument).where(
            PackageDocument.package_id == wf.engagement_package_id,
            PackageDocument.tenant_id == wf.tenant_id,
        ).order_by(PackageDocument.sequence)
    )
    return {
        "completed_copy_available": wf.state in ("FULLY_EXECUTED", "ACTIVATION_PENDING", "ACTIVATED"),
        "documents": [
            {"document_version_id": str(d.document_version_id), "role": d.document_role, "hash": d.document_hash}
            for d in docs_result.scalars().all()
        ],
    }
