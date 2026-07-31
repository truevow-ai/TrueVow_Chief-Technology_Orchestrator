"""v1.1 Addendum — InformationRequestItem, InformationSubmission, EngagementOutcome, ClientExperienceProjection.

Revision ID: 0006_v11_addendum
Revises: 0005_portal_and_delivery
Create Date: 2026-07-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_v11_addendum"
down_revision: str | None = "0005_portal_and_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "information_request_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), sa.ForeignKey("retainer.missing_information_requests.id"), nullable=False),
        sa.Column("item_key", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("status", sa.String(), nullable=False, server_default="REQUESTED"),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "item_key"),
        schema="retainer",
    )
    op.create_index("ix_info_request_items_tenant_id", "information_request_items", ["tenant_id"], schema="retainer")

    op.create_table(
        "information_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("request_item_id", sa.Uuid(), sa.ForeignKey("retainer.information_request_items.id"), nullable=False),
        sa.Column("submitted_by_actor_id", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False, server_default="TEXT"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("verification_status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("verified_by_actor_id", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="retainer",
    )
    op.create_index("ix_info_submissions_tenant_id", "information_submissions", ["tenant_id"], schema="retainer")

    op.create_table(
        "engagement_outcomes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("outcome_class", sa.String(), nullable=False),
        sa.Column("friction_reason", sa.String(), nullable=True),
        sa.Column("evidence_classification", sa.String(), nullable=False, server_default="SYSTEM_OBSERVED"),
        sa.Column("stated_by_actor_id", sa.Text(), nullable=True),
        sa.Column("recorded_by_actor_id", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="retainer",
    )
    op.create_index("ix_engagement_outcomes_tenant_id", "engagement_outcomes", ["tenant_id"], schema="retainer")

    op.create_table(
        "client_experience_projections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("recipient_party_role_id", sa.Uuid(), nullable=False),
        sa.Column("display_state", sa.String(), nullable=False),
        sa.Column("primary_action", sa.String(), nullable=True),
        sa.Column("allowed_actions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("last_updated_event_id", sa.Uuid(), nullable=True),
        sa.Column("rebuilt_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="retainer",
    )
    op.create_index("ix_client_exp_projections_tenant_id", "client_experience_projections", ["tenant_id"], schema="retainer")


def downgrade() -> None:
    op.drop_table("client_experience_projections", schema="retainer")
    op.drop_table("engagement_outcomes", schema="retainer")
    op.drop_table("information_submissions", schema="retainer")
    op.drop_table("information_request_items", schema="retainer")
