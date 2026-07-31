"""v1.1 Capability Addendum — domain services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from retainer_contracts.events import EventType
from retainer_contracts.states import EngagementState
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ClientExperienceProjection,
    EngagementOutcome,
    InformationRequestItem,
    InformationSubmission,
    MissingInformationRequest,
    RetainerOutboxEvent,
    RetainerWorkflow,
    ReviewWorkItem,
)

CATEGORIES = ["IDENTITY", "INCIDENT", "INSURANCE", "PARTY_INFORMATION", "REPRESENTATIVE_AUTHORITY", "DOCUMENT", "CONTACT", "OTHER"]
OUTCOME_CLASSES = ["ACTIVATED", "CLIENT_DECLINED", "FIRM_WITHDREW", "EXPIRED_NO_RESPONSE", "SUPERSEDED", "OTHER"]
DISPLAY_STATES = {
    EngagementState.NOT_STARTED: "AGREEMENT_BEING_PREPARED",
    EngagementState.ATTORNEY_APPROVAL_RECORDED: "AGREEMENT_BEING_PREPARED",
    EngagementState.CONFLICT_REVIEW_PENDING: "AGREEMENT_BEING_PREPARED",
    EngagementState.CONFLICT_HOLD: "AGREEMENT_BEING_PREPARED",
    EngagementState.PACKAGE_PREPARATION: "AGREEMENT_BEING_PREPARED",
    EngagementState.DELIVERY_AUTHORIZED: "READY_TO_REVIEW",
    EngagementState.DELIVERED: "READY_TO_REVIEW",
    EngagementState.CLIENT_REVIEW: "READY_TO_REVIEW",
    EngagementState.SIGNATURE_PENDING: "YOUR_ACTION_REQUIRED",
    EngagementState.FULLY_EXECUTED: "COMPLETED_COPY_READY",
    EngagementState.ACTIVATION_PENDING: "COMPLETED_COPY_READY",
    EngagementState.ACTIVATED: "ENGAGEMENT_COMPLETED",
    EngagementState.DECLINED_OR_EXPIRED: "NO_FURTHER_ACTION",
}


async def create_request_items(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    tenant_id: uuid.UUID,
    items: list[dict],
) -> list[uuid.UUID]:
    req = await db.get(MissingInformationRequest, request_id)
    if req is None or str(req.tenant_id) != str(tenant_id):
        raise ValueError("Request not found")

    ids = []
    for item in items:
        ri = InformationRequestItem(
            id=uuid.uuid4(), tenant_id=tenant_id, request_id=request_id,
            item_key=item["item_key"], description=item.get("description", ""),
            category=item.get("category", "OTHER"), required=item.get("required", True),
        )
        db.add(ri)
        ids.append(ri.id)
    return ids


async def submit_information(
    db: AsyncSession,
    *,
    request_item_id: uuid.UUID,
    tenant_id: uuid.UUID,
    submitted_by_actor_id: str,
    content: str,
    content_type: str = "TEXT",
) -> uuid.UUID:
    item = await db.get(InformationRequestItem, request_item_id)
    if item is None or str(item.tenant_id) != str(tenant_id):
        raise ValueError("Request item not found")
    item.status = "FULFILLED"
    item.fulfilled_at = datetime.now(UTC)
    db.add(item)

    sub_id = uuid.uuid4()
    sub = InformationSubmission(
        id=sub_id, tenant_id=tenant_id, request_item_id=request_item_id,
        submitted_by_actor_id=submitted_by_actor_id, content=content, content_type=content_type,
    )
    db.add(sub)

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(), tenant_id=tenant_id, aggregate_id=request_item_id,
        event_type=EventType.ENGAGEMENT_QUESTION_RECEIVED, schema_version="1.0.1",
        payload_json={"item_id": str(request_item_id), "status": "FULFILLED"},
    )
    db.add(outbox)
    return sub_id


async def verify_submission(
    db: AsyncSession,
    *,
    submission_id: uuid.UUID,
    tenant_id: uuid.UUID,
    verified_by_actor_id: str,
    status: str = "VERIFIED",
) -> uuid.UUID:
    sub = await db.get(InformationSubmission, submission_id)
    if sub is None or str(sub.tenant_id) != str(tenant_id):
        raise ValueError("Submission not found")
    sub.verification_status = status
    sub.verified_by_actor_id = verified_by_actor_id
    sub.verified_at = datetime.now(UTC)
    db.add(sub)
    return submission_id


async def record_engagement_outcome(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    tenant_id: uuid.UUID,
    outcome_class: str,
    friction_reason: str | None = None,
    evidence_classification: str = "SYSTEM_OBSERVED",
    stated_by_actor_id: str | None = None,
    recorded_by_actor_id: str = "system",
    notes: str | None = None,
) -> uuid.UUID:
    outcome_id = uuid.uuid4()
    outcome = EngagementOutcome(
        id=outcome_id, tenant_id=tenant_id, workflow_id=workflow_id,
        outcome_class=outcome_class, friction_reason=friction_reason,
        evidence_classification=evidence_classification,
        stated_by_actor_id=stated_by_actor_id, recorded_by_actor_id=recorded_by_actor_id,
        notes=notes,
    )
    db.add(outcome)

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(), tenant_id=tenant_id, aggregate_id=workflow_id,
        event_type=EventType.ENGAGEMENT_EXPIRED, schema_version="1.0.1",
        payload_json={"outcome_class": outcome_class, "friction_reason": friction_reason},
    )
    db.add(outbox)
    return outcome_id


async def build_client_experience_projection(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    tenant_id: uuid.UUID,
    recipient_party_role_id: uuid.UUID | str,
) -> uuid.UUID:
    if isinstance(recipient_party_role_id, str):
        recipient_party_role_id = uuid.UUID(recipient_party_role_id)
    workflow = await db.get(RetainerWorkflow, workflow_id)
    if workflow is None or str(workflow.tenant_id) != str(tenant_id):
        raise ValueError("Workflow not found")

    display = DISPLAY_STATES.get(workflow.state, "AGREEMENT_BEING_PREPARED")
    actions = []
    if workflow.state == EngagementState.DELIVERED:
        actions = ["VIEW_DOCUMENTS", "ASK_QUESTION", "GRANT_CONSENT", "DECLINE"]
    elif workflow.state == EngagementState.SIGNATURE_PENDING:
        actions = ["VIEW_DOCUMENTS", "SIGN", "ASK_QUESTION"]
    elif workflow.state == EngagementState.FULLY_EXECUTED:
        actions = ["VIEW_DOCUMENTS", "VIEW_COMPLETED_COPY"]

    proj_id = uuid.uuid4()
    proj = ClientExperienceProjection(
        id=proj_id, tenant_id=tenant_id, workflow_id=workflow_id,
        recipient_party_role_id=recipient_party_role_id,
        display_state=display, primary_action=actions[0] if actions else None,
        allowed_actions=actions,
    )
    db.add(proj)
    return proj_id


async def pause_work_item(
    db: AsyncSession, *, item_id: uuid.UUID, tenant_id: uuid.UUID, reason: str,
) -> uuid.UUID:
    item = await db.get(ReviewWorkItem, item_id)
    if item is None or str(item.tenant_id) != str(tenant_id):
        raise ValueError("Work item not found")
    item.state = "PAUSED"
    db.add(item)
    return item_id


async def resume_work_item(
    db: AsyncSession, *, item_id: uuid.UUID, tenant_id: uuid.UUID,
) -> uuid.UUID:
    item = await db.get(ReviewWorkItem, item_id)
    if item is None or str(item.tenant_id) != str(tenant_id):
        raise ValueError("Work item not found")
    item.state = "PENDING"
    db.add(item)
    return item_id


async def reassign_work_item(
    db: AsyncSession, *, item_id: uuid.UUID, tenant_id: uuid.UUID, new_actor_id: str,
) -> uuid.UUID:
    item = await db.get(ReviewWorkItem, item_id)
    if item is None or str(item.tenant_id) != str(tenant_id):
        raise ValueError("Work item not found")
    item.assigned_actor_id = new_actor_id
    db.add(item)
    return item_id
