"""BP-07 TRACE Handoff — generates a TRACE manifest after matter activation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from retainer_contracts.events import EventType
from retainer_contracts.states import EngagementState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActivationChecklist,
    ActivationChecklistItem,
    ConflictReview,
    EngagementPackage,
    PackageDocument,
    RepresentationDecision,
    RetainerOutboxEvent,
    RetainerWorkflow,
    SignatureCeremony,
    SignatureEvidenceRef,
)


async def generate_trace_manifest(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> dict:
    workflow = await db.get(RetainerWorkflow, workflow_id)
    if workflow is None or str(workflow.tenant_id) != str(tenant_id):
        raise ValueError("Workflow not found")
    if workflow.state != EngagementState.ACTIVATED:
        raise ValueError(f"TRACE manifest requires ACTIVATED state, not {workflow.state}")

    manifest = {
        "manifest_id": str(uuid.uuid4()),
        "generated_at": datetime.now(UTC).isoformat(),
        "workflow_id": str(workflow_id),
        "tenant_id": str(tenant_id),
        "activated_matter_id": str(workflow.activated_matter_id) if workflow.activated_matter_id else None,
        "candidate_version": workflow.candidate_version,
    }

    if workflow.representation_decision_id:
        decision = await db.get(RepresentationDecision, workflow.representation_decision_id)
        if decision:
            manifest["representation"] = {"outcome": decision.outcome, "scope": decision.scope_json, "decided_at": decision.decided_at.isoformat() if decision.decided_at else None}

    if workflow.conflict_review_id:
        review = await db.get(ConflictReview, workflow.conflict_review_id)
        if review:
            manifest["conflict_review"] = {"outcome": review.outcome, "decided_at": review.decided_at.isoformat() if review.decided_at else None}

    if workflow.engagement_package_id:
        package = await db.get(EngagementPackage, workflow.engagement_package_id)
        if package:
            docs_result = await db.execute(select(PackageDocument).where(PackageDocument.package_id == package.id))
            manifest["package"] = {"package_hash": package.package_hash, "documents": [{"role": d.document_role, "hash": d.document_hash} for d in docs_result.scalars().all()]}

    ceremonies_result = await db.execute(select(SignatureCeremony).where(SignatureCeremony.package_id == workflow.engagement_package_id))
    ceremonies = ceremonies_result.scalars().all()
    if ceremonies:
        sig_data = []
        for cer in ceremonies:
            ev_result = await db.execute(select(SignatureEvidenceRef).where(SignatureEvidenceRef.ceremony_id == cer.id))
            sig_data.append({"ceremony_id": str(cer.id), "state": cer.state, "signatures": len(ev_result.scalars().all())})
        manifest["signatures"] = sig_data

    if workflow.activation_checklist_id:
        checklist = await db.get(ActivationChecklist, workflow.activation_checklist_id)
        if checklist:
            items_result = await db.execute(select(ActivationChecklistItem).where(ActivationChecklistItem.checklist_id == checklist.id))
            manifest["activation"] = {"items": [{"control_id": i.control_id, "result": i.result} for i in items_result.scalars().all()]}

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(), tenant_id=tenant_id, aggregate_id=workflow_id,
        event_type=EventType.COMPLETED_COPY_DELIVERED, schema_version="1.0.1",
        payload_json={"manifest_id": manifest["manifest_id"], "matter_id": manifest["activated_matter_id"]},
    )
    db.add(outbox)

    return manifest
