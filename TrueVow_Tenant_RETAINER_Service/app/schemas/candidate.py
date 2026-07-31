"""Request and response schemas for BP-01 Candidate Review and Representation Decision."""

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
    candidate_id: uuid.UUID
    state: EngagementState
    candidate_version: int


class CandidateSummary(BaseModel):
    candidate_id: uuid.UUID
    workflow_id: uuid.UUID
    state: EngagementState
    candidate_version: int
    review_state: str
    responsible_attorney: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CandidateListResponse(BaseModel):
    candidates: list[CandidateSummary]


class CandidateDetailResponse(BaseModel):
    candidate_id: uuid.UUID
    workflow_id: uuid.UUID
    tenant_id: uuid.UUID
    state: EngagementState
    candidate_version: int
    version: int
    review_state: str | None = None
    prepared_by_actor_id: str | None = None
    responsible_attorney_actor_id: str | None = None
    representation_decision_id: uuid.UUID | None = None
    decision_outcome: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StartReviewRequest(BaseModel):
    pass


class StartReviewResponse(BaseModel):
    review_id: uuid.UUID
    review_state: str


class AssignAttorneyRequest(BaseModel):
    attorney_actor_id: str = Field(min_length=1)


class AssignAttorneyResponse(BaseModel):
    review_id: uuid.UUID
    responsible_attorney_actor_id: str


class RequestInformationRequest(BaseModel):
    reason: str = Field(min_length=1)
    fields_required: list[str] = Field(default_factory=list)


class RequestInformationResponse(BaseModel):
    request_id: uuid.UUID
    state: str


class RepresentationDecisionRequest(BaseModel):
    outcome: Annotated[str, Field(pattern="^(APPROVED|DECLINED|DEFERRED)$")]
    scope_json: dict = Field(default_factory=dict)
    authority_record_id: uuid.UUID
    policy_snapshot_id: uuid.UUID | None = None


class RepresentationDecisionResponse(BaseModel):
    decision_id: uuid.UUID
    outcome: str
    decided_at: datetime


class AuditEntry(BaseModel):
    event_id: uuid.UUID
    event_type: str
    actor_id: str
    actor_role: str | None = None
    authority_class: str | None = None
    action: str
    result: str
    occurred_at: datetime


class AuditResponse(BaseModel):
    candidate_id: uuid.UUID
    audit_entries: list[AuditEntry]


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
