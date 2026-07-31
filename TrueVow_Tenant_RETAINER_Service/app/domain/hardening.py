"""BP-08 Hardening — policy enforcement and audit compliance."""

from __future__ import annotations

import uuid

from retainer_contracts.states import EngagementState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditEvent,
    AuthorityEvaluation,
    ConflictReview,
    RepresentationDecision,
    RetainerWorkflow,
)

CALIFORNIA_V1_POLICY = {
    "jurisdiction": "CA",
    "named_attorney_approval": True,
    "named_attorney_conflict_clearance": True,
    "named_attorney_activation": True,
    "ai_authority_path": False,
    "ai_legal_explanation": False,
}


async def validate_policy_compliance(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> dict:
    workflow = await db.get(RetainerWorkflow, workflow_id)
    if workflow is None or str(workflow.tenant_id) != str(tenant_id):
        raise ValueError("Workflow not found")

    violations = []

    if workflow.state in (EngagementState.ATTORNEY_APPROVAL_RECORDED,):
        decision_result = await db.execute(
            select(RepresentationDecision).where(RepresentationDecision.id == workflow.representation_decision_id)
        )
        decision = decision_result.scalars().first()
        if decision:
            auth_evals = (await db.execute(
                select(AuthorityEvaluation).where(
                    AuthorityEvaluation.workflow_id == workflow_id,
                    AuthorityEvaluation.authority_class == "ATTY_AUTH",
                )
            )).scalars().all()
            if not auth_evals:
                violations.append("MISSING_ATTORNEY_AUTHORITY_EVIDENCE")

    if workflow.state in (EngagementState.PACKAGE_PREPARATION,):
        conflict_result = await db.execute(
            select(ConflictReview).where(ConflictReview.id == workflow.conflict_review_id)
        )
        conflict = conflict_result.scalars().first()
        if conflict and conflict.outcome == "CLEARED":
            auth_evals = (await db.execute(
                select(AuthorityEvaluation).where(
                    AuthorityEvaluation.workflow_id == workflow_id,
                    AuthorityEvaluation.action == "clear_conflict_review",
                    AuthorityEvaluation.authority_class == "ATTY_AUTH",
                )
            )).scalars().all()
            if not auth_evals:
                violations.append("MISSING_ATTORNEY_CONFLICT_CLEARANCE")

    audit_events = (await db.execute(
        select(AuditEvent).where(AuditEvent.workflow_id == workflow_id)
    )).scalars().all()

    ai_attempts = [e for e in audit_events if e.actor_role in ("ai_agent", "system") and e.result == "denied"]
    return {
        "workflow_id": str(workflow_id),
        "state": workflow.state,
        "jurisdiction": "CA",
        "violations": violations,
        "ai_blocked_attempts": len(ai_attempts),
        "compliant": len(violations) == 0,
    }


async def get_workflow_health(
    db: AsyncSession,
    *,
    workflow_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> dict:
    workflow = await db.get(RetainerWorkflow, workflow_id)
    if workflow is None or str(workflow.tenant_id) != str(tenant_id):
        raise ValueError("Workflow not found")

    return {
        "workflow_id": str(workflow_id),
        "state": workflow.state,
        "version": workflow.version,
        "has_representation": workflow.representation_decision_id is not None,
        "has_conflict_review": workflow.conflict_review_id is not None,
        "has_package": workflow.engagement_package_id is not None,
        "has_activation_checklist": workflow.activation_checklist_id is not None,
        "is_activated": workflow.activated_matter_id is not None,
    }
