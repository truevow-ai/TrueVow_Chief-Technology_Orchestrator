"""BP-06/07 Communications and Activation schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateReminderScheduleRequest(BaseModel):
    policy_version_id: uuid.UUID
    max_attempts: int = Field(default=5, ge=1)
    next_due_at: datetime | None = None


class CreateReminderScheduleResponse(BaseModel):
    schedule_id: uuid.UUID
    state: str


class SendReminderRequest(BaseModel):
    communication_id: uuid.UUID
    attempt_no: int = Field(ge=1)
    result: str = Field(default="SENT")


class SendReminderResponse(BaseModel):
    attempt_id: uuid.UUID
    attempt_no: int


class ExpireEngagementResponse(BaseModel):
    workflow_id: uuid.UUID
    state: str


class ChecklistItemInput(BaseModel):
    control_id: str = Field(min_length=1)
    required: bool = True


class CreateChecklistRequest(BaseModel):
    policy_version_id: uuid.UUID
    items: list[ChecklistItemInput] = Field(min_length=1)


class ChecklistItemResponse(BaseModel):
    id: uuid.UUID
    control_id: str
    required: bool
    result: str

    model_config = {"from_attributes": True}


class CreateChecklistResponse(BaseModel):
    checklist_id: uuid.UUID
    state: str
    items: list[ChecklistItemResponse]


class EvaluateItemRequest(BaseModel):
    result: str = Field(min_length=1)
    evidence_refs: list | None = None


class EvaluateItemResponse(BaseModel):
    item_id: uuid.UUID
    result: str


class AuthorizeActivationResponse(BaseModel):
    checklist_id: uuid.UUID
    state: str


class ConfirmActivationRequest(BaseModel):
    activated_matter_id: uuid.UUID


class ConfirmActivationResponse(BaseModel):
    workflow_id: uuid.UUID
    state: str
    activated_matter_id: uuid.UUID
