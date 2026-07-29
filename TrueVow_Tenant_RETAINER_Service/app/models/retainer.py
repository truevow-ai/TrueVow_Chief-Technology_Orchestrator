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
