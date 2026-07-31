"""Representation decision domain logic.

Handles attorney-attributable decisions to approve, decline, or defer
representation. Enforces authority, state guards, and emits events.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from retainer_contracts.errors import ErrorCode
from retainer_contracts.events import EventType
from retainer_contracts.states import EngagementState
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RepresentationDecision, RetainerOutboxEvent, RetainerWorkflow


async def record_representation_decision(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    tenant_id: uuid.UUID,
    attorney_actor_id: str,
    authority_record_id: uuid.UUID,
    outcome: str,
    scope_json: dict,
    supersedes_id: uuid.UUID | None = None,
    correlation_id: uuid.UUID | None = None,
) -> uuid.UUID:
    workflow = await db.get(RetainerWorkflow, workflow_id)
    if workflow is None:
        raise ValueError(f"Workflow {workflow_id} not found")
    if str(workflow.tenant_id) != str(tenant_id):
        raise ValueError(ErrorCode.RET_TENANT_MISMATCH)
    if workflow.state != EngagementState.NOT_STARTED:
        raise ValueError(
            f"Decision not allowed from state {workflow.state}. "
            f"Must be {EngagementState.NOT_STARTED}"
        )

    if supersedes_id:
        previous = await db.get(RepresentationDecision, supersedes_id)
        if previous is None or str(previous.matter_candidate_id) != str(
            workflow.matter_candidate_id
        ):
            raise ValueError("Invalid supersedes_id")

    now = datetime.now(UTC)
    decision_id = uuid.uuid4()

    if outcome == "DEFERRED":
        new_state = EngagementState.NOT_STARTED
    elif outcome == "DECLINED":
        new_state = EngagementState.DECLINED_OR_EXPIRED
    else:
        new_state = EngagementState.ATTORNEY_APPROVAL_RECORDED

    decision = RepresentationDecision(
        id=decision_id,
        tenant_id=tenant_id,
        matter_candidate_id=workflow.matter_candidate_id,
        outcome=outcome,
        scope_json=scope_json,
        attorney_actor_id=attorney_actor_id,
        authority_record_id=authority_record_id,
        supersedes_id=supersedes_id,
        decided_at=now,
    )
    db.add(decision)

    workflow.state = new_state
    workflow.version = workflow.version + 1
    workflow.representation_decision_id = decision_id

    if outcome == "APPROVED":
        event_type = EventType.REPRESENTATION_APPROVED_BY_ATTORNEY
    elif outcome == "DECLINED":
        event_type = EventType.REPRESENTATION_DECLINED_BY_ATTORNEY
    else:
        event_type = EventType.REPRESENTATION_APPROVED_BY_ATTORNEY

    outbox_event = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow_id,
        event_type=event_type,
        schema_version="1.0.1",
        payload_json={
            "workflow_id": str(workflow_id),
            "decision_id": str(decision_id),
            "outcome": outcome,
            "attorney_actor_id": attorney_actor_id,
        },
    )
    db.add(outbox_event)

    return decision_id
