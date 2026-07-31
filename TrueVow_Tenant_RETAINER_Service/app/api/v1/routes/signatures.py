"""BP-05 Signature Ceremony API routes."""

# ruff: noqa: B008

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthContext, get_current_context
from app.core.database import get_db
from app.domain.signature import (
    apply_signature,
    create_ceremony,
    invalidate_signature,
    mark_fully_executed,
)
from app.models import (
    SignatureCeremony,
    SignatureEvidenceRef,
    SignerRequirement,
)
from app.schemas import (
    ApplySignatureRequest,
    ApplySignatureResponse,
    CeremonyDetailResponse,
    CreateCeremonyRequest,
    CreateCeremonyResponse,
    InvalidateSignatureRequest,
    InvalidateSignatureResponse,
    MarkExecutedResponse,
    SignerRequirementResponse,
)

router = APIRouter(tags=["signatures"])


@router.post(
    "/packages/{package_id}/ceremonies",
    status_code=201,
    response_model=CreateCeremonyResponse,
)
async def create_ceremony_endpoint(
    package_id: uuid.UUID,
    payload: CreateCeremonyRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        signers = [s.model_dump() for s in payload.signers]
        ceremony_id = await create_ceremony(
            db,
            package_id=package_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            provider_type=payload.provider_type,
            signers=signers,
            expires_at=payload.expires_at,
        )
        await db.commit()
        ceremony = await db.get(SignatureCeremony, ceremony_id)
        signer_result = await db.execute(
            select(SignerRequirement).where(SignerRequirement.ceremony_id == ceremony_id)
        )
        signers_list = signer_result.scalars().all()
        return CreateCeremonyResponse(
            ceremony_id=ceremony_id,
            provider_type=ceremony.provider_type if ceremony else "",
            state=ceremony.state if ceremony else "",
            created_at=ceremony.created_at if ceremony else None,
            signers=[SignerRequirementResponse(**s.__dict__) for s in signers_list],
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.get(
    "/ceremonies/{ceremony_id}",
    response_model=CeremonyDetailResponse,
)
async def get_ceremony_detail(
    ceremony_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    ceremony = await db.get(SignatureCeremony, ceremony_id)
    if ceremony is None or str(ceremony.tenant_id) != ctx.firm_id:
        raise HTTPException(status_code=404, detail="Ceremony not found")

    signer_result = await db.execute(
        select(SignerRequirement).where(SignerRequirement.ceremony_id == ceremony_id)
    )
    signers = signer_result.scalars().all()

    evidence_result = await db.execute(
        select(SignatureEvidenceRef).where(SignatureEvidenceRef.ceremony_id == ceremony_id)
    )
    evidences = evidence_result.scalars().all()

    return CeremonyDetailResponse(
        ceremony_id=ceremony.id,
        package_id=ceremony.package_id,
        provider_type=ceremony.provider_type,
        state=ceremony.state,
        created_at=ceremony.created_at,
        expires_at=ceremony.expires_at,
        signers=[SignerRequirementResponse(**s.__dict__) for s in signers],
        signatures=[{"evidence_id": str(e.id), "validity_state": e.validity_state, "signer_id": str(e.signer_requirement_id)} for e in evidences],
    )


@router.post(
    "/ceremonies/{ceremony_id}/sign",
    status_code=201,
    response_model=ApplySignatureResponse,
)
async def apply_signature_endpoint(
    ceremony_id: uuid.UUID,
    payload: ApplySignatureRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        evidence_id = await apply_signature(
            db,
            ceremony_id=ceremony_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            party_role_id=payload.party_role_id,
            shared_signature_evidence_id=payload.shared_signature_evidence_id,
            signer_requirement_id=payload.signer_requirement_id,
        )
        await db.commit()
        evidence = await db.get(SignatureEvidenceRef, evidence_id)
        return ApplySignatureResponse(
            evidence_id=evidence_id,
            validity_state=evidence.validity_state if evidence else "VALID",
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post(
    "/ceremonies/{ceremony_id}/invalidate-signature",
    status_code=200,
    response_model=InvalidateSignatureResponse,
)
async def invalidate_signature_endpoint(
    ceremony_id: uuid.UUID,
    payload: InvalidateSignatureRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        ev_id = await invalidate_signature(
            db,
            evidence_id=payload.evidence_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            reason=payload.reason,
        )
        await db.commit()
        return InvalidateSignatureResponse(evidence_id=ev_id, validity_state="INVALIDATED")
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post(
    "/ceremonies/{ceremony_id}/mark-executed",
    status_code=200,
    response_model=MarkExecutedResponse,
)
async def mark_executed_endpoint(
    ceremony_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = await mark_fully_executed(
            db,
            ceremony_id=ceremony_id,
            tenant_id=uuid.UUID(ctx.firm_id),
        )
        await db.commit()
        ceremony = await db.get(SignatureCeremony, cid)
        return MarkExecutedResponse(
            ceremony_id=cid,
            state=ceremony.state if ceremony else "FULLY_EXECUTED",
            executed_at=ceremony.created_at if ceremony else None,
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None
