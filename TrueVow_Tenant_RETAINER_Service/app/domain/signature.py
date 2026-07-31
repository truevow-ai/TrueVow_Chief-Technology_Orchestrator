"""BP-05 Signature Ceremony domain services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from retainer_contracts.events import EventType
from retainer_contracts.states import EngagementState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    EngagementPackage,
    RetainerOutboxEvent,
    RetainerWorkflow,
    SignatureCeremony,
    SignatureEvidenceRef,
    SignerRequirement,
)


async def create_ceremony(
    db: AsyncSession,
    *,
    package_id: uuid.UUID,
    tenant_id: uuid.UUID,
    provider_type: str,
    signers: list[dict],
    expires_at: datetime | None = None,
) -> uuid.UUID:
    package = await db.get(EngagementPackage, package_id)
    if package is None or str(package.tenant_id) != str(tenant_id):
        raise ValueError("Package not found")
    if package.status != "LOCKED":
        raise ValueError("Package must be locked before creating ceremony")

    wf_result = await db.execute(
        select(RetainerWorkflow).where(
            RetainerWorkflow.id == package.workflow_id,
        ).with_for_update(),
    )
    workflow = wf_result.scalars().first()
    if workflow is None:
        raise ValueError("Workflow not found")
    if workflow.state not in (EngagementState.DELIVERED, EngagementState.CLIENT_REVIEW):
        raise ValueError(f"Signatures require DELIVERED or CLIENT_REVIEW state, not {workflow.state}")

    now = datetime.now(UTC)
    ceremony_id = uuid.uuid4()
    ceremony = SignatureCeremony(
        id=ceremony_id,
        tenant_id=tenant_id,
        package_id=package_id,
        provider_type=provider_type,
        state="CREATED",
    )
    db.add(ceremony)

    for s in signers:
        sr = SignerRequirement(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            ceremony_id=ceremony_id,
            party_role_id=s["party_role_id"],
            signer_role=s["signer_role"],
            authority_scope=s.get("authority_scope"),
            required=s.get("required", True),
        )
        db.add(sr)

    workflow.state = EngagementState.SIGNATURE_PENDING
    workflow.version = workflow.version + 1

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow.id,
        event_type=EventType.SIGNATURE_REQUESTED,
        schema_version="1.0.1",
        payload_json={
            "ceremony_id": str(ceremony_id),
            "package_id": str(package_id),
            "signer_count": len(signers),
        },
    )
    db.add(outbox)
    return ceremony_id


async def apply_signature(
    db: AsyncSession,
    *,
    ceremony_id: uuid.UUID,
    tenant_id: uuid.UUID,
    party_role_id: uuid.UUID,
    shared_signature_evidence_id: uuid.UUID,
    signer_requirement_id: uuid.UUID,
) -> uuid.UUID:
    ceremony = await db.get(SignatureCeremony, ceremony_id)
    if ceremony is None or str(ceremony.tenant_id) != str(tenant_id):
        raise ValueError("Ceremony not found")
    if ceremony.state not in ("CREATED", "SIGNATURE_PENDING"):
        raise ValueError(f"Cannot sign from state {ceremony.state}")

    signer = await db.get(SignerRequirement, signer_requirement_id)
    if signer is None or str(signer.ceremony_id) != str(ceremony_id):
        raise ValueError("Signer requirement not found for this ceremony")

    ceremony.state = "SIGNATURE_PENDING"
    evidence_id = uuid.uuid4()
    evidence = SignatureEvidenceRef(
        id=evidence_id,
        tenant_id=tenant_id,
        ceremony_id=ceremony_id,
        signer_requirement_id=signer_requirement_id,
        shared_signature_evidence_id=shared_signature_evidence_id,
        validity_state="VALID",
    )
    db.add(evidence)

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=ceremony.package_id,
        event_type=EventType.SIGNATURE_APPLIED,
        schema_version="1.0.1",
        payload_json={
            "ceremony_id": str(ceremony_id),
            "evidence_id": str(evidence_id),
            "party_role_id": str(party_role_id),
        },
    )
    db.add(outbox)
    return evidence_id


async def invalidate_signature(
    db: AsyncSession,
    *,
    evidence_id: uuid.UUID,
    tenant_id: uuid.UUID,
    reason: str,
) -> uuid.UUID:
    evidence = await db.get(SignatureEvidenceRef, evidence_id)
    if evidence is None or str(evidence.tenant_id) != str(tenant_id):
        raise ValueError("Signature evidence not found")

    evidence.validity_state = "INVALIDATED"
    db.add(evidence)

    ceremony = await db.get(SignatureCeremony, evidence.ceremony_id)
    if ceremony:
        ceremony.state = "SIGNATURE_PENDING"

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=evidence.ceremony_id,
        event_type=EventType.SIGNATURE_INVALIDATED,
        schema_version="1.0.1",
        payload_json={
            "evidence_id": str(evidence_id),
            "reason": reason,
        },
    )
    db.add(outbox)
    return evidence_id


async def mark_fully_executed(
    db: AsyncSession,
    *,
    ceremony_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> uuid.UUID:
    ceremony = await db.get(SignatureCeremony, ceremony_id)
    if ceremony is None or str(ceremony.tenant_id) != str(tenant_id):
        raise ValueError("Ceremony not found")
    if ceremony.state != "SIGNATURE_PENDING":
        raise ValueError(f"Cannot complete from state {ceremony.state}")

    signers = (
        await db.execute(
            select(SignerRequirement).where(
                SignerRequirement.ceremony_id == ceremony_id,
                SignerRequirement.tenant_id == tenant_id,
                SignerRequirement.required == True,
            )
        )
    ).scalars().all()

    valid_evidences = (
        await db.execute(
            select(SignatureEvidenceRef).where(
                SignatureEvidenceRef.ceremony_id == ceremony_id,
                SignatureEvidenceRef.tenant_id == tenant_id,
                SignatureEvidenceRef.validity_state == "VALID",
            )
        )
    ).scalars().all()

    signed_requirement_ids = {e.signer_requirement_id for e in valid_evidences}
    required_ids = {s.id for s in signers}
    if not required_ids.issubset(signed_requirement_ids):
        raise ValueError("Not all required signers have applied valid signatures")

    ceremony.state = "FULLY_EXECUTED"

    package = await db.get(EngagementPackage, ceremony.package_id)
    if package:
        wf_result = await db.execute(
            select(RetainerWorkflow).where(RetainerWorkflow.id == package.workflow_id)
        )
        workflow = wf_result.scalars().first()
        if workflow:
            workflow.state = EngagementState.FULLY_EXECUTED
            workflow.version = workflow.version + 1

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=ceremony.package_id,
        event_type=EventType.PACKAGE_FULLY_EXECUTED,
        schema_version="1.0.1",
        payload_json={
            "ceremony_id": str(ceremony_id),
            "signature_count": len(valid_evidences),
        },
    )
    db.add(outbox)
    return ceremony_id
