"""BP-03 Template Resolution and Package Generation API routes."""

# ruff: noqa: B008

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthContext, get_current_context
from app.core.database import get_db
from app.domain.template_package import generate_package, resolve_template
from app.models import (
    EngagementPackage,
    PackageDocument,
    PackagePreflightResult,
    TemplateMergeField,
    TemplateResolution,
)
from app.schemas import (
    GeneratePackageRequest,
    GeneratePackageResponse,
    MergeFieldResponse,
    PackageDetailResponse,
    PackageDocumentResponse,
    PreflightResultResponse,
    ResolveTemplateRequest,
    ResolveTemplateResponse,
)

router = APIRouter(tags=["templates"])


@router.post(
    "/workflows/{workflow_id}/templates/resolve",
    status_code=201,
    response_model=ResolveTemplateResponse,
)
async def resolve_template_endpoint(
    workflow_id: uuid.UUID,
    payload: ResolveTemplateRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        merge_dicts = [m.model_dump() for m in payload.merge_fields]
        resolution_id = await resolve_template(
            db,
            workflow_id=workflow_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            template_definition_id=payload.template_definition_id,
            template_version=payload.template_version,
            policy_version_id=payload.policy_version_id,
            merge_fields=merge_dicts,
            jurisdiction_profile_version_id=payload.jurisdiction_profile_version_id,
        )
        await db.commit()
        resolution = await db.get(TemplateResolution, resolution_id)
        fields_result = await db.execute(
            select(TemplateMergeField).where(
                TemplateMergeField.template_resolution_id == resolution_id
            )
        )
        fields = fields_result.scalars().all()
        return ResolveTemplateResponse(
            resolution_id=resolution_id,
            template_definition_id=resolution.template_definition_id,
            template_version=resolution.template_version,
            template_hash=resolution.template_hash,
            resolved_at=resolution.resolved_at,
            merge_fields=[MergeFieldResponse(**f.__dict__) for f in fields],
        )
    except ValueError as e:
        await db.rollback()
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from None
        raise HTTPException(status_code=409, detail=msg) from None


@router.post(
    "/workflows/{workflow_id}/packages",
    status_code=201,
    response_model=GeneratePackageResponse,
)
async def generate_package_endpoint(
    workflow_id: uuid.UUID,
    payload: GeneratePackageRequest,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        preflight_dicts = [p.model_dump() for p in payload.preflight_controls]
        package_id = await generate_package(
            db,
            workflow_id=workflow_id,
            tenant_id=uuid.UUID(ctx.firm_id),
            template_resolution_id=payload.template_resolution_id,
            document_roles=payload.document_roles or ["engagement_letter"],
            preflight_controls=preflight_dicts,
            actor_id=ctx.user_id,
        )
        await db.commit()
        package = await db.get(EngagementPackage, package_id)
        docs_result = await db.execute(
            select(PackageDocument).where(
                PackageDocument.package_id == package_id,
                PackageDocument.tenant_id == uuid.UUID(ctx.firm_id),
            )
        )
        docs = docs_result.scalars().all()
        preflight_result = await db.execute(
            select(PackagePreflightResult).where(
                PackagePreflightResult.package_id == package_id
            )
        )
        preflights = preflight_result.scalars().all()
        return GeneratePackageResponse(
            package_id=package_id,
            status=package.status,
            package_hash=package.package_hash,
            generated_at=package.generated_at,
            documents=[
                PackageDocumentResponse(
                    document_version_id=d.document_version_id,
                    document_role=d.document_role,
                    required=d.required,
                    sequence=d.sequence,
                    document_hash=d.document_hash,
                )
                for d in docs
            ],
            preflight_results=[
                PreflightResultResponse(
                    control_id=p.control_id,
                    control_name=p.control_name,
                    passed=p.passed,
                    detail=p.detail,
                )
                for p in preflights
            ],
        )
    except ValueError as e:
        await db.rollback()
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from None
        raise HTTPException(status_code=409, detail=msg) from None


@router.get(
    "/packages/{package_id}",
    response_model=PackageDetailResponse,
)
async def get_package_detail(
    package_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    package = await db.get(EngagementPackage, package_id)
    if package is None or str(package.tenant_id) != ctx.firm_id:
        raise HTTPException(status_code=404, detail="Package not found")

    docs_result = await db.execute(
        select(PackageDocument).where(
            PackageDocument.package_id == package_id,
            PackageDocument.tenant_id == uuid.UUID(ctx.firm_id),
        ).order_by(PackageDocument.sequence)
    )
    docs = docs_result.scalars().all()
    preflight_result = await db.execute(
        select(PackagePreflightResult).where(
            PackagePreflightResult.package_id == package_id
        )
    )
    preflights = preflight_result.scalars().all()

    return PackageDetailResponse(
        package_id=package.id,
        workflow_id=package.workflow_id,
        tenant_id=package.tenant_id,
        status=package.status,
        package_hash=package.package_hash,
        generated_at=package.generated_at,
        locked_at=package.locked_at,
        documents=[
            PackageDocumentResponse(
                document_version_id=d.document_version_id,
                document_role=d.document_role,
                required=d.required,
                sequence=d.sequence,
                document_hash=d.document_hash,
            )
            for d in docs
        ],
        preflight_results=[
            PreflightResultResponse(
                control_id=p.control_id,
                control_name=p.control_name,
                passed=p.passed,
                detail=p.detail,
            )
            for p in preflights
        ],
    )
