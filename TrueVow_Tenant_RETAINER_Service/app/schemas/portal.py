"""BP-04 Client Engagement Portal schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AuthorizeDeliveryRequest(BaseModel):
    authority_record_id: uuid.UUID
    channel: str = Field(default="portal")
    recipient_verified: bool = False


class AuthorizeDeliveryResponse(BaseModel):
    authorization_id: uuid.UUID
    authorized_at: datetime


class GeneratePortalTokenRequest(BaseModel):
    prospect_party_role_id: uuid.UUID
    package_id: uuid.UUID


class PortalTokenResponse(BaseModel):
    access_token: str
    token_hash: str
    issued_at: datetime
    expires_at: datetime | None = None


class PortalAccessDetailResponse(BaseModel):
    access_id: uuid.UUID
    package_id: uuid.UUID
    state: str
    issued_at: datetime
    first_accessed_at: datetime | None = None
    documents: list[dict]
    consent_status: str | None = None


class GrantConsentRequest(BaseModel):
    prospect_party_role_id: uuid.UUID
    ip_address: str | None = None
    user_agent: str | None = None


class GrantConsentResponse(BaseModel):
    consent_id: uuid.UUID
    state: str
    granted_at: datetime


class SubmitQuestionRequest(BaseModel):
    question_text: str = Field(min_length=1)
    document_version_id: uuid.UUID | None = None
    page_or_clause_ref: str | None = None


class SubmitQuestionResponse(BaseModel):
    question_id: uuid.UUID
    state: str
    created_at: datetime


class ClientDeclineRequest(BaseModel):
    reason: str | None = None


class ClientDeclineResponse(BaseModel):
    workflow_id: uuid.UUID
    state: str
    declined_at: datetime
