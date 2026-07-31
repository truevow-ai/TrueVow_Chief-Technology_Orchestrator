"""Request and response schemas for BP-03 Template Resolution and Package Generation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MergeFieldInput(BaseModel):
    field_name: str = Field(min_length=1)
    field_value: str = Field(min_length=1)
    source: str = Field(default="candidate_record")


class ResolveTemplateRequest(BaseModel):
    template_definition_id: uuid.UUID
    template_version: str = Field(min_length=1)
    policy_version_id: uuid.UUID
    merge_fields: list[MergeFieldInput] = Field(default_factory=list)
    jurisdiction_profile_version_id: uuid.UUID | None = None


class MergeFieldResponse(BaseModel):
    field_name: str
    field_value: str
    source: str
    validated: bool

    model_config = {"from_attributes": True}


class ResolveTemplateResponse(BaseModel):
    resolution_id: uuid.UUID
    template_definition_id: uuid.UUID
    template_version: str
    template_hash: str
    resolved_at: datetime
    merge_fields: list[MergeFieldResponse]


class PreflightControlInput(BaseModel):
    control_id: str
    control_name: str
    passed: bool
    detail: str | None = None


class GeneratePackageRequest(BaseModel):
    template_resolution_id: uuid.UUID
    document_roles: list[str] = Field(default_factory=list)
    preflight_controls: list[PreflightControlInput] = Field(default_factory=list)


class PreflightResultResponse(BaseModel):
    control_id: str
    control_name: str
    passed: bool
    detail: str | None = None

    model_config = {"from_attributes": True}


class PackageDocumentResponse(BaseModel):
    document_version_id: uuid.UUID
    document_role: str
    required: bool
    sequence: int
    document_hash: str

    model_config = {"from_attributes": True}


class GeneratePackageResponse(BaseModel):
    package_id: uuid.UUID
    status: str
    package_hash: str
    generated_at: datetime
    documents: list[PackageDocumentResponse]
    preflight_results: list[PreflightResultResponse]


class PackageDetailResponse(BaseModel):
    package_id: uuid.UUID
    workflow_id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    package_hash: str
    generated_at: datetime
    locked_at: datetime | None = None
    documents: list[PackageDocumentResponse]
    preflight_results: list[PreflightResultResponse]
