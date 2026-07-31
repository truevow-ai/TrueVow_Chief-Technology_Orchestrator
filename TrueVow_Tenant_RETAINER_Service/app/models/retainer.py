"""RETAINER domain models.

All tables are in the ``retainer`` schema. Every tenant-owned table carries a
non-null tenant_id. Shared canonical records are referenced by ID and remain
owned by their shared/canonical services.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RetainerWorkflow(Base, TimestampMixin):
    __tablename__ = "retainer_workflows"
    __table_args__ = (
        UniqueConstraint("tenant_id", "matter_candidate_id", "candidate_version"),
        CheckConstraint("version > 0"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    matter_candidate_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    candidate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False, default="NOT_STARTED")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    representation_decision_id: Mapped[_uuid.UUID | None] = mapped_column(
        Uuid, nullable=True
    )
    conflict_review_id: Mapped[_uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    engagement_package_id: Mapped[_uuid.UUID | None] = mapped_column(
        Uuid, nullable=True
    )
    activation_checklist_id: Mapped[_uuid.UUID | None] = mapped_column(
        Uuid, nullable=True
    )
    activated_matter_id: Mapped[_uuid.UUID | None] = mapped_column(
        Uuid, nullable=True
    )


class RepresentationDecision(Base):
    __tablename__ = "representation_decisions"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    matter_candidate_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    scope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    attorney_actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    authority_record_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    supersedes_id: Mapped[_uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("representation_decisions.id"), nullable=True
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ConflictSearch(Base):
    __tablename__ = "conflict_searches"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    party_set_version: Mapped[int] = mapped_column(Integer, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    scope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConflictCandidate(Base):
    __tablename__ = "conflict_candidates"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    search_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conflict_searches.id"), nullable=False
    )
    matched_party_ref: Mapped[str] = mapped_column(Text, nullable=False)
    match_basis_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rule_or_score: Mapped[str | None] = mapped_column(Text, nullable=True)
    disposition: Mapped[str] = mapped_column(String, nullable=False, default="UNREVIEWED")


class ConflictReview(Base):
    __tablename__ = "conflict_reviews"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    search_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conflict_searches.id"), nullable=False
    )
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    attorney_actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    authority_record_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    rationale_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConflictSearchParty(Base):
    __tablename__ = "conflict_search_parties"
    __table_args__ = (
        UniqueConstraint("search_id", "canonical_ref"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    search_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conflict_searches.id"), nullable=False
    )
    party_type: Mapped[str] = mapped_column(String, nullable=False)
    canonical_ref: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    prior_names: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    aliases: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    normalized_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_identifiers: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    relationship_to_candidate: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String, nullable=True)
    candidate_version: Mapped[int] = mapped_column(Integer, nullable=False)


class ConflictSearchSource(Base):
    __tablename__ = "conflict_search_sources"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    search_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conflict_searches.id"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_identifier: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(Text, nullable=False)
    coverage_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ConflictHold(Base):
    __tablename__ = "conflict_holds"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    search_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conflict_searches.id"), nullable=False
    )
    attorney_actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    authority_record_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    affected_candidate_id: Mapped[_uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("conflict_candidates.id"), nullable=True
    )
    supporting_evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    required_followup: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_owner: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_snapshot_id: Mapped[_uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    held_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConflictEvidenceSnapshot(Base):
    __tablename__ = "conflict_evidence_snapshots"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    search_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("conflict_searches.id"), nullable=False
    )
    snapshot_type: Mapped[str] = mapped_column(String, nullable=False)
    party_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_snapshot_id: Mapped[_uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    snapshot_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    snapped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TemplateResolution(Base):
    __tablename__ = "template_resolutions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "workflow_id", "template_definition_id", "template_version"
        ),

    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    template_definition_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    template_version: Mapped[str] = mapped_column(Text, nullable=False)
    template_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    inputs_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EngagementPackage(Base):
    __tablename__ = "engagement_packages"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    template_resolution_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("template_resolutions.id"),
        nullable=False,
    )
    manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String, nullable=False, default="DRAFT")
    package_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TemplateMergeField(Base):
    __tablename__ = "template_merge_fields"
    __table_args__ = (
        UniqueConstraint("template_resolution_id", "field_name"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    template_resolution_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("template_resolutions.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    field_value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    validated: Mapped[bool] = mapped_column(default=True)


class PackagePreflightResult(Base):
    __tablename__ = "package_preflight_results"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    package_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("engagement_packages.id"), nullable=False
    )
    control_id: Mapped[str] = mapped_column(Text, nullable=False)
    control_name: Mapped[str] = mapped_column(Text, nullable=False)
    passed: Mapped[bool] = mapped_column(default=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PackageDocument(Base):
    __tablename__ = "package_documents"
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, primary_key=True)
    package_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("engagement_packages.id"),
        nullable=False,
        primary_key=True,
    )
    document_version_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, nullable=False, primary_key=True
    )
    document_role: Mapped[str] = mapped_column(Text, nullable=False)
    required: Mapped[bool] = mapped_column(default=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DeliveryAuthorization(Base):
    __tablename__ = "delivery_authorizations"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    package_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("engagement_packages.id"), nullable=False
    )
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    authorized_by_actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    authority_record_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False, default="portal")
    recipient_verified: Mapped[bool] = mapped_column(default=False)
    authorized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ClientPortalAccess(Base):
    __tablename__ = "client_portal_access"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    access_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    package_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("engagement_packages.id"), nullable=False
    )
    prospect_party_role_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False, default="PENDING_INVITATION")
    scopes: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    canonical_access_grant_id: Mapped[_uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    source_event_id: Mapped[_uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    last_synchronized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PortalInvitation(Base):
    __tablename__ = "portal_invitations"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    access_grant_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("client_portal_access.id"), nullable=False
    )
    invitation_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    channel: Mapped[str] = mapped_column(String, nullable=False, default="email")
    recipient: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False, default="ISSUED")
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ESignConsent(Base):
    __tablename__ = "esign_consent_records"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    portal_access_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("client_portal_access.id"), nullable=False
    )
    prospect_party_role_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False, default="GRANTED")
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EngagementQuestion(Base):
    __tablename__ = "engagement_questions"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    document_version_id: Mapped[_uuid.UUID | None] = mapped_column(
        Uuid, nullable=True
    )
    page_or_clause_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False, default="RECEIVED")
    submitted_by_actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_actor_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SignatureCeremony(Base):
    __tablename__ = "signature_ceremonies"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    package_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("engagement_packages.id"), nullable=False
    )
    provider_type: Mapped[str] = mapped_column(Text, nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SignerRequirement(Base):
    __tablename__ = "signer_requirements"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    ceremony_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("signature_ceremonies.id"),
        nullable=False,
    )
    party_role_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    signer_role: Mapped[str] = mapped_column(Text, nullable=False)
    authority_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    required: Mapped[bool] = mapped_column(default=True)


class SignatureEvidenceRef(Base):
    __tablename__ = "signature_evidence_refs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "shared_signature_evidence_id"),

    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    ceremony_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("signature_ceremonies.id"),
        nullable=False,
    )
    signer_requirement_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("signer_requirements.id"),
        nullable=False,
    )
    shared_signature_evidence_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, nullable=False
    )
    validity_state: Mapped[str] = mapped_column(String, nullable=False, default="VALID")


class ActivationChecklist(Base):
    __tablename__ = "activation_checklists"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    policy_version_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ActivationChecklistItem(Base):
    __tablename__ = "activation_checklist_items"
    __table_args__ = (
        UniqueConstraint("checklist_id", "control_id"),

    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    checklist_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("activation_checklists.id"),
        nullable=False,
    )
    control_id: Mapped[str] = mapped_column(Text, nullable=False)
    required: Mapped[bool] = mapped_column(default=True)
    result: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    evidence_refs_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: []
    )
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReminderSchedule(Base):
    __tablename__ = "reminder_schedules"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    policy_version_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")


class ReminderAttempt(Base):
    __tablename__ = "reminder_attempts"
    __table_args__ = (
        UniqueConstraint("schedule_id", "attempt_no"),

    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    schedule_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("reminder_schedules.id"),
        nullable=False,
    )
    communication_id: Mapped[_uuid.UUID | None] = mapped_column(
        Uuid, nullable=True
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetainerInboxEvent(Base):
    __tablename__ = "retainer_inbox_events"
    event_id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)


class RetainerOutboxEvent(Base):
    __tablename__ = "retainer_outbox_events"
    event_id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    aggregate_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RetainerIdempotencyKey(Base):
    __tablename__ = "retainer_idempotency_keys"
    tenant_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, nullable=False, primary_key=True
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    command_type: Mapped[str] = mapped_column(Text, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RetainerProjectionCheckpoint(Base):
    __tablename__ = "retainer_projection_checkpoints"
    projection_name: Mapped[str] = mapped_column(Text, nullable=False, primary_key=True)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, nullable=False, primary_key=True
    )
    last_event_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rebuilt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CandidateReview(Base):
    __tablename__ = "candidate_reviews"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    review_state: Mapped[str] = mapped_column(
        String, nullable=False, default="UNREVIEWED"
    )
    prepared_by_actor_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attorney_assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    responsible_attorney_actor_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_version_reviewed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ReviewWorkItem(Base):
    __tablename__ = "review_work_items"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    work_type: Mapped[str] = mapped_column(String, nullable=False)
    assigned_actor_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MissingInformationRequest(Base):
    __tablename__ = "missing_information_requests"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    requested_by_actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    fields_required: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String, nullable=False, default="OPEN")
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthorityEvaluation(Base):
    __tablename__ = "authority_evaluations"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    authority_class: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[str] = mapped_column(String, nullable=False)
    policy_snapshot_id: Mapped[_uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ConfigurationResolutionSnapshot(Base):
    __tablename__ = "configuration_resolution_snapshots"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    resolution_type: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version_id: Mapped[_uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    jurisdiction_profile_version_id: Mapped[_uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    resolution_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditEvent(Base):
    __tablename__ = "retainer_audit_events"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    workflow_id: Mapped[_uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    actor_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    authority_class: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(String, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InformationRequestItem(Base):
    __tablename__ = "information_request_items"
    __table_args__ = (
        UniqueConstraint("request_id", "item_key"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    request_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("missing_information_requests.id"), nullable=False
    )
    item_key: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    required: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="REQUESTED")
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InformationSubmission(Base):
    __tablename__ = "information_submissions"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    request_item_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("information_request_items.id"), nullable=False
    )
    submitted_by_actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False, default="TEXT")
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    verification_status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    verified_by_actor_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EngagementOutcome(Base):
    __tablename__ = "engagement_outcomes"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    outcome_class: Mapped[str] = mapped_column(String, nullable=False)
    friction_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_classification: Mapped[str] = mapped_column(String, nullable=False, default="SYSTEM_OBSERVED")
    stated_by_actor_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by_actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ClientExperienceProjection(Base):
    __tablename__ = "client_experience_projections"
    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    tenant_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    workflow_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("retainer_workflows.id"), nullable=False
    )
    recipient_party_role_id: Mapped[_uuid.UUID] = mapped_column(Uuid, nullable=False)
    display_state: Mapped[str] = mapped_column(String, nullable=False)
    primary_action: Mapped[str | None] = mapped_column(String, nullable=True)
    allowed_actions: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    last_updated_event_id: Mapped[_uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    rebuilt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
