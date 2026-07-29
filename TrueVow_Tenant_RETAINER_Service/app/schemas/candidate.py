"""Request and response schemas for candidate and representation endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field
from retainer_contracts.states import EngagementState


class CandidateHandoffRequest(BaseModel):
    tenant_id: uuid.UUID
    matter_candidate_id: uuid.UUID
    candidate_version: Annotated[int, Field(ge=1)]
    prospective_client_party_role_ids: list[uuid.UUID] = Field(min_length=1)
    intake_session_ids: list[uuid.UUID]
    qualification_assessment_id: uuid.UUID | None = None
    consent_record_ids: list[uuid.UUID]
    communication_ids: list[uuid.UUID]
    source_event_ids: list[uuid.UUID] = Field(min_length=1)
    submitted_by_actor_id: str = Field(min_length=1)
    submitted_at: datetime


class CandidateImportResponse(BaseModel):
    workflow_id: uuid.UUID
    state: EngagementState
    candidate_version: int
    correlation_id: str | None = None


class RepresentationDecisionRequest(BaseModel):
    outcome: Annotated[str, Field(pattern="^(APPROVED|DECLINED|DEFERRED)$")]
    scope_json: dict = Field(default_factory=dict)
    authority_record_id: uuid.UUID
    supersedes_id: uuid.UUID | None = None


class RepresentationDecisionResponse(BaseModel):
    decision_id: uuid.UUID
    outcome: str
    decided_at: datetime
    correlation_id: str | None = None


class WorkflowSummary(BaseModel):
    workflow_id: uuid.UUID
    matter_candidate_id: uuid.UUID
    state: EngagementState
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowDetail(BaseModel):
    workflow_id: uuid.UUID
    tenant_id: uuid.UUID
    matter_candidate_id: uuid.UUID
    candidate_version: int
    state: EngagementState
    version: int
    representation_decision_id: uuid.UUID | None = None
    conflict_review_id: uuid.UUID | None = None
    engagement_package_id: uuid.UUID | None = None
    activation_checklist_id: uuid.UUID | None = None
    activated_matter_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewQueueResponse(BaseModel):
    workflows: list[WorkflowSummary]


class TimelineEvent(BaseModel):
    event_id: uuid.UUID
    event_type: str
    occurred_at: datetime
    authority_class: str
    actor_id: str
    from_state: str | None = None
    to_state: str | None = None


class WorkflowTimelineResponse(BaseModel):
    workflow_id: uuid.UUID
    events: list[TimelineEvent]
