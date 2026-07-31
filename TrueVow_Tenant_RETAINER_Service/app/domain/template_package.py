"""BP-03 Template Resolution and Package Generation domain services."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from retainer_contracts.events import EventType
from retainer_contracts.states import EngagementState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    EngagementPackage,
    PackageDocument,
    PackagePreflightResult,
    RetainerOutboxEvent,
    RetainerWorkflow,
    TemplateMergeField,
    TemplateResolution,
)


def _compute_hash(data: dict) -> str:
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


async def resolve_template(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    tenant_id: uuid.UUID,
    template_definition_id: uuid.UUID,
    template_version: str,
    policy_version_id: uuid.UUID,
    merge_fields: list[dict],
    jurisdiction_profile_version_id: uuid.UUID | None = None,
) -> uuid.UUID:
    result = await db.execute(
        select(RetainerWorkflow).where(
            RetainerWorkflow.id == workflow_id,
            RetainerWorkflow.tenant_id == tenant_id,
        ).with_for_update(),
    )
    workflow = result.scalars().first()
    if workflow is None:
        raise ValueError("Workflow not found")
    if workflow.state != EngagementState.PACKAGE_PREPARATION:
        raise ValueError(f"Template resolution requires PACKAGE_PREPARATION, not {workflow.state}")

    existing = (
        await db.execute(
            select(TemplateResolution).where(
                TemplateResolution.tenant_id == tenant_id,
                TemplateResolution.workflow_id == workflow_id,
                TemplateResolution.template_definition_id == template_definition_id,
                TemplateResolution.template_version == template_version,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing.id

    now = datetime.now(UTC)
    resolution_id = uuid.uuid4()
    inputs = {
        "merge_fields": {m["field_name"]: m["field_value"] for m in merge_fields},
        "jurisdiction_profile_version_id": str(jurisdiction_profile_version_id) if jurisdiction_profile_version_id else None,
    }
    template_hash = _compute_hash({
        "template_definition_id": str(template_definition_id),
        "template_version": template_version,
        "inputs": inputs,
    })

    resolution = TemplateResolution(
        id=resolution_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        template_definition_id=template_definition_id,
        template_version=template_version,
        template_hash=template_hash,
        policy_version_id=policy_version_id,
        inputs_json=inputs,
        resolved_at=now,
    )
    db.add(resolution)

    for m in merge_fields:
        field = TemplateMergeField(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            template_resolution_id=resolution_id,
            field_name=m["field_name"],
            field_value=m["field_value"],
            source=m.get("source", "candidate_record"),
            validated=True,
        )
        db.add(field)

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow_id,
        event_type=EventType.TEMPLATE_RESOLVED,
        schema_version="1.0.1",
        payload_json={
            "resolution_id": str(resolution_id),
            "template_definition_id": str(template_definition_id),
            "template_version": template_version,
            "field_count": len(merge_fields),
        },
    )
    db.add(outbox)

    return resolution_id


async def generate_package(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    tenant_id: uuid.UUID,
    template_resolution_id: uuid.UUID,
    document_roles: list[str],
    preflight_controls: list[dict],
    actor_id: str,
) -> uuid.UUID:
    result = await db.execute(
        select(RetainerWorkflow).where(
            RetainerWorkflow.id == workflow_id,
            RetainerWorkflow.tenant_id == tenant_id,
        ).with_for_update(),
    )
    workflow = result.scalars().first()
    if workflow is None:
        raise ValueError("Workflow not found")
    if workflow.state != EngagementState.PACKAGE_PREPARATION:
        raise ValueError(f"Package generation requires PACKAGE_PREPARATION, not {workflow.state}")

    resolution = await db.get(TemplateResolution, template_resolution_id)
    if resolution is None or str(resolution.workflow_id) != str(workflow_id):
        raise ValueError("Template resolution not found for this workflow")

    all_passed = all(p.get("passed", False) for p in preflight_controls)
    if preflight_controls and not all_passed:
        raise ValueError("Preflight checks failed — cannot generate package")

    now = datetime.now(UTC)
    package_id = uuid.uuid4()
    doc_hashes = []
    for role in document_roles:
        doc_hash = _compute_hash({"role": role, "template": str(template_resolution_id)})
        doc_hashes.append(doc_hash)

    package_hash = _compute_hash({
        "template_resolution_id": str(template_resolution_id),
        "document_roles": document_roles,
        "document_hashes": doc_hashes,
    })

    package = EngagementPackage(
        id=package_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        template_resolution_id=template_resolution_id,
        manifest_json={"document_roles": document_roles},
        status="DRAFT",
        package_hash=package_hash,
        generated_at=now,
    )
    db.add(package)

    for i, role in enumerate(document_roles):
        doc_version_id = uuid.uuid4()
        doc = PackageDocument(
            tenant_id=tenant_id,
            package_id=package_id,
            document_version_id=doc_version_id,
            document_role=role,
            required=True,
            sequence=i + 1,
            document_hash=doc_hashes[i] if i < len(doc_hashes) else _compute_hash({"role": role}),
        )
        db.add(doc)

    for control in preflight_controls:
        preflight = PackagePreflightResult(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            package_id=package_id,
            control_id=control.get("control_id", str(uuid.uuid4())),
            control_name=control.get("control_name", "unknown"),
            passed=control.get("passed", False),
            detail=control.get("detail"),
        )
        db.add(preflight)

    workflow.engagement_package_id = package_id
    workflow.version = workflow.version + 1

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow_id,
        event_type=EventType.PACKAGE_GENERATED,
        schema_version="1.0.1",
        payload_json={
            "package_id": str(package_id),
            "workflow_id": str(workflow_id),
            "document_count": len(document_roles),
            "package_hash": package_hash,
        },
    )
    db.add(outbox)

    return package_id
