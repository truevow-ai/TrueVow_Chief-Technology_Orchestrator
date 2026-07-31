"""Add DeliveryAuthorization, ClientPortalAccess, ESignConsent tables.

Revision ID: 0005_portal_and_delivery
Revises: 0004_template_package_tables
Create Date: 2026-07-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_portal_and_delivery"
down_revision: str | None = "0004_template_package_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delivery_authorizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), sa.ForeignKey("retainer.engagement_packages.id"), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("authorized_by_actor_id", sa.Text(), nullable=False),
        sa.Column("authority_record_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False, server_default="portal"),
        sa.Column("recipient_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("authorized_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="retainer",
    )
    op.create_index("ix_delivery_authorizations_tenant_id", "delivery_authorizations", ["tenant_id"], schema="retainer")

    op.create_table(
        "client_portal_access",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("access_token_hash", sa.String(64), nullable=False),
        sa.Column("package_id", sa.Uuid(), sa.ForeignKey("retainer.engagement_packages.id"), nullable=False),
        sa.Column("prospect_party_role_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="ISSUED"),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("access_token_hash"),
        schema="retainer",
    )
    op.create_index("ix_client_portal_access_tenant_id", "client_portal_access", ["tenant_id"], schema="retainer")

    op.create_table(
        "esign_consent_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("portal_access_id", sa.Uuid(), sa.ForeignKey("retainer.client_portal_access.id"), nullable=False),
        sa.Column("prospect_party_role_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="GRANTED"),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="retainer",
    )
    op.create_index("ix_esign_consent_records_tenant_id", "esign_consent_records", ["tenant_id"], schema="retainer")


def downgrade() -> None:
    op.drop_table("esign_consent_records", schema="retainer")
    op.drop_table("client_portal_access", schema="retainer")
    op.drop_table("delivery_authorizations", schema="retainer")
