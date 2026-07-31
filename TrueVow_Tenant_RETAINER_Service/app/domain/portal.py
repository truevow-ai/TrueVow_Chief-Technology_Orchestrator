"""BP-04 Client Engagement Portal domain services."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from retainer_contracts.events import EventType
from retainer_contracts.states import EngagementState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ClientPortalAccess,
    DeliveryAuthorization,
    EngagementPackage,
    EngagementQuestion,
    ESignConsent,
    PackageDocument,
    RetainerOutboxEvent,
    RetainerWorkflow,
)

ENGAGEMENT_SCOPES = ["ENGAGEMENT_VIEW", "ENGAGEMENT_QUESTION", "ENGAGEMENT_SIGN", "COMPLETED_COPY_DOWNLOAD"]
MATTER_SCOPES = ["MATTER_VIEW", "MATTER_MESSAGE", "MATTER_UPLOAD", "REQUEST_RESPOND", "DOCUMENT_DOWNLOAD"]


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def authorize_delivery(
    db: AsyncSession,
    *,
    package_id: uuid.UUID,
    tenant_id: uuid.UUID,
    authorized_by_actor_id: str,
    authority_record_id: uuid.UUID,
    channel: str = "portal",
    recipient_verified: bool = False,
) -> uuid.UUID:
    package_result = await db.execute(
        select(EngagementPackage).where(
            EngagementPackage.id == package_id,
            EngagementPackage.tenant_id == tenant_id,
        ).with_for_update(),
    )
    package = package_result.scalars().first()
    if package is None:
        raise ValueError("Package not found")

    wf_result = await db.execute(
        select(RetainerWorkflow).where(RetainerWorkflow.id == package.workflow_id)
    )
    workflow = wf_result.scalars().first()
    if workflow is None:
        raise ValueError("Workflow not found")
    if workflow.state != EngagementState.PACKAGE_PREPARATION:
        raise ValueError(f"Delivery requires PACKAGE_PREPARATION, not {workflow.state}")

    auth_id = uuid.uuid4()
    auth = DeliveryAuthorization(
        id=auth_id,
        tenant_id=tenant_id,
        package_id=package_id,
        workflow_id=package.workflow_id,
        authorized_by_actor_id=authorized_by_actor_id,
        authority_record_id=authority_record_id,
        channel=channel,
        recipient_verified=recipient_verified,
    )
    db.add(auth)

    package.status = "LOCKED"
    now = datetime.now(UTC)
    package.locked_at = now

    workflow.state = EngagementState.DELIVERY_AUTHORIZED
    workflow.version = workflow.version + 1

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=package.workflow_id,
        event_type=EventType.PACKAGE_DELIVERY_AUTHORIZED,
        schema_version="1.0.1",
        payload_json={
            "package_id": str(package_id),
            "authorization_id": str(auth_id),
            "channel": channel,
        },
    )
    db.add(outbox)
    return auth_id


async def generate_portal_token(
    db: AsyncSession,
    *,
    package_id: uuid.UUID,
    tenant_id: uuid.UUID,
    prospect_party_role_id: uuid.UUID,
    actor_id: str,
) -> tuple[str, uuid.UUID]:
    package = await db.get(EngagementPackage, package_id)
    if package is None or str(package.tenant_id) != str(tenant_id):
        raise ValueError("Package not found")
    if package.status != "LOCKED":
        raise ValueError("Package must be locked before generating portal token")

    access_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(access_token)
    access_id = uuid.uuid4()
    now = datetime.now(UTC)

    access = ClientPortalAccess(
        id=access_id,
        tenant_id=tenant_id,
        workflow_id=package.workflow_id,
        access_token_hash=token_hash,
        package_id=package_id,
        prospect_party_role_id=prospect_party_role_id,
        state="PENDING_INVITATION",
        scopes=["ENGAGEMENT_VIEW", "ENGAGEMENT_QUESTION", "ENGAGEMENT_SIGN", "COMPLETED_COPY_DOWNLOAD"],
        expires_at=now + timedelta(days=90),
    )
    db.add(access)

    workflow = await db.get(RetainerWorkflow, package.workflow_id)
    if workflow and workflow.state == EngagementState.DELIVERY_AUTHORIZED:
        workflow.state = EngagementState.DELIVERED
        workflow.version = workflow.version + 1

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(), tenant_id=tenant_id, aggregate_id=package.workflow_id,
        event_type=EventType.PACKAGE_DELIVERED, schema_version="1.0.1",
        payload_json={"package_id": str(package_id), "access_id": str(access_id)},
    )
    db.add(outbox)

    return access_token, access_id


async def validate_portal_access(
    db: AsyncSession,
    *,
    access_token: str,
) -> dict:
    token_hash = _hash_token(access_token)
    result = await db.execute(
        select(ClientPortalAccess).where(
            ClientPortalAccess.access_token_hash == token_hash,
            ClientPortalAccess.state.in_(["ACTIVE", "PENDING_INVITATION"]),
        )
    )
    access = result.scalars().first()
    if access is None:
        return {"valid": False}
    if access.expires_at and access.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        return {"valid": False, "reason": "expired"}

    if access.first_accessed_at is None:
        access.first_accessed_at = datetime.now(UTC)

    docs_result = await db.execute(
        select(PackageDocument).where(
            PackageDocument.package_id == access.package_id,
            PackageDocument.tenant_id == access.tenant_id,
        ).order_by(PackageDocument.sequence)
    )
    docs = docs_result.scalars().all()

    consent_result = await db.execute(
        select(ESignConsent).where(
            ESignConsent.portal_access_id == access.id,
            ESignConsent.state == "GRANTED",
        )
    )
    consent = consent_result.scalars().first()

    return {
        "valid": True,
        "access_id": str(access.id),
        "package_id": str(access.package_id),
        "tenant_id": str(access.tenant_id),
        "workflow_id": str(access.workflow_id),
        "prospect_party_role_id": str(access.prospect_party_role_id),
        "scopes": access.scopes or [],
        "documents": [
            {
                "document_version_id": str(d.document_version_id),
                "document_role": d.document_role,
                "document_hash": d.document_hash,
            }
            for d in docs
        ],
        "consent_status": consent.state if consent else None,
    }


async def grant_esign_consent(
    db: AsyncSession,
    *,
    access_token: str,
    prospect_party_role_id: uuid.UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> uuid.UUID:
    token_hash = _hash_token(access_token)
    result = await db.execute(
        select(ClientPortalAccess).where(
            ClientPortalAccess.access_token_hash == token_hash,
            ClientPortalAccess.state.in_(["ACTIVE", "PENDING_INVITATION"]),
        )
    )
    access = result.scalars().first()
    if access is None:
        raise ValueError("Invalid or expired access token")

    existing = await db.execute(
        select(ESignConsent).where(
            ESignConsent.portal_access_id == access.id,
            ESignConsent.state == "GRANTED",
        )
    )
    if existing.scalars().first() is not None:
        raise ValueError("Consent already granted")

    consent_id = uuid.uuid4()
    consent = ESignConsent(
        id=consent_id,
        tenant_id=access.tenant_id,
        workflow_id=access.workflow_id,
        portal_access_id=access.id,
        prospect_party_role_id=prospect_party_role_id,
        state="GRANTED",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(consent)

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=access.tenant_id,
        aggregate_id=access.workflow_id,
        event_type=EventType.ESIGN_CONSENT_GRANTED,
        schema_version="1.0.1",
        payload_json={
            "consent_id": str(consent_id),
            "access_id": str(access.id),
        },
    )
    db.add(outbox)
    return consent_id


async def submit_client_question(
    db: AsyncSession,
    *,
    access_token: str,
    question_text: str,
    document_version_id: uuid.UUID | None = None,
    page_or_clause_ref: str | None = None,
) -> uuid.UUID:
    token_hash = _hash_token(access_token)
    result = await db.execute(
        select(ClientPortalAccess).where(
            ClientPortalAccess.access_token_hash == token_hash,
        )
    )
    access = result.scalars().first()
    if access is None:
        raise ValueError("Invalid access token")

    question_id = uuid.uuid4()
    question = EngagementQuestion(
        id=question_id,
        tenant_id=access.tenant_id,
        workflow_id=access.workflow_id,
        document_version_id=document_version_id,
        page_or_clause_ref=page_or_clause_ref,
        question_text=question_text,
        classification="CLIENT_QUESTION",
        state="RECEIVED",
        submitted_by_actor_id=str(access.prospect_party_role_id),
    )
    db.add(question)

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=access.tenant_id,
        aggregate_id=access.workflow_id,
        event_type=EventType.ENGAGEMENT_QUESTION_RECEIVED,
        schema_version="1.0.1",
        payload_json={
            "question_id": str(question_id),
            "workflow_id": str(access.workflow_id),
        },
    )
    db.add(outbox)
    return question_id


async def record_client_decline(
    db: AsyncSession,
    *,
    access_token: str,
    reason: str | None = None,
) -> uuid.UUID:
    token_hash = _hash_token(access_token)
    result = await db.execute(
        select(ClientPortalAccess).where(
            ClientPortalAccess.access_token_hash == token_hash,
        )
    )
    access = result.scalars().first()
    if access is None:
        raise ValueError("Invalid access token")

    access.state = "DECLINED"
    wf_result = await db.execute(
        select(RetainerWorkflow).where(RetainerWorkflow.id == access.workflow_id)
    )
    workflow = wf_result.scalars().first()
    if workflow is None:
        raise ValueError("Workflow not found")
    workflow.state = EngagementState.DECLINED_OR_EXPIRED
    workflow.version = workflow.version + 1

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=access.tenant_id,
        aggregate_id=access.workflow_id,
        event_type=EventType.ENGAGEMENT_DECLINED_BY_CLIENT,
        schema_version="1.0.1",
        payload_json={
            "workflow_id": str(access.workflow_id),
            "reason": reason,
        },
    )
    db.add(outbox)
    return access.workflow_id
