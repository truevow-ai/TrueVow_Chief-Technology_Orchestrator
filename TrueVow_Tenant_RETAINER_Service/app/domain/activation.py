"""BP-07 Activation and TRACE Handoff domain services."""

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
    ClientPortalAccess,
    RetainerOutboxEvent,
    RetainerWorkflow,
)


async def create_activation_checklist(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    tenant_id: uuid.UUID,
    policy_version_id: uuid.UUID,
    items: list[dict],
) -> uuid.UUID:
    workflow = await db.get(RetainerWorkflow, workflow_id)
    if workflow is None or str(workflow.tenant_id) != str(tenant_id):
        raise ValueError("Workflow not found")
    if workflow.state != EngagementState.FULLY_EXECUTED:
        raise ValueError(f"Activation checklist requires FULLY_EXECUTED, not {workflow.state}")

    checklist_id = uuid.uuid4()
    checklist = ActivationChecklist(
        id=checklist_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        policy_version_id=policy_version_id,
        state="PENDING",
        version=1,
    )
    db.add(checklist)

    for item in items:
        ci = ActivationChecklistItem(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            checklist_id=checklist_id,
            control_id=item["control_id"],
            required=item.get("required", True),
            result="PENDING",
        )
        db.add(ci)

    workflow.state = EngagementState.ACTIVATION_PENDING
    workflow.version = workflow.version + 1
    workflow.activation_checklist_id = checklist_id

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow_id,
        event_type=EventType.MATTER_ACTIVATION_AUTHORIZED,
        schema_version="1.0.1",
        payload_json={"checklist_id": str(checklist_id), "item_count": len(items)},
    )
    db.add(outbox)
    return checklist_id


async def authorize_activation(
    db: AsyncSession,
    *,
    checklist_id: uuid.UUID,
    tenant_id: uuid.UUID,
    attorney_actor_id: str,
) -> uuid.UUID:
    checklist = await db.get(ActivationChecklist, checklist_id)
    if checklist is None or str(checklist.tenant_id) != str(tenant_id):
        raise ValueError("Checklist not found")

    items = (
        await db.execute(
            select(ActivationChecklistItem).where(
                ActivationChecklistItem.checklist_id == checklist_id,
                ActivationChecklistItem.required == True,
            )
        )
    ).scalars().all()

    all_pass = all(item.result == "PASSED" for item in items)
    if not all_pass:
        raise ValueError("Not all required checklist items have passed")

    checklist.state = "AUTHORIZED"

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=checklist.workflow_id,
        event_type=EventType.MATTER_ACTIVATION_AUTHORIZED,
        schema_version="1.0.1",
        payload_json={"checklist_id": str(checklist_id), "actor_id": attorney_actor_id},
    )
    db.add(outbox)
    return checklist_id


async def evaluate_checklist_item(
    db: AsyncSession,
    *,
    item_id: uuid.UUID,
    tenant_id: uuid.UUID,
    result: str,
    evidence_refs: list | None = None,
) -> uuid.UUID:
    item = await db.get(ActivationChecklistItem, item_id)
    if item is None or str(item.tenant_id) != str(tenant_id):
        raise ValueError("Checklist item not found")
    item.result = result
    if evidence_refs:
        item.evidence_refs_json = evidence_refs
    item.evaluated_at = datetime.now(UTC)
    db.add(item)
    return item_id


async def confirm_matter_activated(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    tenant_id: uuid.UUID,
    activated_matter_id: uuid.UUID,
) -> uuid.UUID:
    workflow = await db.get(RetainerWorkflow, workflow_id)
    if workflow is None or str(workflow.tenant_id) != str(tenant_id):
        raise ValueError("Workflow not found")
    if workflow.state != EngagementState.ACTIVATION_PENDING:
        raise ValueError(f"Activation requires ACTIVATION_PENDING, not {workflow.state}")

    workflow.state = EngagementState.ACTIVATED
    workflow.version = workflow.version + 1
    workflow.activated_matter_id = activated_matter_id

    portal_result = await db.execute(
        select(ClientPortalAccess).where(
            ClientPortalAccess.workflow_id == workflow_id,
            ClientPortalAccess.state.in_(["PENDING_INVITATION", "ACTIVE"]),
        )
    )
    portal_access = portal_result.scalars().first()
    if portal_access:
        portal_access.state = "ACTIVE"
        existing = set(portal_access.scopes or [])
        action_scopes = {"ENGAGEMENT_QUESTION", "ENGAGEMENT_SIGN", "ENGAGEMENT_DECLINE"}
        portal_access.scopes = list(existing - action_scopes | {"ENGAGEMENT_HISTORY"})

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow_id,
        event_type=EventType.MATTER_ACTIVATED,
        schema_version="1.0.1",
        payload_json={"workflow_id": str(workflow_id), "matter_id": str(activated_matter_id)},
    )
    db.add(outbox)
    return workflow_id
