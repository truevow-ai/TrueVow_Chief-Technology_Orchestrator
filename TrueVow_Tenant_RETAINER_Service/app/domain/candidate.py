"""Candidate import domain logic.

Handles INTAKE candidate handoffs, creating RETAINER workflows with
idempotency, tenant validation, and version-conflict detection.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from retainer_contracts.errors import ErrorCode
from retainer_contracts.events import EventType
from retainer_contracts.states import EngagementState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    RetainerIdempotencyKey,
    RetainerInboxEvent,
    RetainerOutboxEvent,
    RetainerWorkflow,
)


def _hash_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


async def import_candidate(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    matter_candidate_id: uuid.UUID,
    candidate_version: int,
    source_event_id: uuid.UUID,
    submitted_by_actor_id: str,
    source_event_ids: list[uuid.UUID],
    correlation_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    payload_hash = _hash_payload({
        "matter_candidate_id": str(matter_candidate_id),
        "candidate_version": candidate_version,
        "source_event_ids": [str(e) for e in source_event_ids],
    })

    inbox_event_id = uuid.uuid4()
    now = datetime.now(UTC)

    existing_inbox = await db.get(RetainerInboxEvent, inbox_event_id)
    if existing_inbox:
        raise ValueError("Duplicate event_id in inbox")

    existing_workflow = (
        await db.execute(
            select(RetainerWorkflow).where(
                RetainerWorkflow.tenant_id == tenant_id,
                RetainerWorkflow.matter_candidate_id == matter_candidate_id,
                RetainerWorkflow.candidate_version == candidate_version,
            )
        )
    ).scalar_one_or_none()

    if existing_workflow:
        inbox = RetainerInboxEvent(
            event_id=inbox_event_id,
            tenant_id=tenant_id,
            event_type=EventType.CANDIDATE_SUBMITTED_FOR_REPRESENTATION_REVIEW,
            schema_version="1.0.0",
            payload_hash=payload_hash,
            processed_at=now,
            result="duplicate",
        )
        db.add(inbox)
        await db.flush()
        return existing_workflow.id, inbox_event_id

    max_version = (
        await db.execute(
            select(RetainerWorkflow.candidate_version).where(
                RetainerWorkflow.tenant_id == tenant_id,
                RetainerWorkflow.matter_candidate_id == matter_candidate_id,
            )
        )
    ).scalar_one_or_none()

    if max_version is not None and candidate_version <= max_version:
        inbox = RetainerInboxEvent(
            event_id=inbox_event_id,
            tenant_id=tenant_id,
            event_type=EventType.CANDIDATE_SUBMITTED_FOR_REPRESENTATION_REVIEW,
            schema_version="1.0.0",
            payload_hash=payload_hash,
            processed_at=now,
            result="version_conflict",
            error_code=ErrorCode.RET_CANDIDATE_VERSION_CONFLICT,
        )
        db.add(inbox)
        await db.flush()
        raise ValueError(
            f"Version conflict: received v{candidate_version}, latest is v{max_version}"
        )

    workflow_id = uuid.uuid4()
    workflow = RetainerWorkflow(
        id=workflow_id,
        tenant_id=tenant_id,
        matter_candidate_id=matter_candidate_id,
        candidate_version=candidate_version,
        state=EngagementState.NOT_STARTED,
        version=1,
    )
    db.add(workflow)

    inbox = RetainerInboxEvent(
        event_id=inbox_event_id,
        tenant_id=tenant_id,
        event_type=EventType.CANDIDATE_SUBMITTED_FOR_REPRESENTATION_REVIEW,
        schema_version="1.0.0",
        payload_hash=payload_hash,
        processed_at=now,
        result="created",
    )
    db.add(inbox)

    outbox_event_id = uuid.uuid4()
    outbox = RetainerOutboxEvent(
        event_id=outbox_event_id,
        tenant_id=tenant_id,
        aggregate_id=workflow_id,
        event_type=EventType.ENGAGEMENT_WORKFLOW_STARTED,
        schema_version="1.0.0",
        payload_json={
            "workflow_id": str(workflow_id),
            "matter_candidate_id": str(matter_candidate_id),
            "candidate_version": candidate_version,
        },
    )
    db.add(outbox)

    idempotency_key = str(inbox_event_id)
    idemp_record = RetainerIdempotencyKey(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        command_type="import_candidate",
        request_hash=payload_hash,
        result_ref=str(workflow_id),
    )
    db.add(idemp_record)

    return workflow_id, inbox_event_id
