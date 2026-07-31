"""BP-04 Client Engagement Portal API routes."""

# ruff: noqa: B008

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthContext, get_current_context
from app.core.database import get_db, get_db_public
from app.domain.portal import (
    authorize_delivery,
    generate_portal_token,
    grant_esign_consent,
    record_client_decline,
    submit_client_question,
    validate_portal_access,
)
from app.models import (
    ClientPortalAccess,
    DeliveryAuthorization,
)
from app.schemas import (
    AuthorizeDeliveryRequest,
    AuthorizeDeliveryResponse,
    ClientDeclineRequest,
    ClientDeclineResponse,
    GeneratePortalTokenRequest,
    GrantConsentRequest,
    GrantConsentResponse,
    PortalAccessDetailResponse,
    PortalTokenResponse,
    SubmitQuestionRequest,
    SubmitQuestionResponse,
)

router = APIRouter(tags=["portal"])


@router.post(
    "/workflows/{workflow_id}/packages/{package_id}/authorize-delivery",
    status_code=201,
    response_model=AuthorizeDeliveryResponse,
)
async def authorize_delivery_endpoint(
    workflow_id: uuid.UUID,
    package_id: uuid.UUID,
    payload: AuthorizeDeliveryRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        auth_id = await authorize_delivery(
            db,
            package_id=package_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            authorized_by_actor_id=ctx.user_id,
            authority_record_id=payload.authority_record_id,
            channel=payload.channel,
            recipient_verified=payload.recipient_verified,
        )
        await db.commit()
        auth = await db.get(DeliveryAuthorization, auth_id)
        return AuthorizeDeliveryResponse(
            authorization_id=auth_id,
            authorized_at=auth.authorized_at if auth else None,
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post(
    "/workflows/{workflow_id}/portal/token",
    status_code=201,
    response_model=PortalTokenResponse,
)
async def generate_portal_token_endpoint(
    workflow_id: uuid.UUID,
    payload: GeneratePortalTokenRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        token, access_id = await generate_portal_token(
            db,
            package_id=payload.package_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            prospect_party_role_id=payload.prospect_party_role_id,
            actor_id=ctx.user_id,
        )
        await db.commit()
        access = await db.get(ClientPortalAccess, access_id)
        return PortalTokenResponse(
            access_token=token,
            token_hash=access.access_token_hash if access else "",
            issued_at=access.issued_at if access else None,
            expires_at=access.expires_at if access else None,
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.get(
    "/portal/access",
    response_model=PortalAccessDetailResponse,
)
async def portal_access_endpoint(
    token: str,
    db: AsyncSession = Depends(get_db_public),
):
    result = await validate_portal_access(db, access_token=token)
    await db.commit()
    if not result.get("valid"):
        raise HTTPException(status_code=404, detail="Invalid or expired access token")
    return PortalAccessDetailResponse(
        access_id=uuid.UUID(result["access_id"]),
        package_id=uuid.UUID(result["package_id"]),
        state="ACTIVE",
        issued_at=datetime.now(UTC),
        documents=result.get("documents", []),
        consent_status=result.get("consent_status"),
    )


@router.post(
    "/portal/consent",
    status_code=201,
    response_model=GrantConsentResponse,
)
async def grant_consent_endpoint(
    token: str,
    payload: GrantConsentRequest,
    db: AsyncSession = Depends(get_db_public),
):
    try:
        consent_id = await grant_esign_consent(
            db,
            access_token=token,
            prospect_party_role_id=payload.prospect_party_role_id,
            ip_address=payload.ip_address,
            user_agent=payload.user_agent,
        )
        await db.commit()
        return GrantConsentResponse(
            consent_id=consent_id,
            state="GRANTED",
            granted_at=datetime.now(UTC),
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post(
    "/portal/questions",
    status_code=201,
    response_model=SubmitQuestionResponse,
)
async def submit_question_endpoint(
    token: str,
    payload: SubmitQuestionRequest,
    db: AsyncSession = Depends(get_db_public),
):
    try:
        q_id = await submit_client_question(
            db,
            access_token=token,
            question_text=payload.question_text,
            document_version_id=payload.document_version_id,
            page_or_clause_ref=payload.page_or_clause_ref,
        )
        await db.commit()
        return SubmitQuestionResponse(
            question_id=q_id,
            state="RECEIVED",
            created_at=datetime.now(UTC),
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.post(
    "/portal/decline",
    response_model=ClientDeclineResponse,
)
async def client_decline_endpoint(
    token: str,
    payload: ClientDeclineRequest,
    db: AsyncSession = Depends(get_db_public),
):
    try:
        wf_id = await record_client_decline(
            db,
            access_token=token,
            reason=payload.reason,
        )
        await db.commit()
        return ClientDeclineResponse(
            workflow_id=wf_id,
            state="DECLINED_OR_EXPIRED",
            declined_at=datetime.now(UTC),
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from None
