"""BP-06 Communications & Expiration domain services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from retainer_contracts.events import EventType
from retainer_contracts.states import EngagementState
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ReminderAttempt,
    ReminderSchedule,
    RetainerOutboxEvent,
    RetainerWorkflow,
)


async def create_reminder_schedule(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    tenant_id: uuid.UUID,
    policy_version_id: uuid.UUID,
    max_attempts: int = 5,
    next_due_at: datetime | None = None,
) -> uuid.UUID:
    workflow = await db.get(RetainerWorkflow, workflow_id)
    if workflow is None or str(workflow.tenant_id) != str(tenant_id):
        raise ValueError("Workflow not found")

    schedule_id = uuid.uuid4()
    schedule = ReminderSchedule(
        id=schedule_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        policy_version_id=policy_version_id,
        max_attempts=max_attempts,
        next_due_at=next_due_at,
        state="ACTIVE",
    )
    db.add(schedule)
    return schedule_id


async def send_reminder(
    db: AsyncSession,
    *,
    schedule_id: uuid.UUID,
    tenant_id: uuid.UUID,
    communication_id: uuid.UUID,
    attempt_no: int,
    result: str,
) -> uuid.UUID:
    schedule = await db.get(ReminderSchedule, schedule_id)
    if schedule is None or str(schedule.tenant_id) != str(tenant_id):
        raise ValueError("Schedule not found")

    attempt_id = uuid.uuid4()
    attempt = ReminderAttempt(
        id=attempt_id,
        tenant_id=tenant_id,
        schedule_id=schedule_id,
        communication_id=communication_id,
        attempt_no=attempt_no,
        result=result,
        attempted_at=datetime.now(UTC),
    )
    db.add(attempt)

    if schedule.max_attempts and attempt_no >= schedule.max_attempts:
        schedule.state = "EXHAUSTED"

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=schedule.workflow_id,
        event_type=EventType.ENGAGEMENT_REMINDER_SENT,
        schema_version="1.0.1",
        payload_json={"schedule_id": str(schedule_id), "attempt_no": attempt_no, "result": result},
    )
    db.add(outbox)
    return attempt_id


async def suppress_reminders(
    db: AsyncSession,
    *,
    schedule_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> uuid.UUID:
    schedule = await db.get(ReminderSchedule, schedule_id)
    if schedule is None or str(schedule.tenant_id) != str(tenant_id):
        raise ValueError("Schedule not found")
    schedule.state = "SUPPRESSED"
    db.add(schedule)

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=schedule.workflow_id,
        event_type=EventType.ENGAGEMENT_REMINDER_SUPPRESSED,
        schema_version="1.0.1",
        payload_json={"schedule_id": str(schedule_id)},
    )
    db.add(outbox)
    return schedule_id


async def expire_engagement(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> uuid.UUID:
    workflow = await db.get(RetainerWorkflow, workflow_id)
    if workflow is None or str(workflow.tenant_id) != str(tenant_id):
        raise ValueError("Workflow not found")
    if workflow.state in (EngagementState.ACTIVATED, EngagementState.DECLINED_OR_EXPIRED):
        raise ValueError(f"Cannot expire from state {workflow.state}")

    workflow.state = EngagementState.DECLINED_OR_EXPIRED
    workflow.version = workflow.version + 1

    outbox = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow_id,
        event_type=EventType.ENGAGEMENT_EXPIRED,
        schema_version="1.0.1",
        payload_json={"workflow_id": str(workflow_id)},
    )
    db.add(outbox)
    return workflow_id
