"""add templates, packages, signatures, activation, reminders tables

Revision ID: 0002_remaining_tables
Revises: 0001_initial
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_remaining_tables"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "template_resolutions",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("template_definition_id", sa.Uuid(), nullable=False),
        sa.Column("template_version", sa.Text(), nullable=False),
        sa.Column("template_hash", sa.String(64), nullable=False),
        sa.Column("policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("inputs_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "workflow_id", "template_definition_id", "template_version"),
        schema="retainer",
    )

    op.create_table(
        "engagement_packages",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("template_resolution_id", sa.Uuid(), sa.ForeignKey("retainer.template_resolutions.id"), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("package_hash", sa.String(64), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        schema="retainer",
    )

    op.create_table(
        "package_documents",
        sa.Column("tenant_id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("package_id", sa.Uuid(), sa.ForeignKey("retainer.engagement_packages.id"), nullable=False, primary_key=True),
        sa.Column("document_version_id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("document_role", sa.Text(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("document_hash", sa.String(64), nullable=False),
        schema="retainer",
    )

    op.create_table(
        "engagement_questions",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=True),
        sa.Column("page_or_clause_ref", sa.Text(), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("classification", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="RECEIVED"),
        sa.Column("submitted_by_actor_id", sa.Text(), nullable=False),
        sa.Column("assigned_actor_id", sa.Text(), nullable=True),
        sa.Column("response_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        schema="retainer",
    )

    op.create_table(
        "signature_ceremonies",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), sa.ForeignKey("retainer.engagement_packages.id"), nullable=False),
        sa.Column("provider_type", sa.Text(), nullable=False),
        sa.Column("provider_ref", sa.Text(), nullable=True),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        schema="retainer",
    )

    op.create_table(
        "signer_requirements",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("ceremony_id", sa.Uuid(), sa.ForeignKey("retainer.signature_ceremonies.id"), nullable=False),
        sa.Column("party_role_id", sa.Uuid(), nullable=False),
        sa.Column("signer_role", sa.Text(), nullable=False),
        sa.Column("authority_scope", sa.Text(), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        schema="retainer",
    )

    op.create_table(
        "signature_evidence_refs",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("ceremony_id", sa.Uuid(), sa.ForeignKey("retainer.signature_ceremonies.id"), nullable=False),
        sa.Column("signer_requirement_id", sa.Uuid(), sa.ForeignKey("retainer.signer_requirements.id"), nullable=False),
        sa.Column("shared_signature_evidence_id", sa.Uuid(), nullable=False),
        sa.Column("validity_state", sa.String(), nullable=False, server_default="VALID"),
        sa.UniqueConstraint("tenant_id", "shared_signature_evidence_id"),
        schema="retainer",
    )

    op.create_table(
        "activation_checklists",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        schema="retainer",
    )

    op.create_table(
        "activation_checklist_items",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("checklist_id", sa.Uuid(), sa.ForeignKey("retainer.activation_checklists.id"), nullable=False),
        sa.Column("control_id", sa.Text(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("result", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("checklist_id", "control_id"),
        schema="retainer",
    )

    op.create_table(
        "reminder_schedules",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="ACTIVE"),
        schema="retainer",
    )

    op.create_table(
        "reminder_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), sa.ForeignKey("retainer.reminder_schedules.id"), nullable=False),
        sa.Column("communication_id", sa.Uuid(), nullable=True),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("schedule_id", "attempt_no"),
        schema="retainer",
    )


def downgrade() -> None:
    tables = [
        "reminder_attempts", "reminder_schedules",
        "activation_checklist_items", "activation_checklists",
        "signature_evidence_refs", "signer_requirements", "signature_ceremonies",
        "engagement_questions", "package_documents", "engagement_packages",
        "template_resolutions",
    ]
    for t in tables:
        op.execute(f"DROP TABLE IF EXISTS retainer.{t} CASCADE")
