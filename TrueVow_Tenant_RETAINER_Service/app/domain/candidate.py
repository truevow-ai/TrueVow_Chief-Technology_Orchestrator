"""BP-01 Candidate Review domain services.

Supports: start-review, assign-attorney, request-information, authority
evaluation, and audit event recording. All decisions are authority-gated
and fail closed.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from retainer_contracts.authority import (
    ACTION_AUTHORITY,
    AuthorityAction,
    AuthorityClass,
)
from retainer_contracts.errors import ErrorCode
from retainer_contracts.events import EventType
from retainer_contracts.states import EngagementState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditEvent,
    AuthorityEvaluation,
    CandidateReview,
    ConfigurationResolutionSnapshot,
    MissingInformationRequest,
    RepresentationDecision,
    RetainerIdempotencyKey,
    RetainerInboxEvent,
    RetainerOutboxEvent,
    RetainerWorkflow,
    ReviewWorkItem,
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
) -> tuple[uuid.UUID, uuid.UUID]:
    payload_hash = _hash_payload({
        "matter_candidate_id": str(matter_candidate_id),
        "candidate_version": candidate_version,
        "source_event_ids": [str(e) for e in source_event_ids],
    })
    inbox_event_id = uuid.uuid4()
    now = datetime.now(UTC)
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
            schema_version="1.0.1",
            payload_hash=payload_hash,
            processed_at=now,
            result="duplicate",
        )
        db.add(inbox)
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
            schema_version="1.0.1",
            payload_hash=payload_hash,
            processed_at=now,
            result="version_conflict",
            error_code=ErrorCode.RET_CANDIDATE_VERSION_CONFLICT,
        )
        db.add(inbox)
        raise ValueError(
            f"Version conflict: v{candidate_version} <= latest v{max_version}"
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
        schema_version="1.0.1",
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
        schema_version="1.0.1",
        payload_json={
            "workflow_id": str(workflow_id),
            "matter_candidate_id": str(matter_candidate_id),
            "candidate_version": candidate_version,
        },
    )
    db.add(outbox)
    idemp_record = RetainerIdempotencyKey(
        tenant_id=tenant_id,
        idempotency_key=str(inbox_event_id),
        command_type="import_candidate",
        request_hash=payload_hash,
        result_ref=str(workflow_id),
    )
    db.add(idemp_record)
    return workflow_id, inbox_event_id


def _evaluate_authority(action: AuthorityAction, role: str | None) -> tuple[AuthorityClass, bool]:
    required = ACTION_AUTHORITY.get(action, AuthorityClass.PROHIBITED)
    if required == AuthorityClass.PROHIBITED:
        return required, False
    if required == AuthorityClass.SYS_ADMIN:
        return required, role == "admin" or role == "service"
    if required == AuthorityClass.ATTY_AUTH:
        return required, role == "attorney"
    if required == AuthorityClass.STAFF_AUTH:
        return required, role in ("staff", "attorney", "admin")
    if required == AuthorityClass.FIRM_POLICY:
        return required, role in ("staff", "attorney", "admin")
    if required == AuthorityClass.CLIENT_AUTH:
        return required, role == "prospective_client"
    return required, False


async def _record_audit(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    workflow_id: uuid.UUID,
    event_type: str,
    actor_id: str,
    actor_role: str | None,
    authority_class: str,
    action: str,
    result: str,
    details: dict | None = None,
) -> None:
    entry = AuditEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        event_type=event_type,
        actor_id=actor_id,
        actor_role=actor_role,
        authority_class=authority_class,
        action=action,
        result=result,
        details=details or {},
    )
    db.add(entry)


async def start_candidate_review(
    db: AsyncSession,
    *,
    candidate_id: uuid.UUID,
    tenant_id: uuid.UUID,
    actor_id: str,
    actor_role: str | None = None,
) -> tuple[uuid.UUID, str]:
    authority, allowed = _evaluate_authority(
        AuthorityAction.REPRESENTATION_PREPARE, actor_role
    )
    if not allowed:
        raise ValueError(ErrorCode.RET_AUTHORITY_MISSING)

    result = await db.execute(
        select(RetainerWorkflow).where(
            RetainerWorkflow.tenant_id == tenant_id,
            RetainerWorkflow.matter_candidate_id == candidate_id,
        ).order_by(RetainerWorkflow.candidate_version.desc())
    )
    workflow = result.scalars().first()
    if workflow is None:
        raise ValueError("Candidate not found")

    await _record_audit(
        db,
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        event_type="authority_check",
        actor_id=actor_id,
        actor_role=actor_role,
        authority_class=authority.value,
        action="start_candidate_review",
        result="allowed",
    )

    existing_review = (
        await db.execute(
            select(CandidateReview).where(
                CandidateReview.tenant_id == tenant_id,
                CandidateReview.workflow_id == workflow.id,
            )
        )
    ).scalar_one_or_none()

    review_id = uuid.uuid4()
    if existing_review:
        existing_review.review_state = "IN_REVIEW"
        existing_review.prepared_by_actor_id = actor_id
        existing_review.prepared_at = datetime.now(UTC)
        existing_review.candidate_version_reviewed = workflow.candidate_version
        review_id = existing_review.id
    else:
        review = CandidateReview(
            id=review_id,
            tenant_id=tenant_id,
            workflow_id=workflow.id,
            review_state="IN_REVIEW",
            prepared_by_actor_id=actor_id,
            prepared_at=datetime.now(UTC),
            candidate_version_reviewed=workflow.candidate_version,
        )
        db.add(review)

    work_item = ReviewWorkItem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        work_type="REVIEW_CANDIDATE",
        assigned_actor_id=actor_id,
        state="PENDING",
    )
    db.add(work_item)

    outbox_event = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow.id,
        event_type=EventType.ENGAGEMENT_WORKFLOW_STARTED,
        schema_version="1.0.1",
        payload_json={
            "workflow_id": str(workflow.id),
            "action": "review_started",
            "actor_id": actor_id,
        },
    )
    db.add(outbox_event)

    return review_id, "IN_REVIEW"


async def assign_responsible_attorney(
    db: AsyncSession,
    *,
    candidate_id: uuid.UUID,
    tenant_id: uuid.UUID,
    attorney_actor_id: str,
    actor_id: str,
    actor_role: str | None = None,
) -> uuid.UUID:
    result = await db.execute(
        select(RetainerWorkflow).where(
            RetainerWorkflow.tenant_id == tenant_id,
            RetainerWorkflow.matter_candidate_id == candidate_id,
        ).order_by(RetainerWorkflow.candidate_version.desc())
    )
    workflow = result.scalars().first()
    if workflow is None:
        raise ValueError("Candidate not found")

    review_result = await db.execute(
        select(CandidateReview).where(
            CandidateReview.tenant_id == tenant_id,
            CandidateReview.workflow_id == workflow.id,
        )
    )
    review = review_result.scalar_one_or_none()
    if review is None:
        raise ValueError("Review not yet started")

    review.responsible_attorney_actor_id = attorney_actor_id
    review.attorney_assigned_at = datetime.now(UTC)

    work_item = ReviewWorkItem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        work_type="ATTORNEY_REVIEW",
        assigned_actor_id=attorney_actor_id,
        state="PENDING",
    )
    db.add(work_item)

    outbox_event = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow.id,
        event_type=EventType.ENGAGEMENT_WORKFLOW_STARTED,
        schema_version="1.0.1",
        payload_json={
            "workflow_id": str(workflow.id),
            "action": "attorney_assigned",
            "attorney_actor_id": attorney_actor_id,
        },
    )
    db.add(outbox_event)

    return review.id


async def request_missing_information(
    db: AsyncSession,
    *,
    candidate_id: uuid.UUID,
    tenant_id: uuid.UUID,
    actor_id: str,
    actor_role: str | None,
    reason: str,
    fields_required: list[str],
) -> uuid.UUID:
    authority, allowed = _evaluate_authority(
        AuthorityAction.REPRESENTATION_PREPARE, actor_role
    )
    if not allowed:
        raise ValueError(ErrorCode.RET_AUTHORITY_MISSING)

    result = await db.execute(
        select(RetainerWorkflow).where(
            RetainerWorkflow.tenant_id == tenant_id,
            RetainerWorkflow.matter_candidate_id == candidate_id,
        ).order_by(RetainerWorkflow.candidate_version.desc())
    )
    workflow = result.scalars().first()
    if workflow is None:
        raise ValueError("Candidate not found")

    request_id = uuid.uuid4()
    info_request = MissingInformationRequest(
        id=request_id,
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        requested_by_actor_id=actor_id,
        reason=reason,
        fields_required=fields_required,
        state="OPEN",
    )
    db.add(info_request)

    return request_id


async def approve_representation(
    db: AsyncSession,
    *,
    candidate_id: uuid.UUID,
    tenant_id: uuid.UUID,
    attorney_actor_id: str,
    authority_record_id: uuid.UUID,
    scope_json: dict,
    policy_snapshot_id: uuid.UUID | None = None,
    actor_role: str | None = None,
) -> uuid.UUID:
    authority, allowed = _evaluate_authority(
        AuthorityAction.REPRESENTATION_DECIDE, actor_role
    )
    if not allowed:
        raise ValueError(ErrorCode.RET_AUTHORITY_MISSING)

    result = await db.execute(
        select(RetainerWorkflow)
        .where(
            RetainerWorkflow.tenant_id == tenant_id,
            RetainerWorkflow.matter_candidate_id == candidate_id,
        )
        .order_by(RetainerWorkflow.candidate_version.desc())
        .with_for_update(),
    )
    workflow = result.scalars().first()
    if workflow is None:
        raise ValueError("Candidate not found")
    current_state = workflow.state
    if current_state != EngagementState.NOT_STARTED:
        raise ValueError(
            f"Decision not allowed from state {current_state}"
        )

    await _record_audit(
        db,
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        event_type="approve_representation",
        actor_id=attorney_actor_id,
        actor_role=actor_role,
        authority_class=authority.value,
        action="approve_representation",
        result="allowed",
    )

    now = datetime.now(UTC)
    decision_id = uuid.uuid4()
    decision = RepresentationDecision(
        id=decision_id,
        tenant_id=tenant_id,
        matter_candidate_id=candidate_id,
        outcome="APPROVED",
        scope_json=scope_json,
        attorney_actor_id=attorney_actor_id,
        authority_record_id=authority_record_id,
        decided_at=now,
    )
    db.add(decision)

    workflow.state = EngagementState.ATTORNEY_APPROVAL_RECORDED
    workflow.version = workflow.version + 1
    workflow.representation_decision_id = decision_id

    if policy_snapshot_id:
        snapshot = ConfigurationResolutionSnapshot(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            workflow_id=workflow.id,
            resolution_type="policy_snapshot",
            policy_version_id=policy_snapshot_id,
        )
        db.add(snapshot)

    auth_eval = AuthorityEvaluation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        action="approve_representation",
        actor_id=attorney_actor_id,
        authority_class=AuthorityClass.ATTY_AUTH.value,
        result="APPROVED",
        policy_snapshot_id=policy_snapshot_id,
    )
    db.add(auth_eval)

    outbox_event = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow.id,
        event_type=EventType.REPRESENTATION_APPROVED_BY_ATTORNEY,
        schema_version="1.0.1",
        payload_json={
            "workflow_id": str(workflow.id),
            "decision_id": str(decision_id),
            "outcome": "APPROVED",
            "attorney_actor_id": attorney_actor_id,
            "candidate_version": workflow.candidate_version,
            "policy_snapshot_id": str(policy_snapshot_id) if policy_snapshot_id else None,
        },
    )
    db.add(outbox_event)

    return decision_id


async def defer_representation(
    db: AsyncSession,
    *,
    candidate_id: uuid.UUID,
    tenant_id: uuid.UUID,
    attorney_actor_id: str,
    authority_record_id: uuid.UUID,
    scope_json: dict,
    policy_snapshot_id: uuid.UUID | None = None,
    actor_role: str | None = None,
) -> uuid.UUID:
    authority, allowed = _evaluate_authority(
        AuthorityAction.REPRESENTATION_DECIDE, actor_role
    )
    if not allowed:
        raise ValueError(ErrorCode.RET_AUTHORITY_MISSING)

    result = await db.execute(
        select(RetainerWorkflow)
        .where(
            RetainerWorkflow.tenant_id == tenant_id,
            RetainerWorkflow.matter_candidate_id == candidate_id,
        )
        .order_by(RetainerWorkflow.candidate_version.desc())
        .with_for_update(),
    )
    workflow = result.scalars().first()
    if workflow is None:
        raise ValueError("Candidate not found")
    current_state = workflow.state
    if current_state != EngagementState.NOT_STARTED:
        raise ValueError(
            f"Decision not allowed from state {current_state}"
        )

    await _record_audit(
        db,
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        event_type="defer_representation",
        actor_id=attorney_actor_id,
        actor_role=actor_role,
        authority_class=authority.value,
        action="defer_representation",
        result="allowed",
    )

    now = datetime.now(UTC)
    decision_id = uuid.uuid4()
    decision = RepresentationDecision(
        id=decision_id,
        tenant_id=tenant_id,
        matter_candidate_id=candidate_id,
        outcome="DEFERRED",
        scope_json=scope_json,
        attorney_actor_id=attorney_actor_id,
        authority_record_id=authority_record_id,
        decided_at=now,
    )
    db.add(decision)

    if policy_snapshot_id:
        snapshot = ConfigurationResolutionSnapshot(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            workflow_id=workflow.id,
            resolution_type="policy_snapshot",
            policy_version_id=policy_snapshot_id,
        )
        db.add(snapshot)

    auth_eval = AuthorityEvaluation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        action="defer_representation",
        actor_id=attorney_actor_id,
        authority_class=AuthorityClass.ATTY_AUTH.value,
        result="DEFERRED",
        policy_snapshot_id=policy_snapshot_id,
    )
    db.add(auth_eval)

    outbox_event = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow.id,
        event_type=EventType.REPRESENTATION_APPROVED_BY_ATTORNEY,
        schema_version="1.0.1",
        payload_json={
            "workflow_id": str(workflow.id),
            "decision_id": str(decision_id),
            "outcome": "DEFERRED",
            "attorney_actor_id": attorney_actor_id,
            "candidate_version": workflow.candidate_version,
            "policy_snapshot_id": str(policy_snapshot_id) if policy_snapshot_id else None,
        },
    )
    db.add(outbox_event)

    return decision_id


async def decline_representation(
    db: AsyncSession,
    *,
    candidate_id: uuid.UUID,
    tenant_id: uuid.UUID,
    attorney_actor_id: str,
    authority_record_id: uuid.UUID,
    actor_role: str | None = None,
) -> uuid.UUID:
    authority, allowed = _evaluate_authority(
        AuthorityAction.REPRESENTATION_DECIDE, actor_role
    )
    if not allowed:
        raise ValueError(ErrorCode.RET_AUTHORITY_MISSING)

    result = await db.execute(
        select(RetainerWorkflow)
        .where(
            RetainerWorkflow.tenant_id == tenant_id,
            RetainerWorkflow.matter_candidate_id == candidate_id,
        )
        .order_by(RetainerWorkflow.candidate_version.desc())
        .with_for_update(),
    )
    workflow = result.scalars().first()
    if workflow is None:
        raise ValueError("Candidate not found")
    current_state = workflow.state
    if current_state != EngagementState.NOT_STARTED:
        raise ValueError(
            f"Decision not allowed from state {current_state}"
        )

    await _record_audit(
        db,
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        event_type="decline_representation",
        actor_id=attorney_actor_id,
        actor_role=actor_role,
        authority_class=authority.value,
        action="decline_representation",
        result="allowed",
    )

    decision_id = uuid.uuid4()
    decision = RepresentationDecision(
        id=decision_id,
        tenant_id=tenant_id,
        matter_candidate_id=candidate_id,
        outcome="DECLINED",
        scope_json={},
        attorney_actor_id=attorney_actor_id,
        authority_record_id=authority_record_id,
        decided_at=datetime.now(UTC),
    )
    db.add(decision)

    workflow.state = EngagementState.DECLINED_OR_EXPIRED
    workflow.version = workflow.version + 1
    workflow.representation_decision_id = decision_id

    auth_eval = AuthorityEvaluation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow.id,
        action="decline_representation",
        actor_id=attorney_actor_id,
        authority_class=AuthorityClass.ATTY_AUTH.value,
        result="DECLINED",
    )
    db.add(auth_eval)

    outbox_event = RetainerOutboxEvent(
        event_id=uuid.uuid4(),
        tenant_id=tenant_id,
        aggregate_id=workflow.id,
        event_type=EventType.REPRESENTATION_DECLINED_BY_ATTORNEY,
        schema_version="1.0.1",
        payload_json={
            "workflow_id": str(workflow.id),
            "decision_id": str(decision_id),
            "outcome": "DECLINED",
            "attorney_actor_id": attorney_actor_id,
        },
    )
    db.add(outbox_event)

    return decision_id
