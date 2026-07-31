"""Request and response schemas for BP-02 Conflict Search and Attorney Clearance."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConflictSearchPartyInput(BaseModel):
    party_type: str = Field(min_length=1)
    canonical_ref: uuid.UUID
    legal_name: str = Field(min_length=1)
    prior_names: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    normalized_name: str | None = None
    date_of_birth: str | None = None
    organization_identifiers: list[str] = Field(default_factory=list)
    relationship_to_candidate: str | None = None
    source: str | None = None
    confidence: str | None = None


class StartConflictSearchRequest(BaseModel):
    parties: list[ConflictSearchPartyInput] = Field(min_length=1)
    candidate_version: int = Field(ge=1)
    scope_json: dict = Field(default_factory=dict)


class ConflictSearchPartyResponse(BaseModel):
    id: uuid.UUID
    party_type: str
    canonical_ref: uuid.UUID
    legal_name: str
    prior_names: list
    aliases: list
    normalized_name: str | None = None
    relationship_to_candidate: str | None = None

    model_config = {"from_attributes": True}


class ConflictCandidateResponse(BaseModel):
    id: uuid.UUID
    matched_party_ref: str
    match_basis_json: dict
    rule_or_score: str | None = None
    disposition: str

    model_config = {"from_attributes": True}


class StartConflictSearchResponse(BaseModel):
    search_id: uuid.UUID
    status: str
    started_at: datetime
    party_count: int


class ConflictSearchDetailResponse(BaseModel):
    search_id: uuid.UUID
    workflow_id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    party_set_version: int
    algorithm_version: str
    started_at: datetime
    completed_at: datetime | None = None
    parties: list[ConflictSearchPartyResponse]
    candidates: list[ConflictCandidateResponse]
    current_hold: dict | None = None
    review_outcome: str | None = None


class ConflictListResponse(BaseModel):
    searches: list[ConflictSearchDetailResponse]


class DispositionRequest(BaseModel):
    disposition: str = Field(min_length=1)
    rationale: str | None = None


class DispositionResponse(BaseModel):
    candidate_id: uuid.UUID
    disposition: str


class ApplyHoldRequest(BaseModel):
    reason: str = Field(min_length=1)
    authority_record_id: uuid.UUID
    affected_candidate_id: uuid.UUID | None = None
    supporting_evidence: dict = Field(default_factory=dict)
    required_followup: str | None = None
    policy_snapshot_id: uuid.UUID | None = None


class ApplyHoldResponse(BaseModel):
    hold_id: uuid.UUID
    held_at: datetime


class ReleaseHoldRequest(BaseModel):
    authority_record_id: uuid.UUID
    reason: str = Field(min_length=1)


class ReleaseHoldResponse(BaseModel):
    hold_id: uuid.UUID
    released_at: datetime | None = None


class ClearConflictRequest(BaseModel):
    authority_record_id: uuid.UUID
    rationale: str | None = None
    policy_snapshot_id: uuid.UUID | None = None


class ClearConflictResponse(BaseModel):
    review_id: uuid.UUID
    outcome: str
    decided_at: datetime


class RerunSearchRequest(BaseModel):
    reason: str = Field(min_length=1)
    parties: list[ConflictSearchPartyInput] = Field(default_factory=list)
    candidate_version: int = Field(ge=1)


class RerunSearchResponse(BaseModel):
    search_id: uuid.UUID
    status: str
    started_at: datetime
    supersedes_search_id: uuid.UUID


class ConflictAuditEntry(BaseModel):
    event_id: uuid.UUID
    event_type: str
    actor_id: str
    actor_role: str | None = None
    authority_class: str | None = None
    action: str
    result: str
    occurred_at: datetime


class ConflictAuditResponse(BaseModel):
    search_id: uuid.UUID
    audit_entries: list[ConflictAuditEntry]
