"""BP-05 Signature Ceremony schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SignerRequirementInput(BaseModel):
    party_role_id: uuid.UUID
    signer_role: str = Field(min_length=1)
    authority_scope: str | None = None
    required: bool = True


class CreateCeremonyRequest(BaseModel):
    provider_type: str = Field(default="docuseal")
    signers: list[SignerRequirementInput] = Field(min_length=1)
    expires_at: datetime | None = None


class SignerRequirementResponse(BaseModel):
    id: uuid.UUID
    party_role_id: uuid.UUID
    signer_role: str
    required: bool

    model_config = {"from_attributes": True}


class CreateCeremonyResponse(BaseModel):
    ceremony_id: uuid.UUID
    provider_type: str
    state: str
    created_at: datetime
    signers: list[SignerRequirementResponse]


class CeremonyDetailResponse(BaseModel):
    ceremony_id: uuid.UUID
    package_id: uuid.UUID
    provider_type: str
    state: str
    created_at: datetime
    expires_at: datetime | None = None
    signers: list[SignerRequirementResponse]
    signatures: list[dict]


class ApplySignatureRequest(BaseModel):
    party_role_id: uuid.UUID
    shared_signature_evidence_id: uuid.UUID
    signer_requirement_id: uuid.UUID


class ApplySignatureResponse(BaseModel):
    evidence_id: uuid.UUID
    validity_state: str


class InvalidateSignatureRequest(BaseModel):
    evidence_id: uuid.UUID
    reason: str = Field(min_length=1)


class InvalidateSignatureResponse(BaseModel):
    evidence_id: uuid.UUID
    validity_state: str


class MarkExecutedResponse(BaseModel):
    ceremony_id: uuid.UUID
    state: str
    executed_at: datetime
